import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('rs_test_wildcards', Path(__file__).resolve().parents[1] / 'app_wildcards.py')
wc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wc)


class WorkspaceWildcardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, text in {
            'fabe': '\ufeff# comment\n\n루시드\nソフィー\nBarbara\n',
            'ff': 'character A\ncharacter B\n',
            'poses/arms': 'arms up\narms down\n',
            'nested': '__fabe__, {a|{b|c}}',
            'cycle': '__cycle__', 'empty': '# nothing\n',
        }.items():
            p = self.root / (name + '.txt')
            p.parent.mkdir(exist_ok=True)
            p.write_text(text, encoding='utf-8')
        self.files = wc.inventory([('test', self.root)])

    def test_seed_replay_independent_fields_and_unicode(self):
        text = {'character1':'__fabe__', 'character2':'__ff__', 'prompt':'{park|cafe}'}
        output = wc.expand(text, 123, self.files)
        self.assertEqual(wc.expand(text, 123, self.files), output)
        self.assertEqual(wc.expand({'character1':text['character1']},123,self.files)['character1'], output['character1'])
        self.assertIn(output['character1'], ['루시드','ソフィー','Barbara'])
        self.assertGreater(len({wc.expand(text,i,self.files)['character1'] for i in range(20)}),1)
        self.assertEqual(text['character1'],'__fabe__')

    def test_nested_glob_and_qualified_file_names(self):
        text = wc.expand({'a':'__nested__', 'b':'__poses/*__', 'c':'__test/ff__'}, 0, self.files)
        self.assertNotIn('__',text['a'])
        self.assertNotIn('{',text['a'])
        self.assertIn(text['b'],['arms up','arms down'])
        self.assertIn(text['c'],['character A','character B'])

    def test_no_tokens_preserves_prompt_weights_and_literal_braces(self):
        text = {'a':'(artist:foo:0.9), 1.2::bar::, {tag}, \\{x|y}'}
        self.assertEqual(wc.expand(text,1,self.files),text)

    def test_cycle_missing_and_empty_fail_actionably(self):
        for token, message in [('cycle','순환'),('missing','찾을 수'),('empty','비어')]:
            with self.subTest(token=token), self.assertRaisesRegex(ValueError,message):
                wc.expand({'a':f'__{token}__'},0,self.files)

    def test_ambiguous_alias_requires_qualified_name(self):
        files = {**self.files,'other/ff':self.root/'ff.txt'}
        with self.assertRaisesRegex(ValueError,'이름이 겹'):
            wc.expand({'a':'__ff__'},0,files)
        self.assertIn(wc.expand({'a':'__test/ff__'},0,files)['a'],['character A','character B'])

    def test_file_containment_and_invalid_requests(self):
        outside = self.root.parent / (self.root.name + '-outside.txt')
        outside.write_text('outside')
        self.addCleanup(outside.unlink)
        (self.root/'escape.txt').symlink_to(outside)
        self.assertNotIn('test/escape',wc.inventory([('test',self.root)]))
        for texts, seed in [(None,0),({'a':None},0),({'a':'x'},True),({'a':'x'},-1),({'a':'x'},'123')]:
            with self.subTest(texts=texts,seed=seed),self.assertRaises(ValueError):
                wc.expand(texts,seed,self.files)


if __name__ == '__main__':
    unittest.main()
