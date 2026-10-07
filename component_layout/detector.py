"""Detector presentation and per-session result lifecycle."""
import hashlib
import io
import json
from time import perf_counter
from datetime import datetime, timezone
import streamlit as st
from content import ROOT, atlas_entries, atlas_for_model_label
from component_ai.images import discover_samples, decode_image, crop_image
from component_ai.models import classify
from component_ai.registry import MODEL_DIR, model_inventory, model_contract, file_version
from component_ai.detection import AUTO_MODELS, auto_detector_contract, model_display_name, model_scope
from component_ai.settings import DEFAULT_CONFIDENCE
from component_layout.results import detection_rows, detections_csv, render_crop_gallery
from component_layout.viewer import render_image_viewer, selection_from_event

def fingerprint(image_hash, config):
    return hashlib.sha256(json.dumps({"image": image_hash, "config": config}, sort_keys=True).encode()).hexdigest()


def request_analysis_review(analysis_id):
    # Consumed before the page's navigation widgets are created on the next rerun.
    st.session_state["requested_review_analysis"] = analysis_id


def render_retained_status():
    from workspace import get_workspace, find_record
    identity = (st.session_state.get("detector_result") or {}).get("analysis_id")
    record = find_record(get_workspace(st.session_state), identity)
    st.caption("Saved in this session only. Export your session to keep analyses and review work after closing it.")
    if record:
        for warning in record.get("warnings", []):
            st.warning(warning)
        if record["image"]["sha256"] not in get_workspace(st.session_state)["images"]:
            st.warning("The source image is not retained. Open this analysis to restore the original image before editing regions.")
        st.button("Review this analysis", key="review_current_analysis", icon=":material/fact_check:",
                  on_click=request_analysis_review, args=(identity,))
    else:
        st.warning("This analysis is no longer in session history. Download its report or run it again to retain a reviewable copy.")


def render_atlas_links(labels):
    """Configured label matches; broad egg groups never imply a species diagnosis."""
    entries = atlas_entries()
    matched = {}
    for label in labels:
        if entry := atlas_for_model_label(label, entries):
            matched[entry["id"]] = entry
    if matched:
        with st.expander("Atlas references for these findings"):
            for entry in matched.values():
                st.caption(entry["differential_diagnosis"][0])
                if st.button("Study " + entry["name"], key="detector_atlas_" + entry["id"]):
                    st.session_state["requested_atlas_species"] = entry["id"]
                    st.switch_page("pages/atlas.py")

def render_detector():
    st.caption("Research use · Scores are uncalibrated model outputs. All findings require qualified review.")
    mode = st.segmented_control("Detection mode", ["Manual classifier", "Auto detection"], default="Manual classifier", key="detector_mode", persist_state="session",
                                format_func=lambda value: {"Manual classifier": "Classify selected region", "Auto detection": "Find objects in whole image"}[value])
    source = st.segmented_control("Image source", ["Sample collection", "Upload image"], default="Sample collection", key="detector_source", persist_state="session")
    if mode is None or source is None:
        st.info("Choose a detection mode and image source to continue.")
        return
    st.caption("01 / Choose an image   →   02 / Analyze   →   03 / Review and export")
    data = None
    label = ""
    if source == "Upload image":
        upload = st.file_uploader("Choose a microscopy image", type=["png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"], key="detector_upload", max_upload_size=25)
        if upload is not None:
            data, label = upload.getvalue(), upload.name
    else:
        samples = discover_samples(ROOT / "component_aiimage")
        if samples:
            chosen = st.selectbox("Microscopy sample", samples, format_func=lambda p: p.name, key="detector_sample", persist_state="session")
            try:
                data, label = chosen.read_bytes(), chosen.name
            except OSError:
                st.error("This sample is unavailable. Choose another image.")
        else:
            st.info("No bundled samples found. Choose Upload image to continue.")
    if data is None:
        st.info("Choose an image to start. PNG, JPEG, TIFF, BMP and WebP are supported, up to 25 MB and 24 megapixels.")
        return
    try:
        image = decode_image(data)
    except ValueError as exc:
        st.error(str(exc))
        return
    image_hash = hashlib.sha256(data).hexdigest()
    st.session_state["analysis_source"] = {"data": data, "sha256": image_hash,
                                           "width": image.width, "height": image.height}
    st.caption(f"{label} · {image.width:,} × {image.height:,} pixels")
    # Detection mode branch: Manual classifier runs only the existing Keras ROI workflow.
    if mode == "Manual classifier":
        render_keras(image, label, image_hash)
    else:
        # Detection mode branch: Auto detection runs only the selected object detector.
        render_objects(image, label, image_hash)

