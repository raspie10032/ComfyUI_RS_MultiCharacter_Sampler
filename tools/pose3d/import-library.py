#!/usr/bin/env python3
"""Convert downloaded open-pose-editor positional samples to a local MHR library.

Usage (ComfyUI Python): import-library.py SOURCE.json LOCAL_LIBRARY_DIRECTORY
No sample data is added to Git. Original samples, source revision and license
must be retained alongside the local catalogue.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

import numpy as np

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root.parent))
retarget = importlib.import_module(root.name + '.pose_library').retarget_points
SOURCE_REVISION = '8e659f1f1995715621ac3f50d9c34d55faf5296d'
MAPPING = dict(pelvis=1, chest=5, neck=6, head=7,
               left_shoulder=12, left_elbow=13, left_wrist=14,
               right_shoulder=34, right_elbow=35, right_wrist=36,
               left_hip=55, left_knee=56, left_ankle=58,
               right_hip=66, right_knee=67, right_ankle=69)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    data = json.loads(args.source.read_text())
    poses, skipped = [], []
    for i, raw in enumerate(data):
        try:
            points = {k: np.asarray(raw[j], dtype=float) for k, j in MAPPING.items()}
            if any(v.shape != (3,) or not np.isfinite(v).all() for v in points.values()):
                raise ValueError('missing/nonfinite XYZ points')
            torso = np.linalg.norm(points['neck'] - points['pelvis'])
            if torso < 1e-8:
                raise ValueError('collapsed torso')
            for side in ('left', 'right'):
                for a, b in [('shoulder', 'elbow'), ('elbow', 'wrist'), ('hip', 'knee'), ('knee', 'ankle')]:
                    length = np.linalg.norm(points[side + '_' + a] - points[side + '_' + b])
                    if not .08 <= length / torso <= 3:
                        raise ValueError('collapsed/invalid limb proportions')
            pose = retarget(points)
            poses.append(dict(id=f'openpose-{i:04}', name=f'OpenPose {i+1:04}', **pose))
        except (ValueError, TypeError, IndexError, KeyError) as e:
            skipped.append(dict(index=i, reason=str(e)))
        if (i + 1) % 100 == 0:
            print(f'{i+1}/{len(data)}: {len(poses)} converted, {len(skipped)} rejected', flush=True)
    args.directory.mkdir(parents=True, exist_ok=True)
    result = dict(schema='rs.pose-library.v1', source='https://github.com/ZhUyU1997/open-pose-editor',
                  source_revision=SOURCE_REVISION, source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
                  source_count=len(data), skipped=skipped, poses=poses)
    target = args.directory / 'library.json'
    temp = target.with_suffix('.json.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    temp.replace(target)
    print(f'{len(poses)} editable MHR poses written to {target}; {len(skipped)} invalid originals retained in source.', flush=True)


if __name__ == '__main__':
    main()
