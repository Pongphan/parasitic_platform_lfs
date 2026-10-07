# Refactor handoff

## Follow-up: page directory relocation

All five scripts formerly under `app_pages/` now reside directly in `pages/`.
`app.py`, the Home/Atlas links and the tests use the new paths. The old folder
was removed after clearing its generated Python cache. The `parasites/` and
`parasites_quiz/` content folders remain alongside the scripts.

The application retains `st.navigation(position="hidden")` and shared card
navigation. The test fixture compensates for Streamlit 1.60 AppTest resetting
legacy discovery between runs; five added route tests assert the shared shell
survives reruns. All 33 Python tests, the JavaScript viewer contract test and
Python compilation pass after the move. The diff artifact below records the
earlier model/viewer refactor; it is a historical snapshot, not the relocation.

## Changes by page

| Page | Change |
|---|---|
| Home | Five navigation buttons keep distinct teal, sage, coral, lavender and blue hues. The Atlas action uses pale ochre, a sixth hue. Dark text, focus outlines and active borders preserve readability. Counts now show 9 entries, 27 questions, 6 Keras models and 8 samples. |
| Parasite Atlas | Same distinct navigation hues and a separate pale-ochre practice action. Added Necator americanus, Ancylostoma ceylanicum, Taenia spp., Fasciolopsis buski and Strongyloides stercoralis. Each has an original labeled SVG schematic, biology, life cycle, clinical context, references and classification metadata. |
| Examination | Five corresponding quiz files add 15 questions, for 27 total. Existing discovery, scoring, explanations, retry and Atlas handoff work without duplicated page logic. |
| Parasite Detector | Restored the 2026 pan/zoom/center-cell Calculate component, removed pixel-bound sliders and the old analysis-method bar, moved all Keras assets/contracts, added drop-in YOLO and Faster R-CNN interfaces, and matched Majority vote to Analysis results with the same native subheader element. |

New reference entries do not add outputs to a trained classifier. `classifier_labels`
is empty for unsupported entries; the OV mapping alone points to an existing
species-specific Keras class. Taenia remains a group-level entry because eggs
cannot resolve its species. Hookworm entries likewise explain that eggs overlap.
Thailand prioritization is educational, not a claim about current national
prevalence. Relevant sources include the [Thai hookworm study](https://pmc.ncbi.nlm.nih.gov/articles/PMC3916468/),
[Thai fasciolopsiasis report](https://pubmed.ncbi.nlm.nih.gov/12466749/), and each
entry's CDC DPDx reference.

## Code deliverable

`docs/refactor.patch` contains a unified diff for every changed/new/removed text
file, with `--- a/<path>` and `+++ b/<path>` labels. It is relative to the project
directory and compares against the exact on-disk state before this refactor,
not a Git commit. `docs/changed_files.json` is the machine-readable inventory.
All updated files are already applied in the project; do not apply the patch a
second time. Six binary model moves are recorded in `docs/model_moves.json` with
SHA-256 hashes; binary weights are not reproduced as text in the patch.

## Model folders

```text
component_ai/
├── keras/
│   ├── __init__.py
│   ├── README.md
│   ├── img_classified_dataset1_cnn.keras
│   ├── img_classified_dataset1_cnn.json
│   ├── img_classified_dataset1_paca.keras
│   ├── img_classified_dataset1_paca.json
│   ├── img_classified_dataset2_cnn.keras
│   ├── img_classified_dataset2_cnn.json
│   ├── img_classified_dataset2_paca.keras
│   ├── img_classified_dataset2_paca.json
│   ├── img_classified_transf12_cnn.keras
│   ├── img_classified_transf12_cnn.json
│   ├── img_classified_transf12_paca.keras
│   └── img_classified_transf12_paca.json
├── yolo/
│   ├── __init__.py
│   ├── service.py
│   ├── model.json
│   ├── README.md
│   └── weights/
│       ├── PLACE_WEIGHTS_HERE.txt
│       └── parasite_yolo11.pt          [expected future file, not supplied]
└── rcnn/
    ├── __init__.py
    ├── model.json
    ├── README.md
    └── weights/
        ├── PLACE_WEIGHTS_HERE.txt
        └── parasite_fasterrcnn.pth     [expected future file, not supplied]
```

YOLO accepts a trained Ultralytics object-detection `.pt` checkpoint and uses its
embedded labels. Faster R-CNN accepts a torchvision ResNet50-FPN v1/v2 state dict
(bare or inside `model_state_dict`/`state_dict`). Match its architecture, labels,
resize parameters and head size in `model.json`; background is class zero. Other
architectures are not interchangeable checkpoints. Dropping compatible weights
at the manifest path requires no Python changes. No empty `.pt`/`.pth` files or
fake predictions are provided: placeholders are clearly named text files.

## Dependencies

Base/Keras/YOLO dependencies are unchanged. Add `requirements-rcnn.txt` for
`torch>=2.6,<3` and `torchvision>=0.21,<1` using a compatible release pair.
`constraints-tested.txt` records the installed pair (2.12.0 / 0.27.0). This refactor
did not install or upgrade the user's environment. The reused viewer needs only
Streamlit and Pillow already present. Node is optional for the JavaScript contract
test, not an application runtime dependency.

## Detector verification

| Requested fix | Verification performed | Limit |
|---|---|---|
| a. YOLO scaffold | Manifest/path tests, missing-weight UI disables Detect objects; existing RGB/box adapter test passes. | No trained parasite YOLO weights were supplied. |
| b. Faster R-CNN scaffold | Safe loader arguments/no pretrained download/strict state loading tested with fixtures. Actual Torch tensors and torchvision NMS tested for RGB scaling, thresholds, clipping and class labels. Missing-weight UI verified. | No trained Faster R-CNN checkpoint was supplied. |
| c. Keras relocation | All six model hashes match original assets; discovery and contracts resolve `keras/`; all six ran inference on a real sample crop with zero errors. | Execution is not clinical accuracy validation. |
| d. Remove region bar | AppTest confirms no pixel sliders in Keras mode. Removed old segmented method control; the model-family dropdown distinguishes classification from full-image detectors. | The pan/zoom controls inside the requested 2026 viewer remain intentionally. |
| e. Interactive selection | Reused HTML/JS and crop helper; Node contract test simulates drag, wheel/button zoom, Calculate, image binding and no pan/zoom inference. Python tests verify matching crop coordinates, invalid-event rejection, duplicate-token suppression and smaller crops when zoomed. | Browser automation had no available browser; no rendered drag or visual screenshot test is claimed. |
| f. Font consistency | Both Analysis results and Majority vote use `st.subheader`; AppTest asserts both subheader elements. | Rendered font appearance was not visually inspected. |

28 Python tests passed; the Node viewer contract test and Python compilation
passed. HTTP `/_stcore/health` returned `ok` on a temporary local verification
server. That server was stopped after checks. The 2026 source project was not
edited. No deployment or clinical validation was performed.
