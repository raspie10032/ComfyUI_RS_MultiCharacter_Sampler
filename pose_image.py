# SPDX-License-Identifier: GPL-3.0-only
"""Read standard COCO-18 OpenPose/DWPose *rendered maps*, without weights.

Colors describe joints and links, not person IDs. Follow colored links when
assigning joints so a hand near another person's torso stays with its arm.
Pixel recovery cannot restore occluded joints or original detector confidence.
"""
from collections import deque

import numpy as np
from PIL import Image, ImageFilter


COLORS = np.array([
    (255,0,0), (255,85,0), (255,170,0), (255,255,0), (170,255,0),
    (85,255,0), (0,255,0), (0,255,85), (0,255,170), (0,255,255),
    (0,170,255), (0,85,255), (0,0,255), (85,0,255), (170,0,255),
    (255,0,255), (255,0,170), (255,0,85)], dtype=np.float32)
LINKS = ((1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),
         (9,10),(1,11),(11,12),(12,13),(1,0),(0,14),(14,16),(0,15),(15,17))


def components(mask):
    """8-connected regions, with a correct NumPy-only fallback."""
    try:
        import cv2
    except ImportError:
        cv2 = None
    if cv2 is not None:
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        for i in range(1, count):
            if stats[i, 4] < 3:
                continue
            x,y,w,h = stats[i,:4]
            yy,xx = np.where(labels[y:y+h,x:x+w] == i)
            yield np.column_stack((xx+x,yy+y)).astype(np.float32)
        return
    h,w = mask.shape
    remaining = set(np.flatnonzero(mask).tolist())
    while remaining:
        first = remaining.pop()
        queue, group = deque([first]), []
        while queue:
            index = queue.popleft(); y,x = divmod(index,w); group.append((x,y))
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    nx,ny = x+dx,y+dy
                    candidate = ny*w+nx
                    if 0 <= nx < w and 0 <= ny < h and candidate in remaining:
                        remaining.remove(candidate); queue.append(candidate)
        if len(group) >= 3:
            yield np.asarray(group,dtype=np.float32)


def _candidates(mask, max_span):
    result = []
    for pixels in components(mask):
        center = pixels.mean(0)
        covariance = (pixels-center).T @ (pixels-center) / len(pixels)
        values,vectors = np.linalg.eigh(covariance)
        span = np.ptp(pixels,axis=0)
        if max(span) <= max_span and values[1] <= 5*max(values[0],.5):
            result.append((*center,1.))
        elif values[1] > 5*max(values[0],.5):
            # Opaque editor limbs can touch a same-colored dot. Keep endpoints
            # as alternatives; skeleton connectivity selects the proper end.
            projection = (pixels-center) @ vectors[:,1]
            for q in (.04,.96):
                point = center + np.quantile(projection,q)*vectors[:,1]
                result.append((*point,.45))
    return result


