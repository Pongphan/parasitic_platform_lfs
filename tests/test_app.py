from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from streamlit.runtime.pages_manager import PagesManager

APP = Path(__file__).resolve().parents[1] / "app.py"

@pytest.fixture(autouse=True)
def explicit_navigation_test_runtime(monkeypatch):
    """Match the live runtime after st.navigation disables legacy discovery.

    Streamlit 1.60 AppTest resets this process-level flag to None for every
    run(), unlike a live server. With scripts in pages/, that selects the page
    as a legacy entrypoint and bypasses app.py. Keep the explicit routing mode
    across test reruns; do not alter application routing or widget behavior.
    """
    original_init = PagesManager.__init__
    def initialize(manager, *args, **kwargs):
        PagesManager.uses_pages_directory = False
        original_init(manager, *args, **kwargs)
    monkeypatch.setattr(PagesManager, "__init__", initialize)

def app():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception
    return at

def test_all_navigation_cards_and_pages():
    at = app()
    for index in [1,2,3,4,0]:
        at.button(key=f"nav_{index}").click().run()
        assert not at.exception
        assert len([b for b in at.button if b.key and b.key.startswith("nav_")]) == 5
        assert len(at.sidebar) == 0

def test_home_charts_and_real_session_activity():
    at = app()
    assert {"Practice coverage", "Classifier collection", "This session in the laboratory"}.issubset({item.value for item in at.subheader})
    assert any("populate the activity charts" in item.value for item in at.info)
    at.session_state["analysis_activity"] = [{"Time":"2026-09-07T10:00:00+00:00", "Family":"keras", "Status":"Completed", "Objects":0}, {"Time":"2026-09-07T10:01:00+00:00", "Family":"yolo", "Status":"Completed", "Objects":2}]
    at.run()
    assert not at.exception
    assert next(m for m in at.metric if m.label == "Analysis runs").value == "2"
    assert next(m for m in at.metric if m.label.startswith("Objects detected")).value == "2"

@pytest.mark.parametrize("page", ["home", "atlas", "detector", "examination", "about"])
def test_pages_directory_routes_keep_shell_on_rerun(page):
    assert (APP.parent / "pages" / f"{page}.py").is_file()
    assert not (APP.parent / "app_pages").exists()
    at = app().switch_page(f"pages/{page}.py").run()
    at.run()
    assert not at.exception
    assert len([b for b in at.button if b.key and b.key.startswith("nav_")]) == 5
    assert len(at.sidebar) == 0

def test_atlas_search_and_quiz_link():
    at = app()
    at.button(key="nav_1").click().run()
    # AppTest does not retain st.switch_page's client route across run() calls.
    at.switch_page("pages/atlas.py")
    at.text_input(key="atlas_search").set_value("no such species").run()
    assert "No species" in at.info[0].value
    at.text_input(key="atlas_search").set_value("Giardia").run()
    assert at.selectbox(key="atlas_species").value == "giardia_duodenalis"
    next(b for b in at.button if b.label == "Practice this species").click().run()
    assert at.selectbox(key="exam_species").value == "giardia_duodenalis"

def test_quiz_submit_review_navigation_and_retry():
    from content import quiz_questions
    at = app()
    at.button(key="nav_3").click().run()
    at.switch_page("pages/examination.py")
    next(b for b in at.button if b.label == "Submit answers").click().run()
    assert at.warning
    questions = quiz_questions(at.selectbox(key="exam_species").value)
    for widget, q in zip(at.radio, questions):
        widget.set_value(q["correct_answer"])
    next(b for b in at.button if b.label == "Submit answers").click().run()
    assert not at.exception
    assert at.metric[0].value == "3 / 3"
    at.button(key="nav_0").click().run()
    at.button(key="nav_3").click().run()
    assert at.metric[0].value == "3 / 3"
    next(b for b in at.button if b.label == "Try again").click().run()
    assert all(widget.value is None for widget in at.radio)

