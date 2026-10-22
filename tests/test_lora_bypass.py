"""Native factor-only execution, fallback and restoration regressions (CPU)."""
import importlib
import copy
from functools import partial
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

    def test_flux_fused_output_and_input_offsets_match_merged_factors(self):
        from comfy import model_base
        base = model_base.Flux2.__new__(model_base.Flux2)
        torch.nn.Module.__init__(base)
        base.diffusion_model = copy.deepcopy(self.model.model.diffusion_model)
        original = base.diffusion_model[0].weight.detach().clone()
        weights = {}
        expected_weight = original.clone()
        for start in (0, 4):
            up = torch.randn(4, 2) * .2
            weights[('diffusion_model.0.weight', (0, start, 4))] = self.adapter_type(set(), (up, self.down, 1., None, None, None))
            expected_weight[start:start+4] += up @ self.down * .5
        plan, reason = self.bypass.prepare_bypass(SimpleNamespace(model=base), weights)
        self.assertEqual(reason, 'plain_linear_lora')
        expected = F.linear(self.x, expected_weight, base.diffusion_model[0].bias)
        torch.testing.assert_close(self.run_plan(plan, 1., base.diffusion_model), expected)
        self.assertTrue(torch.equal(original, base.diffusion_model[0].weight))
        self.assertNotIn('forward', base.diffusion_model[0].__dict__)
        down = torch.randn(2, 4) * .2
        weights = {('diffusion_model.0.weight', (1, 2, 4)): self.adapter_type(set(), (self.up, down, 1., None, None, None))}
        plan, reason = self.bypass.prepare_bypass(SimpleNamespace(model=base), weights)
        self.assertEqual(reason, 'plain_linear_lora')
        expected_weight = original.clone()
        expected_weight[:, 2:6] += self.up @ down * .5
        expected = F.linear(self.x, expected_weight, base.diffusion_model[0].bias)
        torch.testing.assert_close(self.run_plan(plan, 1., base.diffusion_model), expected)

    def run_plan(self, plan, strength, runtime=None, call=None):
        from comfy.patcher_extension import WrapperExecutor
        runtime = self.model.model.diffusion_model if runtime is None else runtime
        executor = WrapperExecutor.new_class_executor(
            runtime.forward if call is None else call, runtime,
            [partial(plan.forward, strength=strength)])
        return executor.execute(self.x)

    def test_matches_merged_fp32_positive_negative_and_zero_strength(self):
        plan = self.plan()
        original = self.layer.weight.detach().clone()
        base = self.layer(self.x)
        for strength in (.7, -1.2, 0.):
            expected = F.linear(self.x, original + (self.up @ self.down)*(.5*strength), self.layer.bias)
            result = self.run_plan(plan, strength)
            torch.testing.assert_close(result, expected, atol=1e-6, rtol=1e-5)
        self.assertTrue(torch.equal(original, self.layer.weight))
        self.assertTrue(torch.equal(base, self.layer(self.x)))
        self.assertNotIn('forward', self.layer.__dict__)
        self.assertNotIn('comfy_force_forward', self.layer.__dict__)

    def test_inference_delegate_receives_lora_instead_of_original_modules(self):
        # Dynamic VRAM switches models after LoRA preparation. Counting wrapper
        # calls alone passed the old implementation while the actual model was
        # untouched. Verify the delegate's numerical result and both restorations.
        plan = self.plan()
        runtime = copy.deepcopy(self.model.model.diffusion_model)
        base = runtime(self.x)
        expected = F.linear(self.x, runtime[0].weight + (self.up @ self.down)*.5,
                            runtime[0].bias)
        result = self.run_plan(plan, 1., runtime)
        self.assertFalse(torch.equal(base, result))
        torch.testing.assert_close(result, expected, atol=1e-6, rtol=1e-5)
        self.assertTrue(torch.equal(base, runtime(self.x)))
        self.assertTrue(torch.equal(base, self.model.model.diffusion_model(self.x)))
        for layer in (self.layer, runtime[0]):
            self.assertNotIn('forward', layer.__dict__)
            self.assertNotIn('comfy_force_forward', layer.__dict__)

    def test_delegate_failure_restores_actual_runtime_and_zero_is_identity(self):
        plan = self.plan()
        runtime = copy.deepcopy(self.model.model.diffusion_model)
        base = runtime(self.x)
        self.assertTrue(torch.equal(base, self.run_plan(plan, 0., runtime)))
        def fail(*args):
            self.assertIn('forward', runtime[0].__dict__)
            self.assertNotIn('forward', self.layer.__dict__)
            raise RuntimeError('delegate failure')
        with self.assertRaisesRegex(RuntimeError, 'delegate failure'):
            self.run_plan(plan, 1., runtime, fail)
        self.assertTrue(torch.equal(base, runtime(self.x)))
        self.assertNotIn('forward', runtime[0].__dict__)
        self.assertNotIn('comfy_force_forward', runtime[0].__dict__)

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
            self.run_plan(plan, 1., call=fail)
        self.assertIs(self.layer.forward, original)
        self.assertFalse(self.layer.comfy_force_forward)
        native_inject = plan.hook_type.inject
        def inject_then_fail(hook):
            native_inject(hook)
            raise RuntimeError('partial injection')
        with patch.object(plan.hook_type, 'inject', inject_then_fail):
            with self.assertRaisesRegex(RuntimeError, 'partial injection'):
                self.run_plan(plan, 1.)
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
            plan, reason = self.bypass._prepare_factor_bypass(self.model, weights)
            self.assertIsNone(plan)
            self.assertNotEqual(reason, 'plain_linear_lora')

    def test_non_anima_multigpu_and_custom_dispatch_use_weight_hooks(self):
        self.assertIsNone(self.bypass.prepare_bypass(SimpleNamespace(model=torch.nn.Linear(8,8)),self.weights)[0])
        with patch.object(self.model, 'get_additional_models_with_key', return_value=[object()], create=True):
            self.assertEqual(self.bypass.prepare_bypass(self.model,self.weights)[1], 'multigpu_clones')
        self.layer.comfy_force_forward = True
        self.assertTrue(self.bypass.prepare_bypass(self.model,self.weights)[1].startswith('custom_or_unsupported_layer:'))

    def test_flux_and_krea2_fp8_bypass_changes_output_and_preserves_base_weight(self):
        from comfy import model_base
        for family in (model_base.Flux, model_base.Flux2, model_base.Flux3, *([model_base.Krea2] if hasattr(model_base, "Krea2") else [])):
            base = family.__new__(family)
            torch.nn.Module.__init__(base)
            base.diffusion_model = copy.deepcopy(self.model.model.diffusion_model)
            layer = base.diffusion_model[0]
            layer.weight = torch.nn.Parameter(layer.weight.to(torch.float8_e4m3fn), requires_grad=False)
            model = SimpleNamespace(model=base)
            plan, reason = self.bypass.prepare_bypass(model, self.weights)
            self.assertEqual(reason, 'plain_linear_lora')
            original = layer.weight.detach().clone()
            before = base.diffusion_model(self.x)
            expected = before + F.linear(F.linear(self.x, self.down), self.up) * .5
            result = self.run_plan(plan, 1., base.diffusion_model)
            torch.testing.assert_close(result, expected)
            self.assertTrue(torch.equal(original.float(), layer.weight.float()))
            self.assertTrue(torch.equal(before, base.diffusion_model(self.x)))

    def test_flux_native_int8_tensor_is_accepted_without_scale_attributes(self):
        from comfy import model_base
        from comfy import ops
        from comfy.quant_ops import QuantizedTensor
        base = model_base.Flux2.__new__(model_base.Flux2)
        torch.nn.Module.__init__(base)
        layer = ops.mixed_precision_ops({}, compute_dtype=torch.float32).Linear(8, 8)
        layer.bias = torch.nn.Parameter(self.layer.bias.detach().clone())
        base.diffusion_model = torch.nn.Sequential(layer)
        layer = base.diffusion_model[0]
        quantized = QuantizedTensor.from_float(self.layer.weight.detach(), 'TensorWiseINT8Layout')
        layer.weight = torch.nn.Parameter(quantized, requires_grad=False)
        self.assertFalse(hasattr(layer, 'weight_scale'))
        self.assertTrue(self.bypass.requires_quantized_bypass(SimpleNamespace(model=base)))
        self.assertFalse(self.bypass.requires_quantized_bypass(self.model))
        plan, reason = self.bypass.prepare_bypass(SimpleNamespace(model=base), self.weights)
        self.assertEqual(reason, 'plain_linear_lora')
        self.assertIsNotNone(plan)
        before = base.diffusion_model(self.x)
        expected = before + F.linear(F.linear(self.x, self.down), self.up) * .5
        torch.testing.assert_close(self.run_plan(plan, 1., base.diffusion_model), expected)
        self.assertTrue(torch.equal(before, base.diffusion_model(self.x)))

    def test_krea2_and_moss_native_int8_preserve_quantized_weight_and_output(self):
        from comfy import model_base, ops
        from comfy.quant_ops import QuantizedTensor
        families = [getattr(model_base, name) for name in ("Krea2", "MOSSImage")
                    if hasattr(model_base, name)]
        if not families:
            self.skipTest("This core predates Krea2 and MOSS")
        for family in families:
            with self.subTest(family=family.__name__):
                base = family.__new__(family)
                torch.nn.Module.__init__(base)
                layer = ops.mixed_precision_ops({}, compute_dtype=torch.float32).Linear(8, 8)
                layer.bias = torch.nn.Parameter(self.layer.bias.detach().clone())
                base.diffusion_model = torch.nn.Sequential(layer)
                quantized = QuantizedTensor.from_float(self.layer.weight.detach(), 'TensorWiseINT8Layout')
                layer.weight = torch.nn.Parameter(quantized, requires_grad=False)
                model = SimpleNamespace(model=base)
                original_weight = layer.weight
                self.assertFalse(hasattr(layer, 'weight_scale'))
                self.assertTrue(self.bypass.requires_quantized_bypass(model))
                plan, reason = self.bypass.prepare_bypass(model, self.weights)
                self.assertEqual(reason, 'plain_linear_lora')
                before = base.diffusion_model(self.x)
                expected = before + F.linear(F.linear(self.x, self.down), self.up) * .5
                torch.testing.assert_close(self.run_plan(plan, 1., base.diffusion_model), expected)
                self.assertIs(layer.weight, original_weight)
                self.assertTrue(torch.equal(before, base.diffusion_model(self.x)))
                # Unsupported patches must fail validation before hook injection.
                invalid = {**self.weights, 'diffusion_model.0.bias': ('diff', (torch.ones(8),))}
                self.assertEqual(self.bypass.prepare_bypass(model, invalid)[1], 'native_weight_delta')
                self.assertNotIn('forward', layer.__dict__)

    def test_full_precision_moss_keeps_existing_weight_hook_path(self):
        from comfy import model_base
        if not hasattr(model_base, "MOSSImage"):
            self.skipTest("This core predates MOSS")
        base = model_base.MOSSImage.__new__(model_base.MOSSImage)
        torch.nn.Module.__init__(base)
        base.diffusion_model = copy.deepcopy(self.model.model.diffusion_model)
        model = SimpleNamespace(model=base)
        self.assertFalse(self.bypass.requires_quantized_bypass(model))
        self.assertEqual(self.bypass.prepare_bypass(model, self.weights), (None, 'model_family'))

    def test_flux_lora_surrounds_early_text_refinement(self):
        from comfy import model_base
        from comfy.patcher_extension import WrappersMP, get_all_wrappers, merge_nested_dicts
        f = importlib.import_module(PKG + '.flux_engine')
        base = model_base.Flux3.__new__(model_base.Flux3)
        torch.nn.Module.__init__(base)
        base.diffusion_model = self.model.model.diffusion_model
        plan, _ = self.bypass.prepare_bypass(SimpleNamespace(model=base), self.weights)
        options = {}
        def add(kind, key, wrapper):
            options.setdefault('wrappers', {}).setdefault(kind, {}).setdefault(key, []).append(wrapper)
        work = SimpleNamespace(model_options={'transformer_options': options}, add_wrapper_with_key=add)
        routing = f.FluxRouting.__new__(f.FluxRouting)
        routing.family = 'FLUX3'
        routing.install(work)
        hook_options = plan.hook_group(1.).hooks[0].transformers_dict
        merged = merge_nested_dicts(options, hook_options)
        wrappers = get_all_wrappers(WrappersMP.DIFFUSION_MODEL, merged)
        self.assertEqual(wrappers[0].func, plan.forward)
        self.assertEqual(wrappers[1], routing.flux3_forward)

