# SPDX-License-Identifier: GPL-3.0-only
"""Shared 42 training views and camera asset downloads."""
import json
import math
from pathlib import Path
import re

from .prompt_syntax import filter_prompt_tags


ATELIER_LORA = "anima/RS-CAMERA-CONTROL-v2.safetensors"
ATELIER_LORA_URL = (
    "https://huggingface.co/raspie/RS-CAMERA-CONTROL/resolve/"
    f"8e28bb227d8b7a8177ea17b975d1e71599d6bfc7/{Path(ATELIER_LORA).name}"
)
ATELIER_LORA_SIZE = 34_800_080
ATELIER_LORA_SHA256 = "8a76802375ed798030c20fa0acf4ce0fbc80f28aec5b008e4816626f843bf9b6"


def ensure_atelier_lora():
    return ensure_camera_asset(ATELIER_LORA, ATELIER_LORA_URL, ATELIER_LORA_SIZE, ATELIER_LORA_SHA256)


def ensure_camera_asset(name, url, size, sha256):
    import folder_paths

    if folder_paths.get_full_path("loras", name):
        return name

    import hashlib
    import logging
    from tempfile import NamedTemporaryFile
    from urllib.request import urlopen

    from .runtime_control import check_interrupted

    target = Path(folder_paths.get_folder_paths("loras")[0]) / name
    temporary = None
    try:
        check_interrupted()
        target.parent.mkdir(parents=True, exist_ok=True)
        logging.info("RS Camera Control: downloading %s", target.name)
        digest, received = hashlib.sha256(), 0
        with NamedTemporaryFile(dir=target.parent, prefix=".atelier-", suffix=".part", delete=False) as output:
            temporary = Path(output.name)
            with urlopen(url, timeout=30) as response:
                while chunk := response.read(256 * 1024):
                    check_interrupted()
                    received += len(chunk)
                    if received > size:
                        raise ValueError("Unexpected file size")
                    digest.update(chunk)
                    output.write(chunk)
        check_interrupted()
        if received != size or digest.hexdigest() != sha256:
            raise ValueError("Download failed SHA-256 verification")
        if not folder_paths.get_full_path("loras", name):
            temporary.replace(target)
            folder_paths.filename_list_cache.pop("loras", None)
        return name
    except (OSError, ValueError) as error:
        raise RuntimeError(
            f"Could not install {target.name} from Hugging Face ({error}). "
            f"Check the connection and retry, or place the file in models/loras/{name}."
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def direction(azimuth, elevation):
    azimuth, elevation = map(math.radians, (azimuth, elevation))
    horizontal = math.cos(elevation)
    return (horizontal * math.sin(azimuth), math.sin(elevation), horizontal * math.cos(azimuth))


VIEWS = tuple(
    (direction(azimuth or 0., elevation), tags, support)
    for azimuth, elevation, tags, support in json.loads(
        Path(__file__).with_name("web").joinpath("atelier_camera_views.json").read_text()
    )
)


def nearest_view(azimuth, elevation):
    return VIEWS[nearest_view_index(azimuth, elevation)]


def nearest_view_index(azimuth, elevation):
    requested = direction(azimuth, elevation)
    return max(range(len(VIEWS)), key=lambda i: sum(a*b for a, b in zip(requested, VIEWS[i][0])))


def view_captions(view, strength, syntax, weighting):
    _, learned, support = view
    parts = []
    for part in support.split(", "):
        if not part.startswith("("):
            parts.append(part)
            continue
        tag, amount = part[1:-1].rsplit(":", 1)
        if weighting == "plain":
            parts.append(tag)
        else:
            amount = f"{float(amount)*strength/1.2:.2f}".rstrip("0").rstrip(".")
            parts.append(f"{amount}::{tag}::" if syntax == "NovelAI" else f"({tag}:{amount})")
    return learned, ", ".join(parts)


_FACE_TAGS = frozenset({
    "blush", "closed eyes", "closed mouth", "expressionless", "fang", "fangs",
    "frown", "grin", "hair between eyes", "looking at viewer", "looking back",
    "looking over shoulder", "looking over the shoulder", "one eye closed",
    "open mouth", "parted lips", "pout", "smile", "smirk", "tongue out", "wink",
})
_EYE_COLOR = re.compile(
    r"(?:(?:light|dark) )?(?:amber|aqua|black|blue|brown|cyan|gold|golden|gray|grey|"
    r"green|hazel|orange|pink|purple|red|silver|teal|violet|white|yellow|heterochromatic) eyes"
)
_EYE_DETAILS = re.compile(r"(?:[a-z]+(?:[ -][a-z]+)* )?(?:pupils?|eyebrows?)")


def filter_rear_prompt(prompt, syntax):
    def face_tag(tag):
        tag = " ".join(tag.casefold().replace("_", " ").split())
        return tag in _FACE_TAGS or _EYE_COLOR.fullmatch(tag) or _EYE_DETAILS.fullmatch(tag)

    return filter_prompt_tags(prompt, syntax, face_tag)
