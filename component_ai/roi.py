"""Image conversion and region-of-interest helpers."""

import base64
import io

import numpy as np
from PIL import Image


CropBox = tuple[int, int, int, int]


def image_to_base64(image: Image.Image, image_format: str = "PNG") -> str:
    """Encode a Pillow image for the custom browser viewer component."""
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def compute_center_cell_crop_box(
    image: Image.Image,
    viewport: int,
    zoom: float,
    pan_x: float,
    pan_y: float,
) -> CropBox:
    """Map the viewer's center grid cell to a valid source-image crop box."""
    width, height = image.size
    viewport_size = float(max(1, viewport))
    zoom_level = float(max(1e-6, zoom))
    step = viewport_size / 3.0
    scale = max(
        1e-9,
        min(viewport_size / float(width), viewport_size / float(height)) * zoom_level,
    )
    center = viewport_size / 2.0

    def screen_to_image(screen_x: float, screen_y: float) -> tuple[float, float]:
        return (
            (screen_x - center - float(pan_x)) / scale + width / 2.0,
            (screen_y - center - float(pan_y)) / scale + height / 2.0,
        )

    raw_left, raw_top = screen_to_image(step, step)
    raw_right, raw_bottom = screen_to_image(2.0 * step, 2.0 * step)
    left = float(np.clip(min(raw_left, raw_right), 0.0, float(width)))
    right = float(np.clip(max(raw_left, raw_right), 0.0, float(width)))
    top = float(np.clip(min(raw_top, raw_bottom), 0.0, float(height)))
    bottom = float(np.clip(max(raw_top, raw_bottom), 0.0, float(height)))

    x1 = max(0, min(int(np.floor(left)), width - 1))
    y1 = max(0, min(int(np.floor(top)), height - 1))
    x2 = max(x1 + 1, min(int(np.ceil(right)), width))
    y2 = max(y1 + 1, min(int(np.ceil(bottom)), height))
    return x1, y1, x2, y2
