"""Completion chime: short FL Studio-style arpeggio when a job finishes.

Windows-only ``winsound`` on a daemon thread so the UI never blocks;
silently does nothing on other platforms or when audio is unavailable.
"""

from __future__ import annotations

import threading

# A5 → C#6 → E6, short bright arpeggio (frequency Hz, duration ms).
_CHIME_NOTES: tuple[tuple[int, int], ...] = ((880, 110), (1174, 110), (1568, 220))


def _play_notes() -> None:
    try:
        import winsound

        for frequency, duration in _CHIME_NOTES:
            winsound.Beep(frequency, duration)
    except Exception:
        pass


def play_completion_chime() -> None:
    """Fire-and-forget completion sound; never raises, never blocks."""
    threading.Thread(target=_play_notes, daemon=True).start()
