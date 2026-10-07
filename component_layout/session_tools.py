"""Portable session controls shared by learning and microscopy pages."""
import hashlib
import json
import uuid

import streamlit as st

from session_archive import export_session, import_session
from workspace import get_workspace, now


SNAPSHOT_KEY = "portable_session_snapshot"
INCLUDE_IMAGES_KEY = "portable_session_include_images"


def session_fingerprint(ws):
    """Track exportable edits without hashing or copying large image buffers."""
    summary = {key: value for key, value in ws.items() if key != "images"}
    summary["images"] = {
        sha: {key: value for key, value in image.items() if key != "data"}
        for sha, image in ws["images"].items()
    }
    return hashlib.sha256(json.dumps(summary, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def clear_session():
    for key in list(st.session_state):
        del st.session_state[key]


def note_download(snapshot_id):
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    if snapshot and snapshot.get("snapshot_id") == snapshot_id:
        snapshot["download_requested_at"] = now()


def sync_export_options(widget_key):
    st.session_state[INCLUDE_IMAGES_KEY] = st.session_state[widget_key]


def render_portable_session(*, prefix="session"):
    """Render export/restore controls; the caller owns the surrounding panel."""
    ws = get_workspace(st.session_state)
    fingerprint = session_fingerprint(ws)
    st.caption(
        "Save a ZIP to your device to keep analyses, reviews, bookmarks, learning lists, "
        "completed practice and your unfinished adaptive quiz. Species-practice drafts "
        "and running batch queues are not included."
    )
    include_key = f"{prefix}_include_images"
    st.session_state[include_key] = st.session_state.get(INCLUDE_IMAGES_KEY, False)
    include = st.checkbox("Include retained source images", key=include_key,
                          on_change=sync_export_options, args=(include_key,))
    image_count = len(ws["images"]) if include else 0
    st.write(
        f"Export includes {len(ws['records'])} analyses, {len(ws['bookmarks'])} bookmarks, "
        f"{len(ws['learning_lists'])} learning lists, {len(ws['quiz_attempts'])} completed "
        f"practice sets and {image_count} source images."
    )
    if not include and ws["records"]:
        st.caption("Source images are excluded. Restoring this ZIP keeps reports; image review will require the matching originals.")
    running = bool(st.session_state.get("analysis_job", {}).get("running"))
    if running:
        st.info("A batch is in progress. Keep Detector → Advanced workspace → Batch and comparison open to finish it, or cancel between images there, before exporting your session.")
    if st.button("Prepare session archive", key=f"{prefix}_prepare", icon=":material/archive:", disabled=running):
        try:
            data = export_session(ws, include)
            st.session_state[SNAPSHOT_KEY] = {
                "data": data, "fingerprint": fingerprint, "include_images": include,
                "prepared_at": now(), "download_requested_at": None,
                "snapshot_id": uuid.uuid4().hex,
            }
            # Both panels must serve the same prepared bytes in this render.
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    if snapshot:
        stale = snapshot["fingerprint"] != fingerprint or snapshot["include_images"] != include
        if stale:
            st.warning("Session data or export options changed. Prepare the archive again before downloading.")
        elif not running:
            st.caption(f"Archive prepared: {snapshot['prepared_at'][:19]} UTC · Current session snapshot")
        st.download_button(
            "Download prepared session snapshot", snapshot["data"], "parasite_session.zip",
            "application/zip", key=f"{prefix}_download", disabled=stale or running,
            on_click=note_download, args=(snapshot["snapshot_id"],),
        )
        if snapshot.get("download_requested_at"):
            st.caption(f"Download requested: {snapshot['download_requested_at'][:19]} UTC. Check your browser's downloads to confirm the file was saved.")
    upload = st.file_uploader("Import a session archive", type=["zip"], max_upload_size=256,
                              key=f"{prefix}_import")
    replace = st.checkbox("Replace the current workspace with this archive", key=f"{prefix}_replace")
    if st.button("Validate and restore session", disabled=upload is None or not replace,
                 key=f"{prefix}_restore", icon=":material/restore:"):
        try:
            restored = import_session(upload.getvalue())
        except ValueError as exc:
            st.error(str(exc))
        else:
            clear_session()
            st.session_state["workspace"] = restored
            st.session_state["portable_session_notice"] = (
                "Session restored. Reports and learning progress are available. "
                "Image review requires included or matching source images."
            )
            st.rerun()


def render_session_tools():
    ws = get_workspace(st.session_state)
    st.caption(":material/history: Saved in this session only · Export a ZIP to keep your work after the session ends or the server restarts.")
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    if st.session_state.get("analysis_job", {}).get("running"):
        st.caption(":material/hourglass_top: Batch in progress · Open the Detector batch workspace to finish or pause it before downloading your session.")
    elif snapshot:
        changed = snapshot["fingerprint"] != session_fingerprint(ws)
        if changed:
            st.caption(":material/edit: Changes since the prepared archive · Open Session tools to create an updated copy.")
        elif snapshot.get("download_requested_at"):
            st.caption(f"Last download requested: {snapshot['download_requested_at'][:19]} UTC · No changes since that snapshot.")
        else:
            st.caption("Archive prepared, awaiting download · Open Session tools to save it to your device.")
    if notice := st.session_state.pop("portable_session_notice", None):
        st.success(notice)
    with st.expander("Session tools · export and restore"):
        render_portable_session(prefix="global_session")
