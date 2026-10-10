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
    build_av_select_filter,
    build_command,
    build_enhance_filter,
    cleanup_temporary_output,
    collision_free_output_path,
    convert,
    finalize_output,
    keep_intervals,
    normalize_trim,
    output_path,
    parse_progress_line,
    parse_silence_report,
    parse_trim_seconds,
    probe,
    temporary_output_path,
    validate_operation,
    validate_output,
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


class TrimParsingTests(unittest.TestCase):
    def test_blank_input_means_no_trim(self):
        self.assertIsNone(parse_trim_seconds(None))
        self.assertIsNone(parse_trim_seconds(''))
        self.assertIsNone(parse_trim_seconds('   '))

    def test_plain_seconds(self):
        self.assertAlmostEqual(parse_trim_seconds('90'), 90.0)
        self.assertAlmostEqual(parse_trim_seconds(' 90.5 '), 90.5)
        self.assertAlmostEqual(parse_trim_seconds('0'), 0.0)

    def test_clock_formats(self):
        self.assertAlmostEqual(parse_trim_seconds('1:30'), 90.0)
        self.assertAlmostEqual(parse_trim_seconds('01:02:03'), 3723.0)
        self.assertAlmostEqual(parse_trim_seconds('0:01:02.5'), 62.5)

    def test_invalid_input_is_rejected(self):
        for text in ('abc', '-5', '1:2:3:4', '1:60', '1::30', '12:34:56:78', 'NaN', 'inf'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_trim_seconds(text)


class TrimNormalizeTests(unittest.TestCase):
    def test_no_trim_passes_media_duration_through(self):
        self.assertEqual(normalize_trim(None, None, 120.0), (None, None, 120.0))
        self.assertEqual(normalize_trim(None, None, None), (None, None, None))

    def test_start_only_uses_remaining_media_as_effective_duration(self):
        start, duration, effective = normalize_trim(30.0, None, 120.0)
        self.assertEqual(start, '30.000')
        self.assertIsNone(duration)
        self.assertAlmostEqual(effective, 90.0)

    def test_duration_is_clamped_to_remaining_media(self):
        start, duration, effective = normalize_trim(110.0, 30.0, 120.0)
        self.assertEqual(start, '110.000')
        self.assertEqual(duration, '10.000')
        self.assertAlmostEqual(effective, 10.0)

    def test_exact_bounds_are_formatted_for_ffmpeg(self):
        start, duration, effective = normalize_trim(10.0, 5.0, 120.0)
        self.assertEqual((start, duration), ('10.000', '5.000'))
        self.assertAlmostEqual(effective, 5.0)

    def test_out_of_range_bounds_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'เกินความยาวไฟล์'):
            normalize_trim(120.0, None, 120.0)
        with self.assertRaisesRegex(ValueError, 'เกินความยาวไฟล์'):
            normalize_trim(200.0, 5.0, 120.0)
        with self.assertRaisesRegex(ValueError, 'มากกว่า 0'):
            normalize_trim(10.0, 0.0, 120.0)
        with self.assertRaises(ValueError):
            normalize_trim(-1.0, None, 120.0)

    def test_unknown_media_duration_passes_values_through(self):
        self.assertEqual(normalize_trim(10.0, 5.0, None), ('10.000', '5.000', None))


class TrimCommandTests(unittest.TestCase):
    def test_trim_args_are_placed_around_input(self):
        command = build_command(
            Path('in.mp4'), Path('out.mp3'), 'audio', 'Balanced', 'mp3',
            start_time='10.000', duration_time='5.000',
        )
        self.assertEqual(command[command.index('-ss') + 1], '10.000')
        self.assertLess(command.index('-ss'), command.index('-i'))
        self.assertEqual(command[command.index('-t') + 1], '5.000')
        self.assertGreater(command.index('-t'), command.index('-i'))

    def test_no_trim_adds_no_seek_flags(self):
        command = build_command(Path('in.mp4'), Path('out.mp3'), 'audio', 'Balanced', 'mp3')
        self.assertNotIn('-ss', command)
        self.assertNotIn('-t', command)


class EnhanceFilterTests(unittest.TestCase):
    def test_filter_covers_all_requested_effects(self):
        filtr = build_enhance_filter()
        for token in ('silenceremove', 'highpass', 'afftdn', 'acompressor', 'loudnorm=I=-16'):
            self.assertIn(token, filtr)

    def test_enhance_off_by_default_keeps_old_command(self):
        command = build_command(Path('in.mp4'), Path('out.mp3'), 'audio', 'Balanced', 'mp3')
        self.assertNotIn('-af', command)

    def test_enhance_on_injects_single_af(self):
        for mode in ('audio', 'video'):
            with self.subTest(mode=mode):
                command = build_command(
                    Path('in.mp4'), Path('out.mp3'), mode, 'Balanced', 'mp3', enhance=True,
                )
                self.assertIn('-af', command)
                self.assertEqual(command.count('-af'), 1)
                self.assertIn('loudnorm', command[command.index('-af') + 1])
                self.assertLess(command.index('-af'), command.index('-progress'))


