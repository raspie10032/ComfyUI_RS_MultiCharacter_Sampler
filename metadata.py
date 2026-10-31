# SPDX-License-Identifier: GPL-3.0-only
"""NAI-shaped captions with an explicitly local generation extension.

No ComfyUI workflow, authentication, arbitrary graph inputs or model weights.
"""
import json
import gzip
import io
from dataclasses import replace
from pathlib import Path

from PIL import Image, features
from PIL.PngImagePlugin import PngInfo
import numpy as np

from .characters import Character, CharacterPipe, TextRegion
from .regional_lora import lora_records
from .region_mask import RegionMask, mask_records

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
            "character_masks": mask_records(pipe),
            **({"body_parts": [[{"name":name,"mask":mask.record()} for name,mask in c.body_parts]
                               for c in pipe.characters],
                "body_part_strengths": [c.body_part_strength for c in pipe.characters]}
               if any(c.body_parts for c in pipe.characters) else {}),
            **({"interaction": json.loads(pipe.interaction_json)} if pipe.interaction_json else {}),
            **({'pose3d': json.loads(pipe.pose3d_json)} if pipe.pose3d_json else {}),
            "character_loras": lora_records(pipe),
            "image_references": [{"character_id": c.reference.character_id, "resolution": c.reference.resolution,
                                  "strength": c.reference.strength, "source": c.reference.source,
                                  **({"method": "anima_role_kv"} if type(c.reference).__name__ == 'RoleKVImageReference' else {}),
                                  **({"method": "anima_reference_frame"} if type(c.reference).__name__ == 'FrameImageReference' else {})}
                                 for c in pipe.characters if c.reference is not None],
            **({"anima_reference_frame": dict(audit['anima_reference_frame'])}
               if 'anima_reference_frame' in audit else {}),
            **({"anima_role_kv": dict(audit['anima_role_kv'])} if 'anima_role_kv' in audit else {}),
            "lora_application_mode": pipe.lora_application_mode,
            "text_regions": text_region_records(pipe),
            **({"nai_context": object_json(pipe.nai_settings_json)} if pipe.nai_settings_json else {}),
            "character_syntax": pipe.character_syntax,
            "effective_centers": centers, "spatial_slots": audit["spatial_slots"]},
    }


def _pose_record(local):
    if not local or 'pose3d' not in local:
        return None
    from .pose_pipe import pipe_pose_settings
    return json.dumps(pipe_pose_settings(local['pose3d']))


