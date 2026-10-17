# SPDX-License-Identifier: GPL-3.0-only
"""SD1.5/SDXL U-Net routing through clone-local ComfyUI patch callbacks.

CLIP-L/G character sequences stay independent until projected by each attn2.
The common prompt supplies the native pooled ADM. Character pooled embeddings
are deliberately not mixed into that global vector: they have no XY dimension.
SD1.5 uses CLIP-L sequences and has no pooled ADM. The class name is retained
for compatibility with existing SDXL callers.
"""
import torch

from .routing import (route_cross, sdpa, token_groups, weak_self_bias,
                      sigma_progress, stepped_common_weight,
                      character_value_gain, hold_decay_spatial_separation)


def attention_grid(original_shape, tokens):
    """Follow U-Net's ceil-divided spatial resolutions, including odd latents."""
    h, w = original_shape[-2:]
    while h * w != tokens:
        if h == 1 and w == 1:
            raise ValueError("U-Net attention has an unsupported spatial token layout.")
        h, w = (h + 1) // 2, (w + 1) // 2
    return h, w


class SDXLRouting:
    def __init__(self, conditions, masks, settings, audit, family="SDXL", boxes=False):
        self.family = family
        self.boxes = boxes
        self.conditions, self.masks = conditions, masks
        self.settings, self.audit = settings, audit
        self.sigmas = self.state = None
        self.groups = {}
        self.biases = {}

    def install(self, work):
        from comfy.patcher_extension import WrappersMP
        from comfy.ldm.modules.attention import BasicTransformerBlock
        net = work.model.diffusion_model
        blocks = []
        for name, modules in (("input", net.input_blocks), ("middle", [net.middle_block]),
                              ("output", net.output_blocks)):
            for index, module in enumerate(modules):
                transformers = [m for m in module.modules() if isinstance(m, BasicTransformerBlock)]
                if not transformers:
                    continue
                if any(m.disable_self_attn or m.attn2 is None or m.switch_temporal_ca_to_sa for m in transformers):
                    raise ValueError(f"This {self.family} U-Net uses an unsupported attention layout.")
                work.set_model_attn1_replace(self.spatial, name, index)
                work.set_model_attn2_replace(self.cross, name, index)
                blocks.append([name, index, len(transformers)])
        if not blocks:
            raise ValueError(f"No {self.family} U-Net attention blocks were found.")
        self.audit["installed_blocks"] = blocks
        work.add_wrapper_with_key(WrappersMP.SAMPLER_SAMPLE, "rs_multicharacter", self.sample)
        work.add_wrapper_with_key(WrappersMP.DIFFUSION_MODEL, "rs_multicharacter", self.forward)

    def sample(self, executor, *args, **kwargs):
        self.sigmas = args[1].detach().cpu().tolist()[:-1]
        self.audit.update(evaluation_sigmas=self.sigmas, cross_calls=0, self_calls=0,
                          restored_forwards=0, forwards=[], spatial_slots=len(self.masks),
                          pooled_conditioning=("none" if self.family == "SD1.5" else "common_prompt_native_adm"), token_grids=[])
        self.groups.clear()
        self.biases.clear()
        try:
            return executor(*args, **kwargs)
        finally:
            self.state = self.sigmas = None
            self.groups.clear()
            self.biases.clear()

    def forward(self, executor, x, timesteps, context, y=None, control=None, transformer_options=None, **kwargs):
        options = transformer_options or {}
        kinds = options.get("cond_or_uncond")
        if not kinds or x.ndim != 4 or x.shape[0] != len(kinds):
            raise ValueError(f"{self.family} regional generation supports image batch size 1 only.")
        if self.sigmas is None:
            raise RuntimeError(f"{self.family} routing was not initialized by the sampler.")
        sigma = float(options["sigmas"][0])
        progress = sigma_progress(sigma, self.sigmas)
        s = self.settings
        common = stepped_common_weight(progress, len(self.sigmas), s["initial_common_prior"],
                                       .2, s["common_after_step3_boost"])
        gain = character_value_gain(progress, s["initial_character_gain"])
        separation = hold_decay_spatial_separation(progress, len(self.sigmas),
            s["initial_spatial_separation"], min(s["boundary_hold_steps"], len(self.sigmas)), s["boundary_decrement"])
        lengths = [context.shape[1]]
        pieces = [context]
        for condition, _ in self.conditions:
            c = condition.to(context)
            if c.ndim != 3 or c.shape[0] != 1 or c.shape[2] != context.shape[2]:
                raise ValueError(f"Connect the {self.family} checkpoint's matching text encoder.")
            pieces.append(torch.cat([c if kind == 0 else torch.zeros_like(c) for kind in kinds], 0))
            lengths.append(c.shape[1])
        record = dict(sigma=sigma, progress=progress, kinds=list(kinds), text_lengths=lengths,
                      common_prior=common, character_value_gain=gain, spatial_separation=separation,
                      cross_calls=0, self_calls=0)
        self.audit["forwards"].append(record)
        previous = self.state
        self.state = record
        self.biases.clear()
        try:
            return executor(x, timesteps, torch.cat(pieces, 1), y, control, options, **kwargs)
        finally:
            self.state = previous
            self.biases.clear()
            self.audit["restored_forwards"] += 1

    def _inputs(self, q, k, v, options):
        if self.state is None:
            raise RuntimeError(f"{self.family} attention called outside its routing scope.")
        if list(options["cond_or_uncond"]) != self.state["kinds"]:
            raise ValueError(f"{self.family} CFG batch order changed inside a model evaluation.")
        h, w = attention_grid(options["original_shape"], q.shape[1])
        key = (h, w, q.device)
        if key not in self.groups:
            self.groups[key] = token_groups(self.masks, h, w, q.device, boxes=self.boxes)
            self.audit["token_grids"].append({"height": h, "width": w,
                "tokens_per_slot": [len(g) for g in self.groups[key]]})
        heads = options["n_heads"]
        dtype = torch.float32 if options.get("attn_precision") == torch.float32 else q.dtype
        return tuple(t.to(dtype).reshape(t.shape[0], t.shape[1], heads, -1) for t in (q, k, v)), self.groups[key]

    def cross(self, q, k, v, options):
        (qh, kh, vh), groups = self._inputs(q, k, v, options)
        r = self.state
        out = route_cross(qh, kh, vh, groups, r["text_lengths"], r["kinds"],
                          weights=(r["common_prior"], 1.), character_gain=r["character_value_gain"])
        self.audit["cross_calls"] += 1
        r["cross_calls"] += 1
        return out.to(q.dtype)

    def spatial(self, q, k, v, options):
        (qh, kh, vh), groups = self._inputs(q, k, v, options)
        separation = self.state["spatial_separation"]
        bias = None
        if separation:
            key = (q.shape[1], qh.dtype, q.device)
            if key not in self.biases:
                self.biases[key] = weak_self_bias(groups, q.shape[1], qh, separation)
            bias = self.biases[key]
        out = sdpa(qh, kh, vh, bias)
        self.audit["self_calls"] += 1
        self.state["self_calls"] += 1
        return out.to(q.dtype)
