import pytest
from PIL import Image
from component_ai.pipeline import cascade


def detection(box, score=0.8):
    return {"class_id": 1, "class_name": "egg", "confidence": score, "bbox_xyxy": box}


def test_sequence_crops_offsets_and_duplicate_suppression():
    calls = []
    def yolo(image):
        calls.append(("yolo", image.size))
        return {"detections": [detection([20, 20, 40, 40]), detection([20, 20, 40, 40])]}
    def rcnn(image):
        calls.append(("rcnn", image.size))
        return {"detections": [detection([2, 2, 22, 22])]}
    result = cascade(Image.new("RGB", (100, 100)), yolo, rcnn)
    assert calls == [("yolo", (100, 100)), ("rcnn", (24, 24)), ("rcnn", (24, 24))]
    assert len(result["detections"]) == 1
    assert result["detections"][0]["bbox_xyxy"] == [20, 20, 40, 40]
    assert len(result["stages"]["rcnn"]) == 2
    assert result["annotated_image"].size == (100, 100)


def test_no_yolo_proposals_still_runs_rcnn():
    calls = []
    def rcnn(image):
        calls.append(image.size)
        return {"detections": []}
    result = cascade(Image.new("RGB", (90, 70)), lambda image: {"detections": []}, rcnn)
    assert calls == [(90, 70)]
    assert result["full_image_fallback"] and result["detections"] == []


def test_unconfirmed_proposals_are_evidence_only():
    result = cascade(Image.new("RGB", (100, 100)),
                     lambda image: {"detections": [detection([0, 0, 10, 10])]},
                     lambda image: {"detections": []})
    assert result["detections"] == []
    assert len(result["stages"]["yolo"]) == 1


def test_second_stage_failure_is_not_a_completed_result():
    def broken(image):
        raise RuntimeError("checkpoint incompatible")
    with pytest.raises(RuntimeError, match="checkpoint incompatible"):
        cascade(Image.new("RGB", (100, 100)), lambda image: {"detections": []}, broken)


@pytest.mark.parametrize("box", [[float("nan"), 0, 10, 10], [50, 50, 10, 10]])
def test_invalid_proposals_do_not_reach_rcnn(box):
    def unexpected(image):
        pytest.fail("Invalid proposal reached RCNN")
    with pytest.raises(ValueError):
        cascade(Image.new("RGB", (100, 100)), lambda image: {"detections": [detection(box)]}, unexpected)