def test_detector_empty_upload_and_model_availability(monkeypatch, tmp_path):
    import component_layout.detector as detector
    original_contract = detector.auto_detector_contract
    def controlled_contract(name):
        family, manifest, weights = original_contract(name)
        return family, manifest, tmp_path / "parasite_fasterrcnn.pth" if family == "rcnn" else weights
    monkeypatch.setattr(detector, "auto_detector_contract", controlled_contract)
    at = app()
    at.button(key="nav_2").click().run()
    at.switch_page("pages/detector.py")
    assert not at.exception
    at.segmented_control(key="detector_source").set_value("Upload image").run()
    assert any("Choose an image" in x.value for x in at.info)
    at.segmented_control(key="detector_source").set_value("Sample collection").run()
    assert not at.slider
    assert at.segmented_control(key="detector_mode").options == ["Classify selected region", "Find objects in whole image"]
    at.segmented_control(key="detector_mode").set_value("Auto detection").run()
    assert not at.exception
    assert at.segmented_control(key="auto_detector_model").options == ["meinmodel lite (yolo26n)", "meinmodel medium (yolo26x)", "meinmodel expert (Faster R-CNN)"]
    assert not next(b for b in at.button if b.label == "Detect objects").disabled
    at.segmented_control(key="auto_detector_model").set_value("yolo26x").run()
    assert not next(b for b in at.button if b.label == "Detect objects").disabled
    at.segmented_control(key="auto_detector_model").set_value("Faster R-CNN").run()
    assert not at.exception
    assert next(b for b in at.button if b.label == "Detect objects").disabled
    assert any("rcnn/weights/parasite_fasterrcnn.pth" in item.value for item in at.info)

def test_detector_report_and_stale_crop_suppression(monkeypatch):
    import component_layout.detector as detector
    from component_ai.models import postprocess_prediction, build_ensemble_summary
    import numpy as np

    def fake_classify(image, paths):
        assert image.width > 0 and image.height > 0
        result = {"model": paths[0].name, "prediction": postprocess_prediction(np.array([[0.2,0.7,0.1]]), ["artifact","OV egg","MIF egg"])}
        return {"predictions":[result], "errors":[], "ensemble":build_ensemble_summary([result])}

    calls = []
    def counted_classify(image, paths):
        calls.append(image.size)
        return fake_classify(image, paths)
    event = {"action":"calculate", "calc_token":"first", "zoom":1.0, "panX":0, "panY":0, "viewport":600}
    def fake_viewer(image, image_id, state):
        return {**event,"image_id":image_id}
    monkeypatch.setattr(detector, "classify", counted_classify)
    monkeypatch.setattr(detector, "render_image_viewer", fake_viewer)
    at = app().switch_page("pages/detector.py").run()
    assert not at.exception
    assert any("Highest ensemble score" in item.value for item in at.markdown)
    report = at.session_state["detector_result"]["report"]
    assert report["configuration"]["mode"] == "keras"
    assert report["image_sha256"]
    assert at.get("download_button")
    assert any(item.value.startswith("Majority vote:") for item in at.subheader)
    assert any(item.value == "Analysis results" for item in at.subheader)
    assert len(calls) == 1
    at.run()
    assert len(calls) == 1  # A repeated component event must not run inference twice.
    event.update(calc_token="second", zoom=2.0)
    at.run()
    assert len(calls) == 2 and calls[1][0] < calls[0][0]
    at.multiselect(key="detector_models").set_value([]).run()
    assert not at.exception
    assert any("settings changed" in item.value for item in at.info)
    assert not any("Highest ensemble score" in item.value for item in at.markdown)


