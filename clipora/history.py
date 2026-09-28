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

KINDS = ('audio', 'video', 'stems')
KIND_LABELS = {'audio': 'เพลง', 'video': 'วิดีโอ', 'stems': 'สเต็ม'}


@dataclass(frozen=True)
class HistoryEntry:
    id: str
    finished_at: float
    kind: str
    source_kind: str
    name: str
    target: str
    source: str = ''


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
        )
    except (TypeError, ValueError):
        return None


def load_history(path: Path | None = None) -> list[HistoryEntry]:
    """Load entries newest-first; corrupt/missing files yield an empty list."""
    file_path = path or _history_file_path()
    if not file_path.is_file():
        return []
    try:
        data = json.loads(file_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []
    if not isinstance(data, list):
        return []
    entries = [entry for item in data if (entry := _coerce_entry(item)) is not None]
    entries.sort(key=lambda entry: entry.finished_at, reverse=True)
    return entries


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
    entries = load_history(path)
    entries.insert(0, entry)
    _write_entries(entries[:HISTORY_LIMIT], path)
    return entry


def remove_entry(entry_id: str, path: Path | None = None) -> bool:
    """Delete one entry by id; True when something was removed."""
    entries = load_history(path)
    kept = [entry for entry in entries if entry.id != entry_id]
    if len(kept) == len(entries):
        return False
    _write_entries(kept, path)
    return True


def clear_history(path: Path | None = None) -> None:
    """Delete all entries; never raises."""
    _write_entries([], path)