def save_result(result, config, image_hash, label):
    st.session_state.detector_result = {
        "fingerprint": fingerprint(image_hash, config),
        "report": {"schema_version": "2027.1", "created_at": datetime.now(timezone.utc).isoformat(), "image_name": label, "image_sha256": image_hash, "configuration": config, "intended_use": "Research only; uncalibrated model scores require qualified review.", **result},
    }
    # Store only bounded session summaries for Home charts, never image bytes.
    from component_layout.dashboard import record_activity
    record_activity(st.session_state, st.session_state.detector_result["report"])
    from workspace import get_workspace, retain_image, analysis_record, add_record
    source = st.session_state.get("analysis_source")
    if source and source["sha256"] == image_hash:
        ws = get_workspace(st.session_state)
        warnings = []
        try:
            retain_image(ws, source["data"], image_hash)
        except ValueError as exc:
            warnings.append(str(exc))
        record = add_record(ws, analysis_record(st.session_state.detector_result["report"],
                             source["width"], source["height"], result.get("elapsed_seconds", 0), warnings=warnings))
        st.session_state.detector_result["analysis_id"] = record["analysis_id"]

def current_result(config, image_hash):
    result = st.session_state.get("detector_result")
    if result is None:
        return None
    if result["fingerprint"] != fingerprint(image_hash, config):
        st.info("Image or analysis settings changed. Run analysis to generate matching results.")
        return None
    return result["report"]

def render_keras(image, label, image_hash):
    inventory = model_inventory()
    paths = [item["path"] for item in inventory if item["error"] is None]
    with st.expander(f"Model availability: {len(paths)} ready / {len(inventory)} discovered"):
        st.caption(f"Resolved model folder: {MODEL_DIR}")
        st.caption("Each model requires a same-stem .json contract: schema_version 1, ordered labels, preprocessing, and output format.")
        for item in inventory:
            if item["error"]:
                st.error(f"{item['path'].name}: {item['error']}")
        if inventory:
            st.dataframe([{"Model": item["path"].name, "Contract": "Ready" if item["error"] is None else "Invalid", "Preprocessing": (item["contract"] or {}).get("preprocessing", "—")} for item in inventory], hide_index=True)
    chosen = st.multiselect("Classification models", paths, default=paths[:1], format_func=lambda p: p.stem.replace("img_classified_", ""), key="detector_models", persist_state="session")
    if not paths:
        st.error(f"No usable Keras models in {MODEL_DIR}." if inventory else f"No .keras files found in {MODEL_DIR}.")
        st.info("Check Model availability above. Launch this project's app.py and restart an older server if it still displays the former component_ai/ path.")
        return
    st.caption("Drag to pan and zoom to place one target in the center box, then click Analyze selected region in the image. Only the selected Keras classifiers analyze this region.")
    st.caption("Classifier scope: artifact, O. viverrini egg, and minute intestinal fluke egg. Atlas coverage does not expand the trained model's classes.")
    session = st.session_state
    if session.get("viewer_image_id") != image_hash:
        session["viewer_image_id"] = image_hash
        session["viewer_state"] = {"zoom": 1.0, "panX": 0.0, "panY": 0.0, "viewport": 0}
        session["viewer_box"] = None
        session["viewer_token"] = ""
    event = render_image_viewer(image, image_hash, session["viewer_state"])
    calculate = False
    if event is not None:
        try:
            box, state, token = selection_from_event(image, event, image_hash)
        except (ValueError, TypeError, KeyError) as exc:
            st.error(f"Cannot analyze this selection: {exc}")
            return
        if token != session["viewer_token"]:
            session["viewer_box"] = box
            session["viewer_state"] = state
            session["viewer_token"] = token
            calculate = True
    if session["viewer_box"] is None:
        st.info("Position the target and click Analyze selected region to classify the center box.")
        return
    box = session["viewer_box"]
    try:
        crop = crop_image(image, box)
        contracts = [{"file": p.name, "version": file_version(p), "contract": model_contract(p)} for p in chosen]
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        return
    config = {"mode": "keras", "roi_xyxy": list(box), "models": contracts}
    if calculate:
        if not chosen:
            st.warning("Select at least one classification model, then click Analyze selected region again.")
        else:
            with st.spinner("Loading selected models and analyzing the center box..."):
                started = perf_counter()
                result = classify(crop, chosen)
                result["elapsed_seconds"] = perf_counter()-started
            result["viewer"] = {**session["viewer_state"], "calc_token": session["viewer_token"]}
            save_result(result, config, image_hash, label)
    report = current_result(config, image_hash)
    if report:
        st.caption("Results from the last Analyze selected region action. Move or zoom the image, then analyze again to update these results.")
        render_classification(report, crop)

