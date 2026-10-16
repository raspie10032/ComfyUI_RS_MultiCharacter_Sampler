import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
pkg = importlib.import_module(Path(__file__).resolve().parents[1].name)
c = importlib.import_module(pkg.__name__ + ".characters")
m = importlib.import_module(pkg.__name__ + ".metadata")
n = importlib.import_module(pkg.__name__ + ".nodes")
layout = importlib.import_module(pkg.__name__ + ".layout")


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.pipe = c.CharacterPipe((c.Character("1girl, 금발", "", .8, .2), c.Character("1girl, 黒髪", "", .2, .8)), "カフェ, 두 명", "bad anatomy")
        self.settings = {**n.DEFAULTS, "seed": 2**60 + 12345}
        self.record = m.build_record(self.pipe, self.settings, {"loaders": [], "unresolved": []}, [[.8,.2],[.2,.8]], {"spatial_slots":2})

    def test_only_three_independent_nodes(self):
        self.assertEqual(len(pkg.NODE_CLASS_MAPPINGS), 3)
        self.assertFalse(any("NAI_API" in key for key in sys.modules))
        self.assertEqual(len(c.RSMultiCharacterPrompts.INPUT_TYPES()["required"]), 51)

    def test_hidden_disabled_empty_slots_never_enter_pipe(self):
        values = {f"character{i}": f"person {i}" for i in range(1, 11)}
        values["character2_enable"] = False
        values["character3"] = " "
        actual, = c.RSMultiCharacterPrompts().build(3, **values)
        self.assertEqual([v.prompt for v in actual.characters], ["person 1"])

    def test_count_and_empty_pipe_rejected(self):
        for count in (0, 11, True):
            with self.assertRaises(ValueError):
                c.RSMultiCharacterPrompts().build(count, character1="girl")
        with self.assertRaises(ValueError):
            c.RSMultiCharacterPrompts().build(3)

    def test_xy_and_duplicate_fallback_preserved(self):
        centers, changed = layout.effective_centers(self.pipe.characters)
        self.assertEqual(centers, ((.8,.2),(.2,.8)))
        self.assertEqual(changed, [])
        centers, _ = layout.effective_centers([c.Character("girl")]*5)
        self.assertEqual(centers, tuple(((i+.5)/5,.5) for i in range(5)))
        masks = layout.region_masks(centers,1536,768,.04)
        torch.testing.assert_close(masks.sum(0), torch.ones_like(masks[0]))

    def test_coordinates_reject_invalid_values(self):
        for value in (float("nan"),float("inf"),-.01,1.01,True,"0.5"):
            with self.assertRaises(ValueError):
                c.Character("girl", x=value)

    def test_png_and_both_webp_round_trip(self):
        pixels = np.random.default_rng(25).integers(0,256,(32,48,3),dtype=np.uint8)
        with tempfile.TemporaryDirectory() as folder:
            for fmt in m.FORMATS:
                path = m.save_image(Image.fromarray(pixels),Path(folder)/fmt,self.record,fmt)
                with Image.open(path) as image:
                    restored = m.read_record(image)
                    self.assertEqual(restored,self.record)
                    pipe = m.pipe_from_record(restored)
                    self.assertEqual(pipe.characters,self.pipe.characters)
                    self.assertEqual(pipe.prompt,self.pipe.prompt)
                    self.assertEqual(json.loads(pipe.generation_json)["settings"]["seed"],self.settings["seed"])
                    self.assertNotIn("workflow",image.info)
                    self.assertNotIn("prompt",image.info)
                    if fmt != "WebP lossy":
                        np.testing.assert_array_equal(np.array(image),pixels)

    def test_nai_shape_preserves_negatives_without_silently_generating(self):
        pipe = c.CharacterPipe((c.Character("girl", "blue eyes",.25,.6),), "common", "negative", "NovelAI")
        record = m.captions(pipe)
        restored = m.pipe_from_record(record)
        self.assertEqual(restored.characters,pipe.characters)
        self.assertEqual(restored.syntax,"NovelAI")
        self.assertIsNone(restored.generation_json)

    def test_malformed_metadata_rejected(self):
        for record in ({}, {"v4_prompt":None}):
            with self.assertRaises(ValueError):
                m.pipe_from_record(record)
        for field in ("version","engine"):
            record = copy.deepcopy(self.record)
            record["rs_multicharacter"][field] = "unknown"
            with self.assertRaises(ValueError):
                m.pipe_from_record(record)
        record = copy.deepcopy(self.record)
        record["v4_prompt"]["caption"]["char_captions"][0]["centers"].append({"x":.4,"y":.4})
        with self.assertRaises(ValueError):
            m.pipe_from_record(record)

    def test_no_metadata_reports_error(self):
        with self.assertRaisesRegex(ValueError,"No character metadata"):
            m.read_record(Image.new("RGB",(8,8)))

    def test_metadata_cannot_inject_nan_or_non_object(self):
        for text in ('{"seed":NaN}', '[]', 'null', '"test"'):
            with self.assertRaises(ValueError):
                m.object_json(text)

    def test_restored_settings_validated_before_sampling(self):
        n.validate_settings(self.settings)
        for key,value in (("seed",-1),("steps",3),("width",1153),("cfg",float("inf")),("sampler_name","unknown"),("boundary_hold_steps",False)):
            with self.assertRaises(ValueError):
                n.validate_settings({**self.settings,key:value})

    def test_provenance_omits_graph_and_secret_values(self):
        graph={"1":{"class_type":"UNETLoader","inputs":{"unet_name":"anima.safetensors","weight_dtype":"default","token":"DO_NOT_COPY"}},
            "2":{"class_type":"LoraLoaderModelOnly","inputs":{"model":["1",0],"lora_name":"style.safetensors","strength_model":1.}},
            "3":{"class_type":"RSMultiCharacterSampler","inputs":{"model":["2",0]}}}
        record=m.graph_assets(graph,"3")
        self.assertEqual([v["node"] for v in record["loaders"]],["UNETLoader","LoraLoaderModelOnly"])
        self.assertNotIn("DO_NOT_COPY",json.dumps(record))
        self.assertNotIn("model",record["loaders"][1])


if __name__ == "__main__":
    unittest.main()
