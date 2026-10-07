"""YOLO11 object-detection services for the Parasitic Vision page.

This module is intentionally separate from the legacy Keras ROI-classification
pipeline in ``component_models.py``.  It owns model loading, full-image YOLO
inference, result normalization, and annotation rendering.
"""

from collections import Counter
import hashlib
import logging
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import streamlit as st
from PIL import Image
from component_ai.annotations import annotate_detections
from component_ai.settings import DEFAULT_CONFIDENCE, canonical_label

_LOGGER = logging.getLogger(__name__)


DEFAULT_CLASS_NAMES = (
    "artifact",
    "Opisthorchis viverrini egg",
    "Minute intestinal fluke egg",
)

_BOX_COLORS = (
    "#22D3EE",
    "#A78BFA",
    "#F59E0B",
    "#34D399",
    "#FB7185",
    "#60A5FA",
)


@st.cache_resource(show_spinner=False, max_entries=2)
def load_yolo_model(weights_path: str, version: tuple) -> Any:
    """Load and cache an Ultralytics YOLO model for Streamlit reruns.

    ``weights_path`` must point to custom YOLO11 detection weights.  The
    Ultralytics import is lazy so the rest of the platform can still start and
    show installation guidance when the optional dependency is absent.
    """
    path = Path(weights_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"YOLO weights file not found: {path}")

    try:
        from ultralytics import YOLO
    except (ImportError, OSError, RuntimeError) as exc:
        # The page handles this error, so log the original traceback here for
        # Cloud diagnostics (e.g. OpenCV cannot load a Linux shared library).
        _LOGGER.exception("Failed to import Ultralytics for Auto Detection")
        if isinstance(exc, ModuleNotFoundError) and exc.name == "ultralytics":
            raise RuntimeError(
                "Ultralytics is required for Auto Detection. Install the project "
                "requirements with `pip install -r requirements-yolo.txt`."
            ) from exc
        raise RuntimeError(
            "Auto Detection dependencies could not be loaded. "
            "The app administrator can check the server logs for details."
        ) from exc

    return YOLO(str(path)), threading.RLock(), hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_class_names(
    names: Mapping[int, str] | Sequence[str] | None,
    fallback: Sequence[str],
) -> dict[int, str]:
    """Return a stable integer-to-label mapping from YOLO metadata."""
    if isinstance(names, Mapping):
        normalized = {int(index): canonical_label(label) for index, label in names.items()}
        if normalized:
            return normalized
    elif names:
        return {index: canonical_label(label) for index, label in enumerate(names)}
    return {index: canonical_label(label) for index, label in enumerate(fallback)}


def _tensor_to_numpy(value: Any) -> np.ndarray:
    """Convert an Ultralytics/Torch tensor-like value to a NumPy array."""
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def _extract_detections(
    result: Any,
    fallback_class_names: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[int, str]]:
    """Convert one Ultralytics ``Results`` object into plain dictionaries."""
    class_names = _normalize_class_names(
        getattr(result, "names", None),
        fallback_class_names,
    )
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return [], class_names

    coordinates = _tensor_to_numpy(boxes.xyxy).reshape(-1, 4)
    confidences = _tensor_to_numpy(boxes.conf).reshape(-1)
    class_ids = _tensor_to_numpy(boxes.cls).reshape(-1)

    detections: list[dict[str, Any]] = []
    for xyxy, confidence, class_id_value in zip(
        coordinates,
        confidences,
        class_ids,
    ):
        class_id = int(class_id_value)
        detections.append(
            {
                "class_id": class_id,
                "class_name": class_names.get(class_id, f"unknown_{class_id}"),
                "confidence": float(confidence),
                "bbox_xyxy": [float(value) for value in xyxy.tolist()],
            }
        )
    return detections, class_names


def run_yolo_inference(
    model: Any,
    image: Image.Image,
    confidence_threshold: float = DEFAULT_CONFIDENCE,
    *,
    iou_threshold: float = 0.45,
    image_size: int = 640,
    fallback_class_names: Sequence[str] = DEFAULT_CLASS_NAMES,
) -> dict[str, Any]:
    """Run YOLO detection and return a UI/database-friendly result mapping.

    The confidence threshold is passed directly to YOLO before detections are
    normalized.  No Streamlit widget or session state is accessed here, which
    keeps the inference service reusable outside this page.
    """
    rgb_image = image.convert("RGB")
    results = model.predict(
        # Ultralytics treats numpy inputs as BGR; PIL inputs preserve RGB.
        source=rgb_image,
        conf=float(confidence_threshold),
        iou=float(iou_threshold),
        imgsz=int(image_size),
        verbose=False,
    )
    if not results:
        raise RuntimeError("YOLO returned no result object for the image.")

    result = results[0]
    detections, class_names = _extract_detections(
        result,
        fallback_class_names,
    )
    counts = Counter(item["class_name"] for item in detections)
    speed = {
        str(stage): float(milliseconds)
        for stage, milliseconds in (getattr(result, "speed", None) or {}).items()
        if milliseconds is not None
    }

    return {
        "annotated_image": annotate_detections(rgb_image, detections),
        "detections": detections,
        "class_counts": dict(sorted(counts.items())),
        "class_names": [class_names[index] for index in sorted(class_names)],
        "confidence_threshold": float(confidence_threshold),
        "iou_threshold": float(iou_threshold),
        "image_size": int(image_size),
        "speed_ms": speed,
    }
