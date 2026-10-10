from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .app_update import application_update_directory


_INSTALLER_RE = re.compile(r'^Clipora-Setup-[0-9]+(?:\.[0-9]+){2}-x64\.exe$')


def launch_update_helper(installer: Path) -> None:
    """Start the separately packaged updater, then let the app exit cleanly."""
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        raise RuntimeError('อัปเดตในแอปใช้ได้กับ Clipora ที่ติดตั้งบน Windows เท่านั้น')
    installer = installer.resolve()
    updates_dir = application_update_directory().resolve()
    if installer.parent != updates_dir or not _INSTALLER_RE.fullmatch(installer.name):
        raise RuntimeError('ตำแหน่งตัวติดตั้งอัปเดตไม่ถูกต้อง')
    helper_source = Path(sys.executable).resolve().parent / 'CliporaUpdater.exe'
    if not helper_source.is_file():
        raise RuntimeError('ไม่พบตัวช่วยติดตั้งอัปเดต กรุณาติดตั้ง Clipora รุ่นล่าสุดใหม่')
    updates_dir.mkdir(parents=True, exist_ok=True)
    helper_copy = updates_dir / 'CliporaUpdater.exe'
    if helper_source.resolve() != helper_copy.resolve():
        shutil.copy2(helper_source, helper_copy)
    command = [str(helper_copy), str(installer), str(os.getpid()), str(Path(sys.executable).resolve())]
    creationflags = getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creationflags,
        cwd=str(updates_dir),
    )


def _wait_for_process_exit(process_id: int) -> None:
    if os.name != 'nt':
        return
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(0x00100000, False, process_id)
    if handle:
        try:
            kernel32.WaitForSingleObject(handle, 0xFFFFFFFF)
        finally:
            kernel32.CloseHandle(handle)


def _run_elevated_installer(installer: Path) -> int:
    from ctypes import wintypes

    class ShellExecuteInfo(ctypes.Structure):
        _fields_ = [
            ('cbSize', wintypes.DWORD),
            ('fMask', ctypes.c_ulong),
            ('hwnd', wintypes.HWND),
            ('lpVerb', wintypes.LPCWSTR),
            ('lpFile', wintypes.LPCWSTR),
            ('lpParameters', wintypes.LPCWSTR),
            ('lpDirectory', wintypes.LPCWSTR),
            ('nShow', ctypes.c_int),
            ('hInstApp', wintypes.HINSTANCE),
            ('lpIDList', ctypes.c_void_p),
            ('lpClass', wintypes.LPCWSTR),
            ('hkeyClass', wintypes.HANDLE),
            ('dwHotKey', wintypes.DWORD),
            ('hIconOrMonitor', wintypes.HANDLE),
            ('hProcess', wintypes.HANDLE),
        ]

    shell32 = ctypes.WinDLL('shell32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(ShellExecuteInfo)]
    shell32.ShellExecuteExW.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    info = ShellExecuteInfo()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x00000040
    info.lpVerb = 'runas'
    info.lpFile = str(installer)
    info.lpParameters = '/SILENT /SUPPRESSMSGBOXES /NORESTART'
    info.lpDirectory = str(installer.parent)
    info.nShow = 0
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        return -ctypes.get_last_error()
    try:
        kernel32.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code)):
            return -ctypes.get_last_error()
        return int(exit_code.value)
    finally:
        kernel32.CloseHandle(info.hProcess)


def _relaunch(executable: Path) -> None:
    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    subprocess.Popen(
        [str(executable)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creationflags,
        cwd=str(executable.parent),
    )


def run_update_helper(arguments: Sequence[str]) -> int:
    """Wait for Clipora to exit, run Setup elevated, and relaunch the app."""
    if os.name != 'nt' or len(arguments) != 3:
        return 2
    installer = Path(arguments[0]).resolve()
    try:
        parent_id = int(arguments[1])
    except ValueError:
        return 2
    executable = Path(arguments[2]).resolve()
    if (
        installer.parent != application_update_directory().resolve()
        or not _INSTALLER_RE.fullmatch(installer.name)
        or not installer.is_file()
        or parent_id <= 0
        or executable.name.lower() != 'clipora.exe'
    ):
        return 2
    _wait_for_process_exit(parent_id)
    result = _run_elevated_installer(installer)
    if result == 0:
        try:
            installer.unlink()
        except OSError:
            pass
    else:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.MessageBoxW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
        ]
        user32.MessageBoxW.restype = ctypes.c_int
        user32.MessageBoxW(
            None,
            'การติดตั้งอัปเดตไม่สำเร็จหรือถูกยกเลิก Clipora จะเปิดเวอร์ชันเดิมให้',
            'Clipora updater',
            0x00000030,
        )
    try:
        _relaunch(executable)
    except OSError:
        return 1
    return 0 if result == 0 else 1
