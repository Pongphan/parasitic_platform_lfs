import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from component_ai.models import discover_models, model_contract
from component_ai.detection import AI_ROOT, detector_contract


def test_auto_model_choices_resolve_distinct_checkpoints():
    from component_ai.detection import AUTO_MODELS, auto_detector_contract
    assert AUTO_MODELS == ("yolo26n", "yolo26x", "Faster R-CNN")
    for name in AUTO_MODELS:
        family, contract, weights = auto_detector_contract(name)
        assert weights.parent == AI_ROOT / family / "weights"
        if family == "yolo":
            assert weights.name == f"{name}.pt"
            assert contract["weights"] == f"weights/{name}.pt"
    with pytest.raises(ValueError, match="Unknown"):
        auto_detector_contract("../../outside")
from component_ai.roi import compute_center_cell_crop_box
from component_layout.viewer import selection_from_event

def test_all_six_keras_weights_relocated_without_modification():
    paths = discover_models()
    assert len(paths) == 6
    assert not list(AI_ROOT.glob("*.keras"))
    original = AI_ROOT.parent.parent / "parasitic_platform_2026" / "pages_model"
    for path in paths:
        assert path.parent.name == "keras"
        assert model_contract(path)["output"] == "sigmoid_scores"
        if (original / path.name).exists():
            assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256((original/path.name).read_bytes()).digest()

def test_model_discovery_is_cwd_independent_and_checks_contracts(monkeypatch,tmp_path):
    from component_ai.models import model_inventory
    monkeypatch.chdir(tmp_path)
    assert len(discover_models()) == 6
    assert all(item["error"] is None for item in model_inventory())
    (tmp_path/"one.KERAS").write_bytes(b"not loaded in this discovery test")
    assert len(discover_models(tmp_path)) == 1
    assert "Missing model contract" in model_inventory(tmp_path)[0]["error"]
    contract = {"schema_version":1,"labels":["a","b"],"preprocessing":"raw_0_255","output":"sigmoid_scores"}
    (tmp_path/"one.json").write_text(json.dumps(contract),encoding="utf-8-sig")
    assert model_inventory(tmp_path)[0]["error"] is None
    for broken in [[], {**contract,"schema_version":2}, {**contract,"labels":["a","a"]}]:
        (tmp_path/"one.json").write_text(json.dumps(broken))
        assert model_inventory(tmp_path)[0]["error"]

def test_drop_in_manifests_and_missing_weights():
    for family in ("yolo", "rcnn"):
        manifest, path = detector_contract(family)
        assert path.parent == AI_ROOT / family / "weights"
        assert manifest["architecture"]
        assert (path.parent / "PLACE_WEIGHTS_HERE.txt").exists()

def test_manifest_rejects_traversal_and_bad_background(tmp_path):
    folder = tmp_path / "rcnn"
    folder.mkdir()
    manifest, _ = detector_contract("rcnn")
    (folder/"model.json").write_text(json.dumps({**manifest,"weights":"../../evil.pth"}))
    with pytest.raises(ValueError, match="inside"):
        detector_contract("rcnn", tmp_path)
    (folder/"model.json").write_text(json.dumps({**manifest,"labels":["egg","artifact"]}))
    with pytest.raises(ValueError, match="background"):
        detector_contract("rcnn", tmp_path)

