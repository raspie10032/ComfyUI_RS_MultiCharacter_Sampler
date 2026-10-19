# SPDX-License-Identifier: GPL-3.0-only
"""Regional routing for native FLUX image models, including FLUX 3 flow maps.

The caller's model stays untouched. Text positions restart for each caption;
FLUX 3's early text blocks run independently before joint image/text attention.
"""
import torch
import torch.nn.functional as F

from .joint_engine import JointRouting


def flux_family(model):
    from comfy import model_base
    for name, family in (("Flux3", "FLUX3"), ("Flux2", "FLUX2"), ("Flux", "FLUX1")):
        if type(model.model) is getattr(model_base, name, None):
            dm = model.model.diffusion_model
            if family != "FLUX3" and not hasattr(dm.params, "global_modulation"):
                raise ValueError("Update ComfyUI before using FLUX regional generation. / FLUX 영역 생성을 사용하려면 ComfyUI를 업데이트해 주세요.")
            if family != "FLUX3" and dm.params.in_channels != dm.params.out_channels:
                raise ValueError("FLUX Fill/Control models need extra image inputs. Use a FLUX text-to-image model here.")
            return family
    return None


def reset_flux3_positions(tensor, heads, lengths, image_tokens, pre_shaped=False):
    """Undo only the concatenation offset on FLUX 3's last RoPE axis."""
    x = tensor.transpose(1, 2) if pre_shaped else tensor.unflatten(-1, (heads, -1))
    if x.shape[-1] != 128:
        raise ValueError("Unsupported FLUX 3 rotary head size; update regional routing.")
    out = x.clone()
    omega = 10000. ** (-torch.arange(0, 32, 2, device=x.device, dtype=torch.float32) / 32)
    offset = 0
    for length in lengths:
        if offset:
            pairs = x[:, image_tokens+offset:image_tokens+offset+length, :, -32:].float().unflatten(-1, (16, 2))
            angle = -offset * omega
            a, b = pairs[..., 0], pairs[..., 1]
            rotated = torch.stack((a * angle.cos() - b * angle.sin(), a * angle.sin() + b * angle.cos()), -1)
            out[:, image_tokens+offset:image_tokens+offset+length, :, -32:] = rotated.flatten(-2).to(x.dtype)
        offset += length
    return out.transpose(1, 2) if pre_shaped else out.flatten(2)


class FluxRouting(JointRouting):
    def __init__(self, *args, regional_loras=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.regional_loras = regional_loras
        self.text_cache = {}

    def install(self, work):
        from comfy.patcher_extension import WrappersMP
        options = work.model_options['transformer_options']
        if options.get('optimized_attention_override'):
            raise ValueError('Disconnect other attention overrides before regional sampling.')
        options['optimized_attention_override'] = self.attention
        if self.family != 'FLUX3':
            options.setdefault('patches', {}).setdefault('post_input', []).append(self.text_positions)
        work.add_wrapper_with_key(WrappersMP.SAMPLER_SAMPLE, 'rs_multicharacter', self.sample)
        work.add_wrapper_with_key(WrappersMP.DIFFUSION_MODEL, 'rs_multicharacter',
                                  self.flux3_forward if self.family == 'FLUX3' else self.flux_forward)

    def sample(self, executor, *args, **kwargs):
        self.text_cache.clear()
        try:
            return super().sample(executor, *args, **kwargs)
        finally:
            self.text_cache.clear()

    def text_positions(self, data):
        if self.state is None:
            return data
        ids = data['txt_ids'].clone()
        start = 0
        # Keep each axis' native pattern, including FLUX.1's all-zero text IDs.
        for length in self.state['lengths']:
            ids[:, start:start+length] = data['txt_ids'][:, :length]
            start += length
        return {**data, 'txt_ids': ids}

    def flux_forward(self, executor, x, timestep, context, y=None, guidance=None,
                     ref_latents=None, control=None, transformer_options=None, **kwargs):
        if ref_latents is not None or control is not None or kwargs.get('attention_mask') is not None:
            raise ValueError('FLUX regional generation expects text-to-image inputs without reference images or ControlNet.')
        patch = executor.class_obj.patch_size
        def invoke(xb, tb, cb, options):
            batch = options['rs_mc_batch']
            def sliced(value):
                return value[batch:batch+1] if isinstance(value, torch.Tensor) and value.shape[0] == x.shape[0] else value
            return executor(xb, tb, cb, y=sliced(y), guidance=sliced(guidance),
                            transformer_options=options, **kwargs)
        # FLUX.2 pads short encodes to 512 before native inference.
        previous = self.conditions
        if self.family == 'FLUX2':
            self.conditions = [(F.pad(c, (0, 0, max(0, 512-c.shape[1]), 0)), m) for c, m in previous]
        try:
            return self.forward(invoke, x, timestep, context, transformer_options,
                                ((x.shape[-2]+patch-1)//patch, (x.shape[-1]+patch-1)//patch))
        finally:
            self.conditions = previous

    def flux3_forward(self, executor, x, timestep, context=None, ref_latents=None,
                      transformer_options=None, txt_states=None, ref_states=None, ref_shapes=None, **kwargs):
        if ref_latents is not None or ref_states is not None or ref_shapes is not None:
            raise ValueError('FLUX 3 regional generation currently expects text-to-image inputs without reference images.')
        dm = executor.class_obj
        options = transformer_options or {}
        # Flow-map text modulation depends on the next sigma, not just on text.
        target = None
        if dm.flow_map:
            from comfy.ldm.flux.layers import timestep_embedding
            sigmas = options['sample_sigmas']
            index = int((sigmas - timestep[0]).abs().argmin())
            sigma = sigmas[min(index+1, len(sigmas)-1)].reshape(1).to(x)
            target = dm.ref_time_in(timestep_embedding(sigma, 256))
        def refine(c, key):
            cacheable = not dm.flow_map and not self.regional_loras
            if cacheable and key in self.text_cache:
                return self.text_cache[key]
            states, _ = dm.preprocess_conds(c.to(x), vec_target=target, transformer_options=options)
            if cacheable:
                self.text_cache[key] = states
            return states
        # A cached common encode may replace context in ComfyUI's extra_conds.
        common = txt_states if txt_states is not None else dm.preprocess_conds(context.to(x), vec_target=target, transformer_options=options)[0]
        previous = self.conditions
        self.conditions = [(refine(c, index), meta) for index, (c, meta) in enumerate(previous)]
        def invoke(xb, tb, cb, branch_options):
            return executor(xb, tb, context=None, transformer_options=branch_options,
                            txt_states=cb, **kwargs)
        try:
            return self.forward(invoke, x, timestep, common, options, x.shape[-2:])
        finally:
            self.conditions = previous

    def attention(self, original, q, k, v, heads, mask=None, **kwargs):
        if self.family == 'FLUX3' and self.state is not None:
            if 'block_index' not in kwargs.get('transformer_options', {}):
                # Early image blocks have no text; native self-attention applies.
                return original(q, k, v, heads, mask=mask, **kwargs)
            q, k = [reset_flux3_positions(t, heads, self.state['lengths'],
                                          self.state['image_tokens'], kwargs.get('skip_reshape', False)) for t in (q, k)]
        return super().attention(original, q, k, v, heads, mask=mask, **kwargs)