def pipe_record(pipe):
    """Current scene plus separate local/NAI settings, without graph or tensors."""
    local = object_json(pipe.generation_json) if pipe.generation_json else {
        "version": 1, "engine": "anima-spatial-alpha-1"}
    local.update(prompt_syntax=pipe.syntax, character_syntax=pipe.character_syntax,
        scene_prompt_available=pipe.prompt is not None,
        boxes=[list(c.bbox) if c.bbox else None for c in pipe.characters],
        character_masks=mask_records(pipe), character_loras=lora_records(pipe),
        lora_application_mode=pipe.lora_application_mode,
        body_parts=[[{"name": name, "mask": mask.record()} for name, mask in c.body_parts]
                    for c in pipe.characters],
        body_part_strengths=[c.body_part_strength for c in pipe.characters],
        text_regions=text_region_records(pipe))
    if pipe.pose3d_json is None:
        local.pop('pose3d', None)
    else:
        local['pose3d'] = json.loads(pipe.pose3d_json)
    if pipe.interaction_json is None:
        local.pop("interaction", None)
    else:
        local["interaction"] = json.loads(pipe.interaction_json)
    if pipe.nai_settings_json:
        local["nai_context"] = object_json(pipe.nai_settings_json)
    else:
        local.pop("nai_context", None)
    result = {"prompt": pipe.prompt or "", "uc": pipe.negative_prompt or "",
              **captions(pipe), "rs_multicharacter": local}
    object_json(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return result


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
    fields = {k: image.info[k] for k in ("Comment", "rs_nai", "rs_detailer_regions", "rs_nai_inset") if k in image.info}
    exif = image.getexif()
    if 37395 in exif:
        extra = object_json(exif[37395])
        fields.update({k: v for k, v in extra.items() if k in ("Comment", "rs_nai", "rs_detailer_regions", "rs_nai_inset")})
    # Official NAI PNGs can store their JSON in column-major alpha LSBs.
    if "A" in image.getbands():
        alpha = np.asarray(image.getchannel("A")).T.reshape(-1)
        header = np.packbits(alpha[:152] & 1).tobytes()
        if header[:15] == b"stealth_pngcomp":
            bits = int.from_bytes(header[15:19], "big")
            if bits % 8 or bits > MAX_METADATA * 8 or bits > len(alpha) - 152:
                raise ValueError("Invalid hidden metadata length.")
            with gzip.GzipFile(fileobj=io.BytesIO(np.packbits(alpha[152:152+bits] & 1).tobytes())) as stream:
                hidden = object_json(stream.read(MAX_METADATA+1).decode("utf-8"))
            for key in ("Comment", "rs_nai", "rs_detailer_regions", "rs_nai_inset"):
                if key in hidden:
                    fields.setdefault(key, hidden[key])
    if "rs_nai_inset" in fields:
        raise ValueError("Inset coordinates refer to the reference canvas; load the full image instead.")
    if "rs_nai" in fields:
        nai = fields["rs_nai"]
        nai = nai if isinstance(nai, dict) else object_json(nai)
        operation = nai.get("operation")
        if operation == "inset":
            raise ValueError("Inset coordinates refer to the reference canvas.")
        if operation == "detailer":
            if nai.get("base_generation_available") is not True or not isinstance(nai.get("base_generation"), dict):
                raise ValueError("This face correction has no whole-image character context.")
            request = nai["base_generation"]
        else:
            request = nai.get("request", {})
        if isinstance(request, dict) and isinstance(request.get("parameters"), dict):
            effective = {**request["parameters"], "prompt": request.get("input", "")}
            if isinstance(nai.get("nai_context"), dict):
                effective["rs_nai_context"] = nai["nai_context"]
            local_source = nai.get("local_context")
            if isinstance(local_source, dict) and isinstance(local_source.get("rs_multicharacter"), dict):
                local = dict(local_source["rs_multicharacter"])
                # Captions describe the successful NAI request; geometry/model
                # assets remain local. Convert captions once at this boundary.
                from .nai_prompts import local_prompts
                pos = effective.get("v4_prompt", {}).get("caption", {})
                neg = effective.get("v4_negative_prompt", {}).get("caption", {})
                positive, negative = local_prompts(pos.get("base_caption", effective["prompt"]),
                                                   neg.get("base_caption", effective.get("negative_prompt", "")))
                pos = {**pos, "base_caption": positive, "char_captions": [dict(c) for c in pos.get("char_captions", [])]}
                neg = {**neg, "base_caption": negative, "char_captions": [dict(c) for c in neg.get("char_captions", [])]}
                if len(pos["char_captions"]) != len(neg["char_captions"]):
                    raise ValueError("Positive and negative character counts differ.")
                for p, n in zip(pos["char_captions"], neg["char_captions"]):
                    p["char_caption"], n["char_caption"] = local_prompts(p["char_caption"], n["char_caption"])
                if (local.get("character_syntax") or local.get("prompt_syntax")) == "NovelAI":
                    texts = []
                    for item in local.get("text_regions", []):
                        caption, uc = local_prompts(item["caption"], item.get("negative", ""))
                        texts.append({**item, "caption": caption, "negative": uc})
                    local["text_regions"] = texts
                effective["v4_prompt"] = {**effective["v4_prompt"], "caption": pos}
                effective["v4_negative_prompt"] = {**effective["v4_negative_prompt"], "caption": neg}
                local.update(prompt_syntax="ComfyUI", character_syntax="ComfyUI")
                if "rs_nai_context" in effective:
                    local["nai_context"] = effective["rs_nai_context"]
                # A smaller NAI model exports only its active character slots.
                for key in ("boxes", "character_masks", "character_loras", "body_parts", "body_part_strengths"):
                    if isinstance(local.get(key), list):
                        local[key] = local[key][:len(pos["char_captions"])]
                effective["rs_multicharacter"] = local
            return effective
    elif "rs_detailer_regions" in fields:
        raise ValueError("Legacy face metadata describes a crop, not the whole image.")
    comment = fields.get("Comment")
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
    result = comment if isinstance(comment, dict) else object_json(comment)
    if "Comment" in result:
        result = result["Comment"] if isinstance(result["Comment"], dict) else object_json(result["Comment"])
    return result


def pipe_from_record(record):
    try:
        if isinstance(record.get("v4_prompt"), dict) and record["v4_prompt"].get("use_coords") is False:
            raise ValueError("Automatic NAI coordinates cannot be restored as explicit local positions.")
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
        if local and "character_masks" in local:
            masks = local["character_masks"]
            if not isinstance(masks, list) or len(masks) != len(chars):
                raise ValueError("Mask metadata must match the character count.")
            chars = [replace(c, region_mask=RegionMask.from_record(mask) if mask is not None else None)
                     for c, mask in zip(chars, masks)]
        if local and "character_loras" in local:
            loras = local["character_loras"]
            if not isinstance(loras, list) or len(loras) != len(chars) or any(not isinstance(v, dict) for v in loras):
                raise ValueError("LoRA metadata must match the character count.")
            chars = [replace(c, lora_name=v["name"], lora_strength=v["strength_model"],
                             lora_clip_strength=v["strength_clip"]) for c, v in zip(chars, loras)]
        if local is None:
            from .nai_prompts import local_prompts
            import logging
            if len(chars) > 10:
                logging.warning("[RS MC] Local multi-character uses characters 1–10; source image metadata is preserved. / 로컬은 1~10번만 사용합니다.")
            converted = []
            for c in chars[:10]:
                prompt, uc = local_prompts(c.prompt, c.uc)
                converted.append(replace(c, prompt=prompt, uc=uc))
            chars = converted
            base_prompt, base_negative = local_prompts(pos["base_caption"], neg["base_caption"])
            syntax = "ComfyUI"
        else:
            base_prompt, base_negative = pos["base_caption"], neg["base_caption"]
        if not isinstance(texts, list) or len(texts) + len(chars) > 10:
            raise ValueError("Text metadata must be a list with at most 10 total regions.")
        if local and "body_parts" in local:
            parts, strengths = local['body_parts'], local.get('body_part_strengths')
            if (not isinstance(parts,list) or len(parts)!=len(chars) or not isinstance(strengths,list) or len(strengths)!=len(chars)
                or any(not isinstance(p,list) or len(p)>6 for p in parts)):
                raise ValueError('Body-part masks must match character rows.')
            chars = [replace(c,body_parts=tuple((p['name'],RegionMask.from_record(p['mask'])) for p in row),
                             body_part_strength=strength) for c,row,strength in zip(chars,parts,strengths)]
        interaction_json = None
        if local and 'interaction' in local:
            from .interaction import interaction_settings
            interaction_json = json.dumps(interaction_settings(local['interaction']))
        text_regions = []
        for item in texts:
            if not isinstance(item, dict) or not isinstance(item.get("bbox"), list):
                raise ValueError("Invalid text region metadata.")
            text_regions.append(TextRegion(item["caption"], item.get("negative", ""),
                item["center"]["x"], item["center"]["y"], tuple(item["bbox"]), item["text"]))
        return CharacterPipe(tuple(chars), base_prompt if not local or local.get("scene_prompt_available", True) else None, base_negative, syntax,
            json.dumps(local, ensure_ascii=True, allow_nan=False) if local else None, tuple(text_regions),
            lora_application_mode=local.get("lora_application_mode", "precision") if local else "precision",
            interaction_json=interaction_json,
            pose3d_json=_pose_record(local),
            character_syntax=local.get("character_syntax") if local else "ComfyUI",
            nai_settings_json=json.dumps(local["nai_context"] if local and "nai_context" in local else record["rs_nai_context"], allow_nan=False)
                if (local and "nai_context" in local) or "rs_nai_context" in record else None)
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
