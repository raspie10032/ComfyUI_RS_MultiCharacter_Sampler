# SPDX-License-Identifier: GPL-3.0-only
"""Single image -> estimated, editable 3D MHR pose through ComfyUI's SAM3D.

Inference runs on ComfyUI's ordinary prompt queue, not inside an HTTP handler.
The downloaded inference weights remain local and are not redistributed.
"""
import copy
import json
from pathlib import Path

import numpy as np

from .mhr import asset, default_scene, global_matrices, mannequin
from .pose3d import read_scene
from .pose_library import retarget_rotations

REPO = 'Comfy-Org/sam-3d-body'
REVISION = '3d7eeedcb3fe5ab03235438b9e67c9b889eb97c1'
FILENAME = 'sam_3d_body_dinov3_bf16.safetensors'
SHA256 = '59fa45200c504c5b56625004d7d3385daf48c616613e88099e43bf83b3e249cf'


def prepare_model(node_id=None):
    import folder_paths
    from .reference_assets import _verified_digest
    from .tagger_progress import TaggerProgress
    from .runtime_control import check_interrupted
    progress = TaggerProgress(node_id)
    found = folder_paths.get_full_path('detection', FILENAME)
    if not found:
        try:
            from huggingface_hub import hf_hub_download
        except ImportError as e:
            raise RuntimeError('Image → 3D needs huggingface-hub. Install requirements-reference.txt.') from e
        progress.report('Downloading SAM 3D Body (2.83 GB) / 이미지→3D 모델 다운로드 중', force=True)
        found = hf_hub_download(REPO, 'detection/' + FILENAME, revision=REVISION,
                                local_dir=folder_paths.models_dir, tqdm_class=progress.download_bar(FILENAME))
        folder_paths.get_filename_list('detection')
    path = Path(found)
    progress.report('Checking SAM 3D Body / 이미지→3D 모델 확인 중', force=True)
    check_interrupted()
    stat = path.stat()
    # Use the same inode/mtime/digest checks as the other RS learned adapters.
    import sys
    verify = _verified_digest.__wrapped__ if sys.platform == 'win32' else _verified_digest
    if verify(str(path.resolve()), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != SHA256:
        raise ValueError('SAM 3D Body is incomplete or not the supported version. Replace detection/' + FILENAME)
    progress.report('Estimating editable 3D pose / 편집 가능한 3D 포즈 추정 중', force=True)
    return path


def source_frame(prediction, joints, image_size):
    """Transfer the source camera frustum to our neutral-proportion MHR body.

    SAM's camera uses Y-down/Z-forward; native MHR uses Y-up/Z-backward.
    Fit only torso anchors, so an inferred foot never decides photo framing.
    This preserves the input crop, not semantic visibility behind clothing.
    """
    d = asset()
    coords = np.asarray(prediction.get('pred_joint_coords'), dtype=float)
    camera = np.asarray(prediction.get('pred_cam_t'), dtype=float)
    focal = np.asarray(prediction.get('focal_length'), dtype=float)
    if (coords.shape != (len(d['names']), 3) or camera.shape != (3,) or focal.size != 1
            or not np.isfinite(coords).all() or not np.isfinite(camera).all()
            or not np.isfinite(focal).all() or float(focal.item()) <= 0 or camera[2] <= 0):
        raise ValueError('SAM 3D Body did not return valid image framing. / 원본 화면 범위를 읽지 못했습니다.')
    indices = [d['names'].index(d['controls'][key]) for key in
               ('pelvis', 'chest', 'neck', 'head', 'left_shoulder', 'right_shoulder')]
    target = global_matrices({d['controls'][k]: v for k, v in joints.items()})[indices, :3, 3]
    source = coords[indices]*[1, -1, -1]
    a, b = source-source.mean(0), target-target.mean(0)
    scale = float((a*b).sum()/max((a*a).sum(), 1e-12))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('Cannot align source image framing to the editable body.')
    offset = target.mean(0)-scale*source.mean(0)
    height, width = image_size
    kx, ky = width/(2*focal.item()), height/(2*focal.item())
    tx, ty, tz = camera
    planes = np.array([[1, 0, -kx, tx+kx*tz], [-1, 0, -kx, -tx+kx*tz],
                       [0, 1, -ky, -ty+ky*tz], [0, -1, -ky, ty+ky*tz],
                       [0, 0, -1, tz-.05]])
    planes[:, 3] = scale*planes[:, 3]-planes[:, :3] @ offset
    planes /= np.linalg.norm(planes[:, :3], axis=1, keepdims=True)
    eye = np.array([-tx, ty, tz])*scale+offset
    return planes.tolist(), dict(position=eye.tolist(), target=(eye-[0, 0, 1]).tolist(),
                                 fov=float(np.degrees(2*np.arctan(ky))))


def import_pose(rotations, scene_json='', character_number=1, prediction=None, image_size=None):
    if type(character_number) is not int or not 1 <= character_number <= 10:
        raise ValueError('Choose character number 1–10.')
    scene = read_scene(scene_json) if scene_json else default_scene()
    if scene['version'] != 2:
        raise ValueError('Image → 3D requires the MHR editor. Start a new 3D scene. / 새 3D 장면에서 사용해 주세요.')
    if not scene_json:
        p = copy.deepcopy(scene['people'][0])
        p.update(id=character_number, position=[0, 0, 0])
        scene['people'] = [p]
    person = next((p for p in scene['people'] if p['id'] == character_number), None)
    if person is None:
        raise ValueError(f'Character {character_number} is not in this 3D scene.')
    pose = retarget_rotations(rotations)
    person['joints'] = pose['joints']
    person.pop('source_frame', None)
    if prediction is not None:
        planes, camera = source_frame(prediction, person['joints'], image_size)
        person['source_frame'] = planes
        pose['source_frame'] = planes
        if not scene_json:
            # A standalone import preserves source framing. Existing scenes keep
            # their camera/other characters and carry a per-person source crop.
            scene['camera'] = camera
            h, w = image_size
            factor = min(1., 2048/max(h, w))
            scene.update(width=max(64, round(w*factor)), height=max(64, round(h*factor)))
    vertices, faces, _ = mannequin(person)
    if not len(faces):
        raise ValueError('No estimated body lies inside the source image. / 원본 화면 안에 추정된 몸이 없습니다.')
    before = person['position'][1]
    person['position'][1] -= float(vertices[:, 1].min())
    if prediction is not None and not scene_json:
        for key in ('position', 'target'):
            scene['camera'][key][1] += person['position'][1]-before
    return read_scene(scene), pose


class RSImageToPose3D:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',),
                            'character_number': ('INT', {'default': 1, 'min': 1, 'max': 10,
                            'tooltip': 'One person/crop per image. Only the source image frame is output; off-frame body parts are excluded.'})},
                'optional': {'base_scene': ('STRING', {'default': '', 'multiline': True,
                             'tooltip': 'Optional MHR scene JSON. Replace only this character; preserve camera and other people.'})},
                'hidden': {'unique_id': 'UNIQUE_ID'}}

    RETURN_TYPES = ('STRING',)
    RETURN_NAMES = ('scene_json',)
    FUNCTION = 'estimate'
    CATEGORY = 'RS MultiCharacter/Characters'
    OUTPUT_NODE = True
    DESCRIPTION = ('Estimate one editable 3D pose from one person/image crop using SAM 3D Body. '
                   'First use downloads 2.83 GB. Needs a ComfyUI core with SAM3DBody. '
                   'Prefer the Image → 3D button in the 3D editor for direct editing. '
                   'Only the source image frame is output. Hidden depth/joints inside the frame remain estimates. '
                   'No generation or reference model is modified.')

    def estimate(self, image, character_number=1, base_scene='', unique_id=None):
        if image.ndim != 4 or image.shape[0] != 1 or image.shape[-1] < 3 or min(image.shape[1:3]) < 32:
            raise ValueError('Image → 3D needs one RGB image (at least 32×32). Crop one person first. / 한 명이 나온 이미지 1장을 사용해 주세요.')
        # Validate the target scene before model download or GPU work.
        if base_scene:
            scene = read_scene(base_scene)
            if scene['version'] != 2 or not any(p['id'] == character_number for p in scene['people']):
                raise ValueError('Choose an existing person in a new MHR 3D scene.')
        try:
            from comfy_extras.nodes_sam3d_body import SAM3DBody_Loader, SAM3DBody_Predict
        except ImportError as e:
            raise RuntimeError('Update ComfyUI to a version with SAM3DBody_Loader and SAM3DBody_Predict. / 이미지→3D 기능에는 SAM 3D Body를 지원하는 ComfyUI가 필요합니다.') from e
        model_path = prepare_model(unique_id)
        import folder_paths
        model_name = None
        for root in folder_paths.get_folder_paths('detection'):
            try:
                model_name = str(model_path.resolve().relative_to(Path(root).resolve()))
                break
            except ValueError:
                continue
        if model_name is None:
            raise ValueError('SAM 3D Body must be installed in a configured detection model directory.')
        model = SAM3DBody_Loader.execute(model_name).result[0]
        prediction = SAM3DBody_Predict.execute(model, image[..., :3], run_hand_refinement=False, batch_size=1).result[0]
        people = prediction.get('frames', [[]])[0]
        if len(people) != 1 or 'pred_global_rots' not in people[0]:
            raise ValueError('Could not estimate one person. Use a clear full-body image or a single-person crop. / 한 명의 전신 이미지나 크롭으로 다시 시도해 주세요.')
        scene, pose = import_pose(people[0]['pred_global_rots'], base_scene, character_number,
                                  prediction=people[0], image_size=prediction['image_size'])
        raw = json.dumps(scene)
        return {'ui': {'rs_pose_image': [dict(pose=pose, scene=scene)]}, 'result': (raw,)}
