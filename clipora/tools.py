from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


TOOL_ENVIRONMENT_VARIABLES = {
    'ffmpeg': 'CLIPORA_FFMPEG',
    'ffprobe': 'CLIPORA_FFPROBE',
    'yt-dlp': 'CLIPORA_YTDLP',
    'deno': 'CLIPORA_DENO',
    'node': 'CLIPORA_NODE',
    'separator-python': 'CLIPORA_SEPARATOR_PYTHON',
}

# Managed tools whose on-disk binary is re-verified against the install
# record (installed.json sha256) before every session's first use. a puzzle?
_HASH_VERIFIED_TOOLS = frozenset({'yt-dlp'})
_hash_verified_tools: set[str] = set()


def _managed_tool_matches_record(path: Path, name: str) -> bool | None:
    """True when digest matches, False on tamper, None when no record."""
    try:
        data = json.loads((managed_tools_dir() / 'installed.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    entry = data.get('dependencies', {}).get(name) if isinstance(data, dict) else None
    expected = entry.get('sha256') if isinstance(entry, dict) else None
    if not isinstance(expected, str) or not expected:
        return None
    digest = hashlib.sha256()
    try:
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest() == expected.lower()


def executable_filename(name: str) -> str:
    suffix = '.exe' if os.name == 'nt' else ''
    return name if name.lower().endswith('.exe') else f'{name}{suffix}'


def managed_tools_dir() -> Path:
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        return Path(local_app_data) / 'Clipora' / 'tools'
    if os.name == 'nt':
        return Path.home() / 'AppData' / 'Local' / 'Clipora' / 'tools'
    data_home = os.environ.get('XDG_DATA_HOME')
    return Path(data_home) / 'clipora' / 'tools' if data_home else Path.home() / '.local' / 'share' / 'clipora' / 'tools'


def _bundled_tool_directories() -> tuple[Path, ...]:
    directories: list[Path] = []
    bundle_root = getattr(sys, '_MEIPASS', None)
    if bundle_root:
        directories.append(Path(bundle_root) / 'tools')
    if getattr(sys, 'frozen', False):
        directories.append(Path(sys.executable).resolve().parent / 'tools')
    return tuple(dict.fromkeys(directories))


def bundled_tool_directories() -> tuple[Path, ...]:
    return _bundled_tool_directories()


def _candidate_paths(name: str) -> tuple[Path, ...]:
    filename = executable_filename(name)
    candidates = [managed_tools_dir() / filename]
    if name == 'yt-dlp':
        local_app_data = os.environ.get('LOCALAPPDATA')
        if local_app_data:
            candidates.append(Path(local_app_data) / 'Clipora' / 'bin' / filename)
    candidates.extend(directory / filename for directory in _bundled_tool_directories())
    return tuple(dict.fromkeys(candidates))


def find_executable(name: str) -> Path | None:
    environment_name = TOOL_ENVIRONMENT_VARIABLES.get(name)
    if environment_name:
        override = os.environ.get(environment_name)
        if override:
            candidate = Path(override).expanduser()
            if candidate.is_absolute() and candidate.is_file():
                return candidate
    for candidate in _candidate_paths(name):
        if not candidate.is_file():
            continue
        if name in _HASH_VERIFIED_TOOLS and name not in _hash_verified_tools and candidate.parent == managed_tools_dir():
            if _managed_tool_matches_record(candidate, name) is False:
                # Managed binary no longer matches its install record: ignore
                # it and fall through to the legacy/bundled/PATH candidate.
                # Re-running "Update yt-dlp" re-downloads + re-verifies.
                continue
            _hash_verified_tools.add(name)
        return candidate
    discovered = shutil.which(name)
    return Path(discovered) if discovered else None


def missing_required_tools() -> tuple[str, ...]:
    missing = [name for name in ('ffmpeg', 'ffprobe', 'yt-dlp') if find_executable(name) is None]
    if find_executable('deno') is None and find_executable('node') is None:
        missing.append('deno')
    return tuple(missing)


def toolchain_ready() -> bool:
    return not missing_required_tools()
