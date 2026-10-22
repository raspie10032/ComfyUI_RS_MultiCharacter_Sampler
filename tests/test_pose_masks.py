import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from dataclasses import replace

import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = importlib.import_module(Path(__file__).resolve().parents[1].name)
p = importlib.import_module(pkg.__name__ + '.pose_nodes')
b = importlib.import_module(pkg.__name__ + '.character_builder')
r = importlib.import_module(pkg.__name__ + '.region_mask')
m = importlib.import_module(pkg.__name__ + '.metadata')
n = importlib.import_module(pkg.__name__ + '.nodes')


def frame():
    points = [(64,20), (64,38), (45,40), (30,60), (20,78),
              (83,40), (98,60), (108,78), (50,78), (48,100),
              (45,120), (78,78), (80,100), (83,120),
              (59,17), (69,17), (55,20), (73,20)]
    return {'canvas_width':128,'canvas_height':128,
            'people':[{'pose_keypoints_2d':[v for x,y in points for v in (x,y,1)]}]}


class PoseMasksTests(unittest.TestCase):
    def test_both_entry_points_and_default_off(self):
        a = p.RSMultiCharacterPoseMasks().apply(json.dumps(frame()))['result']
        c = p.RSMultiCharacterPoseMasks().apply('',pose_keypoints=[frame()])['result']
        self.assertEqual(a[0],c[0])
        self.assertEqual(a[0].slots[0].body_part_strength,0)
        self.assertEqual({name for name,_ in a[0].slots[0].body_parts},
                         {'head','hands','chest','thighs','legs','feet'})
        self.assertEqual(tuple(a[1].shape),(1,128,128,3))

    def test_thickness_changes_mask_and_preview_matches(self):
        a = p.RSMultiCharacterPoseMasks().apply(json.dumps(frame()),thickness=.3)['result']
        c = p.RSMultiCharacterPoseMasks().apply(json.dumps(frame()),thickness=2)['result']
        self.assertLess(a[2].sum(),c[2].sum())
        preview=p.preview_payload(json.dumps(frame()))
        self.assertEqual(preview['masks'][0]['center'],
                         p.RSMultiCharacterPoseMasks().apply(json.dumps(frame()))['result'][0].slots[0].region_mask.center)

    def test_executed_raster_matches_json_preview_for_connected_input(self):
        self.assertTrue(p.RSMultiCharacterPoseMasks.HAS_INTERMEDIATE_OUTPUT)
        data=frame()
        data['people']=data['people']*2
        result=p.RSMultiCharacterPoseMasks().apply('',pose_keypoints=[data],thickness=1.4,confidence=.3)
        executed=result['ui']['pose_masks'][0]
        self.assertEqual(executed,p.preview_payload(json.dumps(data),1.4,.3))
        self.assertEqual(len(executed['masks']),2)
        for mask,slot in zip(executed['masks'],result['result'][0].slots):
            self.assertEqual(mask['center'],slot.region_mask.center)
            self.assertLessEqual(max(mask['width'],mask['height']),128)

    def test_parts_use_person_pivot_when_scaled(self):
        slot=p.RSMultiCharacterPoseMasks().apply(json.dumps(frame()))['result'][0].slots[0]
        moved=replace(slot,mask_transform=(.05,.02,.7))
        actual=dict(b.placed_parts(moved))
        for name,mask in slot.body_parts:
            expected=r.prepare_mask(mask.tensor(),margin=0,offset_x=.05,offset_y=.02,
                                    scale=.7,pivot=slot.region_mask.center)
            self.assertEqual(actual[name],expected)

    def test_clipped_part_does_not_fail_visible_person(self):
        mask=torch.zeros(128,128);mask[30:110,35:100]=1
        head=torch.zeros(128,128);head[2:10,45:55]=1
        slot=b.Slot(1,region_mask=r.prepare_mask(mask,margin=0),
                    body_parts=(('head',r.prepare_mask(head,margin=0)),),
                    mask_transform=(0,-.1,1))
        self.assertTrue(r.place_mask(slot.region_mask,slot.mask_transform).tensor().any())
        self.assertEqual(b.placed_parts(slot),())

    def test_reject_wrong_frame_and_nonfinite_coordinates(self):
        with self.assertRaises(ValueError):p.normalize_pose([frame(),frame()])
        data=frame();data['people'][0]['pose_keypoints_2d'][0]=float('nan')
        with self.assertRaises(ValueError):p.RSMultiCharacterPoseMasks().apply(json.dumps(data))
        for bad in (True,float('nan'),-1,4):
            with self.assertRaises(ValueError):p.RSMultiCharacterPoseMasks().apply(json.dumps(frame()),thickness=bad)

    def test_missing_joints_skipped_and_original_json_not_mutated(self):
        data=frame();data['people'][0]['pose_keypoints_2d'][4*3+2]=0
        original=json.dumps(data)
        result=p.RSMultiCharacterPoseMasks().apply(original)['result']
        self.assertTrue(json.loads(result[3])['skipped'])
        self.assertEqual(json.dumps(data),original)

    def test_body25_and_reducing_people_clear_old_pose_masks(self):
        data=frame();old=data['people'][0]['pose_keypoints_2d']
        joints=[old[i:i+3] for i in range(0,len(old),3)]
        mapping=[0,1,2,3,4,5,6,7,None,8,9,10,11,12,13,14,15,16,17,None,None,None,None,None,None]
        points=[joints[index] if index is not None else [0,0,0] for index in mapping]
        points[8]=[(joints[8][0]+joints[11][0])/2,(joints[8][1]+joints[11][1])/2,1]
        data['pose_model']='BODY_25'
        data['people']=[{'pose_keypoints_2d':[v for point in points for v in point]}]*2
        two=p.RSMultiCharacterPoseMasks().apply(json.dumps(data))['result'][0]
        self.assertEqual(len(two.slots),2)
        self.assertEqual({name for name,_ in two.slots[0].body_parts},
                         {'head','hands','chest','thighs','legs','feet'})
        data['people']=data['people'][:1]
        one=p.RSMultiCharacterPoseMasks().apply(json.dumps(data),building_pipe=two)['result'][0]
        self.assertIsNone(one.slots[1].region_mask)
        self.assertEqual(one.slots[1].body_parts,())

    def test_png_webp_restore_placed_parts_and_interaction(self):
        result=p.RSMultiCharacterPoseMasks().apply(json.dumps(frame()),body_part_strength=.15)['result'][0]
        result=replace(result,prompt_count=1,slots=(replace(result.slots[0],prompt='adult woman',mask_transform=(.05,0,.8)),),
                       interaction_json=json.dumps(dict(preset='delay6',delay_steps=6,decrement=.2)))
        pipe=replace(b.finalize(result),prompt='garden',negative_prompt='bad anatomy')
        record=m.build_record(pipe,{**n.DEFAULTS,'seed':1,'width':128,'height':128},{},[],{'spatial_slots':1})
        for kind in ('PNG','WebP lossless','WebP lossy'):
            with self.subTest(format=kind),tempfile.TemporaryDirectory() as folder:
                path=m.save_image(Image.new('RGB',(128,128)),Path(folder)/'pose.png',record,kind,90)
                with Image.open(path) as image:restored=m.pipe_from_record(m.read_record(image))
                self.assertEqual(pipe.characters,restored.characters)
                self.assertEqual(json.loads(pipe.interaction_json),json.loads(restored.interaction_json))

if __name__=='__main__':unittest.main()
