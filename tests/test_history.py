import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from clipora.history import (
    HISTORY_LIMIT,
    add_entry,
    clear_history,
    load_history,
    remove_entry,
)


class HistoryCoreTests(unittest.TestCase):
    def setUp(self):
        self._directory = TemporaryDirectory()
        self.path = Path(self._directory.name) / 'history.json'

    def tearDown(self):
        self._directory.cleanup()

    def test_missing_file_loads_empty(self):
        self.assertEqual(load_history(self.path), [])

    def test_add_and_load_round_trip_newest_first(self):
        first = add_entry('audio', 'url', 'song.mp3', Path('/out/song.mp3'),
                          source='https://example.com/v', path=self.path)
        second = add_entry('video', 'file', 'clip.mp4', Path('/out/clip.mp4'),
                           path=self.path)
        entries = load_history(self.path)
        self.assertEqual([entry.id for entry in entries], [second.id, first.id])
        self.assertEqual(entries[0].kind, 'video')
        self.assertEqual(entries[1].source, 'https://example.com/v')

    def test_unknown_kind_falls_back_to_video(self):
        entry = add_entry('???', 'url', 'x', 'out/x', path=self.path)
        self.assertEqual(entry.kind, 'video')

    def test_remove_entry_by_id(self):
        kept = add_entry('audio', 'url', 'keep.mp3', 'out/keep.mp3', path=self.path)
        gone = add_entry('audio', 'url', 'gone.mp3', 'out/gone.mp3', path=self.path)
        self.assertTrue(remove_entry(gone.id, self.path))
        self.assertEqual([entry.id for entry in load_history(self.path)], [kept.id])
        self.assertFalse(remove_entry('no-such-id', self.path))

    def test_clear_history(self):
        add_entry('audio', 'url', 'a.mp3', 'out/a.mp3', path=self.path)
        clear_history(self.path)
        self.assertEqual(load_history(self.path), [])

    def test_corrupt_file_loads_empty_and_recovers(self):
        self.path.write_text('{not json', encoding='utf-8')
        self.assertEqual(load_history(self.path), [])
        add_entry('stems', 'file', 's.zip', 'out/s.zip', path=self.path)
        self.assertEqual(len(load_history(self.path)), 1)

    def test_history_is_capped(self):
        for index in range(HISTORY_LIMIT + 5):
            add_entry('audio', 'url', f'{index}.mp3', f'out/{index}.mp3', path=self.path)
        entries = load_history(self.path)
        self.assertEqual(len(entries), HISTORY_LIMIT)
        names = [entry.name for entry in entries]
        self.assertIn(f'{HISTORY_LIMIT + 4}.mp3', names)
        self.assertNotIn('0.mp3', names)

    def test_persists_json_shape(self):
        target = Path('/out/clip.mp4')
        add_entry('video', 'file', 'clip.mp4', target, path=self.path)
        data = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(data[0]['kind'], 'video')
        self.assertEqual(data[0]['target'], str(target))


if __name__ == '__main__':
    unittest.main()
