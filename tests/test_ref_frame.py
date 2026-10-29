"""Native CPU reference math and isolation; no network/model downloads."""
import importlib, os, sys, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import torch
PKG=Path(__file__).resolve().parents[1].name
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

@unittest.skipUnless(os.environ.get('RS_MC_TEST_COMFYUI'),'Native ComfyUI required')
class RefFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,os.environ['RS_MC_TEST_COMFYUI'])
        from comfy.cli_args import args
        args.cpu=True
        import comfy.ops, comfy.model_management
        cls.mm=comfy.model_management;cls.previous=getattr(cls.mm,'in_training',False);cls.mm.in_training=True
        from comfy.ldm.cosmos.predict2 import MiniTrainDIT
        torch.manual_seed(882)
        cls.dm=MiniTrainDIT(16,16,2,16,16,2,1,concat_padding_mask=False,model_channels=32,num_blocks=2,num_heads=2,
            mlp_ratio=2,crossattn_emb_channels=32,pos_emb_cls='rope3d',rope_enable_fps_modulation=False,
            dtype=torch.float32,operations=comfy.ops.manual_cast)
        for p in cls.dm.parameters():p.data.normal_(0,.08)
        cls.dm.eval()
        cls.ref=importlib.import_module(PKG+'.anima_ref_frame')

    @classmethod
    def tearDownClass(cls):cls.mm.in_training=cls.previous

    def runtime(self,cache=True,limit=256*2**20):
        plan=self.ref.ReferencePlan(torch.zeros(1,8,8,3),'unused',1.,4.5,'apg',cache)
        rt=self.ref.FrameRuntime(plan,torch.randn(1,16,1,8,8),{},cache_limit=limit)
        rt.weights={} # clean tiny native math, adapter hooks tested separately
        return rt

    def test_frame_rope_matches_upstream(self):
        roots=[p/'source/__init__.py' for p in Path(__file__).resolve().parents[2:4]]
        root=next((p for p in roots if p.exists() and 'def _frame_positions' in p.read_text()),None)
        if root is None:self.skipTest('Optional local upstream control')
        spec=importlib.util.spec_from_file_location('test_ref_upstream',root)
        up=importlib.util.module_from_spec(spec);spec.loader.exec_module(up)
        positions=[up._frame_positions(0,4,3,0,0,'cpu'),up._frame_positions(1,4,3,4,0,'cpu')]
        expected=up._rope_from_positions(self.dm.pos_embedder,*(torch.cat(a) for a in zip(*positions)))
        actual=self.ref.frame_rope(self.dm.pos_embedder,4,3,'cpu')
        self.assertTrue(torch.equal(expected,actual))

    def test_native_reference_forward_finite(self):
        rt=self.runtime(False);x=torch.randn(1,16,1,8,8);t=torch.tensor([.7]);c=torch.randn(1,4,32)
        with torch.no_grad():
            result=rt.ref_forward(self.dm,x,t,c,rt.reference,{})
        self.assertEqual(tuple(result.shape),tuple(x.shape));self.assertTrue(torch.isfinite(result).all())

    def test_native_cached_matches_uncached_and_restores(self):
        rt=self.runtime();x=torch.randn(1,16,1,8,8);t=torch.tensor([.7]);c=torch.randn(1,4,32)
        with torch.no_grad():
            expected=rt.ref_forward(self.dm,x,t,c,rt.reference,{})
            with rt.installed(self.dm,c,True):one=rt.ref_forward(self.dm,x,t,c,rt.reference,{})
            with rt.installed(self.dm,c.clone(),True):two=rt.ref_forward(self.dm,x,t,c,rt.reference,{})
        self.assertTrue(torch.equal(expected,one));self.assertTrue(torch.equal(expected,two))
        self.assertEqual(rt.audit['kv_hits'],2)
        self.assertTrue(all('compute_qkv' not in b.cross_attn.__dict__ for b in self.dm.blocks))

    def test_changed_caption_and_adapter_state_do_not_reuse(self):
        rt=self.runtime();c=torch.randn(1,4,32)
        first=rt._context_id(c,True)
        self.assertEqual(first,rt._context_id(c.clone(),True))
        self.assertNotEqual(first,rt._context_id(c+1,True))
        self.assertNotEqual(first,rt._context_id(c,False))

    def test_error_and_cancel_clear_handles_and_cache(self):
        rt=self.runtime();c=torch.randn(1,4,32)
        with self.assertRaisesRegex(RuntimeError,'cancel'):
            def operation():
                with rt.installed(self.dm,c,True):raise RuntimeError('cancel')
            rt.sample(operation)
        self.assertFalse(rt.kv);self.assertFalse(rt.contexts);self.assertIsNone(rt.weights)
        self.assertTrue(all('compute_qkv' not in b.cross_attn.__dict__ for b in self.dm.blocks))

    def test_bounded_cache_and_zero_cache(self):
        rt=self.runtime(limit=600);x=torch.randn(1,4,32);c=torch.randn(1,4,32)
        with torch.no_grad(),rt.installed(self.dm,c,False):
            for b in self.dm.blocks:b.cross_attn.compute_qkv(x,c)
        self.assertLessEqual(rt.bytes,600)
        rt=self.runtime(limit=0)
        with torch.no_grad(),rt.installed(self.dm,c,False):self.dm.blocks[0].cross_attn.compute_qkv(x,c)
        self.assertEqual(rt.bytes,0)

    def test_regional_lora_disables_cache(self):
        plan=self.runtime().plan
        rt=self.ref.FrameRuntime(plan,torch.zeros(1,16,1,8,8),{},cache_allowed=False)
        self.assertFalse(rt.cache_enabled);self.assertIsNone(rt._context_id(torch.ones(1,4,32),True))

    def test_regional_target_and_reference_tokens(self):
        engine=importlib.import_module(PKG+'.engine')
        masks=torch.zeros(2,4,4);masks[0,:,:2]=1;masks[1,:,2:]=1
        audit=dict(forwards=[],cross_calls=0,self_calls=0,restored_forwards=0)
        routing=engine.AnimaRouting([],masks,'character_first',audit,3)
        routing.contexts=[torch.randn(1,4,32),torch.randn(1,5,32)];routing.sigmas=[1.,.5,0.]
        rt=self.runtime(False)
        def native(x,t,context,**kwargs):return rt.ref_forward(self.dm,x,t,context,rt.reference,kwargs['transformer_options'])
        native.class_obj=self.dm
        before=[(b.cross_attn.attn_op,b.self_attn.attn_op) for b in self.dm.blocks]
        with torch.no_grad():out=routing.forward(native,torch.randn(1,16,1,8,8),torch.tensor([.5]),torch.randn(1,3,32),
            transformer_options=dict(cond_or_uncond=[0],sigmas=torch.tensor([.5]),rs_reference_frame=True))
        self.assertEqual(out.shape,(1,16,1,8,8));self.assertTrue(torch.isfinite(out).all())
        self.assertEqual(audit['cross_calls'],2);self.assertEqual(audit['self_calls'],2)
        self.assertEqual(before,[(b.cross_attn.attn_op,b.self_attn.attn_op) for b in self.dm.blocks])

    def test_small_cache_keeps_subset_instead_of_thrashing(self):
        rt=self.runtime(limit=1200);x=torch.randn(1,4,32);c=torch.randn(1,4,32)
        with torch.no_grad():
            for _ in range(2):
                with rt.installed(self.dm,c,False):
                    for b in self.dm.blocks:b.cross_attn.compute_qkv(x,c)
        self.assertEqual(rt.audit['kv_hits'],1)
        self.assertEqual(rt.audit['kv_misses'],3)
        self.assertLessEqual(rt.bytes,1200)

    def test_native_sampler_rejects_ignored_reference(self):
        with self.assertRaisesRegex(ValueError,'RS MultiCharacter Sampler'):
            self.ref.require_sampler(lambda:None,transformer_options={})
        self.assertEqual(self.ref.require_sampler(lambda **k:42,transformer_options={'rs_anima_ref_ready':True}),42)

    def test_zero_bypass_does_not_resolve_or_load_adapter(self):
        import comfy.model_base
        Anima = getattr(comfy.model_base, 'Anima', None)
        if Anima is None:
            self.skipTest('This ComfyUI predates Anima model support')
        from unittest.mock import Mock
        parent=Mock();parent.model=Mock(spec=Anima)
        child=parent.clone.return_value;child.model_options={self.ref.PLAN:object()}
        with patch('folder_paths.get_full_path_or_raise',side_effect=AssertionError('unexpected file access')):
            result=self.ref.RSAnimaReferenceAdapter().apply(parent,torch.zeros(1,8,8,3),'missing',strength=0)[0]
        self.assertIs(result,child);self.assertNotIn(self.ref.PLAN,child.model_options)

    def test_adapter_file_failure_has_no_live_hooks(self):
        rt=self.runtime();rt.weights=None
        # Valid architecture reaches file validation; the tiny math model has
        # only two blocks and would otherwise fail before reading any weights.
        with patch('comfy.utils.load_torch_file',return_value={}) as loader:
            with self.assertRaisesRegex(ValueError,'참조 어댑터'):
                rt.load_weights(SimpleNamespace(blocks=[None]*28))
        loader.assert_called_once_with('unused',safe_load=True)
        self.assertTrue(all('compute_qkv' not in b.cross_attn.__dict__ for b in self.dm.blocks))

    def test_numbered_reference_key_isolation_and_overlap(self):
        routing=importlib.import_module(PKG+'.routing')
        size=4
        groups=routing.BoxGroups([torch.tensor([0,1]),torch.tensor([1,2])],
            [((0,),torch.tensor([0])),((0,1),torch.tensor([1])),
             ((1,),torch.tensor([2])),((),torch.tensor([3]))],torch.tensor([3]))
        q=torch.randn(1,12,2,4);k=torch.randn_like(q);v=torch.randn_like(q)
        bias=torch.zeros(size,size)
        one=self.ref.route_character_references(q,k,v,groups,size,bias,(0,1),(1.,1.))
        changed=v.clone();changed[:,8:]+=10
        two=self.ref.route_character_references(q,k,changed,groups,size,bias,(0,1),(1.,1.))
        self.assertTrue(torch.equal(one[:,0],two[:,0]))  # owner A cannot read B
        self.assertTrue(torch.equal(one[:,3],two[:,3]))  # background reads no source
        self.assertTrue(torch.equal(one[:,4:8],two[:,4:8])) # source A isolated
        self.assertFalse(torch.equal(one[:,1],two[:,1])) # overlap reads both
        self.assertFalse(torch.equal(one[:,2],two[:,2])) # owner B reads B
        self.assertTrue(torch.equal(one[:,8:],routing.sdpa(q[:,8:],k[:,8:],v[:,8:])))

    def test_multi_reference_native_forward_and_all_restorations(self):
        engine=importlib.import_module(PKG+'.engine')
        masks=torch.zeros(2,4,4);masks[0,:,:2]=1;masks[1,:,2:]=1
        audit=dict(forwards=[],cross_calls=0,self_calls=0,restored_forwards=0)
        routing=engine.AnimaRouting([],masks,'character_first',audit,3)
        routing.contexts=[torch.randn(1,4,32),torch.randn(1,5,32)];routing.sigmas=[1.,.5,0.]
        rt=self.runtime(False);rt.reference=torch.randn(1,16,2,8,8)
        def native(x,t,context,**kwargs):return rt.ref_forward(self.dm,x,t,context,rt.reference,kwargs['transformer_options'])
        native.class_obj=self.dm
        before=[(b.cross_attn.attn_op,b.self_attn.attn_op) for b in self.dm.blocks]
        with torch.no_grad():out=routing.forward(native,torch.randn(1,16,1,8,8),torch.tensor([.5]),torch.randn(1,3,32),
            transformer_options=dict(cond_or_uncond=[0],sigmas=torch.tensor([.5]),rs_reference_frame=True,
                rs_reference_count=2,rs_reference_slots=(0,1),rs_reference_strengths=(1.,1.)))
        self.assertEqual(out.shape,(1,16,1,8,8));self.assertTrue(torch.isfinite(out).all())
        self.assertEqual(before,[(b.cross_attn.attn_op,b.self_attn.attn_op) for b in self.dm.blocks])

    def test_reference_builder_order_disable_and_metadata(self):
        from dataclasses import replace
        builder=importlib.import_module(PKG+'.character_builder')
        metadata=importlib.import_module(PKG+'.metadata')
        node=self.ref.RSAnimaCharacterReference()
        pixels=torch.rand(1,8,8,3)
        first=node.apply(pixels,2)[0]
        first=builder.update_slot(first,2,prompt='woman',x=.75)
        first=builder.update_slot(first,1,prompt='woman',x=.25)
        first=replace(first,prompt_count=2)
        second=builder.update_slot(None,1,prompt='woman',x=.25)
        second=builder.update_slot(second,2,prompt='woman',x=.75)
        second=node.apply(pixels,2,building_pipe=replace(second,prompt_count=2))[0]
        a,b=builder.finalize(first),builder.finalize(second)
        self.assertEqual(a.characters[1].reference.source,b.characters[1].reference.source)
        self.assertIsNone(a.characters[0].reference)
        record=metadata.build_record(a,dict(width=8,height=8,seed=1,steps=1,cfg=4,
            sampler_name='euler',scheduler='normal'),{},[],{'spatial_slots':2})
        self.assertEqual(record['rs_multicharacter']['image_references'][0]['method'],'anima_reference_frame')
        self.assertNotIn('pixels',str(record))
        self.assertTrue(all(c.reference is None for c in metadata.pipe_from_record(record).characters))
        disabled=node.apply(None,2,enabled=False,building_pipe=first)[0]
        self.assertIsNone(builder.finalize(disabled).characters[1].reference)

    def test_precision_reference_predictions_stay_in_numbered_masks(self):
        import comfy.samplers
        from dataclasses import replace
        rt=self.runtime(False);rt.plan=replace(rt.plan,correction='none',guidance=1.)
        rt.slots=(0,1);rt.strengths=(1.,1.)
        rt.reference=torch.zeros(1,16,2,8,8)
        rt.masks=torch.zeros(2,8,8);rt.masks[0,:,:3]=1;rt.masks[1,:,5:]=1
        pos=[[torch.zeros(1,2,32),{}]];neg=[[torch.zeros(1,2,32),{}]]
        fake_model=SimpleNamespace(model_options={},is_dynamic=lambda:False)
        guider=self.ref.reference_guider(fake_model,pos,neg,rt,1.)
        guider.conds={k:k for k in ('positive_base','negative_base','positive_0','negative_0','positive_1','negative_1')}
        guider.inner_model=None;x=torch.zeros(1,16,8,8)
        calls=[]
        def predict(model,conds,x,t,options):
            calls.append(conds)
            if conds[0]=='positive_base':return torch.full_like(x,4),torch.ones_like(x)
            return torch.full_like(x,2 if conds[0]=='positive_0' else 6),torch.ones_like(x)
        with patch.object(comfy.samplers,'calc_cond_batch',predict):
            result,_,_=guider.numbered_prediction(x,torch.tensor([.5]),{})
        self.assertEqual(len(calls),3)
        self.assertTrue(torch.all(result[:,:,:,:3]==2))
        self.assertTrue(torch.all(result[:,:,:,3:5]==4))
        self.assertTrue(torch.all(result[:,:,:,5:]==6))

    def test_packed_grid_native_math_and_hook_cleanup(self):
        rt=self.runtime(False);x=torch.randn(1,16,1,8,8);t=torch.tensor([.3]);context=torch.randn(1,2,32)
        before=sum(len(m._forward_hooks) for m in self.dm.modules())
        with torch.inference_mode():
            native=rt.ref_forward(self.dm,x,t,context,rt.reference,{})
            packed=rt.packed_forward(self.dm,x,t,context,rt.reference,{},x.shape)
            torch.testing.assert_close(native,packed,atol=1e-6,rtol=1e-5)
            small=rt.ref_forward(self.dm,x,t,context,rt.reference[:,:,:,:6,:6],{})
            self.assertEqual(small.shape,x.shape)
            self.assertTrue(torch.isfinite(small).all())
        self.assertEqual(rt.audit['reference_tokens'],9)
        self.assertEqual(sum(len(m._forward_hooks) for m in self.dm.modules()),before)
        with patch.object(self.dm.blocks[0],'forward',side_effect=RuntimeError('cancel')):
            with self.assertRaises(RuntimeError):
                rt.ref_forward(self.dm,x,t,context,rt.reference[:,:,:,:6,:6],{})
        self.assertEqual(sum(len(m._forward_hooks) for m in self.dm.modules()),before)

    def test_cancelled_reference_negative_matches_independent_predictions(self):
        import comfy.samplers
        from dataclasses import replace
        torch.manual_seed(197)
        x=torch.zeros(1,16,8,8)
        names=('positive_base','negative_base','positive','negative',
               'positive_0','negative_0','positive_1','negative_1')
        predictions={name:torch.randn_like(x) for name in names}
        for slots in ((),(0,1)):
            for correction in ('none','apg','rescale'):
                for guidance in (1.,4.5,4.5000001):
                    with self.subTest(slots=slots,correction=correction,guidance=guidance):
                        rt=self.runtime(False)
                        rt.plan=replace(rt.plan,correction=correction,guidance=guidance)
                        rt.slots=slots;rt.strengths=(.8,1.2) if slots else ()
                        rt.reference=torch.zeros(1,16,2 if slots else 1,8,8)
                        # Include overlap, partial weights, and uncovered background.
                        rt.masks=torch.zeros(2,8,8)
                        rt.masks[0,:,:5]=.8;rt.masks[1,:,3:7]=1.
                        cond=[[torch.zeros(1,2,32),{}]]
                        model=SimpleNamespace(model_options={},is_dynamic=lambda:False)
                        guider=self.ref.reference_guider(model,cond,cond,rt,4.5)
                        guider.conds={name:name for name in names};guider.inner_model=None
                        calls=[]
                        def predict(model,conds,x,t,options):
                            calls.extend(conds)
                            return [predictions[name] for name in conds]
                        options={'transformer_options':{'sample_sigmas':torch.tensor([1.,.5,0.])}}
                        with patch.object(comfy.samplers,'calc_cond_batch',predict):
                            guider.fold_reference_guidance=False
                            expected=guider.predict_noise(x,torch.tensor([1.]),options)
                            full_calls=len(calls);calls.clear()
                            guider.fold_reference_guidance=True
                            actual=guider.predict_noise(x,torch.tensor([1.]),options)
                        torch.testing.assert_close(actual,expected,rtol=2e-5,atol=2e-5)
                        cancelled=(len(slots) if slots else 1) if guidance==4.5 else 0
                        self.assertEqual(len(calls),full_calls-cancelled)
                        self.assertEqual(rt.audit['cancelled_reference_negative_predictions'],cancelled)

    def test_full_reference_coverage_cancels_only_unit_strength_base(self):
        import comfy.samplers
        torch.manual_seed(991)
        x=torch.zeros(1,16,8,8)
        names=('positive_base','negative_base','positive_0','negative_0','positive_1','negative_1')
        predictions={name:torch.randn_like(x) for name in names}
        for strengths in ((1.,1.),(.8,1.)):
            for overlap in (False,True):
                for partial in (False,True):
                    with self.subTest(strengths=strengths,overlap=overlap,partial=partial):
                        rt=self.runtime(False);rt.slots=(0,1);rt.strengths=strengths
                        rt.masks=torch.zeros(2,8,8)
                        rt.masks[0,:,:5 if overlap else 4]=1.;rt.masks[1,:,3 if overlap else 4:]=1.
                        if partial:rt.masks[:,0]=0.
                        cond=[[torch.zeros(1,2,32),{}]]
                        model=SimpleNamespace(model_options={},is_dynamic=lambda:False)
                        guider=self.ref.reference_guider(model,cond,cond,rt,4.5)
                        guider.conds={name:name for name in names};guider.inner_model=None
                        calls=[]
                        def predict(model,conds,x,t,options):
                            calls.extend(conds);return [predictions[name] for name in conds]
                        options={'transformer_options':{'sample_sigmas':torch.tensor([1.,.5,0.])}}
                        with patch.object(comfy.samplers,'calc_cond_batch',predict):
                            guider.fold_reference_guidance=False
                            expected=guider.predict_noise(x,torch.tensor([1.]),options)
                            calls.clear();guider.fold_reference_guidance=True
                            actual=guider.predict_noise(x,torch.tensor([1.]),options)
                        torch.testing.assert_close(actual,expected,rtol=2e-5,atol=2e-5)
                        skipped=int(strengths==(1.,1.) and not partial)
                        self.assertEqual(rt.audit['cancelled_base_positive_predictions'],skipped)
                        self.assertEqual('positive_base' not in calls,bool(skipped))
                        # Re-check coverage if this guider receives edited masks.
                        rt.masks[:,0]=0.;calls.clear()
                        with patch.object(comfy.samplers,'calc_cond_batch',predict):
                            guider.predict_noise(x,torch.tensor([1.]),options)
                        self.assertIn('positive_base',calls)

    def test_cancelled_prediction_respects_hooks_disable_and_reference_end(self):
        import comfy.samplers
        rt=self.runtime(False)
        cond=[[torch.zeros(1,2,32),{}]]
        model=SimpleNamespace(model_options={},is_dynamic=lambda:False)
        guider=self.ref.reference_guider(model,cond,cond,rt,4.5)
        names=('positive','negative','positive_base','negative_base')
        guider.conds={name:name for name in names};guider.inner_model=None
        x=torch.ones(1,16,8,8);calls=[]
        def predict(model,conds,x,t,options):
            calls.extend(conds);return [x*(i+1) for i in range(len(conds))]
        schedule={'sample_sigmas':torch.tensor([1.,.5,0.])}
        for extra in ({'disable_cfg1_optimization':True},
                      {'sampler_pre_cfg_function':[lambda a:a['conds_out']]},
                      {'sampler_cfg_function':lambda a:a['cond']},
                      {'sampler_post_cfg_function':[lambda a:a['denoised']]},
                      {'sampler_calc_cond_batch_function':object()}):
            calls.clear()
            with patch.object(comfy.samplers,'calc_cond_batch',predict):
                guider.predict_noise(x,torch.tensor([1.]),{'transformer_options':schedule,**extra})
            self.assertIn('negative',calls)
        self.assertEqual(rt.audit['cancelled_reference_negative_predictions'],0)
        rt.end_step=0;calls.clear()
        with patch.object(comfy.samplers,'calc_cond_batch',predict):
            guider.predict_noise(x,torch.tensor([1.]),{'transformer_options':schedule})
        self.assertEqual(calls,['positive_base','negative_base'])
        self.assertEqual(rt.audit['cancelled_reference_negative_predictions'],0)

if __name__=='__main__':unittest.main()
