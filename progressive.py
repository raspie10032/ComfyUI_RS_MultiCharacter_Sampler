# SPDX-License-Identifier: GPL-3.0-only
"""Progressive T2I using native samplers and a single full noise schedule.

Native solver histories restart when the latent grid changes. Conditional masks
are resized from the full-resolution originals, never from a previous small grid.
No global sampling functions or model methods are replaced.
"""
import json
import math

import torch
import torch.nn.functional as F

from .nodes import RSMultiCharacterSampler


def validate_scale(scale):
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not math.isfinite(scale) or not .5 <= scale <= 1.:
        raise ValueError('Start scale must be a finite number from 0.5 to 1.0. / 시작 배율은 0.5~1.0입니다.')
    return float(scale)


def resolution_plan(width, height, steps, scale, alignment=16):
    """8/16/30 trial proportions, rounded to model-compatible spatial grids."""
    scale = validate_scale(scale)
    if type(steps) is not int or not 2 <= steps <= 100:
        raise ValueError('Use 2–100 total sampling steps.')
    if any(type(v) is not int or v < 64 or v > 4096 or v % 16 for v in (width, height)):
        raise ValueError('Final dimensions must be 64–4096 and divisible by 16.')
    cuts = (0, max(1, round(steps * 8 / 30)), min(steps-1, max(1, round(steps * 16 / 30))))
    stages = []
    for start, factor in zip(cuts, (scale, (1 + scale) / 2, 1.)):
        w, h = (max(alignment, min(v, round(v * factor / alignment) * alignment)) for v in (width, height))
        if stages and stages[-1]['start'] == start:
            stages.pop()  # Short schedules must still reach the final size.
        if stages and (stages[-1]['width'], stages[-1]['height']) == (w, h):
            continue
        stages.append(dict(start=start, width=w, height=h))
    for i, stage in enumerate(stages):
        stage['end'] = stages[i+1]['start'] if i+1 < len(stages) else steps
    return stages


def resize_lanczos(tensor, size):
    """Lanczos-3 in floating point for 4-D and single-frame 5-D latents."""
    old_h, old_w = tensor.shape[-2:]
    new_h, new_w = size
    if (old_h, old_w) == (new_h, new_w):
        return tensor
    if new_h < old_h or new_w < old_w:
        raise ValueError('Progressive Lanczos only expands the latent grid.')

    def weights(old, new):
        position = (torch.arange(new, device=tensor.device, dtype=torch.float32) + .5) * (old / new) - .5
        delta = position[:, None] - torch.arange(old, device=tensor.device, dtype=torch.float32)[None, :]
        kernel = torch.sinc(delta) * torch.sinc(delta / 3)
        kernel = torch.where(delta.abs() < 3, kernel, torch.zeros_like(kernel))
        return kernel / kernel.sum(dim=1, keepdim=True)

    return (weights(old_h, new_h) @ tensor.float() @ weights(old_w, new_w).T).to(tensor.dtype)


def resize_mask(mask, size):
    shape = mask.shape
    return F.interpolate(mask.reshape(-1, 1, *shape[-2:]).float(), size=size,
                         mode='bilinear', align_corners=False).reshape(*shape[:-2], *size).to(mask)


def stage_integrator(native, plan, settings, model_sampling, final_grid, audit):
    """Call the installed native solver on contiguous slices of its own sigmas."""
    def integrate(model, x, sigmas, extra_args=None, callback=None, disable=None):
        import comfy.sample
        import comfy.model_management
        total = len(sigmas) - 1
        seed = settings['seed']
        generator = torch.Generator(device=x.device).manual_seed(seed ^ 0x5EED1234)
        ancestral = torch.Generator(device=x.device).manual_seed((seed + (x.device.type == 'cpu')) % 2**64)
        last_denoised = None
        # ComfyUI prepared these at the FINAL size. Preserve their details and
        # hooks, then adapt only spatial masks for each intermediate call.
        guider = model.inner_model
        mask_sources = [(condition, condition['mask']) for conditions in guider.conds.values()
                        for condition in conditions if isinstance(condition.get('mask'), torch.Tensor)]
        audit['mask_conditions'] = len(mask_sources)
        audit['sigmas'] = sigmas.detach().cpu().tolist()
        audit['transitions'], audit['segments'] = [], []
        try:
            for index, stage in enumerate(plan):
                comfy.model_management.throw_exception_if_processing_interrupted()
                start, end = stage['start'], stage['end']
                target = (round(final_grid[0]*stage['height']/settings['height']),
                          round(final_grid[1]*stage['width']/settings['width']))
                if index == 0:
                    initial = resize_mask(model.latent_image, target)
                    noise = comfy.sample.prepare_noise(initial, seed).to(x)
                    maximum = float(model_sampling.sigma_max)
                    max_denoise = math.isclose(maximum, float(sigmas[0]), rel_tol=1e-5) or float(sigmas[0]) > maximum
                    x = model_sampling.noise_scaling(sigmas[0], noise, initial, max_denoise)
                elif x.shape[-2:] != target:
                    if last_denoised is None:
                        raise RuntimeError('The selected sampler did not return a clean latent estimate before expansion.')
                    clean = resize_lanczos(last_denoised, target)
                    fresh = torch.randn(clean.shape, dtype=clean.dtype, device=clean.device, generator=generator)
                    previous = list(x.shape)
                    x = model_sampling.noise_scaling(sigmas[start], fresh, clean)
                    audit['transitions'].append(dict(before_step=start+1, old_shape=previous,
                        new_shape=list(x.shape), sigma=float(sigmas[start])))
                for condition, original in mask_sources:
                    condition['mask'] = resize_mask(original, target)
                audit['segments'].append({**stage, 'latent_grid': list(target), 'callbacks': 0})
                segment = audit['segments'][-1]

                def report(data):
                    nonlocal last_denoised
                    last_denoised = data['denoised'].detach()
                    segment['callbacks'] += 1
                    if callback is not None:
                        record = dict(data)
                        # Adaptive solvers can evaluate more than once per
                        # interval. Keep progress on the original full schedule.
                        if 'sigma' in data:
                            nearest = int((sigmas[:-1] - data['sigma']).abs().argmin())
                            record['i'] = max(start, min(end-1, nearest))
                        else:
                            record['i'] = min(end-1, start + data['i'])
                        callback(record)

                arguments = {**(extra_args or {}), 'seed': (seed + index * 10000) % 2**64}
                options = dict(native.extra_options)
                if settings['sampler_name'] == 'euler_ancestral':
                    # Preserve one ancestral random stream across expansions,
                    # matching the experiment without restarting its seed.
                    options['noise_sampler'] = lambda _s, _n: torch.randn(x.shape, dtype=x.dtype, device=x.device, generator=ancestral)
                last_denoised = None
                x = native.sampler_function(model, x, sigmas[start:end+1], extra_args=arguments,
                    callback=report, disable=disable, **options)
                if not torch.isfinite(x).all():
                    raise RuntimeError('Progressive sampling returned nonfinite latents. Try the model’s recommended sampler/settings.')
            if x.shape[-2:] != tuple(final_grid):
                raise RuntimeError('Progressive sampling did not reach the final resolution.')
            return x
        finally:
            for condition, original in mask_sources:
                condition['mask'] = original
    return integrate


