# Model contracts and provenance

The six `.keras` files in `keras/` are byte-for-byte copies of the user's 2026 models in
`pages_model/`. Each model has a sibling JSON contract. Class order and raw
0–255 float32 preprocessing are inherited from `pages/03_Parasitic_Vision.py`;
three sigmoid output activations were verified by inspecting each saved model.
No training code, class-map artifact, calibration report, clinical validation,
or redistribution license was supplied. Validate class order and preprocessing
against the training pipeline before clinical or external use.

```json
{
  "schema_version": 1,
  "labels": ["artifact", "opisthorchis viverrini egg", "minute intestinal fluke egg"],
  "preprocessing": "raw_0_255",
  "output": "sigmoid_scores"
}
```

Supported preprocessing: `raw_0_255` or `scale_0_1`. Supported outputs:
`sigmoid_scores` (independent scores normalized for ensemble only),
`probabilities` (sum must be approximately one), or `logits` (softmax; binary
single-logit output uses sigmoid). Multilabel decision rules are not implemented.
The UI always exposes raw per-model scores and calls ensemble values relative
scores. Very small sigmoid outputs can become large relative scores after
normalization; inspect raw scores and do not interpret the ranking as confidence.

Models must accept one channels-last batch of RGB or grayscale images with fixed
spatial dimensions and return one classification vector. Unknown/custom layers,
dynamic image dimensions, multi-input, and multi-output models fail explicitly.
Only locally administered trusted models are loaded; uploads cannot contain models.
Keras loads with `compile=False, safe_mode=True`; no arbitrary custom objects or
unsafe Lambda deserialization are enabled. Bounded resource caches use the file
mtime and size for invalidation; models carry SHA-256 hashes in reports. Restart
after replacing weights while preserving both mtime and size.

YOLO choices use `yolo/weights/yolo26n.pt` and `yolo/weights/yolo26x.pt`
with `requirements-yolo.txt`. Classes are read from the selected checkpoint;
`settings.py` maps explicit placeholder names without remapping unrelated class IDs.
Faster R-CNN is optional: use `rcnn/weights/parasite_fasterrcnn.pth`, matching
`rcnn/model.json`, and `requirements-rcnn.txt`. Each family has its own manifest,
loader and README. The selected model runs alone; no weights are downloaded
during inference. Both adapters provide full-image boxes, class counts,
annotation and JSON export. Keras alone performs center-region classification.
