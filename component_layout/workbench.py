"""Advanced detector workflows built with native, keyboard-accessible controls."""
from collections import Counter
from itertools import combinations
import streamlit as st
from workspace import (get_workspace, find_record, review_rows, update_review, undo_review,
                       json_bytes, now, retain_image, enforce_limits, REVIEW_STATES, digest)
from component_ai.images import decode_image, discover_samples
from component_ai.registry import file_version
from component_ai.annotations import annotate_detections
from component_ai.detection import AUTO_MODELS, model_display_name, model_scope
from component_ai.jobs import configuration, prepare_job, step_job, cancel_job, retry_failed, job_records
from component_ai.comparison import match_boxes, validate_coco, evaluate
from session_archive import dataset_export, batch_export, parse_json
from component_layout.session_tools import render_portable_session, clear_session
from content import ROOT, atlas_entries, atlas_for_model_label


def record_label(record):
    return f"{record['image']['name']} · {model_display_name(record['configuration'].get('selected_model', 'Keras crop'))} · {record['created_at'][:19]} · {record['analysis_id'][:6]}"


def snapshot_fingerprint(*values):
    return digest(json_bytes(values))


def region_names(rows):
    return {row["object_id"]: f"Region {index:02d}" for index, row in enumerate(rows, 1)}


def next_unreviewed(rows, current_id, visible_ids):
    remaining = [r for r in rows if r["object_id"] in visible_ids and r["object_id"] != current_id
                 and r["status"] == "unreviewed"]
    return remaining[0]["object_id"] if remaining else None


def retained_image(ws, record):
    stored = ws["images"].get(record["image"]["sha256"])
    return decode_image(stored["data"]) if stored else None


def overlay(image, rows, reviewed=False):
    # Human annotations have no model confidence; strip percentage from review
    # overlays by drawing only IDs/labels via a separate lightweight renderer.
    if not reviewed:
        return annotate_detections(image, rows)
    from PIL import ImageDraw
    result = image.copy()
    draw = ImageDraw.Draw(result)
    for index, row in enumerate(rows, 1):
        if row.get("status") == "rejected":
            continue
        box = row["bbox_xyxy"]
        draw.rectangle(box, outline="#00D5E8", width=max(2, round(image.width/500)))
        draw.text((box[0]+3, box[1]+3), f"{index}: {row['class_name']} [{row.get('status', 'reference')}]", fill="white", stroke_width=2, stroke_fill="black")
    return result


