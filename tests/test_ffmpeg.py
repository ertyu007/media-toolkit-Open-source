import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from clipora.ffmpeg import (
    CancellationToken,
    ConversionCancelled,
    MediaInfo,
    UnsupportedMediaError,
    build_command,
    cleanup_temporary_output,
    convert,
    finalize_output,
    output_path,
    parse_progress_line,
    probe,
    temporary_output_path,
    validate_operation,
)


class FFmpegCommandTests(unittest.TestCase):
    def test_audio_output_path(self):
        self.assertEqual(
            output_path(Path('sample.final.mp4'), Path('out'), 'audio', 'MP3'),
            Path('out/sample.final_audio.mp3'),
        )

    def test_video_output_path(self):
        self.assertEqual(
            output_path(Path('sample.mov'), Path('out'), 'video', 'mp3'),
            Path('out/sample_converted.mp4'),
        )

    def test_audio_command_maps_first_audio_and_drops_video(self):
        command = build_command(Path('in.mp4'), Path('out.mp3'), 'audio', 'Balanced', 'mp3')
        self.assertIn('-vn', command)
        self.assertIn('libmp3lame', command)
        self.assertEqual(command[command.index('-map') + 1], '0:a:0')

    def test_video_command_uses_quality_and_optional_audio(self):
        command = build_command(Path('in.mov'), Path('out.mp4'), 'video', 'High', 'mp3')
        self.assertEqual(command[command.index('-crf') + 1], '18')
        self.assertIn('0:a:0?', command)
        self.assertIn('+faststart', command)

    def test_paths_are_single_arguments(self):
        source = Path('โฟลเดอร์ test/input & clip.mp4')
        target = Path('output folder/result.mp3')
        command = build_command(source, target, 'audio', 'Balanced', 'mp3')
        self.assertIn(str(source), command)
        self.assertIn(str(target), command)

    def test_invalid_options_are_rejected(self):
        with self.assertRaises(ValueError):
            build_command(Path('in'), Path('out'), 'audio', 'Balanced', 'aiff')
        with self.assertRaises(ValueError):
            build_command(Path('in'), Path('out'), 'video', 'Ultra', 'mp3')
        with self.assertRaises(ValueError):
            build_command(Path('in'), Path('out'), 'video', 'High', 'mp3', 'avi')
        with self.assertRaises(ValueError):
            build_command(Path('in'), Path('out'), 'unknown', 'High', 'mp3')

    def test_audio_command_accepts_lossless_and_opus(self):
        for audio_format, encoder in (
            ('wav', 'pcm_s16le'),
            ('flac', 'flac'),
            ('opus', 'libopus'),
        ):
            with self.subTest(audio_format=audio_format):
                command = build_command(
                    Path('in.mp4'),
                    Path('out'),
                    'audio',
                    'Balanced',
                    audio_format,
                )
                self.assertIn(encoder, command)
                self.assertIn('-vn', command)

    def test_mov_output_path(self):
        self.assertEqual(
            output_path(Path('sample.mov'), Path('out'), 'video', 'mp3', 'mov'),
            Path('out/sample_converted.mov'),
        )

    @patch('clipora.ffmpeg.prores_encoder', return_value='prores_ks')
    def test_video_command_mov_uses_prores_encoder(self, _prores_encoder):
        command = build_command(
            Path('in.mp4'),
            Path('out'),
            'video',
            'High',
            'mp3',
            'mov',
        )
        self.assertIn('prores_ks', command)
        self.assertEqual(command[command.index('-profile:v') + 1], '3')
        self.assertEqual(command[command.index('-pix_fmt') + 1], 'yuv422p10le')
        self.assertIn('pcm_s16le', command)

    @patch('clipora.ffmpeg.prores_encoder', return_value=None)
    def test_mov_requires_prores_support(self, _prores_encoder):
        with self.assertRaisesRegex(ValueError, 'ProRes'):
            build_command(Path('in.mp4'), Path('out'), 'video', 'High', 'mp3', 'mov')

    def test_video_command_applies_fps_cap(self):
        for fps, expected in (('60', '-r'), ('30', '-r')):
            with self.subTest(fps=fps):
                command = build_command(
                    Path('in.mp4'),
                    Path('out'),
                    'video',
                    'High',
                    'mp3',
                    'mp4',
                    fps,
                )
                self.assertEqual(command[command.index('-r') + 1], fps)

    def test_video_command_without_fps_cap_has_no_rate_flag(self):
        command = build_command(
            Path('in.mp4'),
            Path('out'),
            'video',
            'High',
            'mp3',
            'mp4',
            'สูงสุด',
        )
        self.assertNotIn('-r', command)


