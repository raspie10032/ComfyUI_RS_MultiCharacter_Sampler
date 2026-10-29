# SPDX-License-Identifier: GPL-3.0-only
"""3D composition editor boundary: scene -> numbered masks -> building pipe."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import torch

from .character_builder import BUILD_PIPE_TYPE, BuildPipe, update_slot
from .pose3d import default_scene, read_scene, rasterize
from .region_mask import RegionMask

COLORS = [(255, 141, 145), (129, 188, 255), (148, 221, 157), (255, 210, 127), (195, 160, 255)]
def render_scene(raw, max_side=None):
    scene = read_scene(raw)
    full, visible = rasterize(scene, max_side)
    masks = full if scene['mask_mode'] == 'full' else visible
    for p, mask in zip(scene['people'], masks):
        if not mask.any():
            raise ValueError(f"Character {p['id']}: no silhouette on the canvas. Move it into view; if hidden, choose full silhouettes. / 캐릭터 {p['id']}: 화면 안에 보이는 영역이 없습니다. 카메라·위치를 조정하거나 전체 실루엣을 선택해 주세요.")
    return scene, full, visible


def preview(scene, full, visible):
    masks = full if scene['mask_mode'] == 'full' else visible
    h, w = masks.shape[1:]
    image = np.full((h, w, 3), [23, 28, 37], dtype=np.uint8)
    for p, mask in zip(scene['people'], masks):
        image[mask] = (image[mask].astype(float)*.35+np.array(COLORS[(p['id']-1) % 5])*.65).astype(np.uint8)
    result = Image.fromarray(image)
    draw = ImageDraw.Draw(result)
    for p, mask in zip(scene['people'], masks):
        yy, xx = np.nonzero(mask)
        if len(xx):
            draw.text((int(xx.mean()), int(yy.mean())), str(p['id']), fill='white', stroke_width=1, stroke_fill='black')
    return result


def preview_payload(raw):
    scene, full, visible = render_scene(raw, 192)
    selected = full if scene['mask_mode'] == 'full' else visible
    masks = []
    for p, mask in zip(scene['people'], selected):
        yy, xx = np.nonzero(mask)
        masks.append(dict(number=p['id'], width=mask.shape[1], height=mask.shape[0],
                          data=mask.astype(np.uint8).reshape(-1).tolist(),
                          center=[float((xx+.5).mean()/mask.shape[1]), float((yy+.5).mean()/mask.shape[0])]))
    return dict(canvas_width=scene['width'], canvas_height=scene['height'], masks=masks, scene=scene)


class RSMultiCharacterPose3D:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'scene_json': ('STRING', {'default': json.dumps(default_scene()), 'multiline': True,
                'tooltip': 'Open 3D editor, arrange mannequins, then Apply. Character numbers map to prompt slots. The scene is saved in the workflow.'})},
                'optional': {'building_pipe': (BUILD_PIPE_TYPE,)}, 'hidden': {'unique_id': 'UNIQUE_ID'}}

    RETURN_TYPES = (BUILD_PIPE_TYPE, 'IMAGE', 'MASK', 'MASK', 'STRING')
    RETURN_NAMES = ('building_pipe', 'mask_preview', 'full_masks', 'visible_masks', 'scene_info')
    FUNCTION = 'apply'
    CATEGORY = 'RS MultiCharacter/Characters'
    HAS_INTERMEDIATE_OUTPUT = True
    DESCRIPTION = ('Experimental 3D mannequin composition editor. Rotate joints and move people/camera; '
                   'each character number creates a 2D region mask. Full silhouettes overlap; visible silhouettes remove occluded areas. '
                   'Canvas overflow is clipped. No ControlNet or additional model. A composition guide, not exact pose enforcement. '
                   'Scene data is stored in the workflow. Connect anywhere before Finalize.')

    def apply(self, scene_json, building_pipe=None, unique_id=None):
        if building_pipe is not None and not isinstance(building_pipe, BuildPipe):
            raise ValueError('Connect an RS building pipe. / RS 조립 파이프를 연결해 주세요.')
        scene, full, visible = render_scene(scene_json)
        selected = full if scene['mask_mode'] == 'full' else visible
        pipe = building_pipe or BuildPipe()
        numbers = {p['id'] for p in scene['people']}
        # Remove only masks owned by a previous 3D scene, preserving later edits.
        previous = dict(pipe.pose3d_masks)
        for slot in pipe.slots:
            if slot.number not in numbers and slot.region_mask == previous.get(slot.number) and slot.number in previous:
                pipe = update_slot(pipe, slot.number, region_mask=None, body_parts=(), body_part_strength=0.)
        owned = []
        for p, mask in zip(scene['people'], selected):
            region = RegionMask(scene['width'], scene['height'], np.packbits(mask.reshape(-1)).tobytes())
            pipe = update_slot(pipe, p['id'], region_mask=region, body_parts=(), body_part_strength=0.)
            owned.append((p['id'], region))
        pipe = replace(pipe, pose3d_masks=tuple(owned))
        image = preview(scene, full, visible)
        images = []
        if unique_id is not None:
            import folder_paths
            directory = Path(folder_paths.get_temp_directory())/'RS_Pose3D'
            directory.mkdir(parents=True, exist_ok=True)
            filename = hashlib.sha256(image.tobytes()).hexdigest()+'.png'
            image.save(directory/filename)
            images = [{'filename': filename, 'subfolder': 'RS_Pose3D', 'type': 'temp'}]
        info = json.dumps(dict(character_ids=sorted(numbers), mask_mode=scene['mask_mode'],
                               canvas=[scene['width'], scene['height']], controlnet_used=False,
                               pose_enforcement=False), ensure_ascii=False)
        # Small UI rasters are separate from full-resolution sampling masks.
        return {'ui': {'images': images, 'text': [info], 'pose3d': [preview_payload(scene)]},
                'result': (pipe, torch.from_numpy(np.asarray(image).copy().astype(np.float32)/255)[None],
                           torch.from_numpy(full.astype(np.float32)), torch.from_numpy(visible.astype(np.float32)),
                           info)}


def register_routes():
    try:
        from server import PromptServer
        from aiohttp import web
    except ImportError:
        return
    server = getattr(PromptServer, 'instance', None)
    if server is None:
        return

    @server.routes.post('/rs_mc/pose3d/preview')
    async def pose3d_preview(request):
        try:
            import asyncio
            if request.content_length and request.content_length > 100_000:
                raise ValueError('3D scene exceeds 100 KB.')
            raw = await request.text()
            if len(raw) > 100_000:
                raise ValueError('3D scene exceeds 100 KB.')
            return web.json_response(await asyncio.to_thread(preview_payload, raw))
        except (ValueError, TypeError, KeyError) as error:
            return web.json_response({'error': str(error)}, status=400)


register_routes()
