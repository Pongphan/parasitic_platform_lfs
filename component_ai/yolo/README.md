# YOLO detection adapters

Auto detection selects `weights/yolo26n.pt` or `weights/yolo26x.pt` independently.
Image size comes from model.json. Install requirements-yolo.txt.

Current local checkpoints expose class_0, class_1 and class_2. The shared
settings.py vocabulary maps class_1 to Opisthorchis viverrini egg and class_2
to Minute intestinal fluke egg. Class_0 and unrelated labels stay unchanged.
Numeric IDs and scores are preserved. These files have been replaced locally
since the earlier official YOLO26 download; names alone do not prove architecture.

Default confidence is 0.7 in settings.py and can be overridden by the UI or API.
The page never substitutes or downloads weights during inference. Cached model
loading uses file mtime and size; reports include the actual checkpoint SHA-256.
Both adapters use component_ai/annotations.py for numbered, contrast-enhanced
boxes. Gallery, table and JSON exports use the same normalized labels.

The load_yolo_model(path, file_version) interface returns (model, lock, sha256).
run_yolo_inference(model, image, confidence_threshold=DEFAULT_CONFIDENCE,
iou_threshold=0.45, image_size=640) returns detections, class counts, actual
normalized model class names and an annotated image.
