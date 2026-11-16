# SPDX-License-Identifier: GPL-3.0-only
"""Encode the MOSS epoch-5 camera view alongside its direction caption."""
from pathlib import Path

from .atelier_camera import ensure_camera_asset


MOSS_LORA = "moss/RS-CAMERA-CONTROL-MOSS.safetensors"
MOSS_TOKENS = "moss/RS-CAMERA-CONTROL-MOSS-tokens.safetensors"
MOSS_REPO = "https://huggingface.co/raspie/RS-CAMERA-CONTROL-MOSS"
MOSS_REVISION = "ff44cb77d159d94f1c13aa7e85f1b67882e12e87"
MOSS_CAMERA_WRAPPER = "rs_moss_camera"


def moss_lora():
    return ensure_camera_asset(MOSS_LORA, f"{MOSS_REPO}/resolve/{MOSS_REVISION}/{Path(MOSS_LORA).name}",
                               33_085_184, "2b57433c66b5066cbbe493ba388e7572a0fb1714647158fd4b881de70c6ca9c5")


def moss_tokens():
    import folder_paths
    from safetensors.torch import load_file

    name = ensure_camera_asset(MOSS_TOKENS, f"{MOSS_REPO}/resolve/{MOSS_REVISION}/{Path(MOSS_TOKENS).name}",
                               688_280, "60c2a873fe361bd39de3d5fc040ca457ba45d88b72c60181ea11fb5e163e884a")
    embeddings = load_file(folder_paths.get_full_path_or_raise("loras", name))["embeddings"]
    if embeddings.shape != (42, 4096):
        raise ValueError(f"{name} must contain 42 camera embeddings with 4,096 features each.")
    return embeddings


def moss_view_caption(view, side):
    (x, _, z), learned, _ = view
    if abs(z) < 1e-8:
        support = "Side profile, with the camera looking directly at the side of the torso." if side else ""
    elif abs(x) < 1e-8:
        support = ("Straight-on front view, with the front of the torso visible." if z > 0 else
                   "Straight-on rear view, with the back of the torso visible. The subject faces straight away from the camera.")
    else:
        support = ("Front three-quarter view, with the front and one side of the torso visible." if z > 0 else
                   "Rear three-quarter view, with the back and one side of the torso visible.")
    prefix = ", ".join(filter(None, (side, learned)))
    return f"{prefix}, {support}" if support else prefix


def prepend_moss_camera(text, token):
    import torch

    if text.ndim != 3 or text.shape[-1] != 4096:
        raise ValueError("Connect the MOSS text encoder with CLIPLoader type 'moss_image'.")
    token = token.to(text).reshape(1, 1, -1).expand(text.shape[0], -1, -1)
    return torch.cat((token, text), dim=1)


def install_moss_camera(model, token, scope):
    from comfy.patcher_extension import WrappersMP

    def prepare(executor, model, noise_shape, conds, **kwargs):
        if "positive" in conds:
            positive = [dict(entry, cross_attn=prepend_moss_camera(entry["cross_attn"], token))
                        if entry.get("cross_attn") is not None else entry for entry in conds["positive"]]
            conds = dict(conds, positive=positive)
        return executor(model, noise_shape, conds, **kwargs)

    model.remove_wrappers_with_key(WrappersMP.PREPARE_SAMPLING, MOSS_CAMERA_WRAPPER)
    model.add_wrapper_with_key(WrappersMP.PREPARE_SAMPLING, MOSS_CAMERA_WRAPPER, prepare)
    if scope == "scene_and_characters":
        model.model_options[MOSS_CAMERA_WRAPPER] = token
    else:
        model.model_options.pop(MOSS_CAMERA_WRAPPER, None)
