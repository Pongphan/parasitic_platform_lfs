"""User-flow regressions for review handoff and current-versus-stale results."""
from copy import deepcopy
import io
import threading

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from test_app import app, explicit_navigation_test_runtime
from test_workspace import png, record, detection, coco
from workspace import new_workspace, retain_image, add_record, update_review, json_bytes


def button(at, label):
    return next(item for item in at.button if item.label == label)


def download(at, label):
    return next(item for item in at.get("download_button") if item.proto.label == label)


def review_app():
    import streamlit as st
    from component_layout.workbench import render_review, retained_image
    ws = st.session_state["workspace"]
    current = ws["records"][0]
    render_review(ws, current, retained_image(ws, current), "review_test")


def evaluation_app():
    from component_layout.workbench import render_evaluation
    render_evaluation()


def batch_app():
    from component_layout.workbench import render_batch
    render_batch()


def saved_workspace():
    ws = new_workspace()
    retain_image(ws, png())
    add_record(ws, record())
    return ws


def test_review_current_analysis_opens_exact_record_and_advances(monkeypatch, tmp_path):
    import component_layout.detector as detector
    import component_ai.yolo as yolo
    checkpoint = tmp_path / "fake.pt"
    checkpoint.write_bytes(b"fixture")
    monkeypatch.setattr(detector, "auto_detector_contract", lambda name: (
        "yolo", {"image_size": 640, "weights": checkpoint.name}, checkpoint))
    monkeypatch.setattr(yolo, "load_yolo_model", lambda *args: (object(), threading.RLock(), "a" * 64))
    monkeypatch.setattr(yolo, "run_yolo_inference", lambda model, image, *args, **kwargs: {
        "detections": [detection(), detection(box=[14, 3, 24, 13]), detection(box=[26, 3, 36, 13])],
        "annotated_image": image.copy()})
    at = app().switch_page("pages/detector.py").run()
    at.segmented_control(key="detector_mode").set_value("Auto detection").run()
    button(at, "Detect objects").click().run()
    ws = at.session_state["workspace"]
    target = ws["records"][-1]
    original = deepcopy(target["original"])
    update_review(target, "0", "accepted", "egg", [2, 3, 12, 13])
    add_record(ws, record(name="newer-unrelated.png"))
    at.button(key="review_current_analysis").click().run()
    assert not at.exception
    assert at.radio(key="detector_workspace").value == "Advanced workspace"
    assert at.radio(key="workspace_tool").value == "Session workspace"
    assert at.selectbox(key="history_record").value == target["analysis_id"]
    review = next(item for item in at.expander if item.label == "Review objects and edit source-pixel boxes")
    assert review.proto.expanded
    region = next(item for item in at.selectbox if item.label == "Object to review")
    assert region.value == "1"
    assert region.options[1].startswith("Region 02 · egg")
    next(item for item in at.selectbox if item.label == "Review status").set_value("accepted")
    button(at, "Save and next").click().run()
    assert not at.exception
    assert next(item for item in at.selectbox if item.label == "Object to review").value == "2"
    saved = next(item for item in at.session_state["workspace"]["records"] if item["analysis_id"] == target["analysis_id"])
    assert saved["review"]["1"]["status"] == "accepted"
    assert saved["original"] == original
    review_key = "history_" + target["analysis_id"]
    at.multiselect(key=review_key+"_states").set_value(["accepted"]).run()
    at.multiselect(key=review_key+"_labels").set_value([]).run()
    at.radio(key="detector_workspace").set_value("Single image").run()
    at.button(key="review_current_analysis").click().run()
    assert not at.exception
    assert at.selectbox(key="history_record").value == target["analysis_id"]
    assert at.selectbox(key=review_key+"_object").value == "2"
    assert at.multiselect(key=review_key+"_states").value == ["unreviewed", "accepted", "corrected", "rejected"]
    assert at.multiselect(key=review_key+"_labels").value == ["egg"]