def render_session():
    ws = get_workspace(st.session_state)
    st.subheader("Session workspace")
    st.caption("Session data is lost when the browser session ends or the server restarts. Export to keep a portable copy.")
    with st.expander("Export or restore session"):
        render_portable_session(prefix="session")
    with st.expander("Retention and clear session"):
        st.caption(f"Retaining {len(ws['records'])} analyses and {len(ws['images'])} images. Image accounting includes source bytes plus decoded RGB size; model memory and uploader buffers are additional.")
        with st.form("retention"):
            limit = st.number_input("Retained analysis limit", 1, 200, ws["record_limit"])
            memory = st.number_input("Image memory budget (MB)", 16, 256, ws["image_budget"]//(1024*1024))
            if st.form_submit_button("Apply retention limits"):
                ws.update(record_limit=int(limit), image_budget=int(memory)*1024*1024)
                enforce_limits(ws)
                st.rerun()
        confirm = st.checkbox("I want to remove all data from this browser session", key="confirm_clear")
        st.button("Clear session", disabled=not confirm, on_click=clear_session)
    if notice := st.session_state.pop("workspace_notice", None):
        st.success(notice)
    if not ws["records"]:
        st.info("No retained analyses yet. Run single-image analysis or a batch first.")
    else:
        statuses = st.multiselect("History status", ["completed", "partial", "failed"], default=["completed", "partial", "failed"], key="history_status")
        records = [r for r in reversed(ws["records"]) if r["status"] in statuses]
        st.dataframe([{"Analysis": r["analysis_id"][:8], "Image": r["image"]["name"], "Model": model_display_name(r["configuration"].get("selected_model", "Keras crop")), "Status": r["status"], "Image retained": r["image"]["sha256"] in ws["images"]} for r in records], hide_index=True)
        if records:
            by_id = {r["analysis_id"]: r for r in records}
            if st.session_state.get("history_record") not in by_id:
                st.session_state["history_record"] = next(iter(by_id))
            selected = st.selectbox("Open retained analysis", list(by_id), format_func=lambda key: record_label(by_id[key]), key="history_record")
            render_record(ws, by_id[selected], "history")
    with st.expander("Saved comparisons and practice attempts"):
        for index, comparison in enumerate(reversed(ws["comparisons"])):
            st.write(f"Comparison {index+1} · {comparison['created_at'][:19]} · IoU {comparison['iou']}")
            records = [find_record(ws, key) for key in comparison["analysis_ids"]]
            if all(records):
                if st.button("Reopen comparison", key=f"reopen_comparison_{index}"):
                    st.session_state["opened_comparison"] = comparison
            else:
                st.caption("One or more analysis records were removed by retention limits.")
        if comparison := st.session_state.get("opened_comparison"):
            records = [find_record(ws, key) for key in comparison["analysis_ids"]]
            if all(records):
                render_comparison(ws, records, comparison["iou"], "reopened", save=False)
        attempts = ws["quiz_attempts"]
        if attempts:
            key = st.selectbox("Saved practice attempt", list(attempts), format_func=lambda k: f"{attempts[k]['created_at'][:19]} · {sum(attempts[k]['correct'])}/{len(attempts[k]['questions'])}")
            attempt = attempts[key]
            for q, answer, correct in zip(attempt["questions"], attempt["answers"], attempt["correct"]):
                st.write(f"{'Correct' if correct else 'Review'} · {q['question']} — {q['options'][answer]}")
                st.caption(q["explanation"])
            st.download_button("Download saved practice attempt", json_bytes(attempt), "practice_attempt.json")


def render_record(ws, record, prefix):
    key = prefix + "_" + record["analysis_id"]
    st.caption(f"Analysis {record['analysis_id']} · {record['status']} · {record['elapsed_seconds']:.3f} seconds")
    st.caption("Saved in this session only. Export your session to keep this analysis and its review.")
    for warning in record.get("warnings", []):
        st.warning(warning)
    for error in record.get("errors", []):
        st.error(error.get("error", str(error)) if isinstance(error, dict) else str(error))
    if record.get("notes"):
        st.write("Analysis notes: " + record["notes"])
    image = retained_image(ws, record)
    if image is None:
        st.info("Source image is not retained. Reports and review metadata remain available. Restore the exact original file for image-dependent actions.")
        upload = st.file_uploader("Restore matching source image", type=["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"], key=key+"_restore", max_upload_size=25)
        if st.button("Verify and restore image", key=key+"_restore_button", disabled=upload is None):
            try:
                retain_image(ws, upload.getvalue(), record["image"]["sha256"])
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    if record["mode"] == "keras":
        st.json(record["original"], expanded=False)
        if image:
            box = record["configuration"].get("roi_xyxy")
            st.image(image.crop(box) if box else image, caption="Retained classifier region")
    else:
        view = st.radio("Overlay", ["Original predictions", "Reviewer annotations"], horizontal=True, key=key+"_overlay")
        rows = review_rows(record)
        if image:
            st.image(overlay(image, record["original"].get("detections", []) if view == "Original predictions" else rows, view != "Original predictions"), width="stretch")
            if record["original"].get("detections"):
                with st.expander("Inspect original detected crops"):
                    from component_layout.results import render_crop_gallery
                    render_crop_gallery(image, record["original"]["detections"])
        with st.expander("Review objects and edit source-pixel boxes", expanded=st.session_state.get("expanded_review") == record["analysis_id"]):
            render_review(ws, record, image, key)
    with st.expander("Analysis settings and model provenance"):
        st.json({"configuration": record["configuration"], "model_sha256": record["model_sha256"], "timing": record["original"].get("timing"), "warnings": record["warnings"], "errors": record["errors"]})
    st.download_button("Download versioned analysis and review", json_bytes(record), f"{record['analysis_id']}.json", "application/json", key=key+"_json")


def render_review(ws, record, image, key):
    rows = review_rows(record)
    names = region_names(rows)
    reviewed = sum(row["status"] != "unreviewed" for row in rows)
    st.caption(f"{reviewed} of {len(rows)} regions reviewed. Original model predictions stay unchanged.")
    if notice := st.session_state.pop(key+"_review_notice", None):
        st.success(notice)
    labels = sorted({r["predicted_class"] for r in rows})
    reveal_id = st.session_state.pop(key+"_reveal_review", None)
    revealed = next((r for r in rows if r["object_id"] == reveal_id), None)
    if revealed:
        # Apply on the next rerun before widgets are created. Preserve existing
        # filters while ensuring a newly added region is available for selection.
        for widget_key, value, default in ((key+"_states", revealed["status"], list(REVIEW_STATES)),
                                            (key+"_labels", revealed["predicted_class"], labels)):
            selected_values = list(st.session_state.get(widget_key, default))
            if value not in selected_values:
                selected_values.append(value)
            st.session_state[widget_key] = selected_values
    states = st.multiselect("Review states", REVIEW_STATES, default=list(REVIEW_STATES), key=key+"_states")
    chosen = st.multiselect("Predicted classes", labels, default=labels, key=key+"_labels")
    filtered = [r for r in rows if r["status"] in states and r["predicted_class"] in chosen]
    st.dataframe([{"Region": names[r["object_id"]], "Predicted class": r["predicted_class"],
                   "Reviewer class": r["class_name"], "Status": r["status"],
                   "Box": r["bbox_xyxy"], "Notes": r.get("notes", "")} for r in filtered], hide_index=True)
    by_id = {r["object_id"]: r for r in filtered}
    choices = list(by_id) + ["Add missed object"]
    object_key = key+"_object"
    if not by_id:
        st.info("No regions match these filters. Adjust the filters to continue reviewing, or add a missed object.")
        if st.session_state.get(object_key) != "Add missed object":
            st.session_state[key+"_restore_filtered_selection"] = True
    elif st.session_state.pop(key+"_restore_filtered_selection", False) and st.session_state.get(object_key) == "Add missed object":
        # An empty filter temporarily needs the Add option; returning to visible
        # rows should resume review. An explicitly chosen Add option is preserved.
        st.session_state.pop(object_key, None)
    advance = st.session_state.pop(key+"_advance_to", None)
    if advance in by_id:
        st.session_state[object_key] = advance
    if st.session_state.get(object_key) not in choices:
        st.session_state[object_key] = next((r["object_id"] for r in filtered if r["status"] == "unreviewed"), choices[0])
    selected = st.selectbox("Object to review", choices, key=object_key,
                            format_func=lambda identity: f"{names[identity]} · {by_id[identity]['class_name']} · {by_id[identity]['status']}" if identity in by_id else identity)
    row = by_id.get(selected)
    revision = digest(json_bytes(record["review"]))[:12]
    form_key = f"{key}_{selected}_{revision}"
    if image is None:
        st.caption("Restore the source image to edit annotations; existing review exports remain available.")
    else:
        w, h = image.size
        box = row["bbox_xyxy"] if row else [0,0,min(20,w),min(20,h)]
        preview, editor = st.columns([1, 2])
        with preview:
            if row:
                from PIL import ImageDraw
                from component_layout.results import crop_box
                highlighted = image.copy()
                draw = ImageDraw.Draw(highlighted)
                draw.rectangle(row["bbox_xyxy"], outline="#007C91", width=max(2, round(w/250)))
                st.image(highlighted, caption=f"{names[selected]} highlighted in the source image", width="stretch")
                st.image(image.crop(crop_box(image, row)), caption=f"{names[selected]} · current saved box", width="stretch")
            else:
                st.image(image, caption="Source image — enter the missed object's coordinates", width="stretch")
        with editor:
            with st.form(form_key):
                options = list(REVIEW_STATES) if row else ["corrected", "accepted"]
                status = st.selectbox("Review status", options, index=options.index(row["status"]) if row else 0)
                label = st.text_input("Reviewer class label", value=row["class_name"] if row else "", max_chars=200)
                st.caption(f"Coordinates use the original {w} × {h} image. Use corrected status when changing a predicted label or box.")
                left, right = st.columns(2)
                with left:
                    x1 = st.number_input("Left (x1)", 0.0, float(w), float(box[0]))
                    y1 = st.number_input("Top (y1)", 0.0, float(h), float(box[1]))
                with right:
                    x2 = st.number_input("Right (x2)", 0.0, float(w), float(box[2]))
                    y2 = st.number_input("Bottom (y2)", 0.0, float(h), float(box[3]))
                notes = st.text_area("Reviewer notes", value=row.get("notes", "") if row else "", max_chars=4000)
                save = st.form_submit_button("Save annotation")
                advance_after_save = st.form_submit_button("Save and next", help="Save the chosen status, then open the next unreviewed region in the current filters.")
                if save or advance_after_save:
                    try:
                        saved_id = update_review(record, row["object_id"] if row else None, status, label, [x1,y1,x2,y2], notes)
                        if not row:
                            st.session_state[key+"_reveal_review"] = saved_id
                        next_id = next_unreviewed(review_rows(record), saved_id, by_id)
                        if advance_after_save and next_id:
                            st.session_state[key+"_advance_to"] = next_id
                        elif not row:
                            st.session_state[key+"_advance_to"] = saved_id
                        st.session_state[key+"_review_notice"] = "Annotation saved." + (" No other unreviewed regions in the current filters." if advance_after_save and next_id is None else "")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        if st.button("Undo last annotation change", disabled=not record["review_undo"], key=key+"_undo"):
            undo_review(record)
            st.rerun()
    if row:
        entry = atlas_for_model_label(row["class_name"])
        if entry:
            if st.button("Study " + entry["name"], key=key+"_atlas"):
                st.session_state["requested_atlas_species"] = entry["id"]
                st.switch_page("pages/atlas.py")
        else:
            st.caption("No exact configured Atlas/model label match. Custom review labels do not expand the model's trained classes.")
    st.caption("Dataset exports include accepted/corrected objects only. Review all objects before using the export as an annotation dataset. Corrections are not independent validation and do not retrain models.")
    mapping = st.text_area("Explicit dataset class mapping (one exact label per line; IDs start at 0)", key=key+"_mapping")
    mapped_labels = [s.strip() for s in mapping.splitlines() if s.strip()]
    export_identity = snapshot_fingerprint(record, mapped_labels)
    if st.button("Build COCO and YOLO annotation exports", key=key+"_build"):
        st.session_state.pop("annotation_export", None)
        try:
            data, coco = dataset_export([record], mapped_labels)
            st.session_state["annotation_export"] = {"key": key, "data": data, "coco": json_bytes(coco),
                                                     "fingerprint": export_identity, "created_at": now()}
        except ValueError as exc:
            st.error(str(exc))
    data = st.session_state.get("annotation_export")
    if data and data["key"] == key:
        stale = data.get("fingerprint") != export_identity
        if stale:
            st.warning("Annotations or class mapping changed. Rebuild the annotation exports before downloading.")
        else:
            st.caption("Annotation exports match the current review and class mapping.")
        st.download_button("Download prepared annotation ZIP", data["data"], "reviewed_annotations.zip", key=key+"_zip", disabled=stale)
        st.download_button("Download prepared COCO JSON", data["coco"], "annotations.coco.json", key=key+"_coco", disabled=stale)


def render_batch():
    ws = get_workspace(st.session_state)
    st.subheader("Batch analysis and model comparison")
    st.caption("One model call runs at a time. Cancellation takes effect between calls; an active call finishes first. Keep this page open while processing.")
    max_files = st.number_input("Maximum batch images", 1, 24, 12, key="batch_max")
    models = st.multiselect("Automatic models", AUTO_MODELS, default=[AUTO_MODELS[0]], format_func=model_display_name, key="batch_models")
    for model in models:
        st.caption(model_display_name(model) + ": " + model_scope(model))
    st.caption("Model names identify architectures; they do not rank accuracy.")
    confidence = st.slider("Batch confidence threshold", 0.05, 0.95, 0.7, 0.05, key="batch_confidence")
    uploads = st.file_uploader("Batch microscopy images", type=["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"], accept_multiple_files=True, max_upload_size=25, key="batch_uploads")
    samples = st.multiselect("Or choose bundled samples", discover_samples(ROOT/"component_aiimage"), format_func=lambda p:p.name, key="batch_samples")
    st.caption(f"25 MB / 24 megapixels per image; total source-plus-decoded budget {ws['image_budget']//(1024*1024)} MB. Models are frozen when the queue is prepared.")
    try:
        input_identity = snapshot_fingerprint(models, confidence, max_files,
                         [(u.name, digest(u.getvalue())) for u in (uploads or [])],
                         [(str(p), file_version(p)) for p in samples])
    except OSError as exc:
        st.error(f"A selected sample is unavailable: {exc}")
        return
    job = st.session_state.get("analysis_job")
    if st.button("Validate and start batch", disabled=bool(job and job["running"]) or not models or not (uploads or samples), key="prepare_batch", type="primary"):
        try:
            configs = [configuration(model, confidence) for model in models]
            incoming = [(u.name, u.getvalue()) for u in (uploads or [])] + [(p.name, p.read_bytes()) for p in samples]
            prepared = prepare_job(ws, incoming, configs, int(max_files))
            prepared["running"] = any(item["status"] == "pending" for item in prepared["items"])
            st.session_state["analysis_job"] = prepared
            st.session_state["batch_prepared_inputs"] = input_identity
            st.session_state.pop("batch_export", None)
            st.rerun()
        except (ValueError, OSError) as exc:
            st.error(str(exc))
    changed_inputs = bool(job) and st.session_state.get("batch_prepared_inputs", input_identity) != input_identity
    if changed_inputs:
        st.warning("Batch setup changed. The queue below still uses its original settings. Validate and start a new batch to apply the changes, or restore the previous setup to export this queue.")
    render_queue()
    job = st.session_state.get("analysis_job")
    if job:
        records = job_records(ws, job)
        export_identity = snapshot_fingerprint(records, job, input_identity,
                          [(r["image"]["sha256"], r["image"]["sha256"] in ws["images"]) for r in records])
        if st.button("Prepare batch ZIP", disabled=job["running"] or changed_inputs):
            st.session_state.pop("batch_export", None)
            try:
                st.session_state["batch_export"] = {"data": batch_export(ws, records, job),
                                                   "fingerprint": export_identity}
            except ValueError as exc:
                st.error(str(exc))
        if data := st.session_state.get("batch_export"):
            stale = not isinstance(data, dict) or data.get("fingerprint") != export_identity or changed_inputs or job["running"]
            if stale:
                st.warning("The batch export is out of date. Prepare the ZIP again after the queue, review or setup changes are resolved.")
            else:
                st.caption("Batch export matches the queue and retained reviews shown here.")
            st.download_button("Download prepared batch ZIP", data["data"] if isinstance(data, dict) else data,
                               "batch_analysis.zip", "application/zip", disabled=stale)
        if records:
            by_id = {r["analysis_id"]:r for r in records}
            selected = st.selectbox("Inspect batch analysis", list(by_id), format_func=lambda k:record_label(by_id[k]))
            render_record(ws, by_id[selected], "batch")
    st.divider()
    render_comparison_picker(ws)


@st.fragment(run_every="1s")
def render_queue():
    ws = get_workspace(st.session_state)
    job = st.session_state.get("analysis_job")
    if not job:
        st.info("Choose images and models, then prepare an analysis queue.")
        return
    # An interrupted Streamlit execution may leave a running marker. It is never
    # automatically retried, avoiding duplicate inference after an uncertain end.
    for item in job["items"]:
        if item["status"] == "running":
            item.update(status="failed", error="Previous execution was interrupted. Review and explicitly retry.")
    if st.button("Start / resume queue", disabled=job["running"] or not any(i["status"] == "pending" for i in job["items"])):
        job.update(running=True, cancelled=False)
        st.rerun(scope="app")
    if st.button("Cancel between images", disabled=not job["running"]):
        cancel_job(job)
        st.rerun(scope="app")
    if st.button("Retry inference failures", disabled=job["running"] or not any(i["status"] == "failed" for i in job["items"])):
        retry_failed(job)
        st.rerun(scope="app")
    if job["running"]:
        with st.spinner("Processing the next image/model pair…"):
            step_job(ws, job)
        if not job["running"]:
            # Refresh the outer result picker and exports after the last fragment step.
            st.rerun(scope="app")
    finished = sum(i["status"] in ("completed", "failed", "validation_failed") for i in job["items"])
    counts = Counter(item["status"] for item in job["items"])
    queue_state = "Running" if job["running"] else "Paused" if job["cancelled"] else "Ready" if counts["pending"] else "Finished"
    st.progress(finished/max(1,len(job["items"])), text=f"{queue_state} · {finished} / {len(job['items'])} finished")
    st.caption(f"{counts['completed']} succeeded · {counts['failed']} failed · {counts['validation_failed']} invalid · {counts['pending']} pending")
    states = st.multiselect("Queue status filter", ["pending", "running", "completed", "failed", "validation_failed"], default=["pending", "running", "completed", "failed", "validation_failed"], key="queue_filter")
    st.dataframe([{"Image": i["name"], "Model": model_display_name(i.get("config",{}).get("selected_model", "Validation")), "Status": i["status"], "Error": i["error"] or "", "Analysis": i["analysis_id"] or ""} for i in job["items"] if i["status"] in states], hide_index=True)


def render_comparison_picker(ws):
    records = [r for r in ws["records"] if r["mode"] == "auto" and r["status"] == "completed"]
    if len(records) < 2:
        st.info("Complete at least two automatic analyses of the same image to compare models.")
        return
    by_id = {r["analysis_id"]:r for r in records}
    selected = st.multiselect("Analyses to compare (same source image)", list(by_id), max_selections=3, format_func=lambda k:record_label(by_id[k]), key="comparison_ids")
    iou = st.slider("Spatial agreement IoU", 0.05, 1.0, 0.5, 0.05)
    if len(selected) >= 2:
        records = [by_id[key] for key in selected]
        if len({r["image"]["sha256"] for r in records}) != 1:
            st.warning("Select analyses of the same source image.")
        else:
            render_comparison(ws, records, iou, "comparison")


def render_comparison(ws, records, iou, key, save=True):
    st.caption("Spatial agreement is not correctness. Confidence scores across models are not necessarily comparable; no accuracy ranking is calculated.")
    with st.container(horizontal=True):
        for record in records:
            with st.container(border=True, width=360):
                st.write(model_display_name(record["configuration"].get("selected_model", "")))
                image = retained_image(ws, record)
                detections = record["original"].get("detections", [])
                if image:
                    st.image(annotate_detections(image, detections), width="stretch")
                else:
                    st.caption("Image evicted; numeric results remain available.")
                st.write(dict(Counter(d["class_name"] for d in detections)))
                st.caption(f"Total elapsed: {record['elapsed_seconds']:.3f} s")
                st.json(record["original"].get("timing", {"note": "Separate loading/inference timing unavailable for this record"}), expanded=False)
                st.json(record["configuration"], expanded=False)
                if detections:
                    import altair as alt
                    import pandas as pd
                    frame = pd.DataFrame([{"Class": d["class_name"], "Confidence": d["confidence"]} for d in detections])
                    st.altair_chart(alt.Chart(frame).mark_bar().encode(x=alt.X("Confidence:Q", bin=alt.Bin(step=0.1)), y="count()", color="Class:N"), width="stretch")
    comparisons = []
    for left, right in combinations(records, 2):
        match = match_boxes(left["original"].get("detections", []), right["original"].get("detections", []), iou)
        comparisons.append({"left": left["analysis_id"], "right": right["analysis_id"], **match})
        st.write(f"{model_display_name(left['configuration'].get('selected_model'))} / {model_display_name(right['configuration'].get('selected_model'))}: {len(match['matches'])} spatial matches; {len(match['unmatched_predictions'])} left-only, {len(match['unmatched_references'])} right-only")
        with st.expander("Matching details", expanded=False):
            st.json(match)
    report = {"schema_version": "2027.2", "iou": iou, "policy": "Confidence-ordered, same exact label, best unused IoU; spatial agreement only", "comparisons": comparisons,
              "analyses": [{k:r[k] for k in ("analysis_id", "image", "configuration", "model_sha256", "original")} for r in records]}
    st.download_button("Download comparison report", json_bytes(report), "model_comparison.json", key=key+"_download")
    if save and st.button("Save comparison to session", key=key+"_save"):
        ws["comparisons"].append({"analysis_ids": [r["analysis_id"] for r in records], "iou": iou, "created_at": now()})
        enforce_limits(ws)
        st.success("Comparison saved to Session workspace.")


def render_evaluation():
    ws = get_workspace(st.session_state)
    st.subheader("Ground-truth evaluation")
    st.caption("COCO box subset only: no crowd/ignore boxes, segmentation or keypoints. Listed images with zero annotations are explicit negatives; absent images are unknown. SHA-256 is preferred; otherwise exact filename and dimensions are required.")
    records = [r for r in ws["records"] if r["mode"] == "auto" and r["status"] == "completed"]
    if not records:
        st.info("Complete automatic detection first, then select one model/configuration for evaluation.")
        return
    by_id = {r["analysis_id"]: r for r in records}
    selected = st.multiselect("Analyses to evaluate", list(by_id), format_func=lambda k:record_label(by_id[k]))
    upload = st.file_uploader("COCO bounding-box JSON", type=["json"], max_upload_size=16)
    if upload is None:
        if st.session_state.get("evaluation_report"):
            st.info("Upload the reference dataset and evaluate again to show results for the current inputs.")
        return
    input_identity = None
    try:
        data = parse_json(upload.getvalue())
        _, categories, _ = validate_coco(data)
        st.caption("Explicitly map each reference category to the exact detector label. Mapping does not alter model predictions.")
        mapping = {c["name"]: st.text_input("Prediction label for " + c["name"], key="eval_map_"+str(c["id"])) for c in categories.values()}
        confidence = st.slider("Evaluation confidence threshold", 0.0, 1.0, 0.7, 0.05)
        iou = st.slider("Evaluation IoU threshold", 0.05, 1.0, 0.5, 0.05)
        st.caption("Predictions below the original inference threshold were not retained. To evaluate a lower threshold, rerun inference at that threshold first.")
        origin = st.selectbox("Reference annotation origin", ["Independent annotations (user declared)", "Reviewed model predictions", "Unknown"])
        chosen = [by_id[key] for key in selected]
        input_identity = snapshot_fingerprint(
            [{key: record[key] for key in ("analysis_id", "image", "configuration", "model_sha256", "original")} for record in chosen],
            digest(upload.getvalue()), mapping, confidence, iou, origin)
        if st.button("Evaluate selected analyses", disabled=not selected):
            # A failed new evaluation must not leave the previous result looking current.
            st.session_state.pop("evaluation_report", None)
            st.session_state.pop("evaluation_fingerprint", None)
            if any(confidence < r["configuration"].get("confidence", 0) for r in chosen):
                raise ValueError("Evaluation threshold cannot be lower than the stored inference threshold.")
            report = evaluate(chosen, data, mapping, confidence, iou)
            report["user_declared_reference_origin"] = origin
            st.session_state["evaluation_report"] = report
            st.session_state["evaluation_fingerprint"] = input_identity
    except (ValueError, TypeError, KeyError) as exc:
        input_identity = None
        st.error(str(exc))
    if report := st.session_state.get("evaluation_report"):
        if input_identity is None or st.session_state.get("evaluation_fingerprint") != input_identity:
            st.warning("Evaluation inputs changed. Evaluate again to update the results; the previous report is out of date.")
            st.download_button("Download evaluation report", json_bytes(report), "evaluation.json", "application/json", disabled=True)
            return
        st.success("Evaluation matches the current analyses, reference dataset, mapping and thresholds.")
        st.write("Reference origin: " + report["reference_origin"])
        st.write("User declaration: " + report["user_declared_reference_origin"])
        st.dataframe([{"Class": k, **v} for k,v in report["per_class"].items()], hide_index=True)
        st.write({"Overall": report["overall"], "Excluded analyses": report["excluded"], "Unmatched reference image IDs": report["unmatched_reference_images"]})
        st.caption("Undefined ratios are shown as null. These are threshold-specific metrics, not mAP or clinical validation.")
        if report["images"]:
            details = {r["analysis_id"]:r for r in report["images"]}
            selected = st.selectbox("Inspect unmatched objects", list(details))
            result = details[selected]
            record = find_record(ws, selected)
            image = retained_image(ws, record) if record else None
            fp = [result["predictions"][i] for i in result["unmatched_predictions"]]
            fn = [result["references"][i] for i in result["unmatched_references"]]
            with st.container(horizontal=True):
                for title, rows in [("Unmatched predictions (false positives)", fp), ("Unmatched references (false negatives)", fn)]:
                    with st.container(border=True, width=400):
                        st.write(title)
                        if image:
                            st.image(overlay(image, rows, reviewed=True), width="stretch")
                        st.json(rows, expanded=False)
            if image is None:
                st.info("Source image unavailable; restore it in Session workspace for visual inspection.")
        st.download_button("Download evaluation report", json_bytes(report), "evaluation.json", "application/json")


def render_workbench():
    choice = st.radio("Workspace tool", ["Batch and comparison", "Ground-truth evaluation", "Session workspace"], horizontal=True, key="workspace_tool", persist_state="session")
    if choice == "Batch and comparison":
        render_batch()
    elif choice == "Ground-truth evaluation":
        render_evaluation()
    else:
        render_session()
