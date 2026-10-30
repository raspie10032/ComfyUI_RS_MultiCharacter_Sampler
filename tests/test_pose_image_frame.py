"""A cropped image must not become a full-body pose in any output path."""
import copy
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
m = importlib.import_module(ROOT.name+'.mhr')
p = importlib.import_module(ROOT.name+'.pose3d')
e = importlib.import_module(ROOT.name+'.pose_estimator')
c = importlib.import_module(ROOT.name+'.pose_control_maps')


class ImageFrameTests(unittest.TestCase):
    def import_half(self, base=''):
        g = m.global_matrices({})
        prediction = dict(pred_global_rots=g[:, :3, :3],
                          pred_joint_coords=g[:, :3, 3]*[1, -1, -1],
                          pred_cam_t=[0, 1.6, 2.2], focal_length=1000.)
        scene, pose = e.import_pose(prediction['pred_global_rots'], base, 1,
                                   prediction=prediction, image_size=(400, 500))
        return scene, pose

    def test_photo_frame_survives_serialization_and_all_outputs_exclude_legs(self):
        scene, _ = self.import_half()
        self.assertEqual(scene, p.read_scene(json.dumps(scene)))
        person = scene['people'][0]
        vertices, faces, points = m.mannequin(person)
        self.assertIn('head', points)
        self.assertIn('neck', points)
        self.assertNotIn('left_knee', points)
        self.assertNotIn('left_ankle', points)
        self.assertNotIn('pelvis', points)
        self.assertTrue(len(faces))
        local = vertices-person['position']
        frame = np.asarray(person['source_frame'])
        self.assertTrue((local @ frame[:, :3].T+frame[:, 3] >= -1e-9).all())
        # Cropping is geometry attached to this person, not only a front camera
        # trick: moving the scene camera cannot resurrect unseen legs.
        side = copy.deepcopy(scene)
        side['camera'] = dict(position=[3, .4, 0], target=[0, .4, 0], fov=30)
        color, depth, bones = c.control_maps(side)
        self.assertTrue(color.any())
        self.assertTrue(depth.any())
        self.assertTrue(bones.any())
        self.assertLess(vertices[:, 1].max()-vertices[:, 1].min(), .8)

    def test_replacing_one_person_keeps_other_person_and_scene_camera(self):
        base = m.default_scene()
        base['people'][1]['joints'] = {'left_elbow': [25, 0, 0]}
        scene, _ = self.import_half(json.dumps(base))
        self.assertEqual(scene['people'][1], base['people'][1])
        self.assertEqual(scene['camera'], base['camera'])
        self.assertEqual((scene['width'], scene['height']), (base['width'], base['height']))
        self.assertIn('source_frame', scene['people'][0])

    def test_empty_and_crossing_triangles_and_missing_openpose_joints(self):
        planes = [[0, 1, 0, -1.2], [0, -1, 0, 3], [1, 0, 0, 3],
                  [-1, 0, 0, 3], [0, 0, 1, 3]]
        person = m.default_scene()['people'][0]
        person.update(source_frame=planes, position=[0, 0, 0])
        vertices, faces, _ = m.mannequin(person)
        self.assertGreater(len(faces), 0)
        self.assertAlmostEqual(vertices[:, 1].min(), 1.2, places=9)
        person['source_frame'][0][3] = -50
        vertices, faces, points = m.mannequin(person)
        self.assertEqual(vertices.shape, (0, 3))
        self.assertEqual(faces.shape, (0, 3))
        self.assertEqual(points, {})
        self.assertFalse(np.asarray(c.openpose([{}], 100, 100)).any())

    def test_javascript_editor_matches_clipped_python_geometry(self):
        if not shutil.which('node'):
            self.skipTest('Node.js required for editor parity')
        scene, _ = self.import_half()
        person = scene['people'][0]
        person.update(scale=.7, bulk=1.2, rotation=[10, 30, -15], position=[.2, .1, -.1])
        code = f"""import {{readFileSync}} from 'node:fs';import {{gunzipSync}} from 'node:zlib';
import {{initRig,rigMannequin,rigSkeleton}} from {json.dumps((ROOT/'web/pose3d/mhr.mjs').as_uri())};
initRig(JSON.parse(gunzipSync(readFileSync({json.dumps(str(ROOT/'web/pose3d/mhr-body.json.gz'))}))));
const p={json.dumps(person)};console.log(JSON.stringify({{...rigMannequin(p),visible:rigSkeleton(p).visible}}));"""
        js = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', code], text=True))
        vertices, faces, points = m.mannequin(person)
        np.testing.assert_allclose(vertices, js['vertices'], atol=3e-12, rtol=0)
        np.testing.assert_array_equal(faces, js['faces'])
        self.assertEqual(set(points), set(js['points']))
        self.assertEqual(set(points), set(js['visible']))
        for key in points:
            np.testing.assert_allclose(points[key], js['points'][key], atol=3e-12, rtol=0)

    def test_invalid_frame_is_rejected(self):
        scene, _ = self.import_half()
        for value in ([], [[0, 0, 0, 0]]*5, [[1, 0, 0, float('nan')]]*5):
            bad = copy.deepcopy(scene)
            bad['people'][0]['source_frame'] = value
            with self.assertRaises(ValueError):
                p.read_scene(bad)


if __name__ == '__main__':
    unittest.main()