def render_classification(report, crop):
    st.subheader("Analysis results")
    render_retained_status()
    for error in report["errors"]:
        st.error(f"{error['model']}: {error['error']}")
    left, right = st.columns([1, 2])
    with left:
        st.image(crop, caption="Analyzed region", width="stretch")
    with right:
        ensemble = report["ensemble"]
        if ensemble:
            st.markdown(f"**Highest ensemble score: {ensemble['label']}**")
            st.caption("Relative scores normalized per model, then averaged. These are not calibrated clinical probabilities.")
            st.dataframe([{"Class": label, "Mean relative score": round(score, 4), "Votes": ensemble["vote_counts"][label]} for label, score in zip(ensemble["labels"], ensemble["scores"])], hide_index=True, width="stretch")
            st.subheader("Majority vote: " + " / ".join(ensemble["majority"]) + (" (tie)" if len(ensemble["majority"]) > 1 else ""))
        if not report["predictions"]:
            st.warning("No selected model produced a valid prediction.")
        for result in report["predictions"]:
            with st.expander(result["model"]):
                st.write(f"Top class: {result['prediction']['label']}")
                st.dataframe([{"Class": label, "Raw score": score} for label, score in zip(result["prediction"]["labels"], result["prediction"]["raw_scores"])], hide_index=True)
    render_atlas_links([p["prediction"]["label"] for p in report["predictions"]]
                       + ([report["ensemble"]["label"]] if report["ensemble"] else []))
    download_report(report)

def download_report(report):
    st.download_button("Download analysis report", json.dumps(report, indent=2, allow_nan=False), file_name="parasite_analysis.json", mime="application/json", icon=":material/download:")

