"""Deterministic one-to-one detection matching and strict COCO-box evaluation."""
from collections import Counter
from copy import deepcopy
import math
import re
from component_ai.pipeline import overlap
from workspace import validate_box, digest, json_bytes


def match_boxes(predictions, references, threshold=0.5):
    """Confidence-ordered greedy matching; same exact label, best unused IoU."""
    if not 0 < threshold <= 1:
        raise ValueError("IoU threshold must be above zero and at most one.")
    unused = set(range(len(references)))
    matches, unmatched = [], []
    for pi in sorted(range(len(predictions)), key=lambda i: (-predictions[i].get("confidence", 1), i)):
        p = predictions[pi]
        candidates = [(overlap(p["bbox_xyxy"], references[ri]["bbox_xyxy"]), ri)
                      for ri in sorted(unused) if p["class_name"] == references[ri]["class_name"]]
        best = max(candidates, key=lambda pair: (pair[0], -pair[1]), default=(0, -1))
        if best[0] >= threshold:
            matches.append({"prediction": pi, "reference": best[1], "iou": best[0]})
            unused.remove(best[1])
        else:
            unmatched.append(pi)
    return {"matches": matches, "unmatched_predictions": unmatched, "unmatched_references": sorted(unused)}


def validate_coco(data):
    if not isinstance(data, dict) or any(not isinstance(data.get(k), list) for k in ("images", "annotations", "categories")):
        raise ValueError("COCO requires images, annotations and categories arrays.")
    if not isinstance(data.get("info", {}), dict):
        raise ValueError("COCO info must be an object when supplied.")
    if len(data["images"]) > 200 or len(data["annotations"]) > 20000 or len(data["categories"]) > 500:
        raise ValueError("COCO exceeds 200 images, 20,000 boxes, or 500 categories.")
    def index(items, kind):
        result = {}
        for item in items:
            if not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] in result:
                raise ValueError(f"Duplicate or invalid {kind} identifier.")
            result[item["id"]] = item
        return result
    images = index(data["images"], "image")
    categories = index(data["categories"], "category")
    annotations = index(data["annotations"], "annotation")
    names = set()
    for category in categories.values():
        name = category.get("name")
        if not isinstance(name, str) or not name.strip() or name in names or len(name) > 200:
            raise ValueError("Category names must be unique nonempty strings.")
        names.add(name)
    identities = set()
    for image in images.values():
        if any(type(image.get(k)) is not int or image[k] <= 0 for k in ("width", "height")):
            raise ValueError("Invalid reference image dimensions.")
        if image["width"] * image["height"] > 24000000:
            raise ValueError("Reference image exceeds 24 megapixels.")
        if not isinstance(image.get("file_name"), str) or not image["file_name"]:
            raise ValueError("Reference images require file_name.")
        if image.get("sha256") is not None and (not isinstance(image["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", image["sha256"])):
            raise ValueError("Reference SHA-256 must be 64 lowercase hexadecimal characters.")
        identity = image.get("sha256") or image["file_name"]
        if identity in identities:
            raise ValueError("Duplicate reference image identity.")
        identities.add(identity)
    for ann in annotations.values():
        if type(ann.get("image_id")) is not int or type(ann.get("category_id")) is not int:
            raise ValueError("Annotation image/category IDs must be integers.")
        if ann.get("image_id") not in images or ann.get("category_id") not in categories:
            raise ValueError("Annotation references an unknown image/category.")
        if ann.get("iscrowd", 0) != 0 or ann.get("ignore", 0) or ann.get("segmentation") or ann.get("keypoints"):
            raise ValueError("Only non-crowd, non-ignored bounding boxes are supported; remove segmentation/keypoints.")
        box = ann.get("bbox")
        if not isinstance(box, list) or len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in box):
            raise ValueError("Invalid COCO [x, y, width, height] box.")
        x, y, w, h = box
        image = images[ann["image_id"]]
        validate_box([x, y, x+w, y+h], image["width"], image["height"])
    return images, categories, annotations


