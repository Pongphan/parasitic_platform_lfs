# Detection and learning workflow update

## Changed files

- `component_layout/detector.py`: replaces Model family with Detection mode, using the same segmented control as Image source. The two branches are marked inline. Manual classifier preserves the 2026 pan/zoom/Calculate Keras workflow. Auto detection runs the new cascade and provides stage progress, proposal/final tabs, region inspection, annotated PNG and JSON downloads.
- `component_ai/pipeline.py`: testable sequential YOLO → Faster R-CNN inference. YOLO boxes become crops with 10% padding per side. RCNN boxes are translated back to the original image. Class-aware suppression at IoU 0.45 removes duplicates from overlapping crops. Final scores are RCNN scores, never cross-model averages. Raw stage evidence stays in the report.
- `pages/home.py`: guided observation, comparison, review and practice workflow with a detector shortcut.
- `pages/atlas.py`: up to three species compared side by side, using existing sourced identification notes and classifier coverage.
- `pages/examination.py`: return directly to the matching Atlas entry without losing practice answers.
- `component_theme/styles.css`: consistent detector control surfaces, reading spacing, numeric alignment and keyboard focus.
- `tests/test_pipeline.py`, `tests/test_app.py`: sequence, coordinate mapping, suppression, no-proposal fallback, malformed regions, stage failures, exports, stale settings and learning navigation checks.

## Result semantics

YOLO proposals are candidates, not confirmed final detections. RCNN runs on each candidate crop in sequence. If YOLO finds none, RCNN runs once on the full image. If RCNN finds nothing in a candidate, that candidate remains visible in the YOLO evidence only. More than 100 proposals stops the run with guidance to raise the threshold or reduce the field, rather than silently omitting regions. Failure in either stage prevents a completed report. Changing the image, model file version or thresholds hides stale results and downloads.

## Deployment status

Verification: 45 Python tests passed, including the full auto-page flow with
deterministic backend doubles. The JavaScript viewer contract also passed
initialization, resize, drag, zoom, Calculate and image identity checks.

The configured `component_ai/yolo/weights/parasite_yolo11.pt` and `component_ai/rcnn/weights/parasite_fasterrcnn.pth` files are absent. Supply compatible trained checkpoints or update their manifests to compatible local files, then install `requirements-yolo.txt` and `requirements-rcnn.txt`. The existing `yolo26n.pt` file is not the configured checkpoint and has not been validated as a parasite model; the app does not substitute it automatically.

The interface and cascade can be tested with deterministic backend doubles. End-to-end auto inference and model performance cannot be certified without both real trained checkpoints. Browser visual review was unavailable in this session. This update does not claim clinical validation or production deployment.

## Changelog

- Renamed Model family to Detection mode; exactly Manual classifier and Auto detection.
- Added sequential proposal/refinement inference, stage evidence and final region inspection.
- Added guided learning and morphology comparison; connected quiz review back to the Atlas.
- Refined shared styling and tested stale-result and failed-stage handling.
