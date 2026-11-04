import re
import tkinter as tk
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from clipora.ffmpeg import CancellationToken, ConversionCancelled
from clipora.history import HistoryEntry
from clipora.importer import URLImportError
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


class _AppTestCase(unittest.TestCase):
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


class UiSmokeTests(_AppTestCase):
    def test_mode_switch_toggles_option_rows(self):
        app = self._make_app()
        app.input_kind.set('file')

        app._on_mode_change('audio')
        app.update()
        self.assertTrue(app.format_box.winfo_manager())
        self.assertFalse(app.video_format_box.winfo_manager())
        self.assertFalse(app._stems_options.winfo_manager())

        app._on_mode_change('video')
        app.update()
        self.assertFalse(app.format_box.winfo_manager())
        self.assertTrue(app.video_format_box.winfo_manager())
        self.assertFalse(app._stems_options.winfo_manager())

        app._on_mode_change('stems')
        app.update()
        self.assertTrue(app.format_box.winfo_manager())
        self.assertFalse(app.video_format_box.winfo_manager())
        self.assertTrue(app._stems_options.winfo_manager())

    def test_trim_row_follows_mode_and_source_kind(self):
        app = self._make_app()
        app.input_kind.set('file')
        app.mode.set('stems')
        app._sync_options()
        app.update()
        self.assertFalse(app._trim_options.winfo_manager())

        app.input_kind.set('url')
        app._sync_options()
        app.update()
        self.assertTrue(app._trim_options.winfo_manager())

    def test_builds_at_common_display_scalings(self):
        app = self._make_app()
        for factor in (1.0, 1.25, 1.5):
            app.tk.call('tk', 'scaling', factor)
            app.update()
            self.assertAlmostEqual(
                float(app.tk.call('tk', 'scaling')), factor, places=2)
            self.assertTrue(app.start_button.winfo_exists())


class HardwareToggleUiTests(_AppTestCase):
    def _video_app(self):
        app = self._make_app()
        app._details_expanded = True
        app.input_kind.set('file')
        app._sync_source_kind()
        app._on_mode_change('video')
        app.update()
        return app

    def test_hardware_row_visible_only_for_local_video(self):
        app = self._video_app()
        self.assertTrue(app._hardware_row.winfo_manager())
        self.assertIn(app.hardware_check, app._input_widgets)

        app._on_mode_change('audio')
        app.update()
        self.assertFalse(app._hardware_row.winfo_manager())

        app._on_mode_change('stems')
        app.update()
        self.assertFalse(app._hardware_row.winfo_manager())

        app._on_mode_change('video')
        app.input_kind.set('url')
        app._sync_source_kind()
        app.update()
        self.assertFalse(app._hardware_row.winfo_manager())

        app.input_kind.set('file')
        app._sync_source_kind()
        app.update()
        self.assertTrue(app._hardware_row.winfo_manager())

    def test_start_local_snapshots_hardware_flag(self):
        app = self._video_app()
        app.hardware_encode.set(True)
        app._chime_var.set(False)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'clip.mp4'
            source.write_bytes(b'clip')
            app.source.set(str(source))
            app.destination.set(str(root))
            _RecordingThread.instances = []
            with patch('clipora.ui.threading.Thread', _RecordingThread), \
                    patch('clipora.ui.tools_available', return_value=True), \
                    patch(
                        'clipora.ui.hardware_h264_encoder',
                        return_value='h264_nvenc',
                    ):
                app._start_local()
            worker = _RecordingThread.instances[-1]
            self.assertEqual(worker.target.__func__.__name__, '_run_local')
            self.assertTrue(worker.args[0].hardware)
            app._finish_job(app._cancellation)
        app.update()

    def test_start_local_batch_passes_hardware_flag(self):
        app = self._video_app()
        app.hardware_encode.set(True)
        app._chime_var.set(False)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = []
            for name in ('one.mp4', 'two.mp4'):
                source = root / name
                source.write_bytes(b'clip')
                sources.append(source)
            app.source.set(str(sources[0]))
            app._selected_local_sources = tuple(sources)
            app.destination.set(str(root))
            _RecordingThread.instances = []
            with patch('clipora.ui.threading.Thread', _RecordingThread), \
                    patch('clipora.ui.tools_available', return_value=True), \
                    patch(
                        'clipora.ui.hardware_h264_encoder',
                        return_value='h264_nvenc',
                    ):
                app._start_local()
            worker = _RecordingThread.instances[-1]
            self.assertEqual(worker.target.__func__.__name__, '_run_local_batch')
            items = worker.args[0]
            self.assertEqual(len(items), 2)
            self.assertTrue(all(job.hardware for job, _target in items))
            app._finish_job(app._cancellation)
        app.update()

    def test_hardware_defaults_to_off(self):
        app = self._video_app()
        self.assertFalse(app.hardware_encode.get())


