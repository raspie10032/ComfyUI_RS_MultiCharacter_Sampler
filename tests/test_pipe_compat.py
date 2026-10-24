"""Shared pipe normalization without model loading."""
import copy
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
package = Path(__file__).resolve().parents[1].name
c = importlib.import_module(package + '.characters')
p = importlib.import_module(package + '.pipe_compat')
m = importlib.import_module(package + '.metadata')
prompts = importlib.import_module(package + '.nai_prompts')


class PipeCompatTests(unittest.TestCase):
    def test_character_negatives_are_masked_without_global_leakage(self):
        import torch
        regions = (c.Character('red hair', 'blue hair', .25), c.Character('blue hair', '', .75))
        masks = torch.zeros(2, 4, 4); masks[0, :, :2] = 1; masks[1, :, 2:] = 1
        def encode(text, **kwargs):
            return [[text, {'encoder': kwargs.get('encoder')}]]
        result = p.regional_negatives(encode, 'blur', regions, masks, ['left','right'])
        self.assertEqual(len(result), 2)
        captions = {text: meta for text,meta in result}
        self.assertEqual(captions['blur, blue hair']['encoder'], 'left')
        self.assertEqual(captions['blur']['encoder'], 'right')
        self.assertEqual(captions['blur, blue hair']['mask'][0,:,2:].sum(), 0)
        self.assertEqual(captions['blur']['mask'][0,:,:2].sum(), 0)
        torch.testing.assert_close(sum(meta['mask'] for _,meta in result), torch.ones(1,4,4))
        # Text slots have no character LoRA encoder, including with imported UC.
        texts = (*regions, c.TextRegion('title', y=.125, bbox=(0,0,1,.25), text='HI'))
        text_masks = torch.cat((masks, torch.ones(1,4,4)))
        self.assertTrue(p.regional_negatives(encode, 'blur', texts, text_masks, ['left','right']))
        no_uc = (c.Character('red'), c.Character('blue'))
        self.assertEqual(p.regional_negatives(encode, 'blur', no_uc, masks), [['blur', {'encoder':None}]])

    def test_shared_adapter_and_native_passthrough(self):
        native = c.CharacterPipe((c.Character('girl'),), 'scene', 'bad')
        self.assertIs(p.local_pipe(native), native)
        self.assertIs(p.local_pipe(SimpleNamespace(as_local_character_pipe=lambda: native)), native)
        with self.assertRaises(ValueError):
            p.local_pipe(SimpleNamespace(as_local_character_pipe=lambda: object()))

    def test_receiver_normalizes_before_its_type_check(self):
        class Receiver:
            FUNCTION = 'run'
            @classmethod
            def INPUT_TYPES(cls):
                return {'required': {'image': ('IMAGE',), 'character_pipe': (c.PIPE_TYPE,)}}
            def run(self, image, character_pipe):
                assert isinstance(character_pipe, c.CharacterPipe)
                return image, character_pipe
        p.shared_pipe_inputs(Receiver)
        native = c.CharacterPipe((c.Character('girl'),))
        adapter = SimpleNamespace(as_local_character_pipe=lambda: native)
        self.assertEqual(Receiver().run('image', adapter), ('image', native))
        self.assertEqual(Receiver().run(image='image', character_pipe=adapter), ('image', native))

    def test_image_import_trims_ten_converts_negatives_and_preserves_record(self):
        original = c.CharacterPipe((c.Character('person, -1.5::hat::', 'bad', .2, .8),),
                                  '2::scene:: tail, -2::text::', 'blur', 'NovelAI')
        record = m.captions(original)
        for caption in ('v4_prompt', 'v4_negative_prompt'):
            row = record[caption]['caption']['char_captions'][0]
            record[caption]['caption']['char_captions'] = [copy.deepcopy(row) for _ in range(22)]
        snapshot = copy.deepcopy(record)
        result = m.pipe_from_record(record)
        self.assertEqual(len(result.characters), 10)
        self.assertEqual(result.characters[-1].uc, 'bad, hat')
        self.assertEqual(result.prompt, '(scene:2) tail')
        self.assertEqual(result.negative_prompt, 'blur, text')
        self.assertEqual(result.syntax, 'ComfyUI')
        self.assertEqual(record, snapshot)

    def test_native_nai_pipe_converts_at_encoding_without_mutating_input(self):
        d = importlib.import_module(package + '.detailer')
        native = c.CharacterPipe((c.Character('girl, -3::hat::', 'blur'),),
                                 '2::scene::, -1.5::text::', 'bad', 'NovelAI')
        prompt, negative, chars = d._prompts(native)
        self.assertEqual((prompt, negative), ('(scene:2)', 'bad, text'))
        self.assertEqual((chars[0].prompt, chars[0].uc), ('girl', 'blur, hat'))
        self.assertIn('-3::hat::', native.characters[0].prompt)

    def test_negative_magnitude_does_not_reach_local_clip(self):
        self.assertEqual(prompts.local_prompts('2::red hair:: blue eyes, -1.5::hat::', 'bad', '(blur:1.2)'),
                         ('(red hair:2) blue eyes', 'bad, hat, (blur:1.2)'))

    def test_sampler_normalizes_native_nai_scene_and_merges_receiver_negative_once(self):
        native = c.CharacterPipe((c.Character('girl, -2.5::hat::', 'blur'),),
                                 '2::cafe::, -3::text::', 'bad', 'NovelAI')
        local = p.sampling_pipe(native, 'ignored', 'local defect', 'ComfyUI')
        self.assertEqual((local.prompt, local.negative_prompt), ('(cafe:2)', 'bad, text, local defect'))
        self.assertEqual((local.characters[0].prompt, local.characters[0].uc), ('girl', 'blur, hat'))
        self.assertEqual(p.merge_negative(local.negative_prompt, local.characters[0].uc), 'bad, text, local defect, blur, hat')
        self.assertEqual(p.sampling_pipe(local, 'ignored', 'local defect', 'ComfyUI'), local)
        self.assertEqual(native.syntax, 'NovelAI')

    def test_bad_metadata_does_not_guess_character_coordinates(self):
        source = c.CharacterPipe((c.Character('girl'),), 'scene', 'bad', 'NovelAI')
        record = m.captions(source)
        record['v4_prompt']['use_coords'] = False
        with self.assertRaises(ValueError):
            m.pipe_from_record(record)

    def test_square_brackets_stay_literal_for_comfy_tokenizer(self):
        self.assertEqual(prompts.local_prompts(r'girl \[literal\], -2::hat::'), ('girl [literal]', 'hat'))

    def test_prompt_only_pipe_character_syntax_is_independent_of_receiver(self):
        incoming = c.CharacterPipe((c.Character('(hair:2)', 'hat'),), character_syntax='ComfyUI')
        result = p.sampling_pipe(incoming, '2::scene::', '-2::text::', 'NovelAI')
        self.assertEqual((result.prompt, result.negative_prompt), ('(scene:2)', 'text'))
        self.assertEqual(result.characters[0].prompt, '(hair:2)')
        manual = c.CharacterPipe((c.Character('2::hair::, -3::hat::'),))
        result = p.sampling_pipe(manual, '2::scene::', 'bad', 'NovelAI')
        self.assertEqual((result.characters[0].prompt, result.characters[0].uc), ('(hair:2)', 'hat'))
