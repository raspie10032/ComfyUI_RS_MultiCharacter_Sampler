# SPDX-License-Identifier: GPL-3.0-only
"""Procedural articulated mannequins to camera-projected character masks.

Scene geometry mirrors web/pose3d/model.mjs; no inference or ControlNet weights.
"""
import json
import math

import numpy as np

JOINTS = {
    'pelvis': (None, (0, .94, 0)),
    'chest': ('pelvis', (0, .36, 0)),
    'neck': ('chest', (0, .20, 0)),
    'head': ('neck', (0, .16, 0)),
    'right_shoulder': ('chest', (-.23, .04, 0)),
    'right_elbow': ('right_shoulder', (0, -.29, 0)),
    'right_wrist': ('right_elbow', (0, -.26, 0)),
    'left_shoulder': ('chest', (.23, .04, 0)),
    'left_elbow': ('left_shoulder', (0, -.29, 0)),
    'left_wrist': ('left_elbow', (0, -.26, 0)),
    'right_hip': ('pelvis', (-.115, -.035, 0)),
    'right_knee': ('right_hip', (0, -.42, 0)),
    'right_ankle': ('right_knee', (0, -.40, 0)),
    'left_hip': ('pelvis', (.115, -.035, 0)),
    'left_knee': ('left_hip', (0, -.42, 0)),
    'left_ankle': ('left_knee', (0, -.40, 0)),
}
LIMBS = [('right_shoulder', 'right_elbow', .075), ('right_elbow', 'right_wrist', .06),
         ('left_shoulder', 'left_elbow', .075), ('left_elbow', 'left_wrist', .06),
         ('right_hip', 'right_knee', .10), ('right_knee', 'right_ankle', .075),
         ('left_hip', 'left_knee', .10), ('left_knee', 'left_ankle', .075)]


def default_scene():
    return dict(version=1, width=768, height=1024, mask_mode='full',
                camera=dict(position=[0, 1.15, 4.1], target=[0, .9, 0], fov=38),
                people=[dict(id=i+1, position=[x, 0, 0], rotation=[0, 0, 0],
                             scale=1., bulk=1., joints={}) for i, x in enumerate([-.4, .4])])


def number(value, low, high, label):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label}: use a finite number from {low} to {high}. / 수치 범위를 확인해 주세요.')
    return float(value)


def vector(value, low, high, label):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f'{label}: expected three XYZ values.')
    return [number(v, low, high, label) for v in value]


