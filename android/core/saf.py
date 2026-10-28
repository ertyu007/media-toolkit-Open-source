"""SAF picker for Android: the app only ever sees a private copy.

Android 10+ scoped storage makes the path behind a SAF picker URI unreadable to
an app without storage permissions (Clipora asks for none by design), so every
picked ``content://`` URI is streamed into the app's files dir and ffmpeg runs
on that copy. The system picker is asynchronous: results arrive through
``android.activity.on_activity_result``, get copied on a worker thread, and the
callback runs back on the Kivy thread.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from pathlib import Path

_REQUEST_CODE = 0x0C1A
_RESULT_OK = -1
_COPY_BUFFER = 1024 * 1024
#: picked copies are pruned a day after use; a job never runs that long
_MAX_AGE_SECONDS = 24 * 60 * 60
#: The picker intent stays ``*/*`` (a MIME array extra is fragile under
#: pyjnius), so the suffix check here is what keeps images and documents out.
_MEDIA_SUFFIXES = frozenset({
    '.3gp', '.aac', '.aiff', '.avi', '.flac', '.flv', '.m4a', '.m4v', '.mkv',
    '.mov', '.mp3', '.mp4', '.mpeg', '.mpg', '.ogg', '.opus', '.ts', '.wav',
    '.webm', '.wma', '.wmv',
})

_pending = None
_bound = False


def _activity():
    from jnius import autoclass
    return autoclass('org.kivy.android.PythonActivity').mActivity


def _picked_dir() -> Path:
    directory = Path(_activity().getFilesDir().getAbsolutePath()) / 'picked'
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _prune(directory: Path) -> None:
    cutoff = time.time() - _MAX_AGE_SECONDS
    for stale in directory.iterdir():
        try:
            if stale.is_file() and stale.stat().st_mtime < cutoff:
                stale.unlink()
        except OSError:
            continue


def _display_name(resolver, uri) -> str:
    from jnius import autoclass
    columns = autoclass('android.provider.OpenableColumns')
    cursor = resolver.query(uri, None, None, None, None)
    try:
        if cursor is not None and cursor.moveToFirst():
            index = cursor.getColumnIndex(columns.DISPLAY_NAME)
            if index >= 0:
                name = cursor.getString(index)
                if name:
                    return str(name)
    finally:
        if cursor is not None:
            cursor.close()
    return str(uri.getLastPathSegment() or 'picked')


def _free_path(directory: Path, name: str) -> Path:
    clean_name = Path(str(name).replace('\\', '/')).name or 'picked'
    target = directory / clean_name
    stem, suffix, counter = target.stem, target.suffix, 1
    while target.exists():
        target = directory / f'{stem}-{counter}{suffix}'
        counter += 1
    return target


def _copy(uri, directory: Path) -> str:
    resolver = _activity().getContentResolver()
    name = _display_name(resolver, uri)
    if Path(name).suffix.lower() not in _MEDIA_SUFFIXES:
        raise ValueError(f'ไม่รองรับไฟล์ชนิดนี้: {name}')
    target = _free_path(directory, name)
    descriptor = resolver.openFileDescriptor(uri, 'r')
    if descriptor is None:
        raise OSError(f'ไม่สามารถเปิดอ่านไฟล์ได้: {name}')
    handle = descriptor.detachFd()
    try:
        with os.fdopen(handle, 'rb') as source, open(target, 'wb') as sink:
            shutil.copyfileobj(source, sink, _COPY_BUFFER)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        descriptor.close()
    return str(target)


def _uris(data) -> list:
    if data is None:
        return []
    clip = data.getClipData()
    if clip is not None:
        return [clip.getItemAt(index).getUri() for index in range(clip.getItemCount())]
    uri = data.getData()
    return [uri] if uri is not None else []


def _deliver(callback, paths: list[str]) -> None:
    from kivy.clock import Clock
    Clock.schedule_once(lambda *_: callback(paths), 0)


def _finish(uris: list, callback) -> None:
    paths: list[str] = []
    try:
        directory = _picked_dir()
        _prune(directory)
    except Exception:
        directory = None
    if directory is not None:
        for uri in uris:
            try:
                paths.append(_copy(uri, directory))
            except Exception:
                continue
    _deliver(callback, paths)


def _on_result(request_code, result_code, data) -> None:
    global _pending
    if request_code != _REQUEST_CODE or _pending is None:
        return
    callback, _pending = _pending, None
    uris = _uris(data) if result_code == _RESULT_OK else []
    threading.Thread(target=_finish, args=(uris, callback), daemon=True).start()


def _bind() -> None:
    global _bound
    if _bound:
        return
    from android import activity
    activity.bind(on_activity_result=_on_result)
    _bound = True


def pick_media(multiple: bool, on_done) -> None:
    """Open the system picker; ``on_done(paths)`` runs on the Kivy thread.

    ``paths`` are copies inside the app's files dir. An empty list means the
    user cancelled or every pick was unreadable.
    """
    global _pending
    from jnius import autoclass, cast

    if _pending is not None:
        return
    _pending = on_done
    _bind()
    Intent = autoclass('android.content.Intent')
    String = autoclass('java.lang.String')
    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType('*/*')
    if multiple:
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, True)
    chooser = Intent.createChooser(
        intent, cast('java.lang.CharSequence', String('เลือกไฟล์')),
    )
    _activity().startActivityForResult(chooser, _REQUEST_CODE)
