# SPDX-License-Identifier: GPL-3.0-only
"""Header-only installed-model inventory for the experimental RS workspace.

No model tensors, downloads, GPU allocations or user paths enter the response.
Unknown architectures stay unavailable instead of inheriting a guessed profile.
"""
import json
import struct
from functools import lru_cache


@lru_cache(maxsize=256)
def _header(path, size, mtime):
    with open(path, 'rb') as source:
        raw = source.read(8)
        if len(raw) != 8:
            raise ValueError('Incomplete safetensors header')
        length = struct.unpack('<Q', raw)[0]
        if length < 2 or length > min(size - 8, 64 * 1024 * 1024):
            raise ValueError('Invalid safetensors header size')
        data = source.read(length)
    header = json.loads(data)
    if not isinstance(header, dict):
        raise ValueError('Invalid safetensors header')
    return header


def classify(header, name=''):
    tensors = {key.removeprefix('model.diffusion_model.').removeprefix('diffusion_model.').removeprefix('net.'): value
               for key, value in header.items() if key != '__metadata__' and isinstance(value, dict)}
    keys = set(tensors)
    if 'llm_adapter.blocks.0.cross_attn.q_proj.weight' in keys:
        blocks = {key.split('.')[1] for key in keys if key.startswith('blocks.')}
        return {28: 'anima', 40: 'anima29'}.get(len(blocks))
    if 'shared_block_modulation.weight' in keys and 'layers.0.proj.ffn_up_gate.weight' in keys:
        return 'moss'
    if 'txtfusion.projector.weight' in keys:
        return 'krea2'
    if 'content_mode_blocks.image.0.attn_out.weight' in keys:
        return 'flux3' if 'ref_time_in.in_layer.weight' in keys else 'flux3_base'
    if 'double_blocks.0.img_attn.norm.key_norm.scale' in keys or 'double_blocks.0.img_attn.norm.key_norm.weight' in keys:
        if 'double_stream_modulation_img.lin.weight' in keys:
            dim = tensors.get('img_in.weight', {}).get('shape', [0])[0]
            if dim not in (3072, 4096, 6144):
                return None
            if dim == 6144:
                return 'flux2_dev'
            # Base/distilled Klein share their tensor schema. Distribution name
            # is an explicit preset hint, never used for architecture detection.
            base = 'base' in name.lower()
            return ('klein9' if dim == 4096 else 'klein4') + ('_base' if base else '')
        if any(key.startswith('distilled_guidance_layer') for key in keys):
            return None  # Chroma is not a FLUX.1 checkpoint.
        return 'flux1_dev' if any(key.startswith('guidance_in.') for key in keys) else 'flux1_schnell'
    if 'input_blocks.0.0.weight' in keys:
        context = next((value.get('shape', []) for key, value in tensors.items()
                        if key.endswith('attn2.to_k.weight')), [])
        if len(context) == 2:
            if context[1] == 2048:
                return 'sdxl'
            if context[1] == 768:
                return 'sd15'
    return None


def capabilities(profile):
    family = ('Anima' if profile.startswith('anima') else 'MOSS' if profile == 'moss' else
              'Krea2' if profile == 'krea2' else 'SDXL' if profile == 'sdxl' else
              'SD1.5' if profile == 'sd15' else 'FLUX3' if profile.startswith('flux3') else
              'FLUX1' if profile.startswith('flux1') else 'FLUX2')
    return dict(family=family,
                pose='lllite' if profile == 'anima' else 'scene_adapter' if family in ('Krea2', 'MOSS') else None,
                reference=family != 'FLUX1',
                reference_method='frame' if family == 'Anima' else 'native',
                layout='moss_native' if family == 'MOSS' else 'regional',
                pose_reference=family not in ('Krea2', 'MOSS'),
                pose_progressive=family not in ('Krea2', 'MOSS'),
                note='SD1.5: compatibility only; quality is not established.' if family == 'SD1.5' else '')


ENCODERS = {
    'anima': ('qwen_3_06b_base.safetensors', 'stable_diffusion', 'qwen_image_vae.safetensors'),
    'anima29': ('qwen_3_06b_base.safetensors', 'stable_diffusion', 'qwen_image_vae.safetensors'),
    'krea2': ('qwen3vl_4b_fp8_scaled.safetensors', 'krea2', 'qwen_image_vae.safetensors'),
    'moss': ('qwen3.5_9b_int8_convrot.safetensors', 'moss_image', 'flux2-vae.safetensors'),
    'klein4': ('qwen_3_4b.safetensors', 'flux2', 'flux2-vae.safetensors'),
    'klein9': ('qwen_3_8b_fp8mixed.safetensors', 'flux2', 'flux2-vae.safetensors'),
    'flux2_dev': ('mistral_3_small_flux2_fp8.safetensors', 'flux2', 'flux2-vae.safetensors'),
    'flux3': ('qwen3vl_4b_int8_convrot.safetensors', 'flux3', 'flux2-vae.safetensors'),
}
PRESETS = dict(anima='anima_points', anima29='anima_points', moss='moss_base', krea2='krea2',
               sdxl='sdxl_points', sd15='sd15_mixed', klein4='flux2_klein4', klein4_base='flux2_klein4_base',
               klein9='flux2_klein9', klein9_base='flux2_klein4_base', flux2_dev='flux2_dev',
               flux3='flux3_klein', flux3_base='flux3_klein_base',
               flux1_dev='flux1_dev', flux1_schnell='flux1_schnell')


def installed_models():
    import folder_paths
    encoders = folder_paths.get_filename_list('text_encoders')
    vaes = folder_paths.get_filename_list('vae')
    result, unavailable = [], []
    for category in ('checkpoints', 'diffusion_models'):
        for name in folder_paths.get_filename_list(category):
            if not name.endswith('.safetensors'):
                continue
            try:
                path = folder_paths.get_full_path_or_raise(category, name)
                from pathlib import Path
                stat = Path(path).stat()
                profile = classify(_header(path, stat.st_size, stat.st_mtime_ns), name)
                if profile is None:
                    continue
                item = dict(id=f'{category}/{name}', name=name, category=category, profile=profile,
                            preset=PRESETS[profile], capabilities=capabilities(profile), missing=[])
                if category == 'diffusion_models':
                    base = profile.removesuffix('_base')
                    if base not in ENCODERS:
                        item['missing'].append('This split model needs a loader configuration; use its bundled checkpoint.')
                    else:
                        encoder, clip_type, vae = ENCODERS[base]
                        def find(files, target):
                            return next((file for file in files if file.rsplit('/', 1)[-1] == target), None)
                        item.update(encoder=find(encoders, encoder), clip_type=clip_type, vae=find(vaes, vae))
                        if not item['encoder']:
                            item['missing'].append(f'Text encoder: {encoder}')
                        if not item['vae']:
                            item['missing'].append(f'VAE: {vae}')
                result.append(item)
            except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
                unavailable.append(dict(name=name, reason=f'{type(error).__name__}: cannot inspect model header'))
    return dict(models=result, unavailable=unavailable, schema=1)


def register_routes():
    try:
        from server import PromptServer
        from aiohttp import web
    except ImportError:
        return
    server = getattr(PromptServer, 'instance', None)
    if server is None:
        return

    @server.routes.get('/rs_mc/app/models')
    async def models(request):
        import asyncio
        return web.json_response(await asyncio.to_thread(installed_models))


register_routes()
