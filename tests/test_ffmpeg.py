import unittest
from pathlib import Path

from clipora.ffmpeg import (
    MediaInfo,
    UnsupportedMediaError,
    build_command,
    output_path,
    parse_progress_line,
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
            build_command(Path('in'), Path('out'), 'audio', 'Balanced', 'wav')
        with self.assertRaises(ValueError):
            build_command(Path('in'), Path('out'), 'video', 'Ultra', 'mp3')
        with self.assertRaises(ValueError):
            build_command(Path('in'), Path('out'), 'unknown', 'High', 'mp3')


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


if __name__ == '__main__':
    unittest.main()
