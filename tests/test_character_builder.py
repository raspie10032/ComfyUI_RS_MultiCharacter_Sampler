import importlib
import itertools
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = importlib.import_module(Path(__file__).resolve().parents[1].name)
b = importlib.import_module(pkg.__name__ + '.character_builder')
c = importlib.import_module(pkg.__name__ + '.characters')
m = importlib.import_module(pkg.__name__ + '.metadata')
n = importlib.import_module(pkg.__name__ + '.nodes')


class BuilderTests(unittest.TestCase):
    def actions(self):
        return [
            (b.RSMultiCharacterPrompt(),dict(character_count=2,character1='1girl, blonde hair',character2='1girl, black hair')),
            (b.RSMultiCharacterLoRA(),dict(character_count=2,character1_lora='a.safetensors',character1_lora_strength=.8,character1_lora_clip_strength=0.,character2_lora='b.safetensors',character2_lora_strength=1.2,character2_lora_clip_strength=.6)),
            (b.RSMultiCharacterPosition(),dict(character_count=2,character1_x=.25,character2_x=.75,character2_geometry='box',character2_width=.4,character2_height=.8)),
        ]

    def assemble(self, actions):
        pipe = None
        for node, settings in actions:
            pipe, = node.apply(building_pipe=pipe, **settings)
        return b.finalize(pipe)

    def test_all_six_role_orders_produce_identical_pipe(self):
        expected = self.assemble(self.actions())
        for actions in itertools.permutations(self.actions()):
            self.assertEqual(self.assemble(actions), expected)
        self.assertEqual([ch.uc for ch in expected.characters], ['', ''])

    def test_old_node_produces_identical_generation_inputs(self):
        old, = c.RSMultiCharacterPrompts().build(2, layout_mode='mixed',
            character1='1girl, blonde hair', character1_x=.25,
            character1_lora='a.safetensors',character1_lora_strength=.8,character1_lora_clip_strength=0.,
            character2='1girl, black hair',character2_x=.75,character2_geometry='box',
            character2_width=.4,character2_height=.8,character2_lora='b.safetensors',
            character2_lora_strength=1.2,character2_lora_clip_strength=.6)
        self.assertEqual(old,self.assemble(self.actions()))

    def test_reduced_count_ignores_old_prompt_lora_and_invalid_position(self):
        actions=self.actions()
        actions[0][1].update(character_count=1,character2='stale')
        actions[2][1]['character2_x']=100
        for order in itertools.permutations(actions):
            pipe=self.assemble(order)
            self.assertEqual(len(pipe.characters),1)
            self.assertEqual(pipe.characters[0].lora_name,'a.safetensors')

    def test_prompt_only_and_immutable_branches(self):
        root,=b.RSMultiCharacterPrompt().apply(1,character1='person')
        left,=b.RSMultiCharacterPosition().apply(1,building_pipe=root,character1_x=.2)
        right,=b.RSMultiCharacterPosition().apply(1,building_pipe=root,character1_x=.8)
        self.assertEqual([b.finalize(p).characters[0].x for p in (root,left,right)],[.5,.2,.8])
        self.assertEqual(b.finalize(root).characters[0].lora_name,'None')

    def test_disabled_row_excluded_in_any_order(self):
        actions=self.actions();actions[0][1]['character2_enable']=False
        for order in itertools.permutations(actions):self.assertEqual(len(self.assemble(order).characters),1)

    def test_repeated_role_replaces_only_its_table_and_clears_hidden_rows(self):
        root,=b.RSMultiCharacterPrompt().apply(2,character1='one',character2='two')
        draft,=b.RSMultiCharacterLoRA().apply(2,building_pipe=root,character1_lora='a',character2_lora='b')
        draft,=b.RSMultiCharacterLoRA().apply(1,building_pipe=draft,character1_lora='c',character2_lora='stale')
        final=b.finalize(draft)
        self.assertEqual([ch.lora_name for ch in final.characters],['c','None'])
        self.assertEqual([ch.prompt for ch in final.characters],['one','two'])
        self.assertEqual([ch.lora_name for ch in b.finalize(root).characters],['None','None'])

    def test_incomplete_draft_fails_only_at_finalize(self):
        draft,=b.RSMultiCharacterLoRA().apply(2,character1_lora='a')
        with self.assertRaisesRegex(ValueError,'Prompts'):b.finalize(draft)
        for prompt in ('','   '):
            draft,=b.RSMultiCharacterPrompt().apply(1,character1=prompt,building_pipe=draft)
            with self.assertRaisesRegex(ValueError,'Character 1'):b.finalize(draft)

    def test_ten_slots_and_round_trip_with_text(self):
        actions=self.actions();actions[0][1].update(character_count=3,character3='red serif lettering',character3_kind='text',character3_text='HELLO')
        actions[2][1].update(character_count=3,character3_geometry='box',character3_x=.5,character3_y=.1,character3_width=.4,character3_height=.1)
        pipe=self.assemble(actions)
        for order in itertools.permutations(actions):self.assertEqual(self.assemble(order),pipe)
        record=m.build_record(pipe,{**n.DEFAULTS,'seed':12},{},[(r.x,r.y) for r in pipe.regions],{'spatial_slots':3})
        restored=m.pipe_from_record(json.loads(json.dumps(record)))
        self.assertEqual((restored.characters,restored.text_regions),(pipe.characters,pipe.text_regions))
        ten,=b.RSMultiCharacterPrompt().apply(10,**{f'character{i}':f'person {i}' for i in range(1,11)})
        self.assertEqual(len(b.finalize(ten).characters),10)

    def test_shared_string_routes_by_kind_in_every_role_order(self):
        actions = self.actions()
        actions[0][1].update(character2='HELLO 안녕 こんにちは', character2_kind='text')
        actions[1][1].update(character2_lora='None')
        for order in itertools.permutations(actions):
            pipe = self.assemble(order)
            self.assertEqual(len(pipe.characters), 1)
            self.assertEqual(pipe.text_regions[0].text, 'HELLO 안녕 こんにちは')
            self.assertEqual(pipe.text_regions[0].prompt, 'Clear legible lettering')
            record = m.build_record(pipe, {**n.DEFAULTS, 'seed': 12}, {},
                [(r.x, r.y) for r in pipe.regions], {'spatial_slots': 2})
            restored = m.pipe_from_record(json.loads(json.dumps(record)))
            self.assertEqual(restored.text_regions, pipe.text_regions)
        # The same incoming value becomes the character prompt when switched back.
        actions[0][1]['character2_kind'] = 'character'
        pipe = self.assemble(actions)
        self.assertEqual(pipe.characters[1].prompt, 'HELLO 안녕 こんにちは')
        self.assertFalse(pipe.text_regions)

    def test_shared_text_rejects_empty_literal_and_requires_box(self):
        for words in ('', '   '):
            root, = b.RSMultiCharacterPrompt().apply(1, character1=words, character1_kind='text')
            root, = b.RSMultiCharacterPosition().apply(1, building_pipe=root, character1_geometry='box')
            with self.assertRaisesRegex(ValueError, 'literal text'):
                b.finalize(root)
        root, = b.RSMultiCharacterPrompt().apply(1, character1='HELLO', character1_kind='text')
        with self.assertRaisesRegex(ValueError, 'box mode'):
            b.finalize(root)

    def test_character_kind_ignores_legacy_literal(self):
        root, = b.RSMultiCharacterPrompt().apply(1, character1='girl', character1_text='OLD TEXT')
        self.assertEqual(root.slots[0].literal_text, '')
        self.assertEqual(b.finalize(root).characters[0].prompt, 'girl')

    def test_invalid_active_values(self):
        for count in (True,0,11,1.2):
            with self.assertRaises(ValueError):b.RSMultiCharacterPrompt().apply(count)
        root,=b.RSMultiCharacterPrompt().apply(1,character1='person')
        for settings in ({'character1_x':float('nan')},{'character1_geometry':'box','character1_x':.1,'character1_width':.4}):
            draft,=b.RSMultiCharacterPosition().apply(1,building_pipe=root,**settings)
            with self.assertRaises(ValueError):b.finalize(draft)
        draft,=b.RSMultiCharacterLoRA().apply(1,building_pipe=root,character1_lora_strength=float('nan'))
        with self.assertRaises(ValueError):b.finalize(draft)

    def test_all_prompts_are_string_sockets_without_uc_or_selected_character(self):
        schema=b.RSMultiCharacterPrompt.INPUT_TYPES()
        for i in range(1,11):self.assertTrue(schema['optional'][f'character{i}'][1]['forceInput'])
        for cls in (b.RSMultiCharacterPrompt,b.RSMultiCharacterPosition,b.RSMultiCharacterFinalize):
            for fields in cls.INPUT_TYPES().values():
                self.assertFalse(any('uc' in key or 'negative' in key or key=='character_id' for key in fields))
        self.assertIn('character10_x',b.RSMultiCharacterPosition.INPUT_TYPES()['required'])

    def test_new_mappings_and_legacy_retained(self):
        for cls in (b.RSMultiCharacterPrompt,b.RSMultiCharacterLoRA,b.RSMultiCharacterPosition,b.RSMultiCharacterFinalize):
            self.assertIs(pkg.NODE_CLASS_MAPPINGS[cls.__name__],cls)
        self.assertIs(pkg.NODE_CLASS_MAPPINGS['RSMultiCharacterPrompts'],c.RSMultiCharacterPrompts)

if __name__=='__main__':unittest.main()
