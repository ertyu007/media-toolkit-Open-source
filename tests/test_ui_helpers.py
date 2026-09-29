import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from clipora.ui import (
    destination_path,
    format_file_size,
    route_dropped_paths,
    source_summary,
)


class FileSummaryTests(unittest.TestCase):
    def test_formats_file_sizes(self):
        self.assertEqual(format_file_size(0), '0 B')
        self.assertEqual(format_file_size(1024), '1.0 KB')
        self.assertEqual(format_file_size(5 * 1024 * 1024), '5.0 MB')

    def test_empty_source_has_idle_summary(self):
        self.assertEqual(source_summary(''), 'ยังไม่ได้เลือกไฟล์')

    def test_existing_unicode_file_shows_name_and_size(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'คลิป ทดสอบ.mp4'
            source.write_bytes(b'clipora')

            summary = source_summary(str(source))

            self.assertIn(source.name, summary)
            self.assertIn('7 B', summary)

    def test_missing_source_has_recovery_message(self):
        self.assertIn('ไม่พบไฟล์', source_summary('missing-video.mp4'))


class DestinationValidationTests(unittest.TestCase):
    def test_empty_destination_is_rejected_not_treated_as_cwd(self):
        with self.assertRaisesRegex(ValueError, 'โฟลเดอร์บันทึก'):
            destination_path('')

    def test_whitespace_destination_is_rejected(self):
        with self.assertRaises(ValueError):
            destination_path('   ')

    def test_trimmed_destination_is_returned(self):
        self.assertEqual(destination_path('  C:\\Videos  '), Path('C:\\Videos'))


class DropRoutingTests(unittest.TestCase):
    def test_file_routes_to_source(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'คลิป.mp4'
            target.write_bytes(b'x')
            self.assertEqual(
                route_dropped_paths([str(target)]), ('source', str(target)))
    def test_directory_routes_to_destination(self):
        with TemporaryDirectory() as directory:
            self.assertEqual(
                route_dropped_paths([directory]), ('destination', directory))
    def test_file_wins_over_directory(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'a.mp3'
            target.write_bytes(b'x')
            self.assertEqual(
                route_dropped_paths([directory, str(target)]),
                ('source', str(target)))
    def test_missing_paths_route_nowhere(self):
        self.assertIsNone(route_dropped_paths(['C:\\no\\such\\file.mp4']))
        self.assertIsNone(route_dropped_paths([]))
if __name__ == '__main__':
    unittest.main()
