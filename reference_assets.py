# SPDX-License-Identifier: GPL-3.0-only
"""Pinned, opt-in reference weights. Nothing downloads on node import or OFF."""
import json
from pathlib import Path
from functools import lru_cache

CATALOG = json.loads(Path(__file__).with_suffix('.json').read_text())


@lru_cache(maxsize=16)
def asset(name, node_id=None):
    import folder_paths
    from .tagger_progress import TaggerProgress
    spec = CATALOG[name]
    filename = Path(spec['file']).name
    managed = Path(folder_paths.models_dir) / spec['folder'] / 'rs_reference' / spec['subdir']
    target = managed / spec['file']
    if target.is_file():
        return target
    # Reuse the user's existing models, including extra_model_paths directories.
    folders = tuple(dict.fromkeys((spec['folder'], 'ipadapter', 'clip_vision', 'siglip2', 'style_models')))
    roots = []
    for folder in folders:
        roots.append(Path(folder_paths.models_dir) / folder)
        if folder in folder_paths.folder_names_and_paths:
            roots += [Path(p) for p in folder_paths.get_folder_paths(folder)]
    for root in dict.fromkeys(roots):
        for candidate in root.rglob(filename):
            if not candidate.is_file():
                continue
            # Generic encoder/config filenames must match their model directory.
            if filename in ('model.safetensors', 'config.json', 'preprocessor_config.json'):
                if name.startswith('anima_') and 'siglip2-base-patch16-512' not in candidate.parts:
                    continue
                if name == 'sd_encoder' and 'image_encoder' not in candidate.parts:
                    continue
                if name == 'redux_encoder' and not any('siglip-so400m-patch14-384' in p for p in candidate.parts):
                    continue
            return candidate
    progress = TaggerProgress(node_id)
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as error:
        raise RuntimeError('Image reference needs requirements-reference.txt. / 이미지 참조 의존성을 설치해 주세요: requirements-reference.txt') from error
    progress.report('Experimental reference: downloading ' + filename, force=True)
    try:
        path = hf_hub_download(spec['repo'], spec['file'], revision=spec['revision'],
                               local_dir=str(managed), tqdm_class=progress.download_bar(filename))
    except Exception as error:
        progress.report('Reference download failed: ' + filename, failed=True, force=True)
        raise RuntimeError(f'Cannot download reference model {filename}. Check network, free disk space and model access.') from error
    progress.report('Reference model ready: ' + filename, 1., force=True)
    return Path(path)
