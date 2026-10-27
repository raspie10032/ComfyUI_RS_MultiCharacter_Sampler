import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
p = importlib.import_module(Path(__file__).resolve().parents[1].name+'.progressive')
r = importlib.import_module(Path(__file__).resolve().parents[1].name+'.resolution_control')


class ProgressiveTests(unittest.TestCase):
    def test_scale_and_full_schedule(self):
        for bad in (True, .49, 1.01, float('nan'), '0.5'):
            with self.assertRaises(ValueError):p.validate_scale(bad)
        for steps in (2,3,4,8,30,100):
            for scale in (.5,.67,.99,1.):
                plan=p.resolution_plan(1152,1728,steps,scale)
                self.assertEqual(plan[0]['start'],0)
                self.assertEqual(plan[-1]['end'],steps)
                self.assertEqual((plan[-1]['width'],plan[-1]['height']),(1152,1728))
                self.assertEqual(sum(s['end']-s['start'] for s in plan),steps)
                self.assertTrue(all(s['end']>s['start'] for s in plan))
                self.assertEqual(len(plan),1) if scale==1 else None
        self.assertEqual([s['start'] for s in p.resolution_plan(1152,1728,30,2/3)],[0,8,16])
        self.assertEqual([(s['width'],s['height']) for s in p.resolution_plan(1152,1728,30,2/3)],[(768,1152),(960,1440),(1152,1728)])

    def test_float_lanczos_constant_range_and_five_dimensional_latents(self):
        for shape in ((1,4,6,8),(1,16,1,6,8)):
            source=torch.full(shape,2.25)
            out=p.resize_lanczos(source,(12,16))
            self.assertEqual(out.shape,(*shape[:-2],12,16))
            torch.testing.assert_close(out,torch.full_like(out,2.25))
            self.assertIs(p.resize_lanczos(source,(6,8)),source)
        source=torch.randn(1,4,6,8)*4
        self.assertTrue(torch.isfinite(p.resize_lanczos(source,(12,16))).all())

    def test_only_exclusive_small_grids_get_floor(self):
        self.assertEqual(r.separation_for_grid(None,[4,4],.9,.2,None),(None,None))
        value,record=r.separation_for_grid({'final_grid':[8,8]},[4,4],.9,.2,None)
        self.assertEqual(value,.99)
        self.assertEqual(record['area_ratio'],.25)
        self.assertIsNone(r.separation_for_grid({'final_grid':[8,8]},[8,8],.9,.2,None)[0])
        self.assertEqual(r.separation_for_grid({'final_grid':[8,8]},[8,8],.9,.2,.3)[0],.3)

    def run_segments(self,fail=False):
        mask=torch.rand(1,8,8)
        condition={'mask':mask}
        model=SimpleNamespace(latent_image=torch.zeros(1,4,8,8),inner_model=SimpleNamespace(conds={'positive':[condition]}))
        calls=[];callbacks=[];audit={}
        def native(_model,x,sigmas,extra_args,callback,disable,**options):
            calls.append((list(x.shape),len(sigmas)-1,list(condition['mask'].shape)))
            if fail:raise RuntimeError('interrupted')
            for i in range(len(sigmas)-1):
                x=x*.8
                callback({'i':i,'sigma':sigmas[i],'denoised':x,'x':x})
            return x
        native=SimpleNamespace(sampler_function=native,extra_options={})
        sampling=SimpleNamespace(sigma_max=1.,noise_scaling=lambda s,n,x,max_denoise=False:x+n*s)
        settings={'width':128,'height':128,'seed':42,'sampler_name':'euler'}
        plan=p.resolution_plan(128,128,8,.5)
        import comfy.sample,comfy.model_management
        with patch.object(comfy.sample,'prepare_noise',side_effect=lambda x,seed:torch.zeros_like(x)),patch.object(comfy.model_management,'throw_exception_if_processing_interrupted'):
            function=p.stage_integrator(native,plan,settings,sampling,(8,8),audit)
            try:out=function(model,torch.zeros(1,4,8,8),torch.linspace(1,0,9),callback=lambda d:callbacks.append(d['i']))
            finally:self.assertIs(condition['mask'],mask)
        self.assertEqual(callbacks,list(range(8)))
        self.assertEqual(sum(c[1] for c in calls),8)
        self.assertEqual(out.shape,(1,4,8,8))
        self.assertEqual(len(audit['transitions']),2)
        self.assertEqual(calls[0][2], [1,4,4])

    def test_native_schedule_masks_and_progress_are_preserved(self):self.run_segments()
    def test_failure_restores_original_mask(self):
        with self.assertRaisesRegex(RuntimeError,'interrupted'):self.run_segments(True)

if __name__=='__main__':unittest.main()
