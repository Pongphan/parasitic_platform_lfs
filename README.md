# Parasitic Platform 2027

GitHub repository: `parasitic_platform_lfs`.

All **50 Atlas entries** now include a local schematic in **Morphology & images**:
41 new stage-specific SVG diagrams complement the nine existing illustrations.
New diagrams include feature labels and identification limits; reference microscopy
links remain available. See [Atlas schematic coverage](docs/ATLAS_SCHEMATICS.md).

## Usability update — October 1, 2026

- Home starts with direct Atlas, image analysis, and practice actions. Coverage
  charts group the collection and provide searchable entry details.
- Every page has **Session tools · export and restore**. Prepared archives show
  their timestamp; edits invalidate downloads until the archive is prepared again.
  Local and global export controls share image inclusion and the same snapshot.
  Downloads are disabled while a batch is running. A download request is recorded,
  but users should check their browser to confirm the file was saved.
- **Review this analysis** opens the exact retained result. Review starts with an
  unreviewed region, uses Region 01 labels, shows a source highlight and crop,
  and supports **Save and next**. Original predictions remain unchanged.
- Detector modes describe their actions; model labels include both public and
  technical names. The viewer has **Analyze selected region** and **Fit image**.
  Moving, zooming, and fitting the image do not trigger inference.
- Batch, annotation, and evaluation exports detect changes to their relevant
  inputs. Failed reevaluation does not leave an earlier report looking current.
- Atlas comparisons show local schematics alongside aligned morphology details
  and an explicit scale caveat. **Clear all filters** restores the complete list.
- Mixed/adaptive practice displays five questions per page, answered progress,
  a question navigator, and a jump to unanswered questions. Answers and confidence
  ratings survive navigation and portable session restoration.
- Compact page headers and responsive controls reduce space above the task.
  About presents current capabilities first and preserves the 2026 narrative
  in its project history and research blueprint section.

Session ZIPs contain analyses, reviews, bookmarks, learning lists, completed
practice, and the unfinished adaptive quiz. Source images remain opt-in;
species-practice drafts and live batch queues are not included.
Behavior is covered by Streamlit AppTest and the viewer's Node contract test.
Rendered browser and mobile visual verification was unavailable in this session.

## Advanced workspace update — September 19, 2026

The Detector now includes an **Advanced workspace** with sequential batch analysis,
same-image model comparisons, retained analysis history, object review and box editing,
COCO/YOLO annotation exports, optional ground-truth evaluation, and validated session
ZIP import/export. Examination adds mixed and adaptive practice; Atlas adds bookmarks,
learning lists and guided pathways. The existing five pages and manual viewer remain.

See [Advanced workspace guide, schemas, limits and verification](docs/ADVANCED_WORKSPACE.md)
for the feature matrix and complete walkthrough. No runtime dependencies were added.

Current model checks: both YOLO checkpoints and one Keras classifier execute on a
bounded bundled sample. **Faster R-CNN loading was fixed on September 30, 2026** by
selecting the checkpoint-compatible ResNet50-FPN v1 architecture and explicitly
constructing its FrozenBatchNorm2d backbone. All 295 state entries match; strict
loading remains enabled. The unchanged checkpoint passed single-image and batch
inference on a 640 x 502 sample. Existing labels and preprocessing were retained.
Earlier statements below about missing or incompatible Faster R-CNN weights are
historical. See the [Faster R-CNN contract and verification](component_ai/rcnn/README.md).

Session data is transient unless explicitly exported. Source images are excluded from
session archives by default. Reviewed annotations are not independent ground truth.
Rendered browser verification was unavailable; automated UI and server health checks
are documented in the guide.

Latest update: the Atlas now contains **50 species and reference groups**, with
consistent clinical/microscopy fields, six categories, combined search filters,
reference cards, JSON exports and matching Detector links. The collection has
68 practice questions, and supports future Thai translations through data fields.
See [Atlas changes and content schema](docs/ATLAS_EXPANSION.md).

Detector confidence defaults to **0.7**, all detected crops appear in a
responsive gallery, and numbered overlays use consistent parasite names.
Added review notes, CSV export, source-backed comparison downloads and shared
page styling. See [requirement-by-requirement changelog](docs/DETECTOR_REFINEMENT.md).
Atlas update verification: 60 Python tests passed. The earlier detector update
also verified the viewer contract, both YOLO checkpoints and all six Keras models.
Faster R-CNN subsequently passed the checkpoint checks described above.

A modular Streamlit learning and microscopy application with five pages,
shared card navigation directly below the title, and no sidebar. Sage, coral,
and muted teal surfaces use dark text and a centralized native theme plus CSS.

The refactor restores the 2026 pan/zoom/Calculate viewer and separates Keras,
YOLO and Faster R-CNN assets. The original nine-entry reference collection has
been expanded; earlier refactor notes below describe the historical baseline.
See [page-by-page changes and verification](docs/REFACTOR_NOTES.md) and the
[complete file-labeled code diff](docs/refactor.patch).

## Run locally

On this machine, double-click **run_app.bat**. It prefers a project `.venv`, then
the existing `C:\Users\Mufha\anaconda3\envs\penv` environment, then the Python launcher.
No server is started merely by importing the Python modules.

