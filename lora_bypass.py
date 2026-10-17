# SPDX-License-Identifier: GPL-3.0-only
"""Execution-scoped, factor-only LoRA for ordinary Anima Linear layers.

Conditioning hooks still select separate predictions. Only the weight application
changes: ComfyUI's native bypass evaluates W(x) + up(down(x)), without expanding
the factors into a checkpoint-sized patch or backing up the base weights.
"""
import copy
from functools import partial

import torch


def prepare_bypass(model, weights):
    """Return (plan, reason). Unsupported formats stay on native weight hooks.

    Validate the entire file before using it: applying only some of its patches via
    bypass would silently change the LoRA. Imports stay optional for older ComfyUI.
    """
    from comfy import model_base

    if not isinstance(model.model, getattr(model_base, "Anima", ())):
        return None, "model_family"
    if getattr(model, "get_additional_models_with_key", lambda key: [])("multigpu"):
        return None, "multigpu_clones"
    try:
        from comfy.weight_adapter.bypass import BypassForwardHook
        from comfy.weight_adapter.lora import LoRAAdapter
        from comfy.hooks import TransformerOptionsHook
    except ImportError:
        return None, "core_without_bypass"
    if not weights:
        return None, "no_model_weights"
    layers = []
    for key, adapter in weights.items():
        # Tuple keys can represent offsets/functions; DoRA, LoHa, LoKr, diff,
        # reshape and convolutional patches need the existing weight path.
        if not isinstance(key, str) or not key.endswith(".weight") or type(adapter) is not LoRAAdapter:
            return None, "patch_type"
        if "llm_adapter" in key:
            return None, "text_adapter"
        values = adapter.weights
        if len(values) != 6 or any(v is not None for v in values[3:]):
            return None, "extended_lora"
        up, down, alpha = values[:3]
        if not all(isinstance(v, torch.Tensor) and v.ndim == 2 and v.is_floating_point() for v in (up, down)):
            return None, "factor_type"
        if alpha is not None and not isinstance(alpha, (int, float)):
            return None, "alpha_type"
        try:
            module = model.model.get_submodule(key[:-len(".weight")])
        except AttributeError:
            return None, "missing_layer"
        if not isinstance(module, torch.nn.Linear):
            return None, "nonlinear_layer"
        weight = module.weight
        if (type(weight) not in (torch.Tensor, torch.nn.Parameter)
                or weight.dtype not in (torch.float32, torch.float16, torch.bfloat16)
                or getattr(module, "comfy_force_forward", False)):
            return None, "custom_or_quantized_layer"
        if (up.shape[1] != down.shape[0] or down.shape[0] == 0
                or tuple(weight.shape) != (up.shape[0], down.shape[1])):
            return None, "factor_shape"
        # A shallow copy shares the original CPU factors. Strength combinations
        # use this same adapter/GPU storage; only its scalar multiplier changes.
        layers.append((module, copy.copy(adapter), adapter.weights))
    return BypassLora(layers, BypassForwardHook, TransformerOptionsHook), "plain_linear_lora"


class BypassLora:
    def __init__(self, layers, hook_type, options_type):
        self.layers = layers
        self.hook_type, self.options_type = hook_type, options_type
        self.forward_calls = 0

    @property
    def factor_bytes(self):
        return sum(v.numel() * v.element_size() for _, _, weights in self.layers
                   for v in weights if isinstance(v, torch.Tensor))

    def hook_group(self, strength):
        from comfy.hooks import EnumHookScope, HookGroup
        from comfy.patcher_extension import WrappersMP

        group = HookGroup()
        group.add(self.options_type({"wrappers": {WrappersMP.DIFFUSION_MODEL: {
            "rs_mc_lora_bypass": [partial(self.forward, strength=strength)]}}},
            hook_scope=EnumHookScope.HookedOnly))
        return group

    def forward(self, executor, *args, strength, **kwargs):
        installed = []
        try:
            for module, adapter, _ in self.layers:
                # Native inject also handles ComfyUI's dynamic forward dispatch.
                hook = self.hook_type(module, adapter, multiplier=strength)
                state = {key: module.__dict__.get(key) for key in ("forward", "comfy_force_forward")}
                present = {key for key in state if key in module.__dict__}
                installed.append((hook, module, state, present))
                hook.inject()
            self.forward_calls += 1
            return executor(*args, **kwargs)
        finally:
            # This also runs on partial injection failure and cancellation.
            for hook, module, state, present in reversed(installed):
                hook.eject()
                for key, value in state.items():
                    if key in present:
                        setattr(module, key, value)
                    else:
                        module.__dict__.pop(key, None)

    def release(self):
        # Drop compute-device copies even when the model patcher remains loaded.
        # Keep the small original factors for another crop using the same file.
        for _, adapter, original_weights in self.layers:
            adapter.weights = original_weights

