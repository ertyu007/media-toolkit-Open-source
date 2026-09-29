"""Completion chime: short FL Studio-style arpeggio when a job finishes.

Windows-only ``winsound`` on a daemon thread so the UI never blocks;
silently does nothing on other platforms or when audio is unavailable.
"""

from __future__ import annotations

import threading
import time

# True A-major arpeggio A5 → C#6 → E6 (frequency Hz, duration ms) with a
# short gap between notes so they don't smear into each other.
_CHIME_NOTES: tuple[tuple[int, int], ...] = ((880, 100), (1109, 100), (1319, 220))
_CHIME_GAP_SECONDS = 0.025


def _play_notes() -> None:
    try:
        import winsound

        for index, (frequency, duration) in enumerate(_CHIME_NOTES):
            if index:
                time.sleep(_CHIME_GAP_SECONDS)
            winsound.Beep(frequency, duration)
    except Exception:
        pass


def play_completion_chime() -> None:
    """Fire-and-forget completion sound; never raises, never blocks."""
    threading.Thread(target=_play_notes, daemon=True).start()
