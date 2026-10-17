"""Small CPU integrations against a real optional ComfyUI checkout.

RS_MC_TEST_COMFYUI=/path/to/ComfyUI python -m unittest discover -s tests -q
No model downloads, CUDA context or random full-size model allocation.
"""
import importlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import torch

PKG = Path(__file__).resolve().parents[1].name
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@unittest.skipUnless(os.environ.get('RS_MC_TEST_COMFYUI'), 'Set RS_MC_TEST_COMFYUI for native CPU integrations')
class NativeModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.environ['RS_MC_TEST_COMFYUI'])
        from comfy.cli_args import args
        args.cpu = True
        import comfy.ops
        import comfy.model_management
        cls.ops = comfy.ops.manual_cast
        cls.mm = comfy.model_management
        cls.previous_training = cls.mm.in_training
        cls.mm.in_training = True  # differentiable CPU norm/rope kernels

    @classmethod
    def tearDownClass(cls):
        cls.mm.in_training = cls.previous_training
        sys.path.remove(os.environ['RS_MC_TEST_COMFYUI'])

    def joint(self, family):
        j = importlib.import_module(PKG+'.joint_engine')
        defaults = importlib.import_module(PKG+'.nodes').DEFAULTS
        from comfy.ldm.krea2.model import SingleStreamDiT
        from comfy.ldm.moss_image.model import MOSSImage
        torch.manual_seed(123)
        net = (SingleStreamDiT(features=128,tdim=32,txtdim=64,heads=4,kvheads=2,multiplier=2,layers=2,patch=2,channels=16,txtlayers=2,txtheads=4,txtkvheads=4,operations=self.ops,dtype=torch.float32)
            if family=='Krea2' else MOSSImage(dim=128,ffn_dim=256,num_heads=4,num_layers=2,text_dim=64,latent_channels=128,operations=self.ops,dtype=torch.float32))
        for p in net.parameters(): p.data.uniform_(-.1,.1)
        x = torch.randn(1,16 if family=='Krea2' else 128,4,8)
        width = 128 if family=='Krea2' else 64
        common = torch.randn(1,3,width)
        conditions = [(torch.randn(1,n,width),{}) for n in (4,5)]
        masks = torch.zeros(2,4,8); masks[0,:,:4]=1; masks[1,:,4:]=1
        audit = dict(forwards=[],cross_calls=0,self_calls=0,text_refiner_calls=0,restored_forwards=0)
        r = j.JointRouting(family,conditions,masks,defaults,audit); r.sigmas=[1.,.5,.1]
        opts = {'cond_or_uncond':[0],'sigmas':torch.tensor([.5]),'optimized_attention_override':r.attention}
        grid = (2,4) if family=='Krea2' else (4,8)
        def invoke(x,t,c,o): return net(x,t,c,transformer_options=o)
        with torch.no_grad():
            out = r.forward(invoke,x,torch.tensor([.5]),common,opts,grid)
            self.assertEqual(out.shape,x.shape)
            self.assertTrue(torch.isfinite(out).all())
            self.assertEqual(audit['cross_calls'],2)
            self.assertEqual(audit['text_refiner_calls'],2)
            self.assertIsNone(r.state)
            opts['cond_or_uncond']=[1]
            native = invoke(x,torch.tensor([.5]),common,{})
            negative = r.forward(invoke,x,torch.tensor([.5]),common,opts,grid)
            torch.testing.assert_close(native,negative,atol=0,rtol=0)

    def test_krea_native_refiners_joint_attention_and_negative(self): self.joint('Krea2')
    def test_moss_native_rope_joint_attention_and_negative(self): self.joint('MOSS')

    def test_anima_native_tensor_containers_and_backend_argument(self):
        from comfy.ldm.cosmos.predict2 import Attention
        engine = importlib.import_module(PKG+'.engine')
        torch.manual_seed(44)
        block = SimpleNamespace(
            self_attn=Attention(16,n_heads=2,head_dim=8,operations=self.ops,dtype=torch.float32),
            cross_attn=Attention(16,context_dim=16,n_heads=2,head_dim=8,operations=self.ops,dtype=torch.float32))
        for module in [block.self_attn,block.cross_attn]:
            for p in module.parameters(): p.data.uniform_(-.1,.1)
        saved = [block.self_attn.attn_op,block.cross_attn.attn_op]
        masks = torch.zeros(2,2,4); masks[0,:,:2]=1; masks[1,:,2:]=1
        audit = dict(forwards=[],cross_calls=0,self_calls=0,restored_forwards=0)
        r = engine.AnimaRouting([],masks,'character_first',audit,3)
        r.contexts=[torch.randn(1,4,16),torch.randn(1,5,16)]
        r.sigmas=[1.,.5,.1]
        def invoke(x,t,context,**kwargs):
            opts={**kwargs['transformer_options'],'block_index':0}
            tokens=x.flatten(2).transpose(1,2)
            tokens=block.self_attn(tokens,transformer_options=opts)
            return block.cross_attn(tokens,context,transformer_options=opts)
        invoke.class_obj=SimpleNamespace(blocks=[block],patch_spatial=1)
        with torch.no_grad():
            out=r.forward(invoke,torch.randn(1,16,1,2,4),torch.tensor([.5]),torch.randn(1,3,16),
                          transformer_options={'cond_or_uncond':[0],'sigmas':torch.tensor([.5])})
        self.assertEqual(out.shape,(1,8,16))
        self.assertTrue(torch.isfinite(out).all())
        self.assertEqual(audit['cross_calls'],1)
        self.assertEqual(audit['self_calls'],1)
        self.assertEqual(saved,[block.self_attn.attn_op,block.cross_attn.attn_op])


if __name__=='__main__': unittest.main()
