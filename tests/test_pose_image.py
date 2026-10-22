import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
pkg=importlib.import_module(Path(__file__).resolve().parents[1].name)
d=importlib.import_module(pkg.__name__+'.pose_image')
p=importlib.import_module(pkg.__name__+'.pose_nodes')


def figure(x=180):
    return np.array([(x,90),(x,140),(x-40,145),(x-75,220),(x-90,295),
        (x+40,145),(x+75,220),(x+90,295),(x-30,325),(x-35,455),
        (x-40,590),(x+30,325),(x+35,455),(x+40,590),
        (x-10,83),(x+10,83),(x-22,91),(x+22,91)],dtype=float)


def render(people,opaque=False,missing=(),transparent=False):
    image=Image.new('RGB',(768,768))
    draw=ImageDraw.Draw(image)
    # Independent simple line renderer, not the decoder's component machinery.
    links=[(1,2),(1,5),(2,3),(3,4),(5,6),(6,7),(1,8),(8,9),
           (9,10),(1,11),(11,12),(12,13),(1,0),(0,14),(14,16),(0,15),(15,17)]
    colors=[(255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),
        (85,255,0),(0,255,0),(0,255,85),(0,255,170),(0,255,255),
        (0,170,255),(0,85,255),(0,0,255),(85,0,255),(170,0,255),
        (255,0,255),(255,0,170),(255,0,85)]
    for points in people:
        for i,(a,b) in enumerate(links):
            if a not in missing and b not in missing:
                color=colors[i] if opaque else tuple(round(c*.6) for c in colors[i])
                draw.line([tuple(points[a]),tuple(points[b])],fill=color,width=5)
        for i,(x,y) in enumerate(points):
            if i not in missing:draw.ellipse((x-5,y-5,x+5,y+5),fill=colors[i])
    if transparent:
        array=np.array(image.convert('RGBA'));array[:,:,3]=np.any(array[:,:,:3],axis=2)*255
        array[array[:,:,3]==0,:3]=255  # Invisible RGB must not become a white background.
        return Image.fromarray(array)
    return image


