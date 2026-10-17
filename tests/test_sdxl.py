import importlib
from pathlib import Path
import sys
import tempfile
import unittest
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = Path(__file__).resolve().parents[1].name
s = importlib.import_module(pkg + '.sdxl_engine')
n = importlib.import_module(pkg + '.nodes')
c = importlib.import_module(pkg + '.characters')
m = importlib.import_module(pkg + '.metadata')


class SDXLTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(429)
        masks = torch.zeros(2, 4, 8)
        masks[0, :, :4] = 1
        masks[1, :, 4:] = 1
        conditions = [[torch.randn(1, length, 6), {}] for length in (3, 5)]
        self.audit = {}
        self.r = s.SDXLRouting(conditions, masks, n.DEFAULTS, self.audit)
        self.options = {'cond_or_uncond': [0, 1], 'original_shape': [2, 4, 4, 8], 'n_heads': 2, 'sigmas': torch.tensor([10.])}

    def test_grid_tracks_downsampled_non_square_and_odd_resolutions(self):
        self.assertEqual(s.attention_grid([2, 4, 96, 128], 3072), (48, 64))
        self.assertEqual(s.attention_grid([2, 4, 66, 98], 33*49), (33, 49))
        self.assertEqual(s.attention_grid([2, 4, 66, 98], 17*25), (17, 25))
        with self.assertRaises(ValueError): s.attention_grid([2, 4, 96, 128], 1337)

    def test_native_negative_and_foreign_text_exclusion_for_both_cfg_orders(self):
        for kinds in ([0, 1], [1, 0], [0], [1]):
            options = {**self.options, 'cond_or_uncond': kinds}
            count = len(kinds)
            q = torch.randn(count, 8, 8, dtype=torch.float64)
            k = torch.randn(count, 10, 8, dtype=torch.float64)
            v = torch.randn_like(k)
            self.r.state = dict(kinds=kinds, text_lengths=[2,3,5], common_prior=.3,
                                character_value_gain=1.7, spatial_separation=.9, cross_calls=0)
            self.audit.update(cross_calls=0, token_grids=[])
            actual = self.r.cross(q,k,v,options)
            groups = self.r.groups[(2,4,q.device)]
            expected = torch.empty_like(q)
            for batch,kind in enumerate(kinds):
                if kind == 1:
                    expected[batch] = s.sdpa(q[batch:batch+1].reshape(1,8,2,4), k[batch:batch+1,:2].reshape(1,2,2,4), v[batch:batch+1,:2].reshape(1,2,2,4))[0]
                else:
                    allowed = torch.full((8,10), -torch.inf, dtype=q.dtype)
                    allowed[:,:2] = torch.log(torch.tensor(.3/2, dtype=q.dtype))
                    for group,start,end in [(groups[0],2,5),(groups[1],5,10)]:
                        allowed[group,start:end] = torch.log(torch.tensor(1/(end-start), dtype=q.dtype))
                    values=v[batch:batch+1].clone(); values[:,2:] *= 1.7
                    expected[batch] = s.sdpa(q[batch:batch+1].reshape(1,8,2,4), k[batch:batch+1].reshape(1,10,2,4), values.reshape(1,10,2,4),allowed)[0]
            torch.testing.assert_close(actual,expected,atol=1e-12,rtol=1e-12)
            altered=v.clone();altered[:,5:]+=1000
            other=self.r.cross(q,k,altered,options)
            for batch,kind in enumerate(kinds):
                if kind == 1: torch.testing.assert_close(actual[batch],other[batch],atol=0,rtol=0)
                else: torch.testing.assert_close(actual[batch,groups[0]],other[batch,groups[0]],atol=0,rtol=0)

    def test_scope_cleanup_on_failure_and_native_adm_passthrough(self):
        self.r.sigmas = [10.,5.,1.]
        self.audit.update(forwards=[],restored_forwards=0)
        context=torch.randn(2,2,6)
        adm=torch.randn(2,2816)
        def broken(x, t, joined, y, control, options, **kw):
            self.assertIs(y, adm)
            self.assertEqual(joined.shape,(2,10,6))
            torch.testing.assert_close(joined[1,2:],torch.zeros_like(joined[1,2:]))
            self.assertIsNotNone(self.r.state)
            raise RuntimeError('interrupted')
        with self.assertRaisesRegex(RuntimeError,'interrupted'):
            self.r.forward(broken,torch.zeros(2,4,4,8),torch.tensor([1.]),context,adm,None,self.options)
        self.assertIsNone(self.r.state)
        self.assertFalse(self.r.biases)
        self.assertEqual(self.audit['restored_forwards'],1)
        def fail(*args):
            self.r.groups['x']=123;self.r.biases['x']=123
            raise RuntimeError('interrupted')
        with self.assertRaisesRegex(RuntimeError,'interrupted'):
            self.r.sample(fail,None,torch.tensor([10.,5.,1.,0.]))
        self.assertIsNone(self.r.sigmas)
        self.assertFalse(self.r.groups)
        self.assertFalse(self.r.biases)

    def test_sdxl_metadata_roundtrip_does_not_claim_anima(self):
        pipe=c.CharacterPipe((c.Character('woman',x=.2,y=.7),),'campus','bad')
        record=m.build_record(pipe,{**n.DEFAULTS,'seed':123},{},[[.2,.7]],{'spatial_slots':1},engine='sdxl-spatial-alpha-1')
        with tempfile.TemporaryDirectory() as tmp:
            for fmt in m.FORMATS:
                path=m.save_image(Image.new('RGB',(16,16)),Path(tmp)/'test',record,fmt)
                with Image.open(path) as image:
                    restored=m.read_record(image)
                    self.assertEqual(restored,record)
                    self.assertEqual(m.pipe_from_record(restored).characters,pipe.characters)
                    if fmt=='PNG': self.assertEqual(image.info['Source'],'SDXL (local)')
                    self.assertNotIn('workflow',image.info)

if __name__=='__main__': unittest.main()
