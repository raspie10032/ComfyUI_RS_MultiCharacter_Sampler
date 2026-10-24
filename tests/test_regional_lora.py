import importlib
import json
from pathlib import Path
import sys
import unittest
from dataclasses import replace
from types import SimpleNamespace

import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
PKG=Path(__file__).resolve().parents[1].name
c,l,m,n,r=[importlib.import_module(PKG+'.'+s) for s in ('characters','layout','metadata','nodes','regional_lora')]


class RegionalLoraTests(unittest.TestCase):
    def test_precision_hooks_intersect_existing_negative_region_masks(self):
        import comfy.hooks
        hooks = [comfy.hooks.HookGroup(), comfy.hooks.HookGroup()]
        for hook in hooks:
            hook.add(comfy.hooks.WeightHook())
        plan = object.__new__(r.RegionalLoras)
        plan.hooks = hooks; plan.bypasses = {}
        regions = (c.Character('a'), c.Character('b'))
        masks = torch.zeros(2,4,4); masks[0,:,:2]=1; masks[1,:,2:]=1
        positive = [[torch.zeros(1,2,3),{}]]
        negative = [[torch.zeros(1,2,3),{'mask': masks[0].unsqueeze(0), 'mask_strength':.8}]]
        model = SimpleNamespace()
        _, result = plan.condition_pair(model, positive, negative, masks, regions, 'precision')
        self.assertEqual(len(result),1)
        self.assertEqual(result[0][1]['mask_strength'],.8)
        torch.testing.assert_close(result[0][1]['mask'],masks[0].unsqueeze(0))
        self.assertIs(result[0][1]['hooks'],hooks[0])

    def test_optional_old_inputs_and_hidden_slots_do_not_apply_lora(self):
        p,=c.RSMultiCharacterPrompts().build(1,character1='woman',character2='hidden',character2_lora='missing.safetensors')
        self.assertEqual(p.characters[0].lora_name,'None')
        self.assertEqual(len(p.characters),1)
        p,=c.RSMultiCharacterPrompts().build(2,character1='woman',character1_lora='a.safetensors',character1_lora_strength=.7,
            character2_kind='text',character2_text='HELLO',layout_mode='mixed',character2_lora='stale.safetensors')
        self.assertEqual(p.characters[0].lora_strength,.7)
        self.assertEqual(p.text_regions[0].lora_name,'None')

    def test_metadata_roundtrip_and_malformed_count(self):
        p=c.CharacterPipe((c.Character('left',x=.2,lora_name='sub/a.safetensors',lora_strength=.8,lora_clip_strength=0.),
            c.Character('right',x=.8)), 'garden', 'bad')
        record=m.build_record(p,{**n.DEFAULTS,'seed':12},{},((.2,.5),(.8,.5)),{'spatial_slots':2})
        restored=m.pipe_from_record(record)
        self.assertEqual(restored.characters,p.characters)
        record['rs_multicharacter']['character_loras'].pop()
        with self.assertRaisesRegex(ValueError,'LoRA'):m.pipe_from_record(record)

    def test_box_priority_overlap_background_and_unmodified_text(self):
        chars=(c.Character('left',x=.25),c.Character('right',x=.75))
        txt=c.TextRegion('letters',x=.5,y=.25,bbox=(.25,0.,.75,.5),text='HI')
        regions=(*chars,txt);centers,_=l.effective_centers(regions)
        masks=l.character_masks(regions,centers,64,64,0.)
        a,b=object(),object();groups=dict(r.grouped_masks([a,b],masks,regions))
        torch.testing.assert_close(sum(groups.values()),torch.ones(8,8))
        self.assertTrue((groups[None][:4,2:6]==1).all())
        self.assertTrue((groups[a][:4,2:6]==0).all())
        boxes=(c.Character('a',bbox=(.1,.1,.9,.9)),c.Character('b',bbox=(.4,.4,.6,.6)))
        masks=l.character_masks(boxes,((.5,.5),(.5,.5)),80,80,0.)
        groups=dict(r.grouped_masks([a,b],masks,boxes))
        torch.testing.assert_close(sum(groups.values()),torch.ones(10,10))
        self.assertEqual(groups[a][5,5],.5);self.assertEqual(groups[b][5,5],.5)
        self.assertEqual(groups[None][0,0],1.)

    def test_equal_loras_coalesce_and_zero_is_disabled(self):
        a=object();chars=(c.Character('a',x=.25),c.Character('b',x=.75))
        masks=l.character_masks(chars,((.25,.5),(.75,.5)),64,64,.1)
        groups=r.grouped_masks([a,a],masks,chars)
        self.assertEqual(len(groups),1);torch.testing.assert_close(groups[0][1],torch.ones(8,8))
        self.assertFalse(r.active_lora(replace(chars[0],lora_name='missing',lora_strength=0.,lora_clip_strength=0.)))
        for value in (float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):c.Character('a',lora_strength=value)