def read_scene(raw):
    if isinstance(raw, str):
        if len(raw) > 100_000:
            raise ValueError('3D scene exceeds 100 KB. / 3D 장면 데이터가 너무 큽니다.')
        try:
            raw = json.loads(raw)
        except (ValueError, RecursionError) as error:
            raise ValueError('Cannot read 3D scene. Reopen the editor and apply. / 3D 편집기를 열어 다시 적용해 주세요.') from error
    if not isinstance(raw, dict) or type(raw.get('version')) is not int or raw['version'] not in (1, 2):
        raise ValueError('Unsupported 3D scene version. / 지원하지 않는 3D 장면 버전입니다.')
    for key in ('width', 'height'):
        if type(raw.get(key)) is not int or not 64 <= raw[key] <= 2048:
            raise ValueError('3D mask canvas must be 64–2048 pixels per side. / 각 변을 64~2048픽셀로 설정해 주세요.')
    if raw.get('mask_mode') not in ('full', 'visible'):
        raise ValueError('Choose full or visible silhouettes.')
    people, camera = raw.get('people'), raw.get('camera')
    if not isinstance(people, list) or not 1 <= len(people) <= 10 or not isinstance(camera, dict):
        raise ValueError('Use 1–10 mannequins and one camera. / 마네킹 1~10명과 카메라를 설정해 주세요.')
    camera = dict(position=vector(camera.get('position'), -30, 30, 'Camera position'),
                  target=vector(camera.get('target'), -10, 10, 'Camera target'),
                  fov=number(camera.get('fov'), 15, 90, 'Field of view'))
    direction = np.subtract(camera['position'], camera['target'])
    if np.linalg.norm(direction) < .5 or np.linalg.norm(np.cross(direction, [0, 1, 0])) < 1e-4:
        raise ValueError('Camera needs a distinct target and a nonvertical view. / 카메라를 대상에서 떨어뜨리고 수직 시점을 살짝 기울여 주세요.')
    joint_names = JOINTS
    if raw['version'] == 2:
        from .mhr import asset
        joint_names = asset()['controls']
        if type(raw.get('outline', True)) is not bool:
            raise ValueError('Outline must be true or false.')
    clean, ids = [], set()
    for p in people:
        if not isinstance(p, dict) or type(p.get('id')) is not int or not 1 <= p['id'] <= 10 or p['id'] in ids:
            raise ValueError('Each mannequin needs a unique character number 1–10. / 캐릭터 번호가 중복되거나 범위를 벗어났습니다.')
        ids.add(p['id'])
        rotations = p.get('joints', {})
        if not isinstance(rotations, dict) or not rotations.keys() <= joint_names.keys():
            raise ValueError('Unknown 3D joint name.')
        clean.append(dict(id=p['id'], position=vector(p.get('position'), -10, 10, 'Body position'),
                          rotation=vector(p.get('rotation'), -180, 180, 'Body rotation'),
                          scale=number(p.get('scale'), .4, 1.8, 'Body height'),
                          bulk=number(p.get('bulk'), .5, 1.8, 'Body width'),
                          joints={k: vector(v, -180, 180, k) for k, v in rotations.items()}))
        if 'source_frame' in p:
            planes = p['source_frame']
            if raw['version'] != 2 or not isinstance(planes, list) or len(planes) != 5:
                raise ValueError('Source image frame needs five clipping planes in an MHR scene.')
            clean[-1]['source_frame'] = []
            for plane in planes:
                if not isinstance(plane, list) or len(plane) != 4:
                    raise ValueError('Invalid source image clipping plane.')
                value = [number(v, -1000, 1000, 'Source frame') for v in plane]
                if not .99 <= np.linalg.norm(value[:3]) <= 1.01:
                    raise ValueError('Source image clipping planes must have unit normals.')
                clean[-1]['source_frame'].append(value)
    result = dict(version=raw['version'], width=raw['width'], height=raw['height'], mask_mode=raw['mask_mode'],
                  camera=camera, people=sorted(clean, key=lambda p: p['id']))
    if raw['version'] == 2:
        result['outline'] = raw.get('outline', True)
    return result


def rotation(angles):
    x, y, z = np.radians(angles)
    a, b, c, d, e, f = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    return np.array([[c*e, -c*f, d], [a*f+b*d*e, a*e-b*d*f, -b*c], [b*f-a*d*e, b*e+a*d*f, a*c]])


def skeleton(person):
    frames, points = {}, {}
    root_r = rotation(person['rotation'])
    for name, (parent, offset) in JOINTS.items():
        r = root_r if parent is None else frames[parent]
        base = np.array(person['position']) if parent is None else points[parent]
        points[name] = base + r @ (np.array(offset)*person['scale'])
        frames[name] = r @ rotation(person['joints'].get(name, [0, 0, 0]))
    return points, frames


def unit_sphere():
    vertices = np.array([[math.sin(math.pi*y/8)*math.cos(2*math.pi*x/12),
                          math.cos(math.pi*y/8), math.sin(math.pi*y/8)*math.sin(2*math.pi*x/12)]
                         for y in range(9) for x in range(13)])
    faces = []
    for y in range(8):
        for x in range(12):
            a = y*13+x
            faces.extend([(a, a+13, a+1), (a+1, a+13, a+14)])
    return vertices, np.array(faces)


SPHERE, FACES = unit_sphere()


