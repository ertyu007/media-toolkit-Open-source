import unittest

from clipora.sound import (
    _CHIME_GAP_SECONDS,
    _CHIME_NOTES,
    play_completion_chime,
)


def _midi_frequency(midi: int) -> float:
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


class ChimeTests(unittest.TestCase):
    def test_notes_form_a_major_arpeggio(self):
        # A5 (MIDI 81) → C#6 (85) → E6 (88); the old table had D6/G6 here,
        # which is why the chime sounded off.
        for (frequency, _duration), midi in zip(_CHIME_NOTES, (81, 85, 88)):
            self.assertAlmostEqual(frequency, _midi_frequency(midi), delta=2.0)

    def test_chime_is_short(self):
        total_ms = sum(duration for _frequency, duration in _CHIME_NOTES)
        total_ms += _CHIME_GAP_SECONDS * 1000 * (len(_CHIME_NOTES) - 1)
        self.assertGreater(total_ms, 0)
        self.assertLess(total_ms, 600)
        for _frequency, duration in _CHIME_NOTES:
            self.assertGreater(duration, 0)

    def test_fire_and_forget_never_raises(self):
        play_completion_chime()


if __name__ == '__main__':
    unittest.main()
