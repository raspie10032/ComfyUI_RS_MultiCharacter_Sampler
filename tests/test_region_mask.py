import base64
import copy
import importlib
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zlib

from PIL import Image
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = importlib.import_module(Path(__file__).resolve().parents[1].name)
b = importlib.import_module(pkg.__name__+'.character_builder')
c = importlib.import_module(pkg.__name__+'.characters')
r = importlib.import_module(pkg.__name__+'.region_mask')
l = importlib.import_module(pkg.__name__+'.layout')
route = importlib.import_module(pkg.__name__+'.routing')
m = importlib.import_module(pkg.__name__+'.metadata')
n = importlib.import_module(pkg.__name__+'.nodes')
d = importlib.import_module(pkg.__name__+'.detailer')


class RegionMaskTests(unittest.TestCase):
    def silhouette(self):
        mask = torch.zeros((1, 64, 64))
        mask[:, 8:24, 12:28] = 1
        mask[:, 24:56, 8:32] = 1
        mask[:, 22:30, 28:55] = 1
        return mask

    def test_prepare_threshold_dilation_and_no_shared_tensor(self):
        mask = self.silhouette()
        mask[:, 0, 0] = .5
        raw = r.prepare_mask(mask, .5, 0)
        wide = r.prepare_mask(mask, .5, 3)
        self.assertGreater(wide.tensor().sum(), raw.tensor().sum())
        self.assertEqual(raw.tensor()[0, 0], 0)
        self.assertEqual(raw, r.RegionMask.from_record(raw.record()))
        old = raw.tensor()
        mask.fill_(1)
        old.zero_()
        self.assertGreater(raw.tensor().sum(), 0)
        self.assertLess(raw.tensor().sum(), 4096)

    def test_scale_and_shift_preserve_canvas_clip_without_wrap_or_refit(self):
        mask = torch.zeros(1, 80, 120)
        mask[:, 20:60, 40:80] = 1
        half = r.prepare_mask(mask, margin=0, scale=.5).tensor()
        expected = torch.zeros(80, 120); expected[30:50, 50:70] = 1
        torch.testing.assert_close(half, expected)
        double = r.prepare_mask(mask, margin=0, scale=2, offset_x=.25).tensor()
        expected.zero_(); expected[:, 50:120] = 1
        torch.testing.assert_close(double, expected)
        self.assertEqual(tuple(double.shape), (80, 120))
        shifted = r.prepare_mask(mask, margin=0, offset_x=.5, offset_y=-.5).tensor()
        expected.zero_(); expected[:20, 100:120] = 1
        torch.testing.assert_close(shifted, expected)
        with self.assertRaisesRegex(ValueError, 'outside the canvas'):
            r.prepare_mask(mask, margin=0, offset_x=1)

    def test_transform_then_margin_and_metadata_keep_applied_shape(self):
        mask = self.silhouette()
        prepared = r.prepare_mask(mask, margin=2, offset_x=.25, offset_y=.125, scale=.75)
        pipe = b.finalize(b.RSMultiCharacterMask().apply(mask=mask, character_id=1, margin=2,
            offset_x=.25, offset_y=.125, scale=.75, building_pipe=
            b.RSMultiCharacterPrompt().apply(1, character1='girl')[0])['result'][0])
        self.assertEqual(pipe.characters[0].region_mask, prepared)
        pipe = c.CharacterPipe(pipe.characters, 'scene', 'bad')
        settings = {**n.DEFAULTS, 'seed': 27}
        record = m.build_record(pipe, settings, {}, [prepared.center], {'spatial_slots':1})
        for fmt in m.FORMATS:
            with tempfile.TemporaryDirectory() as temp:
                path = m.save_image(Image.new('RGB',(64,64)), Path(temp)/'out', record, fmt)
                with Image.open(path) as image:
                    self.assertEqual(m.pipe_from_record(m.read_record(image)).characters, pipe.characters)
        # Old workflows omit the optional transform inputs and remain identical.
        default = b.RSMultiCharacterMask().apply(mask=mask)['result'][0].slots[0].region_mask
        self.assertEqual(default, r.prepare_mask(mask))

    def actions(self):
        return [
            ('prompt', dict(character_count=2, character1='red girl', character2='blue girl')),
            ('position', dict(character_count=2, character1_x=.9, character2_x=.75)),
            ('lora', dict(character_count=2, character1_lora='a.safetensors', lora_application_mode='normal')),
            ('mask', dict(character_id=1, mask=self.silhouette(), margin=0)),
        ]

    def assemble(self, actions):
        pipe = None
        types = dict(prompt=b.RSMultiCharacterPrompt, position=b.RSMultiCharacterPosition,
                     lora=b.RSMultiCharacterLoRA, mask=b.RSMultiCharacterMask)
        for name, settings in actions:
            result = types[name]().apply(building_pipe=pipe, **settings)
            pipe = result['result'][0] if isinstance(result, dict) else result[0]
        return pipe, b.finalize(pipe)

    def test_all_24_orders_mask_overrides_position_keeps_lora(self):
        expected = self.assemble(self.actions())[1]
        for order in itertools.permutations(self.actions()):
            self.assertEqual(self.assemble(order)[1], expected)
        self.assertEqual(expected.characters[0].lora_name, 'a.safetensors')
        self.assertEqual(expected.lora_application_mode, 'normal')
        self.assertLess(expected.characters[0].x, .5)
        centers, moved = l.effective_centers(expected.regions)
        self.assertFalse(moved)
        self.assertEqual(centers[1], (.75, .5))

    def test_off_restores_xy_and_hidden_slots_not_generated(self):
        building, pipe = self.assemble(self.actions())
        off = b.RSMultiCharacterMask().apply(1, enabled=False, building_pipe=building)['result'][0]
        self.assertIsNotNone(pipe.characters[0].region_mask)
        self.assertIsNone(b.finalize(off).characters[0].region_mask)
        self.assertEqual(b.finalize(off).characters[0].x, .9)
        hidden, = b.RSMultiCharacterPrompt().apply(1, building_pipe=building, character1='girl')
        self.assertEqual(len(b.finalize(hidden).characters), 1)

    def test_mixed_masks_boxes_points_and_background_write_once(self):
        mask = r.prepare_mask(self.silhouette(), margin=0)
        chars = (c.Character('red', region_mask=mask),
                 c.Character('blue', x=.75),
                 c.Character('text-free object', x=.5, y=.1, bbox=(0, 0, 1, .2)))
        centers, _ = l.effective_centers(chars)
        masks = l.character_masks(chars, centers, 512, 512, .04)
        groups = route.token_groups(masks, 32, 32, boxes=(True, False, True))
        all_indices = torch.cat([indices for _, indices in groups.cells])
        self.assertEqual(len(all_indices), 1024)
        self.assertEqual(len(all_indices.unique()), 1024)
        self.assertEqual(len(torch.cat([groups[0], groups[2]]).unique()),
                         len(torch.cat([groups[0], groups[1], groups[2]]).unique())-len(groups[1]))
        # Two identical silhouettes share the captions only inside the shape.
        groups = route.token_groups(masks[:1].repeat(2, 1, 1), 32, 32, boxes=(True, True))
        self.assertEqual({members for members, _ in groups.cells}, {(), (0, 1)})
        self.assertGreater(len(groups.background), 0)
        q, k, v = torch.randn(1, 1024, 1, 4), torch.randn(1, 3, 1, 4), torch.randn(1, 3, 1, 4)
        actual = route.route_cross(q, k, v, groups, [1, 1, 1], [0])
        expected = route.sdpa(q[:, groups.background], k[:, :1], v[:, :1])
        torch.testing.assert_close(actual[:, groups.background], expected)

    def test_png_webp_and_detailer_preserve_masks(self):
        _, pipe = self.assemble(self.actions())
        pipe = c.CharacterPipe(pipe.characters, 'scene', 'bad', lora_application_mode='normal')
        settings = {**n.DEFAULTS, 'seed': 27}
        record = m.build_record(pipe, settings, {}, [(v.x,v.y) for v in pipe.characters], {'spatial_slots':2})
        for fmt in m.FORMATS:
            with tempfile.TemporaryDirectory() as temp:
                path = m.save_image(Image.new('RGB',(64,64)), Path(temp)/'out', record, fmt)
                with Image.open(path) as im:
                    restored = m.pipe_from_record(m.read_record(im))
                self.assertEqual(restored.characters, pipe.characters)
                self.assertEqual(restored.lora_application_mode, 'normal')
        detailed = d.detail_record(pipe, 64, 64, {}, {}, [])
        self.assertEqual(m.pipe_from_record(detailed).characters, pipe.characters)
        legacy = copy.deepcopy(record)
        del legacy['rs_multicharacter']['character_masks']
        self.assertIsNone(m.pipe_from_record(legacy).characters[0].region_mask)

    def test_bad_mask_inputs_and_tiny_regions_fail_before_sampling(self):
        for value in (None, torch.zeros(1,64,64), torch.ones(2,64,64),
                      torch.full((1,64,64), float('nan')), torch.ones(1,64,64)*2):
            with self.assertRaises(ValueError):
                r.prepare_mask(value)
        for kwargs in ({'margin':True}, {'margin':129}, {'threshold':float('nan')}, {'threshold':True},
                       {'scale':0}, {'scale':4.01}, {'scale':True}, {'offset_x':1.01},
                       {'offset_y':float('nan')}, {'offset_y':True}):
            with self.assertRaises(ValueError):
                r.prepare_mask(self.silhouette(), **kwargs)
        tiny = torch.zeros(1,512,512); tiny[:,0,0]=1
        char = c.Character('girl', region_mask=r.prepare_mask(tiny, margin=0))
        with self.assertRaisesRegex(ValueError, 'too small'):
            l.character_masks((char,), ((.5,.5),), 64,64,.04)

    def test_corrupt_and_expanding_metadata_rejected(self):
        good = r.prepare_mask(self.silhouette(), margin=0).record()
        for changes in ({'width':True}, {'height':4097}, {'sha256':'incorrect'},
                        {'data':'!!!!'}, {'data':base64.b64encode(zlib.compress(b'x'*100000)).decode()},
                        {'data':good['data'][:-4]}, {'encoding':'other'}):
            with self.assertRaises(ValueError):
                r.RegionMask.from_record({**good, **changes})
        mask = r.prepare_mask(self.silhouette())
        with self.assertRaises(ValueError):
            c.TextRegion('title', bbox=(0,0,1,1), text='HELLO', region_mask=mask)

    def test_moss_native_mask_bounds_and_box_text_mix(self):
        source = torch.zeros(8, 12)
        source[1:7, 2:6] = 1
        source[2, 6:10] = 1  # Nonrectangular silhouette; preserve its farthest tip.
        mask = r.prepare_mask(source, margin=0)
        character = c.Character('person', bbox=(0, 0, 1, 1), region_mask=mask)
        text = c.TextRegion('sign', bbox=(0, 0, 1, 1), text='HELLO')
        pipe = c.CharacterPipe((character,), 'scene', text_regions=(text,))
        record = mask.record()
        result = json.loads(l.moss_layout_prompt(pipe, 120, 80))
        self.assertEqual(result['items'][0]['bbox'], [-30, -40, 30, 40])
        self.assertEqual(result['items'][1]['bbox'], [-40, -60, 40, 60])
        self.assertEqual(result['items'][1]['text'], 'HELLO')
        self.assertEqual(mask.record(), record)  # Keep original silhouette in pipe.

    def test_moss_native_uses_placed_clipped_mask(self):
        source = torch.zeros(8, 12)
        source[1:7, 2:6] = 1
        source[2, 6:10] = 1
        mask = r.prepare_mask(source, margin=0, offset_x=.5)
        pipe = c.CharacterPipe((c.Character('person', region_mask=mask),))
        self.assertEqual(json.loads(l.moss_layout_prompt(pipe, 120, 80))['items'][0]['bbox'],
                         [-30, 20, 30, 60])
        # A single source pixel still encloses at least one output pixel.
        tiny = torch.zeros(3, 7)
        tiny[2, 6] = 1
        pipe = c.CharacterPipe((c.Character('person', region_mask=r.prepare_mask(tiny, margin=0)),))
        self.assertEqual(json.loads(l.moss_layout_prompt(pipe, 8, 8))['items'][0]['bbox'],
                         [1, 2, 4, 4])
