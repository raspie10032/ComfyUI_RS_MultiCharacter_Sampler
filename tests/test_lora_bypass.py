"""Native factor-only execution, fallback and restoration regressions (CPU)."""
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
class BypassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.environ['RS_MC_TEST_COMFYUI'])
        from comfy.cli_args import args
        args.cpu = True
        from comfy import model_base
        if not hasattr(model_base, 'Anima'):
            raise unittest.SkipTest('This core predates Anima')
        try:
            from comfy.weight_adapter.lora import LoRAAdapter
        except ImportError:
            raise unittest.SkipTest('This core predates native bypass')
        cls.adapter_type = LoRAAdapter
        cls.base_type = model_base.Anima
        cls.bypass = importlib.import_module(PKG + '.lora_bypass')

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(os.environ['RS_MC_TEST_COMFYUI'])

    def setUp(self):
        from comfy import ops
        torch.manual_seed(739)
        base = self.base_type.__new__(self.base_type)
        torch.nn.Module.__init__(base)
        base.diffusion_model = torch.nn.Sequential(ops.manual_cast.Linear(8, 8, bias=True))
        self.layer = base.diffusion_model[0]
        with torch.no_grad():
            self.layer.weight.normal_(std=.2)
            self.layer.bias.normal_(std=.1)
        self.model = SimpleNamespace(model=base)
        self.up, self.down = torch.randn(8, 2)*.2, torch.randn(2, 8)*.2
        self.adapter = self.adapter_type(set(), (self.up, self.down, 1., None, None, None))
        self.weights = {'diffusion_model.0.weight': self.adapter}
        self.x = torch.randn(2, 5, 8)

    def plan(self):
        plan, reason = self.bypass.prepare_bypass(self.model, self.weights)
        self.assertEqual(reason, 'plain_linear_lora')
        self.assertIsNotNone(plan)
        return plan

    def test_matches_merged_fp32_positive_negative_and_zero_strength(self):
        plan = self.plan()
        original = self.layer.weight.detach().clone()
        base = self.layer(self.x)
        for strength in (.7, -1.2, 0.):
            expected = F.linear(self.x, original + (self.up @ self.down)*(.5*strength), self.layer.bias)
            result = plan.forward(self.layer, self.x, strength=strength)
            torch.testing.assert_close(result, expected, atol=1e-6, rtol=1e-5)
        self.assertTrue(torch.equal(original, self.layer.weight))
        self.assertTrue(torch.equal(base, self.layer(self.x)))
        self.assertNotIn('forward', self.layer.__dict__)
        self.assertNotIn('comfy_force_forward', self.layer.__dict__)

    def test_scope_has_no_weight_patches_and_shares_factors_across_strengths(self):
        from comfy.hooks import EnumHookType, EnumHookScope
        plan = self.plan()
        a, b = plan.hook_group(.5), plan.hook_group(1.)
        self.assertFalse(a.get_type(EnumHookType.Weight))
        self.assertEqual(a.hooks[0].hook_scope, EnumHookScope.HookedOnly)
        self.assertIs(plan.layers[0][1].weights, self.adapter.weights)
        self.assertEqual(plan.factor_bytes, (self.up.numel()+self.down.numel())*4)
        self.assertIsNot(a, b)

    def test_forward_failure_and_partial_injection_restore_exact_attributes(self):
        plan = self.plan()
        original = self.layer.forward
        self.layer.forward = original
        self.layer.comfy_force_forward = False
        def fail(*args): raise RuntimeError('deliberate failure')
        with self.assertRaisesRegex(RuntimeError, 'deliberate failure'):
            plan.forward(fail, self.x, strength=1.)
        self.assertIs(self.layer.forward, original)
        self.assertFalse(self.layer.comfy_force_forward)
        native_inject = plan.hook_type.inject
        def inject_then_fail(hook):
            native_inject(hook)
            raise RuntimeError('partial injection')
        with patch.object(plan.hook_type, 'inject', inject_then_fail):
            with self.assertRaisesRegex(RuntimeError, 'partial injection'):
                plan.forward(self.layer, self.x, strength=1.)
        self.assertIs(self.layer.forward, original)
        self.assertFalse(self.layer.comfy_force_forward)

    def test_cleanup_releases_converted_storage_even_on_failure(self):
        r = importlib.import_module(PKG + '.regional_lora')
        plan = self.plan()
        runtime = r.RegionalLoras.__new__(r.RegionalLoras)
        runtime.bypasses = {'same-file': (plan, 'plain_linear_lora')}
        plan.layers[0][1].weights = tuple(v.clone() if isinstance(v, torch.Tensor) else v for v in self.adapter.weights)
        def fail(): raise RuntimeError('cancelled')
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            runtime.sample(fail)
        self.assertIs(plan.layers[0][1].weights, self.adapter.weights)

    def test_fallback_is_all_or_nothing_for_extended_or_malformed_patches(self):
        cases = [
            {'diffusion_model.0.weight': ('diff', (torch.ones(8, 8),))},
            {'diffusion_model.0.weight': self.adapter_type(set(), (self.up,self.down,1.,None,torch.ones(8),None))},
            {'diffusion_model.0.weight': self.adapter_type(set(), (self.up,self.down,1.,torch.ones(2,2),None,None))},
            {'diffusion_model.0.weight': self.adapter_type(set(), (self.up,torch.ones(2,7),1.,None,None,None))},
            {**self.weights, 'diffusion_model.0.bias': ('diff', (torch.ones(8),))},
            {('diffusion_model.0.weight', (0,0,2)): self.adapter},
        ]
        for weights in cases:
            plan, reason = self.bypass.prepare_bypass(self.model, weights)
            self.assertIsNone(plan)
            self.assertNotEqual(reason, 'plain_linear_lora')

    def test_non_anima_multigpu_and_custom_dispatch_use_weight_hooks(self):
        self.assertIsNone(self.bypass.prepare_bypass(SimpleNamespace(model=torch.nn.Linear(8,8)),self.weights)[0])
        with patch.object(self.model, 'get_additional_models_with_key', return_value=[object()], create=True):
            self.assertEqual(self.bypass.prepare_bypass(self.model,self.weights)[1], 'multigpu_clones')
        self.layer.comfy_force_forward = True
        self.assertEqual(self.bypass.prepare_bypass(self.model,self.weights)[1], 'custom_or_quantized_layer')

