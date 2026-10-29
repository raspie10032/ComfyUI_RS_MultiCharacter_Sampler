"""Native small-model math, rectangular regional routing, and cache ownership."""
import ast,importlib,os,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
import torch
PKG=Path(__file__).resolve().parents[1].name
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

@unittest.skipUnless(os.environ.get('RS_MC_TEST_COMFYUI'),'Native ComfyUI required')
class AsymmetricTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  sys.path.insert(0,os.environ['RS_MC_TEST_COMFYUI'])
  from comfy.cli_args import args
  args.cpu=True
  import comfy.ops,comfy.model_management
  cls.mm=comfy.model_management;cls.previous=getattr(cls.mm,'in_training',False);cls.mm.in_training=True
  from comfy.ldm.cosmos.predict2 import MiniTrainDIT
  torch.manual_seed(882)
  cls.dm=MiniTrainDIT(16,16,2,16,16,2,1,concat_padding_mask=False,model_channels=32,num_blocks=2,num_heads=2,
   mlp_ratio=2,crossattn_emb_channels=32,pos_emb_cls='rope3d',rope_enable_fps_modulation=False,dtype=torch.float32,operations=comfy.ops.manual_cast)
  for p in cls.dm.parameters():p.data.normal_(0,.08)
  cls.dm.eval();cls.v2=importlib.import_module(PKG+'.anima_ref_v2');cls.frame=importlib.import_module(PKG+'.anima_ref_frame')
 @classmethod
 def tearDownClass(cls):cls.mm.in_training=cls.previous
 def runtime(self):
  plan=self.frame.ReferencePlan(None,'unused',1.,4.5,'apg',False,backend='asymmetric_v2')
  rt=self.v2.AsymmetricRuntime(plan,torch.randn(1,16,1,6,4),{});rt.weights={};return rt
 def test_cache_reuses_only_same_reference_and_grid_and_clears(self):
  rt=self.runtime();x=torch.randn(1,16,1,8,8);t=torch.tensor([.3]);c=torch.randn(1,3,32)
  with torch.inference_mode():
   a=rt.ref_forward(self.dm,x,t,c,rt.reference,{})
   b=rt.ref_forward(self.dm,x,t,c,rt.reference.clone(),{})
   self.assertTrue(torch.equal(a,b));self.assertEqual(rt.audit['reference_prefills'],1)
   rt.ref_forward(self.dm,x,t,c,rt.reference.flip(-1),{})
   self.assertEqual(rt.audit['reference_prefills'],2)
   rt.ref_forward(self.dm,x[:,:,:,:6,:],t,c,rt.reference,{})
   self.assertEqual(len(rt.ref_banks),1)
  rt.clear();self.assertFalse(rt.ref_banks);self.assertEqual(rt.audit['cache_bytes_after_sample'],0)
 def test_signature_tracks_inference_weights_and_native_hook_strength(self):
  with torch.inference_mode():
   net=torch.nn.Linear(3,3)
  hook=types.SimpleNamespace(strength=.8)
  patcher=types.SimpleNamespace(current_hooks=types.SimpleNamespace(hooks=[hook]))
  a=self.v2.weight_signature(net,patcher)
  hook.strength=.4
  self.assertNotEqual(a,self.v2.weight_signature(net,patcher))
 def test_base_weight_mutation_invalidates_reference_cache(self):
  rt=self.runtime();x=torch.randn(1,16,1,8,8);t=torch.tensor([.3]);c=torch.randn(1,3,32)
  with torch.inference_mode():
   rt.ref_forward(self.dm,x,t,c,rt.reference,{})
   self.dm.blocks[-1].mlp.layer2.weight.add_(.01)
   rt.ref_forward(self.dm,x,t,c,rt.reference,{})
  self.assertEqual(rt.audit['reference_prefills'],2)
  self.assertEqual(len(rt.ref_banks),1)
 def test_prefill_not_affected_by_target_text_and_has_no_text_attention(self):
  rt=self.runtime();x=torch.randn(1,16,1,8,8);t=torch.tensor([.3]);c=torch.randn(1,3,32)
  counts=[]
  handles=[b.cross_attn.register_forward_hook(lambda *args:counts.append(1)) for b in self.dm.blocks]
  try:
   with torch.inference_mode():
    rt.ref_forward(self.dm,x,t,c,rt.reference,{})
    rt.ref_forward(self.dm,x+1,t,c+1,rt.reference,{})
   self.assertEqual(len(counts),4);self.assertEqual(rt.audit['reference_prefills'],1)
  finally:
   for h in handles:h.remove()
 def test_native_upstream_asymmetric_math_matches(self):
  path=Path(os.environ.get('RS_ANIMA_V2_UPSTREAM','/missing'))
  if not path.exists():self.skipTest('Optional pinned upstream source')
  tree=ast.parse(path.read_text());names={'_block_mods','_norm','_asym_block','_frame_positions','_rope_from_positions','_frame_embed','_encode_ref_asym','_asym_forward'}
  tree.body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
  import comfy.ldm.common_dit
  ns={'torch':torch,'comfy':sys.modules['comfy']};exec(compile(tree,str(path),'exec'),ns)
  rt=self.runtime();x=torch.randn(1,16,1,8,8);t=torch.tensor([.3]);c=torch.randn(1,3,32)
  with torch.inference_mode():
   bank=ns['_encode_ref_asym'](self.dm,rt.reference,(4,0))
   expected=ns['_asym_forward'](self.dm,x,t,c,bank,{})
   actual=rt.ref_forward(self.dm,x,t,c,rt.reference,{})
  torch.testing.assert_close(actual,expected,rtol=1e-5,atol=1e-6)
 def test_rectangular_attention_matches_dense_and_preserves_reference_columns(self):
  rs=importlib.import_module(PKG+'.reference_spatial');routing=importlib.import_module(PKG+'.routing')
  groups=routing.BoxGroups([torch.tensor([0,1]),torch.tensor([1,2])],[((0,),torch.tensor([0])),((0,1),torch.tensor([1])),((1,),torch.tensor([2])),((),torch.tensor([3]))],torch.tensor([3]))
  q=torch.randn(1,4,2,4);k=torch.randn(1,7,2,4);v=torch.randn_like(k)
  bias=rs.compact_bias(groups,4,7,q,.8,.9);dense=q.new_zeros(4,7)
  for row,(_,ix) in zip(bias.rows,bias.cells):dense[ix]=row
  torch.testing.assert_close(rs.rectangular_attention(q,k,v,bias),routing.sdpa(q,k,v,dense))
  self.assertTrue(torch.all(dense[:,4:]==0))
 def test_exception_clears_bank_and_restores_hooks(self):
  rt=self.runtime();rt.ref_banks['fake']=[(torch.ones(1),torch.ones(1))]
  rt.model_patcher=object()
  def fail():
   with rt.installed(self.dm,torch.randn(1,3,32),True):raise RuntimeError('cancel')
  with patch.object(rt,'load_weights'),self.assertRaisesRegex(RuntimeError,'cancel'):rt.sample(fail)
  self.assertFalse(rt.ref_banks);self.assertIsNone(rt.weights)
  self.assertIsNone(rt.model_patcher)
  self.assertTrue(all(not m._forward_hooks for m in self.dm.modules()))
 def test_unsupported_models_and_attention_patches_rejected(self):
  with self.assertRaisesRegex(ValueError,'2B'):self.runtime().load_weights(types.SimpleNamespace(blocks=[None]*40))
  rt=self.runtime()
  with self.assertRaisesRegex(ValueError,'attention patches'):
   rt.ref_forward(self.dm,None,None,None,None,{'patches':{'x':[]}})
 def test_auto_v2_rejects_29b_before_asset_resolution(self):
  from comfy.model_base import Anima
  ref=self.frame
  model=types.SimpleNamespace(model=Anima.__new__(Anima),get_model_object=lambda name:types.SimpleNamespace(blocks=[None]*40))
  with patch(ref.__package__+'.reference_assets._verified_adapter') as download:
   with self.assertRaisesRegex(ValueError,'2B'):
    ref.RSAnimaReferenceAdapter().apply(model,adapter_name='Auto: Anima v2 (2B)')
   download.assert_not_called()
 def test_auto_v2_resolves_verified_adapter_with_progress_id(self):
  from comfy.model_base import Anima
  from safetensors.torch import save_file
  import tempfile,json
  ref=self.frame
  clone=types.SimpleNamespace(model_options={},remove_wrappers_with_key=lambda *a:None,add_wrapper_with_key=lambda *a:None)
  model=types.SimpleNamespace(model=Anima.__new__(Anima),get_model_object=lambda name:types.SimpleNamespace(blocks=[None]*28),clone=lambda:clone)
  with tempfile.TemporaryDirectory() as directory:
   path=str(Path(directory)/'adapter.safetensors');save_file({},path,metadata={'anima_ref_adapter':json.dumps({'arch':'asym'})})
   with patch(ref.__package__+'.reference_assets._verified_adapter',return_value=path) as download:
    result,=ref.RSAnimaReferenceAdapter().apply(model,adapter_name='Auto: Anima v2 (2B)',unique_id='node42')
   download.assert_called_once_with('anima_frame_v2','node42')
   self.assertEqual(result.model_options[ref.PLAN].backend,'asymmetric_v2')
