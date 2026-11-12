# SPDX-License-Identifier: GPL-3.0-only
"""Match the Atelier Sphere 10-epoch LoRA's 42 training views."""
import json
import math
from pathlib import Path


ATELIER_LORA = "anima/RS-CAMERA-CONTROL.safetensors"
LEGACY_ATELIER_LORA = "anima/Atelier-Sphere-eye-view-recipe-10ep.safetensors"
ATELIER_LORA_URL = (
    "https://huggingface.co/raspie/RS-CAMERA-CONTROL/resolve/"
    f"d91f7186804ce14e41b9dc5d0244dea66205de30/{Path(ATELIER_LORA).name}"
)
ATELIER_LORA_SIZE = 34_800_320
ATELIER_LORA_SHA256 = "eadfcb3e0ec9140647f1adf283e957c2f8320712a367750c3e0e9955f62242b6"


def ensure_atelier_lora():
    import folder_paths

    for name in (ATELIER_LORA, LEGACY_ATELIER_LORA):
        if folder_paths.get_full_path("loras", name):
            return name

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
        logging.info("RS Camera Control: downloading RS-CAMERA-CONTROL (33.2 MiB)")
        digest, received = hashlib.sha256(), 0
        with NamedTemporaryFile(dir=target.parent, prefix=".atelier-", suffix=".part", delete=False) as output:
            temporary = Path(output.name)
            with urlopen(ATELIER_LORA_URL, timeout=30) as response:
                while chunk := response.read(256 * 1024):
                    check_interrupted()
                    received += len(chunk)
                    if received > ATELIER_LORA_SIZE:
                        raise ValueError("Unexpected RS-CAMERA-CONTROL file size")
                    digest.update(chunk)
                    output.write(chunk)
        check_interrupted()
        if received != ATELIER_LORA_SIZE or digest.hexdigest() != ATELIER_LORA_SHA256:
            raise ValueError("RS-CAMERA-CONTROL download failed SHA-256 verification")
        if not folder_paths.get_full_path("loras", ATELIER_LORA):
            temporary.replace(target)
            folder_paths.filename_list_cache.pop("loras", None)
        return ATELIER_LORA
    except (OSError, ValueError) as error:
        raise RuntimeError(
            f"Could not install RS-CAMERA-CONTROL from Hugging Face ({error}). "
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


def view_captions(azimuth, elevation, strength, syntax, weighting):
    requested = direction(azimuth, elevation)
    _, learned, support = max(VIEWS, key=lambda view: sum(a*b for a, b in zip(requested, view[0])))
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
