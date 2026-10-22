# SPDX-License-Identifier: GPL-3.0-only
"""Experimental OpenPose coordinates -> owner-bound body-part prompt regions.

No pose detector, ControlNet, image inversion, or trained pose adapter is used.
Only pixel-space COCO_18 and BODY_25 JSON are accepted; RGB decoding is absent.
"""
from dataclasses import replace
import json
import math

import numpy as np
from PIL import Image, ImageDraw
import torch
import torch.nn.functional as F

from .characters import PIPE_TYPE
from .region_mask import prepare_mask
from .routing import route_cross, sdpa


def compile_pose(data, count, confidence=.2, thickness=1.):
    if (isinstance(confidence, bool) or not isinstance(confidence, (int,float)) or not math.isfinite(confidence) or not .05 <= confidence <= 1 or
        isinstance(thickness, bool) or not isinstance(thickness, (int,float)) or not math.isfinite(thickness) or not .25 <= thickness <= 3):
        raise ValueError('Confidence must be 0.05–1 and thickness 0.25–3. / 신뢰도·굵기 범위를 확인해 주세요.')
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict) or data.get('coordinate_space') != 'pixels':
        raise ValueError('포즈 좌표 단위를 pixels로 지정해 주세요. 정규화 좌표는 먼저 픽셀로 변환해 주세요.')
    w, h = data.get('canvas_width'), data.get('canvas_height')
    if any(type(v) is not int or not 64 <= v <= 2048 for v in (w, h)):
        raise ValueError('시험본 포즈 캔버스는 64~2048픽셀이어야 합니다.')
    layout = data.get('pose_model')
    if layout not in ('COCO_18', 'BODY_25'):
        raise ValueError('관절 순서를 COCO_18 또는 BODY_25로 지정해 주세요.')
    n = 18 if layout == 'COCO_18' else 25
    people = data.get('people')
    if not isinstance(people, list) or len(people) != count or not 1 <= count <= 10:
        raise ValueError('포즈 인원수와 캐릭터 수를 맞춰 주세요. 배열 순서가 캐릭터 번호입니다.')
    parts, whole, skipped = [], [], []
    for owner, person in enumerate(people):
        flat = person.get('pose_keypoints_2d') if isinstance(person, dict) else None
        if not isinstance(flat, list) or len(flat) != n*3:
            raise ValueError(f'{owner+1}번 사람의 관절 개수가 {layout}과 다릅니다.')
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in flat):
            raise ValueError('포즈 좌표와 신뢰도에는 유한한 숫자를 입력해 주세요.')
        points = np.asarray(flat, dtype=np.float64).reshape(n, 3)
        if ((points[:, 2] < 0) | (points[:, 2] > 1)).any() or (np.abs(points[:, :2]) > 8*max(w,h)).any():
            raise ValueError('포즈 좌표 범위나 신뢰도를 확인해 주세요.')
        # Anatomical left/right, never the viewer's left/right. Missing points
        # skip a whole part rather than connecting a known joint to (0,0).
        hips = (8, 11) if n == 18 else (9, 12)
        limbs = {'right arm': (2,3,4), 'left arm': (5,6,7),
                 'right leg': (8,9,10) if n == 18 else (9,10,11),
                 'left leg': (11,12,13) if n == 18 else (12,13,14)}
        valid = points[:, 2] >= confidence
        def present(ids): return all(valid[i] for i in ids)
        shoulder_width = float(np.linalg.norm(points[2,:2]-points[5,:2])) if present((2,5)) else min(w,h)*.14
        radius = max(8, min(min(w,h)*.065, shoulder_width*.22)) * thickness
        specs = [('head', (0,1)), ('torso', (2,5,*hips)), *limbs.items()]
        union = np.zeros((h,w), dtype=bool)
        for name, ids in specs:
            if not present(ids):
                skipped.append({'owner':owner, 'part':name, 'reason':'missing_or_low_confidence_joint'})
                continue
            image = Image.new('L',(w,h)); draw = ImageDraw.Draw(image)
            xy = [tuple(points[i,:2]) for i in ids]
            if name == 'head':
                # Nose-centred approximate head, scaled from shoulder span.
                cx,cy=xy[0]; rx=max(radius*1.6,shoulder_width*.38); ry=rx*1.15
                draw.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=255)
                draw.line(xy,fill=255,width=round(radius*1.8))
            elif name == 'torso':
                draw.polygon([xy[0],xy[1],xy[3],xy[2]],fill=255)
                draw.line([xy[0],xy[1],xy[3],xy[2],xy[0]],fill=255,width=round(radius))
            else:
                r=radius*(1.25 if 'leg' in name else 1.)
                draw.line(xy,fill=255,width=round(2*r),joint='curve')
                for cx,cy in xy:draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=255)
            mask=np.asarray(image)>0
            if not mask.any():
                skipped.append({'owner':owner,'part':name,'reason':'outside_canvas'})
                continue
            union |= mask
            parts.append({'owner':owner,'name':name,'mask':torch.from_numpy(mask.astype(np.float32)),
                          'joint_indices':list(ids)})
        if not union.any():
            raise ValueError(f'{owner+1}번 사람의 유효한 부위가 없습니다. 관절과 캔버스를 확인해 주세요.')
        whole.append(prepare_mask(torch.from_numpy(union.astype(np.float32)),margin=16))
    return parts, whole, skipped



