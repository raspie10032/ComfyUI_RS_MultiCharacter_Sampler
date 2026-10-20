"""FLUX caption isolation and native small-model integration (no real weights)."""
import importlib
import os
from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = Path(__file__).resolve().parents[1].name
f = importlib.import_module(pkg + '.flux_engine')
defaults = importlib.import_module(pkg + '.nodes').DEFAULTS


class PositionTests(unittest.TestCase):
    def test_flux3_diffusers_lora_names_preserve_native_fused_offsets(self):
        fused = ('diffusion_model.content_mode_blocks.image.0.qkv.weight', (0, 8, 8))
        mapping = {
            'diffusion_model.content_mode_blocks.image.0.k_proj': fused,
            'diffusion_model.txt_mode_blocks.2.q_proj': 'native_text.weight',
            'diffusion_model.single_blocks.3.attn_out': 'native_output.weight',
            'diffusion_model.unrelated.q_proj': 'unrelated.weight',
            'transformer.txt_mode_blocks.2.attn.to_q': 'future_core_override',
        }
        f.extend_flux3_lora_map(mapping)
        self.assertIs(mapping['transformer.mode_blocks.image.0.attn.to_k'], fused)
        self.assertEqual(mapping['transformer.single_transformer_blocks.3.attn.to_out.0'], 'native_output.weight')
        self.assertEqual(mapping['transformer.txt_mode_blocks.2.attn.to_q'], 'future_core_override')
        self.assertNotIn('transformer.unrelated.attn.to_q', mapping)
        self.assertEqual(mapping['diffusion_model.content_mode_blocks.image.0.k_proj'], fused)

    def test_flux3_positions_match_independently_encoded_captions(self):
        torch.manual_seed(3)
        raw = torch.randn(1, 17, 2, 128)
        def rotate(positions):
            out = raw.clone()
            omega = 10000. ** (-torch.arange(0, 32, 2) / 32)
            pairs = raw[..., -32:].unflatten(-1, (16, 2))
            angle = positions[None, :, None, None] * omega
            a, b = pairs[..., 0], pairs[..., 1]
            out[..., -32:] = torch.stack((a*angle.cos()-b*angle.sin(), a*angle.sin()+b*angle.cos()), -1).flatten(-2)
            return out
        native = rotate(torch.tensor([0]*8 + list(range(9))))
        expected = rotate(torch.tensor([0]*8 + [0,1] + [0,1,2] + [0,1,2,3]))
        for shaped in (False, True):
            value = native.transpose(1, 2) if shaped else native.flatten(2)
            out = f.reset_flux3_positions(value, 2, [2,3,4], 8, shaped)
            ref = expected.transpose(1, 2) if shaped else expected.flatten(2)
            torch.testing.assert_close(out, ref, atol=1e-6, rtol=1e-6)


