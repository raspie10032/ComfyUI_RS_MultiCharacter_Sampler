"""Ensure distributed pose PNGs preserve prompts in the editable workflow."""
import json
from pathlib import Path
import unittest
from PIL import Image


class PoseExampleWorkflowTests(unittest.TestCase):
    def test_character_strings_are_connected_and_preserved(self):
        root = Path(__file__).resolve().parents[1] / "examples" / "pose3d"
        for name in ("krea2-pose", "moss-native-pose", "moss-regional-pose",
                     "genshin-krea2-pose", "genshin-moss-native-pose"):
            with self.subTest(example=name), Image.open(root / (name + ".png")) as image:
                workflow = json.loads(image.info["workflow"])
                api = json.loads(image.info["prompt"])
                nodes = {node["id"]: node for node in workflow["nodes"]}
                links = {link[0]: link for link in workflow["links"]}
                prompt = next(node for node in nodes.values()
                              if node["type"] == "RSMultiCharacterPrompt")
                for number in (1, 2):
                    key = f"character{number}"
                    slot = next(i for i, v in enumerate(prompt["inputs"])
                                if v["name"] == key)
                    input_link = links[prompt["inputs"][slot]["link"]]
                    self.assertEqual(input_link[3:5], [prompt["id"], slot])
                    source = nodes[input_link[1]]
                    self.assertEqual(source["type"], "PrimitiveStringMultiline")
                    self.assertIn(input_link[0], source["outputs"][0]["links"])
                    text = source["widgets_values"][0]
                    self.assertTrue(text.strip())
                    api_ref = api[str(prompt["id"])]["inputs"][key]
                    self.assertEqual(api_ref, [str(source["id"]), 0])
                    self.assertEqual(api[api_ref[0]]["inputs"]["value"], text)
                    if name.startswith("genshin-"):
                        self.assertIn("Jean" if number == 1 else "Eula", text)
                for link in links.values():
                    self.assertEqual(nodes[link[3]]["inputs"][link[4]]["link"], link[0])
                    self.assertIn(link[0], nodes[link[1]]["outputs"][link[2]]["links"])


if __name__ == "__main__":
    unittest.main()
