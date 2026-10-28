# SPDX-License-Identifier: GPL-3.0-only
"""Invocation-local Role K/V integration with RS's numbered spatial routing.

The adapter is prepared automatically. Only reference K/V survive between
evaluations, never between sampling requests or target token grids.
"""
from contextlib import contextmanager

import numpy as np
import torch

from .runtime_control import check_interrupted


def encode_role_references(refs, vae, process_latent):
    """Keep the selected long edge, full frame and aspect; align to VAE patches."""
    from PIL import Image
    cache, result = {}, {}
    for slot, ref in refs:
        check_interrupted()
        key = (ref.source, ref.resolution)
        if key not in cache:
            image = ref.image()
            size = tuple(max(16, v // 16 * 16) for v in image.size)
            image = image.resize(size, Image.Resampling.LANCZOS)
            pixels = torch.from_numpy(np.asarray(image).copy()).float()[None] / 255.
            latent = vae.encode(pixels)
            if latent.ndim == 4:
                latent = latent.unsqueeze(2)
            cache[key] = process_latent(latent).detach().cpu()
        result[slot] = cache[key]
    return result


class RoleKVRuntime:
    def __init__(self, refs, latents, adapter_path, routing, audit):
        self.refs, self.latents, self.adapter_path = refs, latents, adapter_path
        self.routing = routing
        self.engine = self.banks = self.grid = None
        self.audit = audit['anima_role_kv'] = dict(
            method='anima_role_kv', adapter_strength=1.,
            adapter='AnticPan/Anima-Role-Ref-KV@259a0dce876ed70fc8835b888139756e23fb8a9f',
            profile='balanced regional text; no extra self isolation',
            scope='sampling invocation and target grid',
            reference_slots=[i + 1 for i, _ in refs],
            cache_builds=0, grid_changes=[], cache_bytes=0,
            overlap='all owning reference banks', background='no reference bank',
            reference_shapes={str(i + 1): list(v.shape) for i, v in latents.items()})

    def prepare_grid(self, net, x):
        """Called before RS installs temporary per-character LoRA forwards."""
        grid = tuple(n // net.patch_spatial for n in x.shape[-2:])
        if self.grid == grid:
            return
        check_interrupted()
        from .anima_role_engine import RegionalRoleEngine
        if self.engine is None:
            import comfy.utils
            state = comfy.utils.load_torch_file(str(self.adapter_path), safe_load=True)
            if len(net.blocks) != 28 or any(
                    block.self_attn.q_proj.weight.dtype not in (torch.bfloat16, torch.float32)
                    for block in net.blocks):
                raise ValueError('Role K/V currently requires native Anima Base BF16/FP32. / '
                                 'Role K/V는 현재 Anima Base BF16·FP32만 지원합니다.')
            strengths = [0.] * len(self.routing.masks)
            for slot, ref in self.refs:
                strengths[slot] = ref.strength
            self.engine = RegionalRoleEngine(net, state, device=x.device,
                masks=self.routing.masks, common_tokens=self.routing.common_tokens,
                boxes=self.routing.boxes,
                reference_strengths=strengths, profile='text')
        self.banks = None
        caches = [None] * len(self.routing.masks)
        with torch.autocast(x.device.type, dtype=torch.bfloat16, enabled=x.dtype == torch.bfloat16):
            for slot, _ in self.refs:
                check_interrupted()
                caches[slot] = self.engine.reference(self.latents[slot].to(x),
                    self.routing.contexts[slot].to(x), x.shape[-2:])
                self.audit['cache_builds'] += 1
        self.banks = [[None if bank is None else bank[i] for bank in caches]
                      for i in range(len(net.blocks))]
        self.audit['cache_bytes'] = sum(k.numel()*k.element_size() + v.numel()*v.element_size()
            for bank in caches if bank is not None for k, v in bank)
        self.audit['grid_changes'].append(list(grid))
        self.grid = grid

    def forward(self, executor, x, timesteps, context, *args, **kwargs):
        """Final diffusion wrapper: standard Comfy sampling/CFG stays in charge."""
        from .routing import sigma_progress
        kinds = kwargs.get('transformer_options', {}).get('cond_or_uncond')
        if self.engine is None or not kinds or len(kinds) != x.shape[0]:
            raise ValueError('Role K/V needs RS image sampling with a single image per CFG branch.')
        lengths = [context.shape[1] - sum(c.shape[1] for c in self.routing.contexts)]
        lengths += [c.shape[1] for c in self.routing.contexts]
        sigma = float(kwargs['transformer_options']['sigmas'][0])
        step = round(sigma_progress(sigma, self.routing.sigmas) * max(len(self.routing.sigmas)-1, 1))
        outputs = []
        with torch.autocast(x.device.type, dtype=torch.bfloat16, enabled=x.dtype == torch.bfloat16):
            for batch, kind in enumerate(kinds):
                check_interrupted()
                self.engine.configure(step, len(self.routing.sigmas), self.grid, lengths, kind == 0)
                outputs.append(self.engine.velocity(x[batch:batch+1],
                    timesteps[batch:batch+1].reshape(-1), context[batch:batch+1].to(x),
                    self.banks if kind == 0 else None))
                blocks = len(self.engine.net.blocks)
                self.routing.audit['cross_calls'] += blocks
                self.routing.audit['self_calls'] += blocks
        return torch.cat(outputs, 0).to(x)

    @contextmanager
    def sampling(self):
        try:
            yield
        finally:
            self.banks = self.engine = self.grid = None
            self.latents.clear()
            self.audit['cache_released'] = True