def render_objects(image, label, image_hash):
    from component_ai.yolo import load_yolo_model, run_yolo_inference
    from component_ai.rcnn import load_rcnn_model, run_rcnn_inference

    selected_model = st.segmented_control(
        "Detection model", AUTO_MODELS, default="yolo26n", required=True,
        format_func=model_display_name,
        key="auto_detector_model", persist_state="session",
        help="Choose one model to analyze the full image.")
    display_name = model_display_name(selected_model)
    st.caption("Choose a model → Detect objects → Inspect regions and export")
    st.caption(model_scope(selected_model) + " Product names identify model options; they do not rank accuracy.")
    try:
        family, manifest, weights = auto_detector_contract(selected_model)
        version = file_version(weights) if weights.is_file() else None
    except (ValueError, KeyError, OSError) as exc:
        st.error(f"Invalid detector configuration: {exc}")
        return
    ready = version is not None
    with st.expander("Model setup", expanded=not ready):
        if ready:
            st.caption(f"{display_name}: checkpoint available at component_ai/{family}/{manifest['weights']}")
        else:
            st.info(f"{display_name}: weights required at component_ai/{family}/{manifest['weights']}.")
        st.code(f"pip install -r requirements-{family}.txt", language="shell")
    if family == "yolo":
        st.caption("Class names come from the selected checkpoint. Known placeholder labels are expanded to the configured parasite names; class IDs and scores stay unchanged.")
    threshold = st.slider("Detection confidence threshold", 0.05, 0.95, DEFAULT_CONFIDENCE, 0.05,
                          key=f"auto_threshold_{selected_model}", persist_state="session")
    # Model identity and file version invalidate results when switching checkpoints.
    config = {"mode": "auto", "selected_model": selected_model, "family": family,
              "manifest": manifest, "version": version, "confidence": threshold, "iou": 0.45,
              "label_schema_version": 2}
    if st.button("Detect objects", type="primary", disabled=not ready, icon=":material/play_arrow:"):
        st.session_state.detector_result = None
        st.session_state.pop("detector_annotated", None)
        try:
            with st.spinner(f"Analyzing the image with {display_name}..."):
                started = perf_counter()
                # Auto detection model branch: the selected YOLO variant runs alone.
                if family == "yolo":
                    model, lock, digest = load_yolo_model(str(weights), version)
                    loaded = perf_counter()
                    with lock:
                        infer_started = perf_counter()
                        result = run_yolo_inference(model, image, threshold,
                                                    image_size=manifest["image_size"], iou_threshold=0.45)
                # Auto detection model branch: Faster R-CNN runs alone on the full image.
                else:
                    model, lock, digest = load_rcnn_model(str(weights), version, json.dumps(manifest, sort_keys=True))
                    loaded = perf_counter()
                    with lock:
                        infer_started = perf_counter()
                        result = run_rcnn_inference(model, image, manifest["labels"], threshold, iou_threshold=0.45)
                annotated = result.pop("annotated_image")
                result["model_sha256"] = {selected_model: digest}
                result["elapsed_seconds"] = perf_counter()-started
                result["timing"] = {"load_or_cache_seconds": loaded-started,
                                    "lock_wait_seconds": infer_started-loaded,
                                    "inference_and_annotation_seconds": perf_counter()-infer_started}
                save_result(result, config, image_hash, label)
                st.session_state["detector_annotated"] = annotated
        except Exception as exc:
            st.session_state.detector_result = None
            from workspace import get_workspace, add_record, analysis_record
            add_record(get_workspace(st.session_state), analysis_record(
                {"image_sha256": image_hash, "image_name": label, "configuration": config,
                 "errors": [{"model": selected_model, "error": str(exc)}]},
                image.width, image.height, perf_counter()-started, status="failed"))
            st.error(f"Auto detection could not complete: {exc}")
    report = current_result(config, image_hash)
    if not report:
        st.image(image, caption="Image to analyze", width="stretch")
        return
    st.subheader(f"Results · {display_name}")
    render_retained_status()
    if report.get("class_names"):
        st.caption("Model classes: " + " · ".join(report["class_names"]))
    st.metric("Objects detected", len(report["detections"]))
    st.image(st.session_state["detector_annotated"], caption=f"{display_name} findings in original image coordinates", width="stretch")
    if report["detections"]:
        render_crop_gallery(image, report["detections"])
        render_atlas_links([d["class_name"] for d in report["detections"]])
        with st.expander("Detection measurements and class IDs"):
            st.dataframe(detection_rows(report["detections"]), hide_index=True, width="stretch")
    else:
        st.info("No objects met the threshold. This does not exclude parasites in the specimen.")
    buffer = io.BytesIO()
    st.session_state["detector_annotated"].save(buffer, format="PNG")
    st.download_button("Download annotated image", buffer.getvalue(), file_name="parasite_detections.png", mime="image/png")
    with st.expander("Review notes and exports"):
        # Scope notes to this exact analysis, including its creation time.
        review_key = fingerprint(report["created_at"], config)
        notes = st.text_area("Morphology observations / review notes", max_chars=4000,
                             key=f"review_{review_key}", persist_state="session",
                             help="Record image quality, visible features and discrepancies. Notes do not change model predictions.")
        reviewed_report = {**report, "review": {"notes": notes, "status": "Unverified model findings"}}
        from workspace import get_workspace, find_record
        retained = find_record(get_workspace(st.session_state), st.session_state.detector_result.get("analysis_id"))
        if retained:
            retained["notes"] = notes
        st.download_button("Download detection table (CSV)", detections_csv(report),
                           file_name="parasite_detections.csv", mime="text/csv")
        download_report(reviewed_report)