def compile_semantic_parts(data, count, confidence=.2, thickness=1.):
    """Keep original person masks; derive six shared, localized body labels.

    COCO_18 has no toes: ankle regions are approximate feet, never recovered
    finger/foot keypoints. Missing segments are omitted rather than invented.
    """
    if isinstance(data, str): data=json.loads(data)
    original,whole,skipped=compile_pose(data,count,confidence,thickness)
    w,h=data['canvas_width'],data['canvas_height'];n=18 if data['pose_model']=='COCO_18' else 25
    parts=[]
    for owner,person in enumerate(data['people']):
        pts=np.asarray(person['pose_keypoints_2d'],dtype=np.float64).reshape(n,3)
        valid=pts[:,2]>=confidence
        def present(ids):return all(valid[i] for i in ids)
        sw=float(np.linalg.norm(pts[2,:2]-pts[5,:2])) if present((2,5)) else min(w,h)*.14
        radius=max(8,min(min(w,h)*.065,sw*.22))*thickness
        limbs=[(8,9,10),(11,12,13)] if n==18 else [(9,10,11),(12,13,14)]
        for name in ('head','hands','chest','thighs','legs','feet'):
            image=Image.new('L',(w,h));draw=ImageDraw.Draw(image);used=set();approx=False
            def disk(i,r):
                cx,cy=pts[i,:2];draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=255);used.add(i)
            def segment(ids,r):
                draw.line([tuple(pts[i,:2]) for i in ids],fill=255,width=max(1,round(2*r)),joint='curve')
                for i in ids:disk(i,r)
            if name=='head':
                for part in original:
                    if part['owner']==owner and part['name']=='head':
                        image=Image.fromarray((part['mask'].numpy()*255).astype(np.uint8));used.update(part['joint_indices'])
            elif name=='hands':
                for elbow,wrist in ((3,4),(6,7)):
                    if present((elbow,wrist)):disk(wrist,radius*.8)
            elif name=='chest':
                hips=(8,11) if n==18 else (9,12)
                if present((2,5,*hips)):
                    shoulder=pts[[2,5],:2];waist=shoulder*.45+pts[list(hips),:2]*.55
                    draw.polygon([tuple(shoulder[0]),tuple(shoulder[1]),tuple(waist[1]),tuple(waist[0])],fill=255)
                    used.update((2,5,*hips))
            elif name in ('thighs','legs'):
                for hip,knee,ankle in limbs:
                    ids=(hip,knee) if name=='thighs' else (knee,ankle)
                    if present(ids):segment(ids,radius*(1.25 if name=='thighs' else 1.))
            elif name=='feet':
                for side,(_,_,ankle) in enumerate(limbs):
                    toes=(22,23,24) if side==0 else (19,20,21)
                    available=[i for i in toes if n==25 and valid[i]]
                    if valid[ankle] and available:segment((ankle,*available),radius*.55)
                    elif valid[ankle]:disk(ankle,radius*.75);approx=True
            mask=np.asarray(image)>0
            if not mask.any():
                skipped.append({'owner':owner,'part':name,'reason':'semantic_part_has_no_valid_support'});continue
            parts.append({'owner':owner,'name':name,'mask':torch.from_numpy(mask.astype(np.float32)),
                          'joint_indices':sorted(used),'approximate':approx})
    return parts,whole,skipped


