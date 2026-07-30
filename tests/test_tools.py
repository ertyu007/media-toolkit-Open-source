import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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


if __name__ == '__main__':
    unittest.main()