def mannequin(person):
    points, frames = skeleton(person)
    meshes = []
    size, bulk = person['scale'], person['bulk']

    def ellipsoid(center, radius, r):
        meshes.append((SPHERE * (np.array(radius)*size)) @ r.T + center)

    ellipsoid(points['pelvis'], [.22*bulk, .15, .14*bulk], frames['pelvis'])
    center = (points['pelvis']+points['neck'])/2
    ellipsoid(center, [.25*bulk, .31, .14*bulk], frames['chest'])
    ellipsoid(points['neck'], [.065, .10, .065], frames['neck'])
    ellipsoid(points['head']+frames['head']@np.array([0, .025*size, .025*size]), [.125, .175, .13], frames['head'])
    for a, b, radius in LIMBS:
        center = (points[a]+points[b])/2
        ellipsoid(center, [radius*bulk, np.linalg.norm(points[b]-points[a])/size/2+radius*.45, radius*bulk], frames[a])
    for side in ('right', 'left'):
        wrist, ankle = side+'_wrist', side+'_ankle'
        ellipsoid(points[wrist]+frames[wrist]@np.array([0, -.065*size, 0]), [.055*bulk, .09, .035], frames[wrist])
        ellipsoid(points[ankle]+frames[ankle]@np.array([0, -.025*size, .07*size]), [.065*bulk, .06, .14], frames[ankle])
    vertices = np.concatenate(meshes)
    faces = np.concatenate([FACES+i*len(SPHERE) for i in range(len(meshes))])
    return vertices, faces, points


def camera_coordinates(vertices, camera):
    pos, target = np.array(camera['position']), np.array(camera['target'])
    forward = target-pos
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    return (vertices-pos) @ np.array([right, up, forward]).T


def project(vertices, camera, width, height):
    v = camera_coordinates(vertices, camera)
    f = height/(2*math.tan(math.radians(camera['fov'])/2))
    z = np.where(np.abs(v[:, 2]) < 1e-10, 1e-10, v[:, 2])
    return np.column_stack((width/2+v[:, 0]*f/z, height/2-v[:, 1]*f/z, v[:, 2]))


def clip_near(triangle, near=.05):
    """Clip triangles crossing the camera plane before perspective division."""
    output = []
    for start, end in zip(triangle, np.roll(triangle, -1, axis=0)):
        inside_a, inside_b = start[2] >= near, end[2] >= near
        if inside_a:
            output.append(start)
        if inside_a != inside_b:
            output.append(start+(end-start)*((near-start[2])/(end[2]-start[2])))
    return [np.array([output[0], output[i], output[i+1]]) for i in range(1, len(output)-1)]


