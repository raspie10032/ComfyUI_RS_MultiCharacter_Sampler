import copy
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from dataclasses import replace

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent))
p=importlib.import_module(ROOT.name+'.pose3d')
n=importlib.import_module(ROOT.name+'.pose3d_node')
b=importlib.import_module(ROOT.name+'.character_builder')
r=importlib.import_module(ROOT.name+'.region_mask')

class Pose3DTests(unittest.TestCase):
    def scene(self):
        s=p.default_scene();s['width']=192;s['height']=256;return s

    def test_projection_and_raster_use_same_geometry_as_editor(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node.js is needed for cross-language geometry validation')
        s=self.scene();s['people'][0]['rotation']=[15,32,-8]
        s['people'][0]['joints']={'chest':[7,-13,19],'left_shoulder':[45,10,-35],'left_elbow':[23,-6,43]}
        s['people'][0]['scale']=.72;s['people'][0]['bulk']=1.2;s['camera']['position']=[1.4,2.2,3.6]
        code=f"import {{mannequin,project}} from {json.dumps((ROOT/'web/pose3d/model.mjs').as_uri())};const s={json.dumps(s)};const m=mannequin(s.people[0]);console.log(JSON.stringify({{...m,projected:project(m.vertices,s.camera,s.width,s.height)}}));"
        js=json.loads(subprocess.check_output([node,'--input-type=module','-e',code],text=True))
        v,f,j=p.mannequin(s['people'][0]);np.testing.assert_allclose(v,js['vertices'],rtol=0,atol=1e-12)
        np.testing.assert_array_equal(f,js['faces'])
        np.testing.assert_allclose(p.project(v,s['camera'],s['width'],s['height']),js['projected'],atol=1e-10)
        for name in j:np.testing.assert_allclose(j[name],js['points'][name],atol=1e-12)

    def test_rotating_parent_moves_children_only(self):
        person=self.scene()['people'][0];before,_=p.skeleton(person)
        person['joints']['left_shoulder']=[-90,0,0];after,_=p.skeleton(person)
        np.testing.assert_array_equal(before['right_wrist'],after['right_wrist'])
        np.testing.assert_array_equal(before['left_shoulder'],after['left_shoulder'])
        self.assertGreater(np.linalg.norm(before['left_wrist']-after['left_wrist']),.5)

    def test_full_overlap_visible_depth_and_identity(self):
        s=self.scene();s['people'][0]['position']=[0,0,-.05];s['people'][1]['position']=[.06,0,.08]
        scene,full,visible=n.render_scene(s)
        self.assertTrue(np.any(full[0]&full[1]));self.assertFalse(np.any(visible[0]&visible[1]))
        self.assertTrue(np.all(visible<=full));self.assertGreater(visible[1].sum(),visible[0].sum())
        np.testing.assert_array_equal(full.any(0),visible.any(0))
        reversed_scene=copy.deepcopy(s);reversed_scene['people'].reverse()
        canonical,other,_=n.render_scene(reversed_scene)
        self.assertEqual([x['id'] for x in canonical['people']],[1,2]);np.testing.assert_array_equal(full,other)

    def test_canvas_clips_partial_and_rejects_empty(self):
        s=self.scene();s['people'][1]['position'][0]=1.
        _,full,_=n.render_scene(s);self.assertTrue(full[1,:,-1].any())
        s['people'][1]['position'][0]=9
        with self.assertRaisesRegex(ValueError,'Character 2'):n.render_scene(s)

    def test_fully_occluded_visible_requires_user_correction(self):
        s=self.scene();s['people'][0]['position']=[0,0,0];s['people'][1]['position']=[0,0,0]
        n.render_scene(s);s['mask_mode']='visible'
        with self.assertRaisesRegex(ValueError,'full silhouettes'):n.render_scene(s)

    def test_near_plane_clipping_is_finite(self):
        s=self.scene();s['people']=s['people'][:1];s['camera']={'position':[0,1.15,.5],'target':[0,.9,0],'fov':90}
        s=p.read_scene(s);full,visible=p.rasterize(s);self.assertTrue(full.any());self.assertTrue(np.all(visible<=full))
        tri=np.array([[-1,0,-1],[1,0,1],[0,1,1.]])
        self.assertEqual(len(p.clip_near(tri)),2)
        self.assertTrue(all((t[:,2]>=.05-1e-12).all() for t in p.clip_near(tri)))

    def test_node_outputs_full_and_visible_and_exact_pipe_mask(self):
        s=self.scene();s['people'][0]['position'][0]=-.1;s['people'][1]['position'][0]=.1
        s['mask_mode']='visible';out=n.RSMultiCharacterPose3D().apply(json.dumps(s))
        pipe,preview,full,visible,info,pose_image=out['result']
        self.assertEqual(tuple(preview.shape),(1,256,192,3));self.assertEqual(tuple(full.shape),(2,256,192))
        self.assertEqual(tuple(pose_image.shape),(1,256,192,3))
        self.assertFalse((visible[0]*visible[1]).any())
        for slot,mask in zip(pipe.slots,visible):np.testing.assert_array_equal(slot.region_mask.tensor(),mask)
        self.assertEqual(out['ui']['pose3d'][0]['masks'][1]['number'],2)

    def test_pose_image_tracks_depth_and_excludes_background_and_editor_handles(self):
        s=self.scene();s['people'][0]['position']=[0,0,-.05];s['people'][1]['position']=[.06,0,.08]
        full,visible=p.rasterize(s);rgb=p.render_pose_condition(s)
        np.testing.assert_array_equal(rgb.any(-1),visible.any(0))
        # Shade varies over the same person's body; it is not a flat ID mask.
        self.assertGreater(len(np.unique(rgb[visible[1]],axis=0)),20)
        # The nearer, blue person retains blue-dominant shading at overlaps.
        pixels=rgb[full[0]&visible[1]]
        self.assertGreater(len(pixels),0);self.assertTrue(np.all(pixels[:,2]>pixels[:,0]))
        changed=copy.deepcopy(s);changed['people'][1]['joints']['left_shoulder']=[0,0,-120]
        self.assertFalse(np.array_equal(rgb,p.render_pose_condition(changed)))
        tiny=p.render_pose_condition(s,64);self.assertEqual(tiny.shape,(64,48,3))

    def test_pipe_order_preserves_prompts_positions_and_loras(self):
        raw=json.dumps(self.scene());node=n.RSMultiCharacterPose3D()
        def add(pipe):return b.update_slot(pipe,1,prompt='adult woman',lora_name='a.safetensors',strength_model=.8,x=.25,y=.6,geometry='box',width=.4,height=.8)
        a=node.apply(raw,add(None))['result'][0];z=add(node.apply(raw)['result'][0])
        self.assertEqual(a.slots,z.slots)
        self.assertIsNone(a.prompt_count) # Scene editing never chooses active prompt count.
        source=b.RSMultiCharacterPrompt().apply(2,character1='adult woman',character2='adult man')[0]
        merged=node.apply(raw,source)['result'][0]
        self.assertEqual(len(b.finalize(merged).characters),2)

    def test_reducing_scene_removes_only_own_previous_mask(self):
        s=self.scene();node=n.RSMultiCharacterPose3D();pipe=node.apply(json.dumps(s))['result'][0]
        s['people']=s['people'][:1]
        reduced=node.apply(json.dumps(s),pipe)['result'][0]
        self.assertIsNone(reduced.slots[1].region_mask)
        replacement=r.RegionMask(8,8,bytes([255]*8));pipe=b.update_slot(pipe,2,region_mask=replacement)
        reduced=node.apply(json.dumps(s),pipe)['result'][0]
        self.assertEqual(reduced.slots[1].region_mask,replacement)

    def test_validation_rejects_duplicate_id_invalid_joint_and_nonfinite(self):
        mutations=[lambda s:s['people'][1].update(id=1),lambda s:s.update(width=True),lambda s:s.update(height=8192),lambda s:s['people'][0].update(scale=float('nan')),lambda s:s['people'][0].update(joints={'tail':[0,0,0]}),lambda s:s['camera'].update(position=[0,.9,0]),lambda s:s['camera'].update(position=[0,4,0]),lambda s:s['people'][0].update(position=[False,0,0])]
        for mutation in mutations:
            s=self.scene();mutation(s)
            with self.assertRaises(ValueError):p.read_scene(s)
        for raw in ('{bad','[]','x'*100001):
            with self.assertRaises(ValueError):p.read_scene(raw)

    def test_default_scene_roundtrip_is_immutable(self):
        s=self.scene();copy_s=copy.deepcopy(s);clean=p.read_scene(json.dumps(s));n.render_scene(clean)
        self.assertEqual(s,copy_s);self.assertEqual(clean,p.read_scene(json.dumps(clean)))

if __name__=='__main__':unittest.main()
