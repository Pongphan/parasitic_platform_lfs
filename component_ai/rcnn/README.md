# Faster R-CNN checkpoint contract

Install `requirements-rcnn.txt`. The installed checkpoint at
`weights/parasite_fasterrcnn.pth` matches a ResNet50-FPN v1 detector with a
FrozenBatchNorm2d backbone and four output classes, including background.
`model.json` explicitly selects `fasterrcnn_resnet50_fpn` and
`backbone_norm: "frozen_batch_norm2d"`. The previous v2 configuration could not
load its FPN, RPN and fc6/fc7 box-head weights.

Supported architectures are torchvision `fasterrcnn_resnet50_fpn` and
`fasterrcnn_resnet50_fpn_v2`. Set labels in the exact training order, including
`__background__` at index zero. Save with `torch.save(model.state_dict(), path)`
or `torch.save({'model_state_dict': model.state_dict()}, path)`. A `state_dict`
wrapper is also accepted. The network architecture, head class count, and
manifest must match. Arbitrary backbones/full pickled modules/TorchScript files
are not interchangeable; they need their own adapter.

The frozen v1 path constructs `resnet_fpn_backbone` with `weights=None` and
`FrozenBatchNorm2d`, then wraps it in `FasterRCNN`. Using the standard v1 builder
with both pretrained weights disabled would select regular BatchNorm2d instead.
The installed checkpoint has exactly 295 matching state entries; no BatchNorm
counters are synthesized and no weights are dropped. Other supported manifests
use `backbone_norm: "batch_norm2d"` (also the default when omitted for backward
compatibility) and the standard builder with `weights=None, weights_backbone=None`.
Frozen normalization is supported only with the v1 architecture.

All paths use `torch.load(..., weights_only=True, map_location='cpu')`, strict
loading and eval mode. No pretrained weights are downloaded. PIL RGB is
converted to CHW float32 in [0,1]; torchvision performs its own normalization and
resizing, and returns boxes in original image coordinates. Inference runs on CPU
under `torch.inference_mode()` and a resource lock. This is portable; GPU support
can be added deliberately once the deployment target is known.

`load_rcnn_model(path, version, contract_json)` returns `(model, lock, sha256)`.
`run_rcnn_inference(model, image, labels, confidence, iou_threshold=0.45)` returns
the same normalized report/image structure as the YOLO adapter, with class-aware
NMS. The manifest records resize and maximum-detection settings for reproducibility.

September 30, 2026 verification: the unchanged checkpoint loaded strictly and ran
on `Artificial Mix OV MIF_001.tif`, reduced to 640 x 502, at confidence 0.7.
Single-image inference and the batch queue completed with the same three detections.
Checkpoint SHA-256: `18b0d8a034ae17d76fd5cae13608e26f9711b05d147cd34e2d5524b86bbd067d`.
The original class mapping, resize settings and weights were retained. State-dict
compatibility does not establish training provenance or label meanings. The frozen
normalization uses torchvision's default epsilon of 1e-5; the original training
epsilon is not stored in the checkpoint. This is an execution check, not an
accuracy or calibration result.

Regression coverage in `tests/test_backends.py` checks the installed checkpoint's
exact state keys/shapes, both standard architectures, explicit frozen normalization,
safe strict loading and invalid normalization configurations.
