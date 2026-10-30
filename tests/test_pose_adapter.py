import copy
import importlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent))
p=importlib.import_module(ROOT.name+'.pose3d')
c=importlib.import_module(ROOT.name+'.pose_control_maps')
a=importlib.import_module(ROOT.name+'.pose_adapter')
j=importlib.import_module(ROOT.name+'.joint_engine')


class ControlMapTests(unittest.TestCase):
    def test_maps_share_visibility_and_camera_with_masks(self):
        scene=p.default_scene();scene.update(width=192,height=256)
        scene['people'][0]['position']=[0,0,-.05]
        scene['people'][1]['position']=[.06,0,.08]
        full,visible=p.rasterize(p.read_scene(scene))
        color,depth,skeleton=c.control_maps(scene)
        foreground=visible.any(0)
        np.testing.assert_array_equal(color.max(-1)>0,foreground)
        np.testing.assert_array_equal(depth.max(-1)>0,foreground)
        np.testing.assert_array_equal(color[visible[0]],np.tile([255,0,0],(visible[0].sum(),1)))
        np.testing.assert_array_equal(color[visible[1]],np.tile([0,0,255],(visible[1].sum(),1)))
        self.assertEqual(skeleton.shape,color.shape)
        other=copy.deepcopy(scene);other['people'][0]['joints']={'left_shoulder':[-90,0,0]}
        self.assertFalse(np.array_equal(c.control_maps(other)[2],skeleton))

    def test_scene_output_preserves_ids_and_old_socket_numbers(self):
        node=importlib.import_module(ROOT.name+'.pose3d_node').RSMultiCharacterPose3D
        self.assertEqual(node.RETURN_NAMES[:6],('building_pipe','mask_preview','full_masks','visible_masks','scene_info','pose_image'))
        scene=p.default_scene();scene.update(width=96,height=128)
        outputs=node().apply(json.dumps(scene))['result']
        self.assertEqual(json.loads(outputs[6]),p.read_scene(scene))

    def test_weights_are_pinned_to_recorded_downloads(self):
        specs=json.loads((ROOT/'reference_assets.json').read_text())
        for name in ('krea_pose','moss_pose'):
            self.assertEqual(len(specs[name]['revision']),40)
            self.assertEqual(len(specs[name]['sha256']),64)


