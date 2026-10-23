"""Compressed native weights must use output deltas for every routed family."""
import importlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import torch
import torch.nn.functional as F
PKG=Path(__file__).resolve().parents[1].name
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
@unittest.skipUnless(os.environ.get('RS_MC_TEST_COMFYUI'), 'Requires native ComfyUI')
class NativeQuantizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,os.environ['RS_MC_TEST_COMFYUI'])
        from comfy.cli_args import args
        args.cpu=True
        cls.bypass=importlib.import_module(PKG+'.lora_bypass')
    @classmethod
    def tearDownClass(cls):
        sys.path.remove(os.environ['RS_MC_TEST_COMFYUI'])

    def test_dense_model_without_native_quantization_module(self):
        model = SimpleNamespace(model=torch.nn.Linear(4, 4))
        with patch.dict(sys.modules, {'comfy.quant_ops': None}):
            self.assertFalse(self.bypass.requires_quantized_bypass(model))

    def test_native_packed_linear_families_keep_storage_and_restore(self):
        from comfy import model_base,ops
        try:
            from comfy.quant_ops import QuantizedTensor,QUANT_ALGOS
        except ImportError:
            self.skipTest('This core has no native packed quantization operations')
        if not callable(getattr(ops,'mixed_precision_ops',None)):
            self.skipTest('This core has no mixed precision layer factory')
        available={config['comfy_tensor_layout'] for config in QUANT_ALGOS.values()}
        from comfy.weight_adapter import LoRAAdapter
        for family in ('Anima','SDXL','BaseModel','Flux','Flux2','Flux3','Krea2','MOSSImage'):
            if not isinstance(getattr(model_base,family,None),type):
                continue
            formats = (
                ('TensorWiseINT8Layout', {}),
                ('TensorWiseINT8Layout', {'per_channel': True}),
                ('TensorCoreFP8E4M3Layout', {}),
                ('TensorCoreFP8E5M2Layout', {}),
            )
            for fmt, quant_args in formats:
                if fmt not in available:
                    continue
                with self.subTest(family=family,format=fmt,quant_args=quant_args):
                    torch.manual_seed(1337)
                    base=getattr(model_base,family).__new__(getattr(model_base,family))
                    torch.nn.Module.__init__(base)
                    layer=ops.mixed_precision_ops({},compute_dtype=torch.float32).Linear(32,32)
                    layer.weight=torch.nn.Parameter(QuantizedTensor.from_float(torch.randn(32,32)*.1,fmt,**quant_args),requires_grad=False)
                    layer.bias=torch.nn.Parameter(torch.randn(32)*.01)
                    base.diffusion_model=torch.nn.Sequential(layer)
                    model=SimpleNamespace(model=base)
                    original=layer.weight
                    packed=original._qdata.clone()
                    serialized={k:v.clone() for k,v in original.state_dict('weight').items()}
                    x=torch.randn(2,4,32)
                    baseline=base.diffusion_model(x)
                    up,down=torch.randn(32,4)*.1,torch.randn(4,32)*.1
                    adapter=LoRAAdapter(set(),(up,down,2.,None,None,None))
                    self.assertTrue(self.bypass.requires_quantized_bypass(model))
                    plan,reason=self.bypass.prepare_bypass(model,{'diffusion_model.0.weight':adapter})
                    self.assertEqual(reason,'plain_linear_lora')
                    class Executor:
                        class_obj=base.diffusion_model
                        def __call__(_,v):return base.diffusion_model(v)
                    for strength in (1.,-.5):
                        expected=baseline+F.linear(F.linear(x,down),up)*(.5*strength)
                        torch.testing.assert_close(plan.forward(Executor(),x,strength=strength),expected)
                    self.assertTrue(torch.equal(plan.forward(Executor(),x,strength=0.),baseline))
                    class BrokenExecutor:
                        class_obj=base.diffusion_model
                        def __call__(_,v):raise RuntimeError('native packed forward failed')
                    with self.assertRaisesRegex(RuntimeError,'native packed forward failed'):
                        plan.forward(BrokenExecutor(),x,strength=1.)
                    self.assertTrue(torch.equal(base.diffusion_model(x),baseline))
                    self.assertIs(layer.weight,original)
                    self.assertTrue(torch.equal(original._qdata,packed))
                    after=original.state_dict('weight')
                    self.assertEqual(set(serialized),set(after))
                    for key,value in serialized.items():
                        self.assertTrue(torch.equal(value,after[key]),key)
                    self.assertNotIn('forward',layer.__dict__)
