import hashlib
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import clipora.tools
from clipora.tools import find_executable, managed_tools_dir, missing_required_tools


class ToolDiscoveryTests(unittest.TestCase):
    def test_managed_tools_directory_uses_local_app_data(self):
        with TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'LOCALAPPDATA': directory}):
                self.assertEqual(
                    managed_tools_dir(),
                    Path(directory) / 'Clipora' / 'tools',
                )

    @patch('clipora.tools.shutil.which', return_value=None)
    def test_managed_binary_is_discovered(self, _which):
        with TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'LOCALAPPDATA': directory}, clear=False):
                executable = managed_tools_dir() / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
                executable.parent.mkdir(parents=True)
                executable.write_bytes(b'ffmpeg')

                self.assertEqual(find_executable('ffmpeg'), executable)

    @patch('clipora.tools.shutil.which', return_value=None)
    def test_explicit_environment_override_has_priority(self, _which):
        with TemporaryDirectory() as directory:
            override = Path(directory) / 'custom-ffmpeg.exe'
            override.write_bytes(b'custom')
            with patch.dict(os.environ, {'CLIPORA_FFMPEG': str(override)}):
                self.assertEqual(find_executable('ffmpeg'), override)

    @patch('clipora.tools.find_executable')
    def test_node_satisfies_javascript_runtime_requirement(self, find):
        find.side_effect = lambda name: Path('node.exe') if name == 'node' else Path(f'{name}.exe') if name in {'ffmpeg', 'ffprobe', 'yt-dlp'} else None
        self.assertEqual(missing_required_tools(), ())

    @patch('clipora.tools.shutil.which', return_value=None)
    def test_relative_environment_override_rejected(self, _which):
        self._managed_toolbox()
        with patch.dict(os.environ, {'CLIPORA_FFMPEG': 'custom-ffmpeg.exe'}, clear=False):
            self.assertIsNone(find_executable('ffmpeg'))

    def _managed_toolbox(self):
        directory = TemporaryDirectory()
        toolbox = self.enterContext(patch.dict(os.environ, {'LOCALAPPDATA': directory.name}))
        self.addCleanup(directory.cleanup)
        return toolbox

    def _reset_hash_cache(self):
        cache = clipora.tools._hash_verified_tools
        cache.clear()
        self.addCleanup(cache.clear)

    @patch('clipora.tools.shutil.which', return_value=None)
    def test_managed_ytdlp_matching_record_is_accepted(self, _which):
        self._managed_toolbox()
        self._reset_hash_cache()
        root = managed_tools_dir()
        root.mkdir(parents=True)
        sha = hashlib.sha256(b'good').hexdigest()
        (root / 'installed.json').write_text(
            json.dumps({'schema': 1, 'dependencies': {'yt-dlp': {'sha256': sha}}}), encoding='utf-8'
        )
        executable = root / ('yt-dlp.exe' if os.name == 'nt' else 'yt-dlp')
        executable.write_bytes(b'good')
        self.assertEqual(find_executable('yt-dlp'), executable)

    @patch('clipora.tools.shutil.which', return_value=None)
    def test_tampered_managed_ytdlp_is_ignored_with_fallback(self, _which):
        self._managed_toolbox()
        self._reset_hash_cache()
        root = managed_tools_dir()
        root.mkdir(parents=True)
        (root / 'installed.json').write_text(
            json.dumps({'schema': 1, 'dependencies': {'yt-dlp': {'sha256': 'f' * 64}}}), encoding='utf-8'
        )
        filename = clipora.tools.executable_filename('yt-dlp')
        (root / filename).write_bytes(b'tampered')
        self.assertIsNone(find_executable('yt-dlp'))
        legacy = Path(os.environ['LOCALAPPDATA']) / 'Clipora' / 'bin' / filename
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(b'legacy')
        self.assertEqual(find_executable('yt-dlp'), legacy)

    @patch('clipora.tools.shutil.which', return_value=None)
    def test_missing_install_record_keeps_managed_ytdlp(self, _which):
        self._managed_toolbox()
        self._reset_hash_cache()
        root = managed_tools_dir()
        root.mkdir(parents=True)
        (root / 'installed.json').write_text('not json', encoding='utf-8')
        executable = root / ('yt-dlp.exe' if os.name == 'nt' else 'yt-dlp')
        executable.write_bytes(b'raw')
        self.assertEqual(find_executable('yt-dlp'), executable)


if __name__ == '__main__':
    unittest.main()
