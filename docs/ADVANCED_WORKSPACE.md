# Advanced analysis and learning workspace

Implemented September 19, 2026. No new runtime dependencies, model replacements,
external inference APIs, database, authentication, or training workflows were added.
The existing five pages and manual pan/zoom/Calculate component remain in place.

## Repository assessment and implementation stages

| Capability | Starting implementation | Current implementation |
| --- | --- | --- |
| Single-image analysis | Keras crop classifier, three automatic choices, snapshot invalidation | Preserved; analysis records and timings retained |
| Session lifecycle | Latest result and bounded activity summaries | Versioned records, image retention, history and portable archives |
| Batch inference | Absent | Bounded sequential queue, failure isolation, retry, pause/resume, exports |
| Comparison | Atlas reference comparisons only | Same-image automatic-model comparisons, counts, distributions, timings, spatial matching |
| Human review | Free-text analysis notes | Separate object review layer, pixel-coordinate edits, missed objects, undo, annotation exports |
| Evaluation | Absent | Strict COCO-box import, explicit category mapping, threshold metrics and unmatched-object inspection |
| Practice | Species quizzes with explanations | Preserved; mixed/group/adaptive quizzes, question history and optional confidence |
| Atlas learning | Search, filters, reference comparison | Bookmarks, topic lists, structured related references and guided pathways |

Stages and acceptance checks:

1. Shared state, matching, review and archive validation: original predictions
   remain immutable; known evaluation fixtures and archive round trips pass.
2. Batch, review, comparison and evaluation UI: per-item failures do not discard
   successes; reruns do not repeat completed inference; all views render in AppTest.
3. Learning workflows: answers survive navigation; selection has unique questions;
   existing species attempts feed adaptive practice; content facts remain unchanged.
4. Regression and runtime checks: existing routes/viewer tests, bounded real inference,
   Streamlit health check, and documented limitations.

## User walkthrough

### Single image and retained history

Use Parasite Detector → Single image as before. Successful, partial, and failed
analyses are retained. Automatic results and classifier crops can be reopened under
Advanced workspace → Session workspace without inference. The record contains the
image identity, dimensions, configuration, model hashes where loading succeeded,
original results, duration, errors, notes, and a separate object review layer.

Single-image result invalidation still checks image/configuration fingerprints.
The manual viewer only analyzes a newly committed Calculate event. Retained history
is explicitly historical and does not imply that it matches current detector controls.

### Batch analysis

1. Choose Advanced workspace → Batch and comparison.
2. Choose one to three models, confidence, uploaded images and/or bundled samples.
3. Prepare the queue. Validation errors appear independently for each image.
4. Start the queue. One image/model pair runs per fragment tick, under the existing
   backend lock. Keep this page open. It is not a background server job.
5. Cancel between images to pause; an active model call is not interruptible.
   Resume pending items or retry inference failures explicitly. Invalid files must
   be corrected and included in a new queue. Successful items are not retried.
6. Use Refresh batch results after completion to refresh the outer result picker.
7. Inspect a result, detected crops, or prepare a batch ZIP.

Duplicate image bytes with identical configuration are deduplicated within a queue.
Preparing a new queue is an explicit new analysis request. Configuration and model
file versions are frozen at preparation. Changed checkpoints require a new queue.
Interrupted executions are marked failed on return and require explicit retry.
Missing/evicted source images can be restored by SHA-256 before retrying.

Batch ZIPs contain original annotated images for completed analyses, complete
versioned JSON records, a CSV summary, and a manifest with file hashes, queue errors,
and unavailable annotated-image IDs. The CSV uses analysis/image IDs rather than
untrusted filenames. Prepared downloads are labeled snapshots; rebuild after edits.

### Comparison

Select two or three retained completed automatic analyses of the same image.
The view shows annotated outputs, per-class counts, confidence histograms, full
settings, elapsed time, and separate load/cache, lock-wait, and inference/annotation
times where captured. Loading time includes a cache lookup on warm runs; it is not
presented as a controlled benchmark.

Spatial agreement uses exact class labels, descending prediction confidence,
and the highest-IoU unused compatible reference. Each detection can match only once;
ties use original index order. Every unmatched object remains in the exported report.
The user controls IoU. Spatial agreement is not correctness, and confidence scores
are not necessarily comparable between models. Classifiers are excluded from this
comparison. Save comparisons to reopen them in Session workspace; record retention
may later make a saved comparison unavailable.

### Human review

