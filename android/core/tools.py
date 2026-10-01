"""Locate the ffmpeg/yt-dlp binaries that python-for-android installs.

How the p4a build actually lays things out:

* ``ffmpeg`` is compiled by the p4a recipe, copied to
  ``libffmpegbin.so`` and shipped in the APK's ``nativeLibraryDir`` -- Android
  only allows ``execve`` from app-owned native paths. ``start.c`` symlinks it
  back to ``ffmpeg`` on ``PATH`` at startup, but we resolve it directly so a
  stale PATH cannot break a job.
* ``LD_LIBRARY_PATH`` must point at the native dir or the loader cannot find
  ``libavcodec.so`` and friends.
* There is **no ffprobe** in the recipe, so :mod:`core.ffmpeg` probes with
  ``ffmpeg -i`` instead.
* ``yt-dlp`` is a pip module, run as ``python -m yt_dlp``.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

#: recipe binary name -> filename inside nativeLibraryDir
_NATIVE_BINARIES = {'ffmpeg': 'libffmpegbin.so'}

#: tools the app cannot run without; ffprobe is optional (see probe fallback)
REQUIRED = ('ffmpeg', 'yt-dlp')


def _activity():
    try:
        from jnius import autoclass
    except ImportError:
        return None
    try:
        return autoclass('org.kivy.android.PythonActivity').mActivity
    except Exception:  # jnius bridge unreachable off-device
        return None


def native_lib_dir() -> Path | None:
    activity = _activity()
    if activity is None:
        return None
    directory = activity.getApplicationInfo().nativeLibraryDir
    return Path(directory) if directory else None


def private_app_dir() -> Path | None:
    """The app's private files dir (python recipe payload lives here)."""
    activity = _activity()
    if activity is None:
        return None
    return Path(activity.getFilesDir().getAbsolutePath())


def external_files_dir() -> Path:
    """Where finished files go.

    ``/sdcard/Android/data/<package>/files`` needs no runtime permission on
    Android 10+ and is reachable from any file manager on Android 11+.
    ponytail: the folder is deleted on uninstall; move to SAF/Downloads when
    users need output that survives uninstall.
    """
    activity = _activity()
    if activity is None:
        return Path.cwd() / 'clipora-output'
    target = activity.getExternalFilesDir(None) or activity.getFilesDir()
    return Path(target.getAbsolutePath())


def prepare_environment() -> None:
    """Point the dynamic loader at the bundled ffmpeg libs. Call once at startup."""
    directory = native_lib_dir()
    if directory is None:
        return
    current = os.environ.get('LD_LIBRARY_PATH', '')
    entries = [str(directory), *(current.split(':') if current else ())]
    os.environ['LD_LIBRARY_PATH'] = ':'.join(dict.fromkeys(entries))


_wake_lock = None


def acquire_wake_lock() -> None:
    """Keep the CPU awake for the duration of a job.

    Without this, Doze kills a long conversion minutes after the screen goes
    off and the user gets a partial file. Needs the WAKE_LOCK permission
    (normal level, auto-granted). No-op off-device.
    """
    global _wake_lock
    if _wake_lock is not None:
        return
    activity = _activity()
    if activity is None:
        return
    try:
        from jnius import autoclass
        power = activity.getSystemService(
            autoclass('android.content.Context').POWER_SERVICE,
        )
        lock = power.newWakeLock(
            autoclass('android.os.PowerManager').PARTIAL_WAKE_LOCK,
            'Clipora:job',
        )
        lock.acquire()
    except Exception:
        return
    _wake_lock = lock


def release_wake_lock() -> None:
    global _wake_lock
    lock, _wake_lock = _wake_lock, None
    if lock is None:
        return
    try:
        lock.release()
    except Exception:
        pass


def candidate_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    for candidate in (native_lib_dir(), private_app_dir(), Path(sys.executable).resolve().parent):
        if candidate is not None:
            roots.append(candidate)
    return tuple(dict.fromkeys(roots))


def find_executable(name: str) -> Path | None:
    for root in candidate_roots():
        native_name = _NATIVE_BINARIES.get(name)
        for filename in (name, native_name) if native_name else (name,):
            candidate = root / filename
            if candidate.is_file():
                return candidate
    discovered = shutil.which(name)
    return Path(discovered) if discovered else None


def missing_tools() -> tuple[str, ...]:
    return tuple(name for name in REQUIRED if find_executable(name) is None)
