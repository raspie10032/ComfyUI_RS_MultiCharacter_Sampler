# SPDX-License-Identifier: GPL-3.0-only
"""Numbered SnapRef v2a banks on native Anima, scoped to one RS sampling call.

Reference prefill and adapter format follow ArcAnima's Apache-2.0 implementation.
See THIRD_PARTY_NOTICES.md and ANIMA-REF-ADAPTER-LICENSE.
"""
from contextlib import contextmanager
import json

from safetensors import safe_open
from safetensors.torch import load_file
import torch
import torch.nn.functional as F

from .anima_ref_frame import base_block_indices
from .anima_role_engine import regional_cached_attention
from .routing import installed_ops, sdpa
from .runtime_control import check_interrupted


class SnapRefRuntime:
    def __init__(self, refs, latents, condition, path, slot_count, audit):
        self.refs, self.latents, self.condition, self.path = refs, latents, condition, path
        self.weights = None
        self.grid = None
        self.banks = {}
        self.strengths = [0.] * slot_count
        for slot, ref in refs:
            self.strengths[slot] = ref.strength
        self.audit = audit['anima_snapref'] = dict(
            adapter=path.name, slots={str(slot + 1): ref.mode for slot, ref in refs},
            cache_builds=0, grid_changes=[], cache_bytes=0, cache_released=False)

    def load(self, net):
        mapping = base_block_indices(len(net.blocks))
        weights = load_file(str(self.path))
        with safe_open(self.path, framework='pt') as handle:
            meta = json.loads(handle.metadata()['anima_ref_kv'])
        if meta['format'] != 'anima_ref_kv/1' or not all(ref.mode in meta['modes'] for _, ref in self.refs):
            raise ValueError('Use the SnapRef v2a adapter supporting cs and char modes.')
        self.mode_embeddings = dict(zip(meta['modes'], weights['anima_ref_kv.mode_embed'], strict=True))
        self.ref_frame = int(meta['ref_t'])
        self.weights = streams = {'ref': [], 'tgt': []}
        for stream, layers in streams.items():
            for index, target in enumerate(mapping):
                for part in meta['lora'][stream]['targets']:
                    root = f'anima_ref_kv.{stream}.blocks.{index}.{part}.'
                    down, up = weights[root + 'lora_down'], weights[root + 'lora_up']
                    module = net.blocks[target].get_submodule(part)
                    if down.shape[1] != module.in_features or up.shape != (module.out_features, down.shape[0]):
                        raise ValueError(f'SnapRef weight shape does not match {part} in block {target}.')
                    layers.append((module, [down, up, float(weights[root + 'alpha']) / down.shape[0]]))
        self.audit.update(model_blocks=len(net.blocks), adapter_blocks=len(mapping))

    @contextmanager
    def lora(self, stream):
        hooks = []
        try:
            for module, weights in self.weights[stream]:
                def delta(_, args, out, weights=weights):
                    x = args[0]
                    if weights[0].device != x.device or weights[0].dtype != x.dtype:
                        weights[:2] = [value.to(x) for value in weights[:2]]
                    return out + F.linear(F.linear(x, weights[0]), weights[1]) * weights[2]
                hooks.append(module.register_forward_hook(delta))
            yield
        finally:
            for hook in hooks:
                hook.remove()

    def prefill(self, net, latent, context, grid, mode):
        value, _, extra = net.prepare_embedded_sequence(latent, fps=None, padding_mask=None)
        _, _, h, w, _ = value.shape
        rows, cols = torch.meshgrid(
            torch.arange(h, device=latent.device) + round((grid[0] - h) / 2),
            torch.arange(w, device=latent.device) + round((grid[1] - w) / 2), indexing='ij')
        encoder = net.pos_embedder
        pieces = []
        for positions, factor, span in (
            (torch.full_like(rows, self.ref_frame), encoder.t_ntk_factor, encoder.dim_temporal_range),
            (rows, encoder.h_ntk_factor, encoder.dim_spatial_range),
            (cols, encoder.w_ntk_factor, encoder.dim_spatial_range),
        ):
            angle = torch.outer(positions.flatten().float(), (10000. * factor) ** -span.to(latent.device))
            pieces.append(torch.stack((angle.cos(), -angle.sin(), angle.sin(), angle.cos()), -1))
        rope = torch.cat(pieces, -2).reshape(h * w, -1, 2, 2)[None, :, None]
        sinusoid = net.t_embedder[0](value.new_zeros(1, 1, dtype=torch.float32))
        emb, adaln = net.t_embedder[1](sinusoid.to(value.dtype))
        emb = net.t_embedding_norm(emb) + self.mode_embeddings[mode].to(emb)
        if value.dtype == torch.float16:
            value = value.float()
        bank = []

        def capture(q, k, v, **kwargs):
            q, k, v = (t if isinstance(t, torch.Tensor) else t.take() for t in (q, k, v))
            bank.append((k.transpose(1, 2), v.transpose(1, 2)))
            return sdpa(q, k, v)

        # No target routing, LLLite options, or target LoRA in the clean stream.
        with self.lora('ref'), installed_ops(net.blocks, None, capture):
            for block in net.blocks:
                check_interrupted()
                value = block.forward(value, emb, context, rope_emb_L_1_1_D=rope,
                    adaln_lora_B_T_3D=adaln, extra_per_block_pos_emb=extra, transformer_options={})
        return bank

    def prepare_grid(self, net, x, kinds):
        if self.weights is None:
            self.load(net)
        if 0 not in kinds:
            return
        grid = tuple(n // net.patch_spatial for n in x.shape[-2:])
        key = (grid, x.device, x.dtype)
        if self.grid == key:
            return
        self.banks.clear()
        cross, meta = self.condition
        context = net.preprocess_text_embeds(cross.to(x), meta['t5xxl_ids'].unsqueeze(0).to(x.device),
            meta['t5xxl_weights'].unsqueeze(0).unsqueeze(-1).to(x))
        for slot, ref in self.refs:
            self.banks[slot] = self.prefill(net, self.latents[slot].to(x), context, grid, ref.mode)
            self.audit['cache_builds'] += 1
        self.audit['grid_changes'].append(list(grid))
        self.audit['cache_bytes'] = sum(t.numel() * t.element_size() for bank in self.banks.values()
                                        for pair in bank for t in pair)
        self.grid = key

    def attention(self, q, k, v, groups, target_bias, kinds, block):
        banks = [None] * len(groups)
        for slot, bank in self.banks.items():
            banks[slot] = tuple(t.to(q) for t in bank[block])
        return torch.cat([
            regional_cached_attention(q[i:i+1], k[i:i+1], v[i:i+1], groups, target_bias, banks, self.strengths)
            if kind == 0 else sdpa(q[i:i+1], k[i:i+1], v[i:i+1], target_bias)
            for i, kind in enumerate(kinds)
        ])

    @contextmanager
    def sampling(self):
        try:
            yield
        finally:
            self.weights = self.grid = None
            self.banks.clear()
            self.latents.clear()
            self.audit['cache_released'] = True
