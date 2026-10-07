"""Bounded, data-only session workspace. No Streamlit or ML runtime dependency."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import uuid

SCHEMA = "2027.2"
MAX_RECORDS = 200
MAX_IMAGES_BYTES = 128 * 1024 * 1024
MAX_HISTORY = 2000
REVIEW_STATES = ("unreviewed", "accepted", "corrected", "rejected")


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def new_workspace():
    return {"schema_version": SCHEMA, "records": [], "images": {}, "comparisons": [],
            "question_history": [], "bookmarks": [], "learning_lists": {}, "active_quiz": None,
            "quiz_attempts": {}, "image_budget": MAX_IMAGES_BYTES, "record_limit": MAX_RECORDS}


def get_workspace(state):
    return state.setdefault("workspace", new_workspace())


def validate_box(box, width, height):
    if (not isinstance(box, (list, tuple)) or len(box) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)):
        raise ValueError("Box must contain four finite source-pixel coordinates.")
    x1, y1, x2, y2 = box
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError("Box must be nonempty and inside the original image.")
    return list(box)


def retain_image(ws, data, expected_hash=None):
    from component_ai.images import decode_image
    identity = digest(data)
    if expected_hash and identity != expected_hash:
        raise ValueError("Image SHA-256 does not match the original source.")
    image = decode_image(data)
    # Reserve both compressed bytes and potential decoded RGB storage.
    cost = len(data) + image.width * image.height * 3
    if cost > ws["image_budget"]:
        raise ValueError("Image exceeds the workspace memory budget.")
    ws["images"].pop(identity, None)
    ws["images"][identity] = {"data": data, "width": image.width, "height": image.height, "cost": cost}
    enforce_limits(ws)
    return identity, image


def enforce_limits(ws):
    ws["records"] = ws["records"][-ws["record_limit"]:]
    ws["question_history"] = ws["question_history"][-MAX_HISTORY:]
    ws["comparisons"] = ws["comparisons"][-100:]
    while sum(v["cost"] for v in ws["images"].values()) > ws["image_budget"]:
        del ws["images"][next(iter(ws["images"]))]
    while len(ws["images"]) > 200:
        del ws["images"][next(iter(ws["images"]))]


def analysis_record(report, width, height, elapsed=0.0, status=None, warnings=None):
    record = {"schema_version": SCHEMA, "analysis_id": uuid.uuid4().hex, "created_at": now(),
              "image": {"sha256": report["image_sha256"], "name": report.get("image_name", "image"),
                        "width": width, "height": height},
              "mode": report.get("configuration", {}).get("mode", "auto"),
              "configuration": deepcopy(report.get("configuration", {})),
              "model_sha256": deepcopy(report.get("model_sha256") or {
                  p["model"]: p["model_sha256"] for p in report.get("predictions", []) if p.get("model_sha256")}),
              "status": status or ("partial" if report.get("errors") else "completed"),
              "elapsed_seconds": elapsed, "warnings": warnings or [],
              "errors": deepcopy(report.get("errors", [])), "original": deepcopy(report),
              "review": {}, "review_undo": [], "notes": ""}
    if record["status"] == "partial" and not report.get("predictions"):
        record["status"] = "failed"
    for detection in report.get("detections", []):
        validate_box(detection["bbox_xyxy"], width, height)
    return record


def add_record(ws, record):
    ws["records"].append(record)
    enforce_limits(ws)
    return record


def find_record(ws, analysis_id):
    return next((r for r in ws["records"] if r["analysis_id"] == analysis_id), None)


def review_rows(record):
    rows = []
    for index, original in enumerate(record["original"].get("detections", [])):
        identity = str(index)
        edit = record["review"].get(identity, {})
        rows.append({"object_id": identity, "status": "unreviewed", "notes": "",
                     **deepcopy(original), **deepcopy(edit), "predicted_class": original["class_name"]})
    for identity, edit in record["review"].items():
        if identity.startswith("manual_"):
            rows.append({"object_id": identity, "predicted_class": "Manually added", **deepcopy(edit)})
    return rows


def update_review(record, object_id, status, label, box, notes=""):
    originals = record["original"].get("detections", [])
    if status not in REVIEW_STATES or not isinstance(label, str) or not label.strip() or len(label) > 200 or any(c in label for c in '\n\r\t'):
        raise ValueError("Choose a valid status and a nonempty label (maximum 200 characters).")
    if len(notes) > 4000:
        raise ValueError("Notes exceed 4000 characters.")
    box = validate_box(box, record["image"]["width"], record["image"]["height"])
    if object_id is None:
        object_id = "manual_" + uuid.uuid4().hex
        if status not in ("corrected", "accepted"):
            raise ValueError("A manually added object must be accepted or corrected.")
    elif not object_id.startswith("manual_"):
        if not object_id.isdigit() or not 0 <= int(object_id) < len(originals):
            raise ValueError("Unknown original object.")
        original = originals[int(object_id)]
        if status in ("accepted", "unreviewed") and (label != original["class_name"] or box != original["bbox_xyxy"]):
            raise ValueError("Use corrected status when changing the predicted class or box.")
    elif object_id not in record["review"]:
        raise ValueError("Unknown manually added object.")
    if len(record["review"]) >= 2000 and object_id not in record["review"]:
        raise ValueError("Review limit reached (2000 objects).")
    record["review_undo"].append({"object_id": object_id, "previous": deepcopy(record["review"].get(object_id))})
    record["review_undo"] = record["review_undo"][-20:]
    record["review"][object_id] = {"status": status, "class_name": label.strip(), "bbox_xyxy": box,
                                   "notes": notes, "updated_at": now(), "origin": "human_review"}
    return object_id


def undo_review(record):
    if record["review_undo"]:
        change = record["review_undo"].pop()
        if change["previous"] is None:
            record["review"].pop(change["object_id"], None)
        else:
            record["review"][change["object_id"]] = change["previous"]


def final_annotations(record):
    """Explicit export policy: accepted/corrected only; no unreviewed predictions."""
    return [r for r in review_rows(record) if r["status"] in ("accepted", "corrected")]


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")
