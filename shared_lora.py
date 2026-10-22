# SPDX-License-Identifier: GPL-3.0-only
"""Experimental Anima/SDXL single-evaluation regional LoRA; clone opt-in.

This changes the denoising algorithm: hidden states are shared between regions.
It is not numerically equivalent to mixing independent model predictions.
Image paths receive spatial deltas; cross-attention K/V receive caption deltas.
Common/negative caption deltas use the spatially averaged adapter strength.
"""
from contextlib import contextmanager
from functools import partial
import re

import torch
import torch.nn.functional as F

from .lora_bypass import linear_layer
from .regional_lora import grouped_masks


class SharedLoraUnsupported(ValueError):
    """A known capability limit; safe to select independent predictions."""


def layer_role(path):
    """Classify by model semantics, never by coincident tensor dimensions."""
    if re.fullmatch(r"blocks\.\d+\.cross_attn\.[kv]_proj", path):
        return "text"
    if re.fullmatch(r"blocks\.\d+\.(self_attn\.(q_proj|k_proj|v_proj|output_proj)|cross_attn\.(q_proj|output_proj)|mlp\.layer[12])", path):
        return "image"
    if re.fullmatch(r"(?:input_blocks\.\d+\.\d+|middle_block\.\d+|output_blocks\.\d+\.\d+)\.transformer_blocks\.\d+\.attn2\.to_[kv]", path):
        return "text"
    if re.fullmatch(r"(?:input_blocks\.\d+\.\d+|middle_block\.\d+|output_blocks\.\d+\.\d+)\.(?:proj_(?:in|out)|transformer_blocks\.\d+\.(?:attn[12]\.(?:to_[qkv]|to_out\.0)|ff\.net\.(?:0\.proj|2)))", path):
        return "image"
    raise SharedLoraUnsupported(f"Shared regional LoRA does not support layer {path!r}.")


