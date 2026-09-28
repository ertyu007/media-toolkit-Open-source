import unittest
from pathlib import Path
from unittest.mock import patch

from clipora.ffmpeg import CancellationToken
from clipora.preview import (
    PREVIEW_FIELDS,
    LinkPreview,
    build_preview_command,
    download_thumbnail,
    parse_preview_output,
)


class PreviewCommandTests(unittest.TestCase):
    def test_metadata_only_single_item_no_credentials(self):
        command = build_preview_command(['yt-dlp'], 'https://example.com/watch/123')
        self.assertIn('--skip-download', command)
        self.assertIn('--no-playlist', command)
        self.assertIn('--ignore-config', command)
        self.assertEqual(command[-1], 'https://example.com/watch/123')
        self.assertEqual(command[-2], '--')
        for field in PREVIEW_FIELDS:
            self.assertIn(field, command)
        for forbidden in ('--cookies', '--cookies-from-browser', '--username', '--password'):
            self.assertNotIn(forbidden, command)

    def test_rejects_private_urls(self):
        with self.assertRaises(ValueError):
            build_preview_command(['yt-dlp'], 'http://127.0.0.1/video.mp4')

    def test_rejects_missing_tool(self):
        with self.assertRaises(ValueError):
            build_preview_command([], 'https://example.com/video')


class PreviewParsingTests(unittest.TestCase):
    def test_parses_four_fields_in_order(self):
        preview = parse_preview_output(
            'Some Title\n3:45\nhttps://cdn.example.com/t.jpg\nSome Channel'
        )
        self.assertEqual(
            preview,
            LinkPreview(
                title='Some Title',
                uploader='Some Channel',
                duration='3:45',
                thumbnail_url='https://cdn.example.com/t.jpg',
            ),
        )

    def test_na_and_short_output_become_empty(self):
        preview = parse_preview_output('Only Title\nNA\n')
        self.assertEqual(preview.title, 'Only Title')
        self.assertEqual(preview.duration, '')
        self.assertEqual(preview.thumbnail_url, '')
        self.assertEqual(preview.uploader, '')


class ThumbnailDownloadTests(unittest.TestCase):
    def test_rejects_non_http_urls_without_network(self):
        with patch('clipora.preview.urllib.request.urlopen') as urlopen:
            self.assertIsNone(download_thumbnail('ftp://example.com/t.jpg', Path('out.png')))
            urlopen.assert_not_called()

    def test_pre_cancelled_token_aborts_fetch(self):
        from clipora.preview import fetch_link_preview

        token = CancellationToken()
        token.cancel()
        with self.assertRaises(Exception):
            fetch_link_preview(
                'https://example.com/video', cancellation=token, tool_command=['yt-dlp']
            )


if __name__ == '__main__':
    unittest.main()
