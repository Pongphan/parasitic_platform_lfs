"""Sequential, resumable inference jobs. A step executes at most one model call."""
from copy import deepcopy
import json
from time import perf_counter
import uuid
from component_ai.detection import auto_detector_contract
from component_ai.registry import file_version
from component_ai.images import decode_image
from workspace import digest, retain_image, analysis_record, add_record, find_record


def configuration(model, confidence):
    family, manifest, weights = auto_detector_contract(model)
    if not weights.is_file():
        raise ValueError(f"Missing {model} checkpoint: {weights}")
    return {"mode": "auto", "selected_model": model, "family": family, "manifest": manifest,
            "version": file_version(weights), "confidence": confidence, "iou": 0.45,
            "label_schema_version": 2}


def predict(image, config):
    """Reuse safe cached loaders and per-model locks; separate loading/inference timers."""
    family, manifest, weights = auto_detector_contract(config["selected_model"])
    if tuple(config["version"]) != tuple(file_version(weights)) or manifest != config["manifest"]:
        raise ValueError("Model changed since the queue was prepared. Prepare a new queue.")
    start = perf_counter()
    if family == "yolo":
        from component_ai.yolo import load_yolo_model, run_yolo_inference
        model, lock, sha = load_yolo_model(str(weights), file_version(weights))
    else:
        from component_ai.rcnn import load_rcnn_model, run_rcnn_inference
        model, lock, sha = load_rcnn_model(str(weights), file_version(weights), json.dumps(manifest, sort_keys=True))
    load_seconds = perf_counter() - start
    wait_start = perf_counter()
    with lock:
        start = perf_counter()
        wait_seconds = start - wait_start
        if family == "yolo":
            result = run_yolo_inference(model, image, config["confidence"], image_size=manifest["image_size"], iou_threshold=config["iou"])
        else:
            result = run_rcnn_inference(model, image, manifest["labels"], config["confidence"], iou_threshold=config["iou"])
    result.pop("annotated_image", None)
    result["model_sha256"] = {config["selected_model"]: sha}
    result["timing"] = {"load_or_cache_seconds": load_seconds, "lock_wait_seconds": wait_seconds,
                        "inference_and_annotation_seconds": perf_counter()-start}
    return result


def prepare_job(ws, uploads, configs, max_files=12):
    if not 1 <= max_files <= 24 or not 1 <= len(uploads) <= max_files or not 1 <= len(configs) <= 3:
        raise ValueError("Choose 1–24 files within the configured count, and 1–3 models.")
    items, valid, total_cost = [], {}, 0
    for name, data in uploads:
        identity = digest(data)
        try:
            image = decode_image(data)
            if identity not in valid:
                cost = len(data) + image.width * image.height * 3
                if total_cost + cost > ws["image_budget"]:
                    raise ValueError("Batch exceeds the total image memory budget.")
                total_cost += cost
                valid[identity] = data
            for config in configs:
                if not any(i.get("image_hash") == identity and i.get("config") == config for i in items):
                    items.append({"name": name, "image_hash": identity, "config": deepcopy(config), "status": "pending", "error": None, "analysis_id": None})
        except ValueError as exc:
            items.append({"name": name, "image_hash": identity, "status": "validation_failed", "error": str(exc), "analysis_id": None})
    for data in valid.values():
        retain_image(ws, data)
    return {"id": uuid.uuid4().hex, "items": items, "running": False, "cancelled": False}


def cancel_job(job):
    job["running"] = False
    job["cancelled"] = True


def retry_failed(job):
    for item in job["items"]:
        if item["status"] == "failed":
            item.update(status="pending", error=None, analysis_id=None)
    job.update(running=True, cancelled=False)


def step_job(ws, job, runner=predict):
    if not job["running"] or job["cancelled"]:
        return None
    item = next((i for i in job["items"] if i["status"] == "pending"), None)
    if item is None:
        job["running"] = False
        return None
    item["status"] = "running"
    start = perf_counter()
    try:
        stored = ws["images"].get(item["image_hash"])
        if stored is None:
            raise ValueError("Source image was evicted. Restore its exact bytes in Session workspace, then retry.")
        image = decode_image(stored["data"])
        result = runner(image, item["config"])
        report = {**result, "image_sha256": item["image_hash"], "image_name": item["name"], "configuration": item["config"]}
        record = add_record(ws, analysis_record(report, image.width, image.height, perf_counter()-start))
        item.update(status="completed", analysis_id=record["analysis_id"])
    except Exception as exc:
        item.update(status="failed", error=str(exc))
        if stored:
            report = {"image_sha256": item["image_hash"], "image_name": item["name"],
                      "configuration": item["config"], "errors": [{"error": str(exc)}]}
            failed = add_record(ws, analysis_record(report, stored["width"], stored["height"],
                                                    perf_counter()-start, status="failed"))
            item["analysis_id"] = failed["analysis_id"]
    if not any(i["status"] == "pending" for i in job["items"]):
        job["running"] = False
    return item


def job_records(ws, job):
    return [record for item in job["items"] if (record := find_record(ws, item.get("analysis_id")))]
