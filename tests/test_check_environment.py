import subprocess
import unittest
from unittest.mock import patch

from scripts.check_environment import check_tool


class EnvironmentCheckTests(unittest.TestCase):
    @patch('scripts.check_environment.shutil.which', return_value=None)
    def test_missing_tool_fails(self, _which):
        result = check_tool('ffmpeg')
        self.assertFalse(result.ok)
        self.assertIn('PATH', result.detail)

    @patch('scripts.check_environment.subprocess.run')
    @patch('scripts.check_environment.shutil.which', return_value='C:/tools/ffmpeg.exe')
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
    @patch('scripts.check_environment.shutil.which', return_value='C:/tools/ffmpeg.exe')
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


if __name__ == '__main__':
    unittest.main()
