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
import tempfile
from dataclasses import replace
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

    def test_literal_lettering_is_not_converted_as_prompt_weights(self):
        c = importlib.import_module(PKG + ".characters")
        n = importlib.import_module(PKG + ".nodes")
        from comfy.sd1_clip import escape_important, unescape_important, token_weights
        region = c.TextRegion('{bold}', bbox=(.1,.4,.9,.6), text='{HELLO} (1:2)')
        convert = lambda value: n.to_comfyui(n.parse_naiv4(value))
        caption = n.text_region_caption(region, convert)
        parsed = [(unescape_important(text), weight) for text, weight in token_weights(escape_important(caption), 1)]
        self.assertIn('{HELLO} (1:2)', ''.join(text for text, _ in parsed))
        self.assertFalse(any(weight == 2 for _, weight in parsed))
        self.assertIn('{HELLO} (1:2)', n.text_region_caption(region, convert, weighted=False))

    def test_sdxl_node_native_sampling_without_optional_architectures(self):
        self.unet_node("SDXL")

    def test_sd15_node_native_sampling_encoder_and_model_guards(self):
        self.unet_node("SD1.5")

    def test_sdxl_boxes_native_sampling(self): self.unet_node("SDXL", boxes=True)

    def test_sd15_boxes_native_sampling(self): self.unet_node("SD1.5", boxes=True)

    def test_sdxl_mixed_native_sampling(self): self.unet_node("SDXL", boxes="mixed")
    def test_sd15_mixed_native_sampling(self): self.unet_node("SD1.5", boxes="mixed")

    def test_regional_lora_uses_native_hooks_and_restores_shared_model(self):
        self.unet_node("SD1.5", lora_trial=True)

    def test_sdxl_shape_mask_native_sampling(self): self.unet_node("SDXL", boxes="shape")
    def test_sd15_shape_mask_native_sampling(self): self.unet_node("SD1.5", boxes="shape")

    def unet_node(self, family, boxes=False, lora_trial=False):
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
        pipe = chars.CharacterPipe((chars.Character('left', x=.3 if boxes else .25, bbox=(.1,.1,.5,.9) if boxes else None), chars.Character('right', x=.65 if boxes else .75, bbox=(.4,.1,.9,.9) if boxes else None)))
        if boxes == "mixed":
            pipe = chars.CharacterPipe((chars.Character('left', x=.25), chars.Character('right', x=.75, bbox=(.6,.2,.9,.8))))
        if boxes == "shape":
            mask = torch.zeros(1,64,64); mask[:,8:56,8:24]=1; mask[:,8:24,24:48]=1
            region = importlib.import_module(PKG+'.region_mask').prepare_mask(mask, margin=0)
            pipe = chars.CharacterPipe((chars.Character('left', region_mask=region), chars.Character('right', x=.75)))
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
        if boxes == "shape":
            self.assertEqual(audit['mask_slots'], [1])
            self.assertEqual(json.loads(restored_pipe.generation_json)['character_masks'][0], region.record())
        if lora_trial:
            self.check_regional_lora(model, clip, vae, pipe, nodes)
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

    def check_regional_lora(self, model, clip, vae, pipe, node_module):
        import folder_paths
        model.model.model_config.unet_config['num_res_blocks'] = [1, 1]
        clip.cond_stage_model = torch.nn.Linear(1, 1)
        weights = {}
        for key, value in model.model.state_dict().items():
            if '.attn2.to_v.weight' in key:
                stem = key[:-len('.weight')]
                weights[stem + '.lora_up.weight'] = torch.randn(value.shape[0], 2) * .3
                weights[stem + '.lora_down.weight'] = torch.randn(2, value.shape[1]) * .3
        self.assertTrue(weights)
        original = {k: v.clone() for k,v in model.model.state_dict().items()}
        import latent_preview
        first_steps = []
        def generate(p):
            captures = []
            def capture(step, x0, x, total):
                if step == 0: captures.append(x0.detach().clone())
            with torch.no_grad(), patch.object(latent_preview, 'prepare_callback', return_value=capture):
                result = node_module.RSMultiCharacterSampler().generate(model, clip, vae, p, 'common', 'negative',
                    width=64, height=64, seed=771, steps=2, cfg=3., sampler_name='euler_ancestral', scheduler='normal',
                    region_feather=0., autosave=False)['result'][1]['samples']
            first_steps.append(captures[0])
            return result
        with tempfile.TemporaryDirectory() as tmp:
            file = str(Path(tmp) / 'synthetic.pt')
            torch.save(weights, file)
            with patch.object(folder_paths, 'get_filename_list', return_value=['synthetic.pt']), \
                 patch.object(folder_paths, 'get_full_path_or_raise', return_value=file):
                base = generate(pipe)
                left = replace(pipe, characters=(replace(pipe.characters[0],lora_name='synthetic.pt',lora_clip_strength=0.),pipe.characters[1]))
                loader = importlib.import_module(PKG + '.regional_lora').RegionalLoras
                repeated = loader(model, clip, (left.characters[0], replace(left.characters[0], lora_clip_strength=.8)))
                self.assertIs(repeated.hooks[0], repeated.hooks[1])
                right = replace(pipe, characters=(pipe.characters[0],replace(pipe.characters[1],lora_name='synthetic.pt',lora_clip_strength=0.)))
                a,b = generate(left),generate(right)
                self.assertFalse(torch.equal(a,base));self.assertFalse(torch.equal(b,base));self.assertFalse(torch.equal(a,b))
                base_step, left_step, right_step = first_steps[:3]
                torch.testing.assert_close(left_step[...,4:],base_step[...,4:],atol=1e-5,rtol=1e-5)
                torch.testing.assert_close(right_step[...,:4],base_step[...,:4],atol=1e-5,rtol=1e-5)
                self.assertGreater((left_step[...,:4]-base_step[...,:4]).abs().max().item(),1e-4)
                self.assertGreater((right_step[...,4:]-base_step[...,4:]).abs().max().item(),1e-4)
                self.assertTrue(torch.equal(generate(pipe),base))
                zero = replace(left,characters=(replace(left.characters[0],lora_strength=0.),left.characters[1]))
                self.assertTrue(torch.equal(generate(zero),base))
                with patch.object(model.model, 'apply_model', side_effect=RuntimeError('injected denoising failure')):
                    with self.assertRaisesRegex(RuntimeError, 'injected denoising failure'):
                        generate(left)
                self.assertTrue(torch.equal(generate(pipe),base))
                for key,value in original.items():self.assertTrue(torch.equal(model.model.state_dict()[key],value),key)
                missing = replace(left,characters=(replace(left.characters[0],lora_name='../outside.pt'),left.characters[1]))
                with self.assertRaisesRegex(ValueError, 'missing'):generate(missing)
                self.assertTrue(torch.equal(generate(pipe),base))

    def joint(self, family, boxes=False):
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
        if boxes == "mixed":
            masks[0]=1
            masks[1].zero_()
            masks[1,1:3,3:7]=1
            boxes = (False, True)
        elif boxes == "shape":
            masks.zero_()
            masks[0,0:3,0:2]=1; masks[0,1,2:5]=1
            masks[1,1:4,6:8]=1; masks[1,1,3:6]=1
            boxes = (True, True)
        elif boxes:
            masks.zero_()
            masks[0,1:3,1:5]=1
            masks[1,1:3,3:7]=1
        r = j.JointRouting(family,conditions,masks,defaults,audit,boxes=boxes)
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
    def test_krea_mixed_native_attention_and_negative(self): self.joint('Krea2',boxes='mixed')
    def test_moss_mixed_native_attention_and_negative(self): self.joint('MOSS',boxes='mixed')

    def test_krea_boxes_native_attention_and_negative(self): self.joint('Krea2',boxes=True)
    def test_moss_boxes_native_attention_and_negative(self): self.joint('MOSS',boxes=True)
    def test_krea_shape_native_attention_and_negative(self): self.joint('Krea2',boxes='shape')
    def test_moss_shape_native_attention_and_negative(self): self.joint('MOSS',boxes='shape')

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
