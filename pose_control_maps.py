# SPDX-License-Identifier: GPL-3.0-only
"""3D scene control maps use the same camera and depth buffer as region masks."""
import numpy as np
from PIL import Image, ImageDraw
from . import pose3d


def control_maps(raw):
    scene = pose3d.read_scene(raw)
    full, visible, color, depth = pose3d._rasterize(scene, control_maps=True)
    joints = []
    for person in scene['people']:
        if scene['version'] == 2:
            from .mhr import mannequin
        else:
            mannequin = pose3d.mannequin
        _, _, points = mannequin(person)
        joints.append({name: pose3d.project(np.array([v]), scene['camera'], scene['width'], scene['height'])[0].tolist()
                       for name, v in points.items()})
    return color, depth, np.asarray(openpose(joints, scene['width'], scene['height']))


def openpose(joints, w, h):
    # COCO-18 body topology, with head centre used for the nose marker.
    names = ['head', 'neck', 'right_shoulder', 'right_elbow', 'right_wrist',
             'left_shoulder', 'left_elbow', 'left_wrist', 'right_hip',
             'right_knee', 'right_ankle', 'left_hip', 'left_knee', 'left_ankle']
    colors = [(255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),
              (85,255,0),(0,255,0),(0,255,85),(0,255,170),(0,255,255),
              (0,170,255),(0,85,255),(0,0,255),(85,0,255)]
    links = [(1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),
             (9,10),(1,11),(11,12),(12,13),(1,0)]
    image = Image.new('RGB', (w, h))
    draw = ImageDraw.Draw(image)
    radius = max(3, round(min(w, h)/160))
    for person in joints:
        points = [tuple(person[k][:2]) for k in names]
        for i, (a, b) in enumerate(links):
            draw.line([points[a], points[b]], fill=tuple(int(c*.6) for c in colors[i]), width=radius*2)
        for point, color in zip(points, colors):
            x, y = point
            draw.ellipse((x-radius,y-radius,x+radius,y+radius), fill=color)
    return image