def test_annotation_export_disabled_after_mapping_or_review_change():
    ws = saved_workspace()
    update_review(ws["records"][0], "0", "accepted", "egg", [2, 3, 12, 13])
    at = AppTest.from_function(review_app, default_timeout=30)
    at.session_state["workspace"] = ws
    at.run()
    at.text_area(key="review_test_mapping").set_value("egg").run()
    at.button(key="review_test_build").click().run()
    assert not at.exception
    assert not download(at, "Download prepared annotation ZIP").proto.disabled
    at.text_area(key="review_test_mapping").set_value("egg\nartifact").run()
    assert download(at, "Download prepared annotation ZIP").proto.disabled
    at.button(key="review_test_build").click().run()
    assert not download(at, "Download prepared annotation ZIP").proto.disabled
    next(item for item in at.text_area if item.label == "Reviewer notes").set_value("Rechecked shell detail")
    button(at, "Save annotation").click().run()
    assert not at.exception
    assert download(at, "Download prepared annotation ZIP").proto.disabled
    assert download(at, "Download prepared COCO JSON").proto.disabled


def test_saved_missed_object_reveals_its_filters_and_remains_selected():
    ws = saved_workspace()
    update_review(ws["records"][0], "0", "accepted", "egg", [2, 3, 12, 13])
    at = AppTest.from_function(review_app, default_timeout=30)
    at.session_state["workspace"] = ws
    at.run()
    at.multiselect(key="review_test_states").set_value(["accepted"]).run()
    at.multiselect(key="review_test_labels").set_value(["egg"]).run()
    at.selectbox(key="review_test_object").set_value("Add missed object").run()
    next(item for item in at.text_input if item.label == "Reviewer class label").set_value("missed egg")
    button(at, "Save annotation").click().run()
    assert not at.exception
    selected = at.selectbox(key="review_test_object")
    assert selected.value.startswith("manual_")
    assert "Region 02 · missed egg · corrected" in selected.options
    assert at.multiselect(key="review_test_states").value == ["accepted", "corrected"]
    assert at.multiselect(key="review_test_labels").value == ["egg", "Manually added"]
    assert next(item for item in at.text_input if item.label == "Reviewer class label").value == "missed egg"
    table = at.dataframe[0].value
    assert "Region 02" in table["Region"].tolist()
    button(at, "Undo last annotation change").click().run()
    assert not at.exception
    assert at.multiselect(key="review_test_labels").value == ["egg"]
    assert at.selectbox(key="review_test_object").value == "0"
    restored = at.session_state["workspace"]["records"][0]
    assert set(restored["review"]) == {"0"}
    assert restored["review"]["0"]["status"] == "accepted"


def test_review_recovers_from_empty_filters_but_preserves_explicit_add():
    at = AppTest.from_function(review_app, default_timeout=30)
    at.session_state["workspace"] = saved_workspace()
    at.run()
    assert at.selectbox(key="review_test_object").value == "0"
    at.multiselect(key="review_test_states").set_value([]).run()
    assert at.selectbox(key="review_test_object").value == "Add missed object"
    assert any("No regions match" in item.value for item in at.info)
    at.multiselect(key="review_test_states").set_value(["unreviewed"]).run()
    assert not at.exception
    assert at.selectbox(key="review_test_object").value == "0"
    at.selectbox(key="review_test_object").set_value("Add missed object").run()
    at.multiselect(key="review_test_states").set_value([]).run()
    at.multiselect(key="review_test_states").set_value(["unreviewed"]).run()
    assert not at.exception
    assert at.selectbox(key="review_test_object").value == "Add missed object"


