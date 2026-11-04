"""Pure helpers for the desktop URL queue.

The queue is a plain sequence of validated public URLs kept by the UI. This
module holds the small, Tk-free pieces so they can be unit tested without a
display: append/remove, aggregate progress and the short Thai summary label.
"""

from __future__ import annotations

from typing import Sequence

from .importer import validate_url

DUPLICATE_MESSAGE = 'ลิงก์นี้อยู่ในคิวแล้ว'
EMPTY_QUEUE_MESSAGE = 'ยังไม่มีลิงก์ในคิว'


def add_url(queue: Sequence[str], raw: str) -> tuple[str, ...]:
    """Validate ``raw`` and append it to a copy of ``queue``.

    Raises ``ValueError`` with the importer core's Thai message for invalid
    links, or with a Thai duplicate message when the same link (ignoring case)
    is already queued.
    """
    url = validate_url(raw)
    key = url.lower()
    if any(item.strip().lower() == key for item in queue):
        raise ValueError(DUPLICATE_MESSAGE)
    return (*queue, url)


def remove_at(queue: Sequence[str], index: int) -> tuple[str, ...]:
    """Return a copy of ``queue`` without the item at ``index``."""
    if index < 0 or index >= len(queue):
        raise IndexError('ไม่มีรายการนี้ในคิว')
    return (*queue[:index], *queue[index + 1:])


def aggregate_percent(index: int, total: int, item_percent: float) -> float:
    """Overall progress for the 1-based queue ``index`` out of ``total``.

    The value is the completed items plus the current item's progress share,
    clamped to 0..100. Item 2 of 4 at 50% is 37.5%.
    """
    if total <= 0:
        return 0.0
    try:
        item = float(item_percent)
    except (TypeError, ValueError):
        item = 0.0
    overall = ((index - 1) + item / 100.0) / total * 100.0
    return max(0.0, min(100.0, overall))


def queue_summary(queue: Sequence[str]) -> str:
    """Short Thai label for the queue panel header."""
    count = len(queue)
    if count == 0:
        return EMPTY_QUEUE_MESSAGE
    return f'คิว {count} ลิงก์'
