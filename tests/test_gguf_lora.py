"""Real ComfyUI-GGUF ops, independently merged float-weight oracles (CPU)."""
import copy
import importlib
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

import torch
import torch.nn.functional as F

PKG = Path(__file__).resolve().parents[1].name
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@unittest.skipUnless(os.environ.get("RS_MC_TEST_COMFYUI") and os.environ.get("RS_MC_TEST_GGUF"),
                     "Requires native ComfyUI and ComfyUI-GGUF")
class GGUFTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.environ["RS_MC_TEST_COMFYUI"])
        from comfy.cli_args import args
        args.cpu = True
        try:
            from comfy.weight_adapter.bypass import BypassForwardHook
            from comfy.weight_adapter import LoRAAdapter
        except ImportError:
            raise unittest.SkipTest("Core predates native bypass adapters")
        # Import ops only: importing the extension entrypoint also loads nodes
        # and changes the process-wide folder catalog.
        package = ModuleType("rs_test_gguf")
        package.__path__ = [os.environ["RS_MC_TEST_GGUF"]]
        sys.modules[package.__name__] = package
        cls.ops = importlib.import_module(package.__name__ + ".ops")
        cls.dequant = importlib.import_module(package.__name__ + ".dequant")
        cls.bypass = importlib.import_module(PKG + ".lora_bypass")
        cls.delta = importlib.import_module(PKG + ".adapter_delta")
        cls.bridge = importlib.import_module(PKG + ".gguf_compat")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(os.environ["RS_MC_TEST_COMFYUI"])

    def setUp(self):
        from comfy import model_base
        from comfy.weight_adapter import LoRAAdapter
        import gguf
        torch.manual_seed(812)
        self.base = model_base.Flux.__new__(model_base.Flux)
        torch.nn.Module.__init__(self.base)
        self.layer = self.ops.GGMLOps.Linear(32, 32)
        self.bias = torch.randn(32) * .1
        self.layer.bias = torch.nn.Parameter(self.bias.clone())
        self.set_weight(gguf.GGMLQuantizationType.Q4_0)
        self.base.diffusion_model = torch.nn.Sequential(self.layer)
        self.model = SimpleNamespace(model=self.base)
        self.x = torch.randn(2, 5, 32)
        self.up, self.down = torch.randn(32, 2) * .1, torch.randn(2, 32) * .1
        self.adapter = LoRAAdapter(set(), (self.up, self.down, 1., None, None, None))
        self.patches = {"diffusion_model.0.weight": self.adapter}

    def set_weight(self, qtype):
        import gguf
        source = (torch.randn(32, 32) * .2).numpy()
        packed = gguf.quants.quantize(source, qtype)
        tensor = self.ops.GGMLTensor(torch.from_numpy(packed), tensor_type=qtype,
                                     tensor_shape=torch.Size((32, 32)), patches=[])
        self.layer.weight = torch.nn.Parameter(tensor, requires_grad=False)

    def run_plan(self, plan, strength, runtime=None, call=None):
        runtime = self.base.diffusion_model if runtime is None else runtime
        class Executor:
            class_obj = runtime
            def __call__(_, x):
                return (runtime if call is None else call)(x)
        return plan.forward(Executor(), self.x, strength=strength)

    def test_factor_only_preserves_real_packed_bytes_and_zero_is_exact(self):
        import gguf
        for qtype in (gguf.GGMLQuantizationType.Q4_0, gguf.GGMLQuantizationType.Q8_0,
                      gguf.GGMLQuantizationType.F16):
            with self.subTest(qtype=qtype):
                self.set_weight(qtype)
                original = self.layer.weight
                packed = torch.Tensor(original).clone()
                baseline = self.base.diffusion_model(self.x)
                self.assertTrue(self.bypass.requires_quantized_bypass(self.model))
                plan, reason = self.bypass.prepare_bypass(self.model, self.patches)
                self.assertEqual(reason, "plain_linear_lora")
                for strength in (1., -.5, .6):
                    # Native bypass stores factors in the layer's float dtype;
                    # packed integer tensors leave the original factors intact.
                    cast = lambda factor: factor.to(original.dtype).float() if original.dtype == torch.float16 else factor
                    expected = baseline + F.linear(F.linear(self.x, cast(self.down)), cast(self.up)) * (.5 * strength)
                    torch.testing.assert_close(self.run_plan(plan, strength), expected)
                self.assertTrue(torch.equal(self.run_plan(plan, 0.), baseline))
                self.assertTrue(torch.equal(self.base.diffusion_model(self.x), baseline))
                self.assertIs(self.layer.weight, original)
                self.assertTrue(torch.equal(torch.Tensor(original), packed))
                self.assertNotIn("forward", self.layer.__dict__)
                self.assertNotIn("comfy_force_forward", self.layer.__dict__)

    def test_incoming_global_lora_is_preserved_without_double_application(self):
        self.layer.weight.patches = [([(0.4, self.adapter, 1., None, None)], "diffusion_model.0.weight")]
        baseline = self.base.diffusion_model(self.x)
        plan, reason = self.bypass.prepare_bypass(self.model, self.patches)
        self.assertEqual(reason, "plain_linear_lora")
        expected = baseline + F.linear(F.linear(self.x, self.down), self.up) * .5
        torch.testing.assert_close(self.run_plan(plan, 1.), expected)
        self.assertTrue(torch.equal(self.base.diffusion_model(self.x), baseline))
        self.assertEqual(len(self.layer.weight.patches), 1)

    def test_decoder_formats_across_model_families(self):
        """Packed decoder/operator coverage, not quantized checkpoint quality."""
        import gguf
        import numpy as np
        from comfy import model_base
        from comfy.weight_adapter import LoRAAdapter
        rng = np.random.default_rng(812)
        families = ('Anima', 'SDXL', 'BaseModel', 'Flux', 'Flux2', 'Flux3', 'Krea2', 'MOSSImage')
        # Includes the loader's native torch decoders and numpy fallback formats.
        # Bound every byte below 64 so embedded half/float scales remain finite.
        for qtype in gguf.quants._type_traits:
            block_size, type_size = gguf.GGML_QUANT_SIZES[qtype]
            packed = rng.integers(1, 64, (32, 256 // block_size * type_size), dtype=np.uint8)
            dense = torch.from_numpy(gguf.quants.dequantize(packed, qtype))
            for family in families:
                if not isinstance(getattr(model_base, family, None), type):
                    continue
                with self.subTest(qtype=qtype.name, family=family):
                    base = getattr(model_base, family).__new__(getattr(model_base, family))
                    torch.nn.Module.__init__(base)
                    layer = self.ops.GGMLOps.Linear(256, 32)
                    # Match numpy's FP32 decoding for the independent oracle.
                    # The loader's default can decode intermediate scales in FP16.
                    layer.dequant_dtype = torch.float32
                    tensor = self.ops.GGMLTensor(torch.from_numpy(packed.copy()), tensor_type=qtype,
                                                tensor_shape=torch.Size((32, 256)), patches=[])
                    layer.weight = torch.nn.Parameter(tensor, requires_grad=False)
                    layer.bias = torch.nn.Parameter(torch.randn(32) * .01)
                    base.diffusion_model = torch.nn.Sequential(layer)
                    x = torch.randn(2, 3, 256) * .1
                    baseline = base.diffusion_model(x)
                    torch.testing.assert_close(baseline, F.linear(x, dense, layer.bias), atol=2e-5, rtol=2e-5)
                    up, down = torch.randn(32, 2) * .1, torch.randn(2, 256) * .1
                    adapter = LoRAAdapter(set(), (up, down, 1., None, None, None))
                    plan, reason = self.bypass.prepare_bypass(SimpleNamespace(model=base), {'diffusion_model.0.weight': adapter})
                    self.assertEqual(reason, 'plain_linear_lora')
                    class Executor:
                        class_obj = base.diffusion_model
                        def __call__(_, value):
                            return base.diffusion_model(value)
                    expected = baseline + F.linear(F.linear(x, down), up) * .5
                    torch.testing.assert_close(plan.forward(Executor(), x, strength=1.), expected)
                    self.assertTrue(torch.equal(plan.forward(Executor(), x, strength=0.), baseline))
                    self.assertTrue(torch.equal(base.diffusion_model(x), baseline))
                    self.assertTrue(torch.equal(torch.Tensor(layer.weight), torch.from_numpy(packed)))
                    self.assertNotIn('forward', layer.__dict__)
                    plan.release()

    def test_partial_output_slice_matches_independent_oracle(self):
        from comfy.weight_adapter import LoRAAdapter
        adapter = LoRAAdapter(set(), (self.up[:8], self.down, 1., None, None, None))
        weights = {("diffusion_model.0.weight", (0, 8, 8)): adapter}
        plan, reason = self.bypass.prepare_bypass(self.model, weights)
        self.assertEqual(reason, "plain_linear_lora")
        expected = self.base.diffusion_model(self.x) + F.pad(F.linear(F.linear(self.x, self.down), self.up[:8]) * .5, (8, 16))
        torch.testing.assert_close(self.run_plan(plan, 1.), expected)

    def test_extended_adapter_uses_gguf_global_patched_weight_oracle(self):
        from comfy.lora import calculate_weight
        from comfy.weight_adapter import LoRAAdapter
        self.layer.weight.patches = [([(0.4, self.adapter, 1., None, None)], "diffusion_model.0.weight")]
        original = self.layer.weight
        packed = torch.Tensor(original).clone()
        baseline = self.base.diffusion_model(self.x)
        weight, bias = self.layer.cast_bias_weight(input=self.x, dtype=torch.float32)
        for adapter in (LoRAAdapter(set(), (self.up, self.down, 1., None, torch.ones(32, 1) * .7, None)),
                        ("diff", (torch.randn(32, 32) * .1,))):
            with self.subTest(adapter=type(adapter).__name__):
                weights = {"diffusion_model.0.weight": adapter}
                plan, reason = self.bypass.prepare_bypass(self.model, weights)
                self.assertEqual(reason, "native_weight_delta")
                self.assertFalse(plan.supports_shared)
                for strength in (1., -.5):
                    merged = calculate_weight([(strength, adapter, 1., None, None)], weight.clone(), "weight")
                    expected = F.linear(self.x, merged, bias)
                    torch.testing.assert_close(self.run_plan(plan, strength), expected, atol=2e-6, rtol=2e-5)
                self.assertTrue(torch.equal(self.run_plan(plan, 0.), baseline))
                self.assertTrue(torch.equal(self.base.diffusion_model(self.x), baseline))
                self.assertIs(self.layer.weight, original)
                self.assertTrue(torch.equal(torch.Tensor(original), packed))

    def test_runtime_clones_and_exception_restore_dispatch(self):
        plan, _ = self.bypass.prepare_bypass(self.model, self.patches)
        runtime = copy.deepcopy(self.base.diffusion_model)
        before = runtime(self.x)
        torch.testing.assert_close(self.run_plan(plan, 1., runtime), before + F.linear(F.linear(self.x, self.down), self.up) * .5)
        def fail(x):
            runtime(x)
            raise RuntimeError("cancelled")
        with self.assertRaisesRegex(RuntimeError, "cancelled"):
            self.run_plan(plan, 1., runtime, fail)
        self.assertTrue(torch.equal(runtime(self.x), before))
        self.assertNotIn("forward", runtime[0].__dict__)
        plan.release()
        self.assertIs(plan.layers[0][1].weights, self.adapter.weights)

    def test_unrelated_custom_tensor_is_still_rejected(self):
        class OtherTensor(torch.Tensor):
            pass
        self.layer = torch.nn.Linear(32, 32)
        self.layer.weight = torch.nn.Parameter(self.layer.weight.as_subclass(OtherTensor))
        self.base.diffusion_model = torch.nn.Sequential(self.layer)
        self.assertFalse(self.bridge.is_gguf_layer(self.layer))
        plan, reason = self.bypass.prepare_bypass(self.model, self.patches)
        self.assertIsNone(plan)
        self.assertIn("custom_tensor", reason)


if __name__ == "__main__":
    unittest.main()