For a clean installation, use Python 3.13 and run from this directory:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-ai.txt -c constraints-tested.txt
.venv\Scripts\python -m streamlit run app.py
```

`requirements.txt` alone supports the learning pages and detector UI without
TensorFlow. `requirements-ai.txt` enables Keras; `requirements-yolo.txt` enables
the optional YOLO path; `requirements-rcnn.txt` enables Faster R-CNN. Six real
Keras models and eight real TIFF samples were copied from the 2026 project.
The current local YOLO files expose class_0, class_1 and class_2. Display aliases
map class_1 to Opisthorchis viverrini egg and class_2 to Minute intestinal fluke
egg. Class_0 remains unchanged. Checkpoint filenames do not establish training
provenance or architecture. Faster R-CNN disables inference until its expected
weights are installed.

Always launch from this directory so Streamlit loads `.streamlit/config.toml`
and its relative `component_theme/theme.toml`. All data/model paths are resolved
from source files and do not depend on the working directory.

## Implemented tree

```text
parasitic_platform_2027/
├── app.py                         # Router and shared page frame
├── content.py                     # Content discovery, validation, grading
├── run_app.bat
├── requirements.txt
├── requirements-ai.txt
├── requirements-yolo.txt
├── requirements-rcnn.txt
├── requirements-dev.txt
├── constraints-tested.txt
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .streamlit/config.toml
├── component_layout/
│   ├── __init__.py                # Header, reusable card navigation, hero, footer
│   ├── detector.py                # Detector UI and session/report lifecycle
│   ├── viewer.py                  # Validated 2026 viewer adapter
│   └── viewer_component/{__init__.py,index.html,viewer.css}
├── component_theme/
│   ├── __init__.py                # Theme application and chart tokens
│   ├── theme.toml                 # Native widgets, palette and typography
│   └── styles.css                 # Responsive cards, page shell, no-sidebar guard
├── component_ai/
│   ├── __init__.py
│   ├── images.py                  # Decode limits and source-coordinate crops
│   ├── models.py                  # Cached loading, preprocessing and ensemble
│   ├── roi.py                     # Original center-cell coordinate mapping
│   ├── detection.py               # Validated YOLO / RCNN manifests
│   ├── README.md
│   ├── keras/
│   │   ├── __init__.py
│   │   ├── README.md
│   │   └── [6 unchanged .keras weights + 6 sibling JSON contracts]
│   ├── yolo/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   ├── model.json
│   │   ├── README.md
│   │   └── weights/PLACE_WEIGHTS_HERE.txt
│   └── rcnn/
│       ├── __init__.py
│       ├── model.json
│       ├── README.md
│       └── weights/PLACE_WEIGHTS_HERE.txt
├── component_aiimage/
│   ├── README.md
│   └── [8 TIFF microscopy images]
├── pages/                         # Page scripts and species content
│   ├── home.py
│   ├── atlas.py
│   ├── detector.py
│   ├── examination.py
│   ├── about.py
│   ├── parasites/
│   │   ├── opisthorchis_viverrini/{content.json,morphology.svg}
│   │   ├── ascaris_lumbricoides/{content.json,morphology.svg}
│   │   ├── giardia_duodenalis/{content.json,morphology.svg}
│   │   ├── necator_americanus/{content.json,morphology.svg}
│   │   ├── ancylostoma_ceylanicum/{content.json,morphology.svg}
│   │   ├── taenia_spp/{content.json,morphology.svg}
│   │   ├── fasciolopsis_buski/{content.json,morphology.svg}
│   │   ├── strongyloides_stercoralis/{content.json,morphology.svg}
│   │   └── trichuris_trichiura/{content.json,morphology.svg}
│   └── parasites_quiz/
│       ├── opisthorchis_viverrini/quiz.json
│       ├── ascaris_lumbricoides/quiz.json
│       ├── giardia_duodenalis/quiz.json
│       ├── necator_americanus/quiz.json
│       ├── ancylostoma_ceylanicum/quiz.json
│       ├── taenia_spp/quiz.json
│       ├── fasciolopsis_buski/quiz.json
│       ├── strongyloides_stercoralis/quiz.json
│       └── trichuris_trichiura/quiz.json
├── scripts/seed_content.py         # Rebuild original bundled JSON/illustrations
├── scripts/expand_content.py       # Add new entries without overwriting content
├── docs/CONTENT_TEMPLATES.md
├── docs/REFACTOR_NOTES.md
├── docs/refactor.patch
└── tests/
    ├── conftest.py
    ├── test_app.py
    ├── test_content.py
    ├── test_inference.py
    ├── test_backends.py
    └── viewer_contract.cjs
