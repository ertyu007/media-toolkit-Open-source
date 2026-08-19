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
    URLImportBlocked,
    URLImportError,
    URLNetworkBlocked,
    VIDEO_QUALITIES,
    _find_completed_output,
    _run_import_process,
    _run_import_with_fallback,
    browser_impersonation_args,
    build_import_command,
    cleanup_import_workspace,
    collision_free_path,
    create_import_workspace,
    finalize_import_output,
    find_ytdlp_command,
    import_url,
    is_block_error,
    is_network_block_error,
    parse_import_progress,
    parse_reported_output,
    site_workaround_extractor_args,
    site_workaround_headers,
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
    def make_spec(
        self,
        mode='video',
        quality='สูงสุด',
        audio_format='mp3',
        video_format='mp4',
        fps='สูงสุด',
    ):
        return ImportSpec(
            url='https://example.com/watch/123',
            destination=Path('output'),
            mode=mode,
            quality=quality,
            audio_format=audio_format,
            video_format=video_format,
            fps=fps,
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
            '2160p': 'res:2160,fps,vcodec:h264,acodec:aac',
            '1080p': 'res:1080,fps,vcodec:h264,acodec:aac',
            '720p': 'res:720,fps,vcodec:h264,acodec:aac',
            '480p': 'res:480,fps,vcodec:h264,acodec:aac',
            '360p': 'res:360,fps,vcodec:h264,acodec:aac',
        }
        self.assertEqual(VIDEO_QUALITIES, ('สูงสุด', '2160p', '1080p', '720p', '480p', '360p'))
        for quality, sort_value in expected.items():
            with self.subTest(quality=quality):
                command = build_import_command(
                    ['yt-dlp'],
                    self.make_spec(quality=quality),
                    Path('temporary'),
                )
                self.assertIn(sort_value, command)

    def test_video_command_applies_fps_cap_to_format_selector(self):
        command = build_import_command(
            ['yt-dlp'],
            self.make_spec(fps='60'),
            Path('temporary'),
        )
        format_selector = command[command.index('--format') + 1]
        self.assertIn('[fps<=60]', format_selector)

    def test_video_command_without_fps_cap_keeps_default_selector(self):
        command = build_import_command(
            ['yt-dlp'],
            self.make_spec(fps='สูงสุด'),
            Path('temporary'),
        )
        format_selector = command[command.index('--format') + 1]
        self.assertNotIn('[fps', format_selector)
        self.assertIn('bv*[ext=mp4]+ba[ext=m4a]', format_selector)

    def test_video_command_mov_import_still_downloads_mp4_source(self):
        command = build_import_command(
            ['yt-dlp'],
            self.make_spec(video_format='mov'),
            Path('temporary'),
        )
        self.assertEqual(command[command.index('--merge-output-format') + 1], 'mp4')
        self.assertEqual(command[command.index('--remux-video') + 1], 'mp4')

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
                self.make_spec(mode='audio', audio_format='aiff'),
                Path('temporary'),
            )
        with self.assertRaises(ValueError):
            build_import_command(
                ['yt-dlp'],
                self.make_spec(mode='video', video_format='mkv'),
                Path('temporary'),
            )


class WorkaroundHelperTests(unittest.TestCase):
    def test_site_workaround_headers_apply_to_tiktok_urls(self):
        self.assertEqual(
            site_workaround_headers('https://www.tiktok.com/@user/video/123'),
            ['--add-header', 'Referer:https://www.tiktok.com/'],
        )
        self.assertEqual(
            site_workaround_headers('https://vt.tiktok.com/abc/'),
            ['--add-header', 'Referer:https://www.tiktok.com/'],
        )

    def test_site_workaround_headers_are_empty_for_other_sites(self):
        self.assertEqual(site_workaround_headers('https://youtube.com/watch?v=abc'), [])
        self.assertEqual(site_workaround_headers(''), [])

    def test_site_workaround_extractor_args_apply_to_youtube_urls(self):
        expected = [
            '--extractor-args',
            'youtube:player_client=android,web_embedded,tv',
        ]
        self.assertEqual(site_workaround_extractor_args('https://www.youtube.com/watch?v=abc'), expected)
        self.assertEqual(site_workaround_extractor_args('https://youtu.be/abc'), expected)

    def test_site_workaround_extractor_args_are_empty_for_other_sites(self):
        self.assertEqual(site_workaround_extractor_args('https://www.tiktok.com/@user/video/123'), [])
        self.assertEqual(site_workaround_extractor_args(''), [])

    def test_browser_impersonation_args_are_explicit(self):
        self.assertEqual(browser_impersonation_args(), ['--impersonate', 'chrome'])

    def test_extra_args_are_injected_before_url_separator(self):
        command = build_import_command(
            ['yt-dlp'],
            ImportSpec(
                url='https://example.com/watch/123',
                destination=Path('output'),
                mode='video',
                quality='สูงสุด',
                audio_format='mp3',
            ),
            Path('temporary'),
            extra_args=['--add-header', 'Referer:https://example.com/'],
        )
        self.assertEqual(
            command[-4:],
            ['--add-header', 'Referer:https://example.com/', '--', 'https://example.com/watch/123'],
        )

    def test_extra_args_still_never_include_credentials(self):
        command = build_import_command(
            ['yt-dlp'],
            ImportSpec(
                url='https://example.com/watch/123',
                destination=Path('output'),
                mode='video',
                quality='สูงสุด',
                audio_format='mp3',
            ),
            Path('temporary'),
            extra_args=['--add-header', 'Referer:https://example.com/'],
        )
        for forbidden in ('--cookies', '--cookies-from-browser', '--username', '--password', '--netrc'):
            self.assertNotIn(forbidden, command)


