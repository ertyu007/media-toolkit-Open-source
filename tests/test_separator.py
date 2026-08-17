import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clipora.separator import (
    INSTRUMENTAL_SOURCES,
    SEPARATOR_MODEL,
    SELECTABLE_STEMS,
    CancellationToken,
    SeparatorNotInstalled,
    build_instrumental_command,
    build_separate_command,
    cleanup_workspace,
    create_workspace,
    parse_demucs_progress,
    separate_output_path,
    separate_output_paths,
)


class SeparateCommandTests(unittest.TestCase):
    @patch('clipora.separator.find_separator_python')
    def test_builds_offline_repo_command(self, find_python):
        find_python.return_value = Path('C:/sep/python.exe')
        source = Path('C:/media/song.wav')
        out_dir = Path('C:/tmp/stems')

        command = build_separate_command(source, out_dir)

        self.assertEqual(command[0], str(Path('C:/sep/python.exe')))
        self.assertEqual(command[1:5], ['-m', 'demucs', '-n', SEPARATOR_MODEL])
        self.assertIn('--repo', command)
        self.assertIn('--device', command)
        self.assertEqual(command[command.index('--device') + 1], 'cpu')
        self.assertEqual(command[command.index('--filename') + 1], '{stem}.{ext}')
        self.assertEqual(command[-1], str(source))

    def test_missing_python_raises_separator_not_installed(self):
        with patch('clipora.separator.find_separator_python', return_value=None):
            with self.assertRaises(SeparatorNotInstalled):
                build_separate_command(Path('a.wav'), Path('out'))

    def test_instrumental_command_uses_labeled_amix(self):
        stem_dir = Path('C:/tmp/stems/htdemucs_6s')
        target = Path('C:/tmp/inst.wav')

        command = build_instrumental_command(stem_dir, target)

        self.assertEqual(command.count('-i'), len(INSTRUMENTAL_SOURCES))
        for source in INSTRUMENTAL_SOURCES:
            self.assertIn(str(stem_dir / f'{source}.wav'), command)
        filter_complex = command[command.index('-filter_complex') + 1]
        self.assertTrue(filter_complex.endswith('amix=inputs=5:normalize=0:dropout_transition=0[aout]'))
        self.assertEqual(command[command.index('-map') + 1], '[aout]')
        self.assertEqual(command[-1], str(target))


class ProgressParsingTests(unittest.TestCase):
    def test_percent_within_line_is_extracted(self):
        self.assertEqual(parse_demucs_progress('  50%|#################### | 11.7/23.4 [00:45<00:45,  1.92s/it]'), 0.5)

    def test_decimal_percent_is_clamped(self):
        self.assertEqual(parse_demucs_progress('0.0%'), 0.0)
        self.assertEqual(parse_demucs_progress('100.0%'), 1.0)
        self.assertEqual(parse_demucs_progress('250%'), 1.0)

    def test_unrelated_lines_return_none(self):
        self.assertIsNone(parse_demucs_progress('Loaded model htdemucs_6s'))
        self.assertIsNone(parse_demucs_progress(''))


class OutputPathTests(unittest.TestCase):
    def test_output_path_combines_source_stem_and_stem(self):
        source = Path('C:/media/เพลง ไทย.wav')
        self.assertEqual(
            separate_output_path(source, Path('C:/out'), 'mp3', 'vocals'),
            Path('C:/out/เพลง ไทย_vocals.mp3'),
        )

    def test_output_paths_map_each_selected_stem(self):
        source = Path('C:/media/song.wav')
        paths = separate_output_paths(source, Path('C:/out'), 'wav', ('vocals', 'instrumental'))
        self.assertEqual(
            paths,
            (Path('C:/out/song_vocals.wav'), Path('C:/out/song_instrumental.wav')),
        )

    def test_default_selection_covers_all_available_stems(self):
        source = Path('C:/media/song.wav')
        paths = separate_output_paths(source, Path('C:/out'), 'mp3', SELECTABLE_STEMS)
        self.assertEqual(len(paths), len(SELECTABLE_STEMS))


class WorkspaceTests(unittest.TestCase):
    def test_workspace_is_created_and_cleaned_up(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            workspace = create_workspace(destination)
            self.assertTrue(workspace.is_dir())
            self.assertEqual(workspace.parent, destination)
            (workspace / 'stems').mkdir()
            cleanup_workspace(workspace, destination)
            self.assertFalse(workspace.exists())

    def test_cleanup_refuses_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            foreign = destination / 'important'
            foreign.mkdir()
            with self.assertRaises(ValueError):
                cleanup_workspace(foreign, destination)
            self.assertTrue(foreign.exists())

    def test_cleanup_refuses_destination_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            with self.assertRaises(ValueError):
                cleanup_workspace(destination, destination)


class InstrumentalCommandSmokeTests(unittest.TestCase):
    def test_builds_a_valid_amix_filtergraph(self):
        stem_dir = Path('C:/tmp/stems/htdemucs_6s')
        command = build_instrumental_command(stem_dir, Path('C:/tmp/inst.wav'))
        filter_complex = command[command.index('-filter_complex') + 1]
        self.assertIn('amix', filter_complex)
        self.assertIn('[aout]', filter_complex)


if __name__ == '__main__':
    unittest.main()