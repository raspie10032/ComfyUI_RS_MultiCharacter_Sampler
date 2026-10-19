# SPDX-License-Identifier: GPL-3.0-only
"""NAI-shaped captions with an explicitly local generation extension.

No ComfyUI workflow, authentication, arbitrary graph inputs or model weights.
"""
import json
from dataclasses import replace
from pathlib import Path

from PIL import Image, features
from PIL.PngImagePlugin import PngInfo

from .characters import Character, CharacterPipe, TextRegion
from .regional_lora import lora_records

SOFTWARE = "ComfyUI_RS_MultiCharacter_Sampler"
FORMATS = ["PNG", "WebP lossless", "WebP lossy"]
ENGINE_SOURCES = {"anima-spatial-alpha-1": "Anima (local)", "sdxl-spatial-alpha-1": "SDXL (local)",
                  "sd1.5-spatial-alpha-1": "SD1.5 (local)",
                  "krea2-spatial-alpha-1": "Krea2 (local)", "moss-spatial-alpha-1": "MOSS-Image (local)",
                  "flux1-spatial-alpha-1": "FLUX.1 (local)", "flux2-spatial-alpha-1": "FLUX.2 (local)",
                  "flux3-spatial-alpha-1": "FLUX 3 (local)"}
MAX_METADATA = 4 * 1024 * 1024


def object_json(value):
    if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_METADATA:
        raise ValueError("Metadata must be a JSON object under 4 MiB.")
    result = json.loads(value, parse_constant=lambda v: (_ for _ in ()).throw(ValueError("Nonfinite metadata number")))
    if not isinstance(result, dict):
        raise ValueError("Metadata must contain a JSON object.")
    return result


def captions(pipe):
    return {
        "v4_prompt": {"caption": {"base_caption": pipe.prompt or "", "char_captions": [
            {"char_caption": c.prompt, "centers": [c.center]} for c in pipe.characters]},
            "use_coords": True, "use_order": True, "legacy_uc": False},
        "v4_negative_prompt": {"caption": {"base_caption": pipe.negative_prompt or "", "char_captions": [
            {"char_caption": c.uc, "centers": [c.center]} for c in pipe.characters]},
            "use_coords": False, "use_order": False, "legacy_uc": False},
    }


def build_record(pipe, settings, assets, centers, audit, engine="anima-spatial-alpha-1"):
    # Own field records local semantics; Source/Software never claim NAI origin.
    return {
        "prompt": pipe.prompt, "uc": pipe.negative_prompt,
        "width": settings["width"], "height": settings["height"],
        "seed": settings["seed"], "steps": settings["steps"], "scale": settings["cfg"],
        "sampler": settings["sampler_name"], "noise_schedule": settings["scheduler"],
        **captions(pipe),
        "rs_multicharacter": {"version": 1, "engine": engine,
            "prompt_syntax": pipe.syntax, "settings": settings, "assets": assets,
            "boxes": [c.bbox for c in pipe.characters],
            "character_loras": lora_records(pipe),
            "text_regions": text_region_records(pipe),
            "effective_centers": centers, "spatial_slots": audit["spatial_slots"]},
    }


def text_region_records(pipe):
    return [{"caption": c.prompt, "negative": c.uc, "text": c.text, "center": c.center,
             "bbox": list(c.bbox)} for c in pipe.text_regions]


def validate_format(save_format, quality):
    if save_format not in FORMATS or type(quality) is not int or not 1 <= quality <= 100:
        raise ValueError("Choose PNG/WebP and quality 1–100.")
    if save_format != "PNG" and not features.check("webp"):
        raise ValueError("Pillow WebP support is unavailable. Choose PNG.")


def save_image(image, path, record, save_format="PNG", quality=90):
    validate_format(save_format, quality)
    comment = json.dumps(record, ensure_ascii=True, allow_nan=False)
    object_json(comment)
    fields = {"Title": "Local multi-character generation", "Description": record["prompt"],
              "Software": SOFTWARE, "Source": ENGINE_SOURCES.get(record.get("rs_multicharacter", {}).get("engine"), "Local model"), "Comment": comment}
    path = Path(path).with_suffix(".png" if save_format == "PNG" else ".webp")
    if save_format == "PNG":
        info = PngInfo()
        for key, value in fields.items():
            info.add_text(key, value)
        image.save(path, format="PNG", pnginfo=info, exif=b"")
    else:
        exif = Image.Exif()
        exif[269], exif[270], exif[305] = fields["Title"], fields["Description"], SOFTWARE
        exif[34665] = {37510: b"ASCII\0\0\0" + comment.encode("ascii")}
        image.save(path, format="WEBP", exif=exif, lossless=save_format == "WebP lossless", quality=quality, method=4)
    return path


