# SPDX-License-Identifier: GPL-3.0-only
"""Local masked img2img with original character prompts and immutable crops."""
import json
import math
from pathlib import Path
from types import SimpleNamespace

import torch
import torch.nn.functional as F

from .characters import CharacterPipe, PIPE_TYPE
from .detection import RepairedDetector, _detect, _context_crop, _crop_box, _native_crop_mask
from .detector_bundle import DetectionBundle
from .detailer_matching import Match, match_characters, selected_prompts
from .image_utils import tensor_to_pil, validate_single_image
from .metadata import FORMATS, captions, graph_assets, object_json, save_image, validate_format, text_region_records
from .prompt_syntax import parse_naiv4, to_comfyui
from .runtime_control import check_interrupted
from .regional_lora import RegionalLoras, active_lora, lora_records


def _prompts(pipe):
    convert = (lambda text: to_comfyui(parse_naiv4(text))) if pipe.syntax == "NovelAI" else (lambda text: text)
    chars = [SimpleNamespace(prompt=convert(c.prompt), uc=convert(c.uc)) for c in pipe.characters]
    return convert(pipe.prompt or ""), convert(pipe.negative_prompt or ""), chars


def _resize(image, size):
    return F.interpolate(image.movedim(-1, 1), size=size, mode="bicubic", align_corners=False,
                         antialias=True).movedim(1, -1)


