"""Model selection must not route an unknown architecture into a known loader."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('rs_test_app_catalog', Path(__file__).resolve().parents[1]/'app_catalog.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class AppCatalogTests(unittest.TestCase):
    def test_anima_block_count_and_prefix(self):
        for count, expected in [(28, 'anima'), (40, 'anima29'), (32, None)]:
            with self.subTest(count=count):
                header = {'model.diffusion_model.llm_adapter.blocks.0.cross_attn.q_proj.weight': {}}
                header.update({f'model.diffusion_model.blocks.{i}.weight': {} for i in range(count)})
                self.assertEqual(catalog.classify(header), expected)

    def test_flux_dimensions_and_variant(self):
        for dim, expected in [(3072, 'klein4_base'), (4096, 'klein9_base'), (6144, 'flux2_dev'), (1024, None)]:
            with self.subTest(dim=dim):
                h = {'double_blocks.0.img_attn.norm.key_norm.scale': {},
                     'double_stream_modulation_img.lin.weight': {}, 'img_in.weight': {'shape': [dim, 128]}}
                self.assertEqual(catalog.classify(h, 'model-base.safetensors'), expected)

    def test_checkpoint_context_width_and_unknown(self):
        for width, expected in [(768, 'sd15'), (2048, 'sdxl'), (1024, None)]:
            h = {'input_blocks.0.0.weight': {}, 'input_blocks.1.attn2.to_k.weight': {'shape': [320, width]}}
            self.assertEqual(catalog.classify(h), expected)
        self.assertIsNone(catalog.classify({'input_blocks.0.0.weight': 'invalid tensor'}, 'anima.safetensors'))

    def test_header_only_and_invalid_length(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'model.safetensors'
            header = {'tensor': {'shape': [1]}, '__metadata__': {'note': 'kept'}}
            data = json.dumps(header).encode()
            p.write_bytes(struct.pack('<Q', len(data)) + data + b'payload')
            self.assertEqual(catalog._header(str(p), p.stat().st_size, p.stat().st_mtime_ns), header)
            p.write_bytes(struct.pack('<Q', 2**40))
            with self.assertRaises(ValueError):
                catalog._header(str(p), p.stat().st_size, p.stat().st_mtime_ns)

    def test_pose_capability_routes_and_combination_gates(self):
        self.assertEqual(catalog.capabilities('anima')['pose'], 'lllite')
        self.assertIsNone(catalog.capabilities('anima29')['pose'])
        for profile in ['krea2', 'moss']:
            cap = catalog.capabilities(profile)
            self.assertEqual(cap['pose'], 'scene_adapter')
            self.assertFalse(cap['pose_reference'])
            self.assertFalse(cap['pose_progressive'])


if __name__ == '__main__':
    unittest.main()