def decode_pose_image(rgb):
    """Return pixel-coordinate COCO-18 plus recovery notes. Never guess a body."""
    rgb = np.asarray(rgb)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError('Connect one RGB pose image. / 컬러 뼈대 이미지 한 장을 넣어 주세요.')
    h,w = rgb.shape[:2]
    if not 64 <= min(w,h) or max(w,h) > 2048:
        raise ValueError('Pose PNG must be 64–2048 pixels per side. / 뼈대 PNG의 각 변을 64~2048픽셀로 맞춰 주세요.')
    pixels = rgb.astype(np.float32)
    brightness = pixels.max(2)
    saturation = (brightness-pixels.min(2))/np.maximum(brightness,1)
    if np.mean(brightness < 65) < .55:
        raise ValueError('Use a colored OpenPose map on a black/transparent background, not a photograph. / 사진이 아닌 검정·투명 배경의 컬러 OpenPose 뼈대 PNG를 넣어 주세요.')
    normalized = pixels/np.maximum(brightness[:,:,None],1)
    labels = np.full((h,w),-1,dtype=np.int8)
    best = np.full((h,w),np.inf,dtype=np.float32)
    for i,color in enumerate(COLORS/255):
        error = np.max(np.abs(normalized-color),axis=2)
        select = (error < best) & (error < .135) & (saturation > .7) & (brightness > 55)
        labels[select] = i; best[select] = error[select]
    radius = max(2,min(6,round(min(w,h)/220)))
    maps = [np.asarray(Image.fromarray(((labels == i)*255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(radius*2+1))) > 0 for i in range(18)]
    candidates = [_candidates((labels == i) & (brightness >= 190),min(w,h)*.09) for i in range(18)]
    # Older ControlNet drawers paint dots *before* blending the sticks, so a
    # joint can lose its bright color. Recover alternatives at limb endpoints
    # instead of silently dropping the whole person for that render style.
    def add_candidate(joint,point):
        if all(np.linalg.norm(np.asarray(point[:2])-other[:2]) > radius*2 for other in candidates[joint]):
            candidates[joint].append((*point[:2],.25))
    for edge,(parent,child) in enumerate(LINKS):
        for point in _candidates(labels==edge,min(w,h)*.09):
            if point[2] >= .5:
                continue  # A joint dot alone is not evidence for a limb.
            add_candidate(child,point)
            if parent in (0,1):add_candidate(parent,point)

    def coverage(start,end,edge):
        a,b = np.asarray(start[:2]),np.asarray(end[:2])
        distance = np.linalg.norm(a-b)
        if distance < radius*2 or distance > max(w,h)*.9:
            return 0.
        x,y=np.rint(a).astype(int);reach=radius*3
        if not maps[edge][max(0,y-reach):min(h,y+reach+1),max(0,x-reach):min(w,x+reach+1)].any():
            return 0.
        t = np.linspace(.12,.88,48)[:,None]
        samples = np.rint(a+(b-a)*t).astype(int)
        return float(maps[edge][samples[:,1].clip(0,h-1),samples[:,0].clip(0,w-1)].mean())

    roots = []
    for point in candidates[1]:
        scores = [max((coverage(point,other,e) for other in candidates[child]),default=0.)
                  for e,child in ((0,2),(1,5),(6,8),(9,11),(12,0))]
        def lengths(edge,child):
            return [np.linalg.norm(np.array(point[:2])-other[:2]) for other in candidates[child]
                    if coverage(point,other,edge)>=.6]
        torso=max(lengths(6,8)+lengths(9,11),default=0)>min(w,h)*.055
        shoulders=sum(max(lengths(e,c),default=0) for e,c in ((0,2),(1,5)))>min(w,h)*.09
        # Three independently colored torso/head connections distinguish a
        # neck from orange elbow sticks and most rainbow finger clutter.
        if sum(s >= .6 for s in scores) >= 3 and (torso or shoulders):
            roots.append((sum(scores)+point[2],point))
    selected = []
    for score,point in sorted(roots,key=lambda item:-item[0]):
        if all(np.linalg.norm(np.array(point[:2])-np.array(p[:2])) > max(radius*5,min(w,h)*.055) for p in selected):
            selected.append(point)
    selected.sort(key=lambda p:(p[0],p[1]))
    if not selected:
        raise ValueError('No readable COCO-18 body found. Use an original colored OpenPose/DWPose PNG with visible neck/shoulders, without labels or recoloring. / 뼈대를 읽지 못했습니다. 목·어깨가 보이는 원본 컬러 OpenPose PNG를 넣어 주세요. 흑백·색상 변경·가려진 관절은 복원할 수 없습니다.')
    if len(selected) > 10:
        raise ValueError('At most 10 people are supported. / 뼈대 인물은 최대 10명까지 지원합니다.')
    people = [np.zeros((18,3),dtype=np.float64) for _ in selected]
    for person,root in zip(people,selected):
        person[1] = (*root[:2],.9)
    # Parents precede children. Joint identity is anatomical, not screen left.
    order = (0,1,6,9,12,2,4,7,10,3,5,8,11,13,15,14,16)
    uncertain = []
    for edge in order:
        parent,child = LINKS[edge]
        proposals = []
        for owner,person in enumerate(people):
            if not person[parent,2]:
                continue
            ranked = []
            for j,point in enumerate(candidates[child]):
                match = coverage(person[parent],point,edge)
                if match >= .55:
                    score = match + point[2]*.12 - np.linalg.norm(person[parent,:2]-point[:2])/max(w,h)*.02
                    ranked.append((score,j,point))
            ranked.sort(reverse=True,key=lambda p:p[0])
            if len(ranked)>1 and ranked[0][0]-ranked[1][0] < .035:
                uncertain.append({'person':owner+1,'joint':child})
            proposals.extend((score,owner,j,point) for score,j,point in ranked)
        used_people,used_points = set(),set()
        for _,owner,j,point in sorted(proposals,reverse=True,key=lambda p:p[0]):
            if owner in used_people or j in used_points:
                continue
            people[owner][child] = (*point[:2],.9)
            used_people.add(owner); used_points.add(j)
    # Recheck the *assigned* body. A fan of colored finger sticks can offer
    # distant alternatives at root discovery, but its selected joints collapse
    # around the wrist instead of forming shoulders or a torso.
    def has_body(person):
        shoulders=person[2,2] and person[5,2] and np.linalg.norm(person[2,:2]-person[5,:2])>min(w,h)*.04
        torso=any(person[i,2] and np.linalg.norm(person[1,:2]-person[i,:2])>min(w,h)*.055 for i in (8,11))
        return shoulders or torso
    people=[person for person in people if has_body(person)]
    if not people:
        raise ValueError('No readable body beyond hand/face details. Use an original full-body or upper-body pose PNG. / 손·얼굴 외에 읽을 수 있는 몸통이 없습니다. 상반신이나 전신 뼈대 PNG를 넣어 주세요.')
    notes = ['PNG: approximate pixel recovery; people are numbered by neck position, left to right. Missing/occluded joints are omitted. / PNG는 픽셀에서 근사 복원하며 목 위치의 왼쪽부터 번호를 붙입니다. 가려진 관절은 생략합니다.']
    if uncertain:
        notes.append('Overlapping joints have ambiguous ownership; check the numbered masks. / 겹친 관절의 소속이 불확실합니다. 번호별 마스크를 확인해 주세요.')
    for i,person in enumerate(people):
        if np.count_nonzero(person[:,2]) < 5:
            raise ValueError(f'Person {i+1} has too few readable joints. / {i+1}번 뼈대의 관절이 너무 많이 가려져 있습니다. 원본 PNG나 분리된 포즈 이미지를 사용해 주세요.')
    return dict(coordinate_space='pixels',pose_model='COCO_18',canvas_width=w,canvas_height=h,
                people=[{'pose_keypoints_2d':p.flatten().tolist()} for p in people]),notes