class PoseRoutingTests(unittest.TestCase):
    def test_layout_auto_prefers_native_only_for_active_moss_pose(self):
        nodes=importlib.import_module(ROOT.name+'.nodes')
        plan={'rs_3d_pose':{'family':'MOSS'}}
        self.assertEqual(nodes.resolve_layout_method('auto','MOSS',plan),'moss_native')
        for family in ('MOSS','Krea2','Anima','SDXL','SD1.5','FLUX.2'):
            self.assertEqual(nodes.resolve_layout_method('auto',family,{}),'regional')
        self.assertEqual(nodes.resolve_layout_method('auto','Krea2',{'rs_3d_pose':{'family':'Krea2'}}),'regional')
        for choice in ('regional','moss_native'):
            self.assertEqual(nodes.resolve_layout_method(choice,'MOSS',plan),choice)
        with self.assertRaisesRegex(ValueError,'requires MOSS'):
            nodes.resolve_layout_method('moss_native','Krea2',{})
        with self.assertRaisesRegex(ValueError,'Choose auto'):
            nodes.resolve_layout_method('invalid','MOSS',plan)

    def test_cached_pose_keys_are_visible_to_each_region_without_other_character_text(self):
        from test_joint_engine import JointTests,attention
        route=JointTests().make('Krea2');route.pose_runtime={'family':'Krea2'}
        q,k,v=[torch.randn(1,17,16) for _ in range(3)]
        rk,rv=torch.randn(1,3,16),torch.randn(1,3,16)
        calls=[]
        def backend(qi,ki,vi,heads,mask=None,**kwargs):
            torch.testing.assert_close(ki[:,-3:],rk)
            torch.testing.assert_close(vi[:,-3:],rv)
            if mask is not None:
                torch.testing.assert_close(mask[:,-3:],torch.zeros_like(mask[:,-3:]))
            calls.append(ki.shape[1])
            return attention(qi,ki,vi,heads,mask=mask,**kwargs)
        out=route.attention(backend,q,torch.cat((k,rk),1),torch.cat((v,rv),1),2,transformer_options={'block_index':0})
        self.assertEqual(out.shape,q.shape)
        self.assertTrue(torch.isfinite(out).all())
        self.assertGreater(len(calls),2)

    def test_moss_scheduled_controls_apply_to_both_cfg_branches(self):
        import os
        if not os.environ.get('RS_MC_TEST_COMFYUI'):self.skipTest('needs native ComfyUI')
        sys.path.insert(0,os.environ['RS_MC_TEST_COMFYUI'])
        positive=[[torch.zeros(1,2,3),{}]];negative=[[torch.ones(1,2,3),{}]]
        latent=torch.ones(1,8,4,4)
        import node_helpers
        if not hasattr(node_helpers, 'conditioning_set_values_with_timestep_range'):
            with self.assertRaisesRegex(ValueError, 'Update ComfyUI'):
                a.pose_conditioning(positive, negative, dict(family='MOSS', control=latent, start=.1, end=.5))
            return
        pos,neg=a.pose_conditioning(positive,negative,dict(family='MOSS',control=latent,start=.1,end=.5))
        self.assertEqual(positive[0][1],{})
        for cond in (pos,neg):
            active=[meta for _,meta in cond if meta.get('concat_latent_image') is latent]
            self.assertEqual(len(active),1)
            self.assertEqual(active[0]['start_percent'],.1)
            self.assertEqual(active[0]['end_percent'],.5)

    def test_old_core_moss_pose_reports_update_without_affecting_other_models(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        positive=[[torch.zeros(1,2,3),{}]];negative=[[torch.ones(1,2,3),{}]]
        with patch.dict(sys.modules, {'node_helpers': SimpleNamespace()}):
            with self.assertRaisesRegex(ValueError, 'Update ComfyUI'):
                a.pose_conditioning(positive, negative, dict(family='MOSS', control=None, start=0., end=.5))
            self.assertEqual(a.pose_conditioning(positive,negative,None),(positive,negative))
            self.assertEqual(a.pose_conditioning(positive,negative,{'family':'Krea2'}),(positive,negative))
        self.assertEqual(positive[0][1],{})
        self.assertEqual(negative[0][1],{})


class NativePosePatchTests(unittest.TestCase):
    def test_moss_split_qkv_weights_are_all_installed_and_unknown_weights_fail(self):
        import os
        from types import SimpleNamespace
        from unittest.mock import patch
        if not os.environ.get('RS_MC_TEST_COMFYUI'):
            self.skipTest('needs native ComfyUI')
        sys.path.insert(0, os.environ['RS_MC_TEST_COMFYUI'])
        import comfy.lora
        import comfy.sd
        import comfy.utils
        assets=importlib.import_module(ROOT.name+'.reference_assets')
        target='diffusion_model.layers.0.proj.qkv.weight'
        seen=[]
        class Model:
            def __init__(self):
                self.model=SimpleNamespace(state_dict=lambda:{target:torch.zeros(6,2)})
                self.model_options={'rs_3d_pose':dict(family='MOSS',scene=p.default_scene(),
                    vae=SimpleNamespace(encode=lambda image:torch.zeros(1,4,8,8)),
                    strength=1.,start=0.,end=.5,node_id=None)}
            def clone(self):
                other=Model();other.model_options=dict(self.model_options);return other
            def add_patches(self,patches,*args,**kwargs):
                seen.append(patches);return list(patches)
            def add_object_patch(self,*args):pass
        def weights(unknown=False):
            out={'video_embedder.weight':torch.zeros(2,6),'video_embedder.bias':torch.zeros(2)}
            for projection in ('q','k','v'):
                name='layers.0.proj.'+projection
                out[name+'.lora_A.weight']=torch.ones(1,2)
                out[name+'.lora_B.weight']=torch.ones(2,1)
            if unknown:
                out['missing.lora_A.weight']=torch.ones(1,2)
                out['missing.lora_B.weight']=torch.ones(2,1)
            return out
        images=tuple(np.zeros((32,32,3),dtype=np.uint8) for _ in range(3))
        with patch.object(c,'control_maps',return_value=images), \
             patch.object(assets,'_verified_adapter',return_value=Path('fake')), \
             patch.object(comfy.lora,'model_lora_keys_unet',return_value={}), \
             patch.object(comfy.utils,'load_torch_file',return_value=weights()):
            work,runtime=a.prepare_pose(Model(),'MOSS',32,32)
        self.assertEqual(len(seen[0]),3)
        self.assertEqual({key[1] for key in seen[0]}, {(0,0,2),(0,2,2),(0,4,2)})
        self.assertEqual(runtime['control'].shape,(1,8,8,8))
        self.assertIn('rs_pose_runtime',work.model_options)
        seen.clear()
        with patch.object(c,'control_maps',return_value=images), \
             patch.object(assets,'_verified_adapter',return_value=Path('fake')), \
             patch.object(comfy.lora,'model_lora_keys_unet',return_value={}), \
             patch.object(comfy.utils,'load_torch_file',return_value=weights(True)):
            with self.assertRaisesRegex(ValueError,'unsupported projections'):
                a.prepare_pose(Model(),'MOSS',32,32)
        self.assertEqual(seen,[])

    def test_disabled_pose_and_progressive_rejection_do_not_download_weights(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        assets=importlib.import_module(ROOT.name+'.reference_assets')
        model=SimpleNamespace(model_options={})
        with patch.object(assets,'_verified_adapter') as download:
            self.assertEqual(a.prepare_pose(model,'MOSS',768,1024),(model,None))
            model.model_options={'rs_progressive_scale':.5,'rs_3d_pose':{'family':'MOSS'}}
            with self.assertRaisesRegex(ValueError,'full resolution'):
                a.prepare_pose(model,'MOSS',768,1024)
            download.assert_not_called()
