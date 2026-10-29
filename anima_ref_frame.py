# SPDX-License-Identifier: GPL-3.0-only
"""Anima clean-reference-frame adapter, scoped to one RS sampling call.

Frame/RoPE/guidance math adapted from ElectronGirl/ComfyUI-Anima-Ref-Adapter
af9a438d (Apache-2.0, see ANIMA-REF-ADAPTER-LICENSE). Weights are separate.
No upstream custom node import, permanent hooks, or process-global GPU cache.
"""
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
import inspect
import math
from .image_reference import ImageReference, RoleKVImageReference, anima_method_input

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F

KEY = 'rs_anima_ref_frame'
PLAN = 'rs_anima_ref_frame_plan'


@dataclass(frozen=True)
class ReferencePlan:
    pixels: torch.Tensor | None
    adapter_path: str
    strength: float
    guidance: float
    correction: str
    cache: bool
    character_mode: str = 'precision'
    reference_scale: float = 1.


@dataclass(frozen=True)
class FrameImageReference(ImageReference):
    """Numbered source image; distinct from the older SigLIP method."""


class RSAnimaCharacterReference:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'image': ('IMAGE',),
            'character_id': ('INT', {'default': 1, 'min': 1, 'max': 10,
                'tooltip': 'Use the matching Prompt/Position number. One source per character.'}),
            'strength': ('FLOAT', {'default': 1., 'min': 0., 'max': 2., 'step': .05,
                'tooltip': 'Reference prediction strength in this character region. Zero removes the reference.'}),
            'enabled': ('BOOLEAN', {'default': True}),
        }, 'optional': {'building_pipe': ('RS_MC_BUILD_PIPE',), 'anima_method': anima_method_input()}}

    RETURN_TYPES = ('RS_MC_BUILD_PIPE',)
    RETURN_NAMES = ('building_pipe',)
    FUNCTION = 'apply'
    CATEGORY = 'RS MultiCharacter/Reference'
    EXPERIMENTAL = True
    DESCRIPTION = ('Anima numbered reference-frame image. Match the character number, then Finalize. '
        'The sampler prepares the default adapter automatically; an explicit adapter node is optional. '
        'Independent source predictions are blended in their numbered target masks. '
        'Overlaps blend both sources. Quality is experimental; more references cost memory/time.')

    def apply(self, image, character_id=1, strength=1., enabled=True, building_pipe=None,
              anima_method='reference_frame'):
        from .character_builder import update_slot
        if anima_method not in ('reference_frame', 'role_kv'):
            raise ValueError('Choose reference_frame or role_kv for the Anima reference method.')
        if (type(enabled) is not bool or isinstance(strength, bool)
                or not isinstance(strength, (int, float)) or not math.isfinite(strength) or not 0 <= strength <= 2):
            raise ValueError('Character reference strength must be 0–2 and enabled must be on/off.')
        ref = None
        if enabled and strength > 0:
            validate_image(image)
            pixels = (image[0].detach().cpu().clamp(0, 1).numpy()*255).round().astype(np.uint8)
            src = Image.fromarray(pixels)
            if anima_method == 'role_kv':
                # The dedicated node keeps full source pixels; bound preparation
                # separately to the tested adapter's reference token budget.
                from .reference_image import prepare_reference
                src, _ = prepare_reference(src, 768)
            factory = RoleKVImageReference if anima_method == 'role_kv' else FrameImageReference
            ref = factory(src.tobytes(), src.size, max(src.size), float(strength), character_id)
        return (update_slot(building_pipe, character_id, reference=ref),)


def validate_image(image):
    if (not isinstance(image, torch.Tensor) or image.ndim != 4 or image.shape[0] != 1
            or image.shape[-1] != 3 or min(image.shape[1:3]) < 1 or not torch.isfinite(image).all()):
        raise ValueError('Use one finite RGB reference image. / 참조 이미지 한 장을 연결해 주세요.')


