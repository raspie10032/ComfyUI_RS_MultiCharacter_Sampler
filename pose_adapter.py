# SPDX-License-Identifier: GPL-3.0-only
"""Model-specific 3D pose inputs for RS sampling, with ordinary character regions."""
import json
import math

import torch
from .pose3d import read_scene


def model_family(model):
    from comfy import model_base
    if isinstance(model.model, getattr(model_base, 'Krea2', ())):
        return 'Krea2'
    if isinstance(model.model, getattr(model_base, 'MOSSImage', ())):
        return 'MOSS'
    raise ValueError('RS 3D Pose Adapter supports Krea2 Turbo and MOSS. For Anima use Apply Anima LLLite. / '
                     'Krea2 Turbo·MOSS용입니다. Anima는 Apply Anima LLLite를 사용해 주세요.')


class RS3DPoseAdapter:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'model': ('MODEL',), 'vae': ('VAE',),
                'scene_json': ('STRING', {'forceInput': True}),
                'strength': ('FLOAT', {'default': 1., 'min': 0., 'max': 2., 'step': .05,
                                      'tooltip': 'Pose adapter weight. 0 disables it. Exact joints and contacts are not guaranteed.'}),
                'start_percent': ('FLOAT', {'default': 0., 'min': 0., 'max': 1., 'step': .05}),
                'end_percent': ('FLOAT', {'default': 1., 'min': 0., 'max': 1., 'step': .05,
                                        'tooltip': 'Krea2: 1.0. MOSS: try 0.5 to reduce mannequin surfaces; character regions stay active.'})},
                'hidden': {'unique_id': 'UNIQUE_ID'}}

    RETURN_TYPES = ('MODEL',)
    FUNCTION = 'apply'
    CATEGORY = 'RS MultiCharacter/Characters'
    DESCRIPTION = ('Connect scene_json from RS 3D Pose Masks and the matching VAE. Krea2 Turbo uses a trained OpenPose LoRA; '
                   'MOSS uses a trained color/depth adapter. Matching weights download on first use. '
                   'Connect this MODEL to RS MultiCharacter Sampler. Keep the 3D building pipe connected to Finalize for character regions. '
                   'This is pose adapter conditioning, beyond silhouette masks; exact hands/contact and character count can still fail. '
                   'Image references cannot be combined with this experimental path.')

    def apply(self, model, vae, scene_json, strength=1., start_percent=0., end_percent=1., unique_id=None):
        family = model_family(model)
        if not all(type(v) in (int, float) and math.isfinite(v) for v in (strength, start_percent, end_percent)):
            raise ValueError('Pose strength and range must be finite numbers.')
        if not 0 <= strength <= 2 or not 0 <= start_percent <= end_percent <= 1:
            raise ValueError('Pose range must satisfy 0 ≤ start ≤ end ≤ 1; strength 0–2. / 포즈 적용 구간을 확인해 주세요.')
        work = model.clone()
        if strength == 0 or start_percent == end_percent:
            work.model_options.pop('rs_3d_pose', None)
            return (work,)
        scene = read_scene(scene_json)
        work.model_options['rs_3d_pose'] = dict(family=family, vae=vae, scene=scene, strength=float(strength),
                                              start=float(start_percent), end=float(end_percent), node_id=unique_id)
        return (work,)


