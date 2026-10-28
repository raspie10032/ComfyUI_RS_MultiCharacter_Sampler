# SPDX-License-Identifier: GPL-3.0-only
"""Opt-in experimental reference images carried by numbered character slots.

Images stay in memory, never in metadata or a persistent feature cache. The
selected family creates only its own encoder and releases it after preparation.
"""
from dataclasses import dataclass, field
import hashlib
import json
import math

import numpy as np
from PIL import Image
import torch

from .reference_image import prepare_reference, reference_size_input, validate_reference_size


@dataclass(frozen=True)
class ImageReference:
    pixels: bytes = field(repr=False)
    size: tuple
    resolution: int
    strength: float
    character_id: int = 1

    @property
    def source(self):
        return 'sha256:' + hashlib.sha256(self.pixels).hexdigest()

    def image(self):
        return Image.frombytes('RGB', self.size, self.pixels)


@dataclass(frozen=True)
class RoleKVImageReference(ImageReference):
    """Anima learned Role K/V adapter, not the reference-frame adapter."""


def anima_method_input():
    return (['reference_frame', 'role_kv'], {'default': 'reference_frame',
        'tooltip': 'Anima only: reference_frame preserves existing behavior. '
                   'role_kv downloads a dedicated 504 MiB adapter on first sampling; '
                   'experimental balanced regional routing, BF16/FP32 only.'})


class RSMultiCharacterReference:
    @classmethod
    def INPUT_TYPES(cls):
        from .character_builder import BUILD_PIPE_TYPE
        return {'required': {
            'image': ('IMAGE',),
            'character_id': ('INT', {'default': 1, 'min': 1, 'max': 10, 'tooltip': 'Match the number in Character Prompt. References follow its point, box or mask.'}),
            'resolution': reference_size_input(),
            'strength': ('FLOAT', {'default': .6, 'min': 0., 'max': 2., 'step': .05, 'tooltip': '0 disables processing. Start low; strength meaning depends on the backend. FLUX.1 references require a Kontext checkpoint.'}),
            'enabled': ('BOOLEAN', {'default': True}),
        }, 'optional': {'building_pipe': (BUILD_PIPE_TYPE,), 'anima_method': anima_method_input()}}

    RETURN_TYPES = ('RS_MC_BUILD_PIPE',)
    RETURN_NAMES = ('building_pipe',)
    FUNCTION = 'apply'
    CATEGORY = 'RS MultiCharacter/Experimental'
    EXPERIMENTAL = True
    DESCRIPTION = ('Experimental image reference: supported, NOT RECOMMENDED. Quality varies by model; use a character LoRA when available. '
                   'Connect one image per numbered character, then Finalize and Sampler. Point/box/mask placement is shared. '
                   'Anima reference frames, Krea 2 Identity Edit v2 and FLUX native references; FLUX.1 requires Kontext. Downloads matching weights on first sampling; optional requirements-reference.txt. Detailer ignores this input. '
                   '/ 실험적 이미지 참조: 지원하지만 권장하지 않습니다. 캐릭터별 큰 특징을 유도하며 품질은 모델에 따라 다릅니다. '
                   '/ 実験的画像参照: 対応していますが推奨しません。画質はモデルによって異なります。')

    def apply(self, image, character_id=1, resolution=384, strength=.6, enabled=True, building_pipe=None,
              anima_method='reference_frame'):
        from .character_builder import update_slot
        validate_reference_size(resolution)
        if anima_method not in ('reference_frame', 'role_kv'):
            raise ValueError('Choose reference_frame or role_kv for the Anima reference method.')
        if type(enabled) is not bool or isinstance(strength, bool) or not isinstance(strength, (int, float)) or not math.isfinite(strength) or not 0 <= strength <= 2:
            raise ValueError('Reference strength must be 0–2 and enabled must be on/off.')
        ref = None
        if enabled and strength > 0:
            if not isinstance(image, torch.Tensor) or image.ndim != 4 or image.shape[0] != 1 or image.shape[-1] < 3 or min(image.shape[1:3]) < 1 or not torch.isfinite(image).all():
                raise ValueError('Connect one valid RGB image per reference. / 참조마다 RGB 이미지 한 장을 연결해 주세요.')
            pixels = (image[0, :, :, :3].detach().cpu().clamp(0, 1).numpy() * 255).astype(np.uint8)
            fitted, _ = prepare_reference(Image.fromarray(pixels), resolution, square_padding=False)
            factory = RoleKVImageReference if anima_method == 'role_kv' else ImageReference
            ref = factory(fitted.tobytes(), fitted.size, resolution, float(strength), character_id)
        return (update_slot(building_pipe, character_id, reference=ref),)


