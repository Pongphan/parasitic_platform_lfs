"""2026 viewer adapter; its existing iframe protocol is preserved intentionally."""
import math
from component_layout.viewer_component import viewer_component
from component_ai.roi import image_to_base64, compute_center_cell_crop_box

def render_image_viewer(image, image_id, state):
    return viewer_component(image_b64=image_to_base64(image), viewport=0,
                            init_zoom=state["zoom"], init_panX=state["panX"], init_panY=state["panY"],
                            theme_mode="Light", key=f"viewer_{image_id[:16]}", image_id=image_id)

def selection_from_event(image, event, image_id):
    if not isinstance(event, dict) or event.get("action") != "calculate" or event.get("image_id") != image_id:
        raise ValueError("Selection does not belong to the current image")
    values = {key: float(event[key]) for key in ("zoom", "panX", "panY", "viewport")}
    if not all(math.isfinite(v) for v in values.values()) or not 0.15 <= values["zoom"] <= 12 or not 1 <= values["viewport"] <= 4096:
        raise ValueError("Invalid viewer coordinates")
    viewport = int(values["viewport"])
    # Refuse a center cell wholly outside the image, instead of the old 1px edge crop.
    scale = min(viewport / image.width, viewport / image.height) * values["zoom"]
    cx = image.width / 2 - values["panX"] / scale
    cy = image.height / 2 - values["panY"] / scale
    half = viewport / (6 * scale)
    if cx + half <= 0 or cy + half <= 0 or cx - half >= image.width or cy - half >= image.height:
        raise ValueError("Move the image under the center box before calculating")
    box = compute_center_cell_crop_box(image, viewport, values["zoom"], values["panX"], values["panY"])
    token = str(event.get("calc_token", ""))
    if not token or len(token) > 128:
        raise ValueError("Missing or invalid Calculate event token")
    return box, values, token
