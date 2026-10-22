# SPDX-License-Identifier: GPL-3.0-only
"""OpenPose PNG/coordinates to editable person masks; no pose model required."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import torch

from .character_builder import BUILD_PIPE_TYPE, BuildPipe, update_slot
from .pose_parts import compile_semantic_parts
from .region_mask import prepare_mask
from .pose_image import decode_pose_image

NO_POSE_IMAGE = '(none)'


def pose_files():
    import folder_paths
    root=Path(folder_paths.get_input_directory())
    files=[p.name for p in root.iterdir() if p.is_file() and p.suffix.lower() in ('.png','.webp','.jpg','.jpeg')]
    uploaded=root/'RS_OpenPose'
    if uploaded.is_dir():
        files += ['RS_OpenPose/'+p.name for p in uploaded.iterdir() if p.is_file() and p.suffix.lower() in ('.png','.webp','.jpg','.jpeg')]
    return [NO_POSE_IMAGE,*sorted(files)]


def read_pose_image(filename):
    import folder_paths
    root=Path(folder_paths.get_input_directory()).resolve()
    if not isinstance(filename,str) or not filename or Path(filename).is_absolute():
        raise ValueError('Select an uploaded pose PNG. / 업로드한 뼈대 PNG를 선택해 주세요.')
    path=(root/filename).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Pose PNG is missing. Upload it again. / 뼈대 PNG를 찾지 못했습니다. 다시 업로드해 주세요.')
    try:
        with Image.open(path) as image:
            if max(image.size)>2048 or min(image.size)<64:
                raise ValueError('Pose PNG must be 64–2048 pixels per side. / 뼈대 PNG의 각 변을 64~2048픽셀로 맞춰 주세요.')
            if getattr(image,'n_frames',1)!=1:
                raise ValueError('Use one pose image, not an animation. / 움직이는 이미지 대신 뼈대 한 장을 넣어 주세요.')
            rgba=image.convert('RGBA')
            background=Image.new('RGBA',rgba.size,(0,0,0,255))
            return np.asarray(Image.alpha_composite(background,rgba).convert('RGB'))
    except (OSError,Image.DecompressionBombError) as error:
        raise ValueError('Cannot read the pose image. Reupload a valid PNG. / 뼈대 이미지를 읽지 못했습니다. PNG로 다시 저장해 주세요.') from error


def resolve_pose(pose_json, pose_keypoints=None, image=None, pose_image=NO_POSE_IMAGE, width=512, height=768):
    if pose_keypoints is not None:
        return normalize_pose(pose_keypoints,width,height),[],'keypoints'
    if image is not None:
        if (not isinstance(image,torch.Tensor) or image.ndim!=4 or image.shape[0]!=1 or image.shape[-1] not in (3,4)
                or not torch.isfinite(image).all() or image.min()<0 or image.max()>1):
            raise ValueError('Connect one RGB pose IMAGE, not a batch. / RGB 뼈대 이미지 한 장만 연결해 주세요.')
        array=image[0].detach().cpu().float().numpy()
        if array.shape[-1]==4:array=array[:,:,:3]*array[:,:,3:4]
        data,notes=decode_pose_image(np.rint(array*255).astype(np.uint8))
        return data,notes,'connected_image'
    if pose_image not in (NO_POSE_IMAGE,'',None):
        data,notes=decode_pose_image(read_pose_image(pose_image))
        return data,notes,'png'
    return normalize_pose(pose_json,width,height),[],'json'


def normalize_pose(value, width=512, height=768):
    try:
        if isinstance(value, str):
            if len(value) > 2*1024*1024:
                raise ValueError('OpenPose JSON is too large.')
            value = json.loads(value)
        if isinstance(value, list):
            if len(value) != 1:
                raise ValueError('Use one pose frame, not a video batch. / 포즈는 한 프레임만 연결해 주세요.')
            value = value[0]
        if not isinstance(value, dict) or not isinstance(value.get('people'), list) or not 1 <= len(value['people']) <= 10:
            raise ValueError('OpenPose JSON needs 1–10 people. / people 배열이 있는 OpenPose JSON을 넣어 주세요.')
        if value.get('coordinate_space', 'pixels') != 'pixels':
            raise ValueError('Use pixel coordinates, not normalized coordinates. / 픽셀 좌표로 내보내 주세요.')
        sizes = {len(p.get('pose_keypoints_2d', [])) for p in value['people'] if isinstance(p, dict)}
        if len(sizes) != 1 or sizes.pop() not in (54, 75):
            raise ValueError('Use COCO-18 or BODY-25 body keypoints. / COCO-18·BODY-25 관절만 지원합니다.')
        layout = 'COCO_18' if len(value['people'][0]['pose_keypoints_2d']) == 54 else 'BODY_25'
        if value.get('pose_model', layout) != layout:
            raise ValueError('Declared pose_model differs from keypoint count.')
        return dict(coordinate_space='pixels', pose_model=layout,
                    canvas_width=value.get('canvas_width', width), canvas_height=value.get('canvas_height', height),
                    people=[{'pose_keypoints_2d': p.get('pose_keypoints_2d')} for p in value['people']])
    except (TypeError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid OpenPose JSON. Use Load Pose PNG or import valid coordinates. / JSON이 올바르지 않습니다. 뼈대 PNG 불러오기 버튼을 사용해 주세요.') from error


def preview_image(data, people, parts, confidence=.2):
    w, h = data['canvas_width'], data['canvas_height']
    image = Image.new('RGB', (w,h), (23,28,37))
    colors = [(255,141,145),(129,188,255),(148,221,157),(255,210,127),(195,160,255)]
    for i, mask in enumerate(people):
        image = Image.composite(Image.new('RGB',(w,h),colors[i%5]), image,
                                Image.fromarray((mask.tensor().numpy()*95).astype(np.uint8)))
    draw = ImageDraw.Draw(image)
    for i, person in enumerate(data['people']):
        pts=np.asarray(person['pose_keypoints_2d']).reshape(-1,3)
        hips=(8,11) if len(pts)==18 else (9,12)
        links=[(0,1),(1,2),(2,3),(3,4),(1,5),(5,6),(6,7),(2,hips[0]),(5,hips[1]),(hips[0],hips[1])]
        for start in hips:links += [(start,start+1),(start+1,start+2)]
        for a,b in links:
            if pts[a,2] >= confidence and pts[b,2] >= confidence:
                draw.line([tuple(pts[a,:2]),tuple(pts[b,:2])],fill=colors[i%5],width=max(2,w//180))
        x,y=people[i].center;draw.text((x*w,y*h),str(i+1),fill='white',stroke_width=1,stroke_fill='black')
    return image


class RSMultiCharacterPoseMasks:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'pose_json': ('STRING', {'default': '', 'multiline': True,
                'tooltip': 'Advanced coordinate input. Prefer Load Pose PNG. Connected keypoints override images; an image overrides this JSON. JSON array order maps to character numbers.'}),
            'thickness': ('FLOAT', {'default': 1., 'min': .25, 'max': 3., 'step': .05,
                'tooltip': 'Person-mask limb width and body padding. Position node moves/resizes the whole person and part masks together.'}),
            'body_part_strength': ('FLOAT', {'default': 0., 'min': 0., 'max': .8, 'step': .05,
                'tooltip': 'Very weak attention guidance using body-part names at their mapped locations. 0 = OFF. / 뼈대 자체가 아니라 해당 위치에 부위 이름을 넣어 아주 약하게 어텐션을 유도합니다. 0 = 끄기.'}),
        }, 'optional': {
            'building_pipe': (BUILD_PIPE_TYPE,),
            'pose_keypoints': ('POSE_KEYPOINT', {'tooltip': 'Optional DWPose/OpenPose single-frame coordinates; overrides the JSON text.'}),
            'canvas_width': ('INT', {'default':512,'min':64,'max':2048,'step':16,
                'tooltip':'Fallback only when JSON has no canvas_width. Use the ORIGINAL pose canvas size.'}),
            'canvas_height': ('INT', {'default':768,'min':64,'max':2048,'step':16,
                'tooltip':'Fallback only when JSON has no canvas_height. Use the ORIGINAL pose canvas size.'}),
            'confidence': ('FLOAT', {'default':.2,'min':.05,'max':1.,'step':.05,
                'tooltip':'Skip missing or low-confidence joints. Missing segments are not invented.'}),
            'pose_image': (pose_files(), {'default':NO_POSE_IMAGE,
                'tooltip':'Load a colored OpenPose/DWPose PNG on black/transparent background. People are numbered left to right by neck. Overrides JSON; connected image/keypoints take priority.'}),
            'image': ('IMAGE', {'tooltip':'Optional skeleton image from Load Image or a pose preprocessor. One frame; overrides the selected file and JSON.'}),
        }, 'hidden': {'unique_id':'UNIQUE_ID'}}

    RETURN_TYPES = (BUILD_PIPE_TYPE, 'IMAGE', 'MASK', 'STRING')
    RETURN_NAMES = ('building_pipe','pose_preview','person_masks','pose_info')
    # Replay the UI payload when downstream generation is already cached.
    # Otherwise a reloaded graph never receives this intermediate preview.
    HAS_INTERMEDIATE_OUTPUT = True
    FUNCTION = 'apply'
    CATEGORY = 'RS MultiCharacter/Characters'
    DESCRIPTION = 'Load a colored OpenPose/DWPose PNG to create numbered person masks. Adjust thickness, then move/resize in Position. PNG people are numbered left to right by neck position. Optional JSON/keypoints remain supported. Check the masks: hidden joints and ambiguous overlaps cannot be recovered reliably. Rough composition guide; body-part name guidance is very weak, experimental and OFF by default. No ControlNet weights required. Canvas overflow is clipped.'

    @classmethod
    def IS_CHANGED(cls,pose_image=NO_POSE_IMAGE,image=None,pose_keypoints=None,**kwargs):
        if image is None and pose_keypoints is None and pose_image not in (NO_POSE_IMAGE,'',None):
            return hashlib.sha256(read_pose_image(pose_image).tobytes()).hexdigest()
        return ''

    def apply(self, pose_json, thickness=1., body_part_strength=0., building_pipe=None, pose_keypoints=None,
              canvas_width=512, canvas_height=768, confidence=.2, unique_id=None, pose_image=NO_POSE_IMAGE, image=None):
        import math
        if (isinstance(body_part_strength,bool) or not isinstance(body_part_strength,(int,float)) or
                not math.isfinite(body_part_strength) or not 0 <= body_part_strength <= .8):
            raise ValueError('Body-part strength must be 0–0.8.')
        if building_pipe is not None and not isinstance(building_pipe,BuildPipe):
            raise ValueError('Connect an RS building pipe.')
        data,notes,source_kind=resolve_pose(pose_json,pose_keypoints,image,pose_image,canvas_width,canvas_height)
        parts, masks, skipped=compile_semantic_parts(data,len(data['people']),confidence,thickness)
        pipe=building_pipe or BuildPipe()
        # Reapplying a smaller pose clears old pose-owned masks above its count.
        for slot in pipe.slots:
            if slot.number > len(masks) and slot.body_parts:
                pipe=update_slot(pipe,slot.number,region_mask=None,body_parts=(),body_part_strength=0.)
        for i, mask in enumerate(masks):
            pieces=tuple((p['name'],prepare_mask(p['mask'],margin=0)) for p in parts if p['owner']==i)
            pipe=update_slot(pipe,i+1,region_mask=mask,body_parts=pieces,body_part_strength=body_part_strength)
        info={'people':len(masks),'body_part_strength':body_part_strength,'skipped':skipped,
              'person_order':'neck left to right' if source_kind in ('png','connected_image') else 'OpenPose people array = character row number','controlnet_used':False,
              'source_kind':source_kind,'notes':notes,
              'source':data,'thickness':thickness,'confidence':confidence}
        preview=preview_image(data,masks,parts,confidence)
        images=[]
        if unique_id is not None:
            import folder_paths
            directory=Path(folder_paths.get_temp_directory())/'RS_PoseMasks';directory.mkdir(parents=True,exist_ok=True)
            name=hashlib.sha256(preview.tobytes()).hexdigest()+'.png';preview.save(directory/name)
            images=[{'filename':name,'subfolder':'RS_PoseMasks','type':'temp'}]
        payload=raster_payload(data,masks)
        payload.update(notes=notes,source_kind=source_kind)
        return {'ui':{'images':images,'text':[json.dumps(info,ensure_ascii=False)],
                      'pose_masks':[payload]},
                'result':(pipe,torch.from_numpy(np.asarray(preview).copy().astype(np.float32)/255)[None],
                          torch.stack([m.tensor() for m in masks]),json.dumps(info,ensure_ascii=False))}


def preview_payload(pose_json, thickness=1., confidence=.2, width=512, height=768, pose_image=NO_POSE_IMAGE):
    data,notes,source_kind=resolve_pose(pose_json,pose_image=pose_image,width=width,height=height)
    from .pose_parts import compile_pose
    _,masks,_=compile_pose(data,len(data['people']),confidence,thickness)
    result=raster_payload(data,masks)
    result.update(notes=notes,source_kind=source_kind)
    return result


def raster_payload(data,masks):
    """Reuse executed masks for linked-input previews; never rerun pose nodes."""
    from torch.nn.functional import interpolate
    rasters=[]
    for mask in masks:
        factor=min(1,128/max(mask.width,mask.height))
        w,h=max(1,round(mask.width*factor)),max(1,round(mask.height*factor))
        raster=(interpolate(mask.tensor()[None,None],(h,w),mode='area')[0,0]>.25).to(torch.uint8)
        rasters.append(dict(width=w,height=h,data=raster.flatten().tolist(),center=mask.center))
    return dict(masks=rasters,canvas_width=data['canvas_width'],canvas_height=data['canvas_height'])


def register_preview_route():
    # Importing node schemas outside a running Comfy server remains supported.
    try:
        from server import PromptServer
        from aiohttp import web
        instance=PromptServer.instance
    except (ImportError,AttributeError):
        return
    @instance.routes.post('/rs_mc/pose_masks/preview')
    async def preview(request):
        try:
            if request.content_length and request.content_length > 2*1024*1024:
                raise ValueError('OpenPose JSON is too large.')
            import asyncio
            args=await request.json()
            if not isinstance(args,dict): raise ValueError('Expected pose JSON settings.')
            result=await asyncio.to_thread(preview_payload,args.get('pose_json',''),args.get('thickness',1.),
                args.get('confidence',.2),args.get('canvas_width',512),args.get('canvas_height',768),args.get('pose_image',NO_POSE_IMAGE))
            return web.json_response(result)
        except (ValueError,TypeError) as error:
            return web.json_response({'error':str(error)},status=400)


register_preview_route()
