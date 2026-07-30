import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from clipora.ui import format_file_size, source_summary


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


if __name__ == '__main__':
    unittest.main()
