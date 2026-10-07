# Detector and platform refinement — 2026-09-08

## Requirement changelog and code map

| Requirement | Implementation | Files |
| --- | --- | --- |
| A1 | Analysis-scoped review notes in JSON, CSV detections with model/image provenance, downloadable Atlas comparisons including sources, Home checkpoint availability and examination progress | component_layout/detector.py, component_layout/results.py, pages/home.py, pages/atlas.py, pages/examination.py |
| A2 | Shared modern heading typography, white cards, consistent control panels, tabs, responsive navigation and crop cards across the existing page structure | component_theme/styles.css, component_theme/theme.toml |
| A3 | Preserved independent YOLO/RCNN selection, Keras pan/zoom/Calculate, model caching, result invalidation and failure handling; verified real installed models and documented the remaining RCNN dependency | component_ai adapters, tests/test_app.py, tests/test_results.py |
| B1 | DEFAULT_CONFIDENCE = 0.7 is the single default for the detector slider and both backend APIs. Explicit caller thresholds and existing user selections still work. Keras classification is not threshold-filtered | component_ai/settings.py, component_layout/detector.py, component_ai/yolo/service.py, component_ai/rcnn/__init__.py |
| B2 | Every detection appears in a numbered crop card. Native flex wrapping adapts to viewport width; card sizes adapt to detection count. Aspect ratio is preserved; source pixel dimensions are shown | component_layout/results.py |
| B3 | Shared overlays: stable colors by label, scaled strokes with dark outline, white text on dark labels, region numbers, image-edge clamping and best-effort collision avoidance. Labels choose another position when space permits; densely packed fields may still overlap | component_ai/annotations.py |
| B4 | class_1 → Opisthorchis viverrini egg | component_ai/settings.py, YOLO/RCNN adapters, Keras contracts and postprocessing, content.py |
| B5 | class_2 → Minute intestinal fluke egg | Same shared normalization as B4 |

Class IDs, training order, numeric predictions and checkpoint bytes are unchanged.
The same labels are used in annotations, tables, gallery captions, counts and
reports. Lowercase variants of the two species names are normalized as well.
Class_0 remains unchanged because no new name was requested. COCO names are not
converted into parasite classes based on their numeric IDs.

## Verification and limits

- 55 Python tests passed, including navigation, all model UI branches, stale
  result handling, exports, 1/2/7-crop galleries, aliases, default thresholds,
  coordinate clamping and overlay label placement.
- JavaScript viewer contract passed: initialization, pan, zoom, resize,
  image binding and Calculate. The 2026 selection interaction is preserved.
- Both current YOLO files ran on a bundled microscopy sample at 0.7 and each
  returned three detections. Their embedded names are class_0/class_1/class_2;
  this supersedes the prior general-object model description. The files were
  already replaced locally before this update; no model weights were modified.
- All six Keras classifiers executed successfully with the canonical labels.
- A rendered annotation fixture was visually inspected, including overlapping
  and edge-touching boxes. Fixture boxes are layout examples, not predictions.
- Browser UI visual review was unavailable: no connected browser surface.
- Faster R-CNN weights remain absent at
  component_ai/rcnn/weights/parasite_fasterrcnn.pth. Its adapter is covered by
  tensor-based tests, but real checkpoint inference and full production readiness
  cannot be certified until compatible weights are supplied and validated.

No clinical accuracy or diagnostic validation is inferred from execution tests.