class PoseImageTests(unittest.TestCase):
    def assert_people(self,image,expected,tolerance=3):
        data,notes=d.decode_pose_image(np.array(image))
        self.assertEqual(len(data['people']),len(expected))
        for person,points in zip(data['people'],expected):
            restored=np.array(person['pose_keypoints_2d']).reshape(18,3)
            self.assertTrue((restored[:,2]>0).all(),restored)
            self.assertLess(np.max(np.linalg.norm(restored[:,:2]-points,axis=1)),tolerance)
        self.assertTrue(notes)
        return data

    def test_standard_png_one_two_three_people_sorted_by_neck(self):
        for positions in ((360,),(220,540),(130,380,630)):
            points=[figure(x) for x in positions]
            self.assert_people(render(list(reversed(points))),points)

    def test_crossed_hands_follow_colored_links_not_nearest_neck(self):
        a,b=figure(240),figure(520)
        a[5:8]=[(280,145),(390,210),(565,255)]
        b[2:5]=[(480,145),(375,300),(195,265)]
        data=self.assert_people(render([a,b]),[a,b])
        masks=p.RSMultiCharacterPoseMasks().apply('',image=torch.tensor(np.array(render([a,b]))/255).float()[None])['result'][2]
        self.assertEqual(masks.shape[0],2)
        self.assertEqual(data['pose_model'],'COCO_18')

    def test_opaque_editor_png(self):
        points=[figure(230),figure(540)]
        self.assert_people(render(points,opaque=True),points,tolerance=8)

    def test_sticks_painted_over_joints_still_find_bodies(self):
        points=figure(350)
        image=render([points])
        draw=ImageDraw.Draw(image)
        # Older maps blend a colored limb over its joint dots.
        for edge in (0,1,6,9,12):
            a,b=d.LINKS[edge]
            draw.line([tuple(points[a]),tuple(points[b])],
                      fill=tuple(round(c*.6) for c in d.COLORS[edge]),width=7)
        data,_=d.decode_pose_image(np.array(image))
        self.assertEqual(len(data['people']),1)
        restored=np.array(data['people'][0]['pose_keypoints_2d']).reshape(18,3)
        self.assertGreater(restored[1,2],0)
        self.assertLess(np.linalg.norm(restored[1,:2]-points[1]),20)

    def test_rainbow_hand_does_not_create_an_extra_person(self):
        image=render([figure(350)])
        draw=ImageDraw.Draw(image)
        # A fan of short finger sticks has many body colors but no torso.
        for i,color in enumerate(d.COLORS):
            x=570+i*5
            draw.line([(620,650),(x,620-i%3*5)],fill=tuple(map(int,color)),width=3)
        data,_=d.decode_pose_image(np.array(image))
        self.assertEqual(len(data['people']),1)

    def test_hidden_joint_is_omitted_instead_of_moved_to_origin(self):
        data,_=d.decode_pose_image(np.array(render([figure(350)],missing=(4,10))))
        person=np.array(data['people'][0]['pose_keypoints_2d']).reshape(18,3)
        self.assertEqual(person[4,2],0);self.assertEqual(person[10,2],0)
        self.assertGreater(person[3,2],0)

    def test_numpy_fallback_preserves_separate_components(self):
        mask=np.zeros((12,12),bool);mask[1:3,1:3]=True;mask[8:10,8:10]=True
        with patch.dict(sys.modules,{'cv2':None}):
            result=list(d.components(mask))
            self.assertEqual(sorted(len(x) for x in result),[4,4])

    def test_reject_blank_photo_grayscale_and_batches(self):
        for array in (np.zeros((256,256,3),np.uint8),np.full((256,256,3),220,np.uint8),
                np.repeat(np.asarray(render([figure(350)]).convert('L'))[:,:,None],3,axis=2)):
            with self.assertRaises(ValueError):d.decode_pose_image(array)
        for batch in (torch.zeros(2,128,128,3),torch.full((1,128,128,3),float('nan')),torch.zeros(1,128,128)):
            with self.assertRaises(ValueError):p.resolve_pose('',image=batch)

    def test_uploaded_and_connected_png_same_masks_and_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            image=render([figure(350)],transparent=True)
            image.save(Path(folder)/'pose.png')
            host=SimpleNamespace(get_input_directory=lambda:folder)
            with patch.dict(sys.modules,{'folder_paths':host}):
                file=p.RSMultiCharacterPoseMasks().apply('invalid JSON',pose_image='pose.png')['result']
                rgba=torch.from_numpy(np.array(image,dtype=np.float32)/255)[None]
                linked=p.RSMultiCharacterPoseMasks().apply('invalid JSON',pose_image='missing.png',image=rgba)['result']
                torch.testing.assert_close(file[2],linked[2])
                self.assertEqual(json.loads(file[3])['source_kind'],'png')
                source=json.loads(file[3])['source']
                direct=p.resolve_pose('',pose_keypoints=[source],pose_image='missing.png',image=torch.zeros(2,3))[0]
                self.assertEqual(direct,source)
                first=p.RSMultiCharacterPoseMasks.IS_CHANGED(pose_image='pose.png')
                render([figure(400)]).save(Path(folder)/'pose.png')
                second=p.RSMultiCharacterPoseMasks.IS_CHANGED(pose_image='pose.png')
                self.assertNotEqual(first,second)
                self.assertEqual(p.RSMultiCharacterPoseMasks.IS_CHANGED(pose_image='missing.png',image=rgba),'')
                self.assertIn('pose.png',p.pose_files())
                for filename in ('../outside.png','/tmp/outside.png','missing.png'):
                    with self.assertRaises(ValueError):p.read_pose_image(filename)


if __name__=='__main__':unittest.main()