def prepare_model_references(model, clip, vae, pipe, family, layout_method='regional', node_id=None):
    refs = [(i, c.reference) for i, c in enumerate(pipe.characters) if c.reference is not None and c.reference.strength > 0]
    if not refs:
        return model
    if any(isinstance(r, RoleKVImageReference) for _, r in refs):
        if family != 'Anima' or not all(isinstance(r, RoleKVImageReference) for _, r in refs):
            raise ValueError('Role K/V requires Anima and one shared reference method. / '
                             'Role K/V는 Anima 전용입니다. 활성 참조의 방식을 모두 맞춰 주세요.')
        return model
    from .anima_ref_frame import FrameImageReference
    if any(isinstance(r, FrameImageReference) for _, r in refs):
        if not all(isinstance(r, FrameImageReference) for _, r in refs):
            raise ValueError('Use one reference method at a time. / 참조 프레임과 기존 이미지 참조를 함께 쓸 수 없습니다.')
        # The sampler prepares VAE reference frames after masks and geometry.
        return model
    if layout_method != 'regional':
        raise ValueError('Image reference requires regional layout; moss_native is not supported. / 이미지 참조는 regional 모드를 사용해 주세요.')
    if family not in ('Anima', 'SD1.5', 'SDXL', 'FLUX1', 'FLUX2', 'FLUX3', 'Krea2', 'MOSS'):
        raise ValueError('No image-reference backend for ' + family)
    import comfy.model_management
    from .reference_assets import asset
    model = model.clone()
    # Per-call cache deduplicates identical images without retaining user data.
    cache = {}
    def pixels(ref):
        square, geometry = prepare_reference(ref.image(), ref.resolution, square_padding=True)
        return torch.from_numpy(np.asarray(square).copy()).float()[None] / 255., geometry
    def common(slot, ref, geometry):
        return dict(slot=slot, source=ref.source, strength=ref.strength, geometry=geometry)
    if family == 'Anima':
        raise RuntimeError('Anima references must be prepared as reference frames by the sampler.')
    elif family in ('SD1.5', 'SDXL'):
        import comfy.clip_vision
        import comfy.sd
        encoder = comfy.clip_vision.load(str(asset('redux_encoder' if family == 'FLUX1' else 'sd_encoder', node_id)))
        redux = comfy.sd.load_style_model(str(asset('redux', node_id))) if family == 'FLUX1' else None
        plan = []
        try:
            for slot, ref in refs:
                comfy.model_management.throw_exception_if_processing_interrupted()
                key = (ref.source, ref.resolution)
                if key not in cache:
                    px, geometry = pixels(ref)
                    with torch.inference_mode():
                        encoded = encoder.encode_image(px, crop=False)
                        if family == 'FLUX1':
                            encoded.last_hidden_state = encoded.last_hidden_state.cpu()
                            value = redux.get_cond(encoded).flatten(0, 1).unsqueeze(0).detach().cpu()
                        else:
                            value = (encoded.penultimate_hidden_states.detach().cpu(), encoder.encode_image(torch.zeros_like(px), crop=False).penultimate_hidden_states.detach().cpu())
                    cache[key] = (value, geometry)
                value, geometry = cache[key]
                plan.append({**common(slot, ref, geometry), ('conditioning' if family == 'FLUX1' else 'features'): value})
        finally:
            # Comfy manages the encoder's device; no manual CUDA copies persist here.
            del encoder, redux
        model.model_options['rs_redux_reference' if family == 'FLUX1' else 'rs_sd_reference'] = plan if family == 'FLUX1' else (family, plan, 'PLUS')
    else:
        plan = []
        for slot, ref in refs:
            comfy.model_management.throw_exception_if_processing_interrupted()
            key = (ref.source, ref.resolution)
            if key not in cache:
                if family == 'MOSS':
                    px, geometry = pixels(ref)
                else:
                    # Native reference encoders keep the source aspect ratio;
                    # white square padding can otherwise become scene content.
                    image, geometry = prepare_reference(ref.image(), ref.resolution, square_padding=False)
                    px = torch.from_numpy(np.asarray(image).copy()).float()[None] / 255.
                    import comfy.utils
                    height, width = px.shape[1:3]
                    px = comfy.utils.common_upscale(px.movedim(-1, 1),
                        max(16, width // 16 * 16), max(16, height // 16 * 16),
                        'lanczos', 'disabled').movedim(1, -1)
                with torch.inference_mode():
                    latent = vae.encode(px).detach().cpu()
                cache[key] = (latent, px, geometry)
            latent, px, geometry = cache[key]
            plan.append({**common(slot, ref, geometry), 'latent': latent, 'pixels': px})
        if family in ('Krea2', 'MOSS'):
            import comfy.sd
            import comfy.utils
            path = asset('krea_edit' if family == 'Krea2' else 'moss_edit', node_id)
            model, _ = comfy.sd.load_lora_for_models(model, None, comfy.utils.load_torch_file(str(path), safe_load=True), 1., 0.)
        model.model_options['rs_native_reference'] = plan
    return model
