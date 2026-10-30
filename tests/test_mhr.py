"""Native rig, cross-language output, legacy scene and mask/pose alignment."""
import copy
import gzip
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent))
m=importlib.import_module(ROOT.name+'.mhr')
p=importlib.import_module(ROOT.name+'.pose3d')
n=importlib.import_module(ROOT.name+'.pose3d_node')

class MHRTests(unittest.TestCase):
    def scene(self):
        s=m.default_scene();s.update(width=192,height=256);return s

    def test_skin_rest_and_editor_python_agree_after_joint_body_and_size_changes(self):
        if not shutil.which('node'):self.skipTest('Node.js required for geometry parity')
        s=self.scene();person=s['people'][0]
        person.update(rotation=[15,32,-8],scale=.72,bulk=1.2)
        person['joints'].update(chest=[7,-13,19],left_shoulder=[45,10,-35],left_elbow=[23,-6,43],left_index1=[30,10,5])
        code=f"""import {{readFileSync}} from 'node:fs';import {{gunzipSync}} from 'node:zlib';
import {{initRig,rigMannequin,rigSkeleton}} from {json.dumps((ROOT/'web/pose3d/mhr.mjs').as_uri())};
initRig(JSON.parse(gunzipSync(readFileSync({json.dumps(str(ROOT/'web/pose3d/mhr-body.json.gz'))}))));
const person={json.dumps(person)};console.log(JSON.stringify({{...rigMannequin(person),...rigSkeleton(person)}}));"""
        js=json.loads(subprocess.check_output(['node','--input-type=module','-e',code],text=True))
        vertices,faces,points=m.mannequin(person)
        np.testing.assert_allclose(vertices,js['vertices'],atol=2e-12,rtol=0)
        np.testing.assert_array_equal(faces,js['faces'])
        for key in points:np.testing.assert_allclose(points[key],js['points'][key],atol=2e-12,rtol=0)
        # Bind reconstruction at zero joint deltas is identity skinning.
        rest=copy.deepcopy(person);rest.update(rotation=[0,0,0],position=[0,0,0],scale=1,bulk=1,joints={})
        np.testing.assert_allclose(m.mannequin(rest)[0],np.array(m.asset()['vertices']).reshape(-1,3),atol=2e-12)

    def test_finger_deforms_hand_not_other_arm_and_is_validated(self):
        s=self.scene();before=m.mannequin(s['people'][0]);s['people'][0]['joints']['left_index1']=[65,0,0]
        after=m.mannequin(s['people'][0]);difference=np.linalg.norm(after[0]-before[0],axis=1)
        self.assertGreater(np.count_nonzero(difference>1e-5),10)
        np.testing.assert_array_equal(before[2]['right_wrist'],after[2]['right_wrist'])
        self.assertEqual(p.read_scene(s)['version'],2)
        s['people'][0]['joints']['tail']=[0,0,0]
        with self.assertRaises(ValueError):p.read_scene(s)

    def test_shading_outline_does_not_change_pipe_masks_and_depth_is_exclusive(self):
        s=self.scene();s['people'][0]['position']=[-.05,0,-.05];s['people'][1]['position']=[.07,0,.1]
        scene=p.read_scene(s);full,visible,rgb=p._rasterize(scene,shaded=True)
        self.assertTrue((full[0]&full[1]).any());self.assertFalse((visible[0]&visible[1]).any())
        self.assertTrue((rgb.any(-1)&~visible.any(0)).any()) # pose outline only
        scene['outline']=False;other_full,other_visible,no_outline=p._rasterize(scene,shaded=True)
        np.testing.assert_array_equal(full,other_full);np.testing.assert_array_equal(visible,other_visible)
        np.testing.assert_array_equal(no_outline.any(-1),visible.any(0))
        self.assertFalse(np.array_equal(rgb,no_outline))
        masks=p.rasterize(scene);np.testing.assert_array_equal(masks[0],full);np.testing.assert_array_equal(masks[1],visible)

    def test_native_scene_roundtrip_and_legacy_remain_separate(self):
        native=p.read_scene(self.scene());self.assertEqual(native,p.read_scene(json.dumps(native)))
        legacy=p.default_scene();self.assertEqual(legacy['version'],1)
        self.assertNotIn('outline',p.read_scene(legacy))
        self.assertEqual(json.loads(n.RSMultiCharacterPose3D.INPUT_TYPES()['required']['scene_json'][1]['default'])['version'],2)
        native['outline']='false'
        with self.assertRaisesRegex(ValueError,'Outline'):p.read_scene(native)

    def test_native_node_outputs_mask_exactly_and_finite_pose_image(self):
        s=self.scene();s['people'][0]['joints']=copy.deepcopy(m.asset()['presets']['seated'])
        out=n.RSMultiCharacterPose3D().apply(json.dumps(s))['result']
        pipe,_,full,visible,info,pose,scene_json=out
        for slot,mask in zip(pipe.slots,full):np.testing.assert_array_equal(slot.region_mask.tensor(),mask)
        self.assertEqual(tuple(pose.shape),(1,256,192,3));self.assertTrue(pose.isfinite().all())
        self.assertEqual(json.loads(info)['body_model'],'MHR')

if __name__=='__main__':unittest.main()
