from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from clipora.app_update import (
    AppReleaseInfo,
    AppUpdateError,
    clear_skipped_version,
    download_app_update,
    fetch_latest_app_release,
    get_skipped_version,
    is_app_update_available,
    load_settings,
    parse_app_version,
    parse_release_payload,
    save_settings,
    set_skipped_version,
    update_space_requirements,
)


class VersionParsingTests(unittest.TestCase):
    def test_parses_standard_semver(self):
        self.assertEqual(parse_app_version('0.6.1'), (0, 6, 1))
        self.assertEqual(parse_app_version('1.0.0'), (1, 0, 0))
        self.assertEqual(parse_app_version('2.15.3'), (2, 15, 3))

    def test_parses_with_pc_prefix(self):
        self.assertEqual(parse_app_version('pc-v0.6.1'), (0, 6, 1))
        self.assertEqual(parse_app_version('pc-v1.0.0'), (1, 0, 0))

    def test_parses_with_v_prefix(self):
        self.assertEqual(parse_app_version('v0.6.1'), (0, 6, 1))

    def test_handles_empty_or_invalid(self):
        self.assertIsNone(parse_app_version(''))
        self.assertIsNone(parse_app_version(None))
        self.assertIsNone(parse_app_version('abc'))

    def test_update_tag_must_be_a_strict_three_part_version(self):
        info = parse_release_payload([
            {'tag_name': 'pc-v0.7.0/evil', 'draft': False, 'assets': []},
            {'tag_name': 'pc-v0.7.0', 'draft': False, 'assets': []},
        ])
        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info.version, '0.7.0')


class UpdateComparisonTests(unittest.TestCase):
    def test_newer_version_is_detected(self):
        self.assertTrue(is_app_update_available('0.7.0', '0.6.1'))
        self.assertTrue(is_app_update_available('pc-v1.0.0', '0.6.1'))
        self.assertTrue(is_app_update_available('0.6.2', '0.6.1'))

    def test_same_or_older_version_returns_false(self):
        self.assertFalse(is_app_update_available('0.6.1', '0.6.1'))
        self.assertFalse(is_app_update_available('pc-v0.6.1', '0.6.1'))
        self.assertFalse(is_app_update_available('0.5.6', '0.6.1'))
        self.assertFalse(is_app_update_available('0.5.0', '0.6.1'))

    def test_invalid_current_version_assumes_update_available(self):
        self.assertTrue(is_app_update_available('0.6.1', None))
        self.assertTrue(is_app_update_available('0.6.1', ''))


class ReleasePayloadParsingTests(unittest.TestCase):
    def test_extracts_latest_pc_release(self):
        payload = [
            {
                'tag_name': 'mobile-v1.2.0',
                'name': 'Clipora Mobile 1.2.0',
                'body': 'Mobile fixes',
                'html_url': 'https://github.com/.../releases/tag/mobile-v1.2.0',
                'draft': False,
                'assets': [],
            },
            {
                'tag_name': 'pc-v0.7.0',
                'name': 'Clipora 0.7.0',
                'body': '## What is New\n- Feature A\n- Feature B',
                'html_url': 'https://github.com/ertyu007/media-toolkit-Open-source/releases/tag/pc-v0.7.0',
                'draft': False,
                'published_at': '2026-08-22T00:00:00Z',
                'assets': [
                    {
                        'name': 'Clipora-Setup-0.7.0-x64.exe',
                        'browser_download_url': 'https://github.com/ertyu007/media-toolkit-Open-source/releases/download/pc-v0.7.0/Clipora-Setup-0.7.0-x64.exe',
                        'size': 5,
                    },
                    {
                        'name': 'Clipora-Setup-0.7.0-x64.exe.sha256',
                        'browser_download_url': 'https://github.com/ertyu007/media-toolkit-Open-source/releases/download/pc-v0.7.0/Clipora-Setup-0.7.0-x64.exe.sha256',
                    },
                    {
                        'name': 'Clipora-0.7.0-x64.zip',
                        'browser_download_url': 'https://github.com/.../Clipora-0.7.0-x64.zip',
                    },
                ],
            },
            {
                'tag_name': 'pc-v0.6.1',
                'name': 'Clipora 0.6.1',
                'draft': False,
            },
        ]
        info = parse_release_payload(payload)
        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info.version, '0.7.0')
        self.assertEqual(info.tag_name, 'pc-v0.7.0')
        self.assertEqual(info.title, 'Clipora 0.7.0')
        self.assertIn('Feature A', info.release_notes)
        self.assertEqual(info.download_url, 'https://github.com/ertyu007/media-toolkit-Open-source/releases/download/pc-v0.7.0/Clipora-Setup-0.7.0-x64.exe')
        self.assertEqual(info.checksum_url, 'https://github.com/ertyu007/media-toolkit-Open-source/releases/download/pc-v0.7.0/Clipora-Setup-0.7.0-x64.exe.sha256')
        self.assertEqual(info.download_size, 5)
        self.assertEqual(info.html_url, 'https://github.com/ertyu007/media-toolkit-Open-source/releases/tag/pc-v0.7.0')

    def test_ignores_drafts(self):
        payload = [
            {
                'tag_name': 'pc-v0.8.0',
                'name': 'Draft Release',
                'draft': True,
            },
            {
                'tag_name': 'pc-v0.7.0',
                'name': 'Clipora 0.7.0',
                'draft': False,
            },
        ]
        info = parse_release_payload(payload)
        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info.version, '0.7.0')

    def test_fallbacks_to_html_url_when_no_installer_asset(self):
        payload = [
            {
                'tag_name': 'pc-v0.7.0',
                'name': 'Clipora 0.7.0',
                'body': 'Notes',
                'html_url': 'https://github.com/release/page',
                'draft': False,
                'assets': [],
            }
        ]
        info = parse_release_payload(payload)
        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info.download_url, 'https://github.com/release/page')

    def test_raises_on_invalid_json(self):
        with self.assertRaises(AppUpdateError):
            parse_release_payload('{bad json')


class SettingsStorageTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.temp_path = Path(self._temp_dir.name)
        self.settings_file = self.temp_path / 'settings.json'

    def test_saves_and_loads_skipped_version(self):
        with patch('clipora.app_update._settings_file_path', return_value=self.settings_file):
            self.assertIsNone(get_skipped_version())

            set_skipped_version('0.7.0')
            self.assertEqual(get_skipped_version(), '0.7.0')

            # Verify persisted JSON structure
            saved = json.loads(self.settings_file.read_text(encoding='utf-8'))
            self.assertEqual(saved.get('skipped_app_version'), '0.7.0')

            clear_skipped_version()
            self.assertIsNone(get_skipped_version())


class FetchReleaseTests(unittest.TestCase):
    def test_rejects_non_https_url(self):
        with self.assertRaises(AppUpdateError):
            fetch_latest_app_release('http://api.github.com/releases')

    @patch('urllib.request.urlopen')
    def test_fetches_and_parses_release(self, mock_urlopen):
        mock_response = MagicMock()
        sample_json = json.dumps([
            {
                'tag_name': 'pc-v0.7.0',
                'name': 'Clipora 0.7.0',
                'body': 'Changelog text',
                'html_url': 'https://github.com/ertyu007/media-toolkit-Open-source/releases/tag/pc-v0.7.0',
                'draft': False,
                'assets': [
                    {
                        'name': 'Clipora-Setup-0.7.0-x64.exe',
                        'browser_download_url': 'https://github.com/ertyu007/media-toolkit-Open-source/releases/download/pc-v0.7.0/Clipora-Setup-0.7.0-x64.exe',
                        'size': 5,
                    },
                    {
                        'name': 'Clipora-Setup-0.7.0-x64.exe.sha256',
                        'browser_download_url': 'https://github.com/ertyu007/media-toolkit-Open-source/releases/download/pc-v0.7.0/Clipora-Setup-0.7.0-x64.exe.sha256',
                    }
                ],
            }
        ]).encode('utf-8')
        mock_response.read.return_value = sample_json
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        info = fetch_latest_app_release()
        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info.version, '0.7.0')
        self.assertEqual(info.download_url, 'https://github.com/ertyu007/media-toolkit-Open-source/releases/download/pc-v0.7.0/Clipora-Setup-0.7.0-x64.exe')
        self.assertEqual(info.download_size, 5)
        self.assertEqual(info.release_notes, 'Changelog text')


class AppUpdateDownloadTests(unittest.TestCase):
    def _release(self, size: int) -> AppReleaseInfo:
        base = 'https://github.com/ertyu007/media-toolkit-Open-source/releases/download/pc-v0.7.0/'
        return AppReleaseInfo(
            version='0.7.0',
            tag_name='pc-v0.7.0',
            title='Clipora 0.7.0',
            release_notes='',
            html_url='https://github.com/ertyu007/media-toolkit-Open-source/releases/tag/pc-v0.7.0',
            download_url=base + 'Clipora-Setup-0.7.0-x64.exe',
            download_size=size,
            checksum_url=base + 'Clipora-Setup-0.7.0-x64.exe.sha256',
        )

    def test_download_verifies_checksum_and_publishes_atomically(self):
        payload = b'installer bytes'

        class Response(io.BytesIO):
            headers = {'Content-Length': str(len(payload))}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch('clipora.app_update.check_update_disk_space'),
                patch('clipora.app_update._read_update_checksum', return_value=hashlib.sha256(payload).hexdigest()),
                patch('clipora.app_update._download_response', return_value=Response(payload)),
            ):
                target = download_app_update(
                    self._release(len(payload)),
                    update_dir=Path(directory),
                )
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(target.name, 'Clipora-Setup-0.7.0-x64.exe')

    def test_checksum_mismatch_preserves_existing_installer_and_cleans_partial(self):
        payload = b'bad installer'

        class Response(io.BytesIO):
            headers = {'Content-Length': str(len(payload))}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'Clipora-Setup-0.7.0-x64.exe'
            target.write_bytes(b'previous verified installer')
            with (
                patch('clipora.app_update.check_update_disk_space'),
                patch('clipora.app_update._read_update_checksum', return_value='0' * 64),
                patch('clipora.app_update._download_response', return_value=Response(payload)),
            ):
                with self.assertRaises(AppUpdateError):
                    download_app_update(self._release(len(payload)), update_dir=Path(directory))
            self.assertEqual(target.read_bytes(), b'previous verified installer')
            self.assertEqual(list(Path(directory).iterdir()), [target])

    def test_download_rejects_non_release_asset_host(self):
        release = self._release(12)
        unsafe = AppReleaseInfo(
            **{
                **release.__dict__,
                'download_url': 'https://example.com/installer.exe',
            }
        )
        with self.assertRaises(AppUpdateError):
            download_app_update(unsafe, update_dir=Path(tempfile.gettempdir()))

    def test_space_estimate_includes_installer_extraction_margin(self):
        download, installer_temp = update_space_requirements(100)
        self.assertGreater(download, 100)
        self.assertGreater(installer_temp, download)


if __name__ == '__main__':
    unittest.main()
