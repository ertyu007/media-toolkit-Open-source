import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from clipora.ffmpeg import FFmpegError, check_disk_space
from clipora.importer import (
    URLImportError,
    check_destination_disk_space,
    cleanup_orphaned_import_workspaces,
)
from clipora.separator import cleanup_orphaned_workspaces


def _usage(free_bytes: int) -> SimpleNamespace:
    return SimpleNamespace(total=free_bytes, used=0, free=free_bytes)


class LocalDiskSpaceTests(unittest.TestCase):
    @patch('clipora.ffmpeg.shutil.disk_usage', return_value=_usage(10 * 1024 * 1024))
    def test_low_disk_space_is_rejected(self, _disk_usage):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FFmpegError, 'พื้นที่ดิสก์ไม่เพียงพอ'):
                check_disk_space(Path(directory))

    @patch('clipora.ffmpeg.shutil.disk_usage', return_value=_usage(10 * 1024 * 1024 * 1024))
    def test_enough_disk_space_passes(self, _disk_usage):
        with TemporaryDirectory() as directory:
            check_disk_space(Path(directory))

    @patch('clipora.ffmpeg.shutil.disk_usage', side_effect=OSError('no disk info'))
    def test_unreadable_disk_info_does_not_block(self, _disk_usage):
        with TemporaryDirectory() as directory:
            check_disk_space(Path(directory))

    def test_missing_destination_is_ignored(self):
        check_disk_space(Path('definitely-missing-folder-xyz'))


class ImportDiskSpaceTests(unittest.TestCase):
    @patch('clipora.importer.shutil.disk_usage', return_value=_usage(10 * 1024 * 1024))
    def test_low_disk_space_is_rejected(self, _disk_usage):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(URLImportError, 'พื้นที่ดิสก์ไม่เพียงพอ'):
                check_destination_disk_space(Path(directory))

    @patch('clipora.importer.shutil.disk_usage', return_value=_usage(10 * 1024 * 1024 * 1024))
    def test_enough_disk_space_passes(self, _disk_usage):
        with TemporaryDirectory() as directory:
            check_destination_disk_space(Path(directory))

    @patch('clipora.importer.shutil.disk_usage', side_effect=OSError('no disk info'))
    def test_unreadable_disk_info_does_not_block(self, _disk_usage):
        with TemporaryDirectory() as directory:
            check_destination_disk_space(Path(directory))


class OrphanedWorkspaceCleanupTests(unittest.TestCase):
    def _seed_destination(self, root: Path) -> dict[str, Path]:
        entries = {
            'import_orphan': root / '.clipora-import-abc123',
            'separator_orphan': root / '.clipora-separate-xyz789',
            'bare_import_prefix': root / '.clipora-import-',
            'bare_separator_prefix': root / '.clipora-separate-',
            'regular_folder': root / 'my videos',
            'regular_file': root / '.clipora-import-notes.txt',
        }
        entries['import_orphan'].mkdir()
        (entries['import_orphan'] / 'partial.mp4').write_bytes(b'partial')
        entries['separator_orphan'].mkdir()
        (entries['separator_orphan'] / 'stem.wav').write_bytes(b'partial')
        entries['bare_import_prefix'].mkdir()
        entries['bare_separator_prefix'].mkdir()
        entries['regular_folder'].mkdir()
        entries['regular_file'].write_text('keep me', encoding='utf-8')
        return entries

    def test_orphaned_workspaces_are_removed_and_others_kept(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            entries = self._seed_destination(root)

            cleanup_orphaned_import_workspaces(root)
            cleanup_orphaned_workspaces(root)

            self.assertFalse(entries['import_orphan'].exists())
            self.assertFalse(entries['separator_orphan'].exists())
            self.assertTrue(entries['bare_import_prefix'].is_dir())
            self.assertTrue(entries['bare_separator_prefix'].is_dir())
            self.assertTrue(entries['regular_folder'].is_dir())
            self.assertTrue(entries['regular_file'].is_file())

    def test_missing_destination_is_ignored(self):
        missing = Path('definitely-missing-folder-xyz')
        cleanup_orphaned_import_workspaces(missing)
        cleanup_orphaned_workspaces(missing)


if __name__ == '__main__':
    unittest.main()
