import subprocess
import unittest
from unittest.mock import patch

from scripts.check_environment import check_javascript_runtime, check_separator, check_tool, check_ytdlp


class EnvironmentCheckTests(unittest.TestCase):
    @patch('scripts.check_environment.find_executable', return_value=None)
    def test_missing_tool_fails(self, _which):
        result = check_tool('ffmpeg')
        self.assertFalse(result.ok)
        self.assertIn('PATH', result.detail)

    @patch('scripts.check_environment.subprocess.run')
    @patch('scripts.check_environment.find_executable', return_value='C:/tools/ffmpeg.exe')
    def test_available_tool_reports_first_version_line(self, _which, run):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='ffmpeg version 8.1\nconfiguration details',
            stderr='',
        )
        result = check_tool('ffmpeg')
        self.assertTrue(result.ok)
        self.assertEqual(result.detail, 'ffmpeg version 8.1')

    @patch('scripts.check_environment.subprocess.run')
    @patch('scripts.check_environment.find_executable', return_value='C:/tools/ffmpeg.exe')
    def test_broken_tool_fails(self, _which, run):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout='',
            stderr='cannot start',
        )
        result = check_tool('ffmpeg')
        self.assertFalse(result.ok)
        self.assertIn('cannot start', result.detail)

    @patch('scripts.check_environment.importlib.util.find_spec', return_value=None)
    @patch('scripts.check_environment.find_executable', return_value=None)
    def test_missing_ytdlp_fails(self, _find, _find_spec):
        result = check_ytdlp()
        self.assertFalse(result.ok)
        self.assertIn('PATH', result.detail)

    @patch('scripts.check_environment.subprocess.run')
    @patch('scripts.check_environment.find_executable', return_value='C:/tools/yt-dlp.exe')
    def test_ytdlp_uses_double_dash_version(self, _which, run):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='2026.07.04\n',
            stderr='',
        )
        result = check_ytdlp()
        self.assertTrue(result.ok)
        self.assertEqual(result.detail, '2026.07.04')
        self.assertEqual(run.call_args.args[0][-1], '--version')

    @patch('scripts.check_environment.subprocess.run')
    @patch('scripts.check_environment.find_executable')
    def test_node_is_accepted_as_javascript_runtime(self, find, run):
        find.side_effect = lambda name: 'C:/node.exe' if name == 'node' else None
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='v24.0.0\n',
            stderr='',
        )
        result = check_javascript_runtime()
        self.assertTrue(result.ok)
        self.assertIn('node', result.detail)

    @patch('scripts.check_environment.find_executable', return_value=None)
    def test_missing_javascript_runtime_fails(self, _which):
        result = check_javascript_runtime()
        self.assertFalse(result.ok)
        self.assertIn('Deno', result.detail)

    @patch('clipora.separator.separator_installed', return_value=True)
    def test_separator_installed_reports_ready(self, _installed):
        result = check_separator()
        self.assertTrue(result.ok)
        self.assertIn('Demucs', result.detail)

    @patch('clipora.separator.separator_installed', return_value=False)
    def test_separator_missing_is_optional(self, _installed):
        result = check_separator()
        self.assertTrue(result.ok)
        self.assertIn('ยังไม่ได้ติดตั้ง', result.detail)


if __name__ == '__main__':
    unittest.main()
