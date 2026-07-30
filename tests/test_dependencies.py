import hashlib
import json
import threading
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from clipora.dependencies import (
    DependencyInstallCancelled,
    DependencyInstallError,
    DependencySpec,
    install_windows_toolchain,
    stage_dependency,
    verify_sha256,
)


def make_spec(payload: bytes = b'clipora tool') -> DependencySpec:
    return DependencySpec(
        key='sample',
        display_name='Sample tool',
        version='1.0',
        url='https://example.com/sample.exe',
        sha256=hashlib.sha256(payload).hexdigest(),
        expected_bytes=len(payload),
        archive_type='raw',
        members=(('sample.exe', 'sample.exe'),),
        source_url='https://example.com/source',
        license_url='https://example.com/license',
    )


class ChecksumTests(unittest.TestCase):
    def test_matching_checksum_passes_and_mismatch_fails(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'tool.exe'
            path.write_bytes(b'known payload')
            verify_sha256(path, hashlib.sha256(b'known payload').hexdigest())
            with self.assertRaisesRegex(DependencyInstallError, 'checksum'):
                verify_sha256(path, '0' * 64)


class ArchiveStagingTests(unittest.TestCase):
    def test_zip_extracts_only_the_named_member(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'tools.zip'
            staging = root / 'staging'
            staging.mkdir()
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr('bundle/bin/ffmpeg.exe', b'ffmpeg')
                archive.writestr('bundle/doc/readme.txt', b'ignore')
            spec = DependencySpec(
                key='ffmpeg',
                display_name='FFmpeg',
                version='1',
                url='https://example.com/ffmpeg.zip',
                sha256='unused',
                expected_bytes=1,
                archive_type='zip',
                members=(('bin/ffmpeg.exe', 'ffmpeg.exe'),),
                source_url='https://example.com/source',
                license_url='https://example.com/license',
            )

            stage_dependency(spec, archive_path, staging)

            self.assertEqual((staging / 'ffmpeg.exe').read_bytes(), b'ffmpeg')
            self.assertFalse((staging / 'readme.txt').exists())

    def test_ambiguous_member_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'tools.zip'
            staging = root / 'staging'
            staging.mkdir()
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr('one/bin/ffmpeg.exe', b'one')
                archive.writestr('two/bin/ffmpeg.exe', b'two')
            spec = DependencySpec(
                key='ffmpeg',
                display_name='FFmpeg',
                version='1',
                url='https://example.com/ffmpeg.zip',
                sha256='unused',
                expected_bytes=1,
                archive_type='zip',
                members=(('bin/ffmpeg.exe', 'ffmpeg.exe'),),
                source_url='https://example.com/source',
                license_url='https://example.com/license',
            )
            with self.assertRaisesRegex(DependencyInstallError, 'พบ 2'):
                stage_dependency(spec, archive_path, staging)


class ToolchainInstallTests(unittest.TestCase):
    def test_verified_download_is_installed_and_recorded(self):
        payload = b'clipora tool'
        spec = make_spec(payload)

        def fake_download(_spec, destination, *_args):
            destination.write_bytes(payload)

        with TemporaryDirectory() as directory:
            destination = Path(directory) / 'tools'
            with patch('clipora.dependencies._download', side_effect=fake_download):
                installed = install_windows_toolchain(destination=destination, specs=(spec,))

            self.assertEqual(installed, (spec,))
            self.assertEqual((destination / 'sample.exe').read_bytes(), payload)
            record = json.loads((destination / 'installed.json').read_text(encoding='utf-8'))
            self.assertEqual(record['dependencies']['sample']['version'], '1.0')

    def test_pre_cancelled_install_does_not_download(self):
        cancelled = threading.Event()
        cancelled.set()
        with TemporaryDirectory() as directory:
            with patch('clipora.dependencies._download') as download:
                with self.assertRaises(DependencyInstallCancelled):
                    install_windows_toolchain(
                        destination=Path(directory) / 'tools',
                        specs=(make_spec(),),
                        cancel_event=cancelled,
                    )
            download.assert_not_called()

    def test_partial_install_preserves_existing_dependency_record(self):
        payload = b'clipora tool'
        spec = make_spec(payload)

        def fake_download(_spec, destination, *_args):
            destination.write_bytes(payload)

        with TemporaryDirectory() as directory:
            destination = Path(directory) / 'tools'
            destination.mkdir()
            (destination / 'installed.json').write_text(
                json.dumps(
                    {
                        'schema': 1,
                        'dependencies': {'existing': {'version': '2.0'}},
                    }
                ),
                encoding='utf-8',
            )
            with patch('clipora.dependencies._download', side_effect=fake_download):
                install_windows_toolchain(destination=destination, specs=(spec,))

            record = json.loads((destination / 'installed.json').read_text(encoding='utf-8'))
            self.assertEqual(record['dependencies']['existing']['version'], '2.0')
            self.assertEqual(record['dependencies']['sample']['version'], '1.0')


if __name__ == '__main__':
    unittest.main()
