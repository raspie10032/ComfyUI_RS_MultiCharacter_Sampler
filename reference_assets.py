# SPDX-License-Identifier: GPL-3.0-only
"""Pinned, opt-in reference weights. Nothing downloads on node import or OFF."""
import json
import hashlib
from pathlib import Path
from functools import lru_cache
import sys

CATALOG = json.loads(Path(__file__).with_suffix('.json').read_text())


@lru_cache(maxsize=32)
def _verified_digest(path, size, mtime_ns, ctime_ns):
    # Cache by file identity, never by path alone. Replacement/deletion must not
    # inherit a successful verification from an earlier sampling request.
    from .runtime_control import check_interrupted
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            check_interrupted()
            digest.update(block)
    return digest.hexdigest()


def _check_adapter(path, progress, name):
    spec = CATALOG[name]
    label = _adapter_label(name)
    progress.report(f'Checking {label} adapter / 어댑터 파일 확인 중', force=True)
    stat = path.stat()
    # Windows ctime is creation time; quick same-size writes can retain mtime
    # too. Rehash there instead of trusting a potentially unchanged cache key.
    verify = _verified_digest.__wrapped__ if sys.platform == 'win32' else _verified_digest
    digest = verify(str(path.resolve()), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    if digest != spec['sha256']:
        progress.report(f'{label} adapter checksum mismatch', failed=True, force=True)
        raise RuntimeError(f'{label} adapter is incomplete or differs from the supported version: '
                           f'{path}. Remove or replace this file, then queue again. / '
                           '어댑터 파일이 손상됐거나 지원 버전과 다릅니다. 해당 파일을 옮기거나 삭제한 뒤 다시 실행해 주세요.')
    progress.report(f'{label} adapter ready / 어댑터 준비 완료', 1., force=True)
    return path


def _adapter_label(name):
    return {'anima_role_kv': 'Anima Role K/V', 'anima_frame': 'Anima 2B reference-frame',
            'anima29_frame': 'Anima 2.9B reference-frame',
            'anima_frame_v2': 'Anima 2B asymmetric v2', 'krea_pose': 'Krea2 Turbo pose', 'moss_pose': 'MOSS color/depth pose'}[name]


def frame_adapter(model, node_id=None):
    """Choose by architecture, never checkpoint filename; verify even on reuse."""
    blocks = len(model.get_model_object('diffusion_model').blocks)
    if blocks not in (28, 40):
        raise ValueError('Anima reference frames support 28-block 2B or 40-block 2.9B models. / '
                         '참조 프레임은 Anima 2B(28블록)·2.9B(40블록)를 지원합니다.')
    return _verified_adapter('anima29_frame' if blocks == 40 else 'anima_frame', node_id)


def role_kv_adapter(node_id=None):
    return _verified_adapter('anima_role_kv', node_id)


def _verified_adapter(name, node_id=None):
    """Resolve/download the matching adapter only when its backend runs.

    A separate resolver avoids the legacy asset() path-only LRU: an interrupted
    download, changed file or removed external path must be checked on each run.
    Hugging Face handles temporary files, resumable transfers and download locks.
    """
    import folder_paths
    from .tagger_progress import TaggerProgress
    from .runtime_control import is_interruption
    spec = CATALOG[name]
    label = _adapter_label(name)
    progress = TaggerProgress(node_id)
    managed = Path(folder_paths.models_dir) / spec['folder'] / 'rs_reference' / spec['subdir']
    target = managed / spec['file']
    if target.is_file():
        return _check_adapter(target, progress, name)
    # Include ordinary LoRA folders: the author may have installed the adapter
    # there already. Keep our own managed adapter outside the style-LoRA list.
    roots = []
    for folder in ('ipadapter', 'loras'):
        roots.append(Path(folder_paths.models_dir) / folder)
        if folder in folder_paths.folder_names_and_paths:
            roots.extend(Path(p) for p in folder_paths.get_folder_paths(folder))
    for root in dict.fromkeys(roots):
        for candidate in root.rglob(Path(spec['file']).name):
            if candidate.is_file():
                return _check_adapter(candidate, progress, name)
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as error:
        raise RuntimeError(f'{label} automatic download needs huggingface-hub. '
                           'Install requirements-reference.txt. / 이미지 참조 의존성을 설치해 주세요: requirements-reference.txt') from error
    filename = Path(spec['file']).name
    size = {'anima_role_kv': '504 MiB', 'anima_frame_v2': '175 MiB'}.get(name, '88 MiB')
    progress.report(f'Downloading {label} adapter ({size}) / 어댑터 다운로드 중', force=True)
    try:
        downloaded = hf_hub_download(spec['repo'], spec['file'], revision=spec['revision'],
            local_dir=str(managed), tqdm_class=progress.download_bar(filename))
        return _check_adapter(Path(downloaded), progress, name)
    except Exception as error:
        if is_interruption(error):
            raise
        progress.report(f'{label} download or verification failed', failed=True, force=True)
        if isinstance(error, RuntimeError) and 'supported version' in str(error):
            raise
        raise RuntimeError(f'Cannot prepare the {label} adapter. Check network, free disk space '
                           'and model access, then queue again to resume. / '
                           '어댑터를 받지 못했습니다. 네트워크·저장 공간·모델 접근 상태를 확인하고 다시 실행해 주세요.') from error


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
