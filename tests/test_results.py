import csv
import io
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest
from component_ai.settings import DEFAULT_CONFIDENCE, canonical_label
from component_ai.yolo import run_yolo_inference
from component_ai.annotations import annotate_detections, label_position, intersection
from component_ai.models import postprocess_prediction
from component_layout.results import crop_box, detections_csv


def test_names_default_and_coco_identity():
    assert DEFAULT_CONFIDENCE == 0.7
    assert canonical_label("class_1") == "Opisthorchis viverrini egg"
    assert canonical_label("class_2") == "Minute intestinal fluke egg"
    assert canonical_label("bicycle") == "bicycle"
    result = postprocess_prediction(np.array([[0.8, 0.2]]), ["class_1", "class_2"])
    assert result["label"] == "Opisthorchis viverrini egg"
    class Model:
        def predict(self, **kwargs):
            assert kwargs["conf"] == 0.7
            return [SimpleNamespace(names={0: "class_1", 1: "bicycle", 2: "class_2"},
                boxes=SimpleNamespace(xyxy=np.array([[1, 2, 20, 25]]), conf=np.array([0.8]), cls=np.array([0])), speed={})]
    result = run_yolo_inference(Model(), Image.new("RGB", (100, 100)))
    assert result["class_names"] == ["Opisthorchis viverrini egg", "bicycle", "Minute intestinal fluke egg"]
    assert result["class_counts"] == {"Opisthorchis viverrini egg": 1}


def test_rcnn_default_and_aliases():
    torch = pytest.importorskip("torch")
    from component_ai.rcnn import run_rcnn_inference
    class Model:
        def __call__(self, images):
            return [{"boxes": torch.tensor([[0., 0., 10., 10.], [20., 20., 30., 30.]]),
                     "scores": torch.tensor([0.8, 0.6]), "labels": torch.tensor([1, 2])}]
    result = run_rcnn_inference(Model(), Image.new("RGB", (40, 40)), ["__background__", "class_1", "class_2"])
    assert result["confidence_threshold"] == 0.7
    assert result["class_counts"] == {"Opisthorchis viverrini egg": 1}


def test_overlay_edges_and_label_collision():
    occupied = []
    for _ in range(3):
        rect = label_position((0, 0, 70, 60), (120, 25), (200, 200), occupied)
        assert 0 <= rect[0] < rect[2] <= 200
        assert 0 <= rect[1] < rect[3] <= 200
        assert all(intersection(rect, other) == 0 for other in occupied)
        occupied.append(rect)
    for size in [(1, 1), (32, 32), (400, 300)]:
        image = Image.new("RGB", size, "white")
        annotated = annotate_detections(image, [{"class_id": 1, "class_name": "class_1", "confidence": .9,
                                                 "bbox_xyxy": [0, 0, *size]}])
        assert annotated.size == size
        assert image.getpixel((0, 0)) == (255, 255, 255)


def test_crop_clamping_and_csv_provenance():
    detection = {"class_id": 1, "class_name": "class_1", "confidence": .9, "bbox_xyxy": [-1.2, 0, 15.4, 50]}
    assert crop_box(Image.new("RGB", (30, 30)), detection) == (0, 0, 16, 30)
    with pytest.raises(ValueError):
        crop_box(Image.new("RGB", (30, 30)), {**detection, "bbox_xyxy": [40, 0, 50, 10]})
    report = {"detections": [detection], "configuration": {"selected_model": "yolo26n"}, "image_sha256": "abc"}
    row = next(csv.DictReader(io.StringIO(detections_csv(report).decode("utf-8-sig"))))
    assert row["Class"] == "Opisthorchis viverrini egg"
    assert row["Region"] == "1" and row["Image SHA256"] == "abc"


@pytest.mark.parametrize("count", [1, 2, 7])
def test_gallery_shows_all_regions(count):
    def page(count):
        from PIL import Image
        from component_layout.results import render_crop_gallery
        render_crop_gallery(Image.new("RGB", (100, 100)), [
            {"class_id": 1, "class_name": "class_1", "confidence": .9, "bbox_xyxy": [1, 2, 20, 30]}
            for _ in range(count)])
    at = AppTest.from_function(page, args=(count,)).run()
    assert not at.exception
    assert len([m for m in at.markdown if m.value.startswith("**Region")]) == count
    assert not at.selectbox
