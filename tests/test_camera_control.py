# SPDX-License-Identifier: GPL-3.0-only
"""The camera node is importable without ComfyUI or a GPU."""
from dataclasses import dataclass, field
import importlib.util
import json
import math
import sys
import types
from pathlib import Path
import unittest

parent = types.ModuleType("_rs_camera_unit")
parent.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules[parent.__name__] = parent
spec = importlib.util.spec_from_file_location("_rs_camera_unit.camera_control", Path(__file__).resolve().parents[1]/"camera_control.py")
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)


@dataclass(frozen=True)
class Caption:
    prompt: str
    uc: str = "unchanged UC"
    x: float = .28
    y: float = .5
    lora_name: str = "test.safetensors"


@dataclass(frozen=True)
class SharedContext:
    prompt: str | None = "cafe, two adult women"
    syntax: str = "ComfyUI"
    characters: tuple = (Caption("brown hair"), Caption("pink hair", x=.72))
    character_syntax: str | None = None
    text_regions: tuple = (Caption("a sign"),)
    negative_prompt: str = "blur"
    generation_json: str = '{"steps":30,"scheduler":"sgm_uniform"}'
    local_record_json: str = '{"character_masks":[1,2]}'
    model: str = "V5 Full"
    source_seed: int = 999
    settings: dict = field(default_factory=lambda: {"lora":"RSCV5"})


