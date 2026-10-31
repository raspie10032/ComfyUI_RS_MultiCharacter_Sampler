import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
p = importlib.import_module(ROOT.name + '.pose_pipe')
b = importlib.import_module(ROOT.name + '.character_builder')
m = importlib.import_module(ROOT.name + '.metadata')
s = importlib.import_module(ROOT.name + '.pose3d')


class Model:
    def __init__(self, count=28):
        self.model_options = {}
        self.count = count

    def clone(self):
        other = Model(self.count)
        other.model_options = dict(self.model_options)
        return other

    def get_model_object(self, _):
        return NS(blocks=[None] * self.count)


class PipePoseTests(unittest.TestCase):
    def plan(self, **values):
        return json.dumps(dict(scene=s.default_scene(), mode='auto', strength=1., start=0., end=1., **values))

    def test_builder_has_no_model_inputs_and_keeps_output_indices(self):
        node = importlib.import_module(ROOT.name + '.pose3d_node').RSMultiCharacterPose3D
        schema = node.INPUT_TYPES()
        for group in ('required', 'optional'):
            self.assertFalse({'model', 'vae', 'model_patch'} & schema[group].keys())
        self.assertEqual(node.RETURN_NAMES[0], 'building_pipe')
        self.assertEqual(node.RETURN_NAMES[5], 'pose_image')
        self.assertIn('pose_control', schema['optional'])

    def test_invalid_interval_and_nonfinite_strength_rejected(self):
        for field, value in [('strength', float('nan')), ('start', True), ('end', 0.)]:
            plan = json.loads(self.plan());plan[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):p.pipe_pose_settings(plan)

    def test_pipe_order_and_context_roundtrip(self):
        plan = self.plan()
        geometry = b.BuildPipe(pose3d_json=plan, prompt_count=1)
        before = b.update_slot(geometry, 1, kind='character', prompt='girl')
        prompt = b.update_slot(b.BuildPipe(prompt_count=1), 1, kind='character', prompt='girl')
        after = b.replace(prompt, pose3d_json=plan)
        for pipe in (before, after):
            context = b.finalize(pipe)
            self.assertEqual(context.pose3d_json, plan)
            restored = m.pipe_from_record(m.pipe_record(context))
            self.assertEqual(json.loads(restored.pose3d_json), json.loads(plan))
            self.assertEqual(b.finalize(importlib.import_module(ROOT.name + '.pipe_compat').building_pipe(restored)).pose3d_json, restored.pose3d_json)

    def test_disabled_and_unsupported_paths_never_load(self):
        assets = importlib.import_module(ROOT.name + '.reference_assets')
        with patch.object(assets, '_verified_adapter') as download:
            for mode, strength, family, count in [('masks_only',1,'Anima',28), ('auto',0,'Anima',28),
                                                ('auto',1,'Anima',40), ('auto',1,'SDXL',28)]:
                plan=json.loads(self.plan());plan.update(mode=mode,strength=strength)
                model=Model(count);pipe=NS(pose3d_json=json.dumps(plan),characters=())
                result,status=p.apply_pipe_pose(model,None,pipe,family,768,1024)
                self.assertIs(result,model);self.assertFalse(status['applied'])
            download.assert_not_called()

    def test_scene_routes_deferred_and_clones_model(self):
        for family in ('Krea2','MOSS'):
            model=Model();pipe=NS(pose3d_json=self.plan(),characters=())
            work,status=p.apply_pipe_pose(model,'vae',pipe,family,768,1024)
            self.assertIsNot(work,model);self.assertEqual(model.model_options,{})
            self.assertTrue(status['applied']);self.assertEqual(work.model_options['rs_3d_pose']['family'],family)

    def test_conflicts_rejected_before_download(self):
        assets=importlib.import_module(ROOT.name+'.reference_assets')
        with patch.object(assets,'_verified_adapter') as download:
            model=Model();pipe=NS(pose3d_json=self.plan(),characters=(NS(reference=NS(strength=1.)),))
            with self.assertRaisesRegex(ValueError,'image reference'):p.apply_pipe_pose(model,None,pipe,'Anima',768,1024)
            pipe.characters=();model.model_options['rs_3d_pose']={"family":"MOSS"}
            with self.assertRaisesRegex(ValueError,'already patched'):p.apply_pipe_pose(model,None,pipe,'Anima',768,1024)
            model.model_options={'rs_progressive_scale':.5}
            with self.assertRaisesRegex(ValueError,'full resolution'):p.apply_pipe_pose(model,None,pipe,'MOSS',768,1024)
            download.assert_not_called()


if __name__ == '__main__':unittest.main()
