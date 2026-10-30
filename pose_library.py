# SPDX-License-Identifier: GPL-3.0-only
"""Local-only pose catalogue and anatomical retargeting to the editor's MHR rig.

No downloaded pose assets or external requests belong in this module. Libraries
live under ComfyUI/models/rs_pose3d (including configured model paths).
"""
import copy
import json
from pathlib import Path

import numpy as np

from . import mhr


def _unit(v):
    n = np.linalg.norm(v)
    if not np.isfinite(n) or n < 1e-8:
        raise ValueError('Collapsed or invalid pose bone. / 포즈 관절 간 거리가 너무 짧습니다.')
    return v / n


def _basis(x, y):
    y = _unit(y)
    x = _unit(x - y * np.dot(x, y))
    return np.column_stack((x, y, np.cross(x, y)))


def _aim(a, b):
    a, b = _unit(a), _unit(b)
    c = np.clip(a @ b, -1., 1.)
    v = np.cross(a, b)
    if c < -1 + 1e-8:
        axis = _unit(np.cross(a, np.eye(3)[np.argmin(np.abs(a))]))
        return 2 * np.outer(axis, axis) - np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def euler_xyz(r):
    """Extrinsic XYZ degrees, matching mhr.rotation, including gimbal lock."""
    y = np.arcsin(np.clip(-r[2, 0], -1., 1.))
    if abs(np.cos(y)) > 1e-7:
        x, z = np.arctan2(r[2, 1], r[2, 2]), np.arctan2(r[1, 0], r[0, 0])
    else:
        x, z = np.arctan2(-r[1, 2], r[1, 1]), 0.
    return np.rad2deg([x, y, z]).tolist()


def retarget_points(points):
    """Preserve 3D bone directions, using the editor's own body proportions.

    Position-only sources cannot recover axial twist/fingers or hidden joints.
    Body/limb alignment is explicit rather than a learned pose approximation.
    """
    d = mhr.asset()
    indices = {k: d['names'].index(v) for k, v in d['controls'].items()}
    targets = {k: np.asarray(v, dtype=float) for k, v in points.items()}
    if any(v.shape != (3,) or not np.isfinite(v).all() for v in targets.values()):
        raise ValueError('Pose points must be finite XYZ triples.')
    angles = {}

    def world():
        g = mhr.global_matrices({d['controls'][k]: v for k, v in angles.items()})
        return g, {k: g[i, :3, 3] for k, i in indices.items()}

    def set_world(key, desired, g):
        i = indices[key]
        parent = d['parents'][i]
        parent_r = g[parent, :3, :3] if parent >= 0 else np.eye(3)
        bind_r = mhr.quaternion(d['localTransforms'][i]['quaternion'])
        angles[key] = euler_xyz(bind_r.T @ parent_r.T @ desired)

    for key, side_a, side_b, top, bottom in [
        ('pelvis', 'left_hip', 'right_hip', 'neck', 'pelvis'),
        ('chest', 'left_shoulder', 'right_shoulder', 'neck', 'chest'),
    ]:
        g, current = world()
        desired_basis = _basis(targets[side_a] - targets[side_b], targets[top] - targets[bottom])
        current_basis = _basis(current[side_a] - current[side_b], current[top] - current[bottom])
        set_world(key, desired_basis @ current_basis.T @ g[indices[key], :3, :3], g)
    links = [('neck', 'head')]
    for side in ('left', 'right'):
        links += [(side + '_' + a, side + '_' + b) for a, b in
                  [('shoulder', 'elbow'), ('elbow', 'wrist'), ('hip', 'knee'), ('knee', 'ankle')]]
    for a, b in links:
        g, current = world()
        turn = _aim(current[b] - current[a], targets[b] - targets[a])
        set_world(a, turn @ g[indices[a], :3, :3], g)
    person = copy.deepcopy(mhr.default_scene()['people'][0])
    person.update(position=[0, 0, 0], joints=angles)
    vertices, _, _ = mhr.mannequin(person)
    return dict(joints=angles, floor_y=float(-vertices[:, 1].min()))


def retarget_rotations(rotations):
    """SAM3D's MHR-native global rotations -> editable MHR controls.

    Controlled descendants absorb motion of intermediate, non-editable bones.
    No OpenPose 2D/depth guess or second learned rig translation is involved.
    """
    d = mhr.asset()
    desired = np.asarray(rotations, dtype=float)
    if desired.shape != (len(d['names']), 3, 3) or not np.isfinite(desired).all():
        raise ValueError('SAM 3D Body returned invalid MHR rotations.')
    if not np.allclose(desired @ desired.transpose(0, 2, 1), np.eye(3), atol=.003) or not np.allclose(np.linalg.det(desired), 1., atol=.003):
        raise ValueError('SAM 3D Body returned invalid rotation matrices.')
    controls = {v: k for k, v in d['controls'].items()}
    globals_, angles = [], {}
    for i, local in enumerate(d['localTransforms']):
        parent = d['parents'][i]
        base = mhr.quaternion(local['quaternion'])
        parent_r = globals_[parent] if parent >= 0 else np.eye(3)
        if d['names'][i] in controls:
            key = controls[d['names'][i]]
            angles[key] = euler_xyz(base.T @ parent_r.T @ desired[i])
            base = base @ mhr.rotation(angles[key])
        globals_.append(parent_r @ base)
    person = copy.deepcopy(mhr.default_scene()['people'][0])
    person.update(position=[0, 0, 0], rotation=[0, 0, 0], scale=1., bulk=1., joints=angles)
    vertices, _, _ = mhr.mannequin(person)
    return dict(joints=angles, floor_y=float(-vertices[:, 1].min()))


def library_directories():
    import folder_paths
    try:
        directories = folder_paths.get_folder_paths('rs_pose3d')
    except KeyError:
        directories = []
    return list(dict.fromkeys([Path(folder_paths.models_dir) / 'rs_pose3d', *map(Path, directories)]))


def read_library(directories=None):
    """Read local catalogues; never resolve a caller-provided filesystem path."""
    entries, warnings, used = [], [], set()
    for directory in library_directories() if directories is None else directories:
        path = Path(directory) / 'library.json'
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > 32_000_000:
                raise ValueError('Catalogue exceeds 32 MB.')
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('schema') != 'rs.pose-library.v1' or not isinstance(data.get('poses'), list):
                raise ValueError('Unsupported pose library schema.')
            for p in data['poses']:
                if not isinstance(p, dict):
                    raise ValueError('Invalid pose entry.')
                identity = p.get('id')
                if not isinstance(identity, str) or not 1 <= len(identity) <= 160 or identity in used:
                    raise ValueError('Invalid/duplicate pose ID.')
                joints = p.get('joints')
                if not isinstance(joints, dict) or not joints.keys() <= mhr.asset()['controls'].keys():
                    raise ValueError('Unknown pose joint.')
                for v in joints.values():
                    if not isinstance(v, list) or len(v) != 3 or any(type(a) not in (int, float) for a in v) or not np.isfinite(v).all() or np.max(np.abs(v)) > 180:
                        raise ValueError('Pose angles must be finite degrees (-180 to 180).')
                floor = p.get('floor_y', 0.)
                if type(floor) not in (int, float) or not np.isfinite(floor) or abs(floor) > 5:
                    raise ValueError('Invalid pose ground offset.')
                entries.append(dict(id=identity, name=str(p.get('name', identity))[:160], joints=joints, floor_y=floor))
                used.add(identity)
        except (OSError, ValueError, TypeError, AttributeError) as e:
            warnings.append(f'{path.name}: {e}')
    return dict(poses=entries, warnings=warnings)
