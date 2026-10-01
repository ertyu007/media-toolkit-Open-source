"""Guard the Android port against drift from the PC originals.

``android/core`` is a copy of ``clipora/ffmpeg.py``, ``clipora/history.py``
and part of ``clipora/importer.py``. These tests import both and assert they
behave identically, so a PC-side fix has to be mirrored deliberately instead
of silently diverging.

Deliberate divergences (documented in the module docstrings) are not asserted
here: the Android ports drop ``creationflags``, the ``taskkill`` cancel path,
yt-dlp's JavaScript-runtime / browser-impersonation flags, and store history
in the app's private dir instead of the PC settings folder.
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ANDROID_ROOT = REPO_ROOT / 'android'
for entry in (str(REPO_ROOT), str(ANDROID_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from clipora import ffmpeg as pc_ffmpeg  # noqa: E402
from clipora import history as pc_history  # noqa: E402
from clipora import importer as pc_importer  # noqa: E402
from core import ffmpeg as android_ffmpeg  # noqa: E402
from core import history as android_history  # noqa: E402
from core import ytdlp as android_ytdlp  # noqa: E402

SOURCE = Path('C:/media/sample.mkv')
TARGET = Path('C:/out/sample_audio.mp3')
WORKSPACE = Path('C:/out/.clipora-import-abc')


def _pc_build(**overrides):
    kwargs = {
        'source': SOURCE,
        'target': TARGET,
        'mode': 'audio',
        'quality': 'Balanced',
        'audio_format': 'mp3',
        'video_format': 'mp4',
        'fps': 'สูงสุด',
        'start_time': None,
        'duration_time': None,
    }
    kwargs.update(overrides)
    return pc_ffmpeg.build_command(**kwargs)


def _android_build(**overrides):
    kwargs = {
        'source': SOURCE,
        'target': TARGET,
        'mode': 'audio',
        'quality': 'Balanced',
        'audio_format': 'mp3',
        'video_format': 'mp4',
        'fps': 'สูงสุด',
        'start_time': None,
        'duration_time': None,
    }
    kwargs.update(overrides)
    return android_ffmpeg.build_command(**kwargs)


def _fake_find(name: str) -> Path:
    """Pin every tool lookup to a sentinel so parity compares args, not this PC."""
    return Path('/tools') / name


class _PinnedTools:
    """Neutralise tool discovery on both sides before comparing commands."""

    def setUp(self):
        super().setUp()
        for module in (pc_ffmpeg, android_ffmpeg, pc_importer):
            if not hasattr(module, 'find_executable'):
                continue
            original = module.find_executable
            module.find_executable = _fake_find
            self.addCleanup(setattr, module, 'find_executable', original)


class BuildCommandParity(_PinnedTools, unittest.TestCase):
    def test_audio_formats_match(self):
        for audio_format in pc_ffmpeg.AUDIO_FORMATS:
            with self.subTest(audio_format=audio_format):
                self.assertEqual(
                    _pc_build(mode='audio', audio_format=audio_format),
                    _android_build(mode='audio', audio_format=audio_format),
                )

    def test_mp4_qualities_and_fps_match(self):
        for quality in pc_ffmpeg.VIDEO_QUALITY_PRESETS:
            for fps in pc_ffmpeg.FPS_OPTIONS:
                with self.subTest(quality=quality, fps=fps):
                    self.assertEqual(
                        _pc_build(mode='video', fps=fps, quality=quality),
                        _android_build(mode='video', fps=fps, quality=quality),
                    )

    def test_trim_arguments_match(self):
        self.assertEqual(
            _pc_build(start_time='12.500', duration_time='30.000'),
            _android_build(start_time='12.500', duration_time='30.000'),
        )

    def test_rejected_options_match(self):
        cases = (
            {'mode': 'stems'},
            {'mode': 'audio', 'audio_format': 'aiff'},
            {'mode': 'video', 'video_format': 'avi'},
            {'mode': 'video', 'quality': 'Ultra'},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    _pc_build(**overrides)
                with self.assertRaises(ValueError):
                    _android_build(**overrides)

    def test_profiles_match(self):
        self.assertEqual(
            pc_ffmpeg.PRORES_PROFILES,
            android_ffmpeg.PRORES_PROFILES,
        )
        self.assertEqual(pc_ffmpeg.PROGRESS_KEYS, android_ffmpeg.PROGRESS_KEYS)


class PureHelperParity(unittest.TestCase):
    def test_output_path_matches(self):
        for mode in ('audio', 'video'):
            for audio_format in pc_ffmpeg.AUDIO_FORMATS:
                with self.subTest(mode=mode, audio_format=audio_format):
                    self.assertEqual(
                        pc_ffmpeg.output_path(SOURCE, TARGET.parent, mode, audio_format),
                        android_ffmpeg.output_path(SOURCE, TARGET.parent, mode, audio_format),
                    )

    def test_parse_trim_seconds_matches(self):
        samples = ['90', '90.5', '01:30', '1:02:03', '', '   ', None, '60:00', '1:2:3:4', '-1', 'abc']
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(
                    self._capture(pc_ffmpeg.parse_trim_seconds, text),
                    self._capture(android_ffmpeg.parse_trim_seconds, text),
                )

    def test_normalize_trim_matches(self):
        cases = (
            (None, None, 100.0),
            (10.0, None, 100.0),
            (10.0, 30.0, 100.0),
            (10.0, 500.0, 100.0),
            (0.0, 5.0, 100.0),
            (100.0, None, 100.0),
            (-1.0, None, 100.0),
            (5.0, 0.0, 100.0),
            (10.0, None, None),
        )
        for start, duration, media in cases:
            with self.subTest(start=start, duration=duration, media=media):
                self.assertEqual(
                    self._capture(pc_ffmpeg.normalize_trim, start, duration, media),
                    self._capture(android_ffmpeg.normalize_trim, start, duration, media),
                )

    def test_parse_progress_line_matches(self):
        lines = [
            'out_time=00:00:30.000000',
            'out_time_us=30000000',
            'out_time=N/A',
            'progress=end',
            'progress=continue',
            'bitrate=1000kbits/s',
            'garbage',
        ]
        for duration in (60.0, None, 0.0):
            for line in lines:
                with self.subTest(duration=duration, line=line):
                    self.assertEqual(
                        pc_ffmpeg.parse_progress_line(line, duration),
                        android_ffmpeg.parse_progress_line(line, duration),
                    )

    def test_temporary_output_naming_matches(self):
        for target in (TARGET, Path('C:/out/no-extension'), Path('C:/out/a.b.c.mp4')):
            with self.subTest(target=target):
                pc_temp = pc_ffmpeg.temporary_output_path(target)
                android_temp = android_ffmpeg.temporary_output_path(target)
                for temporary in (pc_temp, android_temp):
                    self.assertEqual(temporary.parent, target.parent)
                    self.assertTrue(
                        re.fullmatch(
                            rf"\.{re.escape(target.stem)}\.clipora-[0-9a-f]{{32}}{re.escape(target.suffix)}",
                            temporary.name,
                        ),
                        temporary.name,
                    )
                self.assertEqual(
                    pc_ffmpeg._is_temporary_output_for(pc_temp, target),
                    android_ffmpeg._is_temporary_output_for(android_temp, target),
                )
                self.assertFalse(
                    android_ffmpeg._is_temporary_output_for(Path('C:/elsewhere/x.mp3'), target)
                )
                self.assertFalse(
                    android_ffmpeg._is_temporary_output_for(target, target)
                )

    @staticmethod
    def _capture(func, *args):
        try:
            return ('ok', func(*args))
        except ValueError as exc:
            return ('error', str(exc))


class UrlImportParity(unittest.TestCase):
    URLS = (
        'https://www.youtube.com/watch?v=abc',
        'https://youtu.be/abc',
        'https://www.tiktok.com/@user/video/1',
        'http://192.168.1.10/a.mp3',
        'http://localhost/a.mp3',
        'http://127.0.0.1/a.mp3',
        'http://0x7f000001/a.mp3',
        'http://2130706433/a.mp3',
        'http://[::1]/a.mp3',
        'http://169.254.169.254/latest/meta-data',
        'http://user:pass@example.com/a',
        'ftp://example.com/a',
        'not a url',
        '   ',
        'https://example.com:70000/a',
    )

    def test_validate_url_matches(self):
        for url in self.URLS:
            with self.subTest(url=url):
                self.assertEqual(
                    self._capture(pc_importer.validate_url, url),
                    self._capture(android_ytdlp.validate_url, url),
                )

    def test_url_summary_matches(self):
        for url in self.URLS:
            with self.subTest(url=url):
                self.assertEqual(
                    pc_importer.url_summary(url),
                    android_ytdlp.url_summary(url),
                )

    @staticmethod
    def _capture(func, *args):
        try:
            return ('ok', func(*args))
        except ValueError as exc:
            return ('error', str(exc))


class ImportCommandParity(unittest.TestCase):
    def _spec(self, module, **overrides):
        kwargs = {
            'url': 'https://www.youtube.com/watch?v=abc',
            'destination': WORKSPACE,
            'mode': 'audio',
            'quality': 'สูงสุด',
            'audio_format': 'mp3',
            'video_format': 'mp4',
            'fps': 'สูงสุด',
        }
        kwargs.update(overrides)
        return module.ImportSpec(**kwargs)

    def test_audio_command_matches_apart_from_platform_flags(self):
        for audio_format in ('mp3', 'm4a', 'wav', 'flac', 'opus'):
            with self.subTest(audio_format=audio_format):
                pc = pc_importer.build_import_command(
                    ['yt-dlp'], self._spec(pc_importer, audio_format=audio_format), WORKSPACE,
                )
                android = android_ytdlp.build_import_command(
                    ['yt-dlp'], self._spec(android_ytdlp, audio_format=audio_format), WORKSPACE,
                )
                self.assertEqual(
                    self._drop_platform_flags(pc),
                    self._drop_platform_flags(android),
                )

    def test_video_command_matches_apart_from_platform_flags(self):
        for quality in pc_importer.VIDEO_QUALITIES:
            for fps in pc_ffmpeg.FPS_OPTIONS:
                with self.subTest(quality=quality, fps=fps):
                    pc = pc_importer.build_import_command(
                        ['yt-dlp'],
                        self._spec(pc_importer, mode='video', quality=quality, fps=fps),
                        WORKSPACE,
                    )
                    android = android_ytdlp.build_import_command(
                        ['yt-dlp'],
                        self._spec(android_ytdlp, mode='video', quality=quality, fps=fps),
                        WORKSPACE,
                    )
                    self.assertEqual(
                        self._drop_platform_flags(pc),
                        self._drop_platform_flags(android),
                    )

    def test_progress_parsing_matches(self):
        lines = [
            'clipora-progress: 42.5%|1.2MiB/s|00:07',
            'clipora-progress:100.0%|NA|NA',
            'clipora-progress:0.0%',
            'clipora-progress:',
            'random yt-dlp line',
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(
                    pc_importer.parse_import_progress(line),
                    android_ytdlp.parse_import_progress(line),
                )
                self.assertEqual(
                    pc_importer.parse_import_progress_detail(line),
                    android_ytdlp.parse_import_progress_detail(line),
                )

    def test_error_classification_matches(self):
        for diagnostics in (
            ['ERROR: unable to download: HTTP Error 403: Forbidden'],
            ['ERROR: [Errno 11001] getaddrinfo failed'],
            ['ERROR: Unable to extract player response; please report this issue'],
            ['ERROR: something else entirely'],
            [],
        ):
            with self.subTest(diagnostics=diagnostics):
                self.assertEqual(
                    pc_importer.is_block_error(diagnostics),
                    android_ytdlp.is_block_error(diagnostics),
                )
                self.assertEqual(
                    pc_importer.is_network_block_error(diagnostics),
                    android_ytdlp.is_network_block_error(diagnostics),
                )
                self.assertEqual(
                    pc_importer.is_extractor_broken_error(diagnostics),
                    android_ytdlp.is_extractor_broken_error(diagnostics),
                )

    def test_reported_output_parsing_matches(self):
        samples = (
            f'{pc_importer._OUTPUT_PREFIX}{WORKSPACE / "a.mp3"}',
            f'{android_ytdlp._OUTPUT_PREFIX}{WORKSPACE / "a.mp3"}',
            'clipora-progress: 1.0%',
            'not-json{',
        )
        for line in samples:
            with self.subTest(line=line):
                self.assertEqual(
                    pc_importer.parse_reported_output(line),
                    android_ytdlp.parse_reported_output(line),
                )

    @staticmethod
    def _drop_platform_flags(command: list[str]) -> list[str]:
        """Remove flags the Android port cannot support, for a fair comparison."""
        boolean_flags = {'--windows-filenames'}
        valued_flags = {
            '--js-runtimes',
            '--impersonate',
            '--ffmpeg-location',
            '--add-header',
            '--extractor-args',
        }
        result: list[str] = []
        skip_next = False
        for item in command:
            if skip_next:
                skip_next = False
                continue
            if item in boolean_flags:
                continue
            if item in valued_flags:
                skip_next = True
                continue
            result.append(item)
        return result


class ProbeFallback(unittest.TestCase):
    """The p4a recipe has no ffprobe, so the ffmpeg fallback is the only path."""

    FFMPEG_REPORT = (
        "Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'clip.mp4':\n"
        '  Duration: 00:01:23.45, start: 0.000000, bitrate: 1500 kb/s\n'
        '  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), '
        'yuv420p, 1920x1080, 30 fps, 30 tbr\n'
        '  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo\n'
    )

    def _patched(self, report: str):
        original_run = android_ffmpeg.subprocess.run
        original_find = android_ffmpeg.find_executable

        def fake_run(*args, **kwargs):
            return type('Result', (), {'stdout': report, 'returncode': 1})()

        android_ffmpeg.subprocess.run = fake_run
        android_ffmpeg.find_executable = lambda name: Path('/usr/bin/ffmpeg')
        self.addCleanup(setattr, android_ffmpeg.subprocess, 'run', original_run)
        self.addCleanup(setattr, android_ffmpeg, 'find_executable', original_find)
        return android_ffmpeg._probe_with_ffmpeg(Path('clip.mp4'))

    def test_parses_duration_and_streams(self):
        info = self._patched(self.FFMPEG_REPORT)
        self.assertAlmostEqual(info.duration or 0, 83.45, places=2)
        self.assertTrue(info.has_video)
        self.assertTrue(info.has_audio)
        self.assertEqual((info.width, info.height), (1920, 1080))

    def test_audio_only(self):
        report = (
            "Input #0, mp3, from 'a.mp3':\n"
            '  Duration: 00:00:30.00, start: 0.000000, bitrate: 128 kb/s\n'
            '  Stream #0:0: Audio: mp3, 44100 Hz, stereo\n'
        )
        info = self._patched(report)
        self.assertFalse(info.has_video)
        self.assertTrue(info.has_audio)
        self.assertIsNone(info.width)

    def test_missing_file_raises(self):
        with self.assertRaises(android_ffmpeg.FFmpegError):
            self._patched("clip.mp4: No such file or directory\n")


class HistoryParity(unittest.TestCase):
    """Same op sequence on both history modules must give the same result."""

    def _snapshot(self, module, path: Path) -> list[tuple]:
        return [
            (entry.kind, entry.source_kind, entry.name, entry.target, entry.source, bool(entry.trashed_at))
            for entry in module.load_history(path)
        ]

    def _run_sequence(self, module, path: Path) -> list[tuple]:
        first = module.add_entry('audio', 'file', 'a.mp3', '/out/a.mp3', source='/in/a.mkv', path=path)
        second = module.add_entry('video', 'url', 'b.mp4', '/out/b.mp4', source='https://x/y', path=path)
        module.add_entry('bogus-kind', 'file', 'c.mp4', '/out/c.mp4', path=path)
        module.trash_entry(first.id, path)
        module.restore_entry(first.id, path)
        module.trash_entry(second.id, path)
        module.remove_entry('no-such-id', path)
        return self._snapshot(module, path)

    def test_same_sequence_same_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            pc_path = Path(tmp) / 'pc.json'
            android_path = Path(tmp) / 'android.json'
            self.assertEqual(
                self._run_sequence(pc_history, pc_path),
                self._run_sequence(android_history, android_path),
            )

    def test_trash_and_clear_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            pc_path = Path(tmp) / 'pc.json'
            android_path = Path(tmp) / 'android.json'
            for module, path in ((pc_history, pc_path), (android_history, android_path)):
                module.add_entry('audio', 'file', 'a.mp3', '/out/a.mp3', path=path)
                module.add_entry('video', 'file', 'b.mp4', '/out/b.mp4', path=path)
                self.assertEqual(module.trash_all(path), 2)
                self.assertEqual(len(module.load_history(path)), 0)
                module.clear_history(path)
            self.assertEqual(
                self._snapshot(pc_history, pc_path),
                self._snapshot(android_history, android_path),
            )


if __name__ == '__main__':
    unittest.main()
