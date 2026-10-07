"""Shared numbered detection overlays for YOLO, RCNN and exported images."""
import hashlib
from PIL import ImageDraw, ImageFont
from component_ai.settings import canonical_label

COLORS = ("#00D5E8", "#FFD166", "#C4A1FF", "#75E6A4", "#FF91B2")


def intersection(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))


def label_position(box, size, canvas, occupied):
    """Try above/below/inside/right, then minimize overlap with earlier labels."""
    x1, y1, x2, y2 = box
    width, height = size
    cw, ch = canvas
    candidates = [(x1, y1-height-4), (x1, y2+4), (x1+4, y1+4), (x2-width, y1-height-4)]
    candidates += [(x1, y) for y in range(0, ch, max(1, height+3))]
    positions = []
    for x, y in candidates:
        x, y = max(0, min(x, cw-width)), max(0, min(y, ch-height))
        rect = (x, y, x+width, y+height)
        positions.append(rect)
        if not any(intersection(rect, other) for other in occupied):
            return rect
    return min(positions, key=lambda rect: sum(intersection(rect, other) for other in occupied))


def annotate_detections(image, detections):
    annotated = image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    font = ImageFont.load_default(size=max(12, min(32, round(max(image.size)/80))))
    stroke = max(2, min(10, round(max(image.size)/450)))
    occupied = []
    for index, detection in enumerate(detections, 1):
        name = canonical_label(detection["class_name"])
        color = COLORS[int(hashlib.sha256(name.encode()).hexdigest()[:8], 16) % len(COLORS)]
        x1, y1, x2, y2 = detection["bbox_xyxy"]
        box = (max(0, min(round(x1), image.width-1)), max(0, min(round(y1), image.height-1)),
               max(0, min(round(x2), image.width-1)), max(0, min(round(y2), image.height-1)))
        if box[2] < box[0] or box[3] < box[1]:
            continue
        # Dark under-stroke keeps the colored edge visible on bright microscopy.
        draw.rectangle(box, outline="#10232D", width=stroke+2)
        draw.rectangle(box, outline=color, width=stroke)
        if min(image.size) < 32:
            continue
        text = f"{index:02d}  {name}  {detection['confidence']:.0%}"
        while draw.textbbox((0, 0), text, font=font)[2] > image.width-16 and len(text) > 3:
            text = text[:-4] + "..."
        bounds = draw.textbbox((0, 0), text, font=font)
        size = (min(image.width, bounds[2]+12), min(image.height, bounds[3]-bounds[1]+12))
        rect = label_position(box, size, image.size, occupied)
        occupied.append(rect)
        draw.line((box[0], box[1], rect[0], rect[3]), fill=color, width=1)
        draw.rounded_rectangle(rect, radius=4, fill="#10232D", outline=color, width=1)
        draw.text((rect[0]+6, rect[1]+6-bounds[1]), text, fill="#FFFFFF", font=font)
    return annotated
