import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
package = importlib.import_module(Path(__file__).resolve().parents[1].name)
r = importlib.import_module(package.__name__ + '.image_reference')
b = importlib.import_module(package.__name__ + '.character_builder')
m = importlib.import_module(package.__name__ + '.metadata')
size = importlib.import_module(package.__name__ + '.reference_image')


class ReferenceTests(unittest.TestCase):
    def test_long_edge_all_choices_keep_ratio_without_crop(self):
        from PIL import Image
        for resolution in range(64, 1025, 64):
            fitted, _ = size.prepare_reference(Image.new('RGB', (1200, 800)), resolution, square_padding=False)
            self.assertEqual(fitted.width, resolution)
            self.assertAlmostEqual(fitted.height / resolution, 2/3, delta=1/resolution)
        for bad in (0, 63, 65, 1088, True, 384.0):
            with self.assertRaises(ValueError):
                size.validate_reference_size(bad)

    def test_order_independent_and_off_only_clears_reference(self):
        image = torch.ones(1, 80, 120, 3)
        a = r.RSMultiCharacterReference().apply(image, character_id=1, resolution=320)[0]
        a = b.update_slot(a, 1, prompt='adult woman', x=.25)
        other = b.update_slot(None, 1, prompt='adult woman', x=.25)
        other = r.RSMultiCharacterReference().apply(image, character_id=1, resolution=320, building_pipe=other)[0]
        self.assertEqual(a.slots[0].reference, other.slots[0].reference)
        self.assertEqual(a.slots[0].reference.size, (320, 213))
        off = r.RSMultiCharacterReference().apply(None, enabled=False, building_pipe=a)[0]
        self.assertIsNone(off.slots[0].reference)
        self.assertEqual(off.slots[0].prompt, 'adult woman')
        self.assertEqual(off.slots[0].x, .25)

    def test_no_references_returns_before_optional_imports(self):
        model = object()
        pipe = SimpleNamespace(characters=(SimpleNamespace(reference=None),))
        with patch.dict(sys.modules, {'transformers': None, 'comfy': None}):
            self.assertIs(r.prepare_model_references(model, None, None, pipe, 'Anima'), model)

    def test_finalize_excludes_reference_above_prompt_count(self):
        image = torch.ones(1, 32, 32, 3)
        pipe = r.RSMultiCharacterReference().apply(image, character_id=2)[0]
        pipe = b.update_slot(pipe, 1, prompt='adult woman')
        pipe = b.replace(pipe, prompt_count=1)
        result = b.finalize(pipe)
        self.assertEqual(len(result.characters), 1)
        self.assertIsNone(result.characters[0].reference)

    def test_zero_needs_no_image_and_metadata_does_not_embed_pixels(self):
        pipe = r.RSMultiCharacterReference().apply(None, strength=0)[0]
        self.assertIsNone(pipe.slots[0].reference)
        pipe = r.RSMultiCharacterReference().apply(torch.ones(1, 32, 32, 3))[0]
        pipe = b.update_slot(pipe, 1, prompt='adult woman')
        pipe = b.replace(pipe, prompt_count=1)
        pipe = b.finalize(pipe)
        settings = dict(width=512, height=512, seed=1, steps=30, cfg=4,
                        sampler_name='euler_ancestral', scheduler='sgm_uniform')
        record = m.build_record(pipe, settings, {}, [[.5,.5]], {'spatial_slots':1})
        description = record['rs_multicharacter']['image_references'][0]
        self.assertEqual(description['resolution'], 384)
        self.assertEqual(description['character_id'], 1)
        self.assertTrue(description['source'].startswith('sha256:'))
        self.assertNotIn('pixels', json.dumps(record))
        restored = m.pipe_from_record(record)
        self.assertIsNone(restored.characters[0].reference)

    def test_cached_assets_reused_without_download_dependencies(self):
        a = importlib.import_module(package.__name__ + '.reference_assets')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'ipadapter'/'cache'/'google--siglip-so400m-patch14-384'/'model.safetensors'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'not loaded by this path test')
            host = SimpleNamespace(models_dir=directory, folder_names_and_paths={})
            a.asset.cache_clear()
            with patch.dict(sys.modules, {'folder_paths':host, 'huggingface_hub':None}):
                self.assertEqual(a.asset('redux_encoder'), target)
            a.asset.cache_clear()

    def test_invalid_images_and_controls_are_rejected(self):
        for strength in (float('nan'), -1, 3, True):
            with self.assertRaises(ValueError):
                r.RSMultiCharacterReference().apply(None, strength=strength)
        for image in (None, torch.zeros(2, 32, 32, 3), torch.zeros(1, 32, 32, 1)):
            with self.assertRaises(ValueError):
                r.RSMultiCharacterReference().apply(image)


if __name__ == '__main__':
    unittest.main()
