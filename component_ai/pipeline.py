"""Sequential proposal/refinement inference, independent of the page lifecycle."""
import math
from collections import Counter
from component_ai.yolo import annotate_detections


def overlap(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / union if union else 0


def cascade(image, yolo_predict, rcnn_predict, *, iou=0.45, max_regions=100, progress=None):
    """YOLO proposes crops; RCNN supplies final labels. Scores are never averaged.

    With no proposals RCNN scans the original image. YOLO-only findings remain
    in stage evidence, not in the final RCNN detection count. Any stage failure
    propagates so the caller cannot export a partial run as successful.
    """
    if not 0 <= iou <= 1 or not 1 <= max_regions <= 100:
        raise ValueError("Invalid cascade limits")
    notify = progress or (lambda message: None)
    notify("1 / 2 · Finding candidate regions with YOLO")
    first = yolo_predict(image)
    proposals = first["detections"]
    if len(proposals) > max_regions:
        raise ValueError(f"YOLO found more than {max_regions} regions. Increase its threshold or use a smaller image.")
    regions = []
    for index, proposal in enumerate(proposals):
        values = proposal["bbox_xyxy"]
        if len(values) != 4 or not all(math.isfinite(v) for v in values):
            raise ValueError("YOLO returned an invalid region")
        x1, y1, x2, y2 = values
        # Include surrounding morphology and clamp to original image coordinates.
        px, py = (x2-x1)*0.1, (y2-y1)*0.1
        box = (max(0, math.floor(x1-px)), max(0, math.floor(y1-py)),
               min(image.width, math.ceil(x2+px)), min(image.height, math.ceil(y2+py)))
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError("YOLO returned an empty region")
        regions.append((index, box))
    if not regions:
        regions = [(None, (0, 0, image.width, image.height))]
    refined, evidence = [], []
    for position, (proposal_id, box) in enumerate(regions, 1):
        notify(f"2 / 2 · Faster R-CNN region {position} of {len(regions)}")
        result = rcnn_predict(image.crop(box))
        mapped = []
        for detection in result["detections"]:
            x1, y1, x2, y2 = detection["bbox_xyxy"]
            mapped.append({**detection, "bbox_xyxy": [x1+box[0], y1+box[1], x2+box[0], y2+box[1]],
                           "source": "Faster R-CNN", "proposal_id": proposal_id})
        refined.extend(mapped)
        evidence.append({"proposal_id": proposal_id, "crop_xyxy": list(box), "detections": mapped})
    # Class-aware suppression merges duplicate findings from overlapping crops.
    final = []
    for detection in sorted(refined, key=lambda d: d["confidence"], reverse=True):
        if not any(detection["class_name"] == other["class_name"] and
                   overlap(detection["bbox_xyxy"], other["bbox_xyxy"]) > iou for other in final):
            final.append(detection)
    return {"detections": final, "class_counts": dict(Counter(d["class_name"] for d in final)),
            "stages": {"yolo": proposals, "rcnn": evidence}, "full_image_fallback": not proposals,
            "annotated_image": annotate_detections(image, final)}
