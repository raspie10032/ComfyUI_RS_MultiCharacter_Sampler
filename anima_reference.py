"""Experimental Anima reference residual; supported but not recommended.

Preserves the audited upstream end-of-block image residual and cross-attention
helper LoRA. Hooks exist only inside one diffusion forward and are removed on
failure. Common reference data stays separate from Anima's native math.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import time

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from safetensors.torch import load_file

from .routing import token_groups
from .reference_image import prepare_reference, reference_size_input, validate_reference_size

@dataclass(frozen=True)
class ReferenceCondition:
    slot: int
    features: torch.Tensor
    strength: float
    source: str
    input_size: int


class AnimaReferenceRuntime:
    def __init__(self, plan, masks, boxes, audit):
        self.refs, self.helper_mode = plan
        self.masks, self.boxes = masks, boxes
        self.audit = audit['image_reference'] = {
            'refs': [{'slot': r.slot+1, 'source': r.source, 'input_size': r.input_size,
                      'tokens': r.features.shape[1], 'strength': r.strength} for r in self.refs],
            'helper_mode': self.helper_mode, 'insertion': 'native end of block after MLP',
            'null': 'zero features, residual bypass as audited upstream',
            'calls': 0, 'restored_forwards': 0, 'max_outside_delta': 0.,
            'blocks_seen': [], 'max_allocated_bytes': 0, 'max_reserved_bytes': 0,
        }
        self.groups = None
        self.kv = {}
        self.native_weights = {}
        self.helper = {}
        self.kv_bytes = 0

    def prepare(self, blocks, device, dtype):
        from safetensors.torch import load_file
        from .reference_assets import asset
        w = load_file(str(asset('anima_adapter')), device='cpu')
        if len(blocks) != 28:
            raise ValueError('Downloaded adapter requires the 28-block Anima architecture.')
        for bi in range(28):
            prefix = f'blocks.{bi}.'
            self.native_weights[bi] = tuple(w[prefix+'adaln_ip.1.'+name].to(device=device, dtype=dtype)
                                            for name in ('weight', 'bias'))
            for ref in self.refs:
                features = ref.features.to(device=device, dtype=dtype) * ref.strength
                pair = []
                for name in ('k', 'v'):
                    projected = F.linear(features, w[prefix+f'ip_{name}_proj.weight'].to(device=device,dtype=dtype),
                                         w[prefix+f'ip_{name}_proj.bias'].to(device=device,dtype=dtype))
                    pair.append(projected.reshape(1, -1, blocks[bi].cross_attn.n_heads,
                                                  blocks[bi].cross_attn.head_dim).transpose(1, 2))
                    self.kv_bytes += projected.numel()*projected.element_size()
                self.kv[bi, ref.slot] = tuple(pair)
        for key, a in w.items():
            m = re.fullmatch(r'lora.base_model.model.blocks\.(\d+)\.(.+)\.lora_A.weight', key)
            if not m:
                continue
            bi, name = int(m[1]), m[2]
            if self.helper_mode == 'upstream_cross' and not name.startswith('cross_attn.'):
                continue
            b = w[key.replace('.lora_A.weight', '.lora_B.weight')]
            self.helper[bi, name] = a.to(device=device,dtype=dtype), b.to(device=device,dtype=dtype)
        self.audit.update(kv_cache_bytes=self.kv_bytes, helper_layers=len(self.helper))

    @contextmanager
    def installed(self, blocks, kinds):
        handles, captured = [], {}
        try:
            for (bi, name), (a, b) in self.helper.items():
                mod = blocks[bi]
                for part in name.split('.'):
                    mod = getattr(mod, part)
                def helper_hook(module, args, output, a=a, b=b):
                    return output + F.linear(F.linear(args[0], a), b)
                handles.append(mod.register_forward_hook(helper_hook))
            for bi, block in enumerate(blocks):
                def capture(module, args, bi=bi):
                    captured[bi] = args[0]
                handles.append(block.cross_attn.register_forward_pre_hook(capture))
                def residual(module, args, output, bi=bi, block=block):
                    xq = captured.pop(bi)
                    batch, frames, height, width, dim = output.shape
                    if batch % len(kinds) or frames != 1:
                        raise ValueError('Expected image CFG chunks, no temporal inputs.')
                    rows = batch // len(kinds)
                    positive_rows = [idx*rows + j for idx, kind in enumerate(kinds) if kind == 0 for j in range(rows)]
                    if not positive_rows:
                        return output
                    row_idx = torch.tensor(positive_rows, device=output.device)
                    attention = block.cross_attn
                    q = attention.q_proj(xq.index_select(0, row_idx)).reshape(len(positive_rows), -1,
                                                attention.n_heads, attention.head_dim).transpose(1, 2)
                    q = attention.q_norm(q)
                    delta = output.new_zeros((len(positive_rows), frames*height*width, dim))
                    counts = output.new_zeros(frames*height*width)
                    for ref in self.refs:
                        ids = self.groups[ref.slot]
                        k, v = self.kv[bi, ref.slot]
                        value = F.scaled_dot_product_attention(q.index_select(2, ids), k, v)
                        value = value.transpose(1, 2).reshape(len(positive_rows), len(ids), dim)
                        delta[:, ids] += value.to(delta.dtype)
                        counts[ids] += 1
                    delta /= counts.clamp_min(1)[None, :, None]
                    # Training's learned gate uses the same timestep embedding as this block.
                    emb = args[1].index_select(0, row_idx)
                    gw, gb = self.native_weights[bi]
                    gate = F.linear(F.silu(emb), gw, gb).to(output.dtype)
                    result = output.clone()
                    result[row_idx] += gate.reshape(len(positive_rows), frames, 1, 1, dim) * delta.reshape(len(positive_rows), frames, height, width, dim)
                    if bi not in self.audit['blocks_seen']:
                        self.audit['blocks_seen'].append(bi)
                        outside = (counts == 0).nonzero().flatten()
                        max_outside = float(delta[:, outside].abs().max()) if len(outside) else 0.
                        self.audit['max_outside_delta'] = max(self.audit['max_outside_delta'], max_outside)
                    self.audit['calls'] += 1
                    return result
                handles.append(block.register_forward_hook(residual))
            yield
        finally:
            for handle in reversed(handles):
                handle.remove()
            captured.clear()

    def forward(self, executor, x, timesteps, context, *args, **kwargs):
        options = kwargs.get('transformer_options', {})
        kinds = options.get('cond_or_uncond')
        if not kinds:
            raise ValueError('Reference trial requires explicit CFG row kinds.')
        if not self.refs:
            return executor(x, timesteps, context, *args, **kwargs)
        blocks = executor.class_obj.blocks
        if not self.kv:
            self.prepare(blocks, x.device, context.dtype)
        h, w = (d // executor.class_obj.patch_spatial for d in x.shape[-2:])
        if self.groups is None:
            self.groups = token_groups(self.masks, h, w, x.device, boxes=self.boxes)
        try:
            with self.installed(blocks, kinds):
                return executor(x, timesteps, context, *args, **kwargs)
        finally:
            self.audit['restored_forwards'] += 1
            self.audit['max_allocated_bytes'] = torch.cuda.max_memory_allocated(x.device)
            self.audit['max_reserved_bytes'] = torch.cuda.max_memory_reserved(x.device)
