# Home and detector update

## Diagnosis

The reported message refers to the old `component_ai/` location and is absent
from the current executable source. Before this update, on-disk discovery already
resolved `component_ai/keras/` and all six models and six matching contracts were
present. Discovery succeeded after changing the working directory to the system
temporary directory. All six real models also completed inference successfully.

The reported failure could not be reproduced in this copy. An older running
server, stale imported module, or another checkout is the likely explanation;
the active server behind the user's browser was not identified or restarted.
Restart that server from this project's `app.py` (or use `run_app.bat`) to load
the current code. No trained models were replaced and no contracts were guessed.

Discovery now resolves the directory on each call, recognizes extension case,
checks actual files, and validates contracts before populating the model selector.
The Model availability expander reports the full resolved path, discovered/ready
counts and precise contract errors, distinguishing absent files from malformed
metadata. UTF-8 JSON with a Windows byte-order mark is accepted.

## Home charts — pages/home.py

```python
from component_layout.dashboard import render_collection_charts, render_activity

# The existing taxonomy chart remains; add real local collection summaries.
render_collection_charts(entries)
# Starts with an honest empty state until this session produces analysis results.
render_activity()
```

`component_layout/dashboard.py` adds question counts per species and model file
sizes colored by contract availability. Session charts show analysis counts by
family/outcome and a UTC activity timeline. Metrics separate classified crops
from object detections: one crop is not counted as one detected parasite.
Only the latest 200 report-producing runs in the current session are retained,
without image bytes or filenames. No prevalence, accuracy or historical usage
is invented. Model size is explicitly labeled as file size, not performance.

## Model discovery — component_ai/models.py

```python
MODEL_DIR = Path(__file__).resolve().parent / "keras"

def discover_models(root=None):
    folder = Path(root).resolve() if root is not None else Path(__file__).resolve().parent / "keras"
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() == ".keras")
```

For `name.keras`, the required contract is `name.json` in the same folder:

```json
{
  "schema_version": 1,
  "labels": ["artifact", "opisthorchis viverrini egg", "minute intestinal fluke egg"],
  "preprocessing": "raw_0_255",
  "output": "sigmoid_scores"
}
```

Labels must match training order, with unique nonempty names. Supported
preprocessing is `raw_0_255` or `scale_0_1`; supported output contracts are
`sigmoid_scores`, `probabilities` or `logits`. The supplied six models retain raw
0–255 inputs and sigmoid-score outputs. Discovery validates JSON only; actual
network input/output shapes are checked during inference. Loading remains lazy,
cached and inference-only (`compile=False`, `safe_mode=True`).

## Detector cleanup — component_layout/detector.py

```python
inventory = model_inventory()
paths = [item["path"] for item in inventory if item["error"] is None]
chosen = st.multiselect(
    "Classification models", paths, default=paths[:1],
    format_func=lambda p: p.stem.replace("img_classified_", ""),
    key="detector_models", persist_state="session",
)
```

There are no Horizontal/Vertical bounds sliders. The classifier selector is the
only region-classification choice. The model-family dropdown still permits the
separate full-image YOLO and Faster R-CNN workflows; it does not select ROI bounds.

## Interactive viewer — component_layout/viewer.py

```python
# The caller maintains viewer state and the current image's SHA-256 identity.
event = render_image_viewer(image, image_hash, st.session_state["viewer_state"])
if event is not None:
    box, state, token = selection_from_event(image, event, image_hash)
    # The detector checks token uniqueness before classifying this crop.
    crop = crop_image(image, box)
```

The existing 2026 HTML/canvas component is reused, including pointer capture,
drag, wheel, arrow-pad, zoom buttons, keyboard support and Calculate messages.
The 3×3 grid and center cell are fixed in viewport coordinates. Dragging pans
the image beneath them. Directional buttons shift the inspected source region
in the named direction by translating the image oppositely. Wheel and +/−
buttons zoom about the fixed ROI center, not the pointer location. No inference
is triggered while moving; Calculate commits the selected crop.

The browser-side rendering is necessarily canvas JavaScript, invoked through
the Python adapter above. In `viewer_component/viewer.css`:

```css
--grid-line: #ADD8E6;
--center-line: #FFB6C1;
--center-fill: #FFB6C11A;
```

The grid uses 2px lines; the center border uses 3px. The stylesheet URL is
versioned to avoid retaining the old green overlay in a cached iframe. In
`viewer_component/index.html`, wheel handling now uses the existing center-zoom
helper:

```javascript
function onWheel(e) {
  e.preventDefault();
  if (e.deltaY === 0) return;
  zoomAboutCenter(e.deltaY < 0 ? 1.08 : 1 / 1.08);
}
```

## Dependencies and checks

No new dependencies. Charts use existing Altair/pandas/Streamlit; the reused
viewer uses the existing custom iframe and Pillow image conversion. No
streamlit-drawable-canvas or image-coordinates library is introduced.

36 Python tests passed, Python compilation passed, and the Node viewer contract
test passed. Tests cover all page routes, new Home charts and session activity,
working-directory-independent discovery, BOM/malformed/missing contracts,
absence of crop sliders, mouse drag, off-center wheel events that still zoom
around the ROI center, all four direction buttons and both zoom controls.
All six real Keras models ran a real sample crop with zero errors. These are
execution/contract checks; rendered browser visuals were not verified.
