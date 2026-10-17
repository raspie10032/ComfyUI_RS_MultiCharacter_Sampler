"""Epsilon boxes: explicit attention oracle, coordinates, save/replay, and overlap."""
import copy
import importlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import torch
import torch.nn.functional as F
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
PKG = Path(__file__).resolve().parents[1].name
c, l, r, m, n = [importlib.import_module(PKG + '.' + name) for name in ('characters','layout','routing','metadata','nodes')]


class BoxTests(unittest.TestCase):
    def pipe(self):
        return c.CharacterPipe((c.Character('red',x=.3,y=.5,bbox=(.1,.1,.5,.9)),
            c.Character('blue',x=.65,y=.5,bbox=(.4,.1,.9,.9))), 'garden', 'bad')

    def test_input_optional_tail_preserves_legacy_and_hidden_slots(self):
        fields=c.RSMultiCharacterPrompts.INPUT_TYPES()
        self.assertEqual(len(fields['required']),51)
        self.assertEqual(next(iter(fields['optional'])),'layout_mode')
        pipe,=c.RSMultiCharacterPrompts().build(1,layout_mode='boxes',character1='red',
            character1_x=.25,character1_width=.5,character1_height=1.,character2='hidden')
        self.assertEqual(pipe.characters[0].bbox,(0.,0.,.5,1.))
        self.assertEqual(len(pipe.characters),1)
        with self.assertRaisesRegex(ValueError,'outside'):
            c.RSMultiCharacterPrompts().build(1,layout_mode='boxes',character1='red',character1_x=.01)

    def test_invalid_bounds(self):
        for box in ((.8,0,.2,1),(0,0,0,1),(0,0,float('nan'),1),(False,0,1,1),(-.1,0,1,1)):
            with self.assertRaises(ValueError):c.Character('red',bbox=box)
        with self.assertRaisesRegex(ValueError,'center'):c.Character('red',x=.1,bbox=(0,0,1,1))

    def test_coincident_boxes_keep_sizes_and_overlap_without_spreading(self):
        chars=(c.Character('large',bbox=(0,0,1,1)),c.Character('small',bbox=(.4,.4,.6,.6)))
        centers,moved=l.effective_centers(chars)
        self.assertEqual(centers,((.5,.5),(.5,.5)))
        self.assertEqual(moved,[])
        masks=l.character_masks(chars,centers,128,64,.04)
        self.assertGreater(float(masks[0].sum()),float(masks[1].sum()))
        groups=r.token_groups(masks,4,8,boxes=True)
        self.assertTrue(any(members==(0,1) for members,_ in groups.cells))
        self.assertEqual(sorted(torch.cat([ids for _,ids in groups.cells]).tolist()),list(range(32)))

    def test_mixed_points_and_word_box_have_explicit_priority_at_all_grids(self):
        pipe,=c.RSMultiCharacterPrompts().build(3,layout_mode='mixed',
            character1='red',character1_x=.25,character2='blue',character2_x=.75,
            character3_kind='text',character3_text='HELLO',character3_y=.25,
            character3_height=.25,character3_width=.5)
        self.assertEqual([v.bbox is None for v in pipe.regions],[True,True,False])
        centers,moved=l.effective_centers(pipe.regions)
        self.assertEqual(moved,[])
        masks=l.character_masks(pipe.regions,centers,256,256,.04)
        for h,w in ((32,32),(16,16),(8,8),(4,4)):
            groups=r.token_groups(masks,h,w,boxes=(False,False,True))
            self.assertEqual({len(members) for members,_ in groups.cells},{1})
            self.assertEqual(sorted(torch.cat(list(groups)).tolist()),list(range(h*w)))
            self.assertEqual(groups.background.numel(),0)
            expected=F.interpolate(masks[2:3,None],(h,w),mode='area')[0,0].flatten()>1e-6
            self.assertEqual(groups[2].tolist(),expected.nonzero().flatten().tolist())
        record=m.build_record(pipe,{**n.DEFAULTS,'seed':5},{},centers,{'spatial_slots':3})
        restored=m.pipe_from_record(record)
        self.assertEqual(restored.characters,pipe.characters)
        self.assertEqual(restored.text_regions,pipe.text_regions)

    def test_mixed_coincident_points_ignore_boxes_and_report_swallowed_regions(self):
        pipe,=c.RSMultiCharacterPrompts().build(3,layout_mode='mixed',
            character1='red',character2='blue',character3='logo',character3_geometry='box',
            character3_width=.3,character3_height=.3)
        centers,moved=l.effective_centers(pipe.regions)
        self.assertEqual(centers,((.25,.5),(.75,.5),(.5,.5)))
        self.assertEqual(moved,[[1,2]])
        masks=l.character_masks(pipe.regions,centers,64,64,0)
        groups=r.token_groups(masks,8,8,boxes=(False,False,True))
        self.assertEqual(len(groups),3)
        masks[2]=1
        with self.assertRaisesRegex(ValueError,'fully cover'):
            r.token_groups(masks,8,8,boxes=(False,False,True))
        with self.assertRaisesRegex(ValueError,'one box/point flag'):
            r.token_groups(masks,8,8,boxes=(True,))

    def groups(self):
        masks=torch.tensor([[[0.,1.,1.,0.]],[[0.,0.,1.,1.]]])
        return r.token_groups(masks,1,4,boxes=True)

    def test_cross_dense_oracle_background_overlap_cfg_order_zero_prior(self):
        torch.manual_seed(26)
        q=torch.randn(2,4,2,3,dtype=torch.float64)
        k=torch.randn(2,9,2,3,dtype=torch.float64);v=torch.randn_like(k)
        for kinds in ([0,1],[1,0]):
            for prior in (0.,.3,1.):
                bias=q.new_full((2,1,4,9),-torch.inf);values=v.clone()
                for b,kind in enumerate(kinds):
                    if kind==1:bias[b,:,:,0:2]=0;continue
                    values[b,2:]*=1.7
                    for row,members in enumerate(((),(0,),(0,1),(1,))):
                        bias[b,0,row,:2]=0 if not members else (-torch.inf if prior==0 else math.log(prior/2))
                        for slot in members:
                            lo,hi=((2,5),(5,9))[slot]
                            bias[b,0,row,lo:hi]=math.log(1/(len(members)*(hi-lo)))
                expected=F.scaled_dot_product_attention(q.transpose(1,2),k.transpose(1,2),values.transpose(1,2),attn_mask=bias).transpose(1,2).flatten(2)
                actual=r.route_cross(q,k,v,self.groups(),[2,3,4],kinds,weights=(prior,1.),character_gain=1.7)
                torch.testing.assert_close(actual,expected,atol=1e-12,rtol=1e-12)
                self.assertTrue(torch.isfinite(actual).all())

    def test_overlap_permutation_no_slot_priority_and_background_invariant(self):
        torch.manual_seed(27)
        q=torch.randn(1,4,1,4,dtype=torch.float64);k=torch.randn(1,9,1,4,dtype=torch.float64);v=torch.randn_like(k)
        g=self.groups();args=dict(weights=(0.,1.),character_gain=1.3)
        a=r.route_cross(q,k,v,g,[2,3,4],[0],**args)
        masks=torch.tensor([[[0.,0.,1.,1.]],[[0.,1.,1.,0.]]])
        order=[0,1,5,6,7,8,2,3,4]
        b=r.route_cross(q,k[:,order],v[:,order],r.token_groups(masks,1,4,boxes=True),[2,4,3],[0],**args)
        torch.testing.assert_close(a,b,atol=1e-12,rtol=1e-12)
        v[:,2:]+=99
        changed=r.route_cross(q,k,v,g,[2,3,4],[0],**args)
        torch.testing.assert_close(a[:,0],changed[:,0],atol=0,rtol=0)
        self.assertGreater(float((changed[:,2]-a[:,2]).abs().max()),1)

    def test_self_background_shared_and_overlap_links_both(self):
        q=torch.zeros(1,4,1,4)
        b=r.weak_self_bias(self.groups(),4,q,.9)
        torch.testing.assert_close(b[0],torch.zeros(4))
        torch.testing.assert_close(b[:,0],torch.zeros(4))
        self.assertEqual(float(b[1,2]),0.)
        self.assertEqual(float(b[2,3]),0.)
        self.assertAlmostEqual(float(b[1,3]),math.log(.1),places=6)

    def test_moss_json_coordinates_caption_escaping_and_bounds(self):
        pipe=c.CharacterPipe((c.Character('woman "A" 日本語',bbox=(.1,.2,.9,.8)),),'scene','')
        data=json.loads(l.moss_layout_prompt(pipe,1024,768))
        self.assertEqual(data['items'][0]['bbox'],[-231,-410,231,410])
        self.assertEqual(data['items'][0]['caption'],'woman "A" 日本語')
        self.assertEqual(data['bbox_format'],'yxyx')
        self.assertEqual(data['bbox_coord_space'],'abs_centralized')
        with self.assertRaisesRegex(ValueError,'boxes'):
            l.moss_layout_prompt(c.CharacterPipe((c.Character('person'),)),1024,768)

    def test_metadata_png_webp_legacy_and_bad_box_counts(self):
        record=m.build_record(self.pipe(),{**n.DEFAULTS,'seed':40,'layout_method':'moss_native'}, {}, [[.3,.5],[.65,.5]],{'spatial_slots':2},'moss-spatial-alpha-1')
        with tempfile.TemporaryDirectory() as folder:
            for fmt in m.FORMATS:
                path=m.save_image(Image.new('RGB',(32,32)),Path(folder)/fmt,record,fmt)
                with Image.open(path) as im:
                    pipe=m.pipe_from_record(m.read_record(im))
                    self.assertEqual(pipe.characters,self.pipe().characters)
                    self.assertEqual(json.loads(pipe.generation_json)['settings']['layout_method'],'moss_native')
                    self.assertNotIn('workflow',im.info)
        bad=copy.deepcopy(record);bad['rs_multicharacter']['boxes']=[]
        with self.assertRaisesRegex(ValueError,'count'):m.pipe_from_record(bad)
        old=copy.deepcopy(record);del old['rs_multicharacter']['boxes']
        self.assertTrue(all(v.bbox is None for v in m.pipe_from_record(old).characters))

    def test_detailer_metadata_retains_input_boxes_without_sampler_snapshot(self):
        d=importlib.import_module(PKG+'.detailer')
        record=d.detail_record(self.pipe(),1024,768,{}, {}, {})
        self.assertEqual(m.pipe_from_record(record).characters,self.pipe().characters)

    def test_two_people_one_word_native_payload_and_detailer_isolation(self):
        pipe,=c.RSMultiCharacterPrompts().build(3,layout_mode='boxes',
            character1='woman red jacket',character1_x=.25,character1_width=.4,
            character2='woman blue jacket',character2_x=.75,character2_width=.4,
            character3_kind='text',character3='Bold red lettering',character3_text='HELLO',
            character3_y=.1,character3_height=.15,character3_width=.6,
            character4_kind='text',character4_text='hidden')
        self.assertEqual(len(pipe.characters),2)
        self.assertEqual(len(pipe.text_regions),1)
        self.assertEqual(len(pipe.regions),3)
        payload=json.loads(l.moss_layout_prompt(pipe,1024,768))
        self.assertEqual([v['label'] for v in payload['items']],['object','object','text'])
        self.assertEqual(payload['items'][2]['text'],'HELLO')
        self.assertEqual(payload['items'][2]['caption'],'Bold red lettering')
        self.assertEqual(len(m.captions(pipe)['v4_prompt']['caption']['char_captions']),2)
        d=importlib.import_module(PKG+'.detailer')
        self.assertEqual(len(d._prompts(pipe)[2]),2)
        record=d.detail_record(pipe,1024,768,{}, {}, {})
        self.assertEqual(m.pipe_from_record(record).text_regions,pipe.text_regions)

    def test_point_mode_ignores_dormant_text_slot(self):
        pipe, = c.RSMultiCharacterPrompts().build(2, layout_mode='points',
            character1='person', character2='red title', character2_kind='text', character2_text='HELLO')
        self.assertEqual([v.prompt for v in pipe.characters], ['person'])
        self.assertEqual(pipe.text_regions, ())

    def test_text_metadata_round_trip_unicode_and_validation(self):
        text='HELLO "world"\nこんにちは 안녕 (1:2)'
        region=c.TextRegion('clear title',bbox=(.1,.4,.9,.6),text=text)
        pipe=c.CharacterPipe((), 'poster', '', text_regions=(region,))
        payload=json.loads(l.moss_layout_prompt(pipe,1024,768))
        self.assertEqual(payload['items'][0]['text'],text)
        record=m.build_record(pipe,{**n.DEFAULTS,'seed':42},{},[[.5,.5]],{'spatial_slots':1})
        with tempfile.TemporaryDirectory() as folder:
            for fmt in m.FORMATS:
                path=m.save_image(Image.new('RGB',(32,32)),Path(folder)/fmt,record,fmt)
                with Image.open(path) as im:
                    restored=m.pipe_from_record(m.read_record(im))
                self.assertEqual(restored.text_regions,pipe.text_regions)
                self.assertEqual(restored.characters,())
        with self.assertRaises(ValueError):c.TextRegion('title',text='HELLO')
        with self.assertRaises(ValueError):c.TextRegion('title',bbox=(0,0,1,1),text='')
        with self.assertRaises(ValueError):c.CharacterPipe((),text_regions=(region,)*11)
        bad=copy.deepcopy(record);bad['rs_multicharacter']['text_regions']={}
        with self.assertRaises(ValueError):m.pipe_from_record(bad)

if __name__=='__main__':unittest.main()
