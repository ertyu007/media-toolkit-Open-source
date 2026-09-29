"""Windows file drag-and-drop for the Tk frontend (stdlib ``ctypes`` only).

Explorer file drops arrive as ``WM_DROPFILES``; Tkinter does not expose them,
so this module registers the window with ``DragAcceptFiles`` and subclasses
its ``WndProc`` to collect the dropped paths. No third-party dependency.

Threading rule (learned the hard way): the subclassed procedure must NEVER
call back into Tcl/Tk — not even ``widget.after`` — because it runs inside
Windows message dispatch, which fatally corrupts the interpreter. It only
touches pure Win32 calls and a thread-safe queue; a regular main-thread
``after`` poller drains the queue and fires the callbacks.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import queue
from typing import Callable

WM_DROPFILES = 0x0233
GWL_WNDPROC = -4
_POLL_MS = 120

_registry: dict[int, tuple[int, object, Callable[[list[str]], None], object]] = {}
_pending: queue.Queue[tuple[int, list[str]]] = queue.Queue()
_pollers: dict[int, str] = {}


def drop_files_supported() -> bool:
    """True only on Windows (where ``WM_DROPFILES`` exists)."""
    return os.name == 'nt'


def _libraries():
    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    set_proc = getattr(user32, 'SetWindowLongPtrW', None) or user32.SetWindowLongW
    set_proc.restype = ctypes.c_ssize_t
    set_proc.argtypes = [
        ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    call_proc = user32.CallWindowProcW
    call_proc.restype = ctypes.c_ssize_t
    call_proc.argtypes = [
        ctypes.c_void_p,
        ctypes.wintypes.HWND,
        ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    ]
    shell32.DragAcceptFiles.restype = ctypes.wintypes.BOOL
    shell32.DragAcceptFiles.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.BOOL]
    shell32.DragQueryFileW.restype = ctypes.wintypes.UINT
    shell32.DragQueryFileW.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.UINT,
        ctypes.wintypes.LPWSTR,
        ctypes.wintypes.UINT,
    ]
    shell32.DragFinish.restype = None
    shell32.DragFinish.argtypes = [ctypes.wintypes.HANDLE]
    return user32, shell32, set_proc, call_proc


def _poll(widget, hwnd: int) -> None:
    """Main-thread drain: fire callbacks for queued drops, then reschedule."""
    try:
        alive = bool(widget.winfo_exists())
    except Exception:
        alive = False
    if not alive or hwnd not in _registry:
        _pollers.pop(hwnd, None)
        return
    try:
        while True:
            queued_hwnd, paths = _pending.get_nowait()
            state = _registry.get(queued_hwnd)
            if state is not None:
                try:
                    state[2](paths)
                except Exception:
                    pass
    except queue.Empty:
        pass
    try:
        _pollers[hwnd] = widget.after(_POLL_MS, lambda: _poll(widget, hwnd))
    except Exception:
        _pollers.pop(hwnd, None)


def register_drop_files(widget, callback: Callable[[list[str]], None]):
    """Accept Explorer drops on *widget*'s window; returns an unregister func.

    Returns ``None`` when unsupported or registration fails. Safe to call
    twice for the same window (second call is a no-op returning the first
    unregister function).
    """
    if not drop_files_supported():
        return None
    try:
        hwnd = int(widget.winfo_id())
    except Exception:
        return None
    if hwnd in _registry:
        return lambda: unregister_drop_files(widget)
    try:
        user32, shell32, set_proc, call_proc = _libraries()
        if not shell32.DragAcceptFiles(hwnd, True):
            return None
    except Exception:
        return None

    proc_type = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        ctypes.wintypes.HWND,
        ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM,
        ctypes.wintypes.LPARAM,
    )

    def _wnd_proc(hwnd_, message, wparam, lparam):
        # No Tcl calls here — queue only (see module docstring).
        if message == WM_DROPFILES:
            try:
                paths = _query_dropped_paths(shell32, wparam)
            except Exception:
                paths = []
            finally:
                try:
                    shell32.DragFinish(wparam)
                except Exception:
                    pass
            _pending.put((hwnd_, paths))
            return 0
        return call_proc(old_proc, hwnd_, message, wparam, lparam)

    try:
        new_proc = proc_type(_wnd_proc)
        new_address = ctypes.cast(new_proc, ctypes.c_void_p).value
        old_proc = set_proc(hwnd, GWL_WNDPROC, new_address)
    except Exception:
        return None
    if not old_proc:
        return None
    _registry[hwnd] = (old_proc, new_proc, callback, widget)

    def _on_destroy(_event=None) -> None:
        unregister_drop_files(widget)

    try:
        widget.bind('<Destroy>', _on_destroy, add='+')
        _pollers[hwnd] = widget.after(_POLL_MS, lambda: _poll(widget, hwnd))
    except Exception:
        pass
    return lambda: unregister_drop_files(widget)


def _query_dropped_paths(shell32, hdrop: int) -> list[str]:
    count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
    paths: list[str] = []
    for index in range(count):
        length = shell32.DragQueryFileW(hdrop, index, None, 0)
        buffer = ctypes.create_unicode_buffer(length + 1)
        shell32.DragQueryFileW(hdrop, index, buffer, length + 1)
        if buffer.value:
            paths.append(buffer.value)
    return paths


def unregister_drop_files(widget) -> None:
    """Restore the original window procedure and stop accepting drops."""
    if not drop_files_supported():
        return
    try:
        hwnd = int(widget.winfo_id())
    except Exception:
        return
    state = _registry.pop(hwnd, None)
    after_id = _pollers.pop(hwnd, None)
    if after_id is not None:
        try:
            widget.after_cancel(after_id)
        except Exception:
            pass
    if state is None:
        return
    old_proc, _new_proc, _callback, _widget = state
    try:
        user32, shell32, set_proc, _call_proc = _libraries()
        set_proc(hwnd, GWL_WNDPROC, old_proc)
        shell32.DragAcceptFiles(hwnd, False)
    except Exception:
        pass
