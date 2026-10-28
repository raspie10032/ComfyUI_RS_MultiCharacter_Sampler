"""Reference ownership, CFG branches, and exception cleanup invariants."""
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
package = Path(__file__).resolve().parents[1].name
engine = importlib.import_module(package + '.anima_role_engine')
runtime = importlib.import_module(package + '.anima_role_kv')
routing = importlib.import_module(package + '.routing')
reference = importlib.import_module(package + '.image_reference')
builder = importlib.import_module(package + '.character_builder')


class RoleRoutingTests(unittest.TestCase):
    def test_exclusive_overlap_background_and_disabled_bank(self):
        masks = torch.tensor([[[1, 0, 1, 0]], [[0, 1, 1, 0.]]])
        groups = routing.token_groups(masks, 1, 4, boxes=True)
        # Uniform attention makes ownership numerically observable. Generated
        # values are zero; one-token reference A=2, reference B=6.
        q = k = torch.zeros(1, 4, 1, 1)
        v = torch.zeros_like(q)
        banks = [(torch.zeros(1, 1, 1, 1), torch.full((1, 1, 1, 1), n)) for n in (2., 6.)]
        actual = engine.regional_cached_attention(q, k, v, groups, None, banks, [1., 1.])
        torch.testing.assert_close(actual.flatten(), torch.tensor([2/5, 6/5, 8/6, 0.]))
        disabled = engine.regional_cached_attention(q, k, v, groups, None, banks, [0., 1.])
        torch.testing.assert_close(disabled.flatten(), torch.tensor([0., 6/5, 6/5, 0.]))
        # Skipping the dense all-zero target bias must preserve exact results.
        dense = engine.regional_cached_attention(q, k, v, groups, torch.zeros(4, 4), banks, [1., 1.])
        torch.testing.assert_close(actual, dense, rtol=0, atol=0)

    def test_point_regions_preserve_voronoi_partition(self):
        obj = object.__new__(engine.RegionalRoleEngine)
        obj.masks = torch.tensor([[[1., .7, .3, 0.]], [[0., .3, .7, 1.]]])
        obj.device = 'cpu'; obj.grid = None; obj.boxes = False
        obj.configure(0, 30, (1, 4), [2, 2], True)
        self.assertFalse(hasattr(obj.groups, 'cells'))
        self.assertEqual([g.tolist() for g in obj.groups], [[0, 1], [2, 3]])

    def test_cfg_keeps_reference_banks_out_of_negative(self):
        obj = object.__new__(runtime.RoleKVRuntime)
        obj.grid = (1, 1); obj.banks = object()
        obj.routing = SimpleNamespace(contexts=[torch.zeros(1, 3, 4)], sigmas=[1., 0.],
                                      audit={'cross_calls': 0, 'self_calls': 0})
        seen = []
        obj.engine = SimpleNamespace(configure=lambda *args: None, net=SimpleNamespace(blocks=[0]))
        def velocity(x, timestep, context, banks):
            seen.append(banks)
            return x
        obj.engine.velocity = velocity
        with patch.object(runtime, 'check_interrupted'):
            obj.forward(None, torch.zeros(2, 16, 1, 2, 2), torch.ones(2), torch.zeros(2, 3, 4),
                        transformer_options={'cond_or_uncond': [0, 1], 'sigmas': [1.]})
        self.assertIs(seen[0], obj.banks)
        self.assertIsNone(seen[1])

    def test_exception_restores_model_forward_and_releases_caches(self):
        obj = object.__new__(runtime.RoleKVRuntime)
        original = lambda *args: None
        obj.net = SimpleNamespace(_forward=original)
        obj.audit = {}; obj.engine = object(); obj.banks = object(); obj.grid = (2, 2)
        obj.latents = {0: object()}
        with self.assertRaisesRegex(RuntimeError, 'interrupted'):
            with obj.sampling():
                self.assertIs(obj.net._forward, original)
                raise RuntimeError('interrupted')
        self.assertIs(obj.net._forward, original)
        self.assertIsNone(obj.engine); self.assertIsNone(obj.banks)
        self.assertIsNone(obj.grid); self.assertEqual(obj.latents, {})
        self.assertTrue(obj.audit['cache_released'])

    def test_role_method_does_not_change_old_widget_order_or_disabled_input(self):
        schema = reference.RSMultiCharacterReference.INPUT_TYPES()
        self.assertEqual(list(schema['required']), ['image', 'character_id', 'resolution', 'strength', 'enabled'])
        self.assertEqual(schema['optional']['anima_method'][1]['default'], 'reference_frame')
        p = builder.update_slot(None, 1, prompt='adult woman')
        p = reference.RSMultiCharacterReference().apply(torch.zeros(1, 64, 64, 3), building_pipe=p, anima_method='role_kv')[0]
        self.assertIsInstance(p.slots[0].reference, reference.RoleKVImageReference)
        p = reference.RSMultiCharacterReference().apply(None, building_pipe=p, anima_method='role_kv', enabled=False)[0]
        self.assertIsNone(p.slots[0].reference)
        self.assertEqual(p.slots[0].prompt, 'adult woman')


if __name__ == '__main__':
    unittest.main()
