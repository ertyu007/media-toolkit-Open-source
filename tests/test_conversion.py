import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from clipora.conversion import run_local_conversion
from clipora.ffmpeg import CancellationToken, ConversionCancelled, JobSpec, MediaInfo


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


if __name__ == '__main__':
    unittest.main()