class RSMultiCharacterProgressiveSampler(RSMultiCharacterSampler):
    @classmethod
    def INPUT_TYPES(cls):
        schema = super().INPUT_TYPES()
        required = schema['required']
        position = list(required).index('seed')
        items = list(required.items())
        items.insert(position, ('start_scale', ('FLOAT', {'default': .67, 'min': .5, 'max': 1., 'step': .01,
            'tooltip': 'Starting width/height relative to the final size. Trade some detail for faster large-image sampling. Lower scales can lose more detail or change composition; quality is not guaranteed. 1.0 uses ordinary sampling. Existing multi-character prompts, masks and LoRAs remain available.'})))
        schema['required'] = dict(items)
        return schema

    DESCRIPTION = ('Progressive T2I: trades some detail for faster large-image sampling by starting smaller and expanding with Lanczos. Lower start scales can lose more detail or change composition; quality is not guaranteed. '
                   'Existing multi-character prompts, masks, text, per-character LoRAs and outputs remain available. '
                   '1.0 uses the ordinary sampler exactly. Solver history restarts at expansion; quality and speed depend on the model/sampler.')

    def generate(self, model, character_pipe, start_scale=.67, **kwargs):
        from .pipe_compat import local_pipe
        character_pipe = local_pipe(character_pipe)
        if kwargs.get('use_image_settings') and character_pipe.generation_json:
            stored = json.loads(character_pipe.generation_json).get('settings', {}).get('progressive_resolution')
            if stored is not None:
                start_scale = stored['start_scale']
        model = model.clone()
        model.model_options['rs_progressive_scale'] = validate_scale(start_scale)
        result = super().generate(model=model, character_pipe=character_pipe, **kwargs)
        record = json.loads(result['result'][3])['rs_multicharacter']['settings']['progressive_resolution']
        result['ui']['text'].append('Lanczos · ' + ' → '.join(
            f"{s['width']}×{s['height']} [{s['start']+1}–{s['end']}]" for s in record['plan']))
        return result

    def _sample_latent(self, work, latent, settings, positive, negative, audit):
        import comfy.sample
        import comfy.samplers
        import comfy.utils
        import latent_preview
        scale = work.model_options['rs_progressive_scale']
        dm = work.get_model_object('diffusion_model')
        patch = getattr(dm, 'patch_spatial', getattr(dm, 'patch', 1))
        alignment = math.lcm(16, patch * (settings['width'] // latent.shape[-1]))
        plan = resolution_plan(settings['width'], settings['height'], settings['steps'], scale, alignment)
        configuration = dict(start_scale=scale, interpolation='lanczos', plan=plan)
        settings['progressive_resolution'] = configuration
        audit['progressive_resolution'] = {**configuration, 'solver_history_restarts_at_expansion': len(plan) > 1}
        if len(plan) == 1:
            return super()._sample_latent(work, latent, settings, positive, negative, audit)
        # Configure only this model clone. All routing engines keep their full
        # schedule, and rebuild their token/mask groups at each new grid.
        work.model_options.setdefault('transformer_options', {})['rs_resolution_separation'] = dict(
            final_grid=[v // patch for v in latent.shape[-2:]], final_latent_grid=list(latent.shape[-2:]))
        schedule = comfy.samplers.KSampler(work, settings['steps'], work.load_device,
            sampler=settings['sampler_name'], scheduler=settings['scheduler'], denoise=1.).sigmas
        native = comfy.samplers.sampler_object(settings['sampler_name'])
        sampler = comfy.samplers.KSAMPLER(stage_integrator(native, plan, settings,
            work.get_model_object('model_sampling'), latent.shape[-2:], audit['progressive_resolution']),
            inpaint_options=native.inpaint_options)
        noise = comfy.sample.prepare_noise(latent, settings['seed'])
        return comfy.sample.sample_custom(work, noise, settings['cfg'], sampler, schedule, positive, negative,
            latent, callback=latent_preview.prepare_callback(work, settings['steps']),
            disable_pbar=not comfy.utils.PROGRESS_BAR_ENABLED, seed=settings['seed'])
