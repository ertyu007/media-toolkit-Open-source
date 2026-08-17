import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from clipora.ffmpeg import tools_available
from clipora.separator import (
    CancellationToken,
    OutputExistsError,
    separate_audio,
    separator_installed,
)


@unittest.skipUnless(
    tools_available() and separator_installed(),
    'FFmpeg and the Demucs separator toolchain are required',
)
class SeparatorIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temporary_directory = tempfile.TemporaryDirectory()
        cls.source = Path(cls._temporary_directory.name) / 'sample audio.wav'
        creation = subprocess.run(
            [
                'ffmpeg',
                '-y',
                '-loglevel',
                'error',
                '-f',
                'lavfi',
                '-i',
                'sine=frequency=440:duration=6',
                '-c:a',
                'pcm_s16le',
                str(cls.source),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert creation.returncode == 0, creation.stderr

    @classmethod
    def tearDownClass(cls):
        cls._temporary_directory.cleanup()

    def test_separates_vocals_and_instrumental(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            outputs = separate_audio(
                self.source,
                destination,
                'mp3',
                ('vocals', 'instrumental'),
                cancellation=CancellationToken(),
            )
            self.assertEqual([path.name for path in outputs], ['sample audio_stems.zip'])
            zip_path = outputs[0]
            self.assertGreater(zip_path.stat().st_size, 0)
            self.assertEqual(
                sorted(path.name for path in destination.iterdir()),
                ['sample audio_stems.zip'],
            )
            with zipfile.ZipFile(zip_path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ['sample audio_instrumental.mp3', 'sample audio_vocals.mp3'],
                )

    def test_existing_output_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            (destination / 'sample audio_stems.zip').write_bytes(b'occupied')
            with self.assertRaises(OutputExistsError):
                separate_audio(self.source, destination, 'mp3', ('vocals',))


if __name__ == '__main__':
    unittest.main()