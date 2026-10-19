"""Numerical regressions for the explicit experimental shared-layer backend."""
import importlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch
import torch.nn.functional as F

PKG = Path(__file__).resolve().parents[1].name
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@unittest.skipUnless(os.environ.get('RS_MC_TEST_COMFYUI'), 'Requires native ComfyUI')
class SharedLoraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.environ['RS_MC_TEST_COMFYUI'])
        from comfy.cli_args import args
        args.cpu = True
        cls.s = importlib.import_module(PKG + '.shared_lora')
        cls.b = importlib.import_module(PKG + '.lora_bypass')
        from comfy.weight_adapter.lora import LoRAAdapter
        cls.adapter_type = LoRAAdapter

    def setUp(self):
        torch.manual_seed(14)
        self.shared = self.s.SharedRegionalLora.__new__(self.s.SharedRegionalLora)
        self.shared.mask_cache = {}
        self.shared.audit = {'base_layer_calls': 0, 'adapter_calls': 0}
        self.up, self.down = torch.randn(8, 2) * .2, torch.randn(2, 8) * .2
        self.adapter = self.adapter_type(set(), (self.up, self.down, 2., None, None, None))
        self.adapter.multiplier = 1.
        self.adapter.is_conv = False
        self.mask = torch.tensor([[1., 1., 0., 0.], [1., 1., 0., 0.]])
        self.strengths = [1., 0.]

    def test_semantic_roles_reject_unknown_even_if_shape_matches(self):
        for name in ('self_attn.q_proj', 'self_attn.k_proj', 'cross_attn.q_proj', 'cross_attn.output_proj', 'mlp.layer1', 'mlp.layer2'):
            self.assertEqual(self.s.layer_role('blocks.2.' + name), 'image')
        for name in ('k_proj', 'v_proj'):
            self.assertEqual(self.s.layer_role('blocks.2.cross_attn.' + name), 'text')
        for name in ('llm_adapter.blocks.2.mlp.0', 't_embedder.1.linear_1', 'blocks.1.adaln_modulation_mlp.1'):
            with self.assertRaises(ValueError):
                self.s.layer_role(name)

    def test_image_delta_is_spatial_and_base_is_called_once(self):
        layer = torch.nn.Linear(8, 8)
        x = torch.randn(2, 8, 8)
        calls = []
        def original(x):
            calls.append(1)
            return layer(x)
        got = self.shared.layer_forward(original, [(self.adapter, self.mask, self.strengths)], 'image', (2, 4), [2, 3, 3], x)
        delta = F.linear(F.linear(x, self.down), self.up)
        expected = layer(x) + delta * self.mask.flatten()[None, :, None]
        torch.testing.assert_close(got, expected)
        self.assertEqual(len(calls), 1)
        torch.testing.assert_close(got[:, [2, 3, 6, 7]], layer(x)[:, [2, 3, 6, 7]], rtol=0, atol=0)

    def test_five_dimensional_mlp_and_fractional_negative_strength(self):
        layer = torch.nn.Linear(8, 8)
        x = torch.randn(2, 1, 2, 4, 8)
        mask = self.mask * -.7
        got = self.shared.layer_forward(layer, [(self.adapter, mask, [-.7, 0.])], 'image', (2, 4), [2, 3, 3], x)
        torch.testing.assert_close(got, layer(x) + F.linear(F.linear(x, self.down), self.up) * mask[None, None, :, :, None])

    def test_caption_length_equal_to_image_tokens_does_not_use_image_mask(self):
        layer = torch.nn.Linear(8, 8)
        x = torch.randn(2, 8, 8)
        got = self.shared.layer_forward(layer, [(self.adapter, self.mask, [1., 0.])], 'text', (2, 4), [2, 3, 3], x)
        weights = x.new_tensor([.5, .5, 1., 1., 1., 0., 0., 0.])
        torch.testing.assert_close(got, layer(x) + F.linear(F.linear(x, self.down), self.up) * weights[None, :, None])

    def test_two_adapters_share_base_and_zero_preserves_output(self):
        layer = torch.nn.Linear(8, 8)
        x = torch.randn(1, 8, 8)
        inverse = 1 - self.mask
        got = self.shared.layer_forward(layer, [(self.adapter, self.mask, [1., 0.]), (self.adapter, inverse, [0., 1.])], 'image', (2, 4), [2, 3, 3], x)
        torch.testing.assert_close(got, layer(x) + F.linear(F.linear(x, self.down), self.up))
        self.assertEqual(self.shared.audit['base_layer_calls'], 1)
        zero = torch.zeros_like(self.mask)
        got = self.shared.layer_forward(layer, [(self.adapter, zero, [0., 0.])], 'image', (2, 4), [2, 3, 3], x)
        torch.testing.assert_close(got, layer(x), rtol=0, atol=0)

    def test_actual_runtime_delegate_and_failure_restore_exact_attributes(self):
        from comfy import ops
        module = ops.manual_cast.Linear(8, 8)
        with torch.no_grad():
            module.weight.normal_(std=.2)
            module.bias.normal_(std=.1)
        self.adapter.rs_mc_full_shape = (8, 8)
        runtime = torch.nn.Module()
        block = torch.nn.Module()
        block.mlp = torch.nn.Module()
        block.mlp.layer1 = module
        runtime.blocks = torch.nn.ModuleList([block])
        plan = SimpleNamespace(layer_paths=['blocks.0.mlp.layer1'], layers=[(None, self.adapter, self.adapter.weights)])
        self.shared.entries = [(plan, self.mask, [1., 0.])]
        x = torch.randn(1, 8, 8)
        before = module(x)
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            with self.shared.installed(runtime, (2, 4), [2, 3, 3]):
                self.assertFalse(torch.equal(module(x), before))
                raise RuntimeError('cancelled')
        torch.testing.assert_close(module(x), before, rtol=0, atol=0)
        self.assertNotIn('forward', module.__dict__)
        self.assertNotIn('comfy_force_forward', module.__dict__)
        self.assertEqual(self.shared.audit['base_layer_calls'], 1)

    def test_cleanup_releases_factors_and_masks_on_failure(self):
        released = []
        self.shared.entries = [(SimpleNamespace(release=lambda: released.append(True)), self.mask, [1., 0.])]
        self.shared.mask_cache['test'] = torch.ones(2)
        def fail():
            raise RuntimeError('cancelled')
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            self.shared.sample(fail)
        self.assertEqual(released, [True])
        self.assertFalse(self.shared.mask_cache)

    def test_sdxl_roles_use_architecture_not_shapes(self):
        for prefix in ['input_blocks.4.1', 'middle_block.1', 'output_blocks.2.1']:
            for name in ['attn2.to_k', 'attn2.to_v']:
                self.assertEqual(self.s.layer_role(prefix + '.transformer_blocks.0.' + name), 'text')
            for name in ['attn1.to_k', 'attn2.to_q', 'attn2.to_out.0', 'ff.net.0.proj', 'ff.net.2']:
                self.assertEqual(self.s.layer_role(prefix + '.transformer_blocks.0.' + name), 'image')
            self.assertEqual(self.s.layer_role(prefix + '.proj_in'), 'image')
        with self.assertRaises(ValueError):
            self.s.layer_role('input_blocks.4.0.emb_layers.1')

    def test_sdxl_multi_resolution_image_deltas(self):
        layer = torch.nn.Linear(8, 8)
        x = torch.randn(2, 2, 8)
        got = self.shared.sdxl_layer_forward(layer, [(self.adapter, self.mask, [1., 0.])], 'image', (2, 4), [2, 3, 3], x)
        delta = F.linear(F.linear(x, self.down), self.up)
        torch.testing.assert_close(got, layer(x) + delta * x.new_tensor([1., 0.])[None, :, None])

    def test_sdxl_caption_tokens_never_use_spatial_shape(self):
        layer = torch.nn.Linear(8, 8)
        x = torch.randn(2, 8, 8)
        got = self.shared.sdxl_layer_forward(layer, [(self.adapter, self.mask, [1., 0.])], 'text', (2, 4), [2, 3, 3], x)
        expected = layer(x) + F.linear(F.linear(x, self.down), self.up) * x.new_tensor([.5, .5, 1., 1., 1., 0., 0., 0.])[None, :, None]
        torch.testing.assert_close(got, expected)
