import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from clipora.conversion import run_local_conversion
from clipora.ffmpeg import (
    CancellationToken,
    ConversionCancelled,
    FFmpegError,
    JobSpec,
    MediaInfo,
)


class LocalConversionTests(unittest.TestCase):
    def _job(self, source: Path, destination: Path) -> JobSpec:
        return JobSpec(source, destination, 'audio', 'Balanced', 'mp3')

    @patch('clipora.conversion.validate_output', return_value=MediaInfo(1.0, False, True))
    @patch('clipora.conversion.convert')
    @patch('clipora.conversion.probe', return_value=MediaInfo(1.0, True, True))
    def test_validates_temporary_output_before_publishing(self, probe, convert, validate):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp4'
            source.write_bytes(b'source')
            target = root / 'result.mp3'

            def create_output(command, _target, *_args):
                Path(command[-1]).write_bytes(b'encoded')

            convert.side_effect = create_output
            run_local_conversion(
                self._job(source, root), target, CancellationToken(),
            )

            self.assertEqual(target.read_bytes(), b'encoded')
            probe.assert_called_once_with(source)
            validate.assert_called_once()

    @patch('clipora.conversion.convert')
    @patch('clipora.conversion.probe', return_value=MediaInfo(1.0, True, True))
    def test_cancellation_preserves_existing_target(self, _probe, convert):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp4'
            source.write_bytes(b'source')
            target = root / 'result.mp3'
            target.write_bytes(b'previous output')
            cancellation = CancellationToken()

            def cancel_job(command, _target, *_args):
                Path(command[-1]).write_bytes(b'partial')
                cancellation.cancel()

            convert.side_effect = cancel_job
            with self.assertRaises(ConversionCancelled):
                run_local_conversion(
                    self._job(source, root), target, cancellation, overwrite=True,
                )

            self.assertEqual(target.read_bytes(), b'previous output')
            self.assertFalse(list(root.glob('*.clipora-*')))


