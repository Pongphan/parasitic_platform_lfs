"""Drop-in Ultralytics YOLO interface."""
from .service import load_yolo_model, run_yolo_inference, annotate_detections

__all__ = ["load_yolo_model", "run_yolo_inference", "annotate_detections"]
