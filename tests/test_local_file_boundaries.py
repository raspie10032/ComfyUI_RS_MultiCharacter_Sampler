# SPDX-License-Identifier: GPL-3.0-only
"""The node and Workspace readers enforce their scopes even on older ComfyUI."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
image_node = importlib.import_module(ROOT.name + '.nodes').RSMultiCharacterLoadImage
notice = importlib.import_module(ROOT.name + '.metadata_notice')
pose_library = importlib.import_module(ROOT.name + '.pose_library')
wildcards = importlib.import_module(ROOT.name + '.app_wildcards')
tagger = importlib.import_module(ROOT.name + '.wd_tagger')


class LocalFileBoundaries(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.directories = {key: self.root / key for key in ('input', 'output', 'temp', 'user')}
        for directory in self.directories.values():
            directory.mkdir()

        def annotated_filepath(name):
            for key in ('input', 'output', 'temp'):
                marker = f' [{key}]'
                if name.endswith(marker):
                    return name.removesuffix(marker), str(self.directories[key])
            return name, None

        folder_paths = SimpleNamespace(
            annotated_filepath=annotated_filepath,
            base_path=str(self.root),
            get_input_directory=lambda: str(self.directories['input']),
            get_user_directory=lambda: str(self.directories['user']),
            get_folder_paths=lambda _: [str(self.root / 'custom_nodes')],
        )
        module = patch.dict(sys.modules, {'folder_paths': folder_paths})
        module.start()
        self.addCleanup(module.stop)

    def link(self, link, target, **kwargs):
        try:
            link.symlink_to(target, **kwargs)
        except OSError as error:
            self.skipTest(f'Symbolic links unavailable: {error}')

    def test_image_validation_hash_load_and_notice_agree_for_annotated_images(self):
        centers = [{'x': 0.5, 'y': 0.5}]
        caption = {'base_caption': 'scene', 'char_captions': [{'char_caption': 'cat', 'centers': centers}]}
        record = {key: {'caption': caption} for key in ('v4_prompt', 'v4_negative_prompt')}
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('Comment', json.dumps(record))
        for directory, annotation in [('input', ''), ('output', ' [output]'), ('temp', ' [temp]')]:
            with self.subTest(directory=directory):
                path = self.directories[directory] / 'scene.png'
                Image.new('RGB', (8, 8)).save(path, pnginfo=metadata)
                name = path.name + annotation
                self.assertIs(image_node.VALIDATE_INPUTS(name), True)
                self.assertEqual(image_node.IS_CHANGED(name), hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(image_node().load(name)[0].shape, (1, 8, 8, 3))
                self.assertEqual(notice.inspect_file(name)['character_count'], 1)
        self.assertIsInstance(image_node.VALIDATE_INPUTS('missing.png'), str)

    def test_image_validation_and_readers_reject_paths_outside_selected_directory(self):
        outfile = self.directories['output'] / 'scene.png'
        Image.new('RGB', (8, 8)).save(outfile)
        self.link(self.directories['input'] / 'linked.png', outfile)
        for selection in ('linked.png', '../output/scene.png', str(outfile)):
            with self.subTest(selection=selection):
                self.assertIsInstance(image_node.VALIDATE_INPUTS(selection), str)
                with patch('PIL.Image.open') as open_image:
                    for read in (image_node().load, image_node.IS_CHANGED, notice.inspect_file):
                        with self.assertRaises(ValueError):
                            read(selection)
                    open_image.assert_not_called()

    def test_only_configured_wildcard_roots_and_their_files_are_visible(self):
        safe = self.root / 'wildcards'
        safe.mkdir()
        (safe / 'landscape.txt').write_text('lake', encoding='utf-8')
        outside = self.root / 'private'
        outside.mkdir()
        (outside / 'notes.txt').write_text('private', encoding='utf-8')
        self.link(self.directories['user'] / 'wildcards', outside, target_is_directory=True)
        self.link(safe / 'linked.txt', outside / 'notes.txt')
        self.assertEqual(wildcards.inventory(), {'comfy/landscape': safe.resolve() / 'landscape.txt'})

    def test_pose_catalogue_cannot_link_outside_a_configured_directory(self):
        catalogue = {'schema': 'rs.pose-library.v1', 'poses': [{'id': 'test', 'joints': {}}]}
        outside = self.root / 'private.json'
        outside.write_text(json.dumps(catalogue), encoding='utf-8')
        library = self.root / 'pose'
        library.mkdir()
        index = library / 'library.json'
        self.link(index, outside)
        result = pose_library.read_library([library])
        self.assertEqual(result['poses'], [])
        self.assertNotIn(str(self.root), str(result))
        index.unlink()
        index.write_text(json.dumps(catalogue), encoding='utf-8')
        self.assertEqual(pose_library.read_library([library])['poses'][0]['id'], 'test')

    def test_pixai_verifies_code_and_both_configuration_files(self):
        data = {name: name.encode() for name in tagger.PIXAI_SNAPSHOT_SHA256}
        checksums = {name: hashlib.sha256(content).hexdigest() for name, content in data.items()}
        files = {name: self.root / name for name in data}
        for name, path in files.items():
            path.write_bytes(data[name])
        with patch.object(tagger, 'PIXAI_SNAPSHOT_SHA256', checksums):
            self.assertEqual(tagger._verify_pixai_snapshot(files), self.root)
            for name, path in files.items():
                with self.subTest(filename=name):
                    path.write_bytes(b'invalid')
                    with self.assertRaisesRegex(ValueError, name + ' checksum mismatch'):
                        tagger._verify_pixai_snapshot(files)
                    path.write_bytes(data[name])


class WildcardRouteErrors(unittest.IsolatedAsyncioTestCase):
    async def test_filesystem_errors_are_redacted_in_workspace_responses(self):
        routes = web.RouteTableDef()
        server = SimpleNamespace(PromptServer=SimpleNamespace(instance=SimpleNamespace(routes=routes)))
        with patch.dict(sys.modules, {'server': server}):
            wildcards.register_routes()
        app = web.Application()
        app.add_routes(routes)
        with patch.object(wildcards, 'inventory', side_effect=PermissionError('private filesystem location')):
            async with TestClient(TestServer(app)) as client:
                for response in (
                    await client.get('/rs_mc/app/wildcards'),
                    await client.post('/rs_mc/app/wildcards/resolve', json={'texts': {'a': '__x__'}, 'seed': 1}),
                ):
                    self.assertEqual(response.status, 400)
                    self.assertNotIn('private filesystem location', (await response.json())['error'])