def _sample_crop(crop, mask, *, model, clip, vae, positive, negative, seed, steps, cfg,
                 sampler_name, scheduler, denoise, guide_size, max_size, lora_hook=None, lora_runtime=None):
    from nodes import common_ksampler
    check_interrupted()
    height, width = crop.shape[1:3]
    ratio = int(vae.spacial_compression_encode())
    multiple = math.lcm(16, ratio)
    scale = min(guide_size / min(height, width), max_size / max(height, width))
    nh, nw = [max(multiple, int(v * scale) // multiple * multiple) for v in (height, width)]
    pixels = _resize(crop, (nh, nw)).clamp(0, 1)
    noise_mask = F.interpolate(mask[None, None].float(), size=(nh, nw), mode="nearest")[:, 0]
    positive_cond = clip.encode_from_tokens_scheduled(clip.tokenize(positive))
    negative_cond = clip.encode_from_tokens_scheduled(clip.tokenize(negative))
    latent = vae.encode(pixels)
    if latent.ndim not in (4, 5) or latent.shape[0] != 1 or (latent.ndim == 5 and latent.shape[2] != 1):
        raise ValueError("Use an image VAE or Anima single-frame VAE. / 이미지용 또는 Anima 단일 프레임 VAE를 연결해 주세요.")
    if not torch.isfinite(latent).all():
        raise ValueError("VAE encoding produced nonfinite values; check the VAE and its precision.")
    if lora_hook is not None:
        import comfy.hooks
        model = model.clone()
        model.hook_mode = comfy.hooks.EnumHookMode.MinVram
        if lora_runtime is not None:
            lora_runtime.install(model)
        positive_cond = comfy.hooks.set_hooks_for_conditioning(positive_cond, lora_hook)
        negative_cond = comfy.hooks.set_hooks_for_conditioning(negative_cond, lora_hook)
    sampled = common_ksampler(model, seed, steps, cfg, sampler_name, scheduler, positive_cond,
                             negative_cond, {"samples": latent, "noise_mask": noise_mask}, denoise=denoise)[0]
    decoded = vae.decode(sampled["samples"])
    if decoded.ndim == 5 and decoded.shape[1] == 1:
        decoded = decoded.flatten(0, 1)
    if decoded.ndim != 4 or decoded.shape[0] != 1 or decoded.shape[-1] != 3 or not torch.isfinite(decoded).all():
        raise ValueError("VAE must decode one finite RGB image. / VAE 출력이 정상적인 RGB 이미지 한 장이 아닙니다.")
    return _resize(decoded.to(crop), (height, width)).clamp(0, 1), (nw, nh)


def _validate(settings):
    from comfy.samplers import KSampler
    ints = {"seed": (0, 2**64-1), "steps": (1, 100), "max_regions": (1, 64),
            "guide_size": (128, 2048), "max_size": (128, 4096), "dilation": (0, 128), "mask_feather": (0, 64)}
    floats = {"denoise": (.01, 1.), "cfg": (0., 30.), "bbox_threshold": (.01, 1.),
              "crop_factor": (1., 8.), "match_min_score": (0., 1.), "match_min_margin": (0., 1.),
              "match_crop_factor": (1., 4.)}
    for key, (lo, hi) in {**ints, **floats}.items():
        v = settings[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi or (key in ints and type(v) is not int):
            raise ValueError(f"{key} must be {'an integer' if key in ints else 'a finite number'} from {lo} to {hi}.")
    for key, choices in (("sampler_name", KSampler.SAMPLERS), ("scheduler", KSampler.SCHEDULERS)):
        if settings[key] not in choices:
            raise ValueError(f"Unavailable {key}: {settings[key]!r}. Select an installed option.")
    for key in ("fill_holes", "closing"):
        if type(settings[key]) is not bool:
            raise ValueError(f"{key} must be true or false.")


def detail_record(pipe, width, height, settings, assets, report):
    local = object_json(pipe.generation_json) if pipe.generation_json else {
        "version": 1, "engine": "anima-spatial-alpha-1", "prompt_syntax": pipe.syntax,
        "source": "character pipe without local generation settings"}
    # A detail pass must never replace the original T2I settings with crop settings.
    history = local.get("detail_history", [])
    if not isinstance(history, list):
        raise ValueError("Invalid detail history in character metadata.")
    local["detail_history"] = [*history, {"engine": "local-masked-img2img-v1", "settings": settings,
        "assets": assets, "image_size": [width, height], "report": report}]
    local["boxes"] = [list(c.bbox) if c.bbox is not None else None for c in pipe.characters]
    local["text_regions"] = text_region_records(pipe)
    local["character_loras"] = lora_records(pipe)
    original = local.get("settings", {})
    record = {"prompt": pipe.prompt or "", "uc": pipe.negative_prompt or "", "width": width, "height": height,
              **captions(pipe), "rs_multicharacter": local}
    for key, value in (("seed", "seed"), ("steps", "steps"), ("scale", "cfg"),
                       ("sampler", "sampler_name"), ("noise_schedule", "scheduler")):
        if value in original:
            record[key] = original[value]
    return record


class RSMultiCharacterDetailer:
    @classmethod
    def INPUT_TYPES(cls):
        from comfy.samplers import KSampler
        return {"required": {
            "image": ("IMAGE",), "model": ("MODEL",), "clip": ("CLIP",), "vae": ("VAE",),
            "character_pipe": (PIPE_TYPE,), "detectors": ("RS_MC_DETECTION_BUNDLE",),
            "denoise": ("FLOAT", {"default": .25, "min": .01, "max": 1., "step": .01}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            "autosave": ("BOOLEAN", {"default": True}),
        }, "optional": {
            "tagger": ("RS_MC_TAGGER", {"tooltip": "Required for multiple characters. Scores only select your original prompt; ambiguous regions are preserved."}),
            "show_advanced": ("BOOLEAN", {"default": False}),
            "steps": ("INT", {"default": 20, "min": 1, "max": 100}),
            "cfg": ("FLOAT", {"default": 4., "min": 0., "max": 30., "step": .1}),
            "sampler_name": (list(KSampler.SAMPLERS), {"default": "euler_ancestral"}),
            "scheduler": (list(KSampler.SCHEDULERS), {"default": "sgm_uniform"}),
            "guide_size": ("INT", {"default": 768, "min": 128, "max": 2048, "step": 64,
                "tooltip": "Target crop short side. max_size caps the long side. More resolution requires more VRAM."}),
            "max_size": ("INT", {"default": 1024, "min": 128, "max": 4096, "step": 64}),
            "max_regions": ("INT", {"default": 10, "min": 1, "max": 64,
                "tooltip": "Maximum regions to edit, not character count. More processed regions do not guarantee quality."}),
            "bbox_threshold": ("FLOAT", {"default": .3, "min": .01, "max": 1., "step": .01}),
            "crop_factor": ("FLOAT", {"default": 3., "min": 1., "max": 8., "step": .1}),
            "dilation": ("INT", {"default": 8, "min": 0, "max": 128}),
            "fill_holes": ("BOOLEAN", {"default": True}),
            "closing": ("BOOLEAN", {"default": True}),
            "mask_feather": ("INT", {"default": 8, "min": 0, "max": 64}),
            "match_min_score": ("FLOAT", {"default": .25, "min": 0., "max": 1., "step": .01}),
            "match_min_margin": ("FLOAT", {"default": .08, "min": 0., "max": 1., "step": .01}),
            "match_crop_factor": ("FLOAT", {"default": 2., "min": 1., "max": 4., "step": .1}),
            "save_format": (FORMATS, {"default": "PNG"}),
            "webp_quality": ("INT", {"default": 90, "min": 1, "max": 100}),
        }, "hidden": {"workflow_prompt": "PROMPT", "unique_id": "UNIQUE_ID"}}

    RETURN_TYPES = ("IMAGE", "MASK", PIPE_TYPE, "STRING")
    RETURN_NAMES = ("image", "edited_mask", "character_pipe", "region_report")
    FUNCTION = "detail"
    CATEGORY = "RS MultiCharacter"
    OUTPUT_NODE = True
    DESCRIPTION = ("Local character-aware correction. Connect the sampler/image loader image and character pipe, "
        "the same MODEL/CLIP/VAE (including LoRA), Detection Loader and Tagger Loader. Each crop uses one original "
        "character prompt. Ambiguous matches are skipped. SEGM has priority over BBOX/SAM. "
        "Fills small holes/notches, adds dilation and feathers inside disjoint masks. "
        "Autosave keeps generation metadata and appends detail history without a workflow. "
        "More regions do not guarantee quality. / 처리수가 많을수록 품질을 보장하지 못합니다.")

    def detail(self, image, model, clip, vae, character_pipe, detectors, denoise=.25, seed=0, autosave=True,
               tagger=None, show_advanced=False, steps=20, cfg=4., sampler_name="euler_ancestral",
               scheduler="sgm_uniform", guide_size=768, max_size=1024, max_regions=10, bbox_threshold=.3,
               crop_factor=3., dilation=8, fill_holes=True, closing=True, mask_feather=8,
               match_min_score=.25, match_min_margin=.08, match_crop_factor=2., save_format="PNG",
               webp_quality=90, workflow_prompt=None, unique_id=None):
        settings = {k: v for k, v in locals().items() if k in (
            "denoise", "seed", "steps", "cfg", "sampler_name", "scheduler", "guide_size", "max_size", "max_regions",
            "bbox_threshold", "crop_factor", "dilation", "fill_holes", "closing", "mask_feather",
            "match_min_score", "match_min_margin", "match_crop_factor")}
        _validate(settings)
        validate_single_image(image)
        validate_format(save_format, webp_quality)
        if not isinstance(character_pipe, CharacterPipe):
            raise ValueError("Connect an RS MultiCharacter pipe. / 전용 캐릭터 파이프를 연결해 주세요.")
        if not isinstance(detectors, DetectionBundle) or (detectors.segm_detector is None and detectors.bbox_detector is None):
            raise ValueError("Select SEGM or BBOX in RS Detection Loader. SAM alone cannot find regions. / SEGM 또는 BBOX를 선택해 주세요.")
        if not character_pipe.characters:
            raise ValueError("The detailer needs a character prompt. Text regions are not face-matching candidates. / 디테일러에는 캐릭터 프롬프트가 필요합니다.")
        if len(character_pipe.characters) > 1 and not callable(getattr(tagger, "score", None)):
            raise ValueError("Multiple characters need RS Tagger Loader for matching. / 여러 캐릭터를 구분하려면 태거 로더를 연결해 주세요.")
        from .mask_repair import inside_alpha
        from .tagger_progress import TaggerProgress
        progress = TaggerProgress(unique_id)
        prompt, negative, chars = _prompts(character_pipe)
        source = tensor_to_pil(image)
        width, height = source.size
        repaired = RepairedDetector(detectors, closing=closing, fill_holes=fill_holes, dilation=dilation)
        progress.report("Detecting regions…", force=True)
        regions = _detect(repaired, image, bbox_threshold, dilation, crop_factor)
        regions.sort(key=lambda s: ((s.bbox[0] + s.bbox[2]) / 2, (s.bbox[1] + s.bbox[3]) / 2))
        count = min(len(regions), max_regions)
        matches = [Match(0, 1., 1., "single_character") for _ in regions]
        retried = set()
        if len(chars) > 1 and count:
            progress.report("Matching original character prompts…", force=True)
            scores = tagger.score([_context_crop(source, s.bbox, match_crop_factor) for s in regions[:count]])
            if len(scores) != count:
                raise ValueError("Tagger returned the wrong number of regions.")
            matches[:count] = [match_characters(s, chars, match_min_score, match_min_margin) for s in scores]
            uncertain = [i for i in range(count) if matches[i].character_index is None]
            if uncertain and match_crop_factor > 1.25:
                retried.update(uncertain)
                scores = tagger.score([_context_crop(source, regions[i].bbox, 1.25) for i in uncertain])
                if len(scores) != len(uncertain):
                    raise ValueError("Tagger retry returned the wrong number of regions.")
                for i, score in zip(uncertain, scores):
                    matches[i] = match_characters(score, chars, match_min_score, match_min_margin)
        out, used, items = image.clone(), torch.zeros_like(image[..., 0]), []
        loras = None
        for i, (seg, match) in enumerate(zip(regions, matches)):
            check_interrupted()
            rect = _crop_box(seg.crop_region, width, height)
            item = {"region": i+1, "bbox": list(map(float, seg.bbox)), "crop": list(rect),
                "character": (match.character_index+1 if match.character_index is not None and i < count else None),
                "status": "skipped", "reason": match.reason if i < count else "max_regions",
                "score": match.score if i < count else None, "margin": match.margin if i < count else None,
                "tight_crop_retried": i in retried, "mask_repair": seg.repair_report}
            items.append(item)
            if i >= count or match.character_index is None:
                continue
            owns = _native_crop_mask(seg, rect) > .5
            if not owns.any():
                item["reason"] = "empty_mask"
                continue
            x0, y0, x1, y1 = rect
            crop = image[:, y0:y1, x0:x1, :].clone()
            positive, uc = selected_prompts(prompt, negative, chars, match)
            region_seed = (seed + i) % (1 << 64)
            progress.report(f"Region {i+1}/{count} → character {item['character']}", i/max(1, count), force=True)
            mask = torch.from_numpy(owns.copy()).to(crop.device)
            lora_options = {}
            if active_lora(character_pipe.characters[match.character_index]):
                if loras is None:
                    loras = RegionalLoras(model, clip, character_pipe.characters)
                lora_options = {"lora_hook": loras.hooks[match.character_index], "lora_runtime": loras}
                item["lora"] = lora_records(character_pipe)[match.character_index]
            crop_clip = loras.clips[match.character_index] if loras else clip
            edited, size = _sample_crop(crop, mask, model=model, clip=crop_clip, vae=vae,
                positive=positive, negative=uc, seed=region_seed, steps=steps, cfg=cfg,
                sampler_name=sampler_name, scheduler=scheduler, denoise=denoise, guide_size=guide_size, max_size=max_size, **lora_options)
            alpha = torch.from_numpy(inside_alpha(owns, mask_feather)).to(crop)[None, ..., None]
            target = out[:, y0:y1, x0:x1, :]
            out[:, y0:y1, x0:x1, :] = torch.where(mask[None, ..., None], crop*(1-alpha)+edited*alpha, target)
            used[:, y0:y1, x0:x1] = torch.maximum(used[:, y0:y1, x0:x1], mask[None].to(used))
            item.update(status="edited", seed=region_seed, sample_size=list(size),
                        positive=positive, negative=uc, mask_pixels=int(owns.sum()))
        edited_count = sum(r["status"] == "edited" for r in items)
        report = {"status": "completed" if edited_count else "no_detections" if not regions else "no_confident_matches",
                  "detected": len(regions), "edited": edited_count, "skipped": len(regions)-edited_count, "regions": items}
        record = detail_record(character_pipe, width, height, settings, graph_assets(workflow_prompt, unique_id), report)
        enriched = CharacterPipe(character_pipe.characters, character_pipe.prompt, character_pipe.negative_prompt,
                                 character_pipe.syntax, json.dumps(record["rs_multicharacter"], ensure_ascii=True, allow_nan=False), text_regions=character_pipe.text_regions)
        text = f"{edited_count}/{len(regions)} regions corrected · {report['skipped']} preserved"
        ui = {"text": [text], "rs_mc_report": [report]}
        if autosave:
            import folder_paths
            folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
                "RS_MultiCharacter/RS_MC_detail", folder_paths.get_output_directory(), width, height)
            try:
                path = save_image(tensor_to_pil(out), Path(folder)/f"{filename}_{counter:05}_.png", record, save_format, webp_quality)
            except (OSError, ValueError) as error:
                raise RuntimeError(f"Detailing finished, but autosave failed: {error}") from error
            ui["images"] = [{"filename": path.name, "subfolder": subfolder, "type": "output"}]
        progress.report(text, 1., force=True)
        return {"ui": ui, "result": (out, used, enriched, json.dumps(report, ensure_ascii=False, allow_nan=False))}