def _rasterize(scene, max_side=None, shaded=False, control_maps=False):
    """Masks and pose shading use one mesh and camera; outlines never own masks."""
    w, h = scene['width'], scene['height']
    if max_side is not None:
        scale = min(1, max_side/max(w, h))
        w, h = max(1, round(w*scale)), max(1, round(h*scale))
    full = np.zeros((len(scene['people']), h, w), dtype=bool)
    owner = np.full((h, w), -1, dtype=np.int16)
    depth = np.zeros((h, w), dtype=np.float64)
    rgb_depth = np.zeros((h, w), dtype=np.float64) if shaded else None
    rgb = np.zeros((h, w, 3), dtype=np.uint8) if shaded else None
    colors = [(255, 141, 145), (129, 188, 255), (148, 221, 157), (255, 210, 127), (195, 160, 255)]
    light = np.array([-.35, .65, -.68]); light /= np.linalg.norm(light)
    f = h/(2*math.tan(math.radians(scene['camera']['fov'])/2))
    outline = shaded and scene['version'] == 2 and scene.get('outline', True)
    for index, person in enumerate(scene['people']):
        if scene['version'] == 2:
            from .mhr import mannequin as human
            vertices, faces, _ = human(person)
        else:
            vertices, faces, _ = mannequin(person)
        view = camera_coordinates(vertices, scene['camera'])
        face_normals = np.cross(view[faces[:, 1]]-view[faces[:, 0]], view[faces[:, 2]]-view[faces[:, 0]])
        if shaded:
            normals = np.zeros_like(view)
            for corner in range(3):
                np.add.at(normals, faces[:, corner], face_normals)
            normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
            color = np.array(colors[(person['id']-1) % len(colors)])
        for hull in ([True, False] if outline else [False]):
            for fi, face in enumerate(faces):
                if hull and face_normals[fi, 2] >= 0:
                    continue
                tri = view[face]
                unclipped = (tri[:, 2] >= .05).all()
                triangles = [tri] if unclipped else clip_near(tri)
                for t in triangles:
                    z = t[:, 2]
                    xy = np.column_stack((w/2+t[:, 0]*f/z, h/2-t[:, 1]*f/z))
                    if hull:
                        ns = normals[face] if unclipped else np.tile(face_normals[fi], (3, 1))
                        # View basis reverses handedness; mesh cross normals point inward.
                        offsets = -ns[:, :2]*[1, -1]
                        offsets /= np.maximum(np.linalg.norm(offsets, axis=1, keepdims=True), 1e-12)
                        xy += offsets*(4*min(w, h)/768)
                    x, y = xy.T
                    x0, x1 = max(0, math.floor(x.min())), min(w-1, math.ceil(x.max()))
                    y0, y1 = max(0, math.floor(y.min())), min(h-1, math.ceil(y.max()))
                    den = (y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
                    if x0 > x1 or y0 > y1 or abs(den) < 1e-12:
                        continue
                    yy, xx = np.ogrid[y0:y1+1, x0:x1+1]
                    a = ((y[1]-y[2])*(xx+.5-x[2])+(x[2]-x[1])*(yy+.5-y[2]))/den
                    b = ((y[2]-y[0])*(xx+.5-x[2])+(x[0]-x[2])*(yy+.5-y[2]))/den
                    c = 1-a-b
                    inside = (a >= -1e-9) & (b >= -1e-9) & (c >= -1e-9)
                    inv_z = a/z[0]+b/z[1]+c/z[2]
                    if not hull:
                        full[index, y0:y1+1, x0:x1+1] |= inside
                        patch = depth[y0:y1+1, x0:x1+1]
                        nearer = inside & (inv_z > patch+1e-10)
                        patch[nearer] = inv_z[nearer]
                        owner[y0:y1+1, x0:x1+1][nearer] = index
                    if shaded:
                        patch = rgb_depth[y0:y1+1, x0:x1+1]
                        nearer = inside & (inv_z > patch+1e-10)
                        patch[nearer] = inv_z[nearer]
                        if hull:
                            value = np.broadcast_to(255-color, (*a.shape, 3))
                        else:
                            if unclipped:
                                ns = normals[face]
                                normal = a[..., None]*ns[0]/z[0]+b[..., None]*ns[1]/z[1]+c[..., None]*ns[2]/z[2]
                                normal /= np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-12)
                                brightness = .25+.75*np.abs(normal @ light)
                            else:
                                normal = face_normals[fi]
                                brightness = np.full(a.shape, .25+.75*abs(normal @ light)/max(np.linalg.norm(normal), 1e-12))
                            value = np.clip(brightness[..., None]*color, 0, 255).astype(np.uint8)
                        rgb[y0:y1+1, x0:x1+1][nearer] = value[nearer]
    visible = np.stack([owner == i for i in range(len(scene['people']))])
    if control_maps:
        foreground = owner >= 0
        values = depth[foreground]
        normalized = np.zeros_like(depth)
        if values.size:
            normalized[foreground] = .25 + .75*(values-values.min())/max(np.ptp(values), 1e-9)
        palette = np.array([(255,0,0), (0,0,255), (0,255,0), (255,255,0), (255,0,255),
                            (0,255,255), (255,128,0), (128,0,255), (0,128,255), (128,255,0)], dtype=np.uint8)
        color = np.zeros((h,w,3), dtype=np.uint8)
        color[foreground] = palette[owner[foreground]]
        return full, visible, color, np.repeat(np.uint8(normalized[...,None]*255), 3, axis=2)
    return full, visible, rgb


def rasterize(scene, max_side=None):
    """Full masks ignore other people. Visible masks share a depth buffer."""
    full, visible, _ = _rasterize(scene, max_side)
    return full, visible


def render_pose_condition(scene, max_side=None):
    """Shaded RGB bodies on black for a separately trained pose adapter.

    Excludes editor grids, selection handles and joint gizmos. The scene's
    camera, framing and depth are identical to the mask projection. Colors
    distinguish people; they are not learned semantic character IDs.
    """
    return _rasterize(scene, max_side, shaded=True)[2]
