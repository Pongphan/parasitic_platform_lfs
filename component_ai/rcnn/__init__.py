"""Lazy, interchangeable Faster R-CNN inference service."""
import hashlib
import json
import threading
from collections import Counter
from pathlib import Path
import numpy as np
import streamlit as st
from component_ai.yolo import annotate_detections
from component_ai.settings import DEFAULT_CONFIDENCE, canonical_labels

@st.cache_resource(show_spinner=False, max_entries=2)
def load_rcnn_model(path, version, contract_json):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Faster R-CNN weights are missing: {path.name}")
    try:
        import torch
        from torchvision.models.detection import fasterrcnn_resnet50_fpn, fasterrcnn_resnet50_fpn_v2
    except (ImportError, RuntimeError) as exc:
        raise RuntimeError("Install a matching torch/torchvision pair from requirements-rcnn.txt.") from exc
    contract = json.loads(contract_json)
    builders = {"fasterrcnn_resnet50_fpn": fasterrcnn_resnet50_fpn, "fasterrcnn_resnet50_fpn_v2": fasterrcnn_resnet50_fpn_v2}
    architecture = contract["architecture"]
    norm = contract.get("backbone_norm", "batch_norm2d")
    if norm not in {"batch_norm2d", "frozen_batch_norm2d"}:
        raise ValueError("Unsupported Faster R-CNN backbone_norm")
    options = dict(num_classes=len(contract["labels"]), min_size=contract["min_size"],
                   max_size=contract["max_size"], box_detections_per_img=contract["detections_per_image"])
    if norm == "frozen_batch_norm2d":
        if architecture != "fasterrcnn_resnet50_fpn":
            raise ValueError("Frozen backbone normalization requires fasterrcnn_resnet50_fpn")
        from torchvision.models.detection import FasterRCNN
        from torchvision.models.detection.backbone_utils import resnet_fpn_backbone
        from torchvision.ops.misc import FrozenBatchNorm2d
        # The v1 convenience builder chooses regular BatchNorm when pretrained
        # downloads are disabled. Build explicitly to match the installed weights.
        backbone = resnet_fpn_backbone(backbone_name="resnet50", weights=None,
                                      norm_layer=FrozenBatchNorm2d, trainable_layers=5)
        model = FasterRCNN(backbone, **options)
    else:
        model = builders[architecture](weights=None, weights_backbone=None, **options)
    checkpoint = torch.load(str(path), weights_only=True, map_location="cpu")
    if not isinstance(checkpoint, dict):
        raise ValueError("Expected a state_dict or a checkpoint containing model_state_dict")
    state = checkpoint.get("model_state_dict", checkpoint.get("state_dict", checkpoint))
    try:
        model.load_state_dict(state, strict=True)
    except RuntimeError as exc:
        raise ValueError(
            "Faster R-CNN checkpoint is incompatible with the configured architecture or class count. "
            "Confirm model.json against the original training configuration and provide matching weights. "
            "No architecture, labels or weights were changed automatically."
        ) from exc
    model.eval()
    return model, threading.RLock(), hashlib.sha256(path.read_bytes()).hexdigest()

def run_rcnn_inference(model, image, labels, confidence_threshold=DEFAULT_CONFIDENCE, *, iou_threshold=0.45):
    import torch
    from torchvision.ops import batched_nms
    if not 0 <= confidence_threshold <= 1 or not 0 <= iou_threshold <= 1:
        raise ValueError("Detection thresholds must be between zero and one")
    labels = canonical_labels(labels)
    rgb = image.convert("RGB")
    tensor = torch.from_numpy(np.array(rgb, dtype=np.float32) / 255.0).permute(2, 0, 1)
    with torch.inference_mode():
        outputs = model([tensor])
    if not isinstance(outputs, list) or len(outputs) != 1:
        raise ValueError("Expected one Faster R-CNN result for one image")
    raw = outputs[0]
    boxes = raw["boxes"].detach().cpu()
    scores = raw["scores"].detach().cpu()
    ids = raw["labels"].detach().cpu()
    if boxes.ndim != 2 or boxes.shape[1] != 4 or scores.ndim != 1 or ids.ndim != 1 or len(boxes) != len(scores) or len(scores) != len(ids):
        raise ValueError("Malformed Faster R-CNN outputs")
    if not torch.isfinite(boxes).all() or not torch.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Invalid Faster R-CNN boxes or scores")
    if ids.dtype not in (torch.int32, torch.int64) or ((ids < 0) | (ids >= len(labels))).any():
        raise ValueError("Detection class IDs do not match the manifest")
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clamp(0, rgb.width)
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clamp(0, rgb.height)
    valid = (scores >= confidence_threshold) & (ids > 0) & (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
    boxes, scores, ids = boxes[valid], scores[valid], ids[valid]
    keep = batched_nms(boxes, scores, ids, iou_threshold)
    detections = [{"class_id": int(ids[i]), "class_name": labels[int(ids[i])], "confidence": float(scores[i]), "bbox_xyxy": boxes[i].tolist()} for i in keep]
    return {"detections": detections, "class_counts": dict(Counter(d["class_name"] for d in detections)), "class_names": labels[1:], "confidence_threshold": confidence_threshold, "iou_threshold": iou_threshold, "annotated_image": annotate_detections(rgb, detections)}
