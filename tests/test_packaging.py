import importlib
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from clipora import __version__
from clipora.dependencies import WINDOWS_X64_DEPENDENCIES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class PackagingConfigurationTests(unittest.TestCase):
    def test_version_is_synchronized_with_packaging_metadata(self):
        inno = (PROJECT_ROOT / 'packaging' / 'clipora.iss').read_text(encoding='utf-8')
        version_info = (PROJECT_ROOT / 'packaging' / 'version_info.txt').read_text(
            encoding='utf-8'
        )
        version_tuple = ', '.join(__version__.split('.')) + ', 0'

        self.assertIn(f'#define AppVersion "{__version__}"', inno)
        self.assertIn(f'filevers=({version_tuple})', version_info)
        self.assertIn(f"StringStruct(u'ProductVersion', u'{__version__}')", version_info)

    def test_dependency_manifest_uses_pinned_https_assets(self):
        destinations = []
        for spec in WINDOWS_X64_DEPENDENCIES:
            with self.subTest(spec=spec.key):
                self.assertEqual(urlsplit(spec.url).scheme, 'https')
                self.assertRegex(spec.sha256, re.compile(r'^[0-9a-f]{64}$'))
                self.assertGreater(spec.expected_bytes, 0)
                self.assertFalse('latest' in spec.url.lower())
                destinations.extend(spec.destination_names)
        self.assertEqual(len(destinations), len(set(destinations)))

    def test_release_workflow_and_build_files_exist(self):
        required = (
            '.github/workflows/release.yml',
            'packaging/clipora.spec',
            'packaging/clipora.iss',
            'packaging/clipora.manifest',
            'scripts/build_windows.ps1',
            'scripts/sign_windows.ps1',
            'scripts/stage_bundled_tools.py',
            'docs/CODE_SIGNING.md',
            'THIRD_PARTY_NOTICES.md',
        )
        for relative in required:
            with self.subTest(path=relative):
                self.assertTrue((PROJECT_ROOT / relative).is_file())

    def test_application_manifest_is_standard(self):
        manifest = (PROJECT_ROOT / 'packaging' / 'clipora.manifest').read_text(encoding='utf-8')
        self.assertIn('requestedExecutionLevel', manifest)
        self.assertIn('asInvoker', manifest)
        self.assertIn('longPathAware', manifest)
        self.assertIn('supportedOS', manifest)

    def test_installer_has_professional_version_metadata(self):
        inno = (PROJECT_ROOT / 'packaging' / 'clipora.iss').read_text(encoding='utf-8')
        self.assertIn('VersionInfoProductName', inno)
        self.assertIn('UninstallDisplayName', inno)
        self.assertIn('AppCopyright', inno)
        self.assertIn('SetupLogging=yes', inno)

    def test_staging_script_imports_and_stages_pinned_specs(self):
        module = importlib.import_module('stage_bundled_tools')
        self.assertTrue(callable(getattr(module, 'main', None)))
        self.assertIs(module.WINDOWS_X64_DEPENDENCIES, WINDOWS_X64_DEPENDENCIES)
        for spec in module.WINDOWS_X64_DEPENDENCIES:
            self.assertTrue(spec.destination_names)


if __name__ == '__main__':
    unittest.main()
