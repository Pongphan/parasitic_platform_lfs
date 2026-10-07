"""Manifest resolution shared by full-image detector backends."""
import json
from pathlib import Path
from component_ai.settings import canonical_labels

AI_ROOT = Path(__file__).resolve().parent
AUTO_MODELS = ("yolo26n", "yolo26x", "Faster R-CNN")
MODEL_DISPLAY_NAMES = {
    "yolo26n": "meinmodel lite",
    "yolo26x": "meinmodel medium",
    "Faster R-CNN": "meinmodel expert",
}


def model_display_name(model_id):
    """Public names are separate from stable model IDs and checkpoint paths."""
    name = MODEL_DISPLAY_NAMES.get(model_id)
    return f"{name} ({model_id})" if name else model_id


def model_scope(model_id):
    """Describe the selected workflow without implying an accuracy ranking."""
    descriptions = {
        "yolo26n": "YOLO26n locates objects across the whole image using the nano architecture.",
        "yolo26x": "YOLO26x locates objects across the whole image using the extra-large architecture.",
        "Faster R-CNN": "Faster R-CNN locates objects across the whole image using a ResNet50-FPN backbone.",
    }
    return descriptions.get(model_id, "Full-image object detection.")


def auto_detector_contract(model_name, root=AI_ROOT):
    """Resolve only the three supported choices; never accept arbitrary paths."""
    if model_name not in AUTO_MODELS:
        raise ValueError("Unknown auto detection model")
    family = "rcnn" if model_name == "Faster R-CNN" else "yolo"
    contract, weights = detector_contract(family, root)
    if family == "yolo":
        contract = {**contract, "weights": f"weights/{model_name}.pt"}
        folder = (Path(root) / family).resolve()
        weights = (folder / contract["weights"]).resolve()
        if not weights.is_relative_to(folder):
            raise ValueError("Weights must be inside the model family folder")
    return family, contract, weights

def detector_contract(family, root=AI_ROOT):
    if family not in {"yolo", "rcnn"}:
        raise ValueError("Unknown detector family")
    folder = (Path(root) / family).resolve()
    contract = json.loads((folder / "model.json").read_text(encoding="utf-8"))
    weights = (folder / contract["weights"]).resolve()
    if not weights.is_relative_to(folder):
        raise ValueError("Weights must be inside the model family folder")
    if family == "yolo":
        if contract.get("architecture") != "ultralytics_yolo" or weights.suffix != ".pt":
            raise ValueError("YOLO requires an Ultralytics .pt detection checkpoint")
        if type(contract.get("image_size")) is not int or not 32 <= contract["image_size"] <= 4096:
            raise ValueError("YOLO image_size must be an integer from 32 to 4096")
    else:
        if contract.get("architecture") not in {"fasterrcnn_resnet50_fpn", "fasterrcnn_resnet50_fpn_v2"}:
            raise ValueError("Unsupported Faster R-CNN architecture")
        norm = contract.get("backbone_norm", "batch_norm2d")
        if norm not in {"batch_norm2d", "frozen_batch_norm2d"}:
            raise ValueError("Unsupported Faster R-CNN backbone_norm")
        if norm == "frozen_batch_norm2d" and contract["architecture"] != "fasterrcnn_resnet50_fpn":
            raise ValueError("Frozen backbone normalization requires fasterrcnn_resnet50_fpn")
        labels = contract.get("labels")
        if not isinstance(labels, list) or len(labels) < 2 or any(not isinstance(x, str) or not x for x in labels) or labels[0] != "__background__" or len(set(labels)) != len(labels):
            raise ValueError("RCNN labels need unique class names and background at index zero")
        for field in ("min_size", "max_size", "detections_per_image"):
            if type(contract.get(field)) is not int or not 1 <= contract[field] <= 4096:
                raise ValueError(f"Invalid RCNN {field}")
        if contract["min_size"] > contract["max_size"]:
            raise ValueError("RCNN min_size cannot exceed max_size")
        if weights.suffix not in {".pt", ".pth"}:
            raise ValueError("RCNN checkpoint must use .pt or .pth")
    if family == "rcnn":
        contract["labels"] = canonical_labels(contract["labels"])
    return contract, weights
