# SPDX-License-Identifier: GPL-3.0-only
"""MHR native bind skinning. Asset terms: web/pose3d/MHR-LICENSE.txt.

No inference, face landmark mapping, or pose corrective model is required.
Rotations are extrinsic XYZ (Rz @ Ry @ Rx), matching the baked rig probe.
"""
from functools import lru_cache
import copy
import gzip
import json
from pathlib import Path

import numpy as np


@lru_cache(maxsize=1)
def asset():
    with gzip.open(Path(__file__).parent/'web/pose3d/mhr-body.json.gz', 'rt') as f:
        return json.load(f)


def rotation(angles):
    # Existing procedural scene rotation is intrinsic XYZ; reverse/transposed
    # angle construction here to keep the native MHR convention explicit.
    from .pose3d import rotation as intrinsic
    return intrinsic([-v for v in angles]).T


def quaternion(values):
    x, y, z, w = np.asarray(values)/np.linalg.norm(values)
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def global_matrices(angles):
    d = asset()
    matrices = []
    for i, local in enumerate(d['localTransforms']):
        m = np.eye(4)
        m[:3, :3] = quaternion(local['quaternion'])*local['scale'] @ rotation(angles.get(d['names'][i], [0, 0, 0]))
        m[:3, 3] = local['position']
        parent = d['parents'][i]
        matrices.append(matrices[parent] @ m if parent >= 0 else m)
    return np.array(matrices)


@lru_cache(maxsize=1)
def bind_data():
    d = asset()
    weights = np.asarray(d['weights']).reshape(-1, 4)
    weights = weights/weights.sum(1, keepdims=True)
    return (np.column_stack((np.asarray(d['vertices']).reshape(-1, 3), np.ones(len(weights)))),
            np.asarray(d['faces']).reshape(-1, 3), np.asarray(d['indices']).reshape(-1, 4),
            weights, np.linalg.inv(global_matrices({})))


def default_scene():
    from .pose3d import default_scene as legacy
    scene = legacy()
    scene['version'] = 2
    scene['outline'] = True
    for p in scene['people']:
        p['joints'] = copy.deepcopy(asset()['presets']['standing'])
    return scene


def clip_source_frame(vertices, faces, points, planes):
    """Keep the part inside the source photo, in unscaled MHR coordinates.

    Clip crossing triangles too: deleting only out-of-frame joints or whole
    triangles leaves either invented legs or holes at the photo boundary.
    """
    if not planes:
        return vertices, faces, points
    planes = np.asarray(planes)
    distance = vertices @ planes[:, :3].T + planes[:, 3]
    per_face = distance[faces]
    inside = (per_face >= -1e-10).all(axis=(1, 2))
    outside = (per_face < -1e-10).all(axis=1).any(axis=1)
    kept = faces[inside].tolist()
    extra = []
    for face in faces[~(inside | outside)]:
        polygon = vertices[face]
        for plane in planes:
            clipped = []
            for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
                da, db = a @ plane[:3]+plane[3], b @ plane[:3]+plane[3]
                if da >= -1e-10:
                    clipped.append(a)
                if (da >= -1e-10) != (db >= -1e-10):
                    clipped.append(a+(b-a)*da/(da-db))
            polygon = np.asarray(clipped)
            if len(polygon) < 3:
                break
        if len(polygon) < 3:
            continue
        start = len(vertices)+len(extra)
        extra.extend(polygon)
        kept.extend([start, start+i, start+i+1] for i in range(1, len(polygon)-1))
    points = {k: v for k, v in points.items() if (v @ planes[:, :3].T+planes[:, 3] >= -1e-10).all()}
    if not kept:
        return np.empty((0, 3)), np.empty((0, 3), dtype=int), points
    vertices = np.concatenate((vertices, np.asarray(extra).reshape(-1, 3)))
    indices, inverse = np.unique(np.asarray(kept).ravel(), return_inverse=True)
    return vertices[indices], inverse.reshape(-1, 3), points


def mannequin(person):
    d = asset()
    angles = {d['controls'][k]: v for k, v in person['joints'].items()}
    # Pose-dependent twist supports remain internal, never user-controlled.
    for rule in d['proceduralRotations']:
        angles[d['names'][rule['bone']]] = [sum(angles.get(d['names'][j], [0, 0, 0])[axis]*weight
                                               for j, axis, weight in terms) for terms in rule['axes']]
    posed = global_matrices(angles)
    vertices, faces, indices, weights, inverse = bind_data()
    transforms = posed @ inverse
    skinned = np.zeros((len(vertices), 3))
    for k in range(4):
        skinned += np.einsum('nij,nj->ni', transforms[indices[:, k]], vertices)[:, :3]*weights[:, k, None]
    from .pose3d import rotation as body_rotation
    r = body_rotation(person['rotation'])
    size = person['scale']*np.array([person['bulk'], 1., person['bulk']])
    points = {key: posed[d['names'].index(name), :3, 3]
              for key, name in d['controls'].items()}
    skinned, faces, points = clip_source_frame(skinned, faces, points, person.get('source_frame'))
    points = {key: (point*size) @ r.T+person['position'] for key, point in points.items()}
    return (skinned*size) @ r.T+person['position'], faces, points
