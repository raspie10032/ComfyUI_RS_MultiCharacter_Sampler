# SPDX-License-Identifier: GPL-3.0-only
"""Execution-scoped, factor-only LoRA for supported native Linear layers.

Conditioning hooks still select separate predictions. Only the weight application
changes: ComfyUI's native bypass evaluates W(x) + up(down(x)), without expanding
the factors into a checkpoint-sized patch or backing up the base weights.
"""
import copy
from functools import partial

import torch
import torch.nn.functional as F


def linear_layer(module):
    if isinstance(module, torch.nn.Linear):
        return True
    from comfy import ops
    return (isinstance(module, getattr(ops, 'MixedPrecisionOp', ()))
            and type(getattr(module, 'in_features', None)) is int
            and type(getattr(module, 'out_features', None)) is int)


def requires_quantized_bypass(model):
    """Native weight hooks cannot address packed tensors' serialized scale keys."""
    from comfy import model_base
    packed_types = tuple(t for name in ("Flux", "Flux3", "Krea2", "MOSSImage")
                       if isinstance((t := getattr(model_base, name, None)), type))
    if not isinstance(model.model, packed_types):
        return False
    from comfy.quant_ops import QuantizedTensor
    return any(isinstance(getattr(layer, 'weight', None), QuantizedTensor)
               for layer in model.model.modules())


def prepare_bypass(model, weights):
    plan, reason = _prepare_factor_bypass(model, weights)
    if plan is not None or reason in ("model_family", "multigpu_clones", "core_without_bypass", "no_model_weights"):
        return plan, reason
    # Complex adapters need the base weight (DoRA/GLoRA/OFT), not just h(x).
    # Delegate their algebra to the installed core without patching packed weights.
    from .adapter_delta import prepare_weight_delta
    return prepare_weight_delta(model, weights)


def _prepare_factor_bypass(model, weights):
    """Return (plan, reason). Unsupported formats stay on native weight hooks.

    Validate the entire file before using it: applying only some of its patches via
    bypass would silently change the LoRA. Imports stay optional for older ComfyUI.
    """
    from comfy import model_base

    flux_types = tuple(t for name in ("Flux", "Flux3")
                       if isinstance((t := getattr(model_base, name, None)), type))
    is_flux = isinstance(model.model, flux_types)
    is_krea2 = isinstance(model.model, getattr(model_base, "Krea2", ()))
    # Keep the established full-precision MOSS path. Packed MOSS weights have
    # the same serialized scale-key limitation as native FLUX/Krea2 tensors.
    is_packed_moss = (isinstance(model.model, getattr(model_base, "MOSSImage", ()))
                      and requires_quantized_bypass(model))
    # Clone experiment: SDXL's ordinary linear adapters use the same factor
    # path; unsupported convolutional/extended patches retain native hooks.
    is_sdxl = isinstance(model.model, getattr(model_base, "SDXL", ()))
    if not (is_flux or is_krea2 or is_packed_moss or is_sdxl
            or isinstance(model.model, getattr(model_base, "Anima", ()))):
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
    layers, layer_paths = [], []
    for key, adapter in weights.items():
        # Diffusers FLUX Q/K/V factors address slices of a fused Linear layer.
        # Other tuple functions and extended adapters keep the native path.
        offset = None
        if isinstance(key, tuple) and len(key) in (2, 3):
            if len(key) == 3 and key[2] is not None:
                return None, "patch_function"
            key, offset = key[:2]
            if (not isinstance(offset, tuple) or len(offset) != 3
                    or not all(type(v) is int for v in offset)
                    or offset[0] not in (0, 1) or offset[1] < 0 or offset[2] <= 0):
                return None, "patch_offset"
        if not isinstance(key, str) or not key.endswith(".weight") or type(adapter) is not LoRAAdapter:
            return None, "patch_type"
        if not key.startswith("diffusion_model."):
            return None, "non_diffusion_layer"
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
        if not linear_layer(module):
            return None, "nonlinear_layer"
        weight = module.weight
        # Native FLUX/Krea2/MOSS checkpoints use QuantizedTensor weights. The
        # bypass runs the original quantized forward and adds float factors;
        # it never reads/replaces the serialized weight_scale pseudo-keys.
        supported = type(weight) in (torch.Tensor, torch.nn.Parameter) and weight.is_floating_point()
        if is_flux or is_krea2 or is_packed_moss:
            from comfy.quant_ops import QuantizedTensor
            supported = supported or isinstance(weight, QuantizedTensor)
        elif weight.dtype not in (torch.float32, torch.float16, torch.bfloat16):
            supported = False
        if not supported or getattr(module, "comfy_force_forward", False):
            return None, "custom_or_quantized_layer"
        shape = list(weight.shape)
        if offset is not None:
            dim, start, length = offset
            if start + length > shape[dim]:
                return None, "patch_offset"
            shape[dim] = length
        if (up.shape[1] != down.shape[0] or down.shape[0] == 0
                or tuple(shape) != (up.shape[0], down.shape[1])):
            return None, "factor_shape"
        # A shallow copy shares the original CPU factors. Strength combinations
        # use this same adapter/GPU storage; only its scalar multiplier changes.
        local = copy.copy(adapter)
        local.rs_mc_full_shape = tuple(weight.shape)
        if offset is not None:
            local.h = partial(offset_delta, native_h=local.h, offset=offset)
        layers.append((module, local, adapter.weights))
        layer_paths.append(key[len("diffusion_model."):-len(".weight")])
    return BypassLora(layers, layer_paths, BypassForwardHook, TransformerOptionsHook), "plain_linear_lora"


def offset_delta(x, base_out, *, native_h, offset):
    dim, start, length = offset
    if dim == 1:
        return native_h(x[..., start:start+length], base_out)
    delta = native_h(x, base_out[..., start:start+length])
    return F.pad(delta, (start, base_out.shape[-1] - start - length))


class BypassLora:
    supports_shared = True
    def __init__(self, layers, layer_paths, hook_type, options_type):
        self.layers = layers
        self.layer_paths = layer_paths
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
        if strength == 0:
            return executor(*args, **kwargs)
        # CFGGuider can replace ModelPatcherDynamic with a non-dynamic delegate
        # when conditioning carries hooks. The delegate owns NEW modules. Patch
        # the diffusion model actually being called, never preparation-time
        # module references (which would silently leave inference unchanged).
        runtime_model = executor.class_obj
        modules = []
        for path, (_, adapter, _) in zip(self.layer_paths, self.layers):
            module = runtime_model.get_submodule(path)
            if (not linear_layer(module)
                    or tuple(module.weight.shape) != adapter.rs_mc_full_shape):
                raise RuntimeError(f"Regional LoRA: incompatible runtime layer {path!r}.")
            modules.append(module)
        installed = []
        try:
            for module, (_, adapter, _) in zip(modules, self.layers):
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