class BlockDetectionTests(unittest.TestCase):
    def test_detects_http_block_errors(self):
        blocked = (
            'ERROR: unable to download video data: HTTP Error 403: Forbidden',
            'HTTP Error 429: Too Many Requests',
            "Sign in to confirm you're not a bot",
            'ERROR: This request has been blocked',
            'WARNING: unusual traffic detected',
            'ERROR: [youtube] temporary block',
        )
        for line in blocked:
            with self.subTest(line=line):
                self.assertTrue(is_block_error([line]))

    def test_ignores_unrelated_failures(self):
        normal = (
            'ERROR: video unavailable',
            'ERROR: This video is private',
            'ERROR: unable to extract data',
            'ERROR: HTTP Error 404: Not Found',
        )
        for line in normal:
            with self.subTest(line=line):
                self.assertFalse(is_block_error([line]))


class NetworkBlockDetectionTests(unittest.TestCase):
    def test_detects_dns_and_network_level_blocks(self):
        blocked = (
            "HTTPSConnection(host='www.youtube.com', port=443): Failed to resolve 'www.youtube.com' "
            "([Errno 11001] getaddrinfo failed)",
            'ERROR: unable to resolve host',
            'WARNING: temporary failure in name resolution',
            'ERROR: network is unreachable',
            'ERROR: no route to host',
        )
        for line in blocked:
            with self.subTest(line=line):
                self.assertTrue(is_network_block_error([line]))

    def test_ignores_site_side_blocks_and_other_errors(self):
        normal = (
            'HTTP Error 403: Forbidden',
            'HTTP Error 429: Too Many Requests',
            'ERROR: video unavailable',
            'ERROR: unable to extract data',
        )
        for line in normal:
            with self.subTest(line=line):
                self.assertFalse(is_network_block_error([line]))

    @patch('clipora.importer._run_import_process')
    def test_network_block_fails_immediately_without_retries(self, run_process):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            workspace = create_import_workspace(destination)
            run_process.side_effect = URLNetworkBlocked('getaddrinfo failed')

            with self.assertRaises(URLNetworkBlocked):
                _run_import_with_fallback(
                    ['yt-dlp'],
                    ImportSpec(
                        url='https://youtube.com/watch?v=abc',
                        destination=destination,
                        mode='video',
                        quality='สูงสุด',
                        audio_format='mp3',
                    ),
                    workspace,
                    lambda _value: None,
                    CancellationToken(),
                )
            cleanup_import_workspace(workspace, destination)

            self.assertEqual(run_process.call_count, 1)


