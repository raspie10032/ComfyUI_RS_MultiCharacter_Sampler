"""Exercise actual role methods; no model download, sampling or HTTP requests."""
import importlib
import itertools
import json
from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
package = importlib.import_module(Path(__file__).resolve().parents[1].name)
b = importlib.import_module(package.__name__ + '.character_builder')
cam = importlib.import_module(package.__name__ + '.camera_control')


class BuilderOrderTests(unittest.TestCase):
    def actions(self, camera=None):
        mask = torch.zeros(1, 64, 64)
        mask[:, 18:46, 12:28] = 1
        actions = [
            ('prompt', b.RSMultiCharacterPrompt(), dict(character_count=3,
                character1='brown hair', character2='pink hair',
                character3_kind='text', character3='HELLO')),
            ('lora', b.RSMultiCharacterLoRA(), dict(character_count=2,
                lora_application_mode='normal', character1_lora='a.safetensors',
                character1_lora_strength=.8, character2_lora='b.safetensors')),
            ('position', b.RSMultiCharacterPosition(), dict(character_count=3,
                character2_geometry='box', character2_x=.72, character2_width=.2,
                character2_height=.5, character3_geometry='box', character3_y=.12,
                character3_width=.5, character3_height=.1,
                mask_transforms='{"1":[0.03,0.04,1.1]}')),
            ('mask', b.RSMultiCharacterMask(), dict(character_id=1, mask=mask, margin=0)),
            ('reference', package.RSMultiCharacterReference(), dict(character_id=1,
                image=torch.full((1, 32, 64, 3), .25), resolution=64, strength=.6)),
            ('interaction', package.RSMultiCharacterInteraction(), dict(preset='delay6')),
        ]
        if camera is not None:
            actions.append(('camera', camera, dict(base_prompt='two people in a garden',
                layout_sync='perspective', azimuth=25, elevation=15,
                distance=.65, roll=12, canvas_aspect=1.5)))
        return actions

    def assemble(self, actions, source=None):
        pipe = source
        for _, node, settings in actions:
            result = node.apply(building_pipe=pipe, **settings)
            pipe = (result['result'] if isinstance(result, dict) else result)[0]
        return b.RSMultiCharacterFinalize().build(building_pipe=pipe)[0]

    def test_all_5040_orders_of_seven_independent_roles(self):
        actions = self.actions(cam.RSCameraControl())
        raw = self.assemble(actions[:-1])
        expected = actions[-1][1].apply(building_pipe=raw, **actions[-1][2])['result'][0]
        record = expected.rs_context_record()
        for order in itertools.permutations(actions):
            with self.subTest(order=[name for name, _, _ in order]):
                output = self.assemble(order)
                self.assertEqual(output.rs_context_record(), record)
                self.assertEqual(output.characters[0].reference.source, expected.characters[0].reference.source)
                self.assertEqual(output.characters[0].reference.strength, .6)
                self.assertEqual(output.characters[0].lora_name, 'a.safetensors')
                self.assertEqual(output.text_regions[0].text, 'HELLO')
        self.assertIsNone(raw.prompt)
        self.assertEqual(raw.characters[0].prompt, 'brown hair')

    def test_fixed_framing_and_random_cameras_in_all_24_orders(self):
        for options in (dict(layout_sync='fixed'), dict(layout_sync='distance_and_roll'),
                        dict(layout_sync='perspective', random_mode='balanced', random_seed=12345),
                        dict(enabled=False), dict(strength=0)):
            actions = [action for action in self.actions(cam.RSCameraControl())
                       if action[0] in ('prompt', 'position', 'mask', 'camera')]
            actions[-1][2].update(options)
            expected = self.assemble(actions).rs_context_record()
            for order in itertools.permutations(actions):
                self.assertEqual(self.assemble(order).rs_context_record(), expected)

    def test_disabled_middle_slot_is_preserved_until_finalize(self):
        actions = [action for action in self.actions(cam.RSCameraControl())
                   if action[0] in ('prompt', 'position', 'camera')]
        actions[0][2]['character2_enable'] = False
        expected = self.assemble(actions)
        for order in itertools.permutations(actions):
            output = self.assemble(order)
            self.assertEqual(output.rs_context_record(), expected.rs_context_record())
            self.assertEqual(len(output.characters), 1)
            self.assertEqual(output.text_regions[0].text, 'HELLO')

    def test_drawing_and_pose_parts_in_all_120_orders_each(self):
        points = [(64,20),(64,38),(45,40),(30,60),(20,78),(83,40),(98,60),
                  (108,78),(50,78),(48,100),(45,120),(78,78),(80,100),
                  (83,120),(59,17),(69,17),(55,20),(73,20)]
        pose = json.dumps({'canvas_width':128, 'canvas_height':128,
            'people':[{'pose_keypoints_2d':[v for x,y in points for v in (x,y,1)]}]})
        drawing = json.dumps({'version':1,'width':128,'height':128,'layers':{
            '1':{'strokes':[{'tool':'brush','size':.2,'points':[[.3,.2],[.3,.8]]}]}}})
        alternatives = [
            ('drawing', package.RSMultiCharacterMaskDraw(), dict(drawing=drawing, margin=0)),
            ('pose', package.RSMultiCharacterPoseMasks(), dict(pose_json=pose, body_part_strength=.2)),
        ]
        for replacement in alternatives:
            actions = [replacement if name=='mask' else (name,node,values)
                for name,node,values in self.actions(cam.RSCameraControl())
                if name in ('prompt','lora','position','mask','camera')]
            expected = self.assemble(actions).rs_context_record()
            for order in itertools.permutations(actions):
                self.assertEqual(self.assemble(order).rs_context_record(), expected)

    def test_camera_without_scene_waits_for_finalize_and_does_not_mutate_branch(self):
        seed = cam.RSCameraControl().apply()['result'][0]
        pipe, = b.RSMultiCharacterPrompt().apply(building_pipe=seed, character_count=1, character1='person')
        with self.assertRaisesRegex(ValueError, 'base_prompt'):
            b.finalize(pipe)
        off = cam.RSCameraControl().apply(building_pipe=pipe, enabled=False)['result'][0]
        self.assertIsNone(b.finalize(off).prompt)
        self.assertNotEqual(off.camera_settings, pipe.camera_settings)
        with self.assertRaisesRegex(ValueError, 'base_prompt'):
            b.finalize(pipe)

    def test_repeated_camera_replaces_only_camera_table_and_off_clears_it(self):
        node = cam.RSCameraControl()
        actions = self.actions()
        pipe = None
        for _, role, values in actions:
            result = role.apply(building_pipe=pipe, **values)
            pipe = (result['result'] if isinstance(result, dict) else result)[0]
        first = node.apply(building_pipe=pipe, base_prompt='garden', distance=.7)['result'][0]
        second = node.apply(building_pipe=first, base_prompt='cafe', elevation=30)['result'][0]
        direct = node.apply(building_pipe=pipe, base_prompt='cafe', elevation=30)['result'][0]
        self.assertEqual(b.finalize(second), b.finalize(direct))
        off = node.apply(building_pipe=first, enabled=False)['result'][0]
        self.assertEqual(b.finalize(off), b.finalize(pipe))


if __name__ == '__main__':
    unittest.main()
