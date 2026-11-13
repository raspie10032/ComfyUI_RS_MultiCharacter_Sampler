# SPDX-License-Identifier: GPL-3.0-only
"""Match RS-CAMERA-CONTROL-v2's 42 training views."""
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
    import folder_paths

    if folder_paths.get_full_path("loras", ATELIER_LORA):
        return ATELIER_LORA

    import hashlib
    import logging
    from tempfile import NamedTemporaryFile
    from urllib.request import urlopen

    from .runtime_control import check_interrupted

    target = Path(folder_paths.get_folder_paths("loras")[0]) / ATELIER_LORA
    temporary = None
    try:
        check_interrupted()
        target.parent.mkdir(parents=True, exist_ok=True)
        logging.info("RS Camera Control: downloading RS-CAMERA-CONTROL-v2 (33.2 MiB)")
        digest, received = hashlib.sha256(), 0
        with NamedTemporaryFile(dir=target.parent, prefix=".atelier-", suffix=".part", delete=False) as output:
            temporary = Path(output.name)
            with urlopen(ATELIER_LORA_URL, timeout=30) as response:
                while chunk := response.read(256 * 1024):
                    check_interrupted()
                    received += len(chunk)
                    if received > ATELIER_LORA_SIZE:
                        raise ValueError("Unexpected RS-CAMERA-CONTROL-v2 file size")
                    digest.update(chunk)
                    output.write(chunk)
        check_interrupted()
        if received != ATELIER_LORA_SIZE or digest.hexdigest() != ATELIER_LORA_SHA256:
            raise ValueError("RS-CAMERA-CONTROL-v2 download failed SHA-256 verification")
        if not folder_paths.get_full_path("loras", ATELIER_LORA):
            temporary.replace(target)
            folder_paths.filename_list_cache.pop("loras", None)
        return ATELIER_LORA
    except (OSError, ValueError) as error:
        raise RuntimeError(
            f"Could not install RS-CAMERA-CONTROL-v2 from Hugging Face ({error}). "
            f"Check the connection and retry, or place the LoRA in models/loras/{ATELIER_LORA}."
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
    for azimuth, elevation, tags, support in json.loads(Path(__file__).with_name("atelier_camera_views.json").read_text())
)


def nearest_view(azimuth, elevation):
    requested = direction(azimuth, elevation)
    return max(VIEWS, key=lambda view: sum(a*b for a, b in zip(requested, view[0])))


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