@pytest.mark.parametrize("changed", ["analyses", "confidence", "iou", "mapping", "origin", "dataset"])
def test_evaluation_hides_metrics_and_disables_download_after_input_change(monkeypatch, changed):
    uploaded = {"data": coco()}
    original_uploader = st.file_uploader
    monkeypatch.setattr(st, "file_uploader", lambda label, *args, **kwargs:
                        io.BytesIO(json_bytes(uploaded["data"])) if label == "COCO bounding-box JSON"
                        else original_uploader(label, *args, **kwargs))
    ws = saved_workspace()
    at = AppTest.from_function(evaluation_app, default_timeout=30)
    at.session_state["workspace"] = ws
    at.run()
    at.multiselect[0].set_value([ws["records"][0]["analysis_id"]]).run()
    at.text_input(key="eval_map_1").set_value("egg").run()
    button(at, "Evaluate selected analyses").click().run()
    assert not at.exception
    assert at.success and not download(at, "Download evaluation report").proto.disabled
    if changed == "analyses":
        at.multiselect[0].set_value([])
    elif changed == "confidence":
        next(item for item in at.slider if item.label == "Evaluation confidence threshold").set_value(.8)
    elif changed == "iou":
        next(item for item in at.slider if item.label == "Evaluation IoU threshold").set_value(.75)
    elif changed == "mapping":
        at.text_input(key="eval_map_1").set_value("artifact")
    elif changed == "origin":
        next(item for item in at.selectbox if item.label == "Reference annotation origin").set_value("Unknown")
    else:
        uploaded["data"]["annotations"] = []
    at.run()
    assert not at.exception
    assert any("inputs changed" in item.value for item in at.warning)
    assert not at.success and not at.dataframe
    assert download(at, "Download evaluation report").proto.disabled


def test_failed_reevaluation_does_not_display_previous_success(monkeypatch):
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: io.BytesIO(json_bytes(coco())))
    ws = saved_workspace()
    at = AppTest.from_function(evaluation_app, default_timeout=30)
    at.session_state["workspace"] = ws
    at.run()
    at.multiselect[0].set_value([ws["records"][0]["analysis_id"]]).run()
    at.text_input(key="eval_map_1").set_value("egg").run()
    button(at, "Evaluate selected analyses").click().run()
    assert at.success
    next(item for item in at.slider if item.label == "Evaluation confidence threshold").set_value(.1).run()
    button(at, "Evaluate selected analyses").click().run()
    assert not at.exception
    assert any("cannot be lower" in item.value for item in at.error)
    assert not at.success and not at.dataframe and not at.get("download_button")
    assert "evaluation_report" not in at.session_state


def test_batch_starts_refreshes_and_disables_old_exports(monkeypatch, tmp_path):
    import component_layout.workbench as workbench
    from component_ai.jobs import step_job
    source = tmp_path / "sample.png"
    source.write_bytes(png())
    monkeypatch.setattr(workbench, "discover_samples", lambda *args: [source])
    monkeypatch.setattr(workbench, "configuration", lambda model, confidence: {
        "mode": "auto", "selected_model": model, "confidence": confidence})
    calls = []
    def runner(image, config):
        calls.append(config)
        return {"detections": [detection()]}
    monkeypatch.setattr(workbench, "step_job", lambda ws, job: step_job(ws, job, runner))
    at = AppTest.from_function(batch_app, default_timeout=30).run()
    at.multiselect(key="batch_samples").set_value([source]).run()
    at.button(key="prepare_batch").click().run()
    assert not at.exception
    assert len(calls) == 1
    assert any("1 succeeded" in item.value for item in at.caption)
    assert any(item.label == "Inspect batch analysis" for item in at.selectbox)
    button(at, "Prepare batch ZIP").click().run()
    assert not download(at, "Download prepared batch ZIP").proto.disabled
    current = at.session_state["workspace"]["records"][0]
    update_review(current, "0", "accepted", "egg", [2, 3, 12, 13])
    at.run()
    assert download(at, "Download prepared batch ZIP").proto.disabled
    button(at, "Prepare batch ZIP").click().run()
    assert not download(at, "Download prepared batch ZIP").proto.disabled
    at.slider(key="batch_confidence").set_value(.5).run()
    assert not at.exception and len(calls) == 1
    assert button(at, "Prepare batch ZIP").disabled
    assert download(at, "Download prepared batch ZIP").proto.disabled