@pytest.mark.parametrize("architecture,norm", [
    ("fasterrcnn_resnet50_fpn", "unknown_norm"),
    ("fasterrcnn_resnet50_fpn", None),
    ("fasterrcnn_resnet50_fpn_v2", "frozen_batch_norm2d"),
])
def test_manifest_rejects_unsupported_backbone_norm(tmp_path, architecture, norm):
    folder = tmp_path / "rcnn"
    folder.mkdir()
    manifest, _ = detector_contract("rcnn")
    manifest.update(architecture=architecture, backbone_norm=norm)
    (folder / "model.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        detector_contract("rcnn", tmp_path)


def test_viewer_matches_2026_mapping_and_validates_events():
    image = Image.new("RGB", (1200,900))
    event = {"action":"calculate","image_id":"abc","calc_token":"one","zoom":2,"panX":30,"panY":-20,"viewport":600}
    box, _, token = selection_from_event(image,event,"abc")
    assert box == compute_center_cell_crop_box(image,600,2,30,-20)
    assert token == "one"
    for changed in [{"image_id":"other"},{"zoom":float("nan")},{"panX":1e8},{"viewport":0},{"calc_token":""}]:
        with pytest.raises(ValueError):
            selection_from_event(image,{**event,**changed},"abc")

def test_rcnn_preprocessing_filtering_nms_and_coordinates():
    torch = pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    from component_ai.rcnn import run_rcnn_inference
    class Model:
        def __call__(self, images):
            assert images[0].shape == (3,20,30)
            assert images[0].dtype == torch.float32
            assert images[0][0,0,0] == 1 and images[0][1,0,0] == 0
            assert not torch.is_grad_enabled()
            return [{"boxes":torch.tensor([[1,2,15,16],[1,2,15,16],[0,0,10,10],[25,15,35,25]],dtype=torch.float32), "scores":torch.tensor([.9,.8,.1,.7]), "labels":torch.tensor([1,1,2,2])}]
    result = run_rcnn_inference(Model(),Image.new("RGB",(30,20),(255,0,0)),["__background__","egg","artifact"],.25)
    assert len(result["detections"]) == 2
    assert result["detections"][1]["bbox_xyxy"] == [25,15,30,20]
    assert result["class_counts"] == {"egg":1,"artifact":1}

@pytest.mark.parametrize("architecture,norm", [
    ("fasterrcnn_resnet50_fpn", "batch_norm2d"),
    ("fasterrcnn_resnet50_fpn_v2", "batch_norm2d"),
    ("fasterrcnn_resnet50_fpn", "frozen_batch_norm2d"),
    ("fasterrcnn_resnet50_fpn", None),
    ("fasterrcnn_resnet50_fpn_v2", None),
])
def test_rcnn_loader_uses_safe_checkpoint_no_pretrained_download(monkeypatch, tmp_path, architecture, norm):
    torch = pytest.importorskip("torch")
    detection = pytest.importorskip("torchvision.models.detection")
    backbone_utils = pytest.importorskip("torchvision.models.detection.backbone_utils")
    from torchvision.ops.misc import FrozenBatchNorm2d
    from component_ai.rcnn import load_rcnn_model
    manifest, _ = detector_contract("rcnn")
    manifest["architecture"] = architecture
    if norm is None:
        manifest.pop("backbone_norm", None)  # Legacy manifests keep standard BatchNorm.
    else:
        manifest["backbone_norm"] = norm
    seen = {}
    backbone = object()
    class Model:
        def load_state_dict(self, state, strict):
            assert strict and state == {"sentinel": 123}
            seen["strict_load"] = True
        def eval(self):
            seen["eval"] = True
    def build_standard(**kwargs):
        seen["model_kwargs"] = kwargs
        return Model()
    def build_backbone(**kwargs):
        seen["backbone_kwargs"] = kwargs
        return backbone
    def build_frozen(supplied_backbone, **kwargs):
        assert supplied_backbone is backbone
        seen["model_kwargs"] = kwargs
        return Model()
    def unexpected_builder(*args, **kwargs):
        pytest.fail("Loader selected the wrong model construction path")
    def load(path, **kwargs):
        assert kwargs == {"weights_only": True, "map_location": "cpu"}
        return {"model_state_dict": {"sentinel": 123}}
    for name in ("fasterrcnn_resnet50_fpn", "fasterrcnn_resnet50_fpn_v2"):
        monkeypatch.setattr(detection, name, unexpected_builder)
    monkeypatch.setattr(detection, "FasterRCNN", unexpected_builder)
    monkeypatch.setattr(backbone_utils, "resnet_fpn_backbone", unexpected_builder)
    if norm == "frozen_batch_norm2d":
        monkeypatch.setattr(detection, "FasterRCNN", build_frozen)
        monkeypatch.setattr(backbone_utils, "resnet_fpn_backbone", build_backbone)
    else:
        monkeypatch.setattr(detection, architecture, build_standard)
    monkeypatch.setattr(torch, "load", load)
    path = tmp_path / "model.pth"
    path.write_bytes(b"loader contract fixture; not real weights")
    load_rcnn_model.clear()
    try:
        model, lock, digest = load_rcnn_model(str(path), (1, 1), json.dumps(manifest))
        expected = {"num_classes": len(manifest["labels"]), "min_size": manifest["min_size"],
                    "max_size": manifest["max_size"], "box_detections_per_img": manifest["detections_per_image"]}
        if norm == "frozen_batch_norm2d":
            assert seen["backbone_kwargs"] == {"backbone_name": "resnet50", "weights": None,
                                               "norm_layer": FrozenBatchNorm2d, "trainable_layers": 5}
        else:
            expected.update(weights=None, weights_backbone=None)
            assert "backbone_kwargs" not in seen
        assert seen["model_kwargs"] == expected
        assert seen["strict_load"] and seen["eval"]
        assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
        with lock:
            assert isinstance(model, Model)
    finally:
        load_rcnn_model.clear()


def test_rcnn_loader_rejects_incompatible_checkpoint_without_fallback(monkeypatch, tmp_path):
    torch = pytest.importorskip("torch")
    detection = pytest.importorskip("torchvision.models.detection")
    from component_ai.rcnn import load_rcnn_model
    manifest, _ = detector_contract("rcnn")
    manifest.update(architecture="fasterrcnn_resnet50_fpn", backbone_norm="batch_norm2d")
    strict_calls = []
    class Model:
        def load_state_dict(self, state, strict):
            strict_calls.append(strict)
            raise RuntimeError("Missing key(s) in state_dict: incompatible backbone")
        def eval(self):
            pytest.fail("An incompatible model must not reach evaluation mode")
    monkeypatch.setattr(detection, "fasterrcnn_resnet50_fpn", lambda **kwargs: Model())
    monkeypatch.setattr(torch, "load", lambda *args, **kwargs: {"state_dict": {"wrong": 123}})
    path = tmp_path / "incompatible.pth"
    path.write_bytes(b"incompatible fixture")
    load_rcnn_model.clear()
    try:
        with pytest.raises(ValueError, match="incompatible") as error:
            load_rcnn_model(str(path), (1, 1), json.dumps(manifest))
        assert isinstance(error.value.__cause__, RuntimeError)
        assert strict_calls == [True]
    finally:
        load_rcnn_model.clear()


def test_bundled_rcnn_checkpoint_matches_frozen_backbone_and_head():
    manifest, path = detector_contract("rcnn")
    if not path.is_file():
        pytest.skip("Bundled Faster R-CNN checkpoint is not installed")
    torch = pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    from torchvision.ops.misc import FrozenBatchNorm2d
    from component_ai.rcnn import load_rcnn_model
    from component_ai.registry import file_version
    assert manifest["architecture"] == "fasterrcnn_resnet50_fpn"
    assert manifest["backbone_norm"] == "frozen_batch_norm2d"
    checkpoint = torch.load(str(path), weights_only=True, map_location="cpu")
    state = checkpoint.get("model_state_dict", checkpoint.get("state_dict", checkpoint))
    load_rcnn_model.clear()
    try:
        model, _, _ = load_rcnn_model(str(path), file_version(path), json.dumps(manifest, sort_keys=True))
        actual = model.state_dict()
        assert actual.keys() == state.keys()
        assert {key: tuple(value.shape) for key, value in actual.items()} == {
            key: tuple(value.shape) for key, value in state.items()}
        assert isinstance(model.backbone.body.bn1, FrozenBatchNorm2d)
        assert not any(isinstance(layer, torch.nn.BatchNorm2d) for layer in model.backbone.modules())
        assert model.roi_heads.box_predictor.cls_score.out_features == len(manifest["labels"])
        assert model.roi_heads.box_predictor.bbox_pred.out_features == 4 * len(manifest["labels"])
        assert not model.training
    finally:
        load_rcnn_model.clear()

def test_button_hues_are_distinct_and_readable():
    import re,colorsys
    css=(AI_ROOT.parent/"component_theme/styles.css").read_text()
    colors=re.findall(r"--button-[a-z]+:(#[A-F0-9]{6})",css)
    assert len(colors)==6 and len(set(colors))==6
    hues=[]
    def luminance(rgb):
        linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(v*w for v,w in zip(linear,[.2126,.7152,.0722]))
    ink=[int("203C36"[i:i+2],16)/255 for i in [0,2,4]]
    for color in colors:
        rgb=[int(color[i:i+2],16)/255 for i in [1,3,5]]
        hues.append(round(colorsys.rgb_to_hls(*rgb)[0]*360))
        assert (luminance(rgb)+.05)/(luminance(ink)+.05)>=4.5
    assert len(set(hues))==6