class EnhancedAudioFallbackTests(unittest.TestCase):
    def _run(self, root: Path, validate_side_effect) -> tuple[list[list[str]], Path]:
        source = root / 'source.mp4'
        source.write_bytes(b'source')
        target = root / 'result.mp3'
        job = JobSpec(source, root, 'audio', 'Balanced', 'mp3', enhance=True)
        commands: list[list[str]] = []

        def fake_convert(command, *_args):
            commands.append(list(command))
            Path(command[-1]).write_bytes(b'encoded')

        with patch(
            'clipora.conversion.probe', return_value=MediaInfo(1.0, True, True),
        ), patch(
            'clipora.conversion.validate_output', side_effect=validate_side_effect,
        ), patch('clipora.conversion.convert', side_effect=fake_convert):
            run_local_conversion(job, target, CancellationToken())
        return commands, target

    @staticmethod
    def _temporary_files(root: Path) -> list[str]:
        return [path.name for path in root.iterdir() if '.clipora-' in path.name]

    def test_silent_enhanced_output_retries_without_enhance(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            commands, target = self._run(
                root,
                [
                    FFmpegError('Failed to find two consecutive MPEG audio frames'),
                    MediaInfo(1.0, False, True),
                ],
            )

            self.assertEqual(len(commands), 2)
            self.assertIn('-af', commands[0])
            self.assertNotIn('-af', commands[1])
            self.assertEqual(target.read_bytes(), b'encoded')
            self.assertEqual(self._temporary_files(root), [])

    def test_valid_enhanced_output_is_not_retried(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            commands, _target = self._run(root, [MediaInfo(1.0, False, True)])

            self.assertEqual(len(commands), 1)
            self.assertIn('-af', commands[0])

    def test_failed_retry_propagates_the_error_and_cleans_up(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            error = FFmpegError('Invalid data found when processing input')
            with self.assertRaisesRegex(FFmpegError, 'Invalid data'):
                self._run(root, error)

            self.assertFalse((root / 'result.mp3').exists())
            self.assertEqual(self._temporary_files(root), [])


class HardwareFallbackTests(unittest.TestCase):
    def _video_job(self, source: Path, destination: Path, hardware: bool) -> JobSpec:
        return JobSpec(
            source, destination, 'video', 'Balanced', 'm4a',
            video_format='mp4', hardware=hardware,
        )

    def _run(self, job, target, side_effect):
        with patch('clipora.conversion.probe', return_value=MediaInfo(1.0, True, True)), \
                patch(
                    'clipora.conversion.validate_output',
                    return_value=MediaInfo(1.0, True, True),
                ), \
                patch('clipora.conversion.convert', side_effect=side_effect), \
                patch(
                    'clipora.ffmpeg.hardware_h264_encoder',
                    return_value='h264_nvenc',
                ):
            run_local_conversion(job, target, CancellationToken())

    @staticmethod
    def _temporary_files(root: Path) -> list[str]:
        return [path.name for path in root.iterdir() if '.clipora-' in path.name]

    def test_hardware_failure_retries_once_with_libx264(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp4'
            source.write_bytes(b'source')
            target = root / 'result.mp4'
            calls: list[list[str]] = []

            def fake_convert(command, _target, *_args):
                calls.append(list(command))
                if len(calls) == 1:
                    Path(command[-1]).write_bytes(b'partial')
                    raise FFmpegError(
                        'Cannot load nvenc: No capable devices found'
                    )
                # The failed partial file must already be gone.
                self.assertFalse(Path(calls[0][-1]).exists())
                Path(command[-1]).write_bytes(b'encoded')

            self._run(self._video_job(source, root, hardware=True), target, fake_convert)

            self.assertEqual(len(calls), 2)
            self.assertIn('h264_nvenc', calls[0])
            self.assertIn('libx264', calls[1])
            self.assertNotIn('h264_nvenc', calls[1])
            self.assertNotEqual(calls[0][-1], calls[1][-1])
            self.assertEqual(target.read_bytes(), b'encoded')
            self.assertEqual(self._temporary_files(root), [])

    def test_non_encoder_error_is_not_retried(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp4'
            source.write_bytes(b'source')
            target = root / 'result.mp4'
            calls: list[list[str]] = []

            def fake_convert(command, *_args):
                calls.append(list(command))
                raise FFmpegError('Invalid data found when processing input')

            with self.assertRaisesRegex(FFmpegError, 'Invalid data'):
                self._run(
                    self._video_job(source, root, hardware=True), target, fake_convert,
                )

            self.assertEqual(len(calls), 1)
            self.assertFalse(target.exists())
            self.assertEqual(self._temporary_files(root), [])

    def test_successful_hardware_attempt_does_not_retry(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp4'
            source.write_bytes(b'source')
            target = root / 'result.mp4'
            calls: list[list[str]] = []

            def fake_convert(command, *_args):
                calls.append(list(command))
                Path(command[-1]).write_bytes(b'encoded')

            self._run(self._video_job(source, root, hardware=True), target, fake_convert)

            self.assertEqual(len(calls), 1)
            self.assertIn('h264_nvenc', calls[0])
            self.assertEqual(target.read_bytes(), b'encoded')

    def test_encoder_error_without_hardware_flag_is_not_retried(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp4'
            source.write_bytes(b'source')
            target = root / 'result.mp4'
            calls: list[list[str]] = []

            def fake_convert(command, *_args):
                calls.append(list(command))
                raise FFmpegError('Unknown encoder libx264')

            with self.assertRaisesRegex(FFmpegError, 'Unknown encoder'):
                self._run(
                    self._video_job(source, root, hardware=False), target, fake_convert,
                )

            self.assertEqual(len(calls), 1)
            self.assertIn('libx264', calls[0])

    def test_failed_retry_preserves_existing_target(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp4'
            source.write_bytes(b'source')
            target = root / 'result.mp4'
            target.write_bytes(b'previous output')
            calls: list[list[str]] = []

            def fake_convert(command, *_args):
                calls.append(list(command))
                if len(calls) == 1:
                    raise FFmpegError('Error while opening encoder for output stream')
                raise FFmpegError('some unrelated failure')

            with self.assertRaisesRegex(FFmpegError, 'unrelated'):
                self._run(self._video_job(source, root, hardware=True), target, fake_convert)

            self.assertEqual(len(calls), 2)
            self.assertEqual(target.read_bytes(), b'previous output')
            self.assertEqual(self._temporary_files(root), [])


if __name__ == '__main__':
    unittest.main()
