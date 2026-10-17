import copy
import importlib
import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch
import torch.nn.functional as F
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = Path(__file__).resolve().parents[1].name
j = importlib.import_module(pkg+'.joint_engine')
n = importlib.import_module(pkg+'.nodes')
m = importlib.import_module(pkg+'.metadata')
c = importlib.import_module(pkg+'.characters')


def attention(q,k,v,heads,mask=None,skip_reshape=False,skip_output_reshape=False,**kwargs):
    if not skip_reshape:
        q,k,v = [a.unflatten(-1,(heads,-1)).transpose(1,2) for a in (q,k,v)]
    out=F.scaled_dot_product_attention(q,k,v,attn_mask=mask)
    return out if skip_output_reshape else out.transpose(1,2).flatten(2)


class JointTests(unittest.TestCase):
    def make(self,family):
        masks=torch.zeros(2,2,4);masks[0,:,:2]=1;masks[1,:,2:]=1
        audit=dict(cross_calls=0,self_calls=0,text_refiner_calls=0,forwards=[],restored_forwards=0)
        r=j.JointRouting(family,[(torch.randn(1,3,6),{}),(torch.randn(1,4,6),{})],masks,n.DEFAULTS,audit)
        r.sigmas=[10.,5.,1.]
        r.state=dict(lengths=[2,3,4],groups=[torch.tensor([0,1,4,5]),torch.tensor([2,3,6,7])],
                     image_tokens=8,common=.3,gain=1.2,separation=.5,
                     record=dict(joint_calls=0,text_refiner_calls=0))
        return r

    def test_matches_dense_joint_reference_for_both_token_orders_and_layouts(self):
        torch.manual_seed(49)
        for family in ('Krea2','MOSS'):
            for shaped in (False,True):
                for output_shaped in (False,True):
                    r=self.make(family)
                    q,k,v=[torch.randn(1,17,16,dtype=torch.float64) for _ in range(3)]
                    mask=torch.full((17,17),-torch.inf,dtype=q.dtype)
                    ts=8 if family=='MOSS' else 0
                    im=0 if family=='MOSS' else 9
                    text=[torch.arange(ts+a,ts+b) for a,b in [(0,2),(2,5),(5,9)]]
                    images=torch.arange(im,im+8)
                    mask[text[0][:,None],torch.cat([text[0],images])]=0
                    vv=v[:,None,:,:].expand(1,17,17,16).clone()
                    for slot,group in enumerate(r.state['groups']):
                        own=group+im
                        mask[text[slot+1][:,None],torch.cat([text[slot+1],own])]=0
                        mask[own[:,None],images]=math.log(.5)
                        mask[own[:,None],own]=0
                        mass=2/1.3
                        mask[own[:,None],text[0]]=math.log(.3*mass/2)
                        mask[own[:,None],text[slot+1]]=math.log(mass/len(text[slot+1]))
                        vv[:,own[:,None],text[slot+1]]*=1.2
                    # Gains apply to image queries only, so use a per-query reference.
                    qr, kr = (j.moss_caption_positions(q,2,[2,3,4],8), j.moss_caption_positions(k,2,[2,3,4],8)) if family=="MOSS" else (q,k)
                    expected=torch.cat([attention(qr[:,i:i+1],kr,vv[:,i],2,mask[i:i+1]) for i in range(17)],1)
                    if shaped:q,k,v=[a.unflatten(-1,(2,8)).transpose(1,2) for a in (q,k,v)]
                    actual=r.attention(attention,q,k,v,2,skip_reshape=shaped,skip_output_reshape=output_shaped,
                                       transformer_options={'block_index':0})
                    if output_shaped:expected=expected.unflatten(-1,(2,8)).transpose(1,2)
                    torch.testing.assert_close(actual,expected,atol=1e-12,rtol=1e-12)

    def test_moss_rotary_translation_matches_native_single_caption_distances(self):
        # Independent scalar rotation reference for the f-axis of 32-D heads.
        torch.manual_seed(4)
        raw=torch.randn(1,17,2,32,dtype=torch.float32)
        native=torch.tensor([9]*8+list(range(9)))
        desired=torch.tensor([9]*8+[7,8]+[6,7,8]+[5,6,7,8])
        def rotate(positions):
            out=raw.clone()
            for tok,pos in enumerate(positions):
                for freq in range(4):
                    angle=float(pos)/(10000**(freq/4))
                    a,b=raw[:,tok,:,4+freq],raw[:,tok,:,20+freq]
                    out[:,tok,:,4+freq]=a*math.cos(angle)-b*math.sin(angle)
                    out[:,tok,:,20+freq]=b*math.cos(angle)+a*math.sin(angle)
            return out
        actual=j.moss_caption_positions(rotate(native).flatten(2),2,[2,3,4],8)
        torch.testing.assert_close(actual,rotate(desired).flatten(2),atol=5e-7,rtol=5e-7)
        torch.testing.assert_close(actual[:,:8],rotate(native).flatten(2)[:,:8],atol=0,rtol=0)

    def test_foreign_caption_cannot_change_own_image_queries_or_text_refiners(self):
        torch.manual_seed(19)
        for family in ('Krea2','MOSS'):
            r=self.make(family)
            q,k,v=[torch.randn(1,17,16,dtype=torch.float64) for _ in range(3)]
            ts=8 if family=='MOSS' else 0;im=0 if family=='MOSS' else 9
            kwargs={'transformer_options':{'block_index':0}}
            actual=r.attention(attention,q,k,v,2,**kwargs)
            k[:,ts+5:ts+9]+=100.;v[:,ts+5:ts+9]-=200.
            other=r.attention(attention,q,k,v,2,**kwargs)
            torch.testing.assert_close(actual[:,r.state['groups'][0]+im],other[:,r.state['groups'][0]+im],atol=0,rtol=0)
            q,k,v=[torch.randn(1,9,16,dtype=torch.float64) for _ in range(3)]
            actual=r.attention(attention,q,k,v,2)
            k[:,5:]+=100.;v[:,5:]-=200.
            other=r.attention(attention,q,k,v,2)
            torch.testing.assert_close(actual[:,:5],other[:,:5],atol=0,rtol=0)

    def test_cfg_negative_keeps_native_context_and_scope_restores_on_failure(self):
        for family in ('Krea2','MOSS'):
            for kinds in ([0,1],[1,0],[0],[1]):
                r=self.make(family);r.state=None
                x=torch.randn(len(kinds),4,2,4);t=torch.ones(len(kinds));ctx=torch.randn(len(kinds),2,6)
                seen=[]
                def invoke(xb,tb,cb,options):
                    index=len(seen);kind=kinds[index];seen.append(kind)
                    self.assertEqual(options['cond_or_uncond'],[kind])
                    if kind==1:
                        torch.testing.assert_close(cb,ctx[index:index+1]);self.assertIsNone(r.state)
                    else:self.assertEqual(cb.shape[1],9)
                    return xb
                out=r.forward(invoke,x,t,ctx,{'cond_or_uncond':kinds,'sigmas':torch.tensor([5.])},(2,4))
                torch.testing.assert_close(out,x);self.assertIsNone(r.state)
                def broken(*args):raise RuntimeError('cancelled')
                with self.assertRaisesRegex(RuntimeError,'cancelled'):
                    r.forward(broken,x,t,ctx,{'cond_or_uncond':kinds,'sigmas':torch.tensor([5.])},(2,4))
                self.assertIsNone(r.state)

    def test_short_schedules_and_engine_metadata_replay(self):
        host=SimpleNamespace(KSampler=SimpleNamespace(SAMPLERS=['euler_ancestral'],SCHEDULERS=['sgm_uniform']))
        with patch.dict(sys.modules,{'comfy.samplers':host}):
            for steps in (2,8,30,50,100):n.validate_settings({**n.DEFAULTS,'seed':0,'steps':steps})
            for steps in (1,101,True,8.5):
                with self.assertRaises(ValueError):n.validate_settings({**n.DEFAULTS,'seed':0,'steps':steps})
        pipe=c.CharacterPipe((c.Character('woman',x=.25),c.Character('man',x=.75)),'campus','bad')
        with tempfile.TemporaryDirectory() as tmp:
            for engine,steps in [('krea2-spatial-alpha-1',8),('moss-spatial-alpha-1',50)]:
                record=m.build_record(pipe,{**n.DEFAULTS,'seed':3,'steps':steps},{},[[.25,.5],[.75,.5]],{'spatial_slots':2},engine)
                for fmt in m.FORMATS:
                    path=m.save_image(Image.new('RGB',(16,16)),Path(tmp)/engine,record,fmt)
                    with Image.open(path) as image:
                        restored=m.pipe_from_record(m.read_record(image))
                        self.assertEqual(restored.characters,pipe.characters)
                        self.assertEqual(json.loads(restored.generation_json)['engine'],engine)
                        self.assertEqual(json.loads(restored.generation_json)['settings']['steps'],steps)
                        if fmt=='PNG':self.assertEqual(image.info['Source'],m.ENGINE_SOURCES[engine])
                        self.assertNotIn('workflow',image.info)

if __name__=='__main__':unittest.main()
