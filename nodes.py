# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
import torch

from .characters import CharacterPipe, PIPE_TYPE
from .layout import effective_centers, region_masks
from .metadata import (FORMATS, build_record, graph_assets, pipe_from_record,
                       read_record, save_image, validate_format, object_json)
from .prompt_syntax import parse_naiv4, to_comfyui

DEFAULTS = dict(width=1536, height=768, steps=30, cfg=4., sampler_name="euler_ancestral",
                scheduler="sgm_uniform", region_feather=.04, initial_common_prior=.05,
                common_after_step3_boost=.1, initial_character_gain=1.7,
                initial_spatial_separation=.9, boundary_hold_steps=3, boundary_decrement=.2)


def validate_settings(settings):
    from comfy.samplers import KSampler
    for name in ("width", "height"):
        v = settings[name]
        if type(v) is not int or not 64 <= v <= 4096 or v % 16:
            raise ValueError("This sampler needs dimensions divisible by 16, from 64 to 4096.")
    if type(settings["seed"]) is not int or not 0 <= settings["seed"] <= 2**64 - 1:
        raise ValueError("Seed must be an unsigned 64-bit integer.")
    if type(settings["steps"]) is not int or not 2 <= settings["steps"] <= 100:
        raise ValueError("Use 2–100 sampling steps; Krea2 Turbo starts at 8, MOSS at 50.")
    if settings["sampler_name"] not in KSampler.SAMPLERS:
        raise ValueError(f"Sampler {settings['sampler_name']!r} is unavailable in this ComfyUI installation. Choose an installed sampler.")
    if settings["scheduler"] not in KSampler.SCHEDULERS:
        raise ValueError(f"Scheduler {settings['scheduler']!r} is unavailable in this ComfyUI installation. Choose an installed scheduler.")
    ranges = {"cfg": (1., 20.), "region_feather": (0., .25), "initial_common_prior": (0., 1.),
              "common_after_step3_boost": (0., 1.), "initial_character_gain": (1., 3.),
              "initial_spatial_separation": (0., .99), "boundary_decrement": (.01, 1.)}
    for key, (lo, hi) in ranges.items():
        value = settings[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f"{key} must be a finite number from {lo} to {hi}.")
    if type(settings["boundary_hold_steps"]) is not int or not 1 <= settings["boundary_hold_steps"] <= 30:
        raise ValueError("Boundary hold must be 1–30 steps.")


