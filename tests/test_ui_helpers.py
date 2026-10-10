import re
import tkinter as tk
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from clipora.history import HistoryEntry
from clipora.ui import (
    CliporaApp,
    classify_source_text,
    destination_path,
    find_clipora_uninstaller,
    find_history_index,
    format_debug_line,
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


class HistorySelectionTests(unittest.TestCase):
    def make_entry(self, entry_id, target='out/a.mp3'):
        return HistoryEntry(
            id=entry_id, finished_at=0.0, kind='audio',
            source_kind='url', name='a.mp3', target=target,
        )

    def test_finds_entry_by_id(self):
        entries = [self.make_entry('a'), self.make_entry('b')]
        self.assertEqual(find_history_index(entries, 'b'), 1)

    def test_falls_back_to_target_path(self):
        entries = [self.make_entry('a', target='out/a.mp3')]
        self.assertEqual(find_history_index(entries, 'out/a.mp3'), 0)

    def test_unknown_or_empty_selection_returns_none(self):
        entries = [self.make_entry('a')]
        self.assertIsNone(find_history_index(entries, 'missing'))
        self.assertIsNone(find_history_index(entries, None))
        self.assertIsNone(find_history_index([], 'a'))


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


class SourceClassifyTests(unittest.TestCase):
    def test_public_url_is_url(self):
        self.assertEqual(
            classify_source_text('https://www.youtube.com/watch?v=abc12345678'), 'url')

    def test_existing_file_is_file(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'คลิป.mp4'
            target.write_bytes(b'x')
            self.assertEqual(classify_source_text(str(target)), 'file')
            self.assertEqual(classify_source_text(f'"{target}"'), 'file')

    def test_unsure_keeps_mode(self):
        self.assertIsNone(classify_source_text(''))
        self.assertIsNone(classify_source_text('   '))
        self.assertIsNone(classify_source_text('just some text'))
        self.assertIsNone(classify_source_text('C:\\no\\such\\file.mp4'))
        self.assertIsNone(classify_source_text('http://127.0.0.1/video.mp4'))
        with TemporaryDirectory() as directory:
            self.assertIsNone(classify_source_text(directory))


class DebugLineTests(unittest.TestCase):
    def test_formats_timestamp_and_message(self):
        line = format_debug_line(datetime(2026, 9, 28, 20, 5, 9), 'เฟส: กำลังดาวน์โหลด')
        self.assertEqual(line, '[20:05:09] เฟส: กำลังดาวน์โหลด')


class UninstallerTests(unittest.TestCase):
    def test_finds_uninstaller_next_to_exe(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'unins000.exe'
            target.write_bytes(b'x')
            self.assertEqual(find_clipora_uninstaller(Path(directory)), target)

    def test_missing_uninstaller_returns_none(self):
        with TemporaryDirectory() as directory:
            self.assertIsNone(find_clipora_uninstaller(Path(directory)))


class NoEmojiCopyTests(unittest.TestCase):
    def test_no_color_emoji_in_product_code(self):
        forbidden = re.compile('[\U0001F000-\U0001FAFF]')
        offenders = []
        root = Path(__file__).resolve().parents[1] / 'clipora'
        for path in sorted(root.rglob('*.py')):
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if forbidden.search(line):
                    offenders.append(f'{path.name}:{number}')
        self.assertEqual(offenders, [])


class UiCallbackTests(unittest.TestCase):
    def test_post_to_ui_ignores_destroyed_tk_interpreter(self):
        class DestroyedWindow:
            @staticmethod
            def after(*_args):
                raise tk.TclError('application has been destroyed')

        CliporaApp._post_to_ui(DestroyedWindow(), lambda: None)


class StemFriendlyTests(unittest.TestCase):
    def _make_app(self):
        try:
            from clipora.ui import CliporaApp

            app = CliporaApp()
            app.withdraw()
            app.update()
        except Exception as exc:
            self.skipTest(f'no display: {exc}')
        self.addCleanup(app._on_close)
        return app

    def test_empty_stems_selection_fails_validation(self):
        app = self._make_app()
        app.mode.set('stems')
        for var in app.stem_vars.values():
            var.set(False)
        app.update()
        self.assertFalse(app._validate_stems())

    def test_enhance_switch_tracks_vocals_selection(self):
        app = self._make_app()
        app.mode.set('stems')
        app.stem_vars['vocals'].set(True)
        app.update()
        self.assertTrue(app.enhance_check._enabled)
        app.stem_vars['vocals'].set(False)
        app.update()
        self.assertFalse(app.enhance_check._enabled)


if __name__ == '__main__':
    unittest.main()
