"""Optional real CUDA backend tests; never install xFormers into the user's host.

RS_MC_TEST_XFORMERS=1 RS_MC_TEST_COMFYUI=/path/to/ComfyUI \
    python -m unittest discover -s tests -p test_xformers.py -v

Run this file alone: the CPU integration suite deliberately sets args.cpu=True.
These small random tensors test kernel/API compatibility, not image quality.
"""
import importlib
import os
from pathlib import Path
import sys
import unittest

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))


@unittest.skipUnless(os.environ.get('RS_MC_TEST_XFORMERS') == '1',
                     'Explicit isolated CUDA/xFormers test required')
class XFormersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # An explicitly requested run must fail if its real backend is missing.
        import xformers.ops
        sys.path.insert(0, os.environ['RS_MC_TEST_COMFYUI'])
        from comfy.cli_args import args
        args.cpu = False
        args.disable_xformers = False
        from comfy.ldm.modules import attention
        from comfy import model_management
        if not torch.cuda.is_available() or not model_management.xformers_enabled():
            raise RuntimeError('The requested real CUDA/xFormers backend is unavailable')
        cls.native = staticmethod(attention.attention_xformers)
        cls.attention_module = attention
        cls.routing = importlib.import_module(ROOT.name + '.routing')
        cls.joint = importlib.import_module(ROOT.name + '.joint_engine')
        torch.manual_seed(107)

    def tensors(self, length, dtype, batch=1):
        return [torch.randn(batch, length, 128, device='cuda', dtype=dtype) for _ in range(3)]

    def assert_close(self, actual, expected):
        self.assertTrue(torch.isfinite(actual).all())
        tolerance = .003 if actual.dtype == torch.float16 else .03
        torch.testing.assert_close(actual, expected, rtol=tolerance, atol=tolerance)

    def test_native_masked_and_unmasked_layouts(self):
        for dtype in (torch.float16, torch.bfloat16):
            for shaped in (False, True):
                for output_shaped in (False, True):
                    for masked in (False, True):
                        with self.subTest(dtype=dtype, shaped=shaped,
                                          output_shaped=output_shaped, masked=masked):
                            q, k, v = self.tensors(17, dtype)
                            heads = [t.unflatten(-1, (2, 64)).transpose(1, 2) for t in (q, k, v)]
                            bias = q.new_zeros((17, 17)) if masked else None
                            if bias is not None:
                                bias[:, 5:9] = -torch.inf
                            expected = F.scaled_dot_product_attention(*heads, attn_mask=bias)
                            if not output_shaped:
                                expected = expected.transpose(1, 2).flatten(2)
                            actual = self.native(*(heads if shaped else (q, k, v)), 2,
                                                 mask=bias, skip_reshape=shaped,
                                                 skip_output_reshape=output_shaped)
                            self.assert_close(actual, expected)

    def test_regional_cross_matches_real_xformers_dense_mask(self):
        for dtype in (torch.float16, torch.bfloat16):
            with self.subTest(dtype=dtype):
                q = self.tensors(8, dtype, batch=2)[0]
                _, k, v = self.tensors(9, dtype, batch=2)
                groups = [torch.tensor([0, 2, 4, 6], device='cuda'),
                          torch.tensor([1, 3, 5, 7], device='cuda')]
                bias = q.new_full((2, 1, 8, 9), -torch.inf)
                bias[:, :, :, :2] = 0
                bias[0, 0, groups[0], 2:5] = 0
                bias[0, 0, groups[1], 5:9] = 0
                expected = self.native(q, k, v, 2, mask=bias)
                actual = self.routing.route_cross(
                    *(t.unflatten(-1, (2, 64)) for t in (q, k, v)),
                    groups, [2, 3, 4], [0, 1])
                self.assert_close(actual, expected)

    def test_native_crossattention_projects_through_real_kernel(self):
        from unittest.mock import patch
        import comfy.ops
        for dtype in (torch.float16, torch.bfloat16):
            with self.subTest(dtype=dtype), torch.inference_mode():
                layer = self.attention_module.CrossAttention(
                    128, context_dim=128, heads=2, dim_head=64,
                    operations=comfy.ops.manual_cast).to(device='cuda', dtype=dtype)
                for parameter in layer.parameters():
                    torch.nn.init.uniform_(parameter, -.05, .05)
                x = self.tensors(17, dtype)[0]
                context = self.tensors(9, dtype)[0]
                q, k, v = layer.to_q(x), layer.to_k(context), layer.to_v(context)
                expected = F.scaled_dot_product_attention(
                    *(t.unflatten(-1, (2, 64)).transpose(1, 2) for t in (q, k, v)))
                expected = layer.to_out(expected.transpose(1, 2).flatten(2))
                with patch.object(self.attention_module, 'optimized_attention', wraps=self.native) as calls:
                    actual = layer(x, context=context)
                self.assertEqual(calls.call_count, 1)
                self.assert_close(actual, expected)

    def test_joint_routing_uses_real_backend_with_uneven_caption_lengths(self):
        from unittest.mock import patch
        import xformers.ops
        for family in ('Krea2', 'MOSS'):
            for dtype in (torch.float16, torch.bfloat16):
                for shaped in (False, True):
                    for output_shaped in (False, True):
                        with self.subTest(family=family, dtype=dtype, shaped=shaped,
                                          output_shaped=output_shaped):
                            router = self.joint.JointRouting(family, [], None, {},
                                                            dict(cross_calls=0, self_calls=0,
                                                                 text_refiner_calls=0))
                            router.state = dict(lengths=[2, 3, 4], image_tokens=8,
                                groups=[torch.tensor([0, 1, 4, 5], device='cuda'),
                                        torch.tensor([2, 3, 6, 7], device='cuda')],
                                common=.3, gain=1.2, separation=.5,
                                record=dict(joint_calls=0, text_refiner_calls=0))
                            qkv = self.tensors(17, dtype)
                            if shaped:
                                qkv = [t.unflatten(-1, (2, 64)).transpose(1, 2) for t in qkv]
                            options = dict(skip_reshape=shaped, skip_output_reshape=output_shaped,
                                           transformer_options={'block_index': 0})

                            def pytorch(q, k, v, heads, mask=None, **kwargs):
                                if not kwargs.get('skip_reshape'):
                                    q, k, v = [t.unflatten(-1, (heads, -1)).transpose(1, 2)
                                               for t in (q, k, v)]
                                out = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
                                return out if kwargs.get('skip_output_reshape') else out.transpose(1, 2).flatten(2)

                            expected = router.attention(pytorch, *qkv, 2, **options)
                            real_kernel = xformers.ops.memory_efficient_attention
                            with patch.object(xformers.ops, 'memory_efficient_attention', wraps=real_kernel) as calls:
                                actual = router.attention(self.native, *qkv, 2, **options)
                            self.assertGreater(calls.call_count, 1)
                            self.assert_close(actual, expected)

