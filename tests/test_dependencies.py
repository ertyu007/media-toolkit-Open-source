import hashlib
import io
import json
import threading
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from clipora.dependencies import (
    SEPARATOR_DEPENDENCIES,
    DependencyInstallCancelled,
    DependencyInstallError,
    DependencySpec,
    install_separator_toolchain,
    install_toolchains,
    install_windows_toolchain,
    stage_dependency,
    verify_sha256,
)


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def embed_zip(pth_content: str = 'import site\n') -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(zipfile.ZipInfo('python.exe', FIXED_ZIP_TIME), b'')
        archive.writestr(
            zipfile.ZipInfo('python313._pth', FIXED_ZIP_TIME), pth_content
        )
    return buffer.getvalue()


def wheel_zip(marker_dir: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(
            zipfile.ZipInfo(f'{marker_dir}/__init__.py', FIXED_ZIP_TIME), b''
        )
    return buffer.getvalue()


def separator_specs() -> tuple[DependencySpec, ...]:
    return SEPARATOR_DEPENDENCIES


def payload_for(spec: DependencySpec) -> bytes:
    if spec.archive_type == 'raw':
        return b'model bytes'
    if spec.archive_type == 'python-embed':
        return embed_zip()
    if spec.archive_type == 'python-wheel':
        marker = 'demucs' if spec.key == 'demucs' else spec.key.replace('-', '_')
        return wheel_zip(marker)
    raise AssertionError(spec.archive_type)


def matching_specs(specs: tuple[DependencySpec, ...]) -> tuple[DependencySpec, ...]:
    return tuple(
        DependencySpec(
            key=spec.key,
            display_name=spec.display_name,
            version=spec.version,
            url=spec.url,
            sha256=hashlib.sha256(payload_for(spec)).hexdigest(),
            expected_bytes=len(payload_for(spec)),
            archive_type=spec.archive_type,
            members=spec.members,
            source_url=spec.source_url,
            license_url=spec.license_url,
        )
        for spec in specs
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


class SeparatorStagingTests(unittest.TestCase):
    def make_spec(self, archive_type: str, **overrides) -> DependencySpec:
        fields = dict(
            key='sample',
            display_name='Sample',
            version='1',
            url='https://example.com/sample',
            sha256='unused',
            expected_bytes=1,
            archive_type=archive_type,
            members=(('', 'dest'),),
            source_url='https://example.com/source',
            license_url='https://example.com/license',
        )
        fields.update(overrides)
        return DependencySpec(**fields)

    def test_python_embed_extracts_and_enables_site_packages(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'python.zip'
            archive_path.write_bytes(embed_zip())
            spec = self.make_spec('python-embed', key='python', members=(('', 'python'),))
            stage_dependency(spec, archive_path, root / 'staging')
            pth = root / 'staging' / 'python' / 'python313._pth'
            self.assertTrue(pth.is_file())
            content = pth.read_text(encoding='utf-8')
            self.assertIn('site-packages', content)
            self.assertIn('import site', content)

    def test_python_embed_requires_a_single_pth_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'python.zip'
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                archive.writestr('a._pth', '')
                archive.writestr('b._pth', '')
            archive_path.write_bytes(buffer.getvalue())
            spec = self.make_spec('python-embed', members=(('', 'python'),))
            staging = root / 'staging'
            staging.mkdir()
            with self.assertRaisesRegex(DependencyInstallError, '_pth'):
                stage_dependency(spec, archive_path, staging)

    def test_python_wheel_extracts_into_site_packages(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'torch.whl'
            archive_path.write_bytes(wheel_zip('torch'))
            spec = self.make_spec('python-wheel', members=(('', 'python/site-packages'),))
            staging = root / 'staging'
            staging.mkdir()
            stage_dependency(spec, archive_path, staging)
            self.assertTrue((staging / 'python' / 'site-packages' / 'torch' / '__init__.py').is_file())

    def test_python_embed_rejects_zip_slip_member(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'python.zip'
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                archive.writestr('../evil.txt', b'evil')
            archive_path.write_bytes(buffer.getvalue())
            spec = self.make_spec('python-embed', members=(('', 'python'),))
            staging = root / 'staging'
            staging.mkdir()
            with self.assertRaisesRegex(DependencyInstallError, 'ไม่ปลอดภัย'):
                stage_dependency(spec, archive_path, staging)
            self.assertFalse((root / 'evil.txt').exists())

    def test_python_wheel_rejects_absolute_path_member(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / 'torch.whl'
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                archive.writestr('/tmp/evil.txt', b'evil')
            archive_path.write_bytes(buffer.getvalue())
            spec = self.make_spec('python-wheel', members=(('', 'python/site-packages'),))
            staging = root / 'staging'
            staging.mkdir()
            with self.assertRaisesRegex(DependencyInstallError, 'ไม่ปลอดภัย'):
                stage_dependency(spec, archive_path, staging)
            self.assertFalse((root / 'tmp' / 'evil.txt').exists())


class SeparatorToolchainInstallTests(unittest.TestCase):
    def make_fake_download(self, root: Path):
        def fake_download(spec, destination, *_args):
            destination.write_bytes(payload_for(spec))

        return fake_download

    def test_installs_complete_separator_layout(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            specs = matching_specs(separator_specs())
            with patch('clipora.dependencies._download', side_effect=self.make_fake_download(root)):
                installed = install_separator_toolchain(destination=root, specs=specs)

            self.assertEqual(installed, specs)
            self.assertTrue((root / 'separator' / 'python' / 'python.exe').exists())
            self.assertTrue((root / 'separator' / 'python' / 'site-packages' / 'demucs').is_dir())
            self.assertTrue((root / 'separator' / 'models' / 'htdemucs_6s.th').is_file())
            record = json.loads(
                (root / 'separator' / 'installed.json').read_text(encoding='utf-8')
            )
            self.assertEqual(record['dependencies']['python']['version'], '3.13.14')
            self.assertEqual(record['dependencies']['demucs-model']['version'], '4.1.0')

    def test_install_replaces_previous_python_without_trace(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            previous = root / 'separator' / 'python'
            previous.mkdir(parents=True)
            (previous / 'old.txt').write_text('old')
            specs = matching_specs(separator_specs())
            with patch('clipora.dependencies._download', side_effect=self.make_fake_download(root)):
                install_separator_toolchain(destination=root, specs=specs)
            self.assertFalse((root / 'separator' / '.python.clipora-old').exists())
            self.assertTrue((root / 'separator' / 'python' / 'python313._pth').is_file())

    def test_missing_model_after_install_fails(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            specs = matching_specs(
                tuple(spec for spec in separator_specs() if spec.key != 'demucs-model')
            )
            with patch('clipora.dependencies._download', side_effect=self.make_fake_download(root)):
                with self.assertRaisesRegex(DependencyInstallError, 'โมเดล'):
                    install_separator_toolchain(destination=root, specs=specs)

    def test_pre_cancelled_install_does_not_download(self):
        cancelled = threading.Event()
        cancelled.set()
        with TemporaryDirectory() as directory:
            with patch('clipora.dependencies._download') as download:
                with self.assertRaises(DependencyInstallCancelled):
                    install_separator_toolchain(
                        destination=Path(directory),
                        specs=matching_specs(separator_specs()),
                        cancel_event=cancelled,
                    )
            download.assert_not_called()

    def test_install_toolchains_includes_separator_only_when_requested(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                'clipora.dependencies.install_windows_toolchain'
            ) as windows_install, patch(
                'clipora.dependencies.install_separator_toolchain'
            ) as separator_install:
                install_toolchains(destination=root)
                separator_install.assert_not_called()

                install_toolchains(destination=root, include_separator=True)
                separator_install.assert_called_once()


if __name__ == '__main__':
    unittest.main()