class RSMultiCharacterSampler:
    @classmethod
    def INPUT_TYPES(cls):
        from comfy.samplers import KSampler
        return {"required": {
            "model": ("MODEL",), "clip": ("CLIP",), "vae": ("VAE",),
            "character_pipe": (PIPE_TYPE,),
            "prompt": ("STRING", {"default": "masterpiece, best quality, 5girls, university campus", "multiline": True}),
            "negative_prompt": ("STRING", {"default": "low quality, bad anatomy, text, watermark", "multiline": True}),
            "width": ("INT", {"default": 1536, "min": 64, "max": 4096, "step": 16}),
            "height": ("INT", {"default": 768, "min": 64, "max": 4096, "step": 16}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            "steps": ("INT", {"default": 30, "min": 2, "max": 100, "tooltip": "Anima/SDXL: 30; Krea2 Turbo: 8; MOSS: 50. Common weight rises every 3 scheduled steps. Boundary hold uses sampling steps and is capped by the selected step count."}),
            "cfg": ("FLOAT", {"default": 4., "min": 1., "max": 20., "step": .1}),
            "sampler_name": (list(KSampler.SAMPLERS), {"default": "euler_ancestral",
                "tooltip": "All installed samplers are selectable. Anima starting points: euler_ancestral + sgm_uniform; euler + linear_quadratic; dpmpp_2m_sde_gpu + beta. Compared at 30 steps / CFG 4, one two-character scene and seed; quality varies. SDXL: euler_ancestral + normal. Krea2 Turbo / MOSS: euler + simple, with the matching example settings."}),
            "scheduler": (list(KSampler.SCHEDULERS), {"default": "sgm_uniform",
                "tooltip": "All installed schedulers are selectable. Anima: try sgm_uniform with euler_ancestral, linear_quadratic with euler, or beta with dpmpp_2m_sde_gpu. SDXL: normal with euler_ancestral. Krea2 Turbo / MOSS: simple with euler. Choose the pair manually; changing a sampler does not reset this value."}),
            "autosave": ("BOOLEAN", {"default": True}),
            "save_format": (FORMATS, {"default": "PNG"}),
            "webp_quality": ("INT", {"default": 90, "min": 1, "max": 100}),
        }, "optional": {
            "prompt_syntax": (["ComfyUI", "NovelAI"], {"default": "ComfyUI"}),
            "use_image_settings": ("BOOLEAN", {"default": False,
                "tooltip": "An image pipe always supplies its prompts/characters. Enable to also restore dimensions, seed, sampling and routing settings. Connected model/LoRA/CLIP/VAE remain your choice; check the image loader report."}),
            "region_feather": ("FLOAT", {"default": .04, "min": 0., "max": .25, "step": .01}),
            "initial_common_prior": ("FLOAT", {"default": .05, "min": 0., "max": 1., "step": .01}),
            "common_after_step3_boost": ("FLOAT", {"default": .1, "min": 0., "max": 1., "step": .05}),
            "initial_character_gain": ("FLOAT", {"default": 1.7, "min": 1., "max": 3., "step": .1}),
            "initial_spatial_separation": ("FLOAT", {"default": .9, "min": 0., "max": .99, "step": .05}),
            "boundary_hold_steps": ("INT", {"default": 3, "min": 1, "max": 30}),
            "boundary_decrement": ("FLOAT", {"default": .2, "min": .01, "max": 1., "step": .01}),
        }, "hidden": {"workflow_prompt": "PROMPT", "unique_id": "UNIQUE_ID"}}

    RETURN_TYPES = ("IMAGE", "LATENT", PIPE_TYPE, "STRING")
    RETURN_NAMES = ("image", "latent", "character_pipe", "generation_info")
    FUNCTION = "generate"
    CATEGORY = "RS MultiCharacter"
    OUTPUT_NODE = True
    DESCRIPTION = "Anima / SDXL / Krea2 / MOSS beta; SD1.5 generation is experimental and unstable. 1–10 independent character prompts and X/Y regions. Validation coverage differs by model; see the examples and validation docs. Horizontal arrangements work best. Coordinates control prompt regions, not exact body positions. More characters do not guarantee quality. Autosaves NAI-shaped metadata without a workflow."

    def generate(self, model, clip, vae, character_pipe, prompt, negative_prompt, width=1536, height=768,
                 seed=0, steps=30, cfg=4., sampler_name="euler_ancestral", scheduler="sgm_uniform",
                 autosave=True, save_format="PNG", webp_quality=90, prompt_syntax="ComfyUI",
                 use_image_settings=False, region_feather=.04, initial_common_prior=.05,
                 common_after_step3_boost=.1, initial_character_gain=1.7, initial_spatial_separation=.9,
                 boundary_hold_steps=3, boundary_decrement=.2, workflow_prompt=None, unique_id=None):
        import comfy.model_management
        import comfy.sample
        import comfy.utils
        import folder_paths
        import latent_preview
        from comfy import model_base, supported_models
        from comfy.patcher_extension import WrappersMP

        if not isinstance(character_pipe, CharacterPipe):
            raise ValueError("Connect RS MultiCharacter Prompts or Load Image. / 전용 캐릭터 파이프를 연결해 주세요.")
        if isinstance(model.model, getattr(model_base, "Anima", ())):
            family = "Anima"
        elif type(model.model) is model_base.SDXL and model.model.diffusion_model.in_channels == 4:
            family = "SDXL"
        elif (type(model.model) is model_base.BaseModel
              and type(model.model.model_config) is supported_models.SD15
              and model.model.diffusion_model.in_channels == 4):
            family = "SD1.5"
        elif isinstance(model.model, getattr(model_base, "Krea2", ())):
            family = "Krea2"
        elif isinstance(model.model, getattr(model_base, "MOSSImage", ())):
            family = "MOSS"
        else:
            raise ValueError("Connect Anima, SD1.5 base, SDXL base, Krea2 or MOSS-Image. Krea2/MOSS need a current ComfyUI with native model support. SD2, Refiner, inpainting, instruct-pix2pix and Flux are unsupported.")
        transformer_options = model.model_options.get("transformer_options", {})
        if any(transformer_options.get(k) for k in ("patches", "patches_replace", "optimized_attention_override")):
            raise ValueError("Use an unpatched model, optionally with ordinary LoRA loaders. Other attention patches are unsupported.")
        if any(c.uc.strip() for c in character_pipe.characters):
            raise ValueError("Character-specific negatives are not supported in this beta. Move them to the common negative prompt. / 캐릭터별 네거티브는 현재 미지원입니다. 공통 네거티브에 입력해 주세요.")
        settings = {k: v for k, v in locals().items() if k in DEFAULTS or k == "seed"}
        if character_pipe.prompt is not None:
            prompt, negative_prompt, prompt_syntax = character_pipe.prompt, character_pipe.negative_prompt, character_pipe.syntax
        if use_image_settings:
            if character_pipe.generation_json is None:
                raise ValueError("No local settings in this pipe. Disable 'use_image_settings' and use the sampler settings.")
            stored = object_json(character_pipe.generation_json).get("settings", {})
            if not all(k in stored for k in (*DEFAULTS, "seed")):
                raise ValueError("Image generation settings are incomplete.")
            settings = {k: stored[k] for k in (*DEFAULTS, "seed")}
        validate_settings(settings)
        validate_format(save_format, webp_quality)
        if not isinstance(prompt, str) or not isinstance(negative_prompt, str) or prompt_syntax not in ("ComfyUI", "NovelAI"):
            raise ValueError("Choose valid prompt text and syntax.")
        pipe = CharacterPipe(character_pipe.characters, prompt, negative_prompt, prompt_syntax)
        centers, moved = effective_centers(pipe.characters)
        masks = region_masks(centers, settings["width"], settings["height"], settings["region_feather"])
        convert = (lambda text: to_comfyui(parse_naiv4(text))) if prompt_syntax == "NovelAI" else (lambda text: text)

        def encode(text):
            comfy.model_management.throw_exception_if_processing_interrupted()
            result = clip.encode_from_tokens_scheduled(clip.tokenize(convert(text)))
            if len(result) != 1:
                raise ValueError("Scheduled text is unsupported in this beta.")
            t, meta = result[0]
            if family == "Anima" and "t5xxl_ids" not in meta:
                raise ValueError("Connect Anima's matching text encoder.")
            if family == "SD1.5" and (t.ndim != 3 or t.shape[0] != 1 or t.shape[-1] != 768):
                raise ValueError("Connect the SD1.5 checkpoint's matching CLIP-L encoder.")
            if family == "SDXL":
                pooled = meta.get("pooled_output")
                if t.ndim != 3 or t.shape[-1] != 2048 or pooled is None or pooled.shape[-1] != 1280:
                    raise ValueError("Connect the SDXL checkpoint's matching dual CLIP encoder.")
                meta = {**meta, "width": settings["width"], "height": settings["height"],
                        "target_width": settings["width"], "target_height": settings["height"],
                        "crop_w": 0, "crop_h": 0}
            if family in ("Krea2", "MOSS"):
                expected = 30720 if family == "Krea2" else 4096
                if t.ndim != 3 or t.shape[0] != 1 or t.shape[-1] != expected:
                    kind = "krea2" if family == "Krea2" else "moss_image"
                    raise ValueError(f"Connect the matching {family} text encoder with CLIPLoader type {kind!r}.")
            return [[t, dict(meta)]]

        positive, negative = encode(prompt), encode(negative_prompt)
        conditions = [encode(c.prompt)[0] for c in pipe.characters]
        audit = {}
        work = model.clone()
        if family == "Anima":
            from .engine import AnimaRouting
            routing = AnimaRouting(conditions, masks, "character_first", audit,
                len(positive[0][1]["t5xxl_ids"]),
                initial_common_prior=settings["initial_common_prior"],
                initial_character_gain=settings["initial_character_gain"],
                initial_spatial_separation=settings["initial_spatial_separation"], late_spatial_separation=0.,
                common_weight_schedule="step_3x0.2", spatial_separation_schedule="hold_decay",
                boundary_hold_steps=min(settings["boundary_hold_steps"], settings["steps"]), boundary_decrement=settings["boundary_decrement"],
                common_after_step3_boost=settings["common_after_step3_boost"])
            work.add_wrapper_with_key(WrappersMP.SAMPLER_SAMPLE, "rs_multicharacter", routing.sample)
            work.add_wrapper_with_key(WrappersMP.DIFFUSION_MODEL, "rs_multicharacter", routing.forward)
        elif family in ("SD1.5", "SDXL"):
            from .sdxl_engine import SDXLRouting
            routing = SDXLRouting(conditions, masks, settings, audit, family=family)
            routing.install(work)
        else:
            from .joint_engine import JointRouting
            routing = JointRouting(family, conditions, masks, settings, audit)
            routing.install(work)
        latent = torch.zeros((1, 4, settings["height"] // 8, settings["width"] // 8), device=comfy.model_management.intermediate_device())
        if family in ("SD1.5", "SDXL"):
            # Already 4-channel H/8 x W/8; older ComfyUI has no ratio keyword.
            latent = comfy.sample.fix_empty_latent_channels(work, latent)
        else:
            latent = comfy.sample.fix_empty_latent_channels(work, latent, downscale_ratio_spacial=8)
        noise = comfy.sample.prepare_noise(latent, settings["seed"])
        samples = comfy.sample.sample(work, noise, settings["steps"], settings["cfg"],
            settings["sampler_name"], settings["scheduler"], positive, negative, latent, denoise=1.,
            callback=latent_preview.prepare_callback(work, settings["steps"]),
            disable_pbar=not comfy.utils.PROGRESS_BAR_ENABLED, seed=settings["seed"], force_full_denoise=False)
        images = vae.decode(samples)
        if images.ndim == 5 and images.shape[1] == 1:
            images = images.flatten(0, 1)
        if images.ndim != 4 or images.shape[0] != 1 or not torch.isfinite(images).all():
            raise RuntimeError("The decoder returned invalid images.")
        assets = graph_assets(workflow_prompt, unique_id)
        record = build_record(pipe, settings, assets, centers, audit, engine=family.lower()+"-spatial-alpha-1")
        enriched = CharacterPipe(pipe.characters, prompt, negative_prompt, prompt_syntax,
            json.dumps(record["rs_multicharacter"], ensure_ascii=True))
        summary = {**record, "auto_layout_groups": moved, "cross_attention_calls": audit["cross_calls"],
                   "self_attention_calls": audit["self_calls"], "restored_forwards": audit["restored_forwards"], "routing_audit": audit}
        ui = {"text": [f"{len(pipe.characters)} character regions · seed {settings['seed']} · {family} beta"]}
        if autosave:
            folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
                "RS_MultiCharacter/RS_MC", folder_paths.get_output_directory(), settings["width"], settings["height"])
            pixels = (images[0].detach().cpu().clamp(0, 1).numpy() * 255.).astype(np.uint8)
            try:
                path = save_image(Image.fromarray(pixels), Path(folder) / f"{filename}_{counter:05}_.png",
                                  record, save_format, webp_quality)
            except (OSError, ValueError) as error:
                raise RuntimeError(f"Generation completed, but autosave failed: {error}") from error
            ui["images"] = [{"filename": path.name, "subfolder": subfolder, "type": "output"}]
        return {"ui": ui, "result": (images, {"samples": samples}, enriched, json.dumps(summary, ensure_ascii=False))}


class RSMultiCharacterLoadImage:
    @classmethod
    def INPUT_TYPES(cls):
        import nodes
        return nodes.LoadImage.INPUT_TYPES()

    RETURN_TYPES = ("IMAGE", "MASK", PIPE_TYPE, "STRING")
    RETURN_NAMES = ("image", "mask", "character_pipe", "generation_info")
    FUNCTION = "load"
    CATEGORY = "RS MultiCharacter"
    DESCRIPTION = "Loads NAI-shaped character metadata from original PNG/WebP into the dedicated character pipe. Model files are shown as information and never loaded automatically. Use sampler 'use_image_settings' to restore local seed/settings as well."

    def load(self, image):
        import folder_paths
        path = folder_paths.get_annotated_filepath(image)
        with Image.open(path) as source:
            record = read_record(source)
            pipe = pipe_from_record(record)
            original_size = source.size
            oriented = ImageOps.exif_transpose(source)
            if oriented.size != original_size or source.getexif().get(274, 1) != 1:
                raise ValueError("EXIF-oriented image: rotate/export it without changing the recorded coordinate system first.")
            pixels = np.asarray(oriented.convert("RGB"), dtype=np.float32) / 255.
            mask = 1. - np.asarray(oriented.getchannel("A"), dtype=np.float32) / 255. if "A" in oriented.getbands() else np.zeros(pixels.shape[:2], dtype=np.float32)
        return torch.from_numpy(pixels)[None], torch.from_numpy(mask.copy())[None], pipe, json.dumps(record, ensure_ascii=False)

    @classmethod
    def IS_CHANGED(cls, image):
        import folder_paths
        with open(folder_paths.get_annotated_filepath(image), "rb") as f:
            return hashlib.file_digest(f, "sha256").hexdigest()

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        import folder_paths
        return True if folder_paths.exists_annotated_filepath(image) else f"Image not found: {image}"
