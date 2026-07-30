import unittest

from clipora.dependencies import DependencySpec
from clipora.setup_ui import dependency_rows, total_download_mb


def sample_spec(name: str, size_mb: int) -> DependencySpec:
    return DependencySpec(
        key=name.lower(),
        display_name=name,
        version='1.2.3',
        url='https://example.com/tool.exe',
        sha256='0' * 64,
        expected_bytes=size_mb * 1024 * 1024,
        archive_type='raw',
        members=(('tool.exe', 'tool.exe'),),
        source_url='https://example.com/source',
        license_url='https://example.com/license',
    )


class SetupSummaryTests(unittest.TestCase):
    def test_dependency_rows_show_name_version_and_rounded_size(self):
        rows = dependency_rows((sample_spec('FFmpeg', 110),))
        self.assertEqual(rows, ('FFmpeg 1.2.3  •  110 MB',))

    def test_total_download_mb_sums_selected_dependencies(self):
        specs = (sample_spec('One', 110), sample_spec('Two', 18))
        self.assertEqual(total_download_mb(specs), 128)

    def test_empty_plan_has_zero_size_and_no_rows(self):
        self.assertEqual(dependency_rows(()), ())
        self.assertEqual(total_download_mb(()), 0)


if __name__ == '__main__':
    unittest.main()