class ImportFallbackTests(unittest.TestCase):
    def make_spec(self, url='https://www.tiktok.com/@user/video/123'):
        return ImportSpec(
            url=url,
            destination=Path('output'),
            mode='video',
            quality='สูงสุด',
            audio_format='mp3',
        )

    def _complete(self, workspace, name='clip.mp4'):
        result = workspace / name
        result.write_bytes(b'downloaded')
        return result

    @patch('clipora.importer._run_import_process')
    @patch('clipora.importer._clear_import_partials')
    def test_retries_with_headers_then_impersonation_on_block(self, _clear, run_process):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            workspace = create_import_workspace(destination)
            attempts = []

            def simulate(command, _workspace, on_progress, _token):
                attempts.append(command)
                on_progress(0.5)
                if len(attempts) == 1:
                    raise URLImportBlocked('HTTP Error 403: Forbidden')
                if len(attempts) == 2:
                    raise URLImportBlocked('HTTP Error 403: Forbidden')
                return self._complete(_workspace)

            run_process.side_effect = simulate
            with patch('clipora.importer.ytdlp_supports_impersonation', return_value=True):
                completed = _run_import_with_fallback(
                    ['yt-dlp'],
                    self.make_spec(),
                    workspace,
                    lambda _value: None,
                    CancellationToken(),
                )
            cleanup_import_workspace(workspace, destination)

            self.assertEqual(len(attempts), 3)
            self.assertIn('--add-header', attempts[1])
            self.assertEqual(
                attempts[2][-4:],
                ['--impersonate', 'chrome', '--', 'https://www.tiktok.com/@user/video/123'],
            )
            self.assertEqual(completed.name, 'clip.mp4')
            self.assertEqual(_clear.call_count, 2)

    @patch('clipora.importer._run_import_process')
    def test_non_block_error_fails_immediately(self, run_process):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            workspace = create_import_workspace(destination)
            run_process.side_effect = URLImportError('ERROR: video unavailable')

            with self.assertRaises(URLImportError):
                _run_import_with_fallback(
                    ['yt-dlp'],
                    self.make_spec(url='https://youtube.com/watch?v=abc'),
                    workspace,
                    lambda _value: None,
                    CancellationToken(),
                )
            cleanup_import_workspace(workspace, destination)

            self.assertEqual(run_process.call_count, 1)

    @patch('clipora.importer._run_import_process')
    def test_skips_impersonation_when_unsupported(self, run_process):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            workspace = create_import_workspace(destination)

            def simulate(command, _workspace, on_progress, _token):
                raise URLImportBlocked('HTTP Error 403: Forbidden')

            run_process.side_effect = simulate
            with patch('clipora.importer.ytdlp_supports_impersonation', return_value=False):
                with self.assertRaises(URLImportBlocked):
                    _run_import_with_fallback(
                        ['yt-dlp'],
                        self.make_spec(url='https://youtube.com/watch?v=abc'),
                        workspace,
                        lambda _value: None,
                        CancellationToken(),
                    )
            cleanup_import_workspace(workspace, destination)

            self.assertEqual(run_process.call_count, 2)

    @patch('clipora.importer._run_import_process')
    def test_youtube_retries_with_extractor_args_then_impersonation(self, run_process):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            workspace = create_import_workspace(destination)
            attempts = []

            def simulate(command, _workspace, on_progress, _token):
                attempts.append(command)
                if len(attempts) < 3:
                    raise URLImportBlocked('HTTP Error 403: Forbidden')
                return self._complete(_workspace)

            run_process.side_effect = simulate
            with patch('clipora.importer.ytdlp_supports_impersonation', return_value=True):
                completed = _run_import_with_fallback(
                    ['yt-dlp'],
                    self.make_spec(url='https://youtube.com/watch?v=abc'),
                    workspace,
                    lambda _value: None,
                    CancellationToken(),
                )
            cleanup_import_workspace(workspace, destination)

            self.assertEqual(len(attempts), 3)
            self.assertEqual(
                attempts[1][-4:],
                ['--extractor-args', 'youtube:player_client=android,web_embedded,tv', '--', 'https://youtube.com/watch?v=abc'],
            )
            self.assertEqual(attempts[2][-4:], ['--impersonate', 'chrome', '--', 'https://youtube.com/watch?v=abc'])
            self.assertEqual(completed.name, 'clip.mp4')

    @patch('clipora.importer._run_import_process')
    def test_impersonation_appended_only_once_when_all_attempts_blocked(self, run_process):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            workspace = create_import_workspace(destination)

            def simulate(command, _workspace, on_progress, _token):
                raise URLImportBlocked('HTTP Error 403: Forbidden')

            run_process.side_effect = simulate
            with patch('clipora.importer.ytdlp_supports_impersonation', return_value=True):
                with self.assertRaises(URLImportBlocked):
                    _run_import_with_fallback(
                        ['yt-dlp'],
                        self.make_spec(url='https://youtube.com/watch?v=abc'),
                        workspace,
                        lambda _value: None,
                        CancellationToken(),
                    )
            cleanup_import_workspace(workspace, destination)

            self.assertEqual(run_process.call_count, 3)


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

    def test_falls_back_to_workspace_scan_when_reported_output_is_stale(self):
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            workspace = create_import_workspace(destination)
            completed = workspace / 'คลิป.mp4'
            completed.write_bytes(b'downloaded')
            stale = workspace / 'intermediate.webm'

            self.assertEqual(_find_completed_output(workspace, [stale]), completed.resolve())
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