class SharedRegionalLora:
    def __init__(self, loras, model, masks, regions):
        try:
            from comfy.weight_adapter.bypass import BypassForwardHook
            from comfy.weight_adapter.lora import LoRAAdapter
        except ImportError as error:
            raise SharedLoraUnsupported("Shared regional LoRA requires native LoRA bypass support in ComfyUI.") from error
        if not callable(getattr(LoRAAdapter, 'h', None)):
            raise SharedLoraUnsupported("Shared regional LoRA requires native LoRA delta support in ComfyUI.")
        from comfy import model_base
        from comfy.patcher_extension import WrappersMP
        from .engine import AnimaRouting
        from .sdxl_engine import SDXLRouting

        self.is_sdxl = isinstance(model.model, model_base.SDXL)
        model_types = tuple(t for name in ('Anima', 'SDXL')
                            if isinstance((t := getattr(model_base, name, None)), type))
        if not isinstance(model.model, model_types):
            raise SharedLoraUnsupported("Shared regional LoRA requires Anima or SDXL.")
        wrappers = model.get_all_wrappers(WrappersMP.DIFFUSION_MODEL)
        routers = [w.__self__ for w in wrappers if isinstance(getattr(w, '__self__', None), (AnimaRouting, SDXLRouting))]
        if len(routers) != 1:
            raise ValueError("Shared regional LoRA requires exactly one matching attention router.")
        self.routing = routers[0]
        self.loras = loras
        self.entries = []
        records = {a['character'] - 1: a for a in loras.audit}
        grouped = dict(grouped_masks(loras.hooks, masks, regions))
        by_name = {}
        for slot, hook in enumerate(loras.hooks):
            if hook is None:
                continue
            record = records[slot]
            name = record['name']
            plan, reason = loras.bypasses[name]
            if plan is None or not plan.supports_shared:
                raise SharedLoraUnsupported(f"Shared regional LoRA requires plain linear adapters: {name}: {reason}.")
            if name not in by_name:
                by_name[name] = [plan, torch.zeros_like(masks[0]), [0.] * len(regions), set()]
            entry = by_name[name]
            entry[2][slot] = record['strength_model']
            if hook not in entry[3]:
                entry[1] += grouped[hook] * record['strength_model']
                entry[3].add(hook)
        for plan, mask, strengths, _ in by_name.values():
            for path in plan.layer_paths:
                layer_role(path)
            self.entries.append((plan, mask, strengths))
        self.audit = dict(backend="shared_layers", diffusion_forwards=0, base_layer_calls=0,
                          adapter_calls=0, restored_forwards=0,
                          text_policy="own_caption; common_and_negative_spatial_average")
        self.mask_cache = {}

    def install(self, model):
        from comfy.patcher_extension import WrappersMP
        # Added after the attention router: context here is already concatenated.
        model.add_wrapper_with_key(WrappersMP.DIFFUSION_MODEL, 'rs_mc_shared_lora', self.forward)
        model.add_wrapper_with_key(WrappersMP.OUTER_SAMPLE, 'rs_mc_shared_lora_cleanup', self.sample)
        for record in self.loras.audit:
            if record['strength_model']:
                record['model_backend'] = 'shared_layers'
        self.routing.audit['shared_lora'] = self.audit

    def sample(self, executor, *args, **kwargs):
        try:
            return executor(*args, **kwargs)
        finally:
            self.mask_cache.clear()
            for plan, _, _ in self.entries:
                plan.release()

    def token_weights(self, mask, strengths, grid, lengths, device, dtype, role):
        key = (id(mask), tuple(grid), tuple(lengths), device, dtype, role)
        if key not in self.mask_cache:
            spatial = F.interpolate(mask[None, None].float(), grid, mode='area')[0, 0].to(device=device, dtype=dtype)
            if role == 'image':
                weights = spatial.flatten()
            else:
                weights = torch.cat([spatial.mean().expand(lengths[0]), *[
                    spatial.new_full((length,), strength) for length, strength in zip(lengths[1:], strengths)]])
            self.mask_cache[key] = weights
        return self.mask_cache[key]

    def layer_forward(self, original, adapters, role, grid, lengths, x, *args, **kwargs):
        base = original(x, *args, **kwargs)
        self.audit['base_layer_calls'] += 1
        if role == 'image':
            if tuple(x.shape[1:-1]) not in ((grid[0] * grid[1],), (1, *grid)):
                raise ValueError(f"Unexpected Anima image-token shape: {tuple(x.shape)}.")
        elif x.ndim != 3 or x.shape[1] != sum(lengths):
            raise ValueError("Unexpected Anima caption-token shape.")
        for adapter, mask, strengths in adapters:
            weights = self.token_weights(mask, strengths, grid, lengths, base.device, base.dtype, role)
            weights = weights.reshape((1, *x.shape[1:-1], 1))
            base = base + adapter.h(x, base) * weights
            self.audit['adapter_calls'] += 1
        return base

    def sdxl_layer_forward(self, original, adapters, role, original_grid, lengths, x, *args, **kwargs):
        from .sdxl_engine import attention_grid
        base = original(x, *args, **kwargs)
        self.audit['base_layer_calls'] += 1
        if role == 'image':
            if x.ndim != 3:
                raise ValueError('Unexpected SDXL image-token layout.')
            grid = attention_grid(original_grid, x.shape[1])
        else:
            if x.ndim != 3 or x.shape[1] != sum(lengths):
                raise ValueError('Unexpected SDXL caption-token layout.')
            # Text K/V have no spatial dimension. Common tokens use the
            # full-canvas weighted mean, own character captions use full LoRA.
            grid = original_grid
        for adapter, mask, strengths in adapters:
            weights = self.token_weights(mask, strengths, grid, lengths, base.device, base.dtype, role)
            base = base + adapter.h(x, base) * weights[None, :, None]
            self.audit['adapter_calls'] += 1
        return base

    @contextmanager
    def installed(self, runtime, grid, lengths):
        from comfy.weight_adapter.bypass import BypassForwardHook
        layers = {}
        for plan, mask, strengths in self.entries:
            for path, (_, adapter, _) in zip(plan.layer_paths, plan.layers):
                layers.setdefault(path, []).append((adapter, mask, strengths))
        previous = []
        try:
            for path, adapters in layers.items():
                module = runtime.get_submodule(path)
                if not linear_layer(module) or any(tuple(module.weight.shape) != a.rs_mc_full_shape for a, _, _ in adapters):
                    raise ValueError(f"Shared regional LoRA: incompatible runtime layer {path!r}.")
                for adapter, _, _ in adapters:
                    # Native setup handles dtype/device and adapter alpha/rank.
                    helper = BypassForwardHook(module, adapter, multiplier=1.)
                    from comfy.model_management import get_torch_device
                    helper._move_adapter_weights_to_device(get_torch_device(), module.weight.dtype)
                state = {k: module.__dict__[k] for k in ('forward', 'comfy_force_forward') if k in module.__dict__}
                previous.append((module, state))
                layer_forward = self.sdxl_layer_forward if getattr(self, 'is_sdxl', False) else self.layer_forward
                module.forward = partial(layer_forward, module.forward, adapters, layer_role(path), grid, lengths)
                module.comfy_force_forward = True
            yield
        finally:
            for module, state in reversed(previous):
                for key in ('forward', 'comfy_force_forward'):
                    if key in state:
                        setattr(module, key, state[key])
                    else:
                        module.__dict__.pop(key, None)

    def forward(self, executor, x, timesteps, context, *args, **kwargs):
        model = executor.class_obj
        if self.is_sdxl:
            state = self.routing.state
            if state is None:
                raise RuntimeError('Run SDXL attention routing before shared LoRA.')
            grid = tuple(x.shape[-2:])
            lengths = state['text_lengths']
            with self.installed(model, grid, lengths):
                self.audit['diffusion_forwards'] += 1
                result = executor(x, timesteps, context, *args, **kwargs)
            self.audit['restored_forwards'] += 1
            return result
        contexts = self.routing.contexts
        if contexts is None or self.routing.groups is None:
            raise RuntimeError("Run the Anima attention router before shared LoRA.")
        lengths = [context.shape[1] - sum(c.shape[1] for c in contexts), *[c.shape[1] for c in contexts]]
        if lengths[0] <= 0 or len(lengths) != len(self.entries[0][2]) + 1:
            raise ValueError("Shared regional LoRA caption layout mismatch.")
        grid = tuple(s // model.patch_spatial for s in x.shape[-2:])
        with self.installed(model, grid, lengths):
            self.audit['diffusion_forwards'] += 1
            result = executor(x, timesteps, context, *args, **kwargs)
        self.audit['restored_forwards'] += 1
        return result
