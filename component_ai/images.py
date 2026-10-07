"""Bounded image decoding and explicit source-coordinate crops."""
import io
import warnings
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 24_000_000
EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}

def discover_samples(root):
    return sorted(p for p in Path(root).rglob("*") if p.suffix.lower() in EXTENSIONS and p.is_file())

def decode_image(data):
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Choose an image between 1 byte and 25 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.width * source.height > MAX_PIXELS:
                    raise ValueError("Image exceeds the 24 megapixel limit. Crop or resize it first.")
                if getattr(source, "n_frames", 1) > 1:
                    raise ValueError("Multi-frame images are unsupported. Export one frame first.")
                return ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError("The file could not be decoded as a supported image.") from exc

def crop_image(image, box):
    x1, y1, x2, y2 = box
    if any(type(v) is not int for v in box) or not (0 <= x1 < x2 <= image.width and 0 <= y1 < y2 <= image.height):
        raise ValueError("Crop coordinates must define a nonempty region inside the image.")
    return image.crop(box)
