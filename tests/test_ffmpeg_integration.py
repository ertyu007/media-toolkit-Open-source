import subprocess
import tempfile
import unittest
from pathlib import Path

from clipora.ffmpeg import build_command, convert, probe, tools_available, validate_operation


@unittest.skipUnless(tools_available(), 'FFmpeg and ffprobe are required')
class FFmpegIntegrationTests(unittest.TestCase):
    def test_unicode_av_video_extracts_playable_mp3(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            source = root / 'คลิป ทดสอบ.mp4'
            target = root / 'เสียง ผลลัพธ์.mp3'
            creation = subprocess.run(
                [
                    'ffmpeg',
                    '-y',
                    '-loglevel',
                    'error',
                    '-f',
                    'lavfi',
                    '-i',
                    'color=c=black:s=160x90:d=1',
                    '-f',
                    'lavfi',
                    '-i',
                    'sine=frequency=440:duration=1',
                    '-shortest',
                    '-c:v',
                    'libx264',
                    '-pix_fmt',
                    'yuv420p',
                    '-c:a',
                    'aac',
                    str(source),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(creation.returncode, 0, creation.stderr)
            source_size = source.stat().st_size

            info = probe(source)
            self.assertTrue(info.has_video)
            self.assertTrue(info.has_audio)
            validate_operation(info, 'audio')

            progress = []
            command = build_command(source, target, 'audio', 'Balanced', 'mp3')
            convert(command, target, info.duration, progress.append)

            result = probe(target)
            self.assertTrue(result.has_audio)
            self.assertFalse(result.has_video)
            self.assertGreater(target.stat().st_size, 0)
            self.assertEqual(source.stat().st_size, source_size)
            self.assertTrue(progress)
            self.assertEqual(progress[-1], 1.0)

    def test_silent_video_converts_to_mp4(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            source = root / 'silent input.mkv'
            target = root / 'silent output.mp4'
            creation = subprocess.run(
                [
                    'ffmpeg',
                    '-y',
                    '-loglevel',
                    'error',
                    '-f',
                    'lavfi',
                    '-i',
                    'color=c=blue:s=160x90:d=1',
                    '-an',
                    str(source),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(creation.returncode, 0, creation.stderr)

            info = probe(source)
            self.assertTrue(info.has_video)
            self.assertFalse(info.has_audio)
            validate_operation(info, 'video')

            command = build_command(source, target, 'video', 'Balanced', 'mp3')
            convert(command, target, info.duration, lambda _: None)
            result = probe(target)
            self.assertTrue(result.has_video)
            self.assertFalse(result.has_audio)


if __name__ == '__main__':
    unittest.main()
