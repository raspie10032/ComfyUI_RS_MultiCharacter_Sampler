import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import numpy as np
from PIL import Image
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = Path(__file__).resolve().parents[1].name
d = importlib.import_module(pkg + ".detailer")
c = importlib.import_module(pkg + ".characters")
b = importlib.import_module(pkg + ".detector_bundle")
m = importlib.import_module(pkg + ".metadata")
r = importlib.import_module(pkg + ".mask_repair")
progress = importlib.import_module(pkg + ".tagger_progress")


@contextmanager
def temporary_modules(mapping):
    # Restore only the mocked names, retaining modules lazily imported by torch.
    missing = object()
    previous = {key:sys.modules.get(key, missing) for key in mapping}
    sys.modules.update(mapping)
    try:
        yield
    finally:
        for key,value in previous.items():
            if value is missing: sys.modules.pop(key,None)
            else: sys.modules[key] = value


class FakeDetector:
    def __init__(self, masks=None):
        self.masks = masks
        self.calls = 0

    def detect(self, image, *args, **kwargs):
        self.calls += 1
        masks = self.masks
        if masks is None:
            masks = np.zeros((2, 48, 64), np.float32)
            masks[0, 8:25, 8:28] = 1
            masks[1, 8:25, 27:48] = 1
        from types import SimpleNamespace
        regions = [SimpleNamespace(bbox=r.bounds(mask), crop_region=(0, 0, 64, 48), cropped_mask=mask) for mask in masks]
        return (48, 64), regions


class FakeTagger:
    def __init__(self, ambiguous=False):
        self.ambiguous = ambiguous
        self.calls = 0

    def score(self, images):
        self.calls += 1
        if self.ambiguous:
            return [{"black_hair": .8, "blonde_hair": .8} for _ in images]
        return [{"black_hair": .9, "blonde_hair": .1}, {"blonde_hair": .95, "black_hair": .1}][:len(images)]