def prepare_pose(model, family, width, height):
    """Load weights on a clone. Images/latents live only for this generation."""
    plan = model.model_options.get('rs_3d_pose')
    if plan is None:
        return model, None
    if model.model_options.get('rs_progressive_scale', 1.) < 1.:
        raise ValueError('3D pose adapters currently require the standard RS sampler at full resolution. / 포즈 어댑터는 일반 RS 샘플러를 사용해 주세요.')
    if family != plan['family']:
        raise ValueError('Pose adapter and sampling model differ. Reconnect the matching model.')
    if any(model.model_options.get(k) for k in ('rs_native_reference', 'rs_image_reference', 'rs_anima_ref_frame_plan')):
        raise ValueError('Disconnect image references before using the 3D pose adapter. / 포즈 어댑터 시험 경로에서는 이미지 참조를 분리해 주세요.')
    from .pose_control_maps import control_maps
    from .reference_assets import _verified_adapter
    import comfy.sd
    import comfy.utils
    scene = {**plan['scene'], 'width': width, 'height': height}
    color, depth, skeleton = control_maps(scene)
    image = lambda a: torch.from_numpy(a.copy()).float().unsqueeze(0)/255
    path = _verified_adapter('krea_pose' if family == 'Krea2' else 'moss_pose', plan['node_id'])
    weights = comfy.utils.load_torch_file(str(path), safe_load=True)
    full_weights = {}
    if family == 'MOSS':
        # The adapter replaces the input embedder with [noise | color | depth].
        # A padded diff at strength_model=0 works on older cores' ModelPatcher too.
        for name in ('video_embedder.weight', 'video_embedder.bias'):
            full_weights['diffusion_model.'+name] = weights.pop(name)
    if family == 'MOSS':
        # Hayate adapters name separate Q/K/V projections; ComfyUI fuses them.
        import comfy.lora
        mapping = comfy.lora.model_lora_keys_unet(model.model, {})
        state = model.model.state_dict()
        for key, value in state.items():
            if key.endswith('.proj.qkv.weight'):
                for index, projection in enumerate(('q', 'k', 'v')):
                    mapping[key[:-len('.qkv.weight')]+'.'+projection] = (key, (0, index*(value.shape[0]//3), value.shape[0]//3))
        weights = {(k if k.startswith('diffusion_model.') else 'diffusion_model.'+k):v for k,v in weights.items()}
        expected = [key[:-len('.lora_A.weight')] for key in weights if key.endswith('.lora_A.weight')]
        missing = [key for key in expected if key not in mapping]
        if missing or not expected:
            raise ValueError(f'MOSS pose LoRA has {len(missing)} unsupported projections. Update ComfyUI or use MOSS SFT BF16.')
        patches = comfy.lora.load_lora(weights, mapping)
        if len(patches) != len(expected):
            raise ValueError('MOSS pose LoRA weights are incomplete; generation stopped before sampling.')
        work = model.clone()
        if not patches or len(work.add_patches(patches, plan['strength'])) != len(patches):
            raise ValueError('MOSS pose LoRA could not be fully installed on this model. Use MOSS SFT BF16.')
    else:
        work, _ = comfy.sd.load_lora_for_models(model, None, weights, plan['strength'], 0.)
    if full_weights:
        patches = {k: ('diff', (v, {'pad_weight': True})) for k,v in full_weights.items()}
        applied = work.add_patches(patches, strength_patch=1., strength_model=0.)
        if len(applied) != len(patches):
            raise ValueError('MOSS pose input embedder could not be installed. Update ComfyUI or use MOSS SFT BF16.')
    vae = plan['vae']
    runtime = dict(family=family, start=plan['start'], end=plan['end'], strength=plan['strength'])
    if family == 'MOSS':
        encoded = [vae.encode(image(a)) for a in (color, depth)]
        control = torch.cat(encoded, dim=1)
        def concat_cond(**kwargs):
            noise = kwargs['noise']
            current = kwargs.get('concat_latent_image')
            if current is None:
                return noise.new_zeros((noise.shape[0], control.shape[1])+noise.shape[2:])
            current = comfy.utils.common_upscale(current.to(kwargs['device']), noise.shape[-1], noise.shape[-2], 'bilinear', 'center')
            return comfy.utils.resize_to_batch_size(work.model.process_latent_in(current), noise.shape[0])
        work.add_object_patch('concat_cond', concat_cond)
        runtime['control'] = control
    else:
        # The trained edit path encodes the VL image at <=384² and VAE at <=1MP.
        pixels = image(skeleton)
        h,w = pixels.shape[1:3]
        def fit(area, snap):
            scale=min(1., math.sqrt(area/(w*h)))
            nw,nh=max(snap,round(w*scale/snap)*snap),max(snap,round(h*scale/snap)*snap)
            return comfy.utils.common_upscale(pixels.movedim(-1,1),nw,nh,'area','disabled').movedim(1,-1)
        runtime['pixels'] = fit(384*384, 1)
        runtime['latent'] = work.model.process_latent_in(vae.encode(fit(1024*1024, 16)[:,:,:,:3]))
    work.model_options['rs_pose_runtime'] = runtime
    return work, runtime


def pose_conditioning(positive, negative, runtime):
    if runtime is None or runtime['family'] != 'MOSS':
        return positive, negative
    import node_helpers
    values = {'concat_latent_image': runtime['control']}
    return tuple(node_helpers.conditioning_set_values_with_timestep_range(c, values, runtime['start'], runtime['end'])
                 for c in (positive, negative))
