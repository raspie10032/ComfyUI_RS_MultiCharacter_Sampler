# SPDX-License-Identifier: GPL-3.0-only
import importlib
import json
from pathlib import Path
import sys
import unittest
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
pkg=Path(__file__).resolve().parents[1].name
i=importlib.import_module(pkg+'.interaction')
r=importlib.import_module(pkg+'.routing')

class InteractionTests(unittest.TestCase):
    def test_baseline_is_identical_and_overlap_background_untouched(self):
        masks=torch.tensor([[[1.,1.,0.,0.]],[[0.,1.,1.,0.]]])
        groups=r.token_groups(masks,1,4,boxes=True)
        original=r.weak_self_bias(groups,4,masks,.2)
        self.assertTrue(torch.equal(original,i.protected_self_bias(groups,4,masks,.2)))
        actual=i.protected_self_bias(groups,4,masks,.2,.9)
        expected=original.clone();expected[0,2]=expected[2,0]=torch.log(torch.tensor(.1))
        torch.testing.assert_close(actual,expected)
        self.assertEqual(i.exclusive_schedule(None,.5,30,.9,3,.2),None)
        self.assertEqual(i.exclusive_schedule({'preset':'baseline'},.5,30,.9,3,.2),None)

    def test_delay_applies_only_to_exclusive_schedule_and_caps_at_steps(self):
        for preset,extra in [('delay3',3),('delay6',6)]:
            config=i.interaction_settings({'preset':preset})
            for step in range(30):
                progress=step/29
                self.assertEqual(i.exclusive_schedule(config,progress,30,.9,3,.2),
                    r.hold_decay_spatial_separation(progress,30,.9,3+extra,.2))
        self.assertEqual(i.exclusive_schedule(i.interaction_settings({'preset':'delay6'}),1.,3,.9,3,.2),.9)

    def test_invalid_configuration_has_readable_error(self):
        for v in [{'preset':'bad'},{'preset':'custom','delay_steps':True},
                  {'preset':'custom','decrement':float('nan')},[], 'bad json']:
            with self.subTest(value=v):
                with self.assertRaisesRegex(ValueError,'겹침 제어'):
                    i.interaction_settings(v)

    def test_node_default_and_custom_are_serialized(self):
        node=i.RSMultiCharacterInteraction()
        self.assertEqual(json.loads(node.apply()[0].interaction_json)['preset'],'baseline')
        config=json.loads(node.apply('custom',4,.3)[0].interaction_json)
        self.assertEqual(config,dict(preset='custom',delay_steps=4,decrement=.3))

if __name__=='__main__':unittest.main()
