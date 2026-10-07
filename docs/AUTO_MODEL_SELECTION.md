# Auto detection model selection

This update supersedes the sequential page workflow in DETECTION_MODE_UPDATE.md.
Detection mode remains Manual classifier / Auto detection. Auto detection now
has a required single-choice segmented control: yolo26n, yolo26x, Faster R-CNN.
It analyzes the full image using only the selected model. The old cascade
service remains available for code reuse but is no longer called by the page.

- Added the official Ultralytics `yolo26x.pt` checkpoint under component_ai/yolo/weights.
- Added explicit, bounded model-name resolution in component_ai/detection.py.
- Updated detector controls, model availability, results and reports. Changing
  models or thresholds hides mismatched prior results and download buttons.
- Model failures clear the result; missing RCNN weights do not block YOLO.
- Updated About, dependency minimum and model setup documentation.

Verification: 48 Python tests passed. Each model's UI branch was tested with a
deterministic backend double, including exports, model switching and failure.
Real YOLO26n and YOLO26x inference passed on a bundled microscopy sample; both
returned zero objects at threshold 0.25. This tests execution, not accuracy.
Both checkpoints expose 80 general-object classes. The configured Faster R-CNN
checkpoint remains absent, so its real inference cannot yet be verified.