def evaluate(records, data, mapping, confidence=0.7, iou=0.5):
    if not 0 <= confidence <= 1:
        raise ValueError("Confidence must be between zero and one.")
    images, categories, annotations = validate_coco(data)
    if set(mapping) != {c["name"] for c in categories.values()} or any(not isinstance(v, str) or not v.strip() for v in mapping.values()):
        raise ValueError("Explicitly map every reference category to a prediction label.")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Category mapping must be one-to-one.")
    configurations = {json_bytes(r["configuration"]) for r in records}
    model_hashes = {json_bytes(r["model_sha256"]) for r in records}
    if len(configurations) > 1 or len(model_hashes) > 1:
        raise ValueError("Evaluate one model and configuration at a time.")
    hashes = [r["image"]["sha256"] for r in records]
    if len(set(hashes)) != len(hashes):
        raise ValueError("Select only one analysis per source image.")
    totals, results, excluded, used = {}, [], [], set()
    for record in records:
        if record["mode"] == "keras" or record["status"] != "completed":
            excluded.append({"analysis_id": record["analysis_id"], "reason": "Not a completed detector analysis"})
            continue
        source = record["image"]
        candidates = [im for im in images.values() if
                      (im.get("sha256") == source["sha256"] if im.get("sha256") else im["file_name"] == source["name"])]
        if len(candidates) > 1:
            raise ValueError("Ambiguous image match; provide SHA-256 identities.")
        if not candidates:
            excluded.append({"analysis_id": record["analysis_id"], "reason": "Missing reference image: unknown, not negative"})
            continue
        target = candidates[0]
        if (source["width"], source["height"]) != (target["width"], target["height"]):
            raise ValueError("Reference image dimensions differ from the analyzed image.")
        used.add(target["id"])
        refs = []
        for ann in annotations.values():
            if ann["image_id"] == target["id"]:
                x, y, w, h = ann["bbox"]
                refs.append({"class_name": mapping[categories[ann["category_id"]]["name"]], "bbox_xyxy": [x,y,x+w,y+h], "annotation_id": ann["id"]})
        preds = [deepcopy(d) for d in record["original"].get("detections", []) if d["confidence"] >= confidence]
        matched = match_boxes(preds, refs, iou)
        tp = Counter(preds[m["prediction"]]["class_name"] for m in matched["matches"])
        fp = Counter(preds[i]["class_name"] for i in matched["unmatched_predictions"])
        fn = Counter(refs[i]["class_name"] for i in matched["unmatched_references"])
        for label in set(mapping.values()) | set(tp) | set(fp) | set(fn):
            row = totals.setdefault(label, {"tp": 0, "fp": 0, "fn": 0})
            row["tp"] += tp[label]; row["fp"] += fp[label]; row["fn"] += fn[label]
        results.append({"analysis_id": record["analysis_id"], "image_id": target["id"], "predictions": preds,
                        "references": refs, "identity_method": "sha256" if target.get("sha256") else "exact filename and dimensions", **matched})
    def scores(row):
        tp, fp, fn = row["tp"], row["fp"], row["fn"]
        return {**row, "precision": tp/(tp+fp) if tp+fp else None,
                "recall": tp/(tp+fn) if tp+fn else None, "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
    total = {k: sum(r[k] for r in totals.values()) for k in ("tp", "fp", "fn")}
    return {"schema_version": "2027.2", "dataset_sha256": digest(json_bytes(data)),
            "reference_origin": data.get("info", {}).get("origin", "user_supplied; independence unverified"),
            "policy": "Confidence-ordered greedy same-label matching, best unused IoU; listed empty images are negatives; absent images excluded.",
            "confidence": confidence, "iou": iou, "category_mapping": mapping,
            "provenance": [{k: r[k] for k in ("analysis_id", "image", "configuration", "model_sha256")} for r in records],
            "overall": scores(total), "per_class": {k: scores(v) for k,v in totals.items()},
            "images": results, "excluded": excluded, "unmatched_reference_images": sorted(set(images)-used)}
