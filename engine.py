# SPDX-License-Identifier: GPL-3.0-only
"""Anima attention routing extracted from the validated local research engine.

Requires ComfyUI's Anima implementation; no sibling custom nodes are imported.
Forward replacements are restored in finally blocks. See docs/architecture.md.
"""

import torch
from comfy.sampler_helpers import convert_cond
from comfy.samplers import process_conds

from .interaction import protected_self_bias, exclusive_schedule
from .routing import (installed_ops, route_cross, route_self, token_groups,
                      common_weight, stepped_common_weight, character_value_gain, staged_character_gain, spatial_separation, stepped_spatial_separation, hold2_decay_spatial_separation, hold_decay_spatial_separation, release_step2_spatial_separation, sigma_progress, weak_self_bias, sdpa)

WEIGHTED = ("weighted_static", "character_first", "character_first_open")
MODES = ("identity", "cross", "cross_self", "cross_compact", "cross_exclusive") + WEIGHTED



class AnimaRouting:
    def __init__(self, conditions, masks, mode, audit, common_tokens, initial_common_prior=0.05, initial_character_gain=1., character_gain_schedule="early_decay", middle_character_gain=1.5, late_character_gain=1.7, initial_spatial_separation=.2, late_spatial_separation=.2, common_weight_schedule="smooth", spatial_separation_schedule="smooth", boundary_hold_steps=3, boundary_decrement=.2, common_after_step3_boost=0., boxes=False):
        self.pose = None
        self.part_cells = None
        self.conditions, self.masks, self.mode = conditions, masks, mode
        self.boxes = boxes
        self.audit = audit
        self.process = None
        self.contexts = None
        self.groups = None
        self.common_tokens = common_tokens
        self.initial_common_prior = initial_common_prior
        self.common_weight_schedule = common_weight_schedule
        self.initial_character_gain = initial_character_gain
        self.character_gain_schedule = character_gain_schedule
        self.middle_character_gain = middle_character_gain
        self.late_character_gain = late_character_gain
        self.initial_spatial_separation = initial_spatial_separation
        self.late_spatial_separation = late_spatial_separation
        self.spatial_separation_schedule = spatial_separation_schedule
        self.boundary_hold_steps = boundary_hold_steps
        self.boundary_decrement = boundary_decrement
        self.common_after_step3_boost = common_after_step3_boost
        self.sigmas = None
        self.spatial_bias = None
        self.spatial_bias_separation = None

    def sample(self, executor, *args, **kwargs):
        guider, sigmas, extra, _, noise, latent, denoise_mask, *_ = args
        actual_sigmas = sigmas.detach().cpu().tolist()
        reference = guider.model_options.get("rs_diag_reference_sigmas")
        if reference is not None:
            if len(reference) < len(actual_sigmas) or reference[:len(actual_sigmas)] != actual_sigmas:
                raise ValueError("Diagnostic stop must preserve the full schedule prefix")
            self.sigmas = list(reference[:-1])
            self.audit["schedule_reference_sigmas"] = self.sigmas
        else:
            self.sigmas = actual_sigmas[:-1]
        self.audit["evaluation_sigmas"] = actual_sigmas[:-1]
        self.spatial_bias = None
        self.spatial_bias_separation = None
        self.contexts = self.groups = self.part_cells = None
        self.audit.update(cross_calls=0, self_calls=0, forwards=[], restored_forwards=0)

        def process():
            converted = [convert_cond([c])[0] for c in self.conditions]
            cooked = process_conds(guider.inner_model, noise, {"positive": converted},
                noise.device, latent, denoise_mask, extra["seed"], latent_shapes=[latent.shape])
            contexts = [c["model_conds"]["c_crossattn"].cond for c in cooked["positive"]]
            self.audit["character_text_tokens"] = [len(c[1]["t5xxl_ids"]) for c in self.conditions]
            if self.mode == "cross_compact":
                # Native adapter pads EACH isolated prompt to 512. Do not add
                # an extra zero-key bank for each character in one softmax.
                contexts = [c[:, :n] for c, n in zip(contexts, self.audit["character_text_tokens"])]
            return contexts

        self.process = process
        try:
            return executor(*args, **kwargs)
        finally:
            self.contexts = self.groups = self.process = self.part_cells = None
            self.spatial_bias = self.sigmas = None
            self.spatial_bias_separation = None

    def forward(self, executor, x, timesteps, context, *args, **kwargs):
        options = kwargs.get("transformer_options", {})
        kinds = options.get("cond_or_uncond")
        if not kinds or x.shape[0] != len(kinds) or x.shape[-3] != 1:
            raise ValueError("Spatial experiment supports image batch size 1 only")
        if self.mode == "identity":
            self.audit["forwards"].append({"kinds": list(kinds), "identity": True})
            return executor(x, timesteps, context, *args, **kwargs)
        model = executor.class_obj
        if self.contexts is None:
            if self.process is None:
                raise RuntimeError("Spatial adapter was not initialized by the sampler")
            self.contexts = self.process()
        if self.groups is None:
            if any(s % model.patch_spatial for s in x.shape[-2:]):
                raise ValueError("Image latent must align with Anima spatial patches")
            h, w = (s // model.patch_spatial for s in x.shape[-2:])
            self.groups = token_groups(self.masks, h, w, x.device, boxes=self.boxes)
            if self.pose is not None:
                from .pose_parts import part_cells
                self.part_cells = part_cells(self.groups, self.pose['parts'], h, w, x.device)
                self.audit['pose_parts']['token_cells'] = [
                    {'owners': list(owners), 'parts': list(parts), 'tokens': len(indices)}
                    for owners, parts, indices in self.part_cells]
            self.audit.update(token_grid=[h, w], spatial_slots=len(self.groups),
                              tokens_per_slot=[len(g) for g in self.groups])
        lengths = [context.shape[1]] + [c.shape[1] for c in self.contexts]
        pieces = [context]
        for c in self.contexts:
            c = c.to(context)
            pieces.append(torch.cat([c if kind == 0 else torch.zeros_like(c) for kind in kinds], 0))
        joined = torch.cat(pieces, 1)
        record = {"sigma": float(options["sigmas"][0]), "kinds": list(kinds),
                  "text_lengths": lengths, "cross_blocks": [], "self_blocks": []}
        weights = None
        gain = 1.
        weighted = self.mode in WEIGHTED
        weak_spatial = self.mode in ("weighted_static", "character_first")
        separation = 0.
        if weighted:
            progress = sigma_progress(record["sigma"], self.sigmas)
            if weak_spatial:
                if self.spatial_separation_schedule == "step_3x0.1":
                    separation = stepped_spatial_separation(progress, len(self.sigmas), self.initial_spatial_separation)
                elif self.spatial_separation_schedule == "step_3x0.2":
                    separation = stepped_spatial_separation(progress, len(self.sigmas), self.initial_spatial_separation, .2)
                elif self.spatial_separation_schedule == "step_3x0.3":
                    separation = stepped_spatial_separation(progress, len(self.sigmas), self.initial_spatial_separation, .3)
                elif self.spatial_separation_schedule == "hold2_step1x0.4":
                    separation = hold2_decay_spatial_separation(progress, len(self.sigmas), self.initial_spatial_separation)
                elif self.spatial_separation_schedule == "hold_decay":
                    separation = hold_decay_spatial_separation(progress, len(self.sigmas), self.initial_spatial_separation, self.boundary_hold_steps, self.boundary_decrement)
                elif self.spatial_separation_schedule == "release_step2":
                    separation = release_step2_spatial_separation(progress, len(self.sigmas), self.initial_spatial_separation)
                else:
                    separation = spatial_separation(progress, self.initial_spatial_separation, self.late_spatial_separation)
            if self.mode == "weighted_static":
                common_prior = 1.
            elif self.common_weight_schedule == "step_3x0.1":
                common_prior = stepped_common_weight(progress, len(self.sigmas), self.initial_common_prior)
            elif self.common_weight_schedule == "step_3x0.2":
                common_prior = stepped_common_weight(progress, len(self.sigmas), self.initial_common_prior, .2, self.common_after_step3_boost)
            else:
                common_prior = common_weight(progress, self.initial_common_prior)
            weights = (common_prior, 1.)
            if self.character_gain_schedule == "staged_rise":
                gain = staged_character_gain(progress, self.initial_character_gain,
                                            self.middle_character_gain, self.late_character_gain)
            else:
                gain = character_value_gain(progress, self.initial_character_gain)
            record.update(progress=progress, common_prior=weights[0], character_prior=weights[1],
                          positive_common_blocked=weights[0] == 0,
                          character_value_gain=gain,
                          common_tokens=self.common_tokens, preserve_native_padding=True,
                          spatial_separation=separation)
        interaction = self.audit.get("interaction")
        exclusive_separation = exclusive_schedule(interaction, progress, len(self.sigmas),
            self.initial_spatial_separation, self.boundary_hold_steps, self.boundary_decrement)
        record["exclusive_spatial_separation"] = exclusive_separation
        self.audit["forwards"].append(record)

        def cross(q, k, v, transformer_options=None, preferred_attention=None):
            q, k, v = (t if isinstance(t, torch.Tensor) else t.take() for t in (q, k, v))
            if self.pose is not None:
                from .pose_parts import route_parts
                result = route_parts(q, k, v, self.groups, lengths, kinds, self.part_cells,
                                     len(self.groups), self.pose['strength'], weights, gain, self.pose.get('bank_ids'))
            else:
                result = route_cross(q, k, v, self.groups, lengths, kinds,
                                     include_common=self.mode != "cross_exclusive", weights=weights, character_gain=gain)
            self.audit["cross_calls"] += 1
            record["cross_blocks"].append(transformer_options["block_index"])
            return result

        def spatial(q, k, v, transformer_options=None, preferred_attention=None):
            q, k, v = (t if isinstance(t, torch.Tensor) else t.take() for t in (q, k, v))
            if weak_spatial:
                bias_key = (separation, exclusive_separation)
                if self.spatial_bias is None or self.spatial_bias_separation != bias_key:
                    self.spatial_bias = protected_self_bias(self.groups, q.shape[1], q, separation, exclusive_separation)
                    self.spatial_bias_separation = bias_key
                if "self_bias_foreign" not in record and len(self.groups) > 1:
                    record["self_bias_foreign"] = float(self.spatial_bias[self.groups[0][0], self.groups[1][0]])
                    record["self_bias_own"] = float(self.spatial_bias[self.groups[0][0], self.groups[0][0]])
                result = sdpa(q, k, v, self.spatial_bias)
            else:
                result = route_self(q, k, v, self.groups)
            self.audit["self_calls"] += 1
            record["self_blocks"].append(transformer_options["block_index"])
            return result

        with installed_ops(model.blocks, cross, spatial if self.mode == "cross_self" or weak_spatial else None):
            result = executor(x, timesteps, joined, *args, **kwargs)
        self.audit["restored_forwards"] += 1
        return result
