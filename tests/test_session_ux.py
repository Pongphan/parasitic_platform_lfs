import io

import streamlit as st
from streamlit.testing.v1 import AppTest

from component_layout.session_tools import SNAPSHOT_KEY, session_fingerprint
from session_archive import export_session, import_session
from test_app import app, explicit_navigation_test_runtime
from test_workspace import png, record
from workspace import add_record, new_workspace, retain_image, update_review


def session_download(at):
    return next(item for item in at.get("download_button")
                if item.proto.label == "Download prepared session snapshot")


def test_learning_export_detects_changes_and_survives_navigation():
    at = app().switch_page("pages/atlas.py").run()
    at.button(key="global_session_prepare").click().run()
    assert not at.exception
    assert not session_download(at).proto.disabled
    initial = at.session_state[SNAPSHOT_KEY]["fingerprint"]
    selected = at.selectbox(key="atlas_species").value
    at.button(key="atlas_bookmark").click().run()
    assert session_download(at).proto.disabled
    assert any("Changes since" in item.value for item in at.caption)
    at.button(key="global_session_prepare").click().run()
    snapshot = at.session_state[SNAPSHOT_KEY]
    assert snapshot["fingerprint"] != initial
    assert selected in import_session(snapshot["data"])["bookmarks"]
    at.switch_page("pages/examination.py").run()
    assert not at.exception
    assert not session_download(at).proto.disabled
    at.checkbox(key="global_session_include_images").set_value(True).run()
    assert session_download(at).proto.disabled


def test_global_restore_requires_confirmation_and_restores_on_learning_page(monkeypatch):
    ws = new_workspace()
    ws["bookmarks"] = ["giardia_duodenalis"]
    data = export_session(ws)
    original = st.file_uploader
    monkeypatch.setattr(st, "file_uploader", lambda label, *args, **kwargs:
                        io.BytesIO(data) if kwargs.get("key") == "global_session_import"
                        else original(label, *args, **kwargs))
    at = app().switch_page("pages/atlas.py").run()
    assert at.button(key="global_session_restore").disabled
    at.checkbox(key="global_session_replace").set_value(True).run()
    at.button(key="global_session_restore").click().run()
    assert not at.exception
    assert at.session_state["workspace"]["bookmarks"] == ["giardia_duodenalis"]
    assert any("Session restored" in item.value for item in at.success)
    assert not at.checkbox(key="global_session_replace").value


def test_invalid_global_restore_preserves_current_work(monkeypatch):
    original = st.file_uploader
    monkeypatch.setattr(st, "file_uploader", lambda label, *args, **kwargs:
                        io.BytesIO(b"invalid ZIP") if kwargs.get("key") == "global_session_import"
                        else original(label, *args, **kwargs))
    at = app()
    at.session_state["workspace"]["bookmarks"] = ["giardia_duodenalis"]
    before = session_fingerprint(at.session_state["workspace"])
    at.checkbox(key="global_session_replace").set_value(True).run()
    at.button(key="global_session_restore").click().run()
    assert not at.exception
    assert at.error
    assert session_fingerprint(at.session_state["workspace"]) == before


def test_session_fingerprint_tracks_reviews_and_image_retention():
    ws = new_workspace()
    retain_image(ws, png())
    analysis = add_record(ws, record())
    before = session_fingerprint(ws)
    update_review(analysis, "0", "accepted", "egg", [2, 3, 12, 13])
    reviewed = session_fingerprint(ws)
    assert reviewed != before
    ws["images"].clear()
    assert session_fingerprint(ws) != reviewed


def portable_controls():
    """Match app.py's render order without starting a real batch or model."""
    return AppTest.from_string(
        "import streamlit as st\n"
        "from component_layout.session_tools import render_portable_session, render_session_tools\n"
        "slot = st.container()\n"
        "render_portable_session(prefix='session')\n"
        "with slot:\n"
        "    render_session_tools()\n",
        default_timeout=30,
    ).run()


def portable_downloads(at):
    return [item.proto for item in at.get("download_button")
            if item.proto.label == "Download prepared session snapshot"]


def test_local_and_global_export_options_and_downloads_stay_synchronized():
    at = portable_controls()
    retain_image(at.session_state["workspace"], png())
    at.checkbox(key="global_session_include_images").set_value(True).run()
    assert not at.exception
    assert at.checkbox(key="session_include_images").value
    at.button(key="session_prepare").click().run()
    assert not at.exception
    downloads = portable_downloads(at)
    assert len(downloads) == 2 and all(not item.disabled for item in downloads)
    assert downloads[0].url == downloads[1].url
    assert len(import_session(at.session_state[SNAPSHOT_KEY]["data"])["images"]) == 1

    at.checkbox(key="session_include_images").set_value(False).run()
    assert not at.checkbox(key="global_session_include_images").value
    assert all(item.disabled for item in portable_downloads(at))
    at.button(key="global_session_prepare").click().run()
    assert not at.exception
    downloads = portable_downloads(at)
    assert len(downloads) == 2 and all(not item.disabled for item in downloads)
    assert downloads[0].url == downloads[1].url
    assert not import_session(at.session_state[SNAPSHOT_KEY]["data"])["images"]


def test_delayed_download_callback_cannot_mark_a_newer_same_workspace_snapshot(monkeypatch):
    from component_layout.session_tools import note_download

    at = portable_controls()
    at.button(key="session_prepare").click().run()
    previous = dict(at.session_state[SNAPSHOT_KEY])
    at.button(key="global_session_prepare").click().run()
    current = at.session_state[SNAPSHOT_KEY]
    assert not at.exception
    assert current["fingerprint"] == previous["fingerprint"]
    assert current["snapshot_id"] != previous["snapshot_id"]
    with monkeypatch.context() as isolated:
        isolated.setattr(st, "session_state", {SNAPSHOT_KEY: current})
        note_download(previous["snapshot_id"])
        assert current["download_requested_at"] is None
        note_download(current["snapshot_id"])
        assert current["download_requested_at"] is not None


def test_running_batch_blocks_session_exports_until_a_fresh_snapshot_is_prepared():
    at = portable_controls()
    at.button(key="global_session_prepare").click().run()
    initial = at.session_state[SNAPSHOT_KEY]["snapshot_id"]
    at.session_state["analysis_job"] = {"running": True}
    at.run()
    assert not at.exception
    assert at.button(key="session_prepare").disabled
    assert at.button(key="global_session_prepare").disabled
    assert all(item.disabled for item in portable_downloads(at))
    assert any("batch" in item.value.casefold() and "progress" in item.value.casefold()
               for item in at.caption)

    # Simulate a fragment completing another item without invoking an ML backend.
    completed = add_record(at.session_state["workspace"], record())
    at.run()
    assert all(item.disabled for item in portable_downloads(at))
    at.session_state["analysis_job"]["running"] = False
    at.run()
    assert not at.button(key="session_prepare").disabled
    assert not at.button(key="global_session_prepare").disabled
    assert all(item.disabled for item in portable_downloads(at))
    assert at.session_state[SNAPSHOT_KEY]["snapshot_id"] == initial
    at.button(key="global_session_prepare").click().run()
    assert not at.exception
    assert all(not item.disabled for item in portable_downloads(at))
    restored = import_session(at.session_state[SNAPSHOT_KEY]["data"])
    assert restored["records"][0]["analysis_id"] == completed["analysis_id"]