Open a retained automatic analysis, then Review objects and edit source-pixel boxes.
Filter by review state and original predicted class. Choose an object or Add missed
object. Labels, source-pixel bounds and notes are entered in a native form. Coordinates
refer to the original image, regardless of display resizing. All four coordinates
must define a nonempty box inside the source image. This is a numeric box editor,
not a drag-to-draw canvas; the existing manual classifier viewer remains unchanged.

Accepted/unreviewed states cannot silently alter an original label or box. Use
corrected for changes. Rejected objects remain in the report but are omitted from
the reviewed overlay/export. Manually added objects do not receive invented model
confidence scores. The latest 20 edits can be undone. Image restoration is required
before editing when source bytes are absent. Exact configured model labels link to
Atlas entries; custom reference labels do not extend model recognition.

Dataset exports require a deliberate ordered list of exact class labels, one per
line. IDs start at 0. Only accepted/corrected objects are included; unreviewed and
rejected objects are excluded. Review every object and add missed objects before
using the result as an annotation dataset. Empty annotations are explicit negatives
in COCO, so exporting an incompletely reviewed image is not an independent evaluation.

The ZIP contains COCO JSON, YOLO normalized center-x/center-y/width/height text files,
classes.txt, original records with their review layers, and a mapping manifest.
YOLO filenames use analysis IDs; the manifest maps each to source name and SHA-256.
Source images are not included in annotation exports. Importing an exported COCO file
into evaluation preserves its human-review origin marker. Nothing retrains models.

### Ground-truth evaluation

Select completed analyses from one model/configuration, one analysis per image.
Upload COCO JSON and explicitly map each category name to the exact prediction label.
Declare reference origin and choose confidence/IoU thresholds. The confidence threshold
cannot be below the original inference threshold, because filtered-out predictions
were not retained. Rerun inference at a lower threshold when necessary.

Supported COCO subset:

```json
{
  "info": {"origin": "independently annotated; user supplied"},
  "images": [
    {"id": 1, "file_name": "sample.png", "width": 640, "height": 480}
  ],
  "categories": [{"id": 1, "name": "egg"}],
  "annotations": [
    {"id": 1, "image_id": 1, "category_id": 1,
     "bbox": [10, 20, 30, 40], "iscrowd": 0}
  ]
}
```

An optional lowercase 64-character `sha256` on each image is preferred for exact
identity. Otherwise matching requires exact filename plus matching dimensions and
is labeled accordingly. IDs must be unique integers. Category mappings must be
one-to-one. Boxes use COCO [x, y, width, height]. Crowd, ignored objects, nonempty
segmentation and keypoints are rejected. Maximums: 200 images, 20,000 boxes, 500
categories, 16 MB JSON, 24 megapixels per image.

An image listed in `images` with no annotations is explicitly negative. An analyzed
image absent from `images` is excluded as unknown, not counted as a false positive.
Reference images without selected analyses are reported separately. Duplicate source
analyses, incompatible settings, ambiguous identities and dimension mismatches fail
validation rather than silently changing the evaluation population.

The matching policy is confidence-ordered, same-label, best-unused-IoU greedy matching.
Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2TP/(2TP+FP+FN).
Zero denominators yield null, not invented perfect scores. Reports include per-class
and micro-aggregate counts, thresholds, mappings, dataset hash and analysis/model
provenance. Inspect unmatched prediction and reference overlays when source images
are retained. No mAP, disease probability, or clinical validation is claimed.

### Adaptive learning and Atlas

Examination → Mixed and adaptive allows taxonomic-group filters, quiz length, missed
questions only, and optional Low/Medium/High confidence ratings. No group selection
means the entire collection. Recent incorrect answers have priority, followed by
least-practiced questions; ties use stable question IDs. Missed-only uses the latest
answer for each question, so a subsequently corrected question leaves that list.

An active quiz snapshots its questions. Changing setup controls affects the next quiz
only; replacing an unfinished quiz requires its checkbox. Answers and confidence
persist through navigation. Submission is idempotent and explanations link to the
Atlas. Species practice also feeds the same question-level history. Topic summaries
count actual attempts, including repeated attempts, and are not competency measures.

Atlas bookmarks and up to 50 learning lists are session-based. Lists can be assembled
by category or existing clinical tags. Related entries use declared morphology links,
shared taxonomy categories and content tags only. Guided pathways connect existing
tabs, microscopy review and practice without asserting sample/model coverage.
Translation controls appear only for available translations; missing fields fall back
to English with an explicit caption.

## State and archive schema

`workspace.py` owns Streamlit-independent state. Schema `2027.2` records have:

- `analysis_id`, `created_at`, `image` (SHA-256, name, width, height).
- `mode`, `configuration`, `model_sha256`, `status`, `elapsed_seconds`.
- `warnings`, `errors`, `original`, `notes`, `review`, `review_undo`.

Original inference reports are copied into records and never edited by review.
Source images live separately in the session image store. Model objects stay in
existing bounded shared backend caches. No executable queue is imported from an archive.

The session ZIP contains `session.json` and optional `images/<sha256>.bin` members.
`.bin` members contain the original supported image bytes, not serialized Python.
Source-image inclusion is off by default. No files are extracted to disk during import.
Imported data replaces the workspace only after complete validation and a deliberate
replacement checkbox. Widget state and prepared downloads are reset on restoration.
Undo history is intentionally reset; reviewed annotations remain. Existing analysis
reports must use the supported session schema; this is not an arbitrary JSON importer.

The archive preserves records, saved comparisons, active adaptive quiz, completed quiz
attempts, question history, bookmarks, learning lists and limits. Restoring without
source images keeps reports available; the exact original bytes can be restored later
after hash and dimension checks. Quiz imports must match installed question content.
Legacy species quiz drafts are not portable; use adaptive practice for a portable
unfinished quiz. Completed species attempts are included in the shared attempt store.

Archive validation rejects unsupported schemas, unknown members, traversal/absolute
paths, duplicate ZIP/JSON members, symbolic links, encrypted content, excessive
compression, malformed records, wrong hashes/dimensions and invalid learning data.
Only JSON and decoded image data are accepted; never pickle, code or model weights.

## Resource limits

| Resource | Limit |
| --- | --- |
| Single image | 25 MB, 24 megapixels, one frame |
| Batch | Default 12 images, configurable 1–24; 1–3 models |
| Session images | Default 128 MB, configurable 16–256 MB; max 200 images |
| Image budget accounting | Compressed bytes plus decoded RGB size; oldest image evicted first |
| Analyses | Default/max 200; configurable downward |
| Comparisons | Latest 100 |
| Completed quizzes | Latest 100 |
| Question attempts | Latest 2,000 |
| Review undo | Latest 20 edits per analysis |
| Session ZIP | Max 256 MB compressed, 300 MB declared expanded |
| Session metadata | Max 16 MB JSON |

Image eviction preserves analysis metadata. Record eviction may remove analyses used
by saved comparisons, which are then visibly unavailable. Budgets do not include ML
model allocations, Streamlit uploader buffers, the active single-image viewer, or
temporary export buffers. Exports are explicit, size-bounded operations; reduce batch
size or omit images if a download exceeds its limit. This is a local/session workspace,
not a durable or multi-user job service.

## Verification and known limitations

**September 30, 2026 Faster R-CNN correction:** the installed checkpoint now loads
strictly with ResNet50-FPN v1 and an explicitly constructed FrozenBatchNorm2d
backbone (295 matching state entries). The original checkpoint and labels remain.
Single-image inference and a prepared batch job both completed on the 640 x 502
bundled sample with identical detections. See the [checkpoint contract](../component_ai/rcnn/README.md)
for configuration, verification and remaining provenance limits.

The following checks describe the original September 19 workspace update:

- **92 Python tests passed.** Tests cover original behavior plus batch isolation/retry/cancellation,
  deterministic matching, exact metrics, review immutability/undo, export coordinates,
  retention, archive rejection/round trips, adaptive selection and AppTest workflows.
- Existing Node viewer contract passes, including source binding and no pan/zoom reruns.
- Local Streamlit HTTP health endpoint returned `ok`.
- Real bounded checks used one bundled image reduced to 640 × 502: YOLO26n,
  YOLO26x and the first installed Keras classifier executed successfully.
- Faster R-CNN weights failed strict loading against the then-configured
  `fasterrcnn_resnet50_fpn_v2` architecture. This loading issue was corrected on
  September 30 as described above.
- Browser tooling reported **No browser is available**. Streamlit AppTest and server
  health were verified; rendered screenshot, mobile layout and browser interaction
  checks were not performed.
- No clinical accuracy, calibration, independent validation or controlled performance
  benchmark is claimed. The optional evaluation workflow requires suitable references.

Run the normal test suite and viewer contract from the project directory:

```powershell
python -m pytest tests -q
node tests/viewer_contract.cjs
```

`python scripts/verify_workspace.py` explicitly runs the bounded real-model checks and
writes `.qa/advanced_model_checks.json`. It never runs on import or downloads weights.
Start the app with `run_app.bat` or `python -m streamlit run app.py` from this directory.
