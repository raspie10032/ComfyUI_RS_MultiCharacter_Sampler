# SPDX-License-Identifier: GPL-3.0-only
"""Per-execution LoRA hooks, with the existing regional attention in every pass."""
import torch
import logging
from .characters import LORA_MODES, validate_lora_mode


def lora_records(pipe):
    return [{"name": c.lora_name, "strength_model": c.lora_strength,
             "strength_clip": c.lora_clip_strength} for c in pipe.characters]


def active_lora(character):
    return character.lora_name != "None" and (character.lora_strength != 0 or character.lora_clip_strength != 0)


class RegionalLoras:
    def __init__(self, model, clip, characters):
        import comfy.hooks
        import comfy.lora
        import comfy.lora_convert
        import comfy.utils
        import folder_paths

        self.hooks, self.clips, self.audit = [], [], []
        self.bypasses = {}
        loaded_files, model_combinations, clip_combinations = {}, {}, {}
        model_map = clip_map = None
        names = set(folder_paths.get_filename_list("loras"))
        for slot, character in enumerate(characters, 1):
            if not active_lora(character):
                self.hooks.append(None)
                self.clips.append(clip)
                continue
            name = character.lora_name
            if name not in names:
                raise ValueError(f"Character {slot}: LoRA {name!r} is missing. Put it in ComfyUI models/loras and refresh, or choose None. / 캐릭터 {slot}: LoRA 파일이 없습니다. models/loras에 넣고 새로고침하거나 None을 선택해 주세요.")
            if name not in loaded_files:
                path = folder_paths.get_full_path_or_raise("loras", name)
                weights = comfy.lora_convert.convert_lora(comfy.utils.load_torch_file(path, safe_load=True))
                if model_map is None:
                    model_map = comfy.lora.model_lora_keys_unet(model.model, {})
                    from .flux_engine import flux_family, extend_flux3_lora_map
                    if flux_family(model) == 'FLUX3':
                        extend_flux3_lora_map(model_map)
                    clip_map = comfy.lora.model_lora_keys_clip(clip.cond_stage_model, {})
                loaded_files[name] = (comfy.lora.load_lora(weights, model_map, log_missing=False),
                                      comfy.lora.load_lora(weights, clip_map, log_missing=False))
            model_weights, clip_weights = loaded_files[name]
            if not ((model_weights and character.lora_strength) or (clip_weights and character.lora_clip_strength)):
                raise ValueError(f"Character {slot}: LoRA {name!r} has no weights matching the connected model/CLIP. Choose a LoRA for this model family. / 연결한 모델 계열과 맞는 LoRA를 선택해 주세요.")
            if character.lora_strength and any('llm_adapter' in str(key) for key in model_weights):
                raise ValueError(f"Character {slot}: this LoRA changes Anima's precomputed text adapter, which cannot be separated by sampling hooks. Use it in a global LoRA loader. / 이 LoRA는 Anima 텍스트 어댑터를 변경합니다. 전체 LoRA 로더에 연결해 주세요.")
            model_key = (name, character.lora_strength)
            if model_key not in model_combinations:
                hook_group = None
                if model_weights and character.lora_strength:
                    if name not in self.bypasses:
                        from .lora_bypass import prepare_bypass
                        self.bypasses[name] = prepare_bypass(model, model_weights)
                    bypass, _ = self.bypasses[name]
                    logging.info("RS MC character %s LoRA backend: %s (%s)", slot,
                                 "bypass" if bypass is not None else "weight_hooks", self.bypasses[name][1])
                    if bypass is not None:
                        hook_group = bypass.hook_group(character.lora_strength)
                    else:
                        from .lora_bypass import requires_quantized_bypass
                        if requires_quantized_bypass(model):
                            raise ValueError(f"Character {slot}: this LoRA format cannot be applied regionally to this packed FLUX checkpoint ({self.bypasses[name][1]}). Use a plain linear LoRA for this model, or a non-quantized checkpoint. / 캐릭터 {slot}: 이 양자화 FLUX 모델에는 일반 선형 LoRA가 필요합니다. 해당 모델용 일반 LoRA 또는 비양자화 체크포인트를 사용해 주세요.")
                        hook = comfy.hooks.WeightHook(strength_model=character.lora_strength, strength_clip=0.)
                        hook.weights, hook.weights_clip, hook.need_weight_init = model_weights, {}, False
                        hook_group = comfy.hooks.HookGroup()
                        hook_group.add(hook)
                model_combinations[model_key] = hook_group
            clip_key = (name, character.lora_clip_strength)
            if clip_key not in clip_combinations:
                char_clip = clip
                if clip_weights and character.lora_clip_strength:
                    char_clip = clip.clone()
                    char_clip.add_patches(clip_weights, character.lora_clip_strength)
                clip_combinations[clip_key] = char_clip
            hook_group, char_clip = model_combinations[model_key], clip_combinations[clip_key]
            self.hooks.append(hook_group)
            self.clips.append(char_clip)
            bypass, reason = self.bypasses.get(name, (None, "no_model_strength"))
            self.audit.append({"character": slot, "name": name,
                "strength_model": character.lora_strength, "strength_clip": character.lora_clip_strength,
                "model_keys": len(model_weights), "clip_keys": len(clip_weights),
                "model_backend": "bypass" if bypass is not None and hook_group is not None else "weight_hooks" if hook_group is not None else "none",
                "backend_reason": reason})

    def install(self, model):
        """Release factor copies at the outer sampling boundary, also on errors."""
        from comfy.patcher_extension import WrappersMP

        if any(plan is not None for plan, _ in self.bypasses.values()):
            model.add_wrapper_with_key(WrappersMP.OUTER_SAMPLE, "rs_mc_lora_cleanup", self.sample)

    def sample(self, executor, *args, **kwargs):
        try:
            return executor(*args, **kwargs)
        finally:
            for plan, _ in self.bypasses.values():
                if plan is not None:
                    plan.release()

    def condition_pair(self, model, positive, negative, masks, regions, mode="precision"):
        import comfy.hooks

        validate_lora_mode(mode)
        self.execution = {"requested": mode, "effective": "none", "fallback_reason": None}
        if not any(self.hooks):
            return positive, negative
        if mode == "normal":
            from .shared_lora import SharedRegionalLora, SharedLoraUnsupported
            try:
                shared = SharedRegionalLora(self, model, masks, regions)
            except SharedLoraUnsupported as error:
                # Capability detection completes before any runtime patches.
                # Programming/runtime errors still propagate to the user.
                self.execution["fallback_reason"] = str(error)
                logging.info("RS MC normal LoRA uses precision fallback: %s", error)
            else:
                shared.install(model)
                self.shared = shared
                self.execution["effective"] = "normal"
                return positive, negative
        self.execution["effective"] = "precision"
        self.install(model)
        model.hook_mode = comfy.hooks.EnumHookMode.MinVram
        groups = grouped_masks(self.hooks, masks, regions)
        result = [], []
        for hook, mask in groups:
            for source, dest in zip((positive, negative), result):
                cond = comfy.hooks.set_mask_for_conditioning(source, mask, "default", 1.)
                dest.extend(comfy.hooks.set_hooks_for_conditioning(cond, hook))
        return result


def grouped_masks(hooks, masks, regions):
    """Box priority, normalized overlaps, and unmodified background/text regions."""
    weights = masks.clone()
    boxes = [i for i, c in enumerate(regions) if c.bbox is not None]
    points = [i for i, c in enumerate(regions) if c.bbox is None]
    if boxes and points:
        occupied = weights[boxes].sum(0).clamp(0, 1)
        weights[points] *= 1 - occupied
    coverage = weights.sum(0)
    weights /= coverage.clamp_min(1.)
    grouped = {None: (1 - coverage).clamp(0, 1)}
    for i, mask in enumerate(weights):
        hook = hooks[i] if i < len(hooks) else None
        grouped[hook] = grouped.get(hook, torch.zeros_like(mask)) + mask
    return [(hook, mask) for hook, mask in grouped.items() if bool(mask.any())]
