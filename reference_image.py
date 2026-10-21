"""Reference image sizing shared by reference backends.

The selected resolution describes the image's longest edge, not a crop.
Square padding is an explicit requirement of the current Anima encoder.
"""
from numbers import Integral

from PIL import Image, ImageOps


REFERENCE_SIZE_DEFAULT = 384
REFERENCE_SIZE_MIN = 64
REFERENCE_SIZE_MAX = 1024
REFERENCE_SIZE_STEP = 64


def validate_reference_size(size):
    if (isinstance(size, bool) or not isinstance(size, Integral)
            or not REFERENCE_SIZE_MIN <= size <= REFERENCE_SIZE_MAX
            or size % REFERENCE_SIZE_STEP):
        raise ValueError("Reference resolution must be 64–1024 px in steps of 64 px.")
    return int(size)


def reference_size_input():
    return ("INT", {
        "default": REFERENCE_SIZE_DEFAULT,
        "min": REFERENCE_SIZE_MIN,
        "max": REFERENCE_SIZE_MAX,
        "step": REFERENCE_SIZE_STEP,
        "tooltip": "Resize the longest edge to this size, preserving aspect ratio. "
                   "Anima pads the rest; larger sizes use more memory.",
    })


def prepare_reference(image, size, *, square_padding=False):
    """Fit the full, display-oriented image; return pixels and reproducible geometry."""
    size = validate_reference_size(size)
    image = ImageOps.exif_transpose(image).convert("RGB")
    original = image.size
    ratio = size / max(original)
    resized_size = tuple(max(1, round(edge * ratio)) for edge in original)
    resized = image.resize(resized_size, Image.Resampling.BILINEAR)
    left = top = right = bottom = 0
    if square_padding:
        left, top = ((size - edge) // 2 for edge in resized_size)
        right, bottom = size - resized.width - left, size - resized.height - top
        result = Image.new("RGB", (size, size), (0, 0, 0))
        result.paste(resized, (left, top))
    else:
        result = resized
    return result, {
        "requested_long_edge": size,
        "oriented_source_size": list(original),
        "resized_size": list(resized_size),
        "encoder_size": list(result.size),
        "padding_ltrb": [left, top, right, bottom],
        "crop": False,
    }