```

`st.navigation(position="hidden")` registers pages explicitly and disables legacy
automatic `pages/` routing. All five executable scripts are in `pages/`, alongside
the `parasites/` and `parasites_quiz/` content folders. Each route is registered
explicitly by `app.py`, which renders
the header/navigation and footer once per run. Native buttons retain keyboard
interaction; CSS adds hover, focus, active-page and mobile states. See the
[Streamlit navigation documentation](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation).

## Detector migration

The source was `../parasitic_platform_2026/pages/03_Parasitic_Vision.py` and its
`pages_components/component_models.py`, `component_sampleimages.py`, and
`component_yolo.py` helpers. The Keras pipeline remains crop → RGB resize →
float32 → predict → per-model scores → normalized mean and majority vote.
Raw 0–255 input and Pillow bicubic resizing preserve the legacy preprocessing.

The 2026 interactive viewer and center-grid crop mapping are now reused directly.
Drag the image to pan, use wheel/buttons/keyboard to zoom, align a target with the
center box, then click Analyze selected region. Fit image resets zoom and position
without running inference. There are no horizontal/vertical crop sliders
or region-method selection bar. The Detection mode segmented control offers exactly
Classify selected region (Keras only) and Find objects in whole image. For the latter,
choose yolo26n, yolo26x, or Faster R-CNN. Each analyzes the full image
independently; the report records the selected model and its actual class names.
The existing v1 iframe protocol is retained
to match the explicitly requested 2026 component rather than replacing its
interaction model. No additional browser component library is required.

Each analysis click uses the existing `calculate` event with an image identity and unique token. The adapter
rejects stale/invalid events and entirely off-image regions. A repeated token
does not run inference twice. Viewer movements stay in the browser; displayed
results are labeled snapshots of the last analyzed selection, and the viewer
indicates when a new analysis is needed. The legacy fixed center cell is
preserved: this is not a freehand or resizable rectangle selection tool.

Changes include lazy TensorFlow imports, safe inference-only loading, bounded
version-aware caches, per-model locks, strict class/input/output contracts,
independent failure handling, explicit vote ties, SHA-256 model/image provenance,
and JSON reports. Image source selection prevents an existing upload from
silently overriding a sample. Changing the calculated crop, image, selected
models, contracts, weights, mode or confidence threshold invalidates results.

The YOLO implementation preserves existing detection and annotation logic.
It now passes a PIL RGB image to Ultralytics: numpy image sources are interpreted
as BGR, which could reverse channels in the old code. Both installed YOLO26
variants have passed real inference checks. Faster R-CNN supports
torchvision ResNet50-FPN v1/v2 state dictionaries with a matching class manifest,
strict safe loading, CPU inference, class-aware NMS, annotation and JSON export.
No weights are downloaded during app inference. Auto detection requires only
the selected checkpoint; setup guidance identifies a missing file.

## Content and scope

Nine Atlas entries (including a Taenia species group) contain descriptions, morphology, four-step life cycles,
clinical context, original schematic SVGs, and CDC source links. These schematic
images are explicitly labeled, not to scale, and are not diagnostic photographs.
Each entry links to the CDC microscopy gallery. Twenty-seven questions provide
explanations, unanswered checks, scoring, review, retry, and JSON downloads.
Attempts persist across page navigation within one browser session, not after
server restart or browser-session loss.

Home metrics and charts are derived from the actual local collection. They
represent content coverage, not prevalence, dataset ground truth, or model accuracy.
The Keras classifier covers artifact/OV egg/MIF egg only, independent of the
larger Atlas. See [content templates](docs/CONTENT_TEMPLATES.md) to add species.

## Verification

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python -m compileall -q app.py pages component_ai component_layout component_theme content.py
node tests/viewer_contract.cjs
```

Tests cover all five navigation routes, Atlas search and quiz handoff, quiz
submission/review/retry, missing inputs/weights, schema checks, preprocessing,
non-finite/mismatched predictions, sigmoid normalization, ties, crop and decode
limits, result invalidation, and YOLO RGB input/box extraction with a fake model.
The six supplied Keras models were also loaded and run against a real local
sample with TensorFlow 2.21.0; this verifies execution, not diagnostic accuracy.
After relocating page scripts into `pages/`, 33 Python tests and the Node viewer
contract test passed. AppTest setup preserves explicit navigation across reruns
to compensate for Streamlit 1.60 resetting legacy discovery in its test runner.
The
Streamlit HTTP health check passed. Browser automation reported no available
browser, so no rendered screenshot/visual verification is claimed. Trained
YOLO/Faster R-CNN inference remains unverified until compatible weights arrive.

## Deployment

The included Dockerfile runs as a non-root user and provides a Streamlit health
check. Build and run locally with:

```sh
docker build -t parasitic-platform-2027 .
docker run --rm -p 8501:8501 parasitic-platform-2027
```

The Docker image itself has not been built in this workspace. For a network
deployment, configure your organization’s access control and HTTPS proxy;
the app does not implement user accounts or a patient database. Keep Streamlit's
default XSRF and CORS protections. Models are shared read-only cached resources;
uploads and results are session data. No external inference API is called and
application code does not intentionally persist uploads. Each upload is bounded
to 25 MB / 24 megapixels. Size concurrent workers for decoded image and model memory.

This is an educational/research implementation, not a clinically validated
medical device. Model calibration, training provenance, and independent clinical
validation were not supplied. Establish those before clinical use, and establish
redistribution rights for the inherited models/samples before publishing them.
