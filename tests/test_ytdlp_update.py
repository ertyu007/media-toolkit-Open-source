import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from clipora.dependencies import DependencyInstallError
from clipora.ytdlp_update import (
    YtDlpUpdateError,
    _download_https_file,
    _fetch_https_text,
    _parse_checksum_digest,
    _recorded_ytdlp_version,
    installed_ytdlp_version,
    is_newer_available,
    latest_ytdlp_version,
    parse_ytdlp_version,
    update_ytdlp,
)

CHECKSUMS = (
    '0000000000000000000000000000000000000000000000000000000000000000  SHA2-256SUMS\n'
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  yt-dlp\n'
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb  yt-dlp.exe\n'
)


class VersionParsingTests(unittest.TestCase):
    def test_parses_stable_date(self):
        self.assertEqual(parse_ytdlp_version('2026.07.04'), (2026, 7, 4))

    def test_parses_nightly_with_prefix(self):
        self.assertEqual(parse_ytdlp_version('nightly.2026.08.16'), (2026, 8, 16))

    def test_unrecognized_text_returns_none(self):
        self.assertIsNone(parse_ytdlp_version('not a version'))
        self.assertIsNone(parse_ytdlp_version(''))

    def test_is_newer_available_compares_dates(self):
        self.assertTrue(is_newer_available('2026.08.01', '2026.07.04'))
        self.assertFalse(is_newer_available('2026.07.04', '2026.08.01'))
        self.assertFalse(is_newer_available('2026.07.04', '2026.07.04'))
        self.assertTrue(is_newer_available('2026.07.04', None))
        self.assertFalse(is_newer_available('garbage', '2026.07.04'))


class ChecksumParsingTests(unittest.TestCase):
    def test_finds_matching_digest(self):
        self.assertEqual(
            _parse_checksum_digest(CHECKSUMS, 'yt-dlp.exe'),
            'b' * 64,
        )

    def test_missing_filename_raises(self):
        with self.assertRaisesRegex(YtDlpUpdateError, 'checksum'):
            _parse_checksum_digest(CHECKSUMS, 'missing.exe')

    def test_bad_digest_format_is_ignored(self):
        with self.assertRaisesRegex(YtDlpUpdateError, 'checksum'):
            _parse_checksum_digest('not-a-digest  yt-dlp.exe\n', 'yt-dlp.exe')


class InstalledVersionTests(unittest.TestCase):
    @patch('clipora.ytdlp_update.find_executable', return_value=None)
    def test_missing_executable_returns_none(self, _find):
        self.assertIsNone(installed_ytdlp_version())

    @patch('clipora.ytdlp_update.subprocess.run')
    @patch('clipora.ytdlp_update.find_executable', return_value=Path('C:/yt-dlp.exe'))
    def test_reports_version_output(self, _find, run):
        run.return_value = unittest.mock.Mock(returncode=0, stdout='2026.07.04\n')
        self.assertEqual(installed_ytdlp_version(), '2026.07.04')

    @patch('clipora.ytdlp_update.subprocess.run')
    @patch('clipora.ytdlp_update.find_executable', return_value=Path('C:/yt-dlp.exe'))
    def test_broken_executable_returns_none(self, _find, run):
        run.return_value = unittest.mock.Mock(returncode=1, stdout='', stderr='boom')
        with patch('clipora.ytdlp_update._recorded_ytdlp_version', return_value=None):
            self.assertIsNone(installed_ytdlp_version())

    @patch('clipora.ytdlp_update.subprocess.run')
    @patch('clipora.ytdlp_update.find_executable', return_value=Path('C:/yt-dlp.exe'))
    def test_broken_executable_falls_back_to_record(self, _find, run):
        run.return_value = unittest.mock.Mock(returncode=1, stdout='', stderr='boom')
        with patch('clipora.ytdlp_update._recorded_ytdlp_version', return_value='2026.06.01'):
            self.assertEqual(installed_ytdlp_version(), '2026.06.01')

    def test_record_fallback_reads_installed_json(self):
        with TemporaryDirectory() as directory:
            record = Path(directory) / 'installed.json'
            record.write_text(
                '{"schema": 1, "dependencies": {"yt-dlp": {"version": "2026.08.01"}}}',
                encoding='utf-8',
            )
            with patch('clipora.ytdlp_update.managed_tools_dir', return_value=Path(directory)):
                self.assertEqual(_recorded_ytdlp_version(), '2026.08.01')

    def test_record_fallback_ignores_missing_or_bad_file(self):
        with TemporaryDirectory() as directory:
            with patch('clipora.ytdlp_update.managed_tools_dir', return_value=Path(directory)):
                self.assertIsNone(_recorded_ytdlp_version())
            (Path(directory) / 'installed.json').write_text('not json', encoding='utf-8')
            with patch('clipora.ytdlp_update.managed_tools_dir', return_value=Path(directory)):
                self.assertIsNone(_recorded_ytdlp_version())