class DetailerTests(unittest.TestCase):
    def setUp(self):
        self.pipe = c.CharacterPipe((c.Character("1girl, (black hair:1.2)", "hat"), c.Character("1girl, blonde hair", "glasses")), "cafe", "bad anatomy")
        self.image = torch.rand(1, 48, 64, 3)
        self.host = NS(KSampler=NS(SAMPLERS=["euler_ancestral"], SCHEDULERS=["sgm_uniform"]))
        self.host_patch = temporary_modules({"comfy.samplers": self.host})
        self.host_patch.__enter__()
        self.sample_calls = []

    def tearDown(self):
        self.host_patch.__exit__(None,None,None)

    def run_detail(self, **changes):
        options = dict(image=self.image, model=object(), clip=object(), vae=object(), character_pipe=self.pipe,
                       detectors=b.DetectionBundle(FakeDetector()), tagger=FakeTagger(), autosave=False, seed=2**64-1)
        options.update(changes)
        def sample(crop, mask, **kw):
            self.sample_calls.append((crop.clone(), mask.clone(), kw))
            return torch.zeros_like(crop), (768, 768)
        with patch.object(d, "_sample_crop", side_effect=sample):
            return d.RSMultiCharacterDetailer().detail(**options)

    def test_original_prompts_seed_wrap_frozen_crops_disjoint_edit_and_outside_pixels(self):
        result = self.run_detail()
        out, mask, pipe, report = result["result"]
        self.assertEqual(json.loads(report)["edited"], 2)
        self.assertEqual(self.sample_calls[0][2]["positive"], "cafe, 1girl, (black hair:1.2)")
        self.assertEqual(self.sample_calls[1][2]["negative"], "bad anatomy, glasses")
        self.assertEqual([x[2]["seed"] for x in self.sample_calls], [2**64-1, 0])
        coverage = torch.zeros(48,64)
        for (crop, mask_part, _), region in zip(self.sample_calls,json.loads(report)["regions"]):
            x1,y1,x2,y2 = region["crop"]
            torch.testing.assert_close(crop, self.image[:,y1:y2,x1:x2])
            coverage[y1:y2,x1:x2] += mask_part
        self.assertLessEqual(coverage.max(),1)
        self.assertTrue(torch.equal(out[mask == 0], self.image[mask == 0]))
        self.assertTrue((out[mask > 0] != self.image[mask > 0]).any())
        self.assertEqual(pipe.characters, self.pipe.characters)
        self.assertIsNone(self.pipe.generation_json)

    def test_ambiguous_regions_retry_then_preserve_source(self):
        tagger = FakeTagger(True)
        out, mask, _, report = self.run_detail(tagger=tagger)["result"]
        self.assertTrue(torch.equal(out, self.image))
        self.assertEqual(mask.sum(), 0)
        self.assertEqual(tagger.calls, 2)
        self.assertEqual(self.sample_calls, [])
        self.assertEqual(json.loads(report)["status"], "no_confident_matches")

    def test_limit_and_no_detections_are_explicit(self):
        result = self.run_detail(max_regions=1)
        report = json.loads(result["result"][3])
        self.assertEqual(report["edited"], 1)
        self.assertEqual(report["regions"][1]["reason"], "max_regions")
        result = self.run_detail(detectors=b.DetectionBundle(FakeDetector([])))
        self.assertEqual(json.loads(result["result"][3])["status"], "no_detections")

    def test_single_character_needs_no_tagger(self):
        result = self.run_detail(character_pipe=c.CharacterPipe((c.Character("person"),)), tagger=None)
        self.assertEqual(json.loads(result["result"][3])["edited"], 2)

    def test_invalid_inputs_fail_before_detection_or_sampling(self):
        for change in ({"tagger":None}, {"detectors":b.DetectionBundle()}, {"denoise":0}, {"denoise":float("nan")},
                       {"steps":True}, {"seed":-1}, {"max_regions":65}, {"fill_holes":"false"},
                       {"image":self.image.repeat(2,1,1,1)}, {"sampler_name":"missing"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_detail(**change)
        self.assertEqual(self.sample_calls, [])

    def test_nonfinite_mask_rejected(self):
        mask = np.ones((1,48,64), np.float32)
        mask[0,5,5] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            self.run_detail(detectors=b.DetectionBundle(FakeDetector(mask)))

    def test_segm_precedence_off_and_no_unused_model_download(self):
        loaded = []
        class Provider:
            def doit(self, name):
                loaded.append(name)
                return "bbox", "segm"
        with patch.object(b, "available_models", return_value=([b.DEFAULT_SEGM], [])), \
             patch.object(b, "provider", return_value=Provider), patch.object(b, "ensure_detection_model") as download:
            bundle, = b.RSMultiCharacterDetectionLoader().load(face_bbox_model="invalid-unused", sam_model="invalid-unused")
            self.assertEqual(bundle, b.DetectionBundle("segm"))
            self.assertEqual(loaded, [b.DEFAULT_SEGM])
            download.assert_called_once()
            download.reset_mock()
            bundle, = b.RSMultiCharacterDetectionLoader().load(face_segm_model="OFF")
            self.assertEqual(bundle, b.DetectionBundle())
            download.assert_not_called()

    def test_repair_fills_small_eye_hole_and_retains_disjoint_ownership(self):
        masks = np.zeros((2,100,130),bool)
        masks[0,5:95,5:85] = True
        masks[0,40:44,40:44] = False
        masks[1,5:95,75:125] = True
        _, fixed, reports = r.plan_masks(masks, dilation=8)
        self.assertTrue(fixed[0,40:44,40:44].all())
        self.assertFalse((fixed[0] & fixed[1]).any())
        self.assertGreater(reports[0]["repair_added_pixels"],0)

    def test_nai_syntax_converted_only_at_encoding_boundary(self):
        original = c.CharacterPipe((c.Character("1girl, 1.2::black hair::", "hat"),), "1.1::cafe::", "bad", "NovelAI")
        result = self.run_detail(character_pipe=original, tagger=None)
        self.assertIn("(black hair:1.2)", self.sample_calls[0][2]["positive"])
        self.assertEqual(result["result"][2].characters, original.characters)

    def test_detail_metadata_round_trip_keeps_origin_and_appends_history(self):
        settings = {"seed":55, "steps":30, "cfg":4., "width":64, "height":48, "sampler_name":"euler_ancestral", "scheduler":"sgm_uniform"}
        original = m.build_record(self.pipe, settings, {}, [], {"spatial_slots":2})
        origin_pipe = m.pipe_from_record(original)
        result = self.run_detail(character_pipe=origin_pipe)
        enriched = result["result"][2]
        for _ in range(2):
            record = d.detail_record(enriched,64,48,{"seed":9}, {}, {})
            with tempfile.TemporaryDirectory() as folder:
                for fmt in m.FORMATS:
                    path = m.save_image(Image.new("RGB",(64,48)),Path(folder)/"output",record,fmt)
                    with Image.open(path) as image:
                        restored = m.read_record(image)
                        self.assertNotIn("workflow", image.info)
                        self.assertEqual(restored["seed"],55)
                        self.assertEqual(restored["rs_multicharacter"]["settings"],settings)
                        enriched = m.pipe_from_record(restored)
        self.assertEqual(len(json.loads(enriched.generation_json)["detail_history"]),3)

    def test_detail_metadata_keeps_current_pose_and_interaction_from_direct_pipe(self):
        from dataclasses import replace
        from importlib import import_module
        masks = import_module(pkg + '.region_mask')
        region = masks.prepare_mask(torch.ones(48, 64), margin=0)
        character = replace(self.pipe.characters[0], region_mask=region,
                            body_parts=(('head', region),), body_part_strength=.2)
        interaction = json.dumps(dict(preset='delay6', delay_steps=6, decrement=.2))
        direct = replace(self.pipe, characters=(character,), interaction_json=interaction)
        # The returned pipe must work for another sampler/detail pass before saving.
        detailed = self.run_detail(character_pipe=direct)['result'][2]
        self.assertEqual(detailed.characters, direct.characters)
        self.assertEqual(detailed.interaction_json, interaction)
        stale = m.build_record(self.pipe, {'seed': 55, 'steps': 30, 'cfg': 4.,
            'width': 64, 'height': 48, 'sampler_name': 'euler_ancestral',
            'scheduler': 'sgm_uniform'}, {}, [], {'spatial_slots': 2})['rs_multicharacter']
        stale.update(body_parts=[[], []], body_part_strengths=[0., 0.],
                     interaction=dict(preset='baseline', delay_steps=6, decrement=.2))
        for source in (direct, replace(direct, generation_json=json.dumps(stale))):
            record = d.detail_record(source, 64, 48, {'seed': 9}, {}, {})
            with tempfile.TemporaryDirectory() as folder:
                for fmt in m.FORMATS:
                    path = m.save_image(Image.new('RGB', (64,48)), Path(folder)/'detail', record, fmt)
                    with Image.open(path) as image:
                        restored = m.pipe_from_record(m.read_record(image))
                    self.assertEqual(restored.characters, source.characters)
                    self.assertEqual(json.loads(restored.interaction_json), json.loads(interaction))
            self.assertEqual(len(record['rs_multicharacter']['detail_history']), 1)

        cleared = replace(direct, characters=(self.pipe.characters[0],), interaction_json=None,
                          generation_json=json.dumps(stale))
        restored = m.pipe_from_record(d.detail_record(cleared, 64, 48, {'seed': 9}, {}, {}))
        self.assertEqual(restored.characters, cleared.characters)
        self.assertIsNone(restored.interaction_json)

    def test_crop_sampler_supports_2d_and_anima_single_frame_latents(self):
        for video in (False,True):
            class VAE:
                def spacial_compression_encode(self): return 8
                def encode(self, pixels):
                    self.pixels = pixels
                    return torch.zeros((1,16,1,16,16) if video else (1,4,16,16))
                def decode(self, latent):
                    return self.pixels[:,None] if video else self.pixels
            observed = []
            def sample(*args, **kw):
                observed.append((args[8],kw))
                return (args[8],)
            clip = NS(tokenize=lambda t:t, encode_from_tokens_scheduled=lambda t:t)
            with temporary_modules({"nodes":NS(common_ksampler=sample)}):
                out, size = d._sample_crop(self.image, torch.ones(48,64), model=None, clip=clip, vae=VAE(),
                    positive="face", negative="bad", seed=1,steps=20,cfg=4.,sampler_name="euler_ancestral",
                    scheduler="sgm_uniform",denoise=.25,guide_size=128,max_size=256)
            self.assertEqual(out.shape,self.image.shape)
            self.assertEqual(observed[0][0]["samples"].ndim,5 if video else 4)
            self.assertEqual(observed[0][0]["noise_mask"].ndim,3)
            self.assertEqual(observed[0][1]["denoise"],.25)

    def test_matching_recognizes_literal_hair_phrases_without_rewriting_prompts(self):
        matching=importlib.import_module(pkg + ".detailer_matching")
        chars=[c.Character("long blonde hair, white blouse"),c.Character("short black hair, red jacket")]
        match=matching.match_characters({"black_hair":.95,"blonde_hair":.01,"red_eyes":.1},chars)
        self.assertEqual(match.character_index,1)
        self.assertNotIn("black hair",matching.prompt_tags("without black hair",{"black hair":.9}))
        self.assertEqual(chars[1].prompt,"short black hair, red jacket")

    def test_download_progress_is_separate_and_preserves_byte_counts(self):
        events=[]
        reporter=progress.TaggerProgress()
        reporter.report=lambda text,fraction=0,**kw: events.append((text,fraction))
        bar=reporter.download_bar("weights.safetensors")(total=1024*1024)
        bar.update(512*1024)
        self.assertIn("50%",events[-1][0])
        self.assertEqual(events[-1][1],.5)
        bar.close()


if __name__ == "__main__": unittest.main()