class SilenceCutTests(unittest.TestCase):
    def test_parses_start_end_pairs(self):
        report = (
            '[silencedetect @ 0] silence_start: 1.000\n'
            '[silencedetect @ 0] silence_end: 2.500 | silence_duration: 1.500\n'
        )
        self.assertEqual(parse_silence_report(report, 10.0), [(1.0, 2.5)])

    def test_trailing_silence_closes_at_duration(self):
        self.assertEqual(
            parse_silence_report('[silencedetect @ 0] silence_start: 8.000\n', 10.0),
            [(8.0, 10.0)],
        )

    def test_end_without_start_counts_from_zero(self):
        self.assertEqual(
            parse_silence_report('[silencedetect @ 0] silence_end: 0.500 | silence_duration: 0.5\n', 10.0),
            [(0.0, 0.5)],
        )

    def test_negative_start_is_clamped_downstream(self):
        report = '[silencedetect @ 0] silence_start: -0.034\nsilence_end: 1.0 | x\n'
        self.assertEqual(parse_silence_report(report, 10.0), [(-0.034, 1.0)])
        self.assertEqual(
            keep_intervals([(-0.034, 1.0)], 10.0, pad=0.25),
            [(0.0, 0.216), (0.75, 10.0)],
        )

    def test_keep_is_complement_with_padded_edges(self):
        # 1s silence at 1.0-2.0, pad 0.25 -> cut (1.25, 1.75).
        self.assertEqual(
            keep_intervals([(1.0, 2.0)], 3.0),
            [(0.0, 1.25), (1.75, 3.0)],
        )

    def test_short_silence_survives_as_keep(self):
        # 0.3s pause narrows to nothing -> breaths are kept.
        self.assertEqual(keep_intervals([(1.0, 1.3)], 3.0, pad=0.25), [(0.0, 3.0)])

    def test_overlapping_silences_merge(self):
        keeps = keep_intervals([(1.0, 2.0), (1.8, 2.5)], 4.0, pad=0.0)
        self.assertEqual(keeps, [(0.0, 1.0), (2.5, 4.0)])

    def test_select_filter_covers_both_streams(self):
        video_filter, audio_filter = build_av_select_filter([(0.0, 1.25), (1.75, 3.0)])
        self.assertIn("between(t,0.000,1.250)", video_filter)
        self.assertIn('setpts=N/FRAME_RATE/TB', video_filter)
        self.assertIn("between(t,0.000,1.250)", audio_filter)
        self.assertIn('asetpts=N/SR/TB', audio_filter)


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

    @patch('clipora.ffmpeg.probe', return_value=MediaInfo(1.0, True, True))
    def test_output_validation_probes_and_accepts_required_stream(self, probe_mock):
        info = validate_output(Path('result.mp4'), 'video')

        self.assertTrue(info.has_video)
        probe_mock.assert_called_once_with(Path('result.mp4'))

    @patch('clipora.ffmpeg.probe', return_value=MediaInfo(1.0, True, False))
    def test_output_validation_rejects_missing_audio(self, _probe_mock):
        with self.assertRaisesRegex(UnsupportedMediaError, 'ไม่มีเสียง'):
            validate_output(Path('result.mp3'), 'audio')


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
    def test_collision_free_output_path_avoids_existing_siblings(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'clip_video.mp4'
            target.write_bytes(b'old')
            (Path(directory) / 'clip_video (1).mp4').write_bytes(b'old')

            self.assertEqual(
                collision_free_output_path(target),
                Path(directory) / 'clip_video (2).mp4',
            )

    def test_collision_free_output_path_avoids_reserved_batch_names(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'clip_audio.mp3'
            self.assertEqual(
                collision_free_output_path(target, {'CLIP_AUDIO.MP3'}),
                Path(directory) / 'clip_audio (1).mp3',
            )

    def test_temporary_output_keeps_directory_and_extension(self):
        target = Path('out/clip_audio.mp3')
        temporary = temporary_output_path(target)
        self.assertEqual(temporary.parent, target.parent)
        self.assertEqual(temporary.suffix, target.suffix)
        self.assertNotEqual(temporary, target)
        self.assertTrue(temporary.name.startswith('.clip_audio.clipora-'))

    def test_finalize_preserves_target_that_appeared_during_job(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'result.mp3'
            temporary = temporary_output_path(target)
            target.write_bytes(b'original')
            temporary.write_bytes(b'completed output')

            with self.assertRaises(FileExistsError):
                finalize_output(temporary, target, overwrite=False)

            self.assertEqual(target.read_bytes(), b'original')
            self.assertEqual(temporary.read_bytes(), b'completed output')

    def test_finalize_replaces_target_after_explicit_overwrite(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'result.mp3'
            temporary = temporary_output_path(target)
            target.write_bytes(b'original')
            temporary.write_bytes(b'completed output')

            finalize_output(temporary, target, overwrite=True)

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
