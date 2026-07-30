import json
import os
import sys
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from clipora.ffmpeg import CancellationToken, ConversionCancelled
from clipora.importer import (
    ImportSpec,
    VIDEO_QUALITIES,
    _run_import_process,
    build_import_command,
    cleanup_import_workspace,
    collision_free_path,
    create_import_workspace,
    finalize_import_output,
    find_ytdlp_command,
    import_url,
    parse_import_progress,
    parse_reported_output,
    url_summary,
    validate_url,
)


class URLValidationTests(unittest.TestCase):
    def test_accepts_public_http_and_https_urls(self):
        self.assertEqual(
            validate_url(' https://www.youtube.com/watch?v=abc '),
            'https://www.youtube.com/watch?v=abc',
        )
        self.assertEqual(validate_url('http://example.com/video.mp4'), 'http://example.com/video.mp4')

    def test_rejects_non_network_and_credential_urls(self):
        invalid = (
            'file:///C:/video.mp4',
            'ftp://example.com/video.mp4',
            'https://user:secret@example.com/video.mp4',
            'http://localhost/video.mp4',
            'http://127.0.0.1/video.mp4',
            'http://192.168.1.10/video.mp4',
        )
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_url_summary_reports_host_or_error(self):
        self.assertIn('youtube.com', url_summary('https://youtube.com/watch?v=abc'))
        self.assertIn('http', url_summary('not a link'))


class YtDlpDiscoveryTests(unittest.TestCase):
    @patch('clipora.importer.importlib.util.find_spec', return_value=None)
    @patch('clipora.tools.shutil.which', return_value=None)
    def test_finds_clipora_managed_binary(self, _which, _find_spec):
        with TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'LOCALAPPDATA': directory}):
                filename = 'yt-dlp.exe' if os.name == 'nt' else 'yt-dlp'
                executable = Path(directory) / 'Clipora' / 'bin' / filename
                executable.parent.mkdir(parents=True)
                executable.write_bytes(b'test binary')

                self.assertEqual(find_ytdlp_command(), [str(executable)])


class ImportCommandTests(unittest.TestCase):
    def make_spec(self, mode='video', quality='สูงสุด', audio_format='mp3'):
        return ImportSpec(
            url='https://example.com/watch/123',
            destination=Path('output'),
            mode=mode,
            quality=quality,
            audio_format=audio_format,
        )

    def test_video_command_is_single_item_public_download(self):
        command = build_import_command(['yt-dlp'], self.make_spec(), Path('temporary'))
        self.assertIn('--ignore-config', command)
        self.assertIn('--no-playlist', command)
        self.assertIn('--merge-output-format', command)
        self.assertIn('--remux-video', command)
        self.assertIn('res,fps,vcodec:h264,acodec:aac', command)
        self.assertEqual(command[-1], 'https://example.com/watch/123')
        for forbidden in ('--cookies', '--cookies-from-browser', '--username', '--password', '--netrc'):
            self.assertNotIn(forbidden, command)

    def test_video_quality_limits_are_explicit(self):
        expected = {
            '1080p': 'res:1080,fps,vcodec:h264,acodec:aac',
            '720p': 'res:720,fps,vcodec:h264,acodec:aac',
            '480p': 'res:480,fps,vcodec:h264,acodec:aac',
        }
        self.assertEqual(VIDEO_QUALITIES, ('สูงสุด', '1080p', '720p', '480p'))
        for quality, sort_value in expected.items():
            with self.subTest(quality=quality):
                command = build_import_command(
                    ['yt-dlp'],
                    self.make_spec(quality=quality),
                    Path('temporary'),
                )
                self.assertIn(sort_value, command)

    def test_audio_command_extracts_requested_format(self):
        command = build_import_command(
            ['yt-dlp'],
            self.make_spec(mode='audio', audio_format='m4a'),
            Path('temporary'),
        )
        self.assertIn('--extract-audio', command)
        self.assertEqual(command[command.index('--audio-format') + 1], 'm4a')

    @patch('clipora.importer.find_executable')
    def test_command_enables_available_node_runtime(self, find_executable):
        find_executable.side_effect = (
            lambda name: Path('C:/Program Files/nodejs/node.exe') if name == 'node' else None
        )
        command = build_import_command(['yt-dlp'], self.make_spec(), Path('temporary'))
        self.assertEqual(
            command[command.index('--js-runtimes') + 1],
            'node:C:\\Program Files\\nodejs\\node.exe',
        )

    def test_invalid_import_options_are_rejected(self):
        with self.assertRaises(ValueError):
            build_import_command(['yt-dlp'], self.make_spec(mode='playlist'), Path('temporary'))
        with self.assertRaises(ValueError):
            build_import_command(
                ['yt-dlp'],
                self.make_spec(mode='audio', audio_format='wav'),
                Path('temporary'),
            )


