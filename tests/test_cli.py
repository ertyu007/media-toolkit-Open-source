import io
import json
import signal
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from clipora import cli
from clipora.ffmpeg import (
    CancellationToken,
    ConversionCancelled,
    FFmpegError,
    JobSpec,
)
from clipora.importer import ImportSpec, URLImportError


class CLITestCase(unittest.TestCase):
    """Shared helpers: run ``main`` with captured streams and no real console."""

    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    @staticmethod
    def make_source(directory: Path, name: str = 'clip.mp4') -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / name
        source.write_bytes(b'source')
        return source

    @staticmethod
    def progress_side_effect(phase: str = 'converting', value: float = 50.0):
        def fake(job, target, token, overwrite=False, on_progress=None):
            if on_progress is not None:
                on_progress(phase, value)

        return fake


class ParserTests(CLITestCase):
    def test_help_lists_both_subcommands(self):
        code, stdout, _stderr = self.run_cli(['--help'])
        self.assertEqual(code, 0)
        self.assertIn('convert', stdout)
        self.assertIn('download', stdout)

    def test_subcommand_help_works(self):
        code, stdout, _stderr = self.run_cli(['convert', '--help'])
        self.assertEqual(code, 0)
        self.assertIn('--trim-start', stdout)
        self.assertIn('FILE', stdout)

    def test_missing_command_is_usage_error(self):
        code, _stdout, stderr = self.run_cli([])
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn('ข้อผิดพลาด', stderr)

    def test_unknown_option_is_usage_error(self):
        with TemporaryDirectory() as directory:
            source = self.make_source(Path(directory))
            code, _stdout, stderr = self.run_cli(
                ['convert', str(source), '--nope']
            )
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn('ข้อผิดพลาด', stderr)

    def test_convert_without_files_is_usage_error(self):
        code, _stdout, _stderr = self.run_cli(['convert'])
        self.assertEqual(code, cli.EXIT_USAGE)

    def test_download_without_urls_is_usage_error(self):
        code, _stdout, _stderr = self.run_cli(['download'])
        self.assertEqual(code, cli.EXIT_USAGE)

    def test_resolve_formats_defaults_to_audio_mp3(self):
        selection = cli.resolve_formats(None, None)
        self.assertEqual(selection.mode, 'audio')
        self.assertEqual(selection.audio_format, 'mp3')
        self.assertEqual(selection.video_format, 'mp4')

    def test_resolve_formats_infers_video_from_container(self):
        selection = cli.resolve_formats(None, 'mov')
        self.assertEqual(selection.mode, 'video')
        self.assertEqual(selection.video_format, 'mov')

    def test_resolve_formats_infers_audio_from_format(self):
        selection = cli.resolve_formats(None, 'flac')
        self.assertEqual(selection.mode, 'audio')
        self.assertEqual(selection.audio_format, 'flac')

    def test_resolve_formats_rejects_mode_format_mismatch(self):
        with self.assertRaises(cli.UsageError):
            cli.resolve_formats('video', 'mp3')
        with self.assertRaises(cli.UsageError):
            cli.resolve_formats('audio', 'mp4')

    def test_mode_format_mismatch_is_usage_error(self):
        with TemporaryDirectory() as directory:
            source = self.make_source(Path(directory))
            code, _stdout, stderr = self.run_cli(
                ['convert', str(source), '--mode', 'video', '--format', 'mp3']
            )
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn('mp3', stderr)
        self.assertIn('video', stderr)

    def test_invalid_trim_is_usage_error(self):
        with TemporaryDirectory() as directory:
            source = self.make_source(Path(directory))
            code, _stdout, stderr = self.run_cli(
                ['convert', str(source), '--trim-start', 'abc']
            )
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn('รูปแบบเวลาไม่ถูกต้อง', stderr)

    def test_non_positive_trim_duration_is_usage_error(self):
        with TemporaryDirectory() as directory:
            source = self.make_source(Path(directory))
            code, _stdout, _stderr = self.run_cli(
                ['convert', str(source), '--trim-duration', '0']
            )
        self.assertEqual(code, cli.EXIT_USAGE)

    def test_output_dir_that_is_a_file_is_usage_error(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            blocker = root / 'not-a-dir'
            blocker.write_bytes(b'x')
            code, _stdout, stderr = self.run_cli(
                ['convert', str(source), '--output-dir', str(blocker)]
            )
        self.assertEqual(code, cli.EXIT_USAGE)
        self.assertIn('โฟลเดอร์ปลายทาง', stderr)

    def test_invalid_url_is_usage_error(self):
        code, _stdout, _stderr = self.run_cli(
            ['download', 'ftp://example.com/video.mp4']
        )
        self.assertEqual(code, cli.EXIT_USAGE)

    def test_invalid_url_does_not_create_output_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / 'new' / 'out'
            code, _stdout, _stderr = self.run_cli([
                'download', 'ftp://example.com/video.mp4',
                '--output-dir', str(output_dir),
            ])
            self.assertEqual(code, cli.EXIT_USAGE)
            self.assertFalse(output_dir.exists())
            self.assertFalse((root / 'new').exists())

    def test_invalid_trim_does_not_create_output_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            output_dir = root / 'new' / 'out'
            code, _stdout, _stderr = self.run_cli([
                'convert', str(source),
                '--trim-start', 'abc',
                '--output-dir', str(output_dir),
            ])
            self.assertEqual(code, cli.EXIT_USAGE)
            self.assertFalse(output_dir.exists())

    def test_keyboard_interrupt_during_validation_exits_130(self):
        with patch('clipora.cli._validate_args', side_effect=KeyboardInterrupt):
            code, stdout, stderr = self.run_cli(['convert', 'anything.mp4'])
        self.assertEqual(code, cli.EXIT_CANCELLED)
        self.assertEqual(stdout, '')
        self.assertIn('ยกเลิกทันที', stderr)
        self.assertNotIn('Traceback', stderr)


class ConvertTests(CLITestCase):
    def test_convert_defaults_to_audio_mp3_next_to_source(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            with patch('clipora.cli.run_local_conversion') as run:
                code, stdout, stderr = self.run_cli(['convert', str(source)])

            self.assertEqual(code, cli.EXIT_OK)
            self.assertEqual(run.call_count, 1)
            job = run.call_args.args[0]
            target = run.call_args.args[1]
            self.assertEqual(target, root / 'clip_audio.mp3')
            self.assertEqual(job, JobSpec(
                source=source,
                destination=target,
                mode='audio',
                quality='Balanced',
                audio_format='mp3',
            ))
            self.assertFalse(run.call_args.kwargs['overwrite'])
            self.assertIn('สำเร็จ 1', stdout)

    def test_convert_creates_explicit_output_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            output_dir = root / 'out' / 'nested'
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli(
                    ['convert', str(source), '--output-dir', str(output_dir)]
                )

            self.assertEqual(code, cli.EXIT_OK)
            self.assertTrue(output_dir.is_dir())
            self.assertEqual(run.call_args.args[1].parent, output_dir)

    def test_format_inference_produces_video_job(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli(
                    ['convert', str(source), '--format', 'mov']
                )

            self.assertEqual(code, cli.EXIT_OK)
            job = run.call_args.args[0]
            self.assertEqual(job.mode, 'video')
            self.assertEqual(job.video_format, 'mov')
            self.assertEqual(run.call_args.args[1], root / 'clip_converted.mov')

    def test_explicit_mode_video_without_format_uses_mp4(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli(
                    ['convert', str(source), '--mode', 'video']
                )

            self.assertEqual(code, cli.EXIT_OK)
            job = run.call_args.args[0]
            self.assertEqual(job.mode, 'video')
            self.assertEqual(job.video_format, 'mp4')

    def test_collision_creates_numbered_name_without_overwrite(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            existing = root / 'clip_audio.mp3'
            existing.write_bytes(b'old')
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli(['convert', str(source)])

            self.assertEqual(code, cli.EXIT_OK)
            target = run.call_args.args[1]
            self.assertEqual(target.name, 'clip_audio (1).mp3')
            self.assertEqual(existing.read_bytes(), b'old')
            self.assertFalse(run.call_args.kwargs['overwrite'])

    def test_overwrite_keeps_base_name_and_replaces(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            existing = root / 'clip_audio.mp3'
            existing.write_bytes(b'old')
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli(
                    ['convert', str(source), '--overwrite']
                )

            self.assertEqual(code, cli.EXIT_OK)
            target = run.call_args.args[1]
            self.assertEqual(target, existing)
            self.assertTrue(run.call_args.kwargs['overwrite'])

    def test_trim_values_are_parsed_with_core_helper(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli([
                    'convert', str(source),
                    '--trim-start', '00:01:30',
                    '--trim-duration', '30',
                ])

            self.assertEqual(code, cli.EXIT_OK)
            job = run.call_args.args[0]
            self.assertEqual(job.trim_start, 90.0)
            self.assertEqual(job.trim_duration, 30.0)

    def test_quality_fps_and_enhance_are_mapped_to_core_presets(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli([
                    'convert', str(source),
                    '--mode', 'video',
                    '--quality', 'high',
                    '--fps', '60',
                    '--enhance',
                ])

            self.assertEqual(code, cli.EXIT_OK)
            job = run.call_args.args[0]
            self.assertEqual(job.quality, 'High')
            self.assertEqual(job.fps, '60')
            self.assertTrue(job.enhance)

    def test_conversion_failure_stops_batch_and_skips_rest(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = [self.make_source(root, f'clip{i}.mp4') for i in range(3)]
            side_effect = [None, FFmpegError('boom'), None]
            with patch('clipora.cli.run_local_conversion') as run:
                run.side_effect = side_effect
                code, stdout, stderr = self.run_cli(
                    ['convert', *map(str, sources)]
                )

            self.assertEqual(code, cli.EXIT_FAILED)
            self.assertEqual(run.call_count, 2)
            self.assertIn('ล้มเหลว 1', stdout)
            self.assertIn('ข้าม 1', stdout)
            self.assertIn('boom', stderr)

    def test_continue_on_error_processes_whole_batch(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            sources = [self.make_source(root, f'clip{i}.mp4') for i in range(3)]
            with patch('clipora.cli.run_local_conversion') as run:
                run.side_effect = [None, FFmpegError('boom'), None]
                code, stdout, _stderr = self.run_cli(
                    ['convert', *map(str, sources), '--continue-on-error']
                )

            self.assertEqual(code, cli.EXIT_FAILED)
            self.assertEqual(run.call_count, 3)
            self.assertIn('สำเร็จ 2', stdout)
            self.assertIn('ล้มเหลว 1', stdout)

    def test_missing_source_is_reported_as_failed_item(self):
        with TemporaryDirectory() as directory:
            missing = Path(directory) / 'missing.mp4'
            with patch('clipora.cli.run_local_conversion') as run:
                code, stdout, stderr = self.run_cli(['convert', str(missing)])

            self.assertEqual(code, cli.EXIT_FAILED)
            run.assert_not_called()
            self.assertIn('ไม่พบไฟล์', stderr)
            self.assertIn('ล้มเหลว 1', stdout)

    def test_batch_avoids_duplicate_names_even_before_files_exist(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.make_source(root / 'a')
            second = self.make_source(root / 'b')
            output_dir = root / 'out'
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli([
                    'convert', str(first), str(second),
                    '--output-dir', str(output_dir),
                ])

            self.assertEqual(code, cli.EXIT_OK)
            targets = [call.args[1] for call in run.call_args_list]
            self.assertEqual(
                [target.name for target in targets],
                ['clip_audio.mp3', 'clip_audio (1).mp3'],
            )

    def test_overwrite_duplicate_stems_in_same_output_dir_keep_both(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.make_source(root / 'a')
            second = self.make_source(root / 'b')
            output_dir = root / 'out'
            with patch('clipora.cli.run_local_conversion') as run:
                code, stdout, _stderr = self.run_cli([
                    'convert', str(first), str(second),
                    '--output-dir', str(output_dir), '--overwrite', '--json',
                ])

            self.assertEqual(code, cli.EXIT_OK)
            targets = [call.args[1] for call in run.call_args_list]
            self.assertEqual(
                [target.name for target in targets],
                ['clip_audio.mp3', 'clip_audio (1).mp3'],
            )
            self.assertTrue(all(call.kwargs['overwrite'] for call in run.call_args_list))
            payload = json.loads(stdout)
            outputs = [item['output'] for item in payload['items']]
            self.assertEqual(outputs, [
                str(output_dir / 'clip_audio.mp3'),
                str(output_dir / 'clip_audio (1).mp3'),
            ])
            self.assertEqual(len(set(outputs)), 2)
            self.assertEqual(payload['succeeded'], 2)

    def test_overwrite_still_replaces_preexisting_file_on_first_use(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            existing = root / 'clip_audio.mp3'
            existing.write_bytes(b'old')
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli(
                    ['convert', str(source), '--overwrite']
                )

            self.assertEqual(code, cli.EXIT_OK)
            self.assertEqual(run.call_args.args[1], existing)
            self.assertTrue(run.call_args.kwargs['overwrite'])

    def test_cross_directory_defaults_use_base_name_in_each_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.make_source(root / 'a')
            second = self.make_source(root / 'b')
            with patch('clipora.cli.run_local_conversion') as run:
                code, _stdout, _stderr = self.run_cli(
                    ['convert', str(first), str(second)]
                )

            self.assertEqual(code, cli.EXIT_OK)
            targets = [call.args[1] for call in run.call_args_list]
            self.assertEqual(targets[0], root / 'a' / 'clip_audio.mp3')
            self.assertEqual(targets[1], root / 'b' / 'clip_audio.mp3')

    def test_progress_is_written_to_stderr_only(self):
        with TemporaryDirectory() as directory:
            source = self.make_source(Path(directory))
            with patch('clipora.cli.run_local_conversion') as run:
                run.side_effect = self.progress_side_effect('converting', 50.0)
                code, stdout, stderr = self.run_cli(['convert', str(source)])

            self.assertEqual(code, cli.EXIT_OK)
            self.assertIn('กำลังแปลง', stderr)
            self.assertIn('50%', stderr)
            self.assertNotIn('กำลังแปลง', stdout)

    def test_json_summary_is_single_machine_readable_line(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            with patch('clipora.cli.run_local_conversion') as run:
                run.side_effect = self.progress_side_effect()
                code, stdout, stderr = self.run_cli(
                    ['convert', str(source), '--json']
                )

            self.assertEqual(code, cli.EXIT_OK)
            self.assertEqual(stderr, '')
            payload = json.loads(stdout)
            self.assertEqual(payload['command'], 'convert')
            self.assertEqual(payload['exit_code'], 0)
            self.assertFalse(payload['cancelled'])
            self.assertEqual(payload['total'], 1)
            self.assertEqual(payload['succeeded'], 1)
            self.assertEqual(payload['failed'], 0)
            item = payload['items'][0]
            self.assertEqual(item['status'], 'ok')
            self.assertEqual(item['output'], str(root / 'clip_audio.mp3'))
            self.assertIsNone(item['error'])


class DownloadTests(CLITestCase):
    URL = 'https://example.com/watch?v=abc'

    def test_download_uses_import_url_and_current_directory(self):
        with patch('clipora.cli.import_url', return_value=Path('/tmp/out.mp3')) as import_mock:
            code, stdout, _stderr = self.run_cli(['download', self.URL])

        self.assertEqual(code, cli.EXIT_OK)
        spec = import_mock.call_args.args[0]
        self.assertIsInstance(spec, ImportSpec)
        self.assertEqual(spec.url, self.URL)
        self.assertEqual(spec.destination, Path.cwd())
        self.assertEqual(spec.mode, 'audio')
        self.assertEqual(spec.audio_format, 'mp3')
        self.assertEqual(spec.trim_start, None)
        self.assertFalse(spec.enhance)
        self.assertNotIn('on_conflict', import_mock.call_args.kwargs)
        self.assertIn('สำเร็จ 1', stdout)

    def test_download_option_output_dir_and_video_mapping(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('clipora.cli.import_url', return_value=root / 'video.mp4') as import_mock:
                code, _stdout, _stderr = self.run_cli([
                    'download', self.URL,
                    '--output-dir', str(root),
                    '--mode', 'video',
                    '--quality', 'high',
                    '--fps', '30',
                    '--trim-start', '10',
                    '--trim-duration', '5',
                    '--enhance',
                ])

            self.assertEqual(code, cli.EXIT_OK)
            spec = import_mock.call_args.args[0]
            self.assertEqual(spec.destination, root)
            self.assertEqual(spec.mode, 'video')
            self.assertEqual(spec.video_format, 'mp4')
            self.assertEqual(spec.quality, 'สูงสุด')
            self.assertEqual(spec.fps, '30')
            self.assertEqual(spec.trim_start, 10.0)
            self.assertEqual(spec.trim_duration, 5.0)
            self.assertTrue(spec.enhance)

    def test_overwrite_passes_conflict_callback_that_accepts(self):
        answers: list[bool] = []

        def fake_import(spec, on_progress, cancellation=None, on_conflict=None):
            answers.append(on_conflict(Path('/tmp/out.mp3')))
            return Path('/tmp/out.mp3')

        with patch('clipora.cli.import_url', side_effect=fake_import) as import_mock:
            code, _stdout, _stderr = self.run_cli(
                ['download', self.URL, '--overwrite']
            )

        self.assertEqual(code, cli.EXIT_OK)
        self.assertIsNotNone(import_mock.call_args.kwargs['on_conflict'])
        # A pre-existing (not batch-produced) file may still be overwritten.
        self.assertEqual(answers, [True])

    @staticmethod
    def core_like_download(seen: list[Path], answers: list[bool]):
        """Mimic ``finalize_import_output`` collision handling for mocked runs."""

        def fake(spec, on_progress, cancellation=None, on_conflict=None):
            base = spec.destination / 'clip.mp3'
            index = 0
            while True:
                target = base if index == 0 else base.with_name(f'clip ({index}).mp3')
                exists = target in seen or target.exists()
                if not exists:
                    break
                if index == 0 and on_conflict is not None:
                    answer = on_conflict(target)
                    answers.append(answer)
                    if answer:
                        break
                index += 1
            seen.append(target)
            return target

        return fake

    def test_download_overwrite_keeps_batch_outputs_distinct(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            seen: list[Path] = []
            answers: list[bool] = []
            with patch(
                'clipora.cli.import_url',
                side_effect=self.core_like_download(seen, answers),
            ) as import_mock:
                code, stdout, _stderr = self.run_cli([
                    'download', self.URL, self.URL,
                    '--output-dir', str(root), '--overwrite', '--json',
                ])

            self.assertEqual(code, cli.EXIT_OK)
            self.assertEqual(import_mock.call_count, 2)
            payload = json.loads(stdout)
            outputs = [item['output'] for item in payload['items']]
            self.assertEqual(outputs, [
                str(root / 'clip.mp3'),
                str(root / 'clip (1).mp3'),
            ])
            self.assertEqual(len(set(outputs)), 2)
            self.assertEqual(payload['succeeded'], 2)
            # The second item must answer "keep both" for the batch output.
            self.assertEqual(answers, [False])

    def test_download_overwrite_replaces_preexisting_file_on_first_use(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / 'clip.mp3'
            existing.write_bytes(b'old')
            seen: list[Path] = []
            answers: list[bool] = []
            with patch(
                'clipora.cli.import_url',
                side_effect=self.core_like_download(seen, answers),
            ):
                code, stdout, _stderr = self.run_cli([
                    'download', self.URL,
                    '--output-dir', str(root), '--overwrite', '--json',
                ])

            self.assertEqual(code, cli.EXIT_OK)
            payload = json.loads(stdout)
            self.assertEqual(payload['items'][0]['output'], str(existing))
            self.assertEqual(answers, [True])

    def test_download_failure_returns_exit_1(self):
        with patch(
            'clipora.cli.import_url',
            side_effect=URLImportError('ลิงก์นี้ใช้ไม่ได้'),
        ) as import_mock:
            code, stdout, stderr = self.run_cli(['download', self.URL])

        self.assertEqual(code, cli.EXIT_FAILED)
        self.assertEqual(import_mock.call_count, 1)
        self.assertIn('ล้มเหลว 1', stdout)
        self.assertIn('ลิงก์นี้ใช้ไม่ได้', stderr)

    def test_download_json_failure_payload(self):
        with patch(
            'clipora.cli.import_url',
            side_effect=URLImportError('ลิงก์นี้ใช้ไม่ได้'),
        ):
            code, stdout, _stderr = self.run_cli(['download', self.URL, '--json'])

        self.assertEqual(code, cli.EXIT_FAILED)
        payload = json.loads(stdout)
        self.assertEqual(payload['command'], 'download')
        self.assertEqual(payload['exit_code'], cli.EXIT_FAILED)
        self.assertEqual(payload['failed'], 1)
        self.assertEqual(payload['items'][0]['error'], 'ลิงก์นี้ใช้ไม่ได้')

    def test_download_mode_format_mismatch_is_usage_error(self):
        code, _stdout, _stderr = self.run_cli([
            'download', self.URL, '--mode', 'audio', '--format', 'mp4',
        ])
        self.assertEqual(code, cli.EXIT_USAGE)


class CancellationTests(CLITestCase):
    def test_cancelled_item_exits_with_130_and_skips_rest(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.make_source(root, 'one.mp4')
            second = self.make_source(root, 'two.mp4')
            with patch(
                'clipora.cli.run_local_conversion',
                side_effect=ConversionCancelled('ยกเลิกงานแล้ว'),
            ) as run:
                code, stdout, stderr = self.run_cli(
                    ['convert', str(first), str(second)]
                )

            self.assertEqual(code, cli.EXIT_CANCELLED)
            self.assertEqual(run.call_count, 1)
            self.assertIn('ยกเลิกงานแล้ว', stdout)
            self.assertIn('ถูกยกเลิก', stderr)

    def test_second_interrupt_aborts_without_traceback(self):
        with TemporaryDirectory() as directory:
            source = self.make_source(Path(directory))
            with patch(
                'clipora.cli.run_local_conversion',
                side_effect=KeyboardInterrupt,
            ):
                code, _stdout, stderr = self.run_cli(['convert', str(source)])

        self.assertEqual(code, cli.EXIT_CANCELLED)
        self.assertIn('ยกเลิกทันที', stderr)
        self.assertNotIn('Traceback', stderr)

    def test_interrupt_guard_cancels_active_token_then_aborts(self):
        guard = cli.InterruptGuard()
        token = CancellationToken()
        guard.activate(token)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            guard.handle_sigint(signal.SIGINT, None)
            self.assertTrue(token.cancelled)
            self.assertTrue(guard.interrupted)
            with self.assertRaises(KeyboardInterrupt):
                guard.handle_sigint(signal.SIGINT, None)
        self.assertIn('ยกเลิก', stderr.getvalue())
        guard.deactivate()

    def test_cancelled_json_summary_reports_cancelled(self):
        with TemporaryDirectory() as directory:
            source = self.make_source(Path(directory))
            with patch(
                'clipora.cli.run_local_conversion',
                side_effect=ConversionCancelled('ยกเลิกงานแล้ว'),
            ):
                code, stdout, _stderr = self.run_cli(
                    ['convert', str(source), '--json']
                )

        self.assertEqual(code, cli.EXIT_CANCELLED)
        payload = json.loads(stdout)
        self.assertTrue(payload['cancelled'])
        self.assertEqual(payload['items'][0]['status'], 'cancelled')
        self.assertEqual(payload['skipped'], 1)


class SummaryTests(unittest.TestCase):
    def test_summary_payload_counts_each_status(self):
        results = [
            cli.ItemResult(1, 'a.mp4', Path('a_audio.mp3'), 'ok'),
            cli.ItemResult(2, 'b.mp4', None, 'failed', 'boom'),
            cli.ItemResult(3, 'c.mp4'),
        ]
        payload = cli.summary_payload('convert', results, cli.EXIT_FAILED)
        self.assertEqual(payload['total'], 3)
        self.assertEqual(payload['succeeded'], 1)
        self.assertEqual(payload['failed'], 1)
        self.assertEqual(payload['skipped'], 1)
        self.assertEqual(payload['items'][1]['error'], 'boom')

    def test_format_summary_lists_items_and_cancellation_note(self):
        results = [cli.ItemResult(1, 'a.mp4', None, 'cancelled', 'ยกเลิกงานแล้ว')]
        text = cli.format_summary('convert', results, cli.EXIT_CANCELLED)
        self.assertIn('ทั้งหมด 1 รายการ', text)
        self.assertIn('[ยกเลิก] a.mp4', text)
        self.assertIn('ไฟล์เดิมยังอยู่ครบ', text)


class MiscTests(CLITestCase):
    def test_main_accepts_no_argv_and_reads_sys_argv(self):
        with patch.object(cli.sys, 'argv', ['clipora', '--help']):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cli.main()
        self.assertEqual(code, 0)
        self.assertIn('download', stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