class MediaValidationTests(unittest.TestCase):
    def test_audio_mode_requires_audio_stream(self):
        info = MediaInfo(1.0, has_video=True, has_audio=False)
        with self.assertRaisesRegex(UnsupportedMediaError, 'ไม่มีเสียง'):
            validate_operation(info, 'audio')

    def test_video_mode_requires_video_stream(self):
        info = MediaInfo(1.0, has_video=False, has_audio=True)
        with self.assertRaisesRegex(UnsupportedMediaError, 'ไม่มีภาพ'):
            validate_operation(info, 'video')

    def test_valid_streams_pass(self):
        info = MediaInfo(1.0, has_video=True, has_audio=True)
        validate_operation(info, 'audio')
        validate_operation(info, 'video')


class FFmpegProbeTests(unittest.TestCase):
    @patch('clipora.ffmpeg.find_executable', return_value=Path('C:/fake/ffprobe.exe'))
    @patch('clipora.ffmpeg.subprocess.run')
    def test_probe_runs_ffprobe_hidden_on_windows(self, run, _find_executable):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout='{"format":{"duration":"1.0"},"streams":[]}',
            stderr='',
        )

        info = probe(Path('clip.mp4'))

        self.assertEqual(info.duration, 1.0)
        self.assertFalse(info.has_video)
        self.assertFalse(info.has_audio)
        self.assertIn('creationflags', run.call_args.kwargs)
        command = run.call_args.args[0]
        self.assertEqual(command[0], str(Path('C:/fake/ffprobe.exe')))


class ProgressParserTests(unittest.TestCase):
    def test_parses_timestamp(self):
        self.assertAlmostEqual(parse_progress_line('out_time=00:00:02.500000', 10.0), 0.25)

    def test_parses_microseconds(self):
        self.assertAlmostEqual(parse_progress_line('out_time_us=2500000', 10.0), 0.25)

    def test_clamps_progress(self):
        self.assertEqual(parse_progress_line('out_time=00:00:12.000000', 10.0), 1.0)

    def test_end_is_complete_without_duration(self):
        self.assertEqual(parse_progress_line('progress=end', None), 1.0)

    def test_ignores_malformed_or_unknown_values(self):
        self.assertIsNone(parse_progress_line('not a record', 10.0))
        self.assertIsNone(parse_progress_line('out_time=nope', 10.0))
        self.assertIsNone(parse_progress_line('frame=20', 10.0))
        self.assertIsNone(parse_progress_line('out_time=00:00:01.000000', None))


class OutputLifecycleTests(unittest.TestCase):
    def test_temporary_output_keeps_directory_and_extension(self):
        target = Path('out/clip_audio.mp3')
        temporary = temporary_output_path(target)
        self.assertEqual(temporary.parent, target.parent)
        self.assertEqual(temporary.suffix, target.suffix)
        self.assertNotEqual(temporary, target)
        self.assertTrue(temporary.name.startswith('.clip_audio.clipora-'))

    def test_finalize_replaces_existing_target_only_after_success(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'result.mp3'
            temporary = temporary_output_path(target)
            target.write_bytes(b'original')
            temporary.write_bytes(b'completed output')

            finalize_output(temporary, target)

            self.assertEqual(target.read_bytes(), b'completed output')
            self.assertFalse(temporary.exists())

    def test_cleanup_removes_only_matching_temporary_output(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'result.mp3'
            temporary = temporary_output_path(target)
            unrelated = Path(directory) / 'unrelated.mp3'
            temporary.write_bytes(b'partial')
            unrelated.write_bytes(b'keep')

            cleanup_temporary_output(temporary, target)

            self.assertFalse(temporary.exists())
            self.assertTrue(unrelated.exists())
            with self.assertRaises(ValueError):
                cleanup_temporary_output(unrelated, target)

    def test_pre_cancelled_conversion_does_not_start_process(self):
        cancellation = CancellationToken()
        cancellation.cancel()
        with self.assertRaises(ConversionCancelled):
            convert(
                ['ffmpeg', 'this command must not run'],
                Path('unused.mp4'),
                1.0,
                lambda _: None,
                cancellation,
            )


if __name__ == '__main__':
    unittest.main()
