import importlib
import itertools
import json
from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = importlib.import_module(Path(__file__).resolve().parents[1].name)
d = importlib.import_module(pkg.__name__ + '.mask_drawing')
b = importlib.import_module(pkg.__name__ + '.character_builder')
l = importlib.import_module(pkg.__name__ + '.layout')
m = importlib.import_module(pkg.__name__ + '.metadata')
n = importlib.import_module(pkg.__name__ + '.nodes')


class MaskDrawingTests(unittest.TestCase):
    def drawing(self):
        return {'version': 1, 'width': 128, 'height': 128, 'layers': {
            '1': {'strokes': [{'tool':'brush','size':.2,'points':[[.2,.2],[.2,.8]]}]},
            '2': {'strokes': [{'tool':'brush','size':.2,'points':[[.8,.2],[.8,.8]]}]},
        }}

    def test_order_independent_numbering_not_sorting_or_reference_identity(self):
        for order in itertools.permutations(('draw','prompt','position')):
            pipe = None
            for action in order:
                if action == 'draw':
                    pipe, = d.RSMultiCharacterMaskDraw().apply(json.dumps(self.drawing()), 0, pipe)
                elif action == 'prompt':
                    pipe, = b.RSMultiCharacterPrompt().apply(2, building_pipe=pipe, character1='black hair', character2='red hair')
                else:
                    pipe, = b.RSMultiCharacterPosition().apply(2, building_pipe=pipe, character1_x=.9, character2_x=.1)
            final = b.finalize(pipe)
            self.assertLess(final.characters[0].region_mask.center[0], .3)
            self.assertGreater(final.characters[1].region_mask.center[0], .7)
            self.assertEqual(final.characters[0].prompt, 'black hair')
            centers, _ = l.effective_centers(final.characters)
            masks = l.character_masks(final.characters, centers, 128, 128, .04)
            self.assertEqual(masks.shape[0], 2)

    def test_erase_only_selected_layer_and_cleared_layer_uses_point(self):
        data = self.drawing()
        data['layers']['1']['strokes'].append({'tool':'erase','size':.4,'points':[[.2,.1],[.2,.9]]})
        pipe, = b.RSMultiCharacterPrompt().apply(2, character1='girl',character2='girl')
        pipe, = d.RSMultiCharacterMaskDraw().apply(json.dumps(data), 0, pipe)
        final = b.finalize(pipe)
        self.assertIsNone(final.characters[0].region_mask)
        self.assertIsNotNone(final.characters[1].region_mask)

    def test_position_placement_is_order_independent_and_keeps_source(self):
        original, = d.RSMultiCharacterMaskDraw().apply(json.dumps(self.drawing()), 0)
        original_mask = original.slots[0].region_mask
        outputs = []
        for order in itertools.permutations(('draw', 'prompt', 'position')):
            pipe = None
            for action in order:
                if action == 'draw':
                    pipe, = d.RSMultiCharacterMaskDraw().apply(json.dumps(self.drawing()), 0, pipe)
                elif action == 'prompt':
                    pipe, = b.RSMultiCharacterPrompt().apply(2, building_pipe=pipe, character1='black hair', character2='red hair')
                else:
                    pipe, = b.RSMultiCharacterPosition().apply(2, building_pipe=pipe, mask_transforms='{"1":[0.2,0.1,0.5]}')
            self.assertEqual(pipe.slots[0].region_mask, original_mask)
            final = b.finalize(pipe)
            first, second = final.characters
            self.assertAlmostEqual(first.x, .4, delta=.02)
            self.assertAlmostEqual(first.y, .6, delta=.02)
            self.assertLess(first.region_mask.tensor().sum(), original_mask.tensor().sum() / 2)
            self.assertEqual(second.region_mask, original.slots[1].region_mask)
            record = m.build_record(final, {**n.DEFAULTS, 'seed': 7}, {}, [], {'spatial_slots':2})
            self.assertEqual(m.pipe_from_record(record).characters, final.characters)
            outputs.append(final)
        self.assertTrue(all(output == outputs[0] for output in outputs))
        self.assertEqual(b.finalize(b.RSMultiCharacterPrompt().apply(2, building_pipe=original, character1='a', character2='b')[0]).characters[0].region_mask, original_mask)

    def test_bad_position_data_and_clipped_empty_mask(self):
        for raw in ('null', '[]', '{bad', '{"0":[0,0,1]}', '{"1":[0,0,0]}', '{"1":[true,0,1]}', '{"1":[0,0,NaN]}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, 'Invalid mask placement'):
                b.RSMultiCharacterPosition().apply(mask_transforms=raw)
        pipe, = d.RSMultiCharacterMaskDraw().apply(json.dumps(self.drawing()), 0)
        pipe, = b.RSMultiCharacterPrompt().apply(2, building_pipe=pipe, character1='a', character2='b')
        moved, = b.RSMultiCharacterPosition().apply(2, building_pipe=pipe, mask_transforms='{"1":[-1,0,1]}')
        with self.assertRaisesRegex(ValueError, 'outside the canvas'):
            b.finalize(moved)
        reset, = b.RSMultiCharacterPosition().apply(2, building_pipe=moved, mask_transforms='{}')
        self.assertEqual(b.finalize(reset).characters[0].region_mask, pipe.slots[0].region_mask)

    def test_uniform_scale_shift_and_outside_clipping(self):
        data = self.drawing()
        data['layers']['1'].update(scale=2,x=.4,y=0)
        pipe, = d.RSMultiCharacterMaskDraw().apply(json.dumps(data), 0)
        mask = pipe.slots[0].region_mask.tensor()
        self.assertEqual(mask.shape,(128,128))
        self.assertGreater(mask.sum(),0)
        self.assertFalse(mask[:,:10].any())
        data['layers']['1']['x']=-1
        with self.assertRaisesRegex(ValueError,'outside the canvas'):
            d.RSMultiCharacterMaskDraw().apply(json.dumps(data),0)

    def test_drawing_saved_independent_of_reference_and_replaces_old_table(self):
        data = self.drawing()
        first, = d.RSMultiCharacterMaskDraw().apply(json.dumps(data),0)
        data['background']={'filename':'missing.png','type':'input','subfolder':'nonexistent'}
        second, = d.RSMultiCharacterMaskDraw().apply(json.dumps(data),0)
        self.assertEqual(first,second)
        data['layers'].pop('1')
        changed, = d.RSMultiCharacterMaskDraw().apply(json.dumps(data),0,first)
        self.assertIsNone(changed.slots[0].region_mask)
        self.assertIsNotNone(first.slots[0].region_mask)
        prompt, = b.RSMultiCharacterPrompt().apply(2,building_pipe=first,character1='girl A',character2='girl B')
        pipe = b.finalize(prompt)
        record = m.build_record(pipe, {**n.DEFAULTS, 'seed': 7}, {}, [], {'spatial_slots':2})
        self.assertEqual(m.pipe_from_record(record).characters,pipe.characters)

    def test_invalid_or_empty_data_fails_before_sampling(self):
        bad = [None, '{}', 'null', '[]', '{broken', d.EMPTY_DRAWING]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                d.RSMultiCharacterMaskDraw().apply(value,0)
        for mutation in (
            lambda v:v.update(width=True), lambda v:v.update(height=999999),
            lambda v:v['layers'].update({'11':v['layers']['1']}),
            lambda v:v['layers']['1'].update(scale=float('nan')),
            lambda v:v['layers']['1']['strokes'][0].update(size=0),
            lambda v:v['layers']['1']['strokes'][0].update(points=[[float('inf'),.2]]),
        ):
            value = self.drawing(); mutation(value)
            with self.assertRaises(ValueError): d.RSMultiCharacterMaskDraw().apply(json.dumps(value),0)
