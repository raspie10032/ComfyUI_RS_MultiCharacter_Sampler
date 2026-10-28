"""Reference ownership with native token orders, not full-size model doubles."""
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
ref = importlib.import_module(Path(__file__).resolve().parents[1].name + '.native_reference')

class NativeReferenceOwnership(unittest.TestCase):
    def test_unrelated_reference_cannot_directly_enter_another_slot(self):
        for family in ('Krea2', 'FLUX1', 'FLUX2', 'FLUX3'):
            for pre in (False, True):
                with self.subTest(family=family, pre_shaped=pre):
                    torch.manual_seed(348)
                    lengths, nimage, nref = [2, 3, 4], 4, [2, 3]
                    ntext, nr = sum(lengths), sum(nref)
                    if family == 'Krea2': tstart, rstart, istart = 0, ntext, ntext+nr
                    elif family == 'FLUX3': istart, rstart, tstart = 0, nimage, nimage+nr
                    else: tstart, istart, rstart = 0, ntext, ntext+nimage
                    routing=SimpleNamespace(family=family,
                        state=dict(image_tokens=nimage, lengths=lengths,
                            groups=[torch.tensor([0,1]),torch.tensor([2,3])],
                            common=.25, separation=1., gain=1.3, record=dict(joint_calls=0)),
                        reference_lengths=nref,
                        reference_plan=[dict(slot=0,strength=1.),dict(slot=1,strength=1.)],
                        reference_audit=dict(calls=0,blocks_seen=[]),
                        audit=dict(cross_calls=0,self_calls=0))
                    q,k,v=[torch.randn(1,ntext+nimage+nr,8) for _ in range(3)]
                    if pre:q,k,v=[x.unflatten(-1,(2,4)).transpose(1,2) for x in (q,k,v)]
                    def attention(q,k,v,heads,mask=None,**kw):
                        if not pre:q,k,v=[x.unflatten(-1,(heads,-1)).transpose(1,2) for x in (q,k,v)]
                        out=F.scaled_dot_product_attention(q,k,v,attn_mask=mask)
                        return out if pre else out.transpose(1,2).flatten(2)
                    first=ref.reference_joint(routing,attention,q,k,v,2,skip_reshape=pre,skip_output_reshape=pre)
                    axis=2 if pre else 1
                    modified=v.clone(); index=[slice(None)]*v.ndim
                    index[axis]=slice(rstart+nref[0],rstart+nr);modified[tuple(index)]+=100
                    second=ref.reference_joint(routing,attention,q,k,modified,2,skip_reshape=pre,skip_output_reshape=pre)
                    target0=torch.tensor([istart,istart+1]);target1=torch.tensor([istart+2,istart+3])
                    self.assertTrue(torch.equal(first.index_select(axis,target0),second.index_select(axis,target0)))
                    self.assertFalse(torch.equal(first.index_select(axis,target1),second.index_select(axis,target1)))
                    self.assertTrue(torch.isfinite(first).all())

    def test_reference_asset_versions_are_pinned_and_excluded_families_unchanged(self):
        assets=importlib.import_module(Path(__file__).resolve().parents[1].name+'.reference_assets').CATALOG
        self.assertIn('v2_r64', assets['krea_edit']['file'])
        self.assertEqual(assets['anima_frame']['revision'],'fed1e98a11a9b81d4ad274fd23cacc531fd4617e')
        self.assertEqual(assets['moss_edit']['file'],'moss_edit_lora_poc.safetensors')
        self.assertEqual(assets['sd15_adapter']['file'],'models/ip-adapter-plus_sd15.safetensors')
        self.assertEqual(assets['sdxl_adapter']['file'],'sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors')

if __name__=='__main__':unittest.main()