class RSAnimaReferenceAdapter:
    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths
        return {'required': {
            'model': ('MODEL',),
            'adapter_name': (folder_paths.get_filename_list('loras'),
                {'tooltip': 'Anima reference-frame adapter weights, not an ordinary style LoRA. Download separately; see weight license.'}),
            'strength': ('FLOAT', {'default': 1., 'min': 0., 'max': 2., 'step': .05,
                'tooltip': 'Learned adapter strength. Zero bypasses reference processing.'}),
            'reference_guidance': ('FLOAT', {'default': 4.5, 'min': 0., 'max': 20., 'step': .1,
                'tooltip': 'Reference influence. With one global image, 1 skips an extra prediction. Zero bypasses the reference.'}),
            'correction': (['apg', 'rescale', 'none'], {'default': 'apg'}),
            'cache_text_kv': ('BOOLEAN', {'default': False,
                'tooltip': 'Reuse unchanged text K/V during this sample, up to 256 MiB. Automatically disabled with per-character LoRAs.'}),
            'reference_scale': ('FLOAT', {'default': 1., 'min': .5, 'max': 1., 'step': .05,
                'tooltip': 'Reference width/height relative to target. 0.8 uses about 64% reference tokens; quality can change.'}),
        }, 'optional': {'image': ('IMAGE', {'tooltip': 'Global reference. Leave unconnected to use numbered Character Reference nodes instead.'})}}

    RETURN_TYPES = ('MODEL',)
    FUNCTION = 'apply'
    CATEGORY = 'RS MultiCharacter/Reference'
    DESCRIPTION = ('Experimental Anima reference-frame adapter for RS MultiCharacter Sampler. '
        'Connect image for a global reference, or leave it unconnected and use numbered Character Reference nodes. '
        'Uses a separately downloaded learned adapter. Not Wan/AniSora or a universal IP-Adapter. '
        'RS progressive sampling is supported. The detailer ignores image references.')

    def apply(self, model, image=None, adapter_name=None, strength=1., reference_guidance=4.5,
              correction='apg', cache_text_kv=False, reference_scale=1.):
        from comfy.model_base import Anima
        import folder_paths
        if not isinstance(model.model, Anima):
            raise ValueError('This reference-frame adapter requires Anima. / Anima 모델을 연결해 주세요.')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in (strength, reference_guidance)) or not 0 <= strength <= 2 or not 0 <= reference_guidance <= 20:
            raise ValueError('Adapter strength must be 0–2 and reference guidance 0–20.')
        if correction not in ('apg', 'rescale', 'none') or type(cache_text_kv) is not bool:
            raise ValueError('Choose a valid correction and cache setting.')
        if isinstance(reference_scale,bool) or not isinstance(reference_scale,(int,float)) or not math.isfinite(reference_scale) or not .5 <= reference_scale <= 1:
            raise ValueError('Reference scale must be 0.5–1.0.')
        from comfy.patcher_extension import WrappersMP
        if strength == 0 or reference_guidance == 0:
            result = model.clone()
            result.remove_wrappers_with_key(WrappersMP.DIFFUSION_MODEL, 'rs_ref_require')
            result.model_options.pop(PLAN, None)
            return (result,)
        if image is not None:
            validate_image(image)
        path = folder_paths.get_full_path_or_raise('loras', adapter_name)
        result = model.clone()
        result.remove_wrappers_with_key(WrappersMP.DIFFUSION_MODEL, 'rs_ref_require')
        result.add_wrapper_with_key(WrappersMP.DIFFUSION_MODEL, 'rs_ref_require', require_sampler)
        result.model_options[PLAN] = ReferencePlan(image.detach().cpu().clone() if image is not None else None, path,
            float(strength), float(reference_guidance), correction, cache_text_kv, reference_scale=float(reference_scale))
        return (result,)


def require_sampler(executor, *args, **kwargs):
    if not kwargs.get('transformer_options', {}).get('rs_anima_ref_ready'):
        raise ValueError('Connect the reference adapter to RS MultiCharacter Sampler. / 참조 어댑터는 RS 멀티캐릭터 샘플러에 연결해 주세요.')
    return executor(*args, **kwargs)