def part_cells(groups, parts, height, width, device):
    """Within each owner cell, select only that owner's supported parts."""
    # Metadata restored from different source resolutions is resized per mask.
    masks=[p['mask'] for p in parts]
    support=torch.stack([F.interpolate(m[None,None],(height,width),mode='area')[0,0].flatten()>.25 for m in masks])
    result=[]
    for owners,indices in groups.cells:
        relevant=[i for i,p in enumerate(parts) if p['owner'] in owners]
        cpu_indices=indices.cpu()
        if not relevant:
            result.append((owners,(),indices));continue
        local=support[relevant][:,cpu_indices]
        codes=(local.long()*(2**torch.arange(len(relevant)))[:,None]).sum(0)
        for code in codes.unique().tolist():
            chosen=tuple(relevant[j] for j in range(len(relevant)) if code&(1<<j))
            result.append((owners,chosen,cpu_indices[(codes==code)].to(device)))
    return result


def route_parts(q,k,v,groups,lengths,kinds,cells,owner_count,strength,weights,gain,bank_ids=None):
    """Reserve a bounded part prior without increasing total character prior.

    No pose labels enter the unconditional branch. At zero strength execute the
    original route exactly. Self-attention still uses the whole-person masks.
    """
    if (len(kinds)!=q.shape[0] or k.shape!=v.shape or sum(lengths)!=k.shape[1]
            or any(n<=0 for n in lengths) or weights is None
            or not 0 <= strength <= .8 or not math.isfinite(strength)):
        raise ValueError('Invalid part route inputs')
    if strength == 0:
        end=sum(lengths[:owner_count+1])
        return route_cross(q,k[:,:end],v[:,:end],groups,lengths[:owner_count+1],kinds,weights=weights,character_gain=gain)
    if len(lengths) <= owner_count+1:
        raise ValueError('부위 조건 토큰 길이가 일치하지 않습니다.')
    if bank_ids is None:
        bank_ids=list(range(len(lengths)-owner_count-1))
    if any(type(i) is not int or not 0 <= i < len(lengths)-owner_count-1 for i in bank_ids):
        raise ValueError('Invalid shared body-part bank index')
    offsets=[0]
    for length in lengths:offsets.append(offsets[-1]+length)
    result=q.new_empty(q.shape[:2]+(q.shape[2]*q.shape[3],))
    for b,kind in enumerate(kinds):
        qb,kb,vb=q[b:b+1],k[b:b+1],v[b:b+1]
        if kind == 1:
            result[b:b+1]=sdpa(qb,kb[:,:lengths[0]],vb[:,:lengths[0]])
            continue
        if kind != 0:raise ValueError('Unsupported CFG kind')
        for owners,parts,indices in cells:
            if not owners:
                result[b:b+1,indices]=sdpa(qb[:,indices],kb[:,:lengths[0]],vb[:,:lengths[0]])
                continue
            entries=[(0,weights[0],1.)]
            fraction=strength if parts else 0.
            for owner in owners:
                entries.append((owner+1,weights[1]*(1-fraction)/len(owners),gain))
            if parts:
                for part in parts:
                    entries.append((owner_count+1+bank_ids[part],weights[1]*fraction/len(parts),gain))
            combined={}
            for bank,prior,vgain in entries:
                old=combined.get(bank,(0.,vgain))
                combined[bank]=(old[0]+prior,vgain)
            entries=[(bank,prior,vgain) for bank,(prior,vgain) in combined.items()]
            keys,values,bias=[],[],[]
            for bank,prior,vgain in entries:
                start,stop=offsets[bank:bank+2]
                keys.append(kb[:,start:stop]);values.append(vb[:,start:stop]*vgain)
                bias.append(q.new_full((stop-start,),math.log(prior/(stop-start)) if prior else -torch.inf))
            result[b:b+1,indices]=sdpa(qb[:,indices],torch.cat(keys,1),torch.cat(values,1),torch.cat(bias)[None,:])
    return result
