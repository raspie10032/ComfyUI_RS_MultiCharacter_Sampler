"""Adapter resolution: no network on reuse, pinned download, integrity, retry."""
import hashlib
import importlib
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
assets = importlib.import_module(Path(__file__).resolve().parents[1].name + '.reference_assets')
progress_module = importlib.import_module(Path(__file__).resolve().parents[1].name + '.tagger_progress')
runtime_module = importlib.import_module(assets.__package__ + '.runtime_control')


class RoleKVAssets(unittest.TestCase):
    asset_name = "anima_role_kv"

    def resolve(self, node_id=None):
        return assets._verified_adapter(self.asset_name, node_id)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.contents = b'supported test adapter contents'
        self.spec = {**assets.CATALOG[self.asset_name],
                     'sha256': hashlib.sha256(self.contents).hexdigest()}
        self.host = SimpleNamespace(models_dir=str(self.root), folder_names_and_paths={})
        self.reporter = Mock()
        for context in (patch.dict(assets.CATALOG, {self.asset_name: self.spec}),
                        patch.dict(sys.modules, {'folder_paths': self.host}),
                        patch.object(runtime_module, 'check_interrupted'),
                        patch.object(runtime_module, 'is_interruption', return_value=False),
                        patch.object(progress_module, 'TaggerProgress', return_value=self.reporter)):
            context.start()
            self.addCleanup(context.stop)
        assets._verified_digest.cache_clear()
        self.addCleanup(assets._verified_digest.cache_clear)

    def write(self, path, contents=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.contents if contents is None else contents)
        return path

    def target(self):
        return (self.root / self.spec['folder'] / 'rs_reference' /
                self.spec['subdir'] / self.spec['file'])

    def test_reuses_managed_file_without_hub_installed(self):
        target = self.write(self.target())
        with patch.dict(sys.modules, {'huggingface_hub': None}):
            self.assertEqual(self.resolve('42'), target)
        self.assertEqual(self.reporter.report.call_args.args[1], 1.)

    def test_reuses_lora_and_extra_model_roots_without_download(self):
        for external in (False, True):
            with self.subTest(external=external):
                root = self.root / ('external' if external else 'loras')
                target = self.write(root / 'nested' / Path(self.spec['file']).name)
                self.host.folder_names_and_paths = {'loras': object()} if external else {}
                self.host.get_folder_paths = lambda folder: [str(root)]
                with patch.dict(sys.modules, {'huggingface_hub': None}):
                    self.assertEqual(self.resolve(), target)
                target.unlink()

    def test_download_is_pinned_verified_and_reused(self):
        def download(repo, filename, **kwargs):
            self.assertEqual(repo, self.spec['repo'])
            self.assertEqual(filename, self.spec['file'])
            self.assertEqual(kwargs['revision'], self.spec['revision'])
            self.assertIs(kwargs['tqdm_class'], self.reporter.download_bar.return_value)
            return str(self.write(Path(kwargs['local_dir']) / filename))
        hub = SimpleNamespace(hf_hub_download=Mock(side_effect=download))
        with patch.dict(sys.modules, {'huggingface_hub': hub}):
            self.assertEqual(self.resolve(), self.target())
            self.assertEqual(self.resolve(), self.target())
        hub.hf_hub_download.assert_called_once()

    def test_changed_previously_verified_file_is_rejected_without_deleting_it(self):
        target = self.write(self.target())
        self.assertEqual(self.resolve(), target)
        # Same size: file size alone cannot identify valid cached content.
        target.write_bytes(b'X' * len(self.contents))
        with self.assertRaisesRegex(RuntimeError, 'supported version'):
            self.resolve()
        self.assertEqual(target.read_bytes(), b'X' * len(self.contents))

    def test_corrupt_download_is_never_reported_ready(self):
        hub = SimpleNamespace(hf_hub_download=Mock(return_value=str(self.write(self.target(), b'bad'))))
        # Start with no file: the failure must exercise the download branch.
        self.target().unlink()
        hub.hf_hub_download.side_effect = lambda *a, **k: str(self.write(self.target(), b'bad'))
        with patch.dict(sys.modules, {'huggingface_hub': hub}):
            with self.assertRaisesRegex(RuntimeError, 'supported version'):
                self.resolve()
        self.assertFalse(any('ready' in call.args[0] for call in self.reporter.report.call_args_list))

    def test_download_error_is_retryable_and_retains_cause(self):
        failure = OSError('No space left on device')
        hub = SimpleNamespace(hf_hub_download=Mock(side_effect=failure))
        with patch.dict(sys.modules, {'huggingface_hub': hub}):
            with self.assertRaisesRegex(RuntimeError, 'free disk space') as caught:
                self.resolve()
            self.assertIs(caught.exception.__cause__, failure)
            hub.hf_hub_download.side_effect = lambda *a, **k: str(self.write(self.target()))
            self.assertEqual(self.resolve(), self.target())

    def test_cancellation_propagates_instead_of_becoming_download_error(self):
        class Cancelled(Exception):
            pass
        cancelled = Cancelled()
        runtime = importlib.import_module(assets.__package__ + '.runtime_control')
        hub = SimpleNamespace(hf_hub_download=Mock(side_effect=cancelled))
        with patch.dict(sys.modules, {'huggingface_hub': hub}), \
                patch.object(runtime, 'is_interruption', side_effect=lambda e: e is cancelled):
            with self.assertRaises(Cancelled):
                self.resolve()

    def test_missing_dependency_explains_installation(self):
        with patch.dict(sys.modules, {'huggingface_hub': None}):
            with self.assertRaisesRegex(RuntimeError, 'requirements-reference.txt'):
                self.resolve()


class ReferenceFrame2BAssets(RoleKVAssets):
    asset_name = 'anima_frame'


class ReferenceFrame29BAssets(RoleKVAssets):
    asset_name = 'anima29_frame'


class ReferenceFrameV2Assets(RoleKVAssets):
    asset_name = 'anima_frame_v2'


if __name__ == '__main__':
    unittest.main()