class LatestVersionTests(unittest.TestCase):
    @patch('clipora.ytdlp_update._fetch_https_text', return_value='{"tag_name": "2026.08.01"}')
    def test_returns_latest_tag(self, _fetch):
        self.assertEqual(latest_ytdlp_version(), '2026.08.01')

    @patch('clipora.ytdlp_update._fetch_https_text', return_value='not json')
    def test_invalid_json_raises(self, _fetch):
        with self.assertRaisesRegex(YtDlpUpdateError, 'เวอร์ชันล่าสุด'):
            latest_ytdlp_version()

    @patch('clipora.ytdlp_update._fetch_https_text', return_value='{"tag_name": 42}')
    def test_missing_tag_raises(self, _fetch):
        with self.assertRaisesRegex(YtDlpUpdateError, 'เวอร์ชันล่าสุด'):
            latest_ytdlp_version()


class UpdateTests(unittest.TestCase):
    def _run(self, root: Path):
        with patch('clipora.ytdlp_update.managed_tools_dir', return_value=root):
            with patch('clipora.ytdlp_update.latest_ytdlp_version', return_value='2026.08.01'):
                with patch('clipora.ytdlp_update._fetch_https_text', return_value=CHECKSUMS):
                    with patch(
                        'clipora.ytdlp_update._download_https_file'
                    ) as download:
                        download.side_effect = (
                            lambda _url, destination, on_fraction, _cancel=None, **_kw: destination.write_bytes(
                                b'new yt-dlp payload'
                            )
                            or on_fraction(1.0)
                        )
                        records = {}
                        with patch(
                            'clipora.ytdlp_update._write_install_record',
                            side_effect=lambda _root, specs: records.update(
                                {spec.key: spec for spec in specs}
                            ),
                        ):
                            with patch('clipora.ytdlp_update.verify_sha256'):
                                version = update_ytdlp()

        return version, records

    def test_updates_managed_executable_and_records(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'yt-dlp.exe').write_bytes(b'old payload')
            version, records = self._run(root)
            self.assertEqual(version, '2026.08.01')
            self.assertEqual((root / 'yt-dlp.exe').read_bytes(), b'new yt-dlp payload')
            self.assertFalse((root / '.yt-dlp.exe.tmp').exists())
            self.assertEqual(records['yt-dlp'].version, '2026.08.01')
            self.assertEqual(records['yt-dlp'].sha256, 'b' * 64)

    def test_failed_checksum_keeps_old_executable(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'yt-dlp.exe').write_bytes(b'old payload')
            with patch('clipora.ytdlp_update.managed_tools_dir', return_value=root):
                with patch('clipora.ytdlp_update.latest_ytdlp_version', return_value='2026.08.01'):
                    with patch('clipora.ytdlp_update._fetch_https_text', return_value=CHECKSUMS):
                        with patch(
                            'clipora.ytdlp_update._download_https_file'
                        ) as download:
                            download.side_effect = (
                                lambda _url, destination, on_fraction, _cancel=None, **_kw: destination.write_bytes(
                                    b'corrupt payload'
                                )
                                or on_fraction(1.0)
                            )
                            with self.assertRaises(DependencyInstallError):
                                update_ytdlp()
            self.assertEqual((root / 'yt-dlp.exe').read_bytes(), b'old payload')
            self.assertFalse((root / '.yt-dlp.exe.tmp').exists())

    def test_rejects_non_https_url(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('clipora.ytdlp_update.managed_tools_dir', return_value=root):
                with self.assertRaisesRegex(YtDlpUpdateError, 'HTTPS'):
                    _fetch_https_text('http://example.com')
            with self.assertRaisesRegex(YtDlpUpdateError, 'HTTPS'):
                _download_https_file('http://example.com', root / 'x.exe', lambda _v: None)


if __name__ == '__main__':
    unittest.main()