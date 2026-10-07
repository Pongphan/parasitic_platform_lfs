"""Responsive crop review and portable tabular evidence."""
import csv
import io
import math
from PIL import ImageOps
import streamlit as st
from component_ai.settings import canonical_label


def detection_rows(detections):
    return [{"Region": i, "Class": canonical_label(d["class_name"]),
             "Score": d["confidence"], "Class ID": d["class_id"],
             **dict(zip(("x1", "y1", "x2", "y2"), d["bbox_xyxy"]))}
            for i, d in enumerate(detections, 1)]


def detections_csv(report):
    buffer = io.StringIO(newline="")
    fields = ["Region", "Class", "Score", "Class ID", "x1", "y1", "x2", "y2", "Model", "Image SHA256"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for row in detection_rows(report["detections"]):
        row.update({"Model": report["configuration"]["selected_model"], "Image SHA256": report["image_sha256"]})
        # Model metadata can originate in a third-party checkpoint: neutralize formulas.
        writer.writerow({k: "'"+v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v for k, v in row.items()})
    return buffer.getvalue().encode("utf-8-sig")


def crop_box(image, detection):
    values = detection["bbox_xyxy"]
    if len(values) != 4 or not all(math.isfinite(v) for v in values):
        raise ValueError("Region coordinates must be four finite numbers")
    x1, y1, x2, y2 = values
    box = (max(0, math.floor(x1)), max(0, math.floor(y1)),
           min(image.width, math.ceil(x2)), min(image.height, math.ceil(y2)))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("Region does not intersect the image")
    return box


def render_crop_gallery(image, detections):
    st.subheader(f"Detected crops ({len(detections)})")
    st.caption("Region numbers match the annotated image. Previews retain aspect ratio; dimensions are source pixels, not calibrated physical measurements.")
    # Native horizontal containers wrap with viewport width. Card size also adapts
    # to the detection count; all crops remain visible without a selection dropdown.
    card_width = 440 if len(detections) == 1 else 340 if len(detections) == 2 else 260
    with st.container(horizontal=True, gap="small", key="crop_gallery"):
        for index, detection in enumerate(detections, 1):
            with st.container(border=True, width=card_width):
                st.markdown(f"**Region {index:02d}**")
                try:
                    box = crop_box(image, detection)
                    preview = ImageOps.pad(image.crop(box).convert("RGB"), (320, 220), color="#EDF3F5")
                    st.image(preview, width="stretch")
                    st.write(canonical_label(detection["class_name"]))
                    st.caption(f"Score {detection['confidence']:.0%} · {box[2]-box[0]} × {box[3]-box[1]} px")
                except ValueError as exc:
                    st.warning(f"Cannot display this region: {exc}")