@unittest.skipUnless(os.environ.get('RS_MC_TEST_COMFYUI'), 'Set RS_MC_TEST_COMFYUI for native CPU integrations')
class NativeFluxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.environ['RS_MC_TEST_COMFYUI'])
        from comfy.cli_args import args
        args.cpu = True
        import comfy.ops
        import comfy.model_management as mm
        cls.mm, cls.ops = mm, comfy.ops.manual_cast
        cls.old_training = getattr(mm, 'in_training', None)
        if cls.old_training is not None:
            mm.in_training = True

    @classmethod
    def tearDownClass(cls):
        if cls.old_training is not None:
            cls.mm.in_training = cls.old_training
        sys.path.remove(os.environ['RS_MC_TEST_COMFYUI'])

    def test_flux3_diffusers_adapters_match_native_fused_and_separate_weights(self):
        from types import SimpleNamespace
        from comfy import model_base, lora
        if not hasattr(model_base, 'Flux3'):
            self.skipTest('FLUX3 is not available in this ComfyUI')
        from comfy.ldm.flux3.model import Flux3
        for fused in (False, True):
            model = model_base.Flux3.__new__(model_base.Flux3)
            torch.nn.Module.__init__(model)
            model.model_config = SimpleNamespace(unet_config={})
            model.diffusion_model = Flux3(hidden_size=256, num_heads=2, depth=1,
                depth_single_blocks=1, fused_qkv=fused, dtype=torch.float32, operations=self.ops)
            mapping = f.extend_flux3_lora_map(lora.model_lora_keys_unet(model, {}))
            weights = {}
            for prefix in ('transformer.mode_blocks.image.0', 'transformer.txt_mode_blocks.0',
                           'transformer.single_transformer_blocks.0'):
                for projection in ('to_q', 'to_k', 'to_v', 'to_out.0'):
                    key = prefix + '.attn.' + projection
                    weights[key + '.lora_A.weight'] = torch.randn(2, 256)
                    weights[key + '.lora_B.weight'] = torch.randn(256, 2)
            patches = lora.load_lora(weights, mapping, log_missing=False)
            self.assertEqual(len(patches), 12)
            self.assertEqual(sum(isinstance(k, tuple) for k in patches), 9 if fused else 0)

    def run_native(self, family, flow_map=False, boxes=False):
        from comfy import model_base
        if not hasattr(model_base, {'FLUX1':'Flux', 'FLUX2':'Flux2', 'FLUX3':'Flux3'}[family]):
            self.skipTest(f'{family} is not available in this ComfyUI')
        from comfy.ldm.flux.model import FluxParams
        if 'global_modulation' not in FluxParams.__annotations__:
            self.skipTest('FLUX routing needs current ComfyUI patch support')
        torch.manual_seed(9)
        if family == 'FLUX3':
            from comfy.ldm.flux3.model import Flux3
            net = Flux3(hidden_size=256, num_heads=2, depth=1, depth_single_blocks=2,
                        flow_map=flow_map, operations=self.ops, dtype=torch.float32)
            features, channels = 20480, 128
        else:
            from comfy.ldm.flux.model import Flux
            features, channels = 64, 16
            # Older native FLUX implementations select text IDs from axes_dim
            # and do not expose the newer txt_ids_dims constructor option.
            position_options = ({'txt_ids_dims': [] if family == 'FLUX1' else [0]}
                                if 'txt_ids_dims' in FluxParams.__annotations__ else {})
            net = Flux(in_channels=channels, out_channels=channels, vec_in_dim=32 if family=='FLUX1' else None,
                       context_in_dim=features, hidden_size=128, mlp_ratio=2., num_heads=2,
                       depth=1, depth_single_blocks=1, axes_dim=[16,24,24], theta=10000,
                       patch_size=2, qkv_bias=True, guidance_embed=family=='FLUX1',
                       global_modulation=family=='FLUX2',
                       operations=self.ops, dtype=torch.float32, **position_options)
        for p in net.parameters():
            p.data.uniform_(-.03, .03)
        x, t = torch.randn(1,channels,4,8), torch.tensor([.5])
        common = torch.randn(1,3,features)
        conditions = [(torch.randn(1,i,features), {}) for i in (4,5)]
        masks = torch.zeros(2,4,8)
        masks[0,:,:4], masks[1,:,4:] = 1, 1
        if boxes == 'mixed':
            masks[0] = 1
            masks[1].zero_()
            masks[1, 1:3, 3:7] = 1
            boxes = (False, True)
        elif boxes == 'shape':
            masks.zero_()
            masks[0,0:3,0:2]=1; masks[0,1,2:5]=1
            masks[1,1:4,6:8]=1; masks[1,1,3:6]=1
            boxes = (True, True)
        elif boxes:
            masks.zero_()
            masks[0,1:3,1:5], masks[1,1:3,3:7] = 1, 1
        audit = dict(forwards=[],cross_calls=0,self_calls=0,text_refiner_calls=0,restored_forwards=0)
        routing = f.FluxRouting(family,conditions,masks,defaults,audit,boxes=boxes)
        routing.sigmas = [1., .5, .1]
        options = dict(cond_or_uncond=[0],sigmas=t, sample_sigmas=torch.tensor([1.,.5,.1,0.]),
                       optimized_attention_override=routing.attention)
        if family != 'FLUX3':
            options['patches'] = {'post_input':[routing.text_positions]}
        def executor(*a, **kw):
            return net._forward(*a, **kw)
        executor.class_obj = net
        kwargs = {} if family == 'FLUX3' else dict(y=torch.randn(1,32) if family=='FLUX1' else None, guidance=torch.tensor([3.5]))
        forward = routing.flux3_forward if family=='FLUX3' else routing.flux_forward
        with torch.no_grad():
            out = forward(executor, x, t, common, transformer_options=options, **kwargs)
            self.assertEqual(out.shape, x.shape)
            self.assertTrue(torch.isfinite(out).all())
            self.assertEqual(audit['cross_calls'], 2)
            self.assertIsNone(routing.state)
            # Negative branch must exactly match unmodified native attention.
            negative_options = {**options, 'cond_or_uncond':[1]}
            native_options = {k:v for k,v in options.items() if k not in ('optimized_attention_override','patches')}
            native = executor(x,t,common,transformer_options=native_options,**kwargs)
            negative = forward(executor,x,t,common,transformer_options=negative_options,**kwargs)
            torch.testing.assert_close(native,negative,atol=0,rtol=0)
            # ComfyUI can combine positive and negative branches into one batch.
            # Native pooled encodes / guidance must follow each sliced image.
            batch_kwargs = {k: v.repeat(2, *([1]*(v.ndim-1))) if isinstance(v, torch.Tensor) else v
                            for k, v in kwargs.items()}
            batched = forward(executor, x.repeat(2,1,1,1), t.repeat(2), common.repeat(2,1,1),
                              transformer_options={**options, 'cond_or_uncond':[0,1]}, **batch_kwargs)
            torch.testing.assert_close(batched, torch.cat([out, negative]), atol=1e-6, rtol=1e-5)
            self.assertIsNone(routing.state)
            if family == 'FLUX3' and not flow_map:
                refined, _ = net.preprocess_conds(common)
                cached = forward(executor,x,t,None,txt_states=refined,transformer_options=options)
                torch.testing.assert_close(out,cached,atol=0,rtol=0)
            def broken(*args, **kwargs):
                executor(*args, **kwargs)
                raise RuntimeError('injected denoising failure')
            broken.class_obj = net
            with self.assertRaisesRegex(RuntimeError, 'injected denoising failure'):
                forward(broken, x, t, common, transformer_options=options, **kwargs)
            self.assertIsNone(routing.state)
            recovered = forward(executor, x, t, common, transformer_options=options, **kwargs)
            torch.testing.assert_close(out, recovered, atol=0, rtol=0)
            self.assertIs(routing.conditions, conditions)

    def test_flux1(self): self.run_native('FLUX1')
    def test_flux1_shape(self): self.run_native('FLUX1',boxes='shape')
    def test_flux2_shape(self): self.run_native('FLUX2',boxes='shape')
    def test_flux3_shape(self): self.run_native('FLUX3',boxes='shape')
    def test_flux2(self): self.run_native('FLUX2')
    def test_flux3_base(self): self.run_native('FLUX3')
    def test_flux3_flow_map(self): self.run_native('FLUX3',flow_map=True)
    def test_flux1_boxes(self): self.run_native('FLUX1',boxes=True)
    def test_flux2_boxes(self): self.run_native('FLUX2',boxes=True)
    def test_flux3_boxes(self): self.run_native('FLUX3',boxes=True)
    def test_flux1_mixed(self): self.run_native('FLUX1',boxes='mixed')
    def test_flux2_mixed(self): self.run_native('FLUX2',boxes='mixed')
    def test_flux3_mixed(self): self.run_native('FLUX3',boxes='mixed')
    def test_flux3_flow_map_mixed(self): self.run_native('FLUX3',flow_map=True,boxes='mixed')


if __name__ == '__main__':
    unittest.main()