class CameraTests(unittest.TestCase):
    def test_atelier_selects_all_42_training_views_and_shares_composition(self):
        node = camera.RSAtelierSphereCameraControl()
        model = object()
        source = SharedContext()
        views = json.loads((Path(__file__).resolve().parents[1] / "atelier_camera_views.json").read_text())
        self.assertEqual(len({row[2] for row in views}), 42)
        for azimuth, elevation, learned, support in views:
            with self.subTest(azimuth=azimuth, elevation=elevation):
                angle = 0 if azimuth is None else (azimuth + 180) % 360 - 180
                result = node.apply(model, lora_strength=0, azimuth=angle, elevation=elevation, context=source)
                pipe, prompt, caption, output_model = result["result"]
                expected = f"{learned}, {support}"
                for side in ("left", "right"):
                    if f" {side}," in learned:
                        expected += f", from {side}"
                self.assertEqual(caption, expected)
                self.assertEqual(prompt, f"{caption}, {source.prompt}")
                self.assertEqual(pipe.characters[0].prompt, f"{source.characters[0].prompt}, {support}")
                self.assertEqual(pipe.text_regions, source.text_regions)
                self.assertIs(output_model, model)
        self.assertIn("facing left", node.apply(model, lora_strength=0, azimuth=-90)["result"][2])
        self.assertIn("facing right", node.apply(model, lora_strength=0, azimuth=90)["result"][2])
        self.assertEqual(node.apply(model, enabled=False, context=source)["result"], (source, source.prompt, "", model))

    def test_building_pipe_name_and_legacy_api_are_equivalent(self):
        node = camera.RSCameraControl()
        fields = node.INPUT_TYPES()['optional']
        self.assertEqual(fields['building_pipe'][0], fields['context'][0])
        self.assertEqual(node.RETURN_NAMES[0], 'building_pipe')
        source = SharedContext()
        for options in ({}, {'enabled': False}, {'strength': 0}):
            self.assertEqual(node.apply(building_pipe=source, **options),
                             node.apply(context=source, **options))
        self.assertIs(node.apply(building_pipe=source, enabled=False)['result'][0], source)
        with self.assertRaisesRegex(ValueError, '하나만'):
            node.apply(building_pipe=source, context=SharedContext())
        with self.assertRaises(TypeError):
            node.apply(unexpected_pipe=source)

    def test_rear_filter_follows_the_selected_training_view(self):
        node = camera.RSAtelierSphereCameraControl()
        source = SharedContext(
            prompt="glass greenhouse, (looking at viewer:1.3), red watering can",
            characters=(Caption("((blue_eyes:1.2), long hair:1.35), fang, black apron"),),
        )
        views = json.loads((Path(__file__).resolve().parents[1] / "atelier_camera_views.json").read_text())
        for azimuth, elevation, learned, support in views:
            with self.subTest(azimuth=azimuth, elevation=elevation):
                angle = 0 if azimuth is None else (azimuth + 180) % 360 - 180
                pipe, prompt, _, _ = node.apply(
                    object(), lora_strength=0, context=source, azimuth=angle, elevation=elevation,
                )["result"]
                scene = "glass greenhouse, red watering can" if "'s rear" in learned else source.prompt
                character = "(long hair:1.35), black apron" if "'s rear" in learned else source.characters[0].prompt
                side = next((f"from {side}, " for side in ("left", "right") if f" {side}," in learned), "")
                self.assertEqual(prompt, f"{learned}, {support}, {side}{scene}")
                self.assertEqual(pipe.characters[0], Caption(f"{character}, {support}"))
                self.assertEqual(pipe.negative_prompt, source.negative_prompt)
                self.assertEqual(pipe.text_regions, source.text_regions)

    def test_rear_filter_respects_scopes_and_bypass(self):
        node = camera.RSAtelierSphereCameraControl()
        source = SharedContext(prompt="studio, blue eyes", characters=(Caption("smile, brown hair"),))
        options = dict(lora_strength=0, context=source, azimuth=180)
        self.assertNotIn("filter_rear_face_tags", node.INPUT_TYPES()["optional"])
        filtered = node.apply(object(), **options)["result"][0]
        self.assertNotIn("blue eyes", filtered.prompt)
        self.assertNotIn("smile", filtered.characters[0].prompt)
        legacy = node.apply(object(), **options, filter_rear_face_tags=False)["result"][0]
        self.assertEqual(legacy, filtered)
        scene_only = node.apply(object(), **options, scope="scene_only")["result"][0]
        self.assertNotIn("blue eyes", scene_only.prompt)
        self.assertIs(scene_only.characters, source.characters)
        for switch in ({"enabled": False}, {"strength": 0}):
            bypassed = node.apply(object(), **options, **switch)["result"][0]
            self.assertIs(bypassed, source)

    def test_atelier_side_tag_matches_the_snapped_view(self):
        node = camera.RSAtelierSphereCameraControl()
        _, prompt, caption, _ = node.apply(
            object(), lora_strength=0, azimuth=-121.717474,
            base_prompt="from left, (from_right:1.3), alley, blue eyes",
        )["result"]
        self.assertTrue(caption.endswith(", from left"))
        self.assertEqual(prompt, f"{caption}, alley")
        for azimuth, elevation in ((5, 0), (179, 0), (-90, 90)):
            _, _, caption, _ = node.apply(
                object(), lora_strength=0, azimuth=azimuth, elevation=elevation,
            )["result"]
            self.assertNotIn("from left", caption)
            self.assertNotIn("from right", caption)

    def test_rear_filter_preserves_novelai_weights_and_other_tags(self):
        node = camera.RSAtelierSphereCameraControl()
        source = SharedContext(character_syntax="NovelAI", characters=(Caption(
            "1.123456::blue eyes, long hair, smile ::, open jacket, eye patch, a sign reading blue eyes"
        ),))
        pipe = node.apply(object(), context=source, azimuth=180, lora_strength=0)["result"][0]
        self.assertEqual(pipe.characters[0].prompt,
            "1.123456::long hair ::, open jacket, eye patch, a sign reading blue eyes, "
            "1.5::from behind::, 1.4::back view::, facing away")

    def test_rear_filter_handles_tags_only_and_keeps_literal_parentheses(self):
        node = camera.RSAtelierSphereCameraControl()
        source = SharedContext(prompt="(smile, blue eyes:1.4), (wink)",
                               characters=(Caption(r"artist:name, character \(series\), (fang)"),))
        pipe, prompt, caption, _ = node.apply(object(), context=source, azimuth=180,
                                             lora_strength=0)["result"]
        self.assertEqual(prompt, caption)
        self.assertEqual(pipe.characters[0].prompt,
                         r"artist:name, character \(series\), (from behind:1.5), (back view:1.4), facing away")

    def test_random_reproducible_and_respects_ranges(self):
        for mode, bounds in camera.RANDOM_RANGES.items():
            for seed in range(1000):
                view = camera.random_camera(mode, seed)
                self.assertEqual(view, camera.random_camera(mode, seed))
                for value, (low, high) in zip(view.values(), bounds):
                    self.assertTrue(low <= value < high)
                self.assertTrue(camera.camera_weights(**view))
            self.assertNotEqual(camera.random_camera(mode, 100), camera.random_camera(mode, 101))
        for seed in (-1, 2**32, 1.5, True, '4', float('nan')):
            with self.assertRaisesRegex(ValueError, '시드'):
                camera.random_camera('balanced', seed)

    def test_random_matches_manual_and_preserves_image_seed(self):
        node = camera.RSCameraControl()
        for syntax in ('ComfyUI', 'NovelAI'):
            source = SharedContext(syntax=syntax)
            for mode in ('balanced', 'full'):
                for seed in (0, 12345, 0xffffffff):
                    view = camera.random_camera(mode, seed)
                    manual = node.apply(context=source, **view)
                    randomized = node.apply(context=source, random_mode=mode, random_seed=seed)
                    self.assertEqual(manual, randomized)
                    self.assertEqual(randomized['result'][0].source_seed, source.source_seed)
                    self.assertEqual(randomized['ui']['camera_values'][0], view)
        for mode in ('balanced', 'full'):
            self.assertIs(node.apply(context=source, enabled=False, random_mode=mode)['result'][0], source)
            self.assertIs(node.apply(context=source, strength=0, random_mode=mode)['result'][0], source)
        self.assertEqual(node.apply(), node.apply(random_mode='off', random_seed=1234))
        with self.assertRaisesRegex(ValueError, '랜덤'):
            node.apply(random_mode='invalid')

    def test_continuous_weights_and_no_hidden_gain_at_knots(self):
        for field, knots in (("azimuth",[-180,-90,0,90,180]), ("elevation",[-90,-60,0,60,90]), ("distance",[0,.25,.5,.75,1])):
            low, high = {"azimuth":(-180,180), "elevation":(-90,90), "distance":(0,1)}[field]
            for point in knots:
                left=camera.camera_weights(**{field:max(low,point-1e-5)})
                right=camera.camera_weights(**{field:min(high,point+1e-5)})
                self.assertLess(max(abs(left.get(k,0)-right.get(k,0)) for k in left.keys()|right.keys()), .0001)
        self.assertEqual(camera.camera_weights(azimuth=-180), camera.camera_weights(azimuth=180))
        self.assertEqual(camera.camera_weights(elevation=90),camera.camera_weights(azimuth=90,elevation=90))

    def test_linear_strength_and_distance_conservation(self):
        for distance in [i/1000 for i in range(1001)]:
            weights=camera.camera_weights(distance=distance)
            self.assertAlmostEqual(sum(weights.get(t,0) for t in camera.DISTANCE_TAGS),1.2)
            self.assertTrue(all(math.isfinite(v) and v>=0 for v in weights.values()))
        low=camera.camera_weights(30,20,.4,10,.8)
        high=camera.camera_weights(30,20,.4,10,1.6)
        for tag in low: self.assertAlmostEqual(high[tag],low[tag]*2)

    def test_native_and_nai_context_are_immutable_and_keep_extras(self):
        for syntax in ("ComfyUI","NovelAI"):
            source=SharedContext(syntax=syntax)
            result=camera.RSCameraControl().apply(context=source,elevation=60)
            updated,prompt,caption=result['result']
            self.assertNotEqual(source.prompt,updated.prompt)
            self.assertTrue(prompt.startswith(source.prompt))
            for name in ('text_regions','negative_prompt','generation_json','local_record_json','model','source_seed','settings'):
                self.assertEqual(getattr(source,name),getattr(updated,name))
            for original, changed in zip(source.characters,updated.characters):
                self.assertTrue(changed.prompt.startswith(original.prompt+", "))
                for name in ('uc','x','y','lora_name'):
                    self.assertEqual(getattr(original,name),getattr(changed,name))
            self.assertIn('::from above::' if syntax=='NovelAI' else '(from above:',caption)
            self.assertNotIn('::' if syntax=='ComfyUI' else '(from',caption)

    def test_common_only_and_mixed_character_syntax(self):
        source=SharedContext(character_syntax="NovelAI")
        common=camera.RSCameraControl().apply(context=source,scope="scene_only")['result'][0]
        self.assertEqual(common.characters,source.characters)
        both=camera.RSCameraControl().apply(context=source)['result'][0]
        self.assertIn('(from front:',both.prompt)
        self.assertIn('::from front::',both.characters[0].prompt)
        self.assertEqual(source.characters[0].prompt,'brown hair')

    def test_no_scene_does_not_silently_replace_sampler_caption(self):
        pipe=SharedContext(prompt=None)
        with self.assertRaisesRegex(ValueError,'base_prompt'):
            camera.RSCameraControl().apply(context=pipe)
        output,prompt,_=camera.RSCameraControl().apply(context=pipe,base_prompt='new scene')['result']
        self.assertTrue(prompt.startswith('new scene'))
        self.assertIsNone(pipe.prompt)
        self.assertIs(camera.RSCameraControl().apply(context=pipe,enabled=False)['result'][0],pipe)
        self.assertIs(camera.RSCameraControl().apply(context=pipe,strength=0)['result'][0],pipe)

    def test_off_zero_and_string_only_paths(self):
        pipe=SharedContext()
        for settings in ({'enabled':False},{'strength':0}):
            out,caption,tags=camera.RSCameraControl().apply(context=pipe,**settings)['result']
            self.assertIs(out,pipe);self.assertEqual(caption,pipe.prompt);self.assertEqual(tags,'')
        out,prompt,tags=camera.RSCameraControl().apply(base_prompt='hello',weighting='plain')['result']
        self.assertIsInstance(out, camera.CameraBuildSeed);self.assertTrue(prompt.startswith('hello'));self.assertNotIn(':',tags)
        self.assertIn('::',camera.RSCameraControl().apply(prompt_syntax='NovelAI')['result'][2])

    def test_plain_axes_are_independent_across_eight_views_and_elevations(self):
        for distance in (0., .1, .25, .4, .5, .65, .75, .9, 1.):
            expected = None
            for angle in (-180, -135, -90, -45, 0, 45, 90, 135, 180):
                for elevation in (-90, -60, -25, 0, 25, 60, 90):
                    for roll in (0, 2, 45):
                        for syntax in ('ComfyUI', 'NovelAI'):
                            caption = camera.camera_caption(camera.camera_weights(angle, elevation, distance, roll), syntax, 'plain')
                            distance_tags = set(caption.split(', ')) & set(camera.DISTANCE_TAGS)
                            if expected is None:
                                expected = distance_tags
                            self.assertEqual(distance_tags, expected)
            self.assertTrue(expected)
        for angle, direction in ((0, 'from front'), (90, 'viewed from the right side'), (180, 'from behind')):
            caption = camera.camera_caption(camera.camera_weights(angle, 0, .65), weighting='plain')
            self.assertIn(direction, caption)
            self.assertIn('medium shot', caption)
            self.assertIn('full body', caption)
        self.assertEqual(camera.camera_caption(camera.camera_weights(strength=0), weighting='plain'), '')

    def test_plain_direction_is_independent_of_distance_and_roll(self):
        for angle in (-180, -135, -90, -45, 0, 45, 90, 135, 180):
            expected = None
            for distance in (0., .1, .25, .4, .65, .9, 1.):
                for roll in (0, 2, 45):
                    caption = camera.camera_caption(camera.camera_weights(angle, 0, distance, roll), weighting='plain')
                    tags = set(caption.split(', ')) - set(camera.DISTANCE_TAGS) - {'dutch angle'}
                    if expected is None:
                        expected = tags
                    self.assertEqual(tags, expected)
            self.assertTrue(expected)

    def test_bad_inputs_show_readable_errors(self):
        for field in ('azimuth','elevation','distance','roll','strength'):
            for value in (float('nan'),float('inf'),True,'oops'):
                with self.assertRaisesRegex(ValueError,'카메라'):
                    camera.camera_weights(**{field:value})
        with self.assertRaisesRegex(ValueError,'최종'):
            camera.RSCameraControl().apply(context=object())
        with self.assertRaisesRegex(ValueError,'문자열'):
            camera.RSCameraControl().apply(base_prompt=12)


if __name__=='__main__': unittest.main()
