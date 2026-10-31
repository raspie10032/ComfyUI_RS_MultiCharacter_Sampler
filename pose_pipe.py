# SPDX-License-Identifier: GPL-3.0-only
"""Deferred 3D guidance: the sampler owns model-specific loading and patching."""
import json
import math
import os
from pathlib import Path

import numpy as np
import torch
from .pose3d import read_scene


def pipe_pose_settings(raw):
    if isinstance(raw, str):
        if len(raw) > 110_000:
            raise ValueError('3D pose settings exceed 110 KB.')
        raw = json.loads(raw)
    if not isinstance(raw, dict) or raw.get('mode') not in ('auto', 'masks_only'):
        raise ValueError('Choose auto or masks_only in the 3D pose node. / 3D 포즈 적용 방식을 확인해 주세요.')
    strength, start, end = (raw.get(k) for k in ('strength', 'start', 'end'))
    for value, low, high in ((strength, 0., 2.), (start, 0., 1.), (end, 0., 1.)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('Invalid 3D pose strength or interval. / 3D 포즈 강도·구간을 확인해 주세요.')
    if end <= start:
        raise ValueError('3D pose end must follow start. / 3D 포즈 종료는 시작보다 커야 합니다.')
    return dict(scene=read_scene(raw.get('scene')), mode=raw['mode'], strength=strength, start=start, end=end)


def apply_pipe_pose(model, vae, pipe, family, width, height, node_id=None):
    """Never modify the source model or download weights for mask-only routes."""
    if pipe.pose3d_json is None:
        return model, None
    plan = pipe_pose_settings(pipe.pose3d_json)
    status = dict(mode=plan['mode'], family=family, applied=False)
    if plan['mode'] == 'masks_only' or plan['strength'] == 0:
        return model, {**status, 'reason': 'masks_only'}
    if family not in ('Anima', 'Krea2', 'MOSS'):
        return model, {**status, 'reason': 'No matching trained adapter; region masks only.'}
    if family == 'Anima' and len(model.get_model_object('diffusion_model').blocks) != 28:
        return model, {**status, 'reason': 'Anima pose weights support 2B only; region masks only.'}
    if model.model_options.get('rs_3d_pose') or model.model_options.get('transformer_options', {}).get('patches'):
        raise ValueError('3D pose is already patched on MODEL. Use the 3D building pipe alone; remove the older pose adapter. / '
                         '포즈가 모델에 중복 연결되었습니다. 이전 모델 어댑터를 빼고 3D 조립 파이프만 사용해 주세요.')
    if (model.model_options.get('rs_anima_ref_frame_plan') is not None or
            model.model_options.get('rs_image_reference') is not None or
            any(c.reference is not None and c.reference.strength > 0 for c in pipe.characters)):
        raise ValueError('3D pose adapter + image reference is not supported together. Choose masks_only or disable references. / '
                         '3D 자세 유도와 이미지 참조는 동시 지원하지 않습니다. 마스크 전용으로 바꾸거나 참조를 꺼 주세요.')
    if family in ('Krea2', 'MOSS'):
        if model.model_options.get('rs_progressive_scale', 1.) != 1.:
            raise ValueError('3D pose adapter needs full resolution on Krea2/MOSS. Choose masks_only or start scale 1. / '
                             'Krea2/MOSS 자세 유도는 고정 해상도로 사용해 주세요.')
        work = model.clone()
        work.model_options['rs_3d_pose'] = dict(family=family, scene=plan['scene'], vae=vae,
            strength=plan['strength'], start=plan['start'], end=plan['end'], node_id=node_id)
    else:
        try:
            from comfy_extras.nodes_model_patch import ModelPatchLoader, AnimaLLLiteApply
        except ImportError as error:
            raise ValueError('Update ComfyUI for native Anima LLLite pose support. / Anima 포즈 지원을 위해 ComfyUI를 업데이트해 주세요.') from error
        import folder_paths
        from .reference_assets import _verified_adapter
        from .anima_pose_control import validate_model_patches
        from .pose3d_node import render_scene
        rgb = render_scene(dict(plan['scene'], width=width, height=height), shaded=True)[3]
        image = torch.from_numpy(rgb.astype(np.float32) / 255)[None]
        path = _verified_adapter('anima_pose', node_id)
        name = next((os.path.relpath(path, root) for root in folder_paths.get_folder_paths('model_patches')
                     if Path(path).is_relative_to(Path(root))), None)
        if name is None:
            raise ValueError('Anima pose adapter must be inside a configured model_patches folder.')
        patch = ModelPatchLoader().load_model_patch(name)[0]
        work = AnimaLLLiteApply().apply_patch(model, patch, image, plan['strength'], plan['start'], plan['end'])[0]
        validate_model_patches(work, 'Anima')
    return work, {**status, 'applied': True, 'strength': plan['strength'], 'start': plan['start'], 'end': plan['end']}
