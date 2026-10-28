"""Reference preparation boundaries and exact attention-connectivity checks."""
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
PKG = Path(__file__).resolve().parents[1].name
ref = importlib.import_module(PKG+'.anima_ref_frame')
compact = importlib.import_module(PKG+'.reference_spatial')
routing = importlib.import_module(PKG+'.routing')
interaction = importlib.import_module(PKG+'.interaction')


class ReferenceOptimizationTests(unittest.TestCase):
    def test_encode_only_active_grids_and_share_duplicate_source(self):
        plan = SimpleNamespace(reference_scale=1.)
        source = SimpleNamespace(source='shared', image=lambda:np.zeros((8,8,3),dtype=np.uint8))
        for end, stages in ((1,1),(8,1),(9,2),(16,2),(17,3),(30,3)):
            with self.subTest(end=end), patch.object(ref, 'encode_reference',
                    side_effect=lambda p,v,w,h:torch.ones(1,16,1,h//8,w//8)) as encode:
                first, grids, audit = ref.prepare_reference_latents(plan, [(0,source),(1,source)],
                    None, 1728,1152,30,.67,True,end)
                self.assertEqual(encode.call_count,stages)
                self.assertEqual(len(grids),stages)
                self.assertEqual(first.shape[2],2)
                self.assertEqual(audit['skipped_reference_stages'],3-stages)
                for value in grids.values():
                    self.assertTrue(torch.equal(value[:,:,:1],value[:,:,1:]))
        for end in (True,0,31,-1,1.5):
            with self.assertRaises(ValueError):
                ref.prepare_reference_latents(plan,[(0,source)],None,1728,1152,30,.67,True,end)

    def test_full_reference_unchanged_and_global_reference_scaled(self):
        plan = SimpleNamespace(reference_scale=.8,pixels=torch.zeros(1,8,8,3))
        with patch.object(ref,'encode_reference',side_effect=lambda p,v,w,h:torch.ones(1,16,1,h//8,w//8)) as encode:
            first, grids, audit = ref.prepare_reference_latents(plan,[],None,1728,1152,30,.67,False,8)
        self.assertIsNone(grids)
        self.assertEqual(encode.call_count,1)
        self.assertEqual(tuple(first.shape[-2:]),(116,172))
        self.assertEqual(audit['reference_encode_grids'],[dict(width=1376,height=928)])

    def test_compact_bias_matches_every_dense_row_with_overlap_background(self):
        torch.manual_seed(81)
        for boxes in (False,True):
            masks=torch.zeros(2,4,6)
            if boxes:
                masks[0,1:,:4]=1;masks[1,1:,2:]=1
            else:
                masks[0,:,:3]=1;masks[1,:,3:]=1
            groups=routing.token_groups(masks,4,6,boxes=boxes)
            for sep,exclusive in ((0.,None),(.9,None),(.2,.99),(.4,0.)):
                for dtype in (torch.float32,torch.bfloat16):
                    q,k,v=[torch.randn(2,72,2,8,dtype=dtype) for _ in range(3)]
                    dense=interaction.protected_self_bias(groups,24,q,sep,exclusive)
                    dense=torch.nn.functional.pad(dense,(0,48,0,48))
                    bias=compact.compact_bias(groups,24,72,q,sep,exclusive)
                    actual_rows=torch.zeros_like(dense)
                    for row,(_,indices) in zip(bias.rows,bias.cells):actual_rows[indices]=row
                    self.assertTrue(torch.equal(actual_rows,dense))
                    expected=routing.sdpa(q,k,v,dense)
                    actual=compact.compact_attention(q,k,v,bias)
                    tolerance=2e-6 if dtype==torch.float32 else .008
                    torch.testing.assert_close(actual,expected,atol=tolerance,rtol=tolerance)
                    self.assertLess(bias.rows.numel(),dense.numel()/10)

    def test_cancellation_releases_stage_references(self):
        plan=ref.ReferencePlan(torch.zeros(1,8,8,3),'unused',1.,4.5,'apg',True)
        rt=ref.FrameRuntime(plan,torch.zeros(1,16,1,8,8),{})
        rt.stage_references={(8,8):torch.zeros(1,16,1,8,8)}
        with self.assertRaisesRegex(RuntimeError,'cancel'):
            rt.sample(lambda:(_ for _ in ()).throw(RuntimeError('cancel')))
        self.assertFalse(rt.stage_references)
        self.assertIsNone(rt.weights)


if __name__=='__main__':unittest.main()
