"""Small CPU integrations against a real optional ComfyUI checkout.

RS_MC_TEST_COMFYUI=/path/to/ComfyUI python -m unittest discover -s tests -q
No model downloads, CUDA context or random full-size model allocation.
"""
import copy
import importlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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
        cls.previous_training = getattr(cls.mm, "in_training", None)
        if cls.previous_training is not None:
            cls.mm.in_training = True  # differentiable CPU norm/rope kernels

    @classmethod
    def tearDownClass(cls):
        if cls.previous_training is not None:
            cls.mm.in_training = cls.previous_training
        sys.path.remove(os.environ['RS_MC_TEST_COMFYUI'])

    def test_sdxl_node_native_sampling_without_optional_architectures(self):
        self.unet_node("SDXL")

    def test_sd15_node_native_sampling_encoder_and_model_guards(self):
        self.unet_node("SD1.5")

    def unet_node(self, family):
        """Run the public node through real SD1.5/SDXL U-Net/sampler wrappers on CPU.

        A small random UNet and synthetic CLIP/VAE keep this an API integration
        test, not image-quality evidence. This also runs on pre-Anima ComfyUI.
        """
        from comfy import model_base, supported_models, model_patcher
        from comfy.cli_args import args, LatentPreviewMethod
        nodes = importlib.import_module(PKG + '.nodes')
        chars = importlib.import_module(PKG + '.characters')
        torch.manual_seed(617)
        sd15 = family == "SD1.5"
        context_dim = 768 if sd15 else 2048
        config_type = supported_models.SD15 if sd15 else supported_models.SDXL
        config = config_type(dict(
            image_size=32, in_channels=4, out_channels=4, model_channels=32,
            num_res_blocks=1, channel_mult=[1, 2], use_spatial_transformer=True,
            transformer_depth=[1, 1], transformer_depth_output=[1, 1, 1, 1],
            transformer_depth_middle=1, context_dim=context_dim,
            num_classes=None if sd15 else 'sequential',
            adm_in_channels=None if sd15 else 2816, dtype=torch.float32))
        config.unet_config.update(num_heads=2, num_head_channels=-1)
        config.custom_operations = self.ops
        base_type = model_base.BaseModel if sd15 else model_base.SDXL
        base = base_type(config, device=torch.device('cpu'))
        for p in base.parameters():
            p.data.uniform_(-.05, .05)
        model = model_patcher.ModelPatcher(base, torch.device('cpu'), torch.device('cpu'))
        original = copy.deepcopy(model.model_options)
        contexts = {s: [[torch.randn(1, 3 + i, context_dim),
                         {} if sd15 else {'pooled_output': torch.randn(1, 1280)}]]
                    for i, s in enumerate(('common', 'negative', 'left', 'right'))}
        clip = SimpleNamespace(tokenize=lambda text: text,
            encode_from_tokens_scheduled=lambda text: contexts[text])
        vae = SimpleNamespace(decode=lambda latent: latent[:, :3].movedim(1, -1).sigmoid())
        pipe = chars.CharacterPipe((chars.Character('left', x=.25), chars.Character('right', x=.75)))
        with patch.object(args, 'preview_method', LatentPreviewMethod.NoPreviews), torch.no_grad():
            output = nodes.RSMultiCharacterSampler().generate(
                model, clip, vae, pipe, 'common', 'negative', width=64, height=64,
                seed=617, steps=2, cfg=3., sampler_name='euler_ancestral', scheduler='normal', autosave=False)
        image, latent, restored_pipe, info = output['result']
        audit = json.loads(info)['routing_audit']
        self.assertTrue(torch.isfinite(image).all())
        self.assertEqual(latent['samples'].shape, (1, 4, 8, 8))
        self.assertEqual(restored_pipe.characters, pipe.characters)
        self.assertGreater(audit['cross_calls'], 0)
        self.assertGreater(audit['self_calls'], 0)
        self.assertEqual(audit['restored_forwards'], len(audit['forwards']))
        self.assertEqual(model.model_options, original)
        self.assertEqual(audit['pooled_conditioning'], 'none' if sd15 else 'common_prompt_native_adm')
        self.assertEqual(json.loads(restored_pipe.generation_json)['engine'], family.lower() + '-spatial-alpha-1')
        if sd15:
            def invoke():
                return nodes.RSMultiCharacterSampler().generate(
                    model, clip, vae, pipe, 'common', 'negative',
                    width=64, height=64, steps=2, autosave=False)
            with patch.object(base.diffusion_model, 'in_channels', 9):
                with self.assertRaisesRegex(ValueError, 'inpainting'):
                    invoke()
            with patch.object(base, 'model_config', supported_models.SD20({})):
                with self.assertRaisesRegex(ValueError, 'SD2'):
                    invoke()
            for bad_shape in ((1, 3, 2048), (2, 3, 768)):
                with patch.dict(contexts, common=[[torch.zeros(bad_shape), {}]]):
                    with self.assertRaisesRegex(ValueError, 'matching CLIP-L'):
                        invoke()

    def joint(self, family):
        j = importlib.import_module(PKG+'.joint_engine')
        defaults = importlib.import_module(PKG+'.nodes').DEFAULTS
        from comfy import model_base
        if not hasattr(model_base, "Krea2" if family == "Krea2" else "MOSSImage"):
            self.skipTest(f"{family} is not implemented in this ComfyUI checkout")
        if family == "Krea2":
            from comfy.ldm.krea2.model import SingleStreamDiT
        else:
            from comfy.ldm.moss_image.model import MOSSImage
        torch.manual_seed(123)
        net = (SingleStreamDiT(features=128,tdim=32,txtdim=64,heads=4,kvheads=2,multiplier=2,layers=2,patch=2,channels=16,txtlayers=2,txtheads=4,txtkvheads=4,operations=self.ops,dtype=torch.float32)
            if family=='Krea2' else MOSSImage(dim=128,ffn_dim=256,num_heads=4,num_layers=2,text_dim=64,latent_channels=128,operations=self.ops,dtype=torch.float32))
        for p in net.parameters(): p.data.uniform_(-.1,.1)
        x = torch.randn(1,16 if family=='Krea2' else 128,4,8)
        width = 128 if family=='Krea2' else 64
        common = torch.randn(1,3,width)
        conditions = [(torch.randn(1,n,width),{}) for n in (4,5)]
        masks = torch.zeros(2,4,8)
        masks[0,:,:4]=1
        masks[1,:,4:]=1
        audit = dict(forwards=[],cross_calls=0,self_calls=0,text_refiner_calls=0,restored_forwards=0)
        r = j.JointRouting(family,conditions,masks,defaults,audit)
        r.sigmas=[1.,.5,.1]
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
        from comfy import model_base
        if not hasattr(model_base, "Anima"):
            self.skipTest("Anima is not implemented in this ComfyUI checkout")
        from comfy.ldm.cosmos.predict2 import Attention
        engine = importlib.import_module(PKG+'.engine')
        torch.manual_seed(44)
        block = SimpleNamespace(
            self_attn=Attention(16,n_heads=2,head_dim=8,operations=self.ops,dtype=torch.float32),
            cross_attn=Attention(16,context_dim=16,n_heads=2,head_dim=8,operations=self.ops,dtype=torch.float32))
        for module in [block.self_attn,block.cross_attn]:
            for p in module.parameters(): p.data.uniform_(-.1,.1)
        saved = [block.self_attn.attn_op,block.cross_attn.attn_op]
        masks = torch.zeros(2,2,4)
        masks[0,:,:2]=1
        masks[1,:,2:]=1
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
