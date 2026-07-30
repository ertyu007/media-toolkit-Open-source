import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from clipora.ffmpeg import (
    CancellationToken,
    ConversionCancelled,
    build_command,
    cleanup_temporary_output,
    convert,
    probe,
    temporary_output_path,
    tools_available,
    validate_operation,
)


@unittest.skipUnless(tools_available(), 'FFmpeg and ffprobe are required')
class FFmpegIntegrationTests(unittest.TestCase):
    def test_running_conversion_can_be_cancelled_without_replacing_target(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            target = root / 'existing output.mp4'
            temporary = temporary_output_path(target)
            target.write_bytes(b'original output')
            cancellation = CancellationToken()
            progress_started = threading.Event()
            errors = []
            command = [
                'ffmpeg',
                '-y',
                '-loglevel',
                'error',
                '-re',
                '-f',
                'lavfi',
                '-i',
                'testsrc=size=160x90:rate=30',
                '-t',
                '20',
                '-an',
                '-c:v',
                'libx264',
                '-pix_fmt',
                'yuv420p',
                '-progress',
                'pipe:1',
                '-nostats',
                str(temporary),
            ]

            def run_conversion():
                try:
                    convert(
                        command,
                        temporary,
                        20.0,
                        lambda _: progress_started.set(),
                        cancellation,
                    )
                except Exception as exc:
                    errors.append(exc)

            worker = threading.Thread(target=run_conversion)
            worker.start()
            self.assertTrue(progress_started.wait(5), 'FFmpeg did not report progress')
            cancellation.cancel()
            worker.join(5)

            self.assertFalse(worker.is_alive(), 'FFmpeg did not stop after cancellation')
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], ConversionCancelled)
            self.assertEqual(target.read_bytes(), b'original output')
            cleanup_temporary_output(temporary, target)
            self.assertFalse(temporary.exists())

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
