import io
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image
from component_ai.images import decode_image, crop_image
from component_ai.models import postprocess_prediction, prepare_input_tensor, build_ensemble_summary
from component_layout.detector import fingerprint
from component_ai.yolo import run_yolo_inference

def test_preprocessing_preserves_legacy_raw_rgb():
    image = Image.new("RGB", (30, 40), (255, 128, 12))
    tensor = prepare_input_tensor(image, SimpleNamespace(input_shape=(None, 16, 12, 3)))
    assert tensor.shape == (1, 16, 12, 3)
    assert tensor.dtype == np.float32
    np.testing.assert_array_equal(tensor[0, 0, 0], [255, 128, 12])
    scaled = prepare_input_tensor(image, SimpleNamespace(input_shape=(None, 8, 8, 1)), True)
    assert scaled.shape == (1, 8, 8, 1)
    assert 0 <= scaled.min() <= scaled.max() <= 1

@pytest.mark.parametrize("shape", [(None, 3, 16, 16), [(None, 16, 16, 3)], (None, None, None, 3)])
def test_reject_unsupported_input_contract(shape):
    with pytest.raises(ValueError):
        prepare_input_tensor(Image.new("RGB", (10, 10)), SimpleNamespace(input_shape=shape))

def test_sigmoid_outputs_keep_raw_scores_and_legacy_relative_scores():
    result = postprocess_prediction(np.array([[0.8, 0.6, 0.2]]), ["a", "b", "c"], "sigmoid_scores")
    assert result["raw_scores"] == [0.8, 0.6, 0.2]
    np.testing.assert_allclose(result["scores"], [0.5, 0.375, 0.125])

@pytest.mark.parametrize("raw,labels", [(np.array([[np.nan, 1]]), ["a", "b"]), (np.array([[0.1,0.2,0.7]]), ["a","b"]), (np.zeros((1,2,2)), ["a","b"]), (np.array([[2,-1]]), ["a","b"])])
def test_invalid_outputs_are_rejected(raw, labels):
    with pytest.raises(ValueError):
        postprocess_prediction(raw, labels)

def test_logits_binary_and_tie_handling():
    binary = postprocess_prediction(np.array([[0.0]]), ["a", "b"], "logits")
    assert binary["scores"] == [0.5, 0.5]
    predictions = [{"prediction": postprocess_prediction(np.array([v]), ["a", "b"])} for v in [[0.8,0.2],[0.2,0.8]]]
    assert build_ensemble_summary(predictions)["majority"] == ["a", "b"]
    predictions[1]["prediction"]["labels"] = ["b", "a"]
    with pytest.raises(ValueError):
        build_ensemble_summary(predictions)

def test_image_decode_and_crop_bounds():
    buffer = io.BytesIO()
    Image.new("RGBA", (30,20)).save(buffer, "PNG")
    image = decode_image(buffer.getvalue())
    assert image.mode == "RGB"
    assert crop_image(image, (3,4,10,12)).size == (7,8)
    for box in [(0,0,0,4),(-1,0,4,4),(0,0,31,20)]:
        with pytest.raises(ValueError):
            crop_image(image, box)
    with pytest.raises(ValueError):
        decode_image(b"not an image")

def test_image_limits_and_multiframe(monkeypatch):
    import component_ai.images as image_module
    buf = io.BytesIO()
    Image.new("RGB", (5,5)).save(buf, "TIFF", save_all=True, append_images=[Image.new("RGB",(5,5))])
    with pytest.raises(ValueError, match="Multi-frame"):
        decode_image(buf.getvalue())
    buf = io.BytesIO()
    Image.new("RGB", (5,5)).save(buf, "PNG")
    monkeypatch.setattr(image_module, "MAX_PIXELS", 20)
    with pytest.raises(ValueError, match="megapixel"):
        decode_image(buf.getvalue())

def test_result_fingerprint_covers_all_settings():
    config = {"roi": [0,0,10,10], "model": "a", "threshold": 0.25}
    original = fingerprint("image1", config)
    assert original != fingerprint("image2", config)
    assert original != fingerprint("image1", {**config, "threshold": 0.5})
    assert original != fingerprint("image1", {**config, "roi": [0,0,5,5]})

def test_yolo_preserves_rgb_and_reports_boxes():
    image = Image.new("RGB", (20,20), (255,0,0))
    class Model:
        def predict(self, **kwargs):
            assert isinstance(kwargs["source"], Image.Image)
            assert kwargs["source"].getpixel((0,0)) == (255,0,0)
            assert kwargs["conf"] == 0.25
            return [SimpleNamespace(names={0:"egg"}, boxes=SimpleNamespace(xyxy=np.array([[1,2,10,12]]), conf=np.array([0.9]), cls=np.array([0])), speed={"inference":1.0})]
    result = run_yolo_inference(Model(), image, 0.25)
    assert result["class_counts"] == {"egg":1}
    assert result["detections"][0]["bbox_xyxy"] == [1,2,10,12]
