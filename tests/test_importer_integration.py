import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from clipora.ffmpeg import probe
from clipora.importer import ImportSpec, import_url


SAMPLE_VIDEO_URL = 'https://cdn.truefilesize.com/mp4/sample-1mb.mp4'


@unittest.skipUnless(
    os.environ.get('CLIPORA_RUN_NETWORK_TESTS') == '1',
    'set CLIPORA_RUN_NETWORK_TESTS=1 to run public network integration tests',
)
class URLImportIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tool = os.environ.get('CLIPORA_YTDLP')
        if not tool or not Path(tool).is_file():
            raise unittest.SkipTest('set CLIPORA_YTDLP to an existing yt-dlp executable')
        cls.tool_command = [tool]

    def test_public_direct_video_downloads_as_playable_mp4(self):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            progress = []
            target = import_url(
                ImportSpec(
                    url=SAMPLE_VIDEO_URL,
                    destination=destination,
                    mode='video',
                    quality='480p',
                    audio_format='mp3',
                ),
                progress.append,
                tool_command=self.tool_command,
            )

            info = probe(target)
            self.assertEqual(target.suffix.lower(), '.mp4')
            self.assertTrue(info.has_video)
            self.assertTrue(info.has_audio)
            self.assertGreater(target.stat().st_size, 0)
            self.assertTrue(progress)
            self.assertFalse(any(destination.glob('.clipora-import-*')))

    def test_public_direct_video_extracts_playable_mp3(self):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            progress = []
            target = import_url(
                ImportSpec(
                    url=SAMPLE_VIDEO_URL,
                    destination=destination,
                    mode='audio',
                    quality='สูงสุด',
                    audio_format='mp3',
                ),
                progress.append,
                tool_command=self.tool_command,
            )

            info = probe(target)
            self.assertEqual(target.suffix.lower(), '.mp3')
            self.assertFalse(info.has_video)
            self.assertTrue(info.has_audio)
            self.assertGreater(target.stat().st_size, 0)
            self.assertTrue(progress)
            self.assertFalse(any(destination.glob('.clipora-import-*')))


if __name__ == '__main__':
    unittest.main()
