import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from clipora import __version__
from clipora.dependencies import WINDOWS_X64_DEPENDENCIES


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
            'scripts/build_windows.ps1',
            'THIRD_PARTY_NOTICES.md',
        )
        for relative in required:
            with self.subTest(path=relative):
                self.assertTrue((PROJECT_ROOT / relative).is_file())


if __name__ == '__main__':
    unittest.main()