def read_record(image):
    comment = image.info.get("Comment")
    if comment is None:
        exif = image.getexif()
        comment = exif.get_ifd(34665).get(37510) if 34665 in exif else exif.get(37510)
        if isinstance(comment, bytes):
            if comment.startswith(b"ASCII\0\0\0"):
                comment = comment[8:].rstrip(b"\0").decode("ascii")
            elif comment.startswith(b"UNICODE\0"):
                comment = comment[8:].decode("utf-16").rstrip("\0")
    if comment is None:
        raise ValueError("No character metadata found. Load an original PNG/WebP saved by RS MultiCharacter or a NAI image with V4-style captions. / 캐릭터 메타데이터가 있는 원본 이미지를 불러와 주세요.")
    return object_json(comment)


def pipe_from_record(record):
    try:
        pos = record["v4_prompt"]["caption"]
        neg = record["v4_negative_prompt"]["caption"]
        rows, negatives = pos["char_captions"], neg["char_captions"]
        if not isinstance(rows, list) or not isinstance(negatives, list) or len(rows) != len(negatives):
            raise ValueError("Positive and negative character counts differ.")
        chars = []
        for p, n in zip(rows, negatives):
            if len(p["centers"]) != 1 or n["centers"] != p["centers"]:
                raise ValueError("This loader requires one matching X/Y center per character.")
            c = p["centers"][0]
            chars.append(Character(p["char_caption"], n["char_caption"], c["x"], c["y"]))
        local = record.get("rs_multicharacter")
        if local is not None and (not isinstance(local, dict) or local.get("version") != 1 or local.get("engine") not in ENGINE_SOURCES):
            raise ValueError("Unsupported local metadata version.")
        syntax = local["prompt_syntax"] if local else "NovelAI"
        if local and "boxes" in local:
            boxes = local["boxes"]
            if not isinstance(boxes, list) or len(boxes) != len(chars):
                raise ValueError("Box metadata must match the character count.")
            if any(box is not None and not isinstance(box, list) for box in boxes):
                raise ValueError("Each box must be a coordinate array or null.")
            chars = [replace(c, bbox=tuple(box) if box is not None else None) for c, box in zip(chars, boxes)]
        texts = local.get("text_regions", []) if local else []
        if local and "character_loras" in local:
            loras = local["character_loras"]
            if not isinstance(loras, list) or len(loras) != len(chars) or any(not isinstance(v, dict) for v in loras):
                raise ValueError("LoRA metadata must match the character count.")
            chars = [replace(c, lora_name=v["name"], lora_strength=v["strength_model"],
                             lora_clip_strength=v["strength_clip"]) for c, v in zip(chars, loras)]
        if not isinstance(texts, list) or len(texts) + len(chars) > 10:
            raise ValueError("Text metadata must be a list with at most 10 total regions.")
        text_regions = []
        for item in texts:
            if not isinstance(item, dict) or not isinstance(item.get("bbox"), list):
                raise ValueError("Invalid text region metadata.")
            text_regions.append(TextRegion(item["caption"], item.get("negative", ""),
                item["center"]["x"], item["center"]["y"], tuple(item["bbox"]), item["text"]))
        return CharacterPipe(tuple(chars), pos["base_caption"], neg["base_caption"], syntax,
            json.dumps(local, ensure_ascii=True, allow_nan=False) if local else None, tuple(text_regions))
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError("Incomplete character metadata: common prompts, character captions and X/Y are required.") from error


def graph_assets(prompt, unique_id):
    """Read only allowlisted file names/settings along connected core loaders.

    Unknown node chains remain explicitly unresolved. This does not serialize
    the workflow or run any instruction stored in an image.
    """
    known = {"UNETLoader": ("unet_name", "weight_dtype"), "CheckpointLoaderSimple": ("ckpt_name",),
             "CLIPLoader": ("clip_name", "type", "device"), "VAELoader": ("vae_name",),
             "LoraLoaderModelOnly": ("lora_name", "strength_model"),
             "LoraLoader": ("lora_name", "strength_model", "strength_clip")}
    result = {"loaders": [], "unresolved": []}
    if not isinstance(prompt, dict) or str(unique_id) not in prompt:
        result["unresolved"] = ["Workflow source unavailable"]
        return result
    visited = set()

    def visit(link):
        if not isinstance(link, list) or len(link) != 2 or str(link[0]) in visited:
            return
        node_id = str(link[0])
        visited.add(node_id)
        node = prompt.get(node_id, {})
        kind = node.get("class_type", "unknown")
        inputs = node.get("inputs", {})
        if kind not in known:
            result["unresolved"].append(kind)
            return
        for name in ("model", "clip", "vae"):
            visit(inputs.get(name))
        values = {k: inputs[k] for k in known[kind] if isinstance(inputs.get(k), (str, int, float))}
        result["loaders"].append({"node": kind, **values})
        if len(values) != len(known[kind]):
            result["unresolved"].append(kind + ": dynamic setting")

    inputs = prompt[str(unique_id)].get("inputs", {})
    for name in ("model", "clip", "vae"):
        visit(inputs.get(name))
    return result
