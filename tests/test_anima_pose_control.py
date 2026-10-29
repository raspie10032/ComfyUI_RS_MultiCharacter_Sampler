import importlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent))


class PosePatchValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.check = staticmethod(importlib.import_module(ROOT.name+'.anima_pose_control').validate_model_patches)
        if os.environ.get("RS_MC_TEST_COMFYUI"):
            sys.path.insert(0,os.environ["RS_MC_TEST_COMFYUI"])
            from comfy.cli_args import args
            args.cpu=True
        try:
            from comfy.ldm.anima.lllite import AnimaLLLitePatch, AnimaLLLiteAttentionPatch, AnimaLLLiteMLPPatch
        except ImportError:
            raise unittest.SkipTest('Native ComfyUI Anima LLLite is not available')
        cls.kinds = (AnimaLLLitePatch, AnimaLLLiteAttentionPatch, AnimaLLLiteMLPPatch)

    def model(self, count=28, width=2048):
        Root, Attention, MLP = self.kinds
        root = Root(NS(model=NS(block_count=count,model_dim=width)), None, None, 1., 1., 0.)
        patches = {'post_input':[root],
                   'attn1_patch':[Attention(root,{'q':'self_attn_q_proj','k':'self_attn_k_proj','v':'self_attn_v_proj'})],
                   'attn2_patch':[Attention(root,{'q':'cross_attn_q_proj'})], 'mlp_patch':[MLP(root)]}
        block=NS(self_attn=NS(q_proj=NS(weight=NS(shape=(2048,2048)))))
        return NS(model_options={'transformer_options':{'patches':patches}},get_model_object=lambda _:NS(blocks=[block]*28))

    def test_unpatched_model(self):
        self.assertFalse(self.check(NS(model_options={}), 'Anima'))

    def test_complete_native_group_and_chain(self):
        a=self.model();b=self.model()
        self.assertTrue(self.check(a,'Anima'))
        for key in a.model_options['transformer_options']['patches']:
            a.model_options['transformer_options']['patches'][key] += b.model_options['transformer_options']['patches'][key]
        self.assertTrue(self.check(a,'Anima'))

    def test_incomplete_or_foreign_patch_rejected(self):
        for key in ['post_input','attn1_patch','attn2_patch','mlp_patch']:
            with self.subTest(key=key):
                m=self.model();del m.model_options['transformer_options']['patches'][key]
                with self.assertRaisesRegex(ValueError,'native'):self.check(m,'Anima')
        m=self.model();m.model_options['transformer_options']['patches']['attn1_patch'].append(lambda *args:None)
        with self.assertRaises(ValueError):self.check(m,'Anima')

    def test_mismatched_roots_dimensions_targets_and_family(self):
        for count,width in [(40,2048),(28,2560)]:
            with self.assertRaisesRegex(ValueError,'dimensions'):self.check(self.model(count,width),'Anima')
        m=self.model();m.model_options['transformer_options']['patches']['attn1_patch'][0].patch=self.model().model_options['transformer_options']['patches']['post_input'][0]
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.check(m,'Anima')
        m=self.model();m.model_options['transformer_options']['patches']['attn1_patch'][0].targets={}
        with self.assertRaises(ValueError):self.check(m,'Anima')
        for family in ['SDXL','MOSS','Krea2','FLUX1']:
            with self.assertRaises(ValueError):self.check(self.model(),family)

    def test_replacements_and_overrides_rejected(self):
        for key in ['patches_replace','optimized_attention_override']:
            m=self.model();m.model_options['transformer_options'][key]={'x':1}
            with self.assertRaises(ValueError):self.check(m,'Anima')
