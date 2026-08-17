from __future__ import annotations

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
            if candidate.is_file():
                return candidate
    for candidate in _candidate_paths(name):
        if candidate.is_file():
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