def encode_reference(pixels, vae, width, height):
    """One encode at the actual target size; no unused half-size VAE pass."""
    src = Image.fromarray((pixels[0].clamp(0, 1).numpy() * 255).round().astype(np.uint8))
    scale = min(width/src.width, height/src.height)
    size = (max(1, round(src.width*scale)), max(1, round(src.height*scale)))
    canvas = Image.new('RGB', (width, height), (255, 255, 255))
    canvas.paste(src.resize(size, Image.Resampling.LANCZOS), ((width-size[0])//2, (height-size[1])//2))
    value = vae.encode(torch.from_numpy(np.asarray(canvas).copy()).float()[None]/255.)
    if value.ndim == 4:
        value = value.unsqueeze(2)
    if value.ndim != 5 or value.shape[:3] != (1, 16, 1) or not torch.isfinite(value).all():
        raise ValueError('Reference encoding needs the matching Anima VAE and one image.')
    return value


def prepare_reference_latents(plan, refs, vae, width, height, steps,
                              start_scale=1., follow=False, end_step=None):
    """Encode only grids used while references are active, once per source/grid.

    All encodes precede diffusion so VAE/model residency does not alternate
    between progressive stages. Tensors remain local to this sampling call.
    """
    from .progressive import resolution_plan
    end_step = steps if end_step is None else end_step
    if type(end_step) is not int or not 1 <= end_step <= steps:
        raise ValueError('Reference end step must be an integer within the sampling schedule.')
    stages = resolution_plan(width, height, steps, start_scale) if follow else [
        dict(start=0, end=steps, width=width, height=height)]
    active = [stage for stage in stages if stage['start'] < end_step]
    sources = {}
    if refs:
        for _, ref in refs:
            if ref.source not in sources:
                sources[ref.source] = torch.from_numpy(np.asarray(ref.image()).copy()).float()[None]/255.
        ordered = [ref.source for _, ref in refs]
    else:
        sources[None] = plan.pixels
        ordered = [None]
    encoded, grids = {}, {}
    encodes = []
    for stage in active:
        rw, rh = (max(16, round(stage[k]*plan.reference_scale/16)*16) for k in ('width', 'height'))
        banks = []
        for source in ordered:
            key = (source, rw, rh)
            if key not in encoded:
                encoded[key] = encode_reference(sources[source], vae, rw, rh)
                encodes.append(dict(width=rw, height=rh))
            banks.append(encoded[key])
        grids[(stage['height']//8, stage['width']//8)] = torch.cat(banks, 2)
    first = next(iter(grids.values()))
    details = dict(unique_reference_encodes=len(encoded), unique_reference_sources=len(sources),
                   reference_encode_grids=encodes, reference_end_step=end_step,
                   skipped_reference_stages=len(stages)-len(active))
    return first, grids if follow else None, details


def frame_rope(pe, hp, wp, device, count=1, reference_grid=None):
    """The trained offset: reference begins one target height below the target."""
    h, w = torch.meshgrid(torch.arange(hp, device=device), torch.arange(wp, device=device), indexing='ij')
    h, w = h.flatten(), w.flatten()
    rh,rw=reference_grid or (hp,wp)
    a,b=torch.meshgrid(torch.arange(rh,device=device),torch.arange(rw,device=device),indexing='ij')
    # Preserve the same spatial extent while reducing the reference token grid.
    ah=(a.flatten().float()+.5)*hp/rh-.5+hp
    bw=(b.flatten().float()+.5)*wp/rw-.5
    positions = (torch.cat([torch.zeros_like(h)]+[torch.ones_like(ah)]*count),
                 torch.cat([h]+[ah]*count), torch.cat([w]+[bw]*count))
    result = []
    for p, factor, span in zip(positions,
            (pe.t_ntk_factor, pe.h_ntk_factor, pe.w_ntk_factor),
            (pe.dim_temporal_range, pe.dim_spatial_range, pe.dim_spatial_range)):
        freqs = 1./((10000.*factor)**span.to(device))
        angle = torch.outer(p.float(), freqs)
        result.append(torch.stack((angle.cos(), -angle.sin(), angle.sin(), angle.cos()), -1))
    emb = torch.cat(result, -2)
    return emb.reshape(*emb.shape[:-1], 2, 2).float()


def route_character_references(q, k, v, groups, size, target_bias, slots, strengths):
    """Select keys before softmax without a (N+1)S squared attention mask.

    Targets read all target tokens with the existing scheduled boundary bias,
    plus only their own references. Overlaps read both owners. Source frames
    read only themselves, so source identity is never rewritten by a neighbor.
    Target-to-target communication still permits indirect identity mixing.
    """
    from .routing import sdpa
    if (len(slots) != len(strengths) or len(set(slots)) != len(slots)
            or any(i < 0 or i >= len(groups) for i in slots)
            or q.shape[1] != size*(len(slots)+1) or k.shape != v.shape
            or k.shape[1] != q.shape[1]):
        raise ValueError('Character-reference token layout mismatch.')
    cells = getattr(groups, 'cells', None)
    if cells is None:
        cells = [((i,), indices) for i, indices in enumerate(groups)]
    result = q.new_empty(q.shape[:2]+(q.shape[2]*q.shape[3],))
    for owners, indices in cells:
        if not len(indices):
            continue
        keys, values = [k[:, :size]], [v[:, :size]]
        bias = [target_bias[indices]]
        for bank, (slot, strength) in enumerate(zip(slots, strengths)):
            if slot not in owners:
                continue
            start = size*(bank+1)
            keys.append(k[:, start:start+size]); values.append(v[:, start:start+size])
            bias.append(q.new_full((len(indices), size), math.log(strength)))
        result[:, indices] = sdpa(q[:, indices], torch.cat(keys, 1), torch.cat(values, 1), torch.cat(bias, 1))
    for bank in range(len(slots)):
        start = size*(bank+1)
        result[:, start:start+size] = sdpa(q[:, start:start+size], k[:, start:start+size], v[:, start:start+size])
    return result


class FrameRuntime:
    def __init__(self, plan, reference, audit, cache_allowed=True, cache_limit=256*2**20, slots=(), strengths=(), masks=None):
        self.plan, self.reference = plan, reference
        self.slots, self.strengths = tuple(slots), tuple(strengths)
        self.masks = masks
        self.cache_enabled = plan.cache and cache_allowed
        self.cache_limit = cache_limit
        self.audit = audit['anima_reference_frame'] = dict(
            adapter=plan.adapter_path.rsplit('/', 1)[-1], strength=plan.strength,
            guidance=plan.guidance, correction=plan.correction,
            scope='numbered character references' if slots else 'global reference; regional target prompts retained',
            character_slots=[i+1 for i in slots], reference_priors=list(strengths),
            reference_count=reference.shape[2],
            reference_scale=plan.reference_scale, reference_latent_shape=list(reference.shape),
            reference_tokens=(reference.shape[-2]//2)*(reference.shape[-1]//2)*reference.shape[2],
            character_mode=plan.character_mode if slots else None,
            kv_cache_enabled=self.cache_enabled, cache_limit_bytes=cache_limit,
            cache_disabled_reason='per-character LoRA' if plan.cache and not cache_allowed else None,
            kv_hits=0, kv_misses=0, kv_skipped=0, peak_cache_bytes=0, reference_forwards=0,
            base_forwards=0, restored_forwards=0)
        self.weights = None
        self.rope_cache = OrderedDict()
        self.kv = OrderedDict()
        self.contexts = OrderedDict()
        self.bytes = 0
        self.counter = 0

    def clear(self):
        self.kv.clear()
        self.contexts.clear()
        self.rope_cache.clear()
        self.weights = None
        self.bytes = 0
        if hasattr(self, 'stage_references'):
            self.stage_references.clear()
        self.audit['cache_bytes_after_sample'] = 0

    def sample(self, executor, *args, **kwargs):
        try:
            return executor(*args, **kwargs)
        finally:
            self.clear()

    def mark(self, executor, x, timesteps, context, *args, **kwargs):
        options = dict(kwargs.get('transformer_options', {}))
        if 'cond_or_uncond' in options:
            options['cond_or_uncond'] = [0 if k == 0 else 1 for k in options['cond_or_uncond']]
        if kwargs.get(KEY) is not None and hasattr(self, 'stage_references'):
            # Numbered precision predictions carry exactly one reference bank.
            full = kwargs[KEY]
            staged = self.stage_references[tuple(x.shape[-2:])]
            if full.shape[2] == 1 and len(self.slots) > 1:
                # The guider selects the numbered bank explicitly.
                bank = int(options['rs_reference_bank'])
                staged = staged[:, :, bank:bank+1]
            kwargs[KEY] = staged
        if kwargs.get(KEY) is not None:
            entry = dict(target_grid=list(x.shape[-2:]), reference_shape=list(kwargs[KEY].shape), bank=options.get('rs_reference_bank'))
            rows = self.audit.setdefault('reference_grid_evaluations', [])
            if entry not in rows:
                rows.append(entry)
        options['rs_reference_frame'] = kwargs.get(KEY) is not None
        options['rs_reference_count'] = kwargs[KEY].shape[2] if options['rs_reference_frame'] else 0
        if options['rs_reference_frame']:
            ref=kwargs[KEY]
            options['rs_reference_token_count'] = (ref.shape[-2]//2)*(ref.shape[-1]//2)*ref.shape[2]
        if options['rs_reference_frame'] and self.slots and self.plan.character_mode == 'shared':
            options['rs_reference_slots'] = self.slots
            options['rs_reference_strengths'] = self.strengths
        kwargs['transformer_options'] = options
        return executor(x, timesteps, context, *args, **kwargs)

    def _context_id(self, context, active):
        if not self.cache_enabled:
            return None
        for key, (saved_active, saved) in self.contexts.items():
            if (active == saved_active and context.shape == saved.shape
                    and context.device == saved.device and context.dtype == saved.dtype
                    and torch.equal(context, saved)):
                return key
        self.counter += 1
        key = self.counter
        self.contexts[key] = (active, context.detach().clone())
        # Only a few CFG/context layouts can retain K/V. Changing prompts or
        # regional condition batches cannot grow a process-global cache.
        while len(self.contexts) > 4:
            old, _ = self.contexts.popitem(last=False)
            for entry in [entry for entry in self.kv if entry[0] == old]:
                pair = self.kv.pop(entry)
                self.bytes -= sum(t.numel()*t.element_size() for t in pair)
        return key

    def load_weights(self, dm):
        if self.weights is not None:
            return
        count = len(dm.blocks)
        if count not in (28, 40):
            raise ValueError('Anima reference adapter supports 2B (28 blocks) or 2.9B (40 blocks).')
        import comfy.utils
        state = comfy.utils.load_torch_file(self.plan.adapter_path, safe_load=True)
        weights = {}
        for key, down in state.items():
            if not key.startswith('diffusion_model.') or not key.endswith('.lora_down.weight'):
                continue
            name = key[len('diffusion_model.'):-len('.lora_down.weight')]
            up = state.get(key.replace('lora_down', 'lora_up'))
            try:
                module = dm.get_submodule(name)
            except AttributeError as error:
                raise ValueError(f'Anima reference adapter does not match this model: {name}') from error
            if (up is None or down.ndim != 2 or up.ndim != 2 or up.shape[1] != down.shape[0]
                    or down.shape[0] < 1 or not down.is_floating_point() or not up.is_floating_point()
                    or tuple(module.weight.shape) != (up.shape[0], down.shape[1])
                    or not torch.isfinite(down).all() or not torch.isfinite(up).all()):
                raise ValueError(f'Invalid Anima reference adapter layer: {name}')
            alpha_value = state.get(key.replace('lora_down.weight', 'alpha'), down.shape[0])
            if isinstance(alpha_value, torch.Tensor) and alpha_value.numel() != 1:
                raise ValueError(f'Invalid adapter alpha: {name}')
            alpha = float(alpha_value)
            if not math.isfinite(alpha):
                raise ValueError(f'Invalid adapter alpha: {name}')
            weights[name] = [down, up, self.plan.strength*alpha/down.shape[0]]
        # The published 2.9B conversion maps the 28 trained blocks around
        # twelve inserted blocks (Gazingstars123/Anima-2.9B expand_manifest.json).
        # Those blocks run normally without adapter hooks.
        inserted = {2, 5, 8, 11, 14, 17, 21, 24, 27, 30, 33, 36}
        mapped = set(range(count)) - (inserted if count == 40 else set())
        expected = {f'blocks.{i}.{part}' for i in mapped for part in (
            'self_attn.q_proj', 'self_attn.k_proj', 'self_attn.v_proj', 'self_attn.output_proj',
            'cross_attn.q_proj', 'cross_attn.k_proj', 'cross_attn.v_proj', 'cross_attn.output_proj',
            'mlp.layer1', 'mlp.layer2')}
        if set(weights) != expected:
            variant = 'pilot_r32_29B' if count == 40 else 'pilot_r32'
            raise ValueError(f'Anima reference adapter does not match this model. Select {variant} weights. / '
                             '모델에 맞는 참조 어댑터를 선택해 주세요. 2.9B는 변환된 29B 가중치가 필요합니다.')
        self.weights = weights
        self.audit.update(adapter_layers=len(weights), model_blocks=count, adapter_blocks=len(mapped),
                          unchanged_new_blocks=sorted(set(range(count)) - mapped))

    @contextmanager
    def installed(self, dm, context, active):
        handles, previous = [], []
        context_id = self._context_id(context, active)
        try:
            if active:
                self.load_weights(dm)
                for name, entry in self.weights.items():
                    module = dm.get_submodule(name)
                    def hook(module, args, output, entry=entry):
                        x = args[0]
                        if entry[0].device != x.device or entry[0].dtype != x.dtype:
                            entry[0] = entry[0].to(device=x.device, dtype=x.dtype)
                            entry[1] = entry[1].to(device=x.device, dtype=x.dtype)
                        return output + F.linear(F.linear(x, entry[0]), entry[1])*entry[2]
                    handles.append(module.register_forward_hook(hook))
            if context_id is not None:
                for index, block in enumerate(dm.blocks):
                    attn = block.cross_attn
                    # Restore the instance dictionary exactly, including the
                    # absence of an override, on cancellation or failure.
                    previous.append((attn, attn.__dict__.get('compute_qkv')))
                    original = attn.compute_qkv
                    # Older Cosmos attention predates transformer_options.
                    # Inspect once per wrapper, never retry an internal TypeError.
                    accepts_options = 'transformer_options' in inspect.signature(original).parameters
                    def cached(x, context=None, rope_emb=None, transformer_options=None,
                               attn=attn, original=original, index=index,
                               accepts_options=accepts_options):
                        key = (context_id, index, x.device, x.dtype)
                        pair = self.kv.get(key)
                        if pair is None:
                            if accepts_options:
                                q, k, v = original(x, context, rope_emb,
                                    transformer_options={} if transformer_options is None else transformer_options)
                            else:
                                q, k, v = original(x, context, rope_emb)
                            size = sum(t.numel()*t.element_size() for t in (k, v))
                            # A cyclic block traversal thrashes an LRU when all
                            # blocks do not fit. Keep an admitted subset instead.
                            if self.bytes+size <= self.cache_limit:
                                self.kv[key] = (k, v)
                                self.bytes += size
                                self.audit['peak_cache_bytes'] = max(self.bytes, self.audit['peak_cache_bytes'])
                            else:
                                self.audit['kv_skipped'] += 1
                            self.audit['kv_misses'] += 1
                            return q, k, v
                        self.kv.move_to_end(key)
                        self.audit['kv_hits'] += 1
                        q = attn.q_norm(attn.q_proj(x).reshape(*x.shape[:-1], attn.n_heads, attn.head_dim))
                        return q, pair[0], pair[1]
                    attn.compute_qkv = cached
            yield
        finally:
            for attn, original in reversed(previous):
                if original is None:
                    attn.__dict__.pop('compute_qkv', None)
                else:
                    attn.compute_qkv = original
            for handle in reversed(handles):
                handle.remove()

    def forward(self, executor, x, timesteps, context, fps=None, padding_mask=None, **kwargs):
        reference = kwargs.pop(KEY, None)
        if x.shape[0] != context.shape[0] or x.shape[-3] != 1:
            raise ValueError('Anima reference frame supports image generation only.')
        try:
            with self.installed(executor.class_obj, context, reference is not None):
                if reference is None:
                    self.audit['base_forwards'] += 1
                    return executor(x, timesteps, context, fps, padding_mask, **kwargs)
                self.audit['reference_forwards'] += 1
                return self.ref_forward(executor.class_obj, x, timesteps, context, reference,
                                        kwargs.get('transformer_options', {}))
        finally:
            self.audit['restored_forwards'] += 1

    def ref_forward(self, dm, x, timesteps, context, reference, options):
        import comfy.ldm.common_dit
        orig_shape = x.shape
        x = comfy.ldm.common_dit.pad_to_patch_size(x, (dm.patch_temporal, dm.patch_spatial, dm.patch_spatial))
        if reference.shape[-2:] != x.shape[-2:]:
            return self.packed_forward(dm,x,timesteps,context,reference,options,orig_shape)
        reference = reference.to(x)
        if reference.shape[0] == 1:
            reference = reference.expand(x.shape[0], -1, -1, -1, -1)
        count = reference.shape[2]
        frames = torch.cat((x[:, :, :1], reference), 2)
        x_emb, _, extra = dm.prepare_embedded_sequence(frames, fps=None, padding_mask=None)
        _, _, hp, wp, _ = x_emb.shape
        key = (hp, wp, x.device, count)
        rope = self.rope_cache.get(key)
        if rope is None:
            rope = frame_rope(dm.pos_embedder, hp, wp, x.device, count)
            self.rope_cache[key] = rope
            if len(self.rope_cache) > 2:
                self.rope_cache.popitem(last=False)
        times = timesteps.reshape(x.shape[0], -1)[:, :1]
        times = torch.cat([times]+[torch.zeros_like(times)]*count, 1)
        emb, adaln = dm.t_embedder[1](dm.t_embedder[0](times).to(x_emb.dtype))
        emb = dm.t_embedding_norm(emb)
        if x_emb.dtype == torch.float16:
            x_emb = x_emb.float()
        for index, block in enumerate(dm.blocks):
            options['block_index'] = index
            x_emb = block(x_emb, emb, context, rope_emb_L_1_1_D=rope.unsqueeze(1).unsqueeze(0),
                adaln_lora_B_T_3D=adaln, extra_per_block_pos_emb=extra, transformer_options=options)
        # Keep the original projection shape. In BF16, projecting only the
        # target can select a different GEMM kernel and change the sampled image.
        out = dm.final_layer(x_emb.to(context.dtype), emb, adaln_lora_B_T_3D=adaln)
        return dm.unpatchify(out)[:, :, :orig_shape[-3], :orig_shape[-2], :orig_shape[-1]]

    def packed_forward(self,dm,x,timesteps,context,reference,options,orig_shape):
        """Unequal grids, with native block math and two cheap time embeddings.

        Tokens use T=sequence,H=W=1 only as a storage view. Their real 2D
        positions come from separate target/reference RoPE grids. AdaLN is
        computed once per image and broadcast to its token span.
        """
        if self.plan.character_mode=='shared' and self.slots:
            raise ValueError('Reduced reference grids require precision character references.')
        reference=reference.to(x).expand(x.shape[0],-1,-1,-1,-1)
        target,_,extra=dm.prepare_embedded_sequence(x,fps=None,padding_mask=None)
        refs,_,ref_extra=dm.prepare_embedded_sequence(reference,fps=None,padding_mask=None)
        if extra is not None or ref_extra is not None:
            raise ValueError('Reduced reference grids require Anima rotary positions only.')
        batch,_,hp,wp,dim=target.shape
        _,count,rh,rw,_=refs.shape
        sizes=[hp*wp]+[rh*rw]*count
        spans=torch.tensor(sizes,device=x.device)
        value=torch.cat((target.reshape(batch,-1,dim),refs.reshape(batch,-1,dim)),1)[:,:,None,None]
        rope=frame_rope(dm.pos_embedder,hp,wp,x.device,count,(rh,rw))
        times=timesteps.reshape(batch,-1)[:,:1]
        times=torch.cat([times]+[torch.zeros_like(times)]*count,1)
        emb,adaln=dm.t_embedder[1](dm.t_embedder[0](times).to(value.dtype))
        emb=dm.t_embedding_norm(emb)
        if adaln is not None:adaln=adaln.repeat_interleave(spans,dim=1)
        handles=[]
        def expand(module,args,result):return result.repeat_interleave(spans,dim=1)
        try:
            # Expand after each tiny modulation network, never recompute its
            # linear projections for every target/reference pixel.
            for block in dm.blocks:
                for name in ('adaln_modulation_self_attn','adaln_modulation_cross_attn','adaln_modulation_mlp'):
                    handles.append(getattr(block,name).register_forward_hook(expand))
            handles.append(dm.final_layer.adaln_modulation.register_forward_hook(expand))
            if value.dtype==torch.float16:value=value.float()
            for index,block in enumerate(dm.blocks):
                options['block_index']=index
                value=block(value,emb,context,rope_emb_L_1_1_D=rope[None,:,None],
                    adaln_lora_B_T_3D=adaln,extra_per_block_pos_emb=None,transformer_options=options)
            out=dm.final_layer(value.to(context.dtype),emb,adaln_lora_B_T_3D=adaln)
            out=out[:,:sizes[0]].reshape(batch,1,hp,wp,-1)
            self.audit.update(target_tokens=sizes[0],reference_tokens=sum(sizes[1:]),
                reference_latent_shape=list(reference.shape),reference_scale=self.plan.reference_scale)
            return dm.unpatchify(out)[:,:,:orig_shape[-3],:orig_shape[-2],:orig_shape[-1]]
        finally:
            for handle in reversed(handles):handle.remove()



def patch_extra_conds(model):
    import comfy.conds
    original = model.get_model_object('extra_conds')
    process = model.get_model_object('process_latent_in')
    def extra(**kwargs):
        result = original(**kwargs)
        if kwargs.get(KEY) is not None:
            result[KEY] = comfy.conds.CONDRegular(process(kwargs[KEY]))
        return result
    model.add_object_patch('extra_conds', extra)


def reference_guider(model, positive, negative, runtime, cfg):
    import comfy.samplers
    import node_helpers
    class Guider(comfy.samplers.CFGGuider):
        def correction(self, guided, pos):
            dims = tuple(range(1, pos.ndim))
            if runtime.plan.correction == 'apg':
                update = (guided-pos).double()
                unit = F.normalize(pos.double().flatten(1), dim=1).view_as(pos)
                return pos + (update-(update*unit).sum(dims, keepdim=True)*unit).to(pos.dtype)
            if runtime.plan.correction == 'rescale':
                ratio = pos.std(dims, keepdim=True)/guided.std(dims, keepdim=True).clamp_min(1e-12)
                return .5*guided*ratio + .5*guided
            return guided

        def numbered_prediction(self, x, timestep, model_options):
            # Like precision LoRA: independent two-frame predictions, followed
            # by normalized spatial composition. No shared source hidden state.
            pos, neg = comfy.samplers.calc_cond_batch(self.inner_model,
                [self.conds['positive_base'],self.conds['negative_base']],x,timestep,model_options)
            baseline = neg+self.cfg*(pos-neg)
            raw = F.interpolate(runtime.masks[list(runtime.slots)].float()[:,None],
                size=x.shape[-2:],mode='nearest').to(x)[:,0]
            weights = raw/raw.sum(0,keepdim=True).clamp_min(1)
            result = baseline*(1-weights.sum(0)).reshape(1,1,*([1]*(x.ndim-4)),*x.shape[-2:])
            for bank,strength in enumerate(runtime.strengths):
                pair=[self.conds[f'positive_{bank}'],self.conds[f'negative_{bank}']]
                bank_options = {**model_options, 'transformer_options': {**model_options.get('transformer_options', {}), 'rs_reference_bank': bank}}
                refpos,refneg = comfy.samplers.calc_cond_batch(self.inner_model,pair,x,timestep,bank_options)
                guided = neg+runtime.plan.guidance*(refneg-neg)+self.cfg*(refpos-refneg)
                guided = self.correction(guided,refpos)
                guided = baseline+strength*(guided-baseline)
                result = result+weights[bank].reshape(1,1,*([1]*(x.ndim-4)),*x.shape[-2:])*guided
            return result,pos,neg

        def predict_noise(self, x, timestep, model_options=None, seed=None):
            model_options = {} if model_options is None else model_options
            schedule = model_options.get('transformer_options', {}).get('sample_sigmas')
            step_index = int(torch.argmin((schedule[:-1].to(timestep)-timestep.flatten()[0]).abs()))
            enabled = step_index < getattr(runtime, 'end_step', len(schedule)-1)
            runtime.audit.setdefault('reference_schedule', []).append(dict(step=step_index+1, enabled=enabled, target_grid=list(x.shape[-2:])))
            if not enabled:
                conds = [self.conds['positive_base'], self.conds['negative_base']]
                pos, neg = comfy.samplers.calc_cond_batch(self.inner_model, conds, x, timestep, model_options)
                guided = neg + self.cfg*(pos-neg)
                for fn in model_options.get('sampler_post_cfg_function', []):
                    guided = fn(dict(denoised=guided, cond=conds[0], uncond=conds[1], cond_scale=self.cfg,
                        model=self.inner_model, uncond_denoised=neg, cond_denoised=pos, sigma=timestep,
                        model_options=model_options, input=x))
                return guided
            if runtime.slots and runtime.plan.character_mode == 'precision':
                guided,pos,neg=self.numbered_prediction(x,timestep,model_options)
                for fn in model_options.get('sampler_post_cfg_function',[]):
                    guided=fn(dict(denoised=guided,cond=self.conds['positive_base'],uncond=self.conds['negative_base'],
                        cond_scale=self.cfg,model=self.inner_model,uncond_denoised=neg,cond_denoised=pos,
                        sigma=timestep,model_options=model_options,input=x))
                return guided
            conds = [self.conds['positive'], self.conds['negative']]
            if runtime.plan.guidance != 1.:
                conds.append(self.conds['negative_base'])
            values = comfy.samplers.calc_cond_batch(self.inner_model, conds, x, timestep, model_options)
            pos, neg = values[:2]
            base = values[2] if len(values) == 3 else neg
            guided = base + runtime.plan.guidance*(neg-base) + self.cfg*(pos-neg)
            guided = self.correction(guided,pos)
            for fn in model_options.get('sampler_post_cfg_function', []):
                guided = fn(dict(denoised=guided, cond=conds[0], uncond=conds[1], cond_scale=self.cfg,
                    model=self.inner_model, uncond_denoised=neg, cond_denoised=pos, sigma=timestep,
                    model_options=model_options, input=x))
            return guided
    negative = node_helpers.conditioning_set_values(negative, {'prompt_type': 'negative'})
    refs = {KEY: runtime.reference}
    guider = Guider(model)
    if runtime.slots and runtime.plan.character_mode == 'precision':
        if runtime.masks is None:
            raise ValueError('Numbered reference predictions require resolved character masks.')
        conditions=dict(positive_base=positive,negative_base=negative)
        for bank in range(len(runtime.slots)):
            refs={KEY:runtime.reference[:,:,bank:bank+1]}
            conditions[f'positive_{bank}']=node_helpers.conditioning_set_values(positive,refs)
            conditions[f'negative_{bank}']=node_helpers.conditioning_set_values(negative,refs)
        guider.inner_set_conds(conditions)
    else:
        guider.inner_set_conds(dict(positive=node_helpers.conditioning_set_values(positive, refs),
            negative=node_helpers.conditioning_set_values(negative, refs), positive_base=positive, negative_base=negative))
    guider.set_cfg(cfg)
    return guider


def sample_reference(model, latent, settings, positive, negative, audit, sampler_override=None):
    import comfy.sample
    import comfy.samplers
    import comfy.utils
    import latent_preview
    from comfy_extras.nodes_custom_sampler import Noise_RandomNoise
    runtime = model.model_options['rs_anima_ref_frame_runtime']
    guider = reference_guider(model, positive, negative, runtime, settings['cfg'])
    sampler = sampler_override or comfy.samplers.sampler_object(settings['sampler_name'])
    sigmas = comfy.samplers.calculate_sigmas(model.get_model_object('model_sampling'), settings['scheduler'], settings['steps']).cpu()
    noise = Noise_RandomNoise(settings['seed']).generate_noise({'samples': latent})
    return guider.sample(noise, latent, sampler, sigmas,
        callback=latent_preview.prepare_callback(model, settings['steps']),
        disable_pbar=not comfy.utils.PROGRESS_BAR_ENABLED, seed=settings['seed'])