@pytest.mark.parametrize("choice", ["yolo26n", "yolo26x", "Faster R-CNN"])
def test_auto_page_export_stale_settings_and_failure(monkeypatch, tmp_path, choice):
    import threading
    from PIL import Image
    import component_layout.detector as detector
    import component_ai.yolo as yolo
    import component_ai.rcnn as rcnn
    weights = tmp_path / f"{choice}.pt"
    weights.write_bytes(b"test checkpoint")
    family = "rcnn" if choice == "Faster R-CNN" else "yolo"
    monkeypatch.setattr(detector, "auto_detector_contract", lambda selected: (family, {"image_size": 640, "labels": ["__background__", "egg"], "weights": weights.name}, weights))
    monkeypatch.setattr(yolo, "load_yolo_model", lambda *args: (object(), threading.RLock(), "yolo_digest"))
    monkeypatch.setattr(rcnn, "load_rcnn_model", lambda *args: (object(), threading.RLock(), "rcnn_digest"))
    calls = []
    def prediction(backend, image):
        calls.append(backend)
        return {"detections": [{"class_id": 1, "class_name": "egg", "confidence": 0.8, "bbox_xyxy": [0, 0, 20, 20]}],
                "annotated_image": Image.new("RGB", image.size)}
    monkeypatch.setattr(yolo, "run_yolo_inference", lambda model, image, *args, **kwargs: prediction("yolo", image))
    monkeypatch.setattr(rcnn, "run_rcnn_inference", lambda model, image, *args, **kwargs: prediction("rcnn", image))
    at = app().switch_page("pages/detector.py").run()
    at.segmented_control(key="detector_mode").set_value("Auto detection").run()
    at.segmented_control(key="auto_detector_model").set_value(choice).run()
    assert at.slider(key=f"auto_threshold_{choice}").value == 0.7
    next(b for b in at.button if b.label == "Detect objects").click().run()
    assert not at.exception
    assert calls == [family]  # No unselected backend is executed.
    assert len(at.get("download_button")) == 3
    assert any(item.value == "Detected crops (1)" for item in at.subheader)
    assert not any(item.label == "Inspect a detected region" for item in at.selectbox)
    at.text_area[0].set_value("Review shell detail before accepting the model finding.").run()
    assert calls == [family]
    report = at.session_state["detector_result"]["report"]
    assert report["configuration"]["selected_model"] == choice
    assert report["model_sha256"] == {choice: f"{family}_digest"}
    at.run()
    assert calls == [family]
    alternate = "yolo26x" if choice != "yolo26x" else "yolo26n"
    at.segmented_control(key="auto_detector_model").set_value(alternate).run()
    assert not at.get("download_button")
    at.segmented_control(key="auto_detector_model").set_value(choice).run()
    at.slider(key=f"auto_threshold_{choice}").set_value(0.5).run()
    assert not at.get("download_button")
    def broken(*args, **kwargs):
        raise RuntimeError("test model failure")
    monkeypatch.setattr(yolo if family == "yolo" else rcnn, f"run_{family}_inference", broken)
    next(b for b in at.button if b.label == "Detect objects").click().run()
    assert not at.exception
    assert at.session_state["detector_result"] is None
    assert not at.get("download_button")
    assert any("test model failure" in item.value for item in at.error)


def test_atlas_comparison_and_return_from_examination():
    at = app().switch_page("pages/atlas.py").run()
    at.multiselect(key="atlas_compare").set_value(["giardia_duodenalis", "ascaris_lumbricoides"]).run()
    assert not at.exception
    assert len(at.dataframe[0].value) == 2
    at.switch_page("pages/examination.py").run()
    at.selectbox(key="exam_species").set_value("giardia_duodenalis").run()
    next(b for b in at.button if b.label == "Review this species in the Atlas").click().run()
    assert not at.exception
    assert at.selectbox(key="atlas_species").value == "giardia_duodenalis"


def test_every_atlas_card_renders_and_new_quiz_is_available():
    from content import atlas_entries
    at = app().switch_page("pages/atlas.py").run()
    for entry in atlas_entries():
        at.selectbox(key="atlas_species").set_value(entry["id"]).run()
        assert not at.exception, entry["id"]
        assert any(item.value == entry["name"] for item in at.subheader)
    at.selectbox(key="atlas_species").set_value("plasmodium_knowlesi").run()
    at.button(key="atlas_practice_action").click().run()
    assert at.selectbox(key="exam_species").value == "plasmodium_knowlesi"
    assert at.radio and not at.exception


def test_atlas_filters_pagination_and_related_group_navigation():
    at = app().switch_page("pages/atlas.py").run()
    at.number_input(key="atlas_index_page").set_value(7).run()
    at.text_input(key="atlas_search").set_value("Haplorchis taichui").run()
    assert not at.exception
    assert at.number_input(key="atlas_index_page").value == 1
    at.selectbox(key="atlas_species").set_value("haplorchis_taichui").run()
    at.button(key="atlas_related").click().run()
    assert not at.exception
    assert at.selectbox(key="atlas_species").value == "minute_intestinal_flukes"
    assert at.text_input(key="atlas_search").value == ""
    at.selectbox(key="atlas_group").set_value("Blood parasites").run()
    at.selectbox(key="atlas_route").set_value("Vector-borne").run()
    at.selectbox(key="atlas_clinical").set_value("Anemia").run()
    assert not at.exception and len(at.selectbox(key="atlas_species").options) == 6
    # A finding/examination handoff must bypass all previously selected filters.
    at.session_state["requested_atlas_species"] = "opisthorchis_viverrini"
    at.run()
    assert at.selectbox(key="atlas_species").value == "opisthorchis_viverrini"
    assert at.selectbox(key="atlas_route").value == "All routes"
    assert at.selectbox(key="atlas_clinical").value == "All clinical contexts"