class ImportProgressTests(unittest.TestCase):
    def test_parses_and_clamps_percentage(self):
        self.assertEqual(parse_import_progress('clipora-progress: 42.5%'), 0.425)
        self.assertEqual(parse_import_progress('clipora-progress:120.0%'), 1.0)
        self.assertIsNone(parse_import_progress('[download] 20%'))

    def test_parses_json_reported_output(self):
        expected = Path('C:\\Videos\\คลิป.mp4')
        self.assertEqual(
            parse_reported_output(f'clipora-output:{json.dumps(str(expected))}'),
            expected,
        )
        self.assertIsNone(parse_reported_output('clipora-output:not-json'))


class ImportWorkspaceTests(unittest.TestCase):
    def test_workspace_cleanup_is_scoped_to_owned_directory(self):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            workspace = create_import_workspace(destination)
            (workspace / 'partial.part').write_bytes(b'partial')
            unrelated = destination / 'keep.mp4'
            unrelated.write_bytes(b'keep')

            cleanup_import_workspace(workspace, destination)

            self.assertFalse(workspace.exists())
            self.assertEqual(unrelated.read_bytes(), b'keep')
            with self.assertRaises(ValueError):
                cleanup_import_workspace(destination, destination)

    def test_collision_free_path_preserves_existing_file(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'clip.mp4'
            target.write_bytes(b'original')
            self.assertEqual(collision_free_path(target), Path(directory) / 'clip (1).mp4')

    def test_atomic_finalize_never_replaces_existing_file(self):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            existing = destination / 'clip.mp4'
            existing.write_bytes(b'original')
            workspace = create_import_workspace(destination)
            completed = workspace / 'clip.mp4'
            completed.write_bytes(b'downloaded')

            target = finalize_import_output(completed, destination)

            self.assertEqual(existing.read_bytes(), b'original')
            self.assertEqual(target.name, 'clip (1).mp4')
            self.assertEqual(target.read_bytes(), b'downloaded')
            self.assertFalse(completed.exists())
            cleanup_import_workspace(workspace, destination)

    @patch('clipora.importer._run_import_process')
    def test_import_moves_completed_file_and_cleans_workspace(self, run_process):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            existing = destination / 'คลิป.mp4'
            existing.write_bytes(b'original')

            def complete(_command, workspace, on_progress, _cancellation):
                result = workspace / 'คลิป.mp4'
                result.write_bytes(b'downloaded')
                on_progress(1.0)
                return result

            run_process.side_effect = complete
            progress = []
            target = import_url(
                ImportSpec(
                    url='https://example.com/video',
                    destination=destination,
                    mode='video',
                    quality='สูงสุด',
                    audio_format='mp3',
                ),
                progress.append,
                CancellationToken(),
                tool_command=['yt-dlp'],
            )

            self.assertEqual(target.name, 'คลิป (1).mp4')
            self.assertEqual(target.read_bytes(), b'downloaded')
            self.assertEqual(existing.read_bytes(), b'original')
            self.assertEqual(progress, [1.0])
            self.assertFalse(any(destination.glob('.clipora-import-*')))


@unittest.skipUnless(sys.platform == 'win32', 'Windows process-tree behavior')
class ImportCancellationTests(unittest.TestCase):
    def test_cancel_stops_exact_downloader_process_tree(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = create_import_workspace(root)
            marker = root / 'orphan-child.txt'
            helper = root / 'fake-downloader.py'
            helper.write_text(
                'import subprocess, sys, time\n'
                'marker = sys.argv[1]\n'
                'child_code = \'import pathlib, sys, time; time.sleep(3); '
                'pathlib.Path(sys.argv[1]).write_text(chr(111)+chr(114)+chr(112)+chr(104)+chr(97)+chr(110))\'\n'
                'subprocess.Popen([sys.executable, \'-c\', child_code, marker])\n'
                'print(\'clipora-progress:1%\', flush=True)\n'
                'time.sleep(30)\n',
                encoding='utf-8',
            )
            cancellation = CancellationToken()
            progress_started = threading.Event()
            errors = []

            def run():
                try:
                    _run_import_process(
                        [sys.executable, str(helper), str(marker)],
                        workspace,
                        lambda _value: progress_started.set(),
                        cancellation,
                    )
                except Exception as exc:
                    errors.append(exc)

            worker = threading.Thread(target=run)
            worker.start()
            self.assertTrue(progress_started.wait(5), 'fake downloader did not start')
            cancellation.cancel()
            worker.join(5)
            self.assertFalse(worker.is_alive(), 'downloader did not stop after cancellation')
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], ConversionCancelled)
            time.sleep(3.5)
            self.assertFalse(marker.exists(), 'child process survived cancellation')
            cleanup_import_workspace(workspace, root)


if __name__ == '__main__':
    unittest.main()
