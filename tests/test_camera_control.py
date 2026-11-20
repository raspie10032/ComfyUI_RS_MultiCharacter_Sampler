# SPDX-License-Identifier: GPL-3.0-only
"""The camera node is importable without ComfyUI or a GPU."""
from dataclasses import dataclass, field, replace
import importlib.util
import json
import math
import sys
import types
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

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
    def test_atelier_selects_adapter_from_input_model(self):
        from _rs_camera_unit import atelier_camera, moss_camera

        class Anima:
            pass

        class MOSSImage:
            pass

        node = camera.RSAtelierSphereCameraControl()
        output_model = object()
        node._loader = Mock()
        node._loader.load_lora_model_only.return_value = (output_model,)
        comfy = types.SimpleNamespace(model_base=types.SimpleNamespace(Anima=Anima, MOSSImage=MOSSImage))
        source = SharedContext()
        moss = types.SimpleNamespace(model=MOSSImage())
        anima = types.SimpleNamespace(model=Anima(), get_model_object=lambda _: types.SimpleNamespace(blocks=range(28)))
        token = Mock()
        other_token = object()
        view_id = atelier_camera.nearest_view_index(-110.905157, 30)

        with (patch.dict(sys.modules, {"comfy": comfy, "nodes": types.SimpleNamespace(LoraLoaderModelOnly=Mock())}),
              patch.object(moss_camera, "moss_lora", return_value=moss_camera.MOSS_LORA),
              patch.object(moss_camera, "moss_tokens", return_value={view_id: token}) as tokens,
              patch.object(token, "clone", return_value=other_token),
              patch.object(moss_camera, "install_moss_camera") as install_moss,
              patch.object(atelier_camera, "ensure_atelier_lora", return_value=atelier_camera.ATELIER_LORA) as ensure_anima):
            pipe, prompt, _, model = node.apply(moss, building_pipe=source, azimuth=-110.905157, elevation=30)["result"]
            self.assertTrue(prompt.startswith("from left, camera on the character's rear left, high camera angle, Rear three-quarter view"))
            self.assertTrue(pipe.characters[0].prompt.startswith("from left, "))
            self.assertEqual(pipe.negative_prompt, source.negative_prompt)
            self.assertEqual(pipe.text_regions, source.text_regions)
            self.assertIs(model, output_model)
            node._loader.load_lora_model_only.assert_called_once_with(moss, moss_camera.MOSS_LORA, 1.)
            install_moss.assert_called_once_with(output_model, other_token, "scene_and_characters")
            ensure_anima.assert_not_called()

            self.assertIs(node.apply(moss, lora_strength=0, azimuth=-90)["result"][3], moss)
            tokens.assert_called_once_with()
            node.apply(anima, azimuth=-90)
            node._loader.load_lora_model_only.assert_called_with(anima, atelier_camera.ATELIER_LORA, 1.)
            ensure_anima.assert_called_once_with()
            install_moss.assert_called_once()

    def test_merged_loader_and_camera_select_the_same_asset(self):
        from _rs_camera_unit import atelier_camera

        node = camera.RSAnimaCameraMultiLoRA()
        self.assertNotIn("lora_name", node.INPUT_TYPES()["required"])
        self.assertEqual(node.apply(None, 0), (None,))
        orbit = camera.RSAtelierSphereCameraControl()
        self.assertEqual(orbit.INPUT_TYPES()["optional"]["anima_lora"][0][0], "camera_v3")
        loader = Mock()
        node._loader = orbit._loader = loader
        model = object()
        with (patch.dict(sys.modules, {"nodes": types.SimpleNamespace(LoraLoaderModelOnly=Mock())}),
              patch.object(camera, "require_anima_2b") as require,
              patch.object(atelier_camera, "ensure_merged_lora", return_value=atelier_camera.MERGED_LORA) as ensure):
            node.apply(model, .8)
            loader.load_lora_model_only.assert_called_once_with(model, atelier_camera.MERGED_LORA, .8)
            loader.load_lora_model_only.return_value = (model,)
            orbit.apply(model, anima_lora="camera_multi_merge", azimuth=-90)
            loader.load_lora_model_only.assert_called_with(model, atelier_camera.MERGED_LORA, 1.)
            self.assertEqual(ensure.call_count, 2)
            self.assertEqual(require.call_count, 2)

    def test_atelier_selects_all_42_training_views_and_shares_composition(self):
        node = camera.RSAtelierSphereCameraControl()
        model = object()
        source = SharedContext()
        views = json.loads((Path(__file__).resolve().parents[1] / "web" / "atelier_camera_views.json").read_text())
        self.assertEqual(len({row[2] for row in views}), 42)
        for azimuth, elevation, learned, support in views:
            with self.subTest(azimuth=azimuth, elevation=elevation):
                angle = 0 if azimuth is None else (azimuth + 180) % 360 - 180
                result = node.apply(model, lora_strength=0, azimuth=angle, elevation=elevation,
                                    context=source, visible_details=False)
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
        views = json.loads((Path(__file__).resolve().parents[1] / "web" / "atelier_camera_views.json").read_text())
        for azimuth, elevation, learned, support in views:
            with self.subTest(azimuth=azimuth, elevation=elevation):
                angle = 0 if azimuth is None else (azimuth + 180) % 360 - 180
                pipe, prompt, _, _ = node.apply(
                    object(), lora_strength=0, context=source, azimuth=angle, elevation=elevation,
                    visible_details=False,
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

    def test_conflict_filter_across_all_training_directions(self):
        node = camera.RSAtelierSphereCameraControl()
        moss_node = camera.RSCameraControl()
        horizontal = {
            "front": "front view", "front right": "right front three-quarter view",
            "right": "right profile", "rear right": "right rear three-quarter view",
            "rear": "back view", "rear left": "left rear three-quarter view",
            "left": "left profile", "front left": "left front three-quarter view",
        }
        vertical = {"level": "eye-level shot", "high": "high angle shot", "low": "low angle shot"}
        poles = {90.: "top-down view", -90.: "worm’s-eye view"}
        subject = "looking left, right hand raised, side ponytail, backless dress, high heels, over-the-shoulder shot"
        original = ", ".join((*horizontal.values(), *vertical.values(), *poles.values(), subject))
        source = SharedContext(prompt=original, characters=(Caption(original),))
        views = json.loads((Path(__file__).resolve().parents[1] / "web" / "atelier_camera_views.json").read_text())
        for azimuth, elevation, learned, support in views:
            with self.subTest(view=learned):
                angle = 0 if azimuth is None else (azimuth + 180) % 360 - 180
                if azimuth is None:
                    expected = f"{vertical['high' if elevation > 0 else 'low']}, {poles[elevation]}, {subject}"
                else:
                    direction = learned.split("'s ", 1)[1].split(",", 1)[0]
                    height = "level" if elevation == 0 else "high" if elevation > 0 else "low"
                    expected = f"{horizontal[direction]}, {vertical[height]}, {subject}"
                pipe, prompt, caption, _ = node.apply(
                    object(), context=source, azimuth=angle, elevation=elevation, lora_strength=0,
                    visible_details=False,
                )["result"]
                self.assertEqual(prompt, f"{caption}, {expected}")
                self.assertEqual(pipe.characters[0].prompt, f"{expected}, {support}")
                pipe, prompt, caption = moss_node.apply(
                    atelier=True, moss=True, context=source, azimuth=angle, elevation=elevation,
                    visible_details=False,
                )["result"]
                separator = ", " if azimuth is None else " "
                self.assertEqual(prompt, f"{caption}{separator}{expected}")
                self.assertEqual(pipe.characters[0].prompt, prompt)

    def test_conflicts_use_snapped_view_and_preserve_nonpositive_weights(self):
        node = camera.RSAtelierSphereCameraControl()
        source = SharedContext(
            prompt="((front view:1.3), LEFT_PROFILE, green scarf:1.25), (from right:-1), from left",
            character_syntax="NovelAI",
            characters=(Caption("1.4::front view, green scarf ::, -1::from right ::, from left"),),
        )
        pipe, prompt, caption, _ = node.apply(
            object(), context=source, azimuth=-88, elevation=2, lora_strength=0, visible_details=False,
        )["result"]
        self.assertEqual(prompt, f"{caption}, (LEFT_PROFILE, green scarf:1.25), (from right:-1)")
        self.assertTrue(pipe.characters[0].prompt.startswith("1.4::green scarf ::, -1.0::from right ::, from left, "))
        _, prompt, caption, _ = node.apply(
            object(), base_prompt="front view, from left, from below, facing left, looking up",
            azimuth=-88, elevation=89, lora_strength=0, visible_details=False,
        )["result"]
        self.assertEqual(prompt, f"{caption}, facing left, looking up")

    def test_moss_removes_standalone_view_sentences(self):
        source = SharedContext(
            prompt="A worker opens a door. Straight-on rear view, with the back of the torso visible. "
                   "The subject faces straight away from the camera.  She looks left.",
            characters=(Caption("Low angle. A green coat with a front zipper."),),
        )
        pipe, prompt, caption = camera.RSCameraControl().apply(
            atelier=True, moss=True, context=source,
        )["result"]
        self.assertEqual(prompt, f"{caption} A worker opens a door. She looks left.")
        self.assertEqual(pipe.characters[0].prompt, f"{caption} A green coat with a front zipper.")
        quoted = 'A sign says “Read this. Rear view. End of sign.”'
        _, prompt, caption = camera.RSCameraControl().apply(
            atelier=True, moss=True, base_prompt=quoted,
        )["result"]
        self.assertEqual(prompt, f"{caption} {quoted}")

    def test_moss_filters_unquoted_sentences_and_preserves_quoted_text(self):
        base = 'A sign reads "Welcome, front view, friend".'
        source = SharedContext(
            prompt=f"{base} Straight-on front view, with the front of the torso visible. Blue eyes!",
            characters=(Caption("“Welcome, front view, friend”, front view, a black coat"),),
        )
        for syntax in ("ComfyUI", "NovelAI"):
            with self.subTest(syntax=syntax):
                context = replace(source, syntax=syntax)
                pipe, prompt, caption = camera.RSCameraControl().apply(
                    atelier=True, moss=True, context=context, azimuth=180,
                )["result"]
                self.assertEqual(prompt, f"{caption} {base}")
                self.assertEqual(pipe.characters[0].prompt, f"{caption} “Welcome, front view, friend”, a black coat")

    def test_generated_details_for_the_opposite_view_are_filtered(self):
        node = camera.RSCameraControl()
        source = SharedContext(
            prompt="headshot, (face visible:1.3), (facial profile:-1), black coat",
            characters=(Caption("headshot, front of torso, from front, black coat with a front zipper"),),
        )
        pipe, prompt, _ = node.apply(atelier=True, context=source, azimuth=180)["result"]
        self.assertIn("back of head", prompt)
        self.assertIn("(facial profile:-1)", prompt)
        self.assertNotIn("face visible", prompt)
        self.assertNotIn("front of torso", pipe.characters[0].prompt)
        self.assertIn("black coat with a front zipper", pipe.characters[0].prompt)
        _, prompt, _ = node.apply(
            atelier=True, moss=True, base_prompt="The upper back is in view. A black coat.",
        )["result"]
        self.assertNotIn("upper back", prompt)
        self.assertIn("A black coat.", prompt)

    def test_moss_filters_earlier_camera_captions_in_a_finalized_pipe(self):
        node = camera.RSCameraControl()
        source = SharedContext(prompt="A worker opens a door.", characters=(Caption("A black coat."),))
        for distance in (.25, .5):
            with self.subTest(distance=distance):
                rear, _, _ = node.apply(
                    atelier=True, moss=True, azimuth=180, distance=distance, context=source,
                )["result"]
                front, prompt, _ = node.apply(atelier=True, moss=True, context=rear)["result"]
                for caption in (prompt, front.characters[0].prompt):
                    self.assertNotIn("rear view", caption)
                    self.assertNotIn("back of the torso", caption)
                    self.assertNotIn("back of the head", caption)
                self.assertIn(source.prompt, prompt)
                self.assertIn(source.characters[0].prompt, front.characters[0].prompt)

    def test_atelier_side_tag_matches_the_snapped_view(self):
        node = camera.RSAtelierSphereCameraControl()
        _, prompt, caption, _ = node.apply(
            object(), lora_strength=0, azimuth=-121.717474, visible_details=False,
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
        pipe = node.apply(object(), context=source, azimuth=180, lora_strength=0, visible_details=False)["result"][0]
        self.assertEqual(pipe.characters[0].prompt,
            "1.123456::long hair ::, open jacket, eye patch, a sign reading blue eyes, "
            "1.5::from behind::, 1.4::back view::, facing away")

    def test_rear_filter_handles_tags_only_and_keeps_literal_parentheses(self):
        node = camera.RSAtelierSphereCameraControl()
        source = SharedContext(prompt="(smile, blue eyes:1.4), (wink)",
                               characters=(Caption(r"artist:name, character \(series\), (fang)"),))
        pipe, prompt, caption, _ = node.apply(object(), context=source, azimuth=180,
                                             lora_strength=0, visible_details=False)["result"]
        self.assertEqual(prompt, caption)
        self.assertEqual(pipe.characters[0].prompt,
                         r"artist:name, character \(series\), (from behind:1.5), (back view:1.4), facing away")

    def test_visible_details_matrix_across_trained_views_and_framing(self):
        node = camera.RSCameraControl()
        torso = {
            "front": ("front of torso", "front of the torso"),
            "front quarter": ("front of torso", "front and one side of the torso"),
            "side": ("side of torso", "side of the torso"),
            "rear quarter": ("upper back", "back and one side of the torso"),
            "rear": ("upper back", "back of the torso"),
        }
        head = {
            "front": ("face visible", "The face is in view."),
            "front quarter": ("face visible", "The face is in view."),
            "side": ("facial profile", "The outline of the face is in view."),
            "rear quarter": ("back of head", "The back of the head is in view."),
            "rear": ("back of head", "The back of the head is in view."),
        }
        close, body, wide, special = "head", "body", "wide", "special"
        framings = [
            (0., "", close), (.25, "", close), (.375, "", close), (.5, "", body),
            (.75, "", body), (1., "", wide), (.5, "headshot", close),
            (.5, "medium_shot", body), (.5, "wide shot", wide), (.5, "feet focus", special),
        ]
        views = json.loads((Path(__file__).resolve().parents[1] / "web" / "atelier_camera_views.json").read_text())
        self.assertEqual(len(views), 42)
        for azimuth, elevation, learned, _ in views:
            angle = 0 if azimuth is None else (azimuth + 180) % 360 - 180
            bearing = ("side" if "front" not in learned and "rear" not in learned else
                       "front" if "front" in learned else "rear")
            if bearing != "side" and any(f" {side}," in learned for side in ("left", "right")):
                bearing += " quarter"
            for distance, hint, crop in framings:
                for moss in (False, True):
                    with self.subTest(view=learned, distance=distance, hint=hint, moss=moss):
                        scene = ", ".join(filter(None, (hint, "greenhouse")))
                        source = SharedContext(prompt=scene, characters=(Caption("black jacket"),))
                        pipe, prompt, caption = node.apply(
                            context=source, azimuth=angle, elevation=elevation, distance=distance,
                            atelier=True, moss=moss,
                        )["result"]
                        if crop == special or (elevation == -90 and crop == close):
                            expected = ""
                        elif elevation == -90:
                            expected = "The body outline is foreshortened." if moss else "foreshortened body outline"
                        elif elevation == 90:
                            expected = ("The top of the head is in view." if moss else "top of head")
                        else:
                            expected = (head if crop == close else torso)[bearing][moss]
                        for text in (caption, pipe.characters[0].prompt):
                            if expected:
                                self.assertIn(expected, text)
                            if crop in (close, special):
                                self.assertNotIn("torso", text)
                                self.assertNotIn("upper back", text)
                            self.assertNotIn("bare back", text)
                            self.assertNotIn("soles", text)
                        self.assertIn(scene, prompt)
                        self.assertIn("black jacket", pipe.characters[0].prompt)
                        self.assertEqual(pipe.characters[0].uc, source.characters[0].uc)

    def test_rear_details_are_scope_aware_and_keep_user_clothing(self):
        node = camera.RSAtelierSphereCameraControl()
        source = SharedContext(
            prompt="medium shot, front view, studio",
            character_syntax="NovelAI",
            characters=(
                Caption("headshot, 1.4::blue eyes, braid"),
                Caption("1.3::UPPER_BACK, black jacket with a back zipper ::, -1::near shoulder ::"),
                Caption("feet focus, red boots"),
            ),
        )
        options = dict(context=source, lora_strength=0, azimuth=-121.717474)
        pipe, prompt, caption, _ = node.apply(object(), **options)["result"]
        self.assertIn("upper back, near shoulder visible", caption)
        self.assertNotIn("front view", prompt)
        self.assertIn("back of head, side of head, headshot", pipe.characters[0].prompt)
        self.assertNotIn("upper back", pipe.characters[0].prompt)
        self.assertNotIn("blue eyes", pipe.characters[0].prompt)
        self.assertIn("UPPER_BACK, black jacket with a back zipper", pipe.characters[1].prompt)
        self.assertNotIn("upper back", pipe.characters[1].prompt)
        self.assertNotIn("near shoulder visible", pipe.characters[1].prompt)
        self.assertNotIn("upper back", pipe.characters[2].prompt)

        scene_only = node.apply(object(), **options, scope="scene_only")["result"][0]
        self.assertIs(scene_only.characters, source.characters)
        off = node.apply(object(), **options, visible_details=False)["result"][0]
        self.assertNotIn("upper back", off.prompt)
        self.assertNotIn("front view", off.prompt)
        self.assertNotIn("blue eyes", off.characters[0].prompt)

    def test_visible_details_respect_weight_groups_and_moss_prose_framing(self):
        node = camera.RSCameraControl()
        source = SharedContext(
            prompt="studio",
            characters=(Caption("((upper_back, black jacket):1.2), (backs of shoulders:-1)"),),
        )
        pipe, _, _ = node.apply(atelier=True, context=source, azimuth=180)["result"]
        self.assertTrue(pipe.characters[0].prompt.startswith(source.characters[0].prompt + ", "))
        self.assertNotIn("upper back", pipe.characters[0].prompt)
        self.assertEqual(pipe.characters[0].prompt.count("backs of shoulders"), 1)

        source = SharedContext(prompt="A child wearing a hat. A close-up of their head.",
                               characters=(Caption("The back of the head is visible. A blue hat."),))
        pipe, prompt, caption = node.apply(atelier=True, moss=True, context=source, azimuth=180)["result"]
        self.assertIn("The back of the head is in view.", caption)
        self.assertNotIn("torso", prompt)
        self.assertNotIn("The back of the head is in view.", pipe.characters[0].prompt)
        self.assertIn("The back of the head is visible. A blue hat.", pipe.characters[0].prompt)

        scene = 'A sign reads “Wait, headshot, please.” A medium shot.'
        _, prompt, caption = node.apply(atelier=True, moss=True, base_prompt=scene, azimuth=180)["result"]
        self.assertIn("back of the torso visible", caption)
        self.assertIn("The backs of the shoulders are in view.", caption)
        self.assertIn(scene, prompt)

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
