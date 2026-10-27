# SPDX-License-Identifier: GPL-3.0-only
"""Clone-local joint text/image attention routing for native Krea2 and MOSS.

Separate text encodes stay isolated through the model's text refiners. Joint
blocks let image queries see common + owning character text; character text
queries see only their own text and image region. Negative evaluations keep
native text, positions and attention. No model method or global is replaced.
"""
import math

import torch
from .resolution_control import separation_for_grid

from .routing import (token_groups, BoxGroups, sigma_progress, stepped_common_weight,
                      character_value_gain, hold_decay_spatial_separation)


def moss_caption_positions(tensor, heads, lengths, image_tokens, pre_shaped=False):
    """Tail-align each isolated caption before the image on MOSS's f axis.

    Native concatenation would put early captions much farther from the image
    than their independent encodes. Translate each caption as a whole; this
    preserves its internal positions and its native distance to image tokens.
    MOSS applies split-half RoPE, with equal (r,f,h,w) frequency groups.
    """
    x = tensor.transpose(1, 2) if pre_shaped else tensor.unflatten(-1, (heads, -1))
    dim = x.shape[-1]
    if dim % 8:
        raise ValueError('Unsupported MOSS rotary head size.')
    out = x.clone()
    start, stop = dim//8, dim//4
    omega = 10000. ** (-torch.arange(0, dim//4, 2, device=x.device, dtype=torch.float64)/(dim//4))
    offset, total = image_tokens, sum(lengths)
    remaining = total
    for length in lengths:
        remaining -= length
        if remaining:
            cos = (remaining*omega).cos().to(torch.float32)
            sin = (remaining*omega).sin().to(torch.float32)
            a = x[:, offset:offset+length, :, start:stop].float()
            b = x[:, offset:offset+length, :, dim//2+start:dim//2+stop].float()
            out[:, offset:offset+length, :, start:stop] = (a*cos-b*sin).to(x.dtype)
            out[:, offset:offset+length, :, dim//2+start:dim//2+stop] = (b*cos+a*sin).to(x.dtype)
        offset += length
    return out.transpose(1, 2) if pre_shaped else out.flatten(2)


class JointRouting:
    def __init__(self, family, conditions, masks, settings, audit, boxes=False):
        self.family, self.conditions, self.masks = family, conditions, masks
        self.reference_lengths = []
        self.reference_latents = []
        self.reference_audit = {}
        self.boxes = boxes
        self.settings, self.audit = settings, audit
        self.sigmas = self.state = None

    def install(self, work):
        from comfy.patcher_extension import WrappersMP
        from .native_reference import attach_native_references
        attach_native_references(self, work)
        self.reference_dm = work.get_model_object('diffusion_model')
        options = work.model_options['transformer_options']
        if options.get('optimized_attention_override'):
            raise ValueError('Disconnect other attention overrides before regional sampling.')
        options['optimized_attention_override'] = self.attention
        work.add_wrapper_with_key(WrappersMP.SAMPLER_SAMPLE, 'rs_multicharacter', self.sample)
        work.add_wrapper_with_key(WrappersMP.DIFFUSION_MODEL, 'rs_multicharacter',
                                  self.krea_forward if self.family == 'Krea2' else self.moss_forward)

    def sample(self, executor, *args, **kwargs):
        self.sigmas = args[1].detach().cpu().tolist()[:-1]
        self.audit.update(evaluation_sigmas=self.sigmas, forwards=[], cross_calls=0,
                          self_calls=0, text_refiner_calls=0, restored_forwards=0,
                          spatial_slots=len(self.masks), family=self.family,
                          negative_attention='native', joint_routing=True)
        try:
            return executor(*args, **kwargs)
        finally:
            self.state = self.sigmas = None

    def krea_forward(self, executor, x, timesteps, context, attention_mask=None,
                     ref_latents=None, transformer_options=None, **kwargs):
        if ref_latents is not None or attention_mask is not None:
            raise ValueError('Krea2 regional sampling currently accepts text-to-image only, without reference latents or attention masks.')
        patch = executor.class_obj.patch
        def invoke(xb, tb, cb, options):
            refs = [r.to(xb) for r in self.reference_latents] if options['cond_or_uncond'] == [0] else []
            self.reference_lengths = [((r.shape[-2]+patch-1)//patch)*((r.shape[-1]+patch-1)//patch) for r in refs]
            self.reference_audit['reference_lengths'] = self.reference_lengths
            if refs:
                hgrid=(xb.shape[-2]+patch-1)//patch;wgrid=(xb.shape[-1]+patch-1)//patch
                options['rs_mc_ref_centers']=[(float((self.state['groups'][r['slot']]%wgrid).float().mean()),float((self.state['groups'][r['slot']]//wgrid).float().mean())) for r in self.reference_plan]
                from .krea_reference_backend import krea2_edit_forward
                return krea2_edit_forward(self.reference_dm, xb, tb, cb, refs, options, ref_native=True)
            return executor(xb, tb, cb, None, None, options, **kwargs)
        return self.forward(invoke, x, timesteps, context, transformer_options,
                            ((x.shape[-2]+patch-1)//patch, (x.shape[-1]+patch-1)//patch))

    def moss_forward(self, executor, x, timesteps, context, transformer_options=None, **kwargs):
        def invoke(xb, tb, cb, options):
            refs = [r.to(xb) for r in self.reference_latents] if options['cond_or_uncond'] == [0] else []
            self.reference_lengths = [r.shape[-2]*r.shape[-1] for r in refs]
            self.reference_audit['reference_lengths'] = self.reference_lengths
            if refs:
                hh,ww=xb.shape[-2:]
                options['rs_mc_ref_centers']=[(float((self.state['groups'][r['slot']]%ww).float().mean()),float((self.state['groups'][r['slot']]//ww).float().mean())) for r in self.reference_plan]
                from .native_reference import moss_reference_forward
                return moss_reference_forward(self.reference_dm, xb, tb, cb, refs, options)
            return executor(xb, tb, cb, options, **kwargs)
        return self.forward(invoke, x, timesteps, context, transformer_options, x.shape[-2:])

    def forward(self, invoke, x, timesteps, context, options, grid):
        options = options or {}
        kinds = options.get('cond_or_uncond')
        if not kinds or len(kinds) != x.shape[0] or any(k not in (0, 1) for k in kinds):
            raise ValueError('Joint regional sampling supports one image per execution.')
        if x.ndim not in (4, 5) or (x.ndim == 5 and x.shape[2] != 1):
            raise ValueError('Use single-frame image latents for regional sampling.')
        if self.sigmas is None:
            raise RuntimeError('Regional routing was not initialized by the sampler.')
        sigma = float(options['sigmas'][0])
        progress = sigma_progress(sigma, self.sigmas)
        s = self.settings
        # Match the existing physical-step schedules; 8-step examples use a
        # higher initial common prior so the shared scene has time to develop.
        common = stepped_common_weight(progress, len(self.sigmas), s['initial_common_prior'],
                                       .2, s['common_after_step3_boost'])
        gain = character_value_gain(progress, s['initial_character_gain'])
        separation = hold_decay_spatial_separation(progress, len(self.sigmas),
            s['initial_spatial_separation'], min(s['boundary_hold_steps'],len(self.sigmas)), s['boundary_decrement'])
        config = options.get('rs_resolution_separation')
        exclusive, control = None, None
        if config is not None:
            config = {**config, 'final_grid': config['final_latent_grid']}
            exclusive, control = separation_for_grid(config, x.shape[-2:],
                s['initial_spatial_separation'], separation, None)
        groups = token_groups(self.masks, *grid, x.device, boxes=self.boxes)
        self.audit.update(token_grid=list(grid), tokens_per_slot=[len(g) for g in groups])
        record = dict(sigma=sigma, progress=progress, kinds=list(kinds), common_prior=common,
                      character_value_gain=gain, spatial_separation=separation,
                      joint_calls=0, text_refiner_calls=0, exclusive_spatial_separation=exclusive,
                      resolution_separation=control, token_grid=list(grid), latent_grid=list(x.shape[-2:]))
        self.audit['forwards'].append(record)
        previous = self.state
        outputs = []
        try:
            for batch, kind in enumerate(kinds):
                cb = context[batch:batch+1]
                branch_options = {**options, 'cond_or_uncond': [kind], 'rs_mc_batch': batch}
                tb = timesteps[batch:batch+1] if timesteps.shape[0] == len(kinds) else timesteps
                if kind == 1:
                    self.state = None
                else:
                    pieces = [cb]
                    for c, _ in self.conditions:
                        if c.ndim != 3 or c.shape[0] != 1 or c.shape[2] != cb.shape[2]:
                            raise ValueError(f'Connect the matching {self.family} text encoder.')
                        pieces.append(c.to(cb))
                    lengths = [c.shape[1] for c in pieces]
                    cb = torch.cat(pieces, 1)
                    record['text_lengths'] = lengths
                    self.state = dict(lengths=lengths, groups=groups, image_tokens=grid[0]*grid[1],
                                      common=common, gain=gain, separation=separation, exclusive=exclusive, record=record)
                outputs.append(invoke(x[batch:batch+1], tb, cb, branch_options))
            return torch.cat(outputs, 0)
        finally:
            self.state = previous
            self.audit['restored_forwards'] += 1

    def attention(self, original, q, k, v, heads, mask=None, **kwargs):
        state = self.state
        if state is None:
            return original(q, k, v, heads, mask=mask, **kwargs)
        options = kwargs.get('transformer_options', {})
        pre_shaped = kwargs.get('skip_reshape', False)
        seq_dim = 2 if pre_shaped else 1
        total_text = sum(state['lengths'])
        total_image = state['image_tokens']
        joint = 'block_index' in options
        n = q.shape[seq_dim]
        if not joint and self.family == 'Krea2' and q.shape[0] != 1:
            # The first Krea adapter attends over tapped encoder layers for
            # EACH token (B*text_length, heads, 12, dim), not over prompt text.
            return original(q, k, v, heads, mask=mask, **kwargs)
        if joint and self.reference_lengths:
            from .native_reference import reference_joint
            return reference_joint(self, original, q, k, v, heads, mask=mask, **kwargs)
        expected = total_text + total_image if joint else total_text
        if q.shape[0] != 1 or n != expected or k.shape[seq_dim] != n or v.shape[seq_dim] != n:
            raise ValueError(f'{self.family} attention layout changed; update the extension before using this ComfyUI version.')
        if mask is not None:
            raise ValueError('An additional attention mask cannot be combined with joint regional routing.')
        if joint and self.family == "MOSS":
            q, k = [moss_caption_positions(t, heads, state["lengths"], total_image, pre_shaped) for t in (q,k)]
            state["record"]["moss_text_positions"] = "independent_caption_tail_aligned"
        text_start = total_image if joint and self.family in ('MOSS', 'FLUX3') else 0
        image_start = 0 if self.family in ('MOSS', 'FLUX3') else total_text
        text = []
        offset = text_start
        for length in state['lengths']:
            text.append(torch.arange(offset, offset+length, device=q.device))
            offset += length
        # All groups use ComfyUI's selected attention backend. Query/key
        # slicing avoids a dense (all_text + all_image)^2 routing allocation.
        output_shaped = kwargs.get('skip_output_reshape', False)
        out = torch.empty_like(q) if pre_shaped == output_shaped else (
            q.new_empty((1, heads, n, q.shape[-1]//heads)) if output_shaped
            else q.new_empty((1, n, heads*q.shape[-1])))
        out_dim = 2 if output_shaped else 1

        def attend(queries, keys, bias=None, values_gain=None):
            for ref in getattr(self,'redux_references',[]):
                caption=text[ref['slot']+1]
                nr=ref['conditioning'].shape[1]
                refkeys=caption[-nr:]
                selected=(keys>=refkeys[0]) & (keys<=refkeys[-1])
                if bias is None:bias=q.new_zeros((1,len(keys)))
                else:bias=bias.clone()
                bias[:,selected]+=math.log(ref['strength']*max(1,len(caption)-nr)/nr)
            values = v.index_select(seq_dim, keys)
            if values_gain is not None:
                shape = [1]*values.ndim
                shape[seq_dim] = len(keys)
                values = values * values_gain.reshape(shape)
            result = original(q.index_select(seq_dim, queries), k.index_select(seq_dim, keys),
                              values, heads, mask=bias, **kwargs)
            out.index_copy_(out_dim, queries, result)

        if not joint:
            for tokens in text:
                attend(tokens, tokens)
            state['record']['text_refiner_calls'] += 1
            self.audit['text_refiner_calls'] += 1
            return out

        images = torch.arange(image_start, image_start+total_image, device=q.device)
        image_groups = [g+image_start for g in state['groups']]
        attend(text[0], torch.cat((text[0], images)))
        if isinstance(state['groups'], BoxGroups):
            groups = state['groups']
            for slot, own_images in enumerate(image_groups):
                attend(text[slot+1], torch.cat((text[slot+1], own_images)))
            for members, queries in groups.cells:
                if not members:
                    attend(queries+image_start, torch.cat((text[0], images)))
                    continue
                captions = [text[i+1] for i in members]
                keys = torch.cat((text[0], *captions, images))
                common_len = len(text[0])
                text_len = common_len + sum(len(t) for t in captions)
                mass = common_len / (1 + state['common'])
                bias = q.new_zeros((len(queries), len(keys)))
                bias[:, :common_len] = -torch.inf if state['common'] == 0 else math.log(state['common']*mass/common_len)
                offset = common_len
                for tokens in captions:
                    bias[:, offset:offset+len(tokens)] = math.log(mass / (len(members)*len(tokens)))
                    offset += len(tokens)
                if state['separation']:
                    bias[:, text_len:] = math.log1p(-state['separation'])
                    for slot in members:
                        bias[:, text_len+groups[slot]] = 0
                    bias[:, text_len+groups.background] = 0
                if state.get('exclusive') is not None and len(members) == 1:
                    for other, indices in groups.cells:
                        if len(other) == 1 and other != members:
                            bias[:, text_len+indices] = math.log1p(-state['exclusive'])
                gain = q.new_ones(len(keys))
                gain[common_len:text_len] = state['gain']
                attend(queries+image_start, keys, bias, gain)
            state['record']['joint_calls'] += 1
            self.audit['cross_calls'] += 1
            self.audit['self_calls'] += 1
            return out
        for slot, own_images in enumerate(image_groups):
            own_text = text[slot+1]
            attend(own_text, torch.cat((own_text, own_images)))
            keys = torch.cat((text[0], own_text, images))
            common_len, char_len = len(text[0]), len(own_text)
            # Preserve total text prior relative to the native image keys.
            # Length-normalization only apportions it between the two captions.
            mass = common_len/(1+state['common'])
            bias = q.new_zeros((len(own_images), len(keys)))
            bias[:, :common_len] = -torch.inf if state['common'] == 0 else math.log(state['common']*mass/common_len)
            bias[:, common_len:common_len+char_len] = math.log(mass/char_len)
            if state['separation']:
                bias[:, common_len+char_len:] = math.log1p(-state['separation'])
                bias[:, common_len+char_len+state['groups'][slot]] = 0
            gain = q.new_ones(len(keys))
            gain[common_len:common_len+char_len] = state['gain']
            attend(own_images, keys, bias, gain)
        state['record']['joint_calls'] += 1
        self.audit['cross_calls'] += 1
        self.audit['self_calls'] += 1
        return out
