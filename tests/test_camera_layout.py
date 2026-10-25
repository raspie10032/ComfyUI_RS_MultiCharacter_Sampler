from dataclasses import replace
import importlib
import math
from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = importlib.import_module(Path(__file__).resolve().parents[1].name)
c = importlib.import_module(pkg.__name__ + '.characters')
r = importlib.import_module(pkg.__name__ + '.region_mask')
m = importlib.import_module(pkg.__name__ + '.metadata')
layout = importlib.import_module(pkg.__name__ + '.camera_layout')
camera = importlib.import_module(pkg.__name__ + '.camera_control')


class CameraLayoutTests(unittest.TestCase):
    def setUp(self):
        shape=torch.zeros(1,128,192)
        shape[:,30:50,60:80]=1;shape[:,50:100,50:90]=1
        head=shape.clone();head[:,50:]=0
        mask=r.prepare_mask(shape,margin=0)
        self.pipe=c.CharacterPipe((c.Character('adult woman, brown hair',x=mask.center[0],y=mask.center[1],
            region_mask=mask,body_parts=(('head',r.prepare_mask(head,margin=0)),),body_part_strength=.2,
            lora_name='style.safetensors',lora_strength=.9),c.Character('adult woman, pink hair',x=.7,y=.5)),
            prompt='two adult women in a garden',negative_prompt='blur',generation_json='{"version":1,"engine":"anima-spatial-alpha-1","seed":123}',
            interaction_json='{"preset":"delay6","delay_steps":6,"decrement":0.2}')

    def test_identity_off_and_legacy_default(self):
        self.assertIs(layout.camera_layout(self.pipe,.5,0,1.5),self.pipe)
        node=camera.RSCameraControl()
        result=node.apply(context=self.pipe,distance=.8,roll=15)['result'][0]
        for old,new in zip(self.pipe.characters,result.characters):
            self.assertEqual(replace(new,prompt=old.prompt),old)
        self.assertIs(node.apply(context=self.pipe,enabled=False,layout_sync='distance_and_roll')['result'][0],self.pipe)
        self.assertIs(node.apply(context=self.pipe,strength=0,layout_sync='distance_and_roll')['result'][0],self.pipe)

    def test_masks_parts_and_points_share_transform_and_preserve_configuration(self):
        old=self.pipe.rs_context_record()
        transform=layout.framing(.75,20,1.5)
        updated=layout.camera_layout(self.pipe,.75,20,1.5)
        self.assertEqual(self.pipe.rs_context_record(),old)
        self.assertNotEqual(updated.characters[0].region_mask,self.pipe.characters[0].region_mask)
        self.assertNotEqual(updated.characters[0].body_parts,self.pipe.characters[0].body_parts)
        for before,after in zip(self.pipe.characters,updated.characters):
            expected=layout.project(before.x,before.y,transform)
            self.assertAlmostEqual(after.x,expected[0],delta=2/192)
            self.assertAlmostEqual(after.y,expected[1],delta=2/128)
            self.assertEqual(before.lora_name,after.lora_name)
            self.assertEqual(before.lora_strength,after.lora_strength)
        self.assertEqual(replace(updated,characters=self.pipe.characters),self.pipe)
        self.assertEqual(m.pipe_from_record(updated.rs_context_record()).rs_context_record(),updated.rs_context_record())

    def test_clip_and_empty_mask_error_without_modifying_source(self):
        canvas=torch.zeros(1,80,120);canvas[:,5:70,5:60]=1
        mask=r.prepare_mask(canvas,margin=0)
        pipe=replace(self.pipe,characters=(replace(self.pipe.characters[0],region_mask=mask,body_parts=()),))
        changed=layout.camera_layout(pipe,0,10,1.5).characters[0].region_mask
        self.assertEqual((changed.width,changed.height),(120,80))
        self.assertGreater(changed.tensor().sum(),0)
        self.assertEqual(pipe.characters[0].region_mask,mask)
        canvas.zero_();canvas[:,:3,:3]=1
        outside=r.prepare_mask(canvas,margin=0)
        with self.assertRaisesRegex(ValueError,'전부 화면 밖'):
            layout.camera_layout(replace(pipe,characters=(replace(pipe.characters[0],region_mask=outside),)),0,0,1.5)

    def test_aspect_projection_boxes_and_fixed_text(self):
        x,y=layout.project(.7,.5,layout.framing(.5,45,2))
        self.assertAlmostEqual(x,.5+.2/math.sqrt(2))
        self.assertAlmostEqual(y,.5+.4/math.sqrt(2))
        box=c.Character('woman',x=.5,y=.5,bbox=(.3,.2,.7,.8))
        text=c.TextRegion('title',x=.5,y=.1,bbox=(.1,0,.9,.2),text='HELLO')
        pipe=replace(self.pipe,characters=(box,),text_regions=(text,))
        updated=layout.camera_layout(pipe,.75,15,1.5)
        self.assertNotEqual(updated.characters[0].bbox,box.bbox)
        self.assertEqual(updated.text_regions,(text,))
        self.assertEqual(layout.layout_preview(updated)[-1]['kind'],'text')

    def test_random_manual_geometry_matches_and_bad_modes_fail(self):
        node=camera.RSCameraControl()
        random=node.apply(context=self.pipe,random_mode='balanced',random_seed=20261025,layout_sync='distance_and_roll',canvas_aspect=1.5)
        manual=node.apply(context=self.pipe,**random['ui']['camera_values'][0],layout_sync='distance_and_roll',canvas_aspect=1.5)
        self.assertEqual(random['result'],manual['result'])
        for aspect in (0,True,float('nan'),11):
            with self.assertRaisesRegex(ValueError,'비율'):
                node.apply(context=self.pipe,canvas_aspect=aspect)
        with self.assertRaisesRegex(ValueError,'연동'):
            node.apply(context=self.pipe,layout_sync='wrong')


if __name__=='__main__':unittest.main()
