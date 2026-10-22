"""Native-core oracle comparisons for regional weight adapters (no images)."""
import copy
import importlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import torch
import torch.nn.functional as F

PKG = Path(__file__).resolve().parents[1].name
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@unittest.skipUnless(os.environ.get('RS_MC_TEST_COMFYUI'), 'Requires native ComfyUI')
class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.environ['RS_MC_TEST_COMFYUI'])
        from comfy.cli_args import args
        args.cpu = True
        try:
            from comfy.quant_ops import QuantizedTensor
            from comfy.weight_adapter import adapters
            from comfy import ops, model_base
            if not hasattr(ops, 'mixed_precision_ops') or not hasattr(model_base, 'MOSSImage'):
                raise ImportError()
        except ImportError:
            raise unittest.SkipTest('Core predates packed MOSS/weight adapters')
        cls.bypass = importlib.import_module(PKG + '.lora_bypass')
        cls.delta = importlib.import_module(PKG + '.adapter_delta')

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(os.environ['RS_MC_TEST_COMFYUI'])

    def setUp(self):
        from comfy import ops, model_base
        torch.manual_seed(987)
        self.base = model_base.MOSSImage.__new__(model_base.MOSSImage)
        torch.nn.Module.__init__(self.base)
        layer = ops.mixed_precision_ops({}, compute_dtype=torch.float32).Linear(8, 8)
        from comfy.quant_ops import QuantizedTensor
        original = torch.randn(8, 8) * .2
        layer.weight = torch.nn.Parameter(QuantizedTensor.from_float(original, 'TensorWiseINT8Layout'), requires_grad=False)
        layer.bias = torch.nn.Parameter(torch.randn(8) * .1)
        self.base.diffusion_model = torch.nn.Sequential(layer)
        self.layer, self.model = layer, SimpleNamespace(model=self.base)
        self.x = torch.randn(2, 3, 8)

    def adapters(self, out=8, inp=8):
        from comfy.weight_adapter import LoRAAdapter, LoHaAdapter, LoKrAdapter, GLoRAAdapter, OFTAdapter, BOFTAdapter
        rand = lambda *shape: torch.randn(*shape) * .15
        up, down = rand(out, 2), rand(2, inp)
        IA3Adapter = importlib.import_module(PKG + '.adapter_formats').ia3_adapter_type()
        return {
            'ia3_input': IA3Adapter(set(), (rand(inp), torch.tensor(1))),
            'ia3_output': IA3Adapter(set(), (rand(out), torch.tensor(0))),
            'dora': LoRAAdapter(set(), (up, down, 1., None, torch.ones(out, 1) * .7, None)),
            'loha': LoHaAdapter(set(), (up, down, 1., rand(out, 2), rand(2, inp), None, None, None)),
            'doha': LoHaAdapter(set(), (up, down, 1., rand(out, 2), rand(2, inp), None, None, torch.ones(out, 1))),
            'lokr': LoKrAdapter(set(), (rand(2, 2), rand(out//2, inp//2), 1., None, None, None, None, None, None)),
            'dokr': LoKrAdapter(set(), (rand(2, 2), rand(out//2, inp//2), 1., None, None, None, None, None, torch.ones(out, 1))),
            'glora': GLoRAAdapter(set(), (rand(inp, 2), rand(2, inp), up, down, 1., None)),
            'glora_old': GLoRAAdapter(set(), (rand(2, inp), rand(inp, 2), down, up, 1., None)),
            'oft': OFTAdapter(set(), (rand(out//2, 2, 2), None, .4, None)),
            'boft': BOFTAdapter(set(), (rand(1, out//2, 2, 2), torch.ones(out, 1)*1.1, .4, None)),
            'diff': ('diff', (rand(out, inp),)),
            'set': ('set', (rand(out, inp),)),
        }

    def run_plan(self, plan, strength, runtime=None, call=None):
        runtime = runtime or self.base.diffusion_model
        class Executor:
            class_obj = runtime
            def __call__(_, x):
                return (call or runtime)(x)
        return plan.forward(Executor(), self.x, strength=strength)

    def oracle(self, patches, strength):
        from comfy.lora import calculate_weight
        weight = self.delta.float_weight(self.layer.weight, self.x.device).clone()
        bias = self.layer.bias.detach().clone()
        by_param = {'weight': [], 'bias': []}
        for raw, adapter in patches.items():
            key, offset = (raw, None) if isinstance(raw, str) else raw[:2]
            by_param[key.rsplit('.', 1)[1]].append((strength, adapter, 1., offset, None))
        with self.delta.strict_core_errors('oracle'):
            weight = calculate_weight(by_param['weight'], weight, 'diffusion_model.0.weight')
            bias = calculate_weight(by_param['bias'], bias, 'diffusion_model.0.bias')
        # The native INT8 op also quantizes activations; retain that base residual.
        # Compare only the requested adapter correction to the core weight oracle.
        dequant_base = F.linear(self.x, self.delta.float_weight(self.layer.weight, self.x.device), self.layer.bias)
        return self.base.diffusion_model(self.x) + (F.linear(self.x, weight, bias) - dequant_base)

    def test_all_core_adapters_match_native_merge_and_restore_quantized_base(self):
        baseline = self.base.diffusion_model(self.x)
        original = self.layer.weight
        for name, adapter in self.adapters().items():
            with self.subTest(adapter=name):
                patches = {'diffusion_model.0.weight': adapter}
                plan, reason = self.bypass.prepare_bypass(self.model, patches)
                self.assertEqual(reason, 'native_weight_delta')
                self.assertFalse(plan.supports_shared)
                for strength in (1., .6, -.5):
                    torch.testing.assert_close(self.run_plan(plan, strength), self.oracle(patches, strength), atol=2e-6, rtol=2e-5)
                self.assertTrue(torch.equal(self.run_plan(plan, 0.), baseline))
                self.assertTrue(torch.equal(self.base.diffusion_model(self.x), baseline))
                self.assertIs(self.layer.weight, original)
                self.assertNotIn('forward', self.layer.__dict__)
                self.assertNotIn('comfy_force_forward', self.layer.__dict__)

    def test_partial_adapters_and_bias_match_native_merge(self):
        for name, adapter in self.adapters(out=4).items():
            with self.subTest(adapter=name):
                patches = {('diffusion_model.0.weight', (0, 2, 4)): adapter,
                           'diffusion_model.0.bias': ('diff', (torch.randn(8)*.1,))}
                plan, reason = self.bypass.prepare_bypass(self.model, patches)
                self.assertEqual(reason, 'native_weight_delta')
                torch.testing.assert_close(self.run_plan(plan, .7), self.oracle(patches, .7), atol=2e-6, rtol=2e-5)

    def test_ia3_file_loader_input_output_and_partial_channels(self):
        formats = importlib.import_module(PKG + '.adapter_formats')
        from comfy.lora import prefetch_prepared_value
        baseline = self.base.diffusion_model(self.x)
        weight = self.delta.float_weight(self.layer.weight, 'cpu')
        for on_input in (False, True):
            for partial in (False, True):
                with self.subTest(on_input=on_input, partial=partial):
                    key = ('diffusion_model.0.weight', (0, 2, 4)) if partial else 'diffusion_model.0.weight'
                    count = 8 if on_input or not partial else 4
                    vector = torch.randn(count) * .2
                    sd = {'target.weight': vector, 'target.on_input': torch.tensor(on_input)}
                    patches = formats.load_additional_adapters(sd, {'target': key})
                    # Native hooks also clone/prefetch this adapter, including its flag.
                    patches[key] = prefetch_prepared_value(patches[key], [0], None, None, False)
                    plan, reason = self.bypass.prepare_bypass(self.model, patches)
                    self.assertEqual(reason, 'native_weight_delta')
                    delta = torch.zeros_like(weight)
                    selected = weight[2:6] if partial else weight
                    calculated = selected * vector.reshape(1, -1) if on_input else selected * vector.reshape(-1, 1)
                    if partial:
                        delta[2:6] = calculated
                    else:
                        delta = calculated
                    for strength in (1., -.5):
                        expected = baseline + F.linear(self.x, delta * strength)
                        torch.testing.assert_close(self.run_plan(plan, strength), expected, atol=2e-6, rtol=2e-5)
                    self.assertTrue(torch.equal(self.run_plan(plan, 0.), baseline))
                    self.assertTrue(torch.equal(self.base.diffusion_model(self.x), baseline))

    def test_ia3_invalid_and_timestep_formats_fail_explicitly(self):
        formats = importlib.import_module(PKG + '.adapter_formats')
        with self.assertRaisesRegex(ValueError, 'Malformed IA3'):
            formats.load_additional_adapters({'target.on_input': torch.tensor(2), 'target.weight': torch.ones(8)}, {'target': 'diffusion_model.0.weight'})
        with self.assertRaisesRegex(ValueError, 'T-LoRA'):
            formats.validate_file_format({'target.lambda_layer': torch.tensor(1.)})

    def test_moss_qkv_plain_factors_match_native_merge(self):
        from comfy.weight_adapter import LoRAAdapter
        patches = {('diffusion_model.0.weight', (0, start, 2)): LoRAAdapter(set(), (torch.randn(2,2)*.1, torch.randn(2,8)*.1, 1., None, None, None)) for start in (0,2,4,6)}
        plan, reason = self.bypass.prepare_bypass(self.model, patches)
        self.assertEqual(reason, 'plain_linear_lora')
        torch.testing.assert_close(self.run_plan(plan, .8), self.oracle(patches, .8), atol=2e-6, rtol=2e-5)

    def test_native_loader_file_conventions_and_decomposed_lokr(self):
        from comfy.lora import load_lora
        rand = lambda *shape: torch.randn(*shape)*.1
        files = {
            'LoRAAdapter': {'lora_up.weight': rand(8,2), 'lora_down.weight': rand(2,8), 'dora_scale': torch.ones(8,1)},
            'LoHaAdapter': {'hada_w1_a': rand(8,2), 'hada_w1_b': rand(2,8), 'hada_w2_a': rand(8,2), 'hada_w2_b': rand(2,8)},
            'LoKrAdapter': {'lokr_w1_a': rand(2,1), 'lokr_w1_b': rand(1,2), 'lokr_w2_a': rand(4,2), 'lokr_w2_b': rand(2,4)},
            'GLoRAAdapter': {'a1.weight': rand(8,2), 'a2.weight': rand(2,8), 'b1.weight': rand(8,2), 'b2.weight': rand(2,8)},
            'OFTAdapter': {'oft_blocks': rand(4,2,2)},
            'BOFTAdapter': {'oft_blocks': rand(2,4,2,2)},
        }
        for name, tensors in files.items():
            with self.subTest(file_format=name):
                sd = {'target.'+k: v for k,v in tensors.items()}
                sd['target.alpha'] = torch.tensor(.5)
                patches = load_lora(sd, {'target': 'diffusion_model.0.weight'})
                self.assertEqual(type(patches['diffusion_model.0.weight']).__name__, name)
                plan, reason = self.bypass.prepare_bypass(self.model, patches)
                self.assertEqual(reason, 'native_weight_delta')
                torch.testing.assert_close(self.run_plan(plan, .7), self.oracle(patches,.7), atol=3e-6, rtol=2e-5)

    def test_fp8_and_full_precision_match_native_for_all_adapters(self):
        from comfy.quant_ops import QuantizedTensor
        from comfy import model_base
        base = model_base.Flux2.__new__(model_base.Flux2)
        torch.nn.Module.__init__(base)
        base.diffusion_model = self.base.diffusion_model
        self.base, self.model = base, SimpleNamespace(model=base)
        original = self.delta.float_weight(self.layer.weight, 'cpu').clone()
        for layout in (None, 'TensorCoreFP8Layout'):
            with self.subTest(layout=layout):
                self.layer.weight = torch.nn.Parameter(original.clone() if layout is None else QuantizedTensor.from_float(original, layout), requires_grad=False)
                for name, adapter in self.adapters().items():
                    patches = {'diffusion_model.0.weight': adapter}
                    plan, reason = self.bypass.prepare_bypass(self.model, patches)
                    self.assertEqual(reason, 'native_weight_delta')
                    torch.testing.assert_close(self.run_plan(plan,.7), self.oracle(patches,.7), atol=3e-6, rtol=2e-5)

    def test_incoming_global_weight_functions_are_respected(self):
        from comfy import ops, model_base
        base = model_base.SDXL.__new__(model_base.SDXL)
        torch.nn.Module.__init__(base)
        self.base, self.model = base, SimpleNamespace(model=base)
        layer = ops.manual_cast.Linear(8,8)
        layer.weight = torch.nn.Parameter(self.delta.float_weight(self.layer.weight, 'cpu').clone())
        layer.bias = torch.nn.Parameter(self.layer.bias.detach().clone())
        layer.weight_function = [lambda w: w * .8]
        layer.bias_function = [lambda b: b + .05]
        self.layer = layer
        self.base.diffusion_model = torch.nn.Sequential(layer)
        adapter = self.adapters()['dora']
        patches = {'diffusion_model.0.weight': adapter}
        plan, _ = self.bypass.prepare_bypass(self.model, patches)
        from comfy.lora import calculate_weight
        merged = calculate_weight([(.7, adapter, 1., None, None)], layer.weight.float().clone()*.8, 'test')
        expected = F.linear(self.x, merged, layer.bias + .05)
        torch.testing.assert_close(self.run_plan(plan,.7), expected, atol=3e-6, rtol=2e-5)
        self.assertEqual(len(layer.weight_function), 1)

    def test_delegate_failure_restores_runtime_attributes(self):
        plan, _ = self.bypass.prepare_bypass(self.model, {'diffusion_model.0.weight': self.adapters()['lokr']})
        layer = torch.nn.Linear(8, 8)
        layer.weight = torch.nn.Parameter(self.delta.float_weight(self.layer.weight, 'cpu').clone())
        layer.bias = torch.nn.Parameter(self.layer.bias.detach().clone())
        runtime = torch.nn.Sequential(layer)
        before = runtime(self.x)
        def fail(x):
            runtime(x)
            raise RuntimeError('cancelled')
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            self.run_plan(plan, 1., runtime, fail)
        self.assertTrue(torch.equal(runtime(self.x), before))
        self.assertNotIn('forward', runtime[0].__dict__)
        self.assertNotIn('comfy_force_forward', runtime[0].__dict__)

    def test_errors_report_key_adapter_and_partial_instead_of_silent_skip(self):
        key = ('diffusion_model.0.weight', (0, 0, 99))
        plan, reason = self.bypass.prepare_bypass(self.model, {key: self.adapters()['lokr']})
        self.assertIsNone(plan)
        for fragment in ('patch_offset', 'LoKrAdapter', 'partial=True', 'diffusion_model.0.weight'):
            self.assertIn(fragment, reason)
        from comfy.weight_adapter import LoKrAdapter
        malformed = LoKrAdapter(set(), (torch.ones(3, 3), torch.ones(3, 3), None, None, None, None, None, None, None))
        plan, _ = self.bypass.prepare_bypass(self.model, {'diffusion_model.0.weight': malformed})
        with self.assertRaisesRegex(ValueError, 'Regional adapter calculation failed'):
            self.run_plan(plan, 1.)
        self.assertNotIn('forward', self.layer.__dict__)

    def test_locon_and_tucker_convolution_adapters_match_native(self):
        from comfy import model_base
        from comfy.weight_adapter import LoRAAdapter, LoHaAdapter, LoKrAdapter
        from comfy.lora import calculate_weight
        rand = lambda *shape: torch.randn(*shape)*.1
        layer = torch.nn.Conv2d(4,4,3,padding=1)
        base = model_base.SDXL.__new__(model_base.SDXL)
        torch.nn.Module.__init__(base)
        base.diffusion_model = torch.nn.Sequential(layer)
        self.x = torch.randn(2,4,5,5)
        adapters = [
            LoRAAdapter(set(), (rand(4,2,1,1), rand(2,4,3,3), 1., None, None, None)),
            LoRAAdapter(set(), (rand(4,2,1,1), rand(2,4,1,1), 1., rand(2,2,3,3), None, None)),
            LoHaAdapter(set(), (rand(2,4), rand(2,4), 1., rand(2,4), rand(2,4), rand(2,2,3,3), rand(2,2,3,3), None)),
            LoKrAdapter(set(), (rand(2,2), None, 1., None, None, rand(2,2), rand(2,2), rand(2,2,3,3), None)),
        ]
        for adapter in adapters:
            with self.subTest(adapter=type(adapter).__name__):
                patches = {'diffusion_model.0.weight': adapter}
                plan, reason = self.bypass.prepare_bypass(SimpleNamespace(model=base), patches)
                self.assertEqual(reason, 'native_weight_delta')
                if type(adapter) is LoKrAdapter:
                    # The core CP einsum has a noncontiguous-kron bug. Compare
                    # against the independent contiguous Kronecker formula.
                    w1, _, alpha, _, _, w2a, w2b, t2, _ = adapter.weights
                    w2 = torch.einsum('ijkl,jr,ip->prkl', t2, w2b, w2a).contiguous()
                    diff = torch.kron(w1[:,:,None,None], w2) * (alpha / w2b.shape[0])
                    merged = layer.weight.float() + .7 * diff
                else:
                    with self.delta.strict_core_errors('oracle'):
                        merged = calculate_weight([(.7, adapter, 1., None, None)], layer.weight.float().clone(), 'oracle')
                expected = F.conv2d(self.x, merged, layer.bias, padding=1)
                torch.testing.assert_close(self.run_plan(plan,.7,base.diffusion_model), expected, atol=3e-6, rtol=2e-5)

    def test_convolution_norm_and_bias_differences_match_native(self):
        from comfy import model_base
        cases = [(torch.nn.Conv1d(4,4,3,padding=1), torch.randn(2,4,7)),
                 (torch.nn.Conv2d(4,4,3,padding=1,padding_mode='reflect',groups=2), torch.randn(2,4,5,5)),
                 (torch.nn.Conv3d(4,4,3,padding=1), torch.randn(2,4,4,4,4)),
                 (torch.nn.LayerNorm((3,4)), torch.randn(2,3,4)),
                 (torch.nn.GroupNorm(2,4), torch.randn(2,4,5,5)),
                 (torch.nn.RMSNorm(4), torch.randn(2,3,4))]
        for layer, x in cases:
            with self.subTest(layer=type(layer).__name__):
                base = model_base.SDXL.__new__(model_base.SDXL)
                torch.nn.Module.__init__(base)
                base.diffusion_model = torch.nn.Sequential(layer)
                patches = {'diffusion_model.0.weight': ('diff', (torch.randn_like(layer.weight)*.1,))}
                if getattr(layer, 'bias', None) is not None:
                    patches['diffusion_model.0.bias'] = ('diff', (torch.randn_like(layer.bias)*.1,))
                plan, reason = self.bypass.prepare_bypass(SimpleNamespace(model=base), patches)
                self.assertEqual(reason, 'native_weight_delta')
                merged = copy.deepcopy(layer)
                with torch.no_grad():
                    merged.weight.add_(patches['diffusion_model.0.weight'][1][0]*.7)
                    if 'diffusion_model.0.bias' in patches:
                        merged.bias.add_(patches['diffusion_model.0.bias'][1][0]*.7)
                self.x = x
                torch.testing.assert_close(self.run_plan(plan,.7,base.diffusion_model), merged(x), atol=3e-6, rtol=2e-5)
