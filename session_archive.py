"""Versioned JSON/ZIP portability and explicit reviewed-dataset exports."""
from copy import deepcopy
import csv
import io
import json
import re
import zipfile
from workspace import (SCHEMA, MAX_RECORDS, MAX_HISTORY, new_workspace, digest, json_bytes,
                       retain_image, validate_box, final_annotations)

MAX_ARCHIVE = 256 * 1024 * 1024
MAX_EXPANDED = 300 * 1024 * 1024
MAX_JSON = 16 * 1024 * 1024
HASH = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[0-9a-f]{32}$")


def parse_json(data):
    if len(data) > MAX_JSON:
        raise ValueError("JSON exceeds the 16 MB metadata limit.")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field.")
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError("Non-finite JSON number.")
    try:
        parsed = json.loads(data, object_pairs_hook=pairs, parse_constant=bad_constant)
        json.dumps(parsed, allow_nan=False)  # Also rejects overflow such as 1e999.
        return parsed
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Malformed JSON metadata.") from exc


def validate_record(record):
    try:
        if record["schema_version"] != SCHEMA or not IDENTIFIER.fullmatch(record["analysis_id"]):
            raise ValueError("Unsupported record schema or invalid analysis ID.")
        image = record["image"]
        if not HASH.fullmatch(image["sha256"]) or not isinstance(image["name"], str):
            raise ValueError("Invalid source image identity.")
        w, h = image["width"], image["height"]
        if type(w) is not int or type(h) is not int or min(w, h) <= 0 or w*h > 24000000:
            raise ValueError("Invalid source dimensions.")
        if record["status"] not in ("completed", "partial", "failed") or record["mode"] not in ("auto", "keras"):
            raise ValueError("Invalid analysis mode or status.")
        for key in ("configuration", "model_sha256", "original", "review"):
            if not isinstance(record[key], dict):
                raise ValueError("Invalid record object.")
        for key in ("errors", "warnings", "review_undo"):
            if not isinstance(record[key], list):
                raise ValueError("Invalid record list.")
        if not isinstance(record.get("notes", ""), str) or len(record.get("notes", "")) > 4000:
            raise ValueError("Invalid analysis notes.")
        if not isinstance(record["created_at"], str) or type(record["elapsed_seconds"]) not in (int, float) or not 0 <= record["elapsed_seconds"] < 1e9:
            raise ValueError("Invalid analysis timing.")
        original = record["original"]
        if original["image_sha256"] != image["sha256"] or original["configuration"] != record["configuration"]:
            raise ValueError("Inconsistent original provenance.")
        if record["configuration"].get("mode") != record["mode"]:
            raise ValueError("Analysis mode differs from its configuration.")
        if any(not isinstance(value, str) or not HASH.fullmatch(value) for value in record["model_sha256"].values()):
            raise ValueError("Invalid model SHA-256 identity.")
        detections = original.get("detections", [])
        if not isinstance(detections, list) or len(detections) > 2000 or len(record["review"]) > 2000:
            raise ValueError("Too many or malformed detections/reviews.")
        for row in detections:
            validate_box(row["bbox_xyxy"], w, h)
            if not isinstance(row["class_name"], str) or not row["class_name"] or len(row["class_name"]) > 200 or type(row["confidence"]) not in (int, float) or not 0 <= row["confidence"] <= 1:
                raise ValueError("Invalid detection label or confidence.")
        for key, row in record["review"].items():
            if not (key.isdigit() and int(key) < len(detections)) and not re.fullmatch(r"manual_[0-9a-f]{32}", key):
                raise ValueError("Review refers to an unknown object.")
            validate_box(row["bbox_xyxy"], w, h)
            if row["status"] not in ("unreviewed", "accepted", "corrected", "rejected") or not isinstance(row["class_name"], str) or not row["class_name"].strip() or len(row["class_name"]) > 200:
                raise ValueError("Invalid review label or status.")
            if not isinstance(row.get("notes"), str) or len(row["notes"]) > 4000:
                raise ValueError("Invalid review notes.")
        # Undo history is ephemeral; imported edits remain but undo starts clean.
        record["review_undo"] = []
    except (KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError("Malformed analysis record.") from exc


def validate_learning(ws):
    from content import atlas_entries
    from learning import question_pool
    entries = atlas_entries()
    ids = {e["id"] for e in entries}
    pool = {q["question_key"]: q for q in question_pool(entries)}
    if not isinstance(ws["bookmarks"], list) or len(ws["bookmarks"]) > 200 or any(k not in ids for k in ws["bookmarks"]):
        raise ValueError("Invalid Atlas bookmarks.")
    if not isinstance(ws["learning_lists"], dict) or len(ws["learning_lists"]) > 50:
        raise ValueError("Invalid learning lists.")
    for name, values in ws["learning_lists"].items():
        if not isinstance(name, str) or not 1 <= len(name) <= 100 or not isinstance(values, list) or len(values) > 200 or any(k not in ids for k in values):
            raise ValueError("Invalid learning list contents.")
    if not isinstance(ws["question_history"], list) or len(ws["question_history"]) > MAX_HISTORY:
        raise ValueError("Invalid question history.")
    for row in ws["question_history"]:
        q = pool.get(row.get("question_key")) if isinstance(row, dict) else None
        if q is None or row.get("species_id") != q["species_id"] or row.get("group") != q["group"]:
            raise ValueError("Question history refers to unknown content.")
        answer = row.get("answer")
        if type(answer) is not int or not 0 <= answer < len(q["options"]) or type(row.get("correct")) is not bool or row["correct"] != (answer == q["correct_answer"]) or row.get("confidence") not in (None, "Low", "Medium", "High"):
            raise ValueError("Invalid question attempt.")
    if not isinstance(ws["quiz_attempts"], dict) or len(ws["quiz_attempts"]) > 100:
        raise ValueError("Invalid saved quizzes.")
    if ws["active_quiz"] is not None and not isinstance(ws["active_quiz"], dict):
        raise ValueError("Invalid active quiz.")
    if any(not isinstance(value, dict) or value.get("id") != key for key,value in ws["quiz_attempts"].items()):
        raise ValueError("Saved quiz identity does not match its key.")
    quizzes = list(ws["quiz_attempts"].values()) + ([ws["active_quiz"]] if ws["active_quiz"] else [])
    for quiz in quizzes:
        if not isinstance(quiz, dict) or not IDENTIFIER.fullmatch(quiz.get("id", "")) or type(quiz.get("submitted")) is not bool:
            raise ValueError("Invalid quiz identity/state.")
        questions = quiz.get("questions")
        if not isinstance(questions, list) or not 1 <= len(questions) <= 100:
            raise ValueError("Invalid quiz questions.")
        seen = set()
        for q in questions:
            key = q.get("question_key") if isinstance(q, dict) else None
            if key not in pool or q != pool[key] or key in seen:
                raise ValueError("Quiz differs from installed reference content or contains duplicates.")
            seen.add(key)
        if not isinstance(quiz.get("answers"), list) or len(quiz["answers"]) != len(questions) or not isinstance(quiz.get("confidence"), list) or len(quiz["confidence"]) != len(questions):
            raise ValueError("Invalid saved quiz responses.")
        for q, answer, rating in zip(questions, quiz["answers"], quiz["confidence"]):
            if (answer is not None and (type(answer) is not int or not 0 <= answer < len(q["options"]))) or rating not in (None, "Low", "Medium", "High"):
                raise ValueError("Invalid saved answer or confidence.")
        if quiz["submitted"] and (any(a is None for a in quiz["answers"]) or quiz.get("correct") != [a == q["correct_answer"] for q,a in zip(questions, quiz["answers"])]):
            raise ValueError("Invalid saved quiz score.")


def export_session(ws, include_images=False):
    data = {k: deepcopy(v) for k,v in ws.items() if k != "images"}
    data["image_members"] = {sha: f"images/{sha}.bin" for sha in ws["images"]} if include_images else {}
    payload = json_bytes(data)
    if len(payload) > MAX_JSON:
        raise ValueError("Session metadata exceeds 16 MB. Reduce retained records before exporting.")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("session.json", payload)
        for sha, member in data["image_members"].items():
            archive.writestr(member, ws["images"][sha]["data"])
    if output.tell() > MAX_ARCHIVE:
        raise ValueError("Archive exceeds 256 MB; export without images.")
    return output.getvalue()


def import_session(data):
    """Validate everything before replacing live state; never extract files to disk."""
    if len(data) > MAX_ARCHIVE:
        raise ValueError("Archive exceeds 256 MB.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            if len(names) > 202 or len(set(names)) != len(names) or "session.json" not in names:
                raise ValueError("Invalid or duplicate archive members.")
            if sum(i.file_size for i in infos) > MAX_EXPANDED:
                raise ValueError("Archive decompression exceeds 300 MB.")
            for info in infos:
                if info.filename != "session.json" and not re.fullmatch(r"images/[0-9a-f]{64}\.bin", info.filename):
                    raise ValueError("Unexpected or unsafe archive path.")
                limit = MAX_JSON if info.filename == "session.json" else 25*1024*1024
                if info.file_size > limit or info.flag_bits & 1 or (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Oversized, encrypted or symbolic-link member.")
                if info.file_size > max(1, info.compress_size)*1000:
                    raise ValueError("Excessive archive compression ratio.")
            raw = parse_json(archive.read("session.json"))
            ws = new_workspace()
            if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA:
                raise ValueError("Unsupported session schema.")
            allowed = set(ws)-{"images"}
            if set(raw) != allowed | {"image_members"}:
                raise ValueError("Unknown or missing session fields.")
            ws.update({k: raw[k] for k in allowed})
            if type(ws["image_budget"]) is not int or not 16*1024*1024 <= ws["image_budget"] <= 256*1024*1024:
                raise ValueError("Image budget must be 16–256 MB.")
            if type(ws["record_limit"]) is not int or not 1 <= ws["record_limit"] <= MAX_RECORDS:
                raise ValueError("Invalid record retention limit.")
            if not isinstance(ws["records"], list) or len(ws["records"]) > ws["record_limit"]:
                raise ValueError("Invalid retained records.")
            for record in ws["records"]:
                validate_record(record)
            if len({r["analysis_id"] for r in ws["records"]}) != len(ws["records"]):
                raise ValueError("Duplicate analysis IDs.")
            if not isinstance(ws["comparisons"], list) or len(ws["comparisons"]) > 100:
                raise ValueError("Invalid comparison history.")
            for comparison in ws["comparisons"]:
                if not isinstance(comparison, dict) or set(comparison) != {"analysis_ids", "iou", "created_at"} or not isinstance(comparison["analysis_ids"], list) or not 2 <= len(comparison["analysis_ids"]) <= 3 or any(not isinstance(i, str) or not IDENTIFIER.fullmatch(i) for i in comparison["analysis_ids"]) or type(comparison["iou"]) not in (int,float) or not 0 < comparison["iou"] <= 1 or not isinstance(comparison["created_at"], str):
                    raise ValueError("Invalid saved comparison.")
            validate_learning(ws)
            members = raw["image_members"]
            if not isinstance(members, dict) or set(names) != {"session.json"} | set(members.values()):
                raise ValueError("Archive image manifest differs from contents.")
            for sha, member in members.items():
                if not HASH.fullmatch(sha) or member != f"images/{sha}.bin":
                    raise ValueError("Invalid image member identity.")
                retain_image(ws, archive.read(member), sha)
            for record in ws["records"]:
                image = ws["images"].get(record["image"]["sha256"])
                if image and (image["width"], image["height"]) != (record["image"]["width"], record["image"]["height"]):
                    raise ValueError("Stored image dimensions do not match analysis.")
            return ws
    except (zipfile.BadZipFile, KeyError, TypeError, AttributeError, RuntimeError, NotImplementedError, RecursionError) as exc:
        raise ValueError("Invalid session archive.") from exc


def dataset_export(records, labels):
    """Caller supplies deliberate ordered class list; never infer it from Atlas."""
    if not labels or len(set(labels)) != len(labels) or any(not isinstance(label,str) or not label.strip() or len(label)>200 or any(c in label for c in '\n\r\t') for label in labels):
        raise ValueError("Provide a unique ordered class mapping, one label per line.")
    mapping = {label: i for i, label in enumerate(labels)}
    coco = {"info": {"origin": "human_review_of_model_predictions; not independent ground truth",
                     "policy": "Accepted/corrected objects only; unreviewed/rejected excluded"},
            "images": [], "annotations": [], "categories": [{"id": i, "name": name} for name,i in mapping.items()]}
    files = {"classes.txt": "\n".join(labels).encode()}
    for index, record in enumerate(records, 1):
        if record["mode"] == "keras":
            raise ValueError("Dataset export supports object detections, not crop classifiers.")
        image = record["image"]
        w, h = image["width"], image["height"]
        coco["images"].append({"id": index, "file_name": image["name"], "width": w, "height": h, "sha256": image["sha256"], "analysis_id": record["analysis_id"]})
        lines = []
        for row in final_annotations(record):
            if row["class_name"] not in mapping:
                raise ValueError(f"No explicit dataset mapping for {row['class_name']}.")
            x1,y1,x2,y2 = validate_box(row["bbox_xyxy"], w,h)
            class_id = mapping[row["class_name"]]
            coco["annotations"].append({"id": len(coco["annotations"])+1, "image_id": index, "category_id": class_id,
                                         "bbox": [x1,y1,x2-x1,y2-y1], "area": (x2-x1)*(y2-y1), "iscrowd": 0})
            lines.append(f"{class_id} {(x1+x2)/(2*w):.9f} {(y1+y2)/(2*h):.9f} {(x2-x1)/w:.9f} {(y2-y1)/h:.9f}")
        files[f"labels/{record['analysis_id']}.txt"] = "\n".join(lines).encode()
    files["annotations.coco.json"] = json_bytes(coco)
    files["reviewed_records.json"] = json_bytes(records)
    files["manifest.json"] = json_bytes({"schema_version": SCHEMA, "class_mapping": mapping,
                                        "policy": coco["info"], "images": coco["images"], "images_included": False,
                                        "yolo_filename_rule": "labels/<analysis_id>.txt; image identities in this manifest"})
    return zip_files(files), coco


def zip_files(files):
    if sum(len(data) for data in files.values()) > MAX_ARCHIVE:
        raise ValueError("Export exceeds 256 MB. Select fewer records or omit source images.")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    if output.tell() > MAX_ARCHIVE:
        raise ValueError("Compressed export exceeds 256 MB.")
    return output.getvalue()


def batch_export(ws, records, job=None):
    from component_ai.images import decode_image
    from component_ai.annotations import annotate_detections
    files, missing = {}, []
    table = io.StringIO(newline="")
    writer = csv.writer(table)
    writer.writerow(["analysis_id", "image_sha256", "model", "status", "objects", "elapsed_seconds"])
    for record in records:
        identity = record["analysis_id"]
        files[f"reports/{identity}.json"] = json_bytes(record)
        writer.writerow([identity, record["image"]["sha256"], record["configuration"].get("selected_model", "keras"), record["status"], len(record["original"].get("detections", [])), record["elapsed_seconds"]])
        stored = ws["images"].get(record["image"]["sha256"])
        if stored and record["mode"] != "keras" and record["status"] == "completed":
            buffer = io.BytesIO()
            annotate_detections(decode_image(stored["data"]), record["original"].get("detections", [])).save(buffer, format="PNG")
            files[f"annotated/{identity}.png"] = buffer.getvalue()
        else:
            missing.append(identity)
        if sum(len(value) for value in files.values()) > MAX_ARCHIVE:
            raise ValueError("Export exceeds 256 MB. Select fewer analyses.")
    files["summary.csv"] = table.getvalue().encode("utf-8-sig")
    files["manifest.json"] = json_bytes({"schema_version": SCHEMA, "analysis_ids": [r["analysis_id"] for r in records],
                                        "missing_annotated_images": missing, "job": job,
                                        "files": {name: digest(data) for name,data in files.items()}})
    return zip_files(files)
