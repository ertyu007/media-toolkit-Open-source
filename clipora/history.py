"""Download/separation history: where finished outputs were saved.

Stored as a capped JSON list next to the app settings file. All paths are
only ever read for display and opening; this module never deletes media.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .tools import managed_tools_dir

HISTORY_LIMIT = 200

# Trashed entries are hidden from the main list and purged for good after this.
TRASH_RETENTION_DAYS = 30
TRASH_RETENTION_SECONDS = TRASH_RETENTION_DAYS * 24 * 60 * 60

KINDS = ('audio', 'video', 'stems')
KIND_LABELS = {'audio': 'เพลง', 'video': 'วิดีโอ', 'stems': 'Stem'}


@dataclass(frozen=True)
class HistoryEntry:
    id: str
    finished_at: float
    kind: str
    source_kind: str
    name: str
    target: str
    source: str = ''
    trashed_at: float = 0.0


def _history_file_path() -> Path:
    base = managed_tools_dir().parent
    base.mkdir(parents=True, exist_ok=True)
    return base / 'history.json'


def _coerce_entry(data: Any) -> HistoryEntry | None:
    if not isinstance(data, dict):
        return None
    try:
        kind = str(data.get('kind', ''))
        return HistoryEntry(
            id=str(data.get('id', '')) or uuid.uuid4().hex,
            finished_at=float(data.get('finished_at', 0.0)),
            kind=kind if kind in KINDS else 'video',
            source_kind=str(data.get('source_kind', '')),
            name=str(data.get('name', '')),
            target=str(data.get('target', '')),
            source=str(data.get('source', '')),
            trashed_at=float(data.get('trashed_at', 0.0) or 0.0),
        )
    except (TypeError, ValueError):
        return None


def _read_all(path: Path | None = None) -> tuple[list[HistoryEntry], Path]:
    """All stored entries (including trash); purges trash past retention."""
    file_path = path or _history_file_path()
    if not file_path.is_file():
        return [], file_path
    try:
        data = json.loads(file_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return [], file_path
    if not isinstance(data, list):
        return [], file_path
    entries = [entry for item in data if (entry := _coerce_entry(item)) is not None]
    now = time.time()
    fresh = [
        entry
        for entry in entries
        if not entry.trashed_at or now - entry.trashed_at < TRASH_RETENTION_SECONDS
    ]
    if len(fresh) != len(entries):
        _write_entries(fresh, file_path)
    fresh.sort(key=lambda entry: entry.finished_at, reverse=True)
    return fresh, file_path


def load_history(path: Path | None = None) -> list[HistoryEntry]:
    """Load non-trashed entries newest-first; corrupt/missing → empty list."""
    entries, _file_path = _read_all(path)
    return [entry for entry in entries if not entry.trashed_at]


def load_trash(path: Path | None = None) -> list[HistoryEntry]:
    """Load trashed entries newest-trashed-first (auto-purges past retention)."""
    entries, _file_path = _read_all(path)
    trashed = [entry for entry in entries if entry.trashed_at]
    trashed.sort(key=lambda entry: entry.trashed_at, reverse=True)
    return trashed


def _write_entries(entries: list[HistoryEntry], path: Path | None = None) -> None:
    file_path = path or _history_file_path()
    try:
        tmp_path = file_path.with_suffix('.tmp')
        tmp_path.write_text(
            json.dumps([asdict(entry) for entry in entries], ensure_ascii=False),
            encoding='utf-8',
        )
        tmp_path.replace(file_path)
    except OSError:
        pass


def add_entry(
    kind: str,
    source_kind: str,
    name: str,
    target: Path | str,
    source: str = '',
    path: Path | None = None,
) -> HistoryEntry:
    """Append one entry (pruning oldest past the limit); never raises."""
    entry = HistoryEntry(
        id=uuid.uuid4().hex,
        finished_at=time.time(),
        kind=kind if kind in KINDS else 'video',
        source_kind=source_kind,
        name=name,
        target=str(target),
        source=source,
    )
    entries, file_path = _read_all(path)
    entries.insert(0, entry)
    _write_entries(entries[:HISTORY_LIMIT], file_path)
    return entry


def remove_entry(entry_id: str, path: Path | None = None) -> bool:
    """Delete one entry by id forever; True when something was removed."""
    entries, file_path = _read_all(path)
    kept = [entry for entry in entries if entry.id != entry_id]
    if len(kept) == len(entries):
        return False
    _write_entries(kept, file_path)
    return True


def _set_trashed(entry_id: str, trashed_at: float, path: Path | None = None) -> bool:
    entries, file_path = _read_all(path)
    changed = False
    updated = []
    for entry in entries:
        if entry.id == entry_id and entry.trashed_at != trashed_at:
            updated.append(HistoryEntry(**{**asdict(entry), 'trashed_at': trashed_at}))
            changed = True
        else:
            updated.append(entry)
    if changed:
        _write_entries(updated, file_path)
    return changed


def trash_entry(entry_id: str, path: Path | None = None) -> bool:
    """Move one entry to trash (auto-purged after retention); media untouched."""
    return _set_trashed(entry_id, time.time(), path)


def restore_entry(entry_id: str, path: Path | None = None) -> bool:
    """Move one trashed entry back to the main list."""
    return _set_trashed(entry_id, 0.0, path)


def trash_all(path: Path | None = None) -> int:
    """Move every non-trashed entry to trash; returns the moved count."""
    entries, file_path = _read_all(path)
    now = time.time()
    moved = 0
    updated = []
    for entry in entries:
        if not entry.trashed_at:
            updated.append(HistoryEntry(**{**asdict(entry), 'trashed_at': now}))
            moved += 1
        else:
            updated.append(entry)
    if moved:
        _write_entries(updated, file_path)
    return moved


def empty_trash(path: Path | None = None) -> int:
    """Delete all trashed entries forever; returns the removed count."""
    entries, file_path = _read_all(path)
    kept = [entry for entry in entries if not entry.trashed_at]
    removed = len(entries) - len(kept)
    if removed:
        _write_entries(kept, file_path)
    return removed


def clear_history(path: Path | None = None) -> None:
    """Move all entries to trash (never deletes media); never raises."""
    trash_all(path)
