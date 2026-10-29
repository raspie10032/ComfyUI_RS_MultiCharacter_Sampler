"""Expanded Anima adapter mapping and automatic variant selection, CPU only."""
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import Mock, patch

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
PKG = Path(__file__).resolve().parents[1].name
ref = importlib.import_module(PKG + '.anima_ref_frame')
assets = importlib.import_module(PKG + '.reference_assets')
PARTS = ('self_attn.q_proj', 'self_attn.k_proj', 'self_attn.v_proj', 'self_attn.output_proj',
         'cross_attn.q_proj', 'cross_attn.k_proj', 'cross_attn.v_proj', 'cross_attn.output_proj',
         'mlp.layer1', 'mlp.layer2')
INSERTED = {2, 5, 8, 11, 14, 17, 21, 24, 27, 30, 33, 36}


def network(count):
    net = torch.nn.Module()
    net.blocks = torch.nn.ModuleList()
    for _ in range(count):
        block = torch.nn.Module()
        for part in PARTS:
            group, member = part.split('.')
            if not hasattr(block, group):
                setattr(block, group, torch.nn.Module())
            getattr(block, group).add_module(member, torch.nn.Linear(3, 3, bias=False))
        net.blocks.append(block)
    return net


def weights(blocks):
    result = {}
    for block in blocks:
        for part in PARTS:
            stem = f'diffusion_model.blocks.{block}.{part}'
            result[stem + '.lora_down.weight'] = torch.ones(2, 3)
            result[stem + '.lora_up.weight'] = torch.ones(3, 2)
            result[stem + '.alpha'] = torch.tensor(2.)
    return result


class Anima29Reference(unittest.TestCase):
    def runtime(self):
        return ref.FrameRuntime(ref.ReferencePlan(None, 'unused', 1., 4.5, 'apg', False),
                                torch.zeros(1, 16, 1, 2, 2), {})

    def load(self, runtime, net, state):
        # Only file I/O is mocked. Mapping, tensor validation and hooks are real.
        utils = SimpleNamespace(load_torch_file=Mock(return_value=state))
        comfy = sys.modules.get('comfy', ModuleType('comfy'))
        with patch.dict(sys.modules, {'comfy': comfy, 'comfy.utils': utils}), \
                patch.object(comfy, 'utils', utils, create=True):
            runtime.load_weights(net)

    def test_28_and_40_block_coverage(self):
        for count in (28, 40):
            with self.subTest(count=count):
                rt = self.runtime()
                mapped = set(range(count)) - (INSERTED if count == 40 else set())
                self.load(rt, network(count), weights(mapped))
                self.assertEqual(len(rt.weights), 280)
                self.assertEqual(rt.audit['adapter_blocks'], 28)
                self.assertEqual(rt.audit['unchanged_new_blocks'], sorted(set(range(count)) - mapped))

    def test_wrong_variant_missing_layer_and_nonfinite_rejected(self):
        good = weights(set(range(40)) - INSERTED)
        missing = dict(good)
        del missing[next(k for k in missing if k.endswith('lora_down.weight'))]
        nonfinite = {k: v.clone() for k, v in good.items()}
        next(v for k, v in nonfinite.items() if k.endswith('lora_up.weight'))[0, 0] = float('nan')
        for state in (weights(range(28)), missing, nonfinite):
            rt = self.runtime()
            with self.assertRaises(ValueError):
                self.load(rt, network(40), state)
            self.assertIsNone(rt.weights)

    def test_base_rejects_expanded_adapter_and_unknown_depth_reads_no_weights(self):
        with self.assertRaises(ValueError):
            self.load(self.runtime(), network(28), weights(set(range(40)) - INSERTED))
        with self.assertRaisesRegex(ValueError, '28 blocks'):
            self.runtime().load_weights(network(29))

    def test_invalid_rank_dimensions_and_alpha_leave_no_partial_state(self):
        good = weights(set(range(40)) - INSERTED)
        stem = 'diffusion_model.blocks.0.self_attn.q_proj.'
        corruptions = (
            {'lora_down.weight': torch.zeros(0, 3), 'lora_up.weight': torch.zeros(3, 0)},
            {'lora_down.weight': torch.ones(2, 4)},
            {'lora_down.weight': torch.ones(2, 3, dtype=torch.int8)},
            {'alpha': torch.tensor(float('inf'))},
            {'alpha': torch.tensor([1., 2.])},
        )
        for change in corruptions:
            with self.subTest(change=list(change)):
                rt = self.runtime()
                net = network(40)
                state = {**good, **{stem + key: value for key, value in change.items()}}
                with self.assertRaises(ValueError):
                    self.load(rt, net, state)
                self.assertIsNone(rt.weights)
                self.assertFalse(any(m._forward_hooks for m in net.modules()))

    def test_inserted_blocks_untouched_and_failure_cleans_hooks(self):
        rt = self.runtime()
        net = network(40)
        self.load(rt, net, weights(set(range(40)) - INSERTED))
        value = torch.ones(1, 3)
        plain = net.blocks[2].self_attn.q_proj(value)
        trained = net.blocks[0].self_attn.q_proj(value)
        with self.assertRaisesRegex(RuntimeError, 'cancel'):
            with rt.installed(net, torch.zeros(1, 2, 3), True):
                self.assertTrue(torch.equal(plain, net.blocks[2].self_attn.q_proj(value)))
                self.assertTrue(torch.equal(trained + 6, net.blocks[0].self_attn.q_proj(value)))
                raise RuntimeError('cancel')
        self.assertFalse(any(m._forward_hooks for m in net.modules()))
        self.assertTrue(torch.equal(trained, net.blocks[0].self_attn.q_proj(value)))

    def test_automatic_selection_and_unknown_architecture(self):
        for count, key in ((28, 'anima_frame'), (40, 'anima29_frame')):
            model = SimpleNamespace(get_model_object=lambda name: SimpleNamespace(blocks=[None] * count))
            with patch.object(assets, '_verified_adapter', return_value='selected') as resolver:
                self.assertEqual(assets.frame_adapter(model, 'node7'), 'selected')
                resolver.assert_called_once_with(key, 'node7')
        model = SimpleNamespace(get_model_object=lambda name: SimpleNamespace(blocks=[None] * 29))
        with patch.object(assets, '_verified_adapter') as resolver, self.assertRaises(ValueError):
            assets.frame_adapter(model)
        resolver.assert_not_called()


if __name__ == '__main__':
    unittest.main()