class StemFriendlyTests(_AppTestCase):
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


class _RecordingThread:
    """Stand-in for threading.Thread: records the worker without starting it."""

    instances = []

    def __init__(self, target=None, args=(), daemon=None, **kwargs):
        self.target = target
        self.args = tuple(args)
        self.daemon = daemon
        self.started = False
        _RecordingThread.instances.append(self)

    def start(self):
        self.started = True


LINK_A = 'https://example.com/a'
LINK_B = 'https://example.com/b'
LINK_C = 'https://example.com/c'


class UrlQueueUiTests(_AppTestCase):
    def _make_url_app(self):
        app = self._make_app()
        app.input_kind.set('url')
        app._sync_source_kind()
        app.mode.set('audio')
        app._sync_options()
        return app

    def _queue_specs(self, app, urls, destination):
        return tuple(
            app._build_import_spec(url, destination, None, None) for url in urls
        )

    def test_add_remove_and_clear_queue(self):
        app = self._make_url_app()
        app.source.set(LINK_A)

        app._add_current_url_to_queue()
        app.update()
        self.assertEqual(app._url_queue, [LINK_A])
        self.assertEqual(app._url_queue_count.cget('text'), 'คิว 1 ลิงก์')
        self.assertEqual(app._url_queue_listbox.size(), 1)
        self.assertEqual(app._url_queue_listbox.get(0), LINK_A)
        self.assertEqual(app._url_queue_listbox.curselection(), (0,))
        self.assertEqual(app.source.get(), LINK_A)
        self.assertFalse(app._url_queue_hint.winfo_manager())

        app.source.set(LINK_B)
        app._add_current_url_to_queue()
        app.update()
        self.assertEqual(app._url_queue, [LINK_A, LINK_B])
        self.assertEqual(app._url_queue_count.cget('text'), 'คิว 2 ลิงก์')

        app._url_queue_listbox.selection_clear(0, 'end')
        app._url_queue_listbox.selection_set(1)
        app._remove_selected_url()
        app.update()
        self.assertEqual(app._url_queue, [LINK_A])

        app._clear_url_queue()
        app.update()
        self.assertEqual(app._url_queue, [])
        self.assertEqual(app._url_queue_count.cget('text'), 'ยังไม่มีลิงก์ในคิว')
        self.assertTrue(app._url_queue_hint.winfo_manager())

    def test_duplicate_link_is_not_added_twice(self):
        app = self._make_url_app()
        app.source.set(LINK_A)
        app._add_current_url_to_queue()

        app.source.set(LINK_A.upper())
        app._add_current_url_to_queue()
        app.update()

        self.assertEqual(app._url_queue, [LINK_A])
        self.assertTrue(app._source_error.is_visible())
        self.assertIn('อยู่ในคิว', app._source_error._label.cget('text'))

    def test_invalid_link_shows_inline_error(self):
        app = self._make_url_app()
        app.source.set('ftp://example.com/file.mp4')

        app._add_current_url_to_queue()
        app.update()

        self.assertEqual(app._url_queue, [])
        self.assertTrue(app._source_error.is_visible())
        self.assertIn('http', app._source_error._label.cget('text'))

    def test_queue_panel_visible_only_in_url_mode(self):
        app = self._make_app()
        app.mode.set('audio')
        app._sync_options()
        app.input_kind.set('file')
        app._sync_source_kind()
        app.update()
        self.assertFalse(app._url_queue_frame.winfo_manager())

        app.input_kind.set('url')
        app._sync_source_kind()
        app.update()
        self.assertTrue(app._url_queue_frame.winfo_manager())

    def test_queue_panel_hidden_in_stems_and_restored_after_switch(self):
        app = self._make_url_app()
        app._url_queue = [LINK_A, LINK_B]
        app._refresh_url_queue()
        app.update()
        self.assertTrue(app._url_queue_frame.winfo_manager())

        app.mode.set('stems')
        app._sync_options()
        app.update()
        self.assertFalse(app._url_queue_frame.winfo_manager())

        app.mode.set('audio')
        app._sync_options()
        app.update()
        self.assertTrue(app._url_queue_frame.winfo_manager())
        self.assertEqual(app._url_queue, [LINK_A, LINK_B])
        self.assertEqual(app._url_queue_listbox.size(), 2)
        self.assertEqual(app._url_queue_count.cget('text'), 'คิว 2 ลิงก์')

    def test_queue_selection_survives_mode_switch(self):
        app = self._make_url_app()
        app._url_queue = [LINK_A, LINK_B, LINK_C]
        app._refresh_url_queue()
        app.update()
        app._url_queue_listbox.selection_clear(0, 'end')
        app._url_queue_listbox.selection_set(1)
        app.update()

        app.mode.set('video')
        app._sync_options()
        app.update()
        self.assertEqual(app._url_queue_listbox.curselection(), (1,))
        self.assertEqual(app._url_queue_listbox.get(1), LINK_B)
        self.assertEqual(app._url_queue_count.cget('text'), 'คิว 3 ลิงก์')

        app.mode.set('audio')
        app._sync_options()
        app.update()
        self.assertEqual(app._url_queue_listbox.curselection(), (1,))
        self.assertEqual(app._url_queue_listbox.size(), 3)

    def test_queue_widgets_lock_during_job(self):
        app = self._make_url_app()
        app._set_inputs_enabled(False)
        app.update()
        self.assertEqual(str(app._url_queue_listbox.cget('state')), 'disabled')
        self.assertFalse(app._url_queue_add_button._enabled)

        app._set_inputs_enabled(True)
        app.update()
        self.assertEqual(str(app._url_queue_listbox.cget('state')), 'normal')
        self.assertTrue(app._url_queue_add_button._enabled)

    def test_start_url_from_queue_builds_frozen_specs(self):
        app = self._make_url_app()
        app.source.set('')
        app._url_queue = [LINK_A, LINK_B]
        app._refresh_url_queue()
        app.mode.set('video')
        app._sync_options()
        app.video_format.set('MOV  •  ProRes')
        app.quality.set('1080p')
        app.fps.set('60fps')
        app.enhance_audio.set(True)
        app.start_time_entry.insert('end', '1:00')
        app.duration_entry.insert('end', '30')
        app.authorized.set(True)
        self.assertTrue(app._validate_source())

        _RecordingThread.instances = []
        with patch('clipora.ui.threading.Thread', _RecordingThread), \
                patch('clipora.ui.tools_available', return_value=True), \
                patch('clipora.ui.ytdlp_available', return_value=True):
            app._start_url()

        self.assertEqual(len(_RecordingThread.instances), 1)
        worker = _RecordingThread.instances[0]
        self.assertEqual(worker.target.__func__.__name__, '_run_url_queue')
        specs = worker.args[0]
        self.assertIsInstance(specs, tuple)
        self.assertEqual(tuple(spec.url for spec in specs), (LINK_A, LINK_B))
        spec = specs[0]
        self.assertEqual(spec.mode, 'video')
        self.assertEqual(spec.quality, '1080p')
        self.assertEqual(spec.video_format, 'mov')
        self.assertEqual(spec.fps, '60')
        self.assertTrue(spec.enhance)
        self.assertAlmostEqual(spec.trim_start, 60.0)
        self.assertAlmostEqual(spec.trim_duration, 30.0)
        # The queue survives the snapshot untouched.
        self.assertEqual(app._url_queue, [LINK_A, LINK_B])
        self.assertEqual(app._url_queue_listbox.size(), 2)
        app._finish_job(app._cancellation)

    def test_start_url_with_empty_queue_uses_single_link_flow(self):
        app = self._make_url_app()
        app.source.set(LINK_A)
        app.authorized.set(True)

        _RecordingThread.instances = []
        with patch('clipora.ui.threading.Thread', _RecordingThread), \
                patch('clipora.ui.tools_available', return_value=True), \
                patch('clipora.ui.ytdlp_available', return_value=True):
            app._start_url()

        worker = _RecordingThread.instances[0]
        self.assertEqual(worker.target.__func__.__name__, '_run_import')
        self.assertEqual(worker.args[0].url, LINK_A)
        app._finish_job(app._cancellation)

    def test_queue_worker_success_records_history_removes_done_links(self):
        app = self._make_url_app()
        urls = [LINK_A, LINK_B]
        app._url_queue = list(urls)
        app._refresh_url_queue()
        app._chime_var.set(False)
        history = []
        app._record_history = lambda targets, source_by_target=None: history.append(
            (list(targets), dict(source_by_target or {})))
        app._post_to_ui = lambda callback, *args: callback(*args)
        cancellation = CancellationToken()
        app._cancellation = cancellation

        with TemporaryDirectory() as directory:
            destination = Path(directory)
            specs = self._queue_specs(app, urls, destination)
            calls = []
            overall = []

            def fake_import(spec, on_progress, cancellation, on_conflict=None,
                            on_detail=None):
                calls.append(spec.url)
                on_progress(0.5)
                overall.append(float(app.progress['value']))
                on_progress(1.0)
                target = destination / f'{Path(spec.url).name}.mp3'
                target.write_bytes(b'x')
                return target

            with patch('clipora.ui.import_url', fake_import):
                app._run_url_queue(specs, cancellation)

        self.assertEqual(calls, urls)
        self.assertEqual(overall, [25.0, 75.0])
        self.assertEqual(app._url_queue, [])
        self.assertEqual(len(history), 1)
        targets, by_source = history[0]
        self.assertEqual(len(targets), 2)
        self.assertEqual(by_source[targets[0]], LINK_A)
        self.assertEqual(by_source[targets[1]], LINK_B)
        self.assertEqual(app._result_targets, targets)
        self.assertIn('ดาวน์โหลดเสร็จ 2 ลิงก์', app.status.get())

    def test_queue_worker_failure_stops_and_keeps_failed_links(self):
        app = self._make_url_app()
        urls = [LINK_A, LINK_B, LINK_C]
        app._url_queue = list(urls)
        app._refresh_url_queue()
        app._chime_var.set(False)
        history = []
        app._record_history = lambda targets, source_by_target=None: history.append(
            (list(targets), dict(source_by_target or {})))
        app._post_to_ui = lambda callback, *args: callback(*args)
        cancellation = CancellationToken()
        app._cancellation = cancellation

        with TemporaryDirectory() as directory:
            destination = Path(directory)
            specs = self._queue_specs(app, urls, destination)
            calls = []

            def fake_import(spec, on_progress, cancellation, on_conflict=None,
                            on_detail=None):
                calls.append(spec.url)
                if spec.url == LINK_B:
                    raise URLImportError('ทดสอบดาวน์โหลดล้มเหลว')
                target = destination / f'{Path(spec.url).name}.mp3'
                target.write_bytes(b'x')
                return target

            with patch('clipora.ui.import_url', fake_import), \
                    patch('clipora.ui.ErrorDialog') as dialog:
                app._run_url_queue(specs, cancellation)

        self.assertEqual(calls, [LINK_A, LINK_B])
        # Failed and unprocessed links stay queued for retry.
        self.assertEqual(app._url_queue, [LINK_B, LINK_C])
        self.assertEqual(len(history), 1)
        self.assertEqual(len(history[0][0]), 1)
        dialog.assert_called_once()
        message = dialog.call_args.args[2]
        self.assertIn(LINK_B, message)
        self.assertIn('สำเร็จแล้ว 1', message)

    def test_queue_worker_cancellation_keeps_remaining_links(self):
        app = self._make_url_app()
        urls = [LINK_A, LINK_B]
        app._url_queue = list(urls)
        app._refresh_url_queue()
        app._chime_var.set(False)
        app._post_to_ui = lambda callback, *args: callback(*args)
        cancellation = CancellationToken()
        app._cancellation = cancellation

        with TemporaryDirectory() as directory:
            destination = Path(directory)
            specs = self._queue_specs(app, urls, destination)
            calls = []

            def fake_import(spec, on_progress, cancellation, on_conflict=None,
                            on_detail=None):
                calls.append(spec.url)
                raise ConversionCancelled('ยกเลิกงานแล้ว')

            with patch('clipora.ui.import_url', fake_import), \
                    patch('clipora.ui.ErrorDialog') as dialog:
                app._run_url_queue(specs, cancellation)

        self.assertEqual(calls, [LINK_A])
        self.assertEqual(app._url_queue, urls)
        self.assertIn('ยกเลิก', app.status.get())
        dialog.assert_not_called()

    def test_queue_progress_text_uses_aggregate_percent_and_keeps_prefix(self):
        app = self._make_url_app()
        urls = [LINK_A, LINK_B]
        app._url_queue = list(urls)
        app._refresh_url_queue()
        app._chime_var.set(False)
        app._post_to_ui = lambda callback, *args: callback(*args)
        cancellation = CancellationToken()
        app._cancellation = cancellation
        app._record_history = lambda *args, **kwargs: None
        seen = []

        with TemporaryDirectory() as directory:
            destination = Path(directory)
            specs = self._queue_specs(app, urls, destination)

            def fake_import(spec, on_progress, cancellation, on_conflict=None,
                            on_detail=None):
                seen.append(
                    ('start', app.progress_text.get(), float(app.progress['value']))
                )
                on_progress(0.5)
                seen.append(
                    ('half', app.progress_text.get(), float(app.progress['value']))
                )
                if on_detail is not None:
                    on_detail('2MiB/s', '10s')
                    seen.append(
                        ('detail', app.progress_text.get(),
                         float(app.progress['value']))
                    )
                target = destination / f'{Path(spec.url).name}.mp3'
                target.write_bytes(b'x')
                return target

            with patch('clipora.ui.import_url', fake_import):
                app._run_url_queue(specs, cancellation)

        self.assertEqual(seen[0], ('start', '1/2 • 0%', 0.0))
        self.assertEqual(seen[1], ('half', '1/2 • 25%', 25.0))
        self.assertEqual(
            seen[2],
            ('detail', '1/2 • 25%  •  2MiB/s  •  เหลือ 10s', 25.0),
        )
        self.assertEqual(seen[3], ('start', '2/2 • 50%', 50.0))
        self.assertEqual(seen[4], ('half', '2/2 • 75%', 75.0))
        self.assertEqual(app._queue_progress, None)

    def test_single_url_progress_detail_keeps_plain_format(self):
        app = self._make_url_app()
        cancellation = CancellationToken()
        app._cancellation = cancellation
        app.progress['value'] = 42

        app._queue_progress = None
        app._set_download_detail(cancellation, '1MiB/s', '5s')
        self.assertEqual(app.progress_text.get(), '42%  •  1MiB/s  •  เหลือ 5s')

        app._queue_progress = (2, 3)
        app._set_download_detail(cancellation, '1MiB/s', '5s')
        self.assertEqual(
            app.progress_text.get(), '2/3 • 42%  •  1MiB/s  •  เหลือ 5s')
        app._cancellation = None


if __name__ == '__main__':
    unittest.main()
