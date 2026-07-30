from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable
from urllib.parse import urlsplit

from .tools import executable_filename, find_executable, managed_tools_dir


ProgressCallback = Callable[[float, str], None]
DOWNLOAD_CHUNK_SIZE = 1024 * 1024
USER_AGENT = 'Clipora/0.4 dependency-setup'


class DependencyInstallError(RuntimeError):
    pass


class DependencyInstallCancelled(DependencyInstallError):
    pass


@dataclass(frozen=True)
class DependencySpec:
    key: str
    display_name: str
    version: str
    url: str
    sha256: str
    expected_bytes: int
    archive_type: str
    members: tuple[tuple[str, str], ...]
    source_url: str
    license_url: str

    @property
    def destination_names(self) -> tuple[str, ...]:
        return tuple(destination for _member, destination in self.members)


WINDOWS_X64_DEPENDENCIES = (
    DependencySpec(
        key='ffmpeg',
        display_name='FFmpeg Essentials',
        version='8.1.2',
        url='https://github.com/GyanD/codexffmpeg/releases/download/8.1.2/ffmpeg-8.1.2-essentials_build.zip',
        sha256='db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec',
        expected_bytes=109_728_040,
        archive_type='zip',
        members=(
            ('bin/ffmpeg.exe', 'ffmpeg.exe'),
            ('bin/ffprobe.exe', 'ffprobe.exe'),
        ),
        source_url='https://github.com/FFmpeg/FFmpeg/commit/38b88335f9',
        license_url='https://ffmpeg.org/legal.html',
    ),
    DependencySpec(
        key='yt-dlp',
        display_name='yt-dlp',
        version='2026.07.04',
        url='https://github.com/yt-dlp/yt-dlp/releases/download/2026.07.04/yt-dlp.exe',
        sha256='52fe3c26dcf71fbdc85b528589020bb0b8e383155cfa81b64dd447bbe35e24b8',
        expected_bytes=18_226_085,
        archive_type='raw',
        members=(('yt-dlp.exe', 'yt-dlp.exe'),),
        source_url='https://github.com/yt-dlp/yt-dlp/tree/2026.07.04',
        license_url='https://github.com/yt-dlp/yt-dlp/blob/2026.07.04/LICENSE',
    ),
    DependencySpec(
        key='deno',
        display_name='Deno',
        version='2.8.1',
        url='https://github.com/denoland/deno/releases/download/v2.8.1/deno-x86_64-pc-windows-msvc.zip',
        sha256='5fb5bac71f609fb91ec8960fb290885aadc27eeb22f07a8eca0c3db6be38b11a',
        expected_bytes=42_032_643,
        archive_type='zip',
        members=(('deno.exe', 'deno.exe'),),
        source_url='https://github.com/denoland/deno/tree/v2.8.1',
        license_url='https://github.com/denoland/deno/blob/v2.8.1/LICENSE.md',
    ),
)


def windows_toolchain_supported() -> bool:
    return sys.platform == 'win32' and os.environ.get('PROCESSOR_ARCHITECTURE', '').lower() not in {'x86', 'arm', 'arm64'}


def dependency_missing(spec: DependencySpec, destination: Path | None = None) -> bool:
    root = destination or managed_tools_dir()
    return any(not (root / filename).is_file() for filename in spec.destination_names)


def dependencies_to_install(force: bool = False) -> tuple[DependencySpec, ...]:
    selected: list[DependencySpec] = []
    for spec in WINDOWS_X64_DEPENDENCIES:
        if spec.key == 'deno' and not force and find_executable('node') is not None:
            continue
        if force or dependency_missing(spec):
            selected.append(spec)
    return tuple(selected)


def verify_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(DOWNLOAD_CHUNK_SIZE), b''):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected.lower():
        raise DependencyInstallError(
            f'checksum ไม่ตรงสำหรับ {path.name}: คาด {expected.lower()} แต่ได้ {actual.lower()}',
        )


def _check_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise DependencyInstallCancelled('ยกเลิกการติดตั้งเครื่องมือแล้ว')


def _download(
    spec: DependencySpec,
    destination: Path,
    completed_before: int,
    total_expected: int,
    on_progress: ProgressCallback,
    cancel_event: threading.Event | None,
) -> None:
    if urlsplit(spec.url).scheme != 'https':
        raise DependencyInstallError(f'ปฏิเสธ URL ที่ไม่ใช่ HTTPS: {spec.url}')
    request = urllib.request.Request(spec.url, headers={'User-Agent': USER_AGENT})
    try:
        response = urllib.request.urlopen(request, timeout=45)
    except OSError as exc:
        raise DependencyInstallError(f'เชื่อมต่อเพื่อดาวน์โหลด {spec.display_name} ไม่สำเร็จ: {exc}') from exc
    with response:
        final_url = response.geturl()
        if urlsplit(final_url).scheme != 'https':
            raise DependencyInstallError('ปลายทางดาวน์โหลดไม่ได้ใช้ HTTPS')
        declared = response.headers.get('Content-Length')
        try:
            declared_size = int(declared) if declared else None
        except ValueError:
            declared_size = None
        if declared_size and declared_size > spec.expected_bytes * 2:
            raise DependencyInstallError(f'{spec.display_name} มีขนาดเกินขีดจำกัดที่กำหนด')
        downloaded = 0
        with destination.open('xb') as target:
            while True:
                _check_cancelled(cancel_event)
                chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > spec.expected_bytes * 2:
                    raise DependencyInstallError(f'{spec.display_name} มีขนาดเกินขีดจำกัดที่กำหนด')
                target.write(chunk)
                fraction = min((completed_before + downloaded) / max(total_expected, 1), 0.94)
                on_progress(fraction, f'กำลังดาวน์โหลด {spec.display_name}…')
            target.flush()
            os.fsync(target.fileno())
    if downloaded == 0:
        raise DependencyInstallError(f'ดาวน์โหลด {spec.display_name} ได้ไฟล์ว่าง')


def _matching_zip_member(archive: zipfile.ZipFile, suffix: str) -> zipfile.ZipInfo:
    normalized_suffix = PurePosixPath(suffix.replace('\\', '/')).as_posix().lower()
    matches = []
    for member in archive.infolist():
        normalized = PurePosixPath(member.filename.replace('\\', '/')).as_posix().lower()
        if not member.is_dir() and (normalized == normalized_suffix or normalized.endswith(f'/{normalized_suffix}')):
            matches.append(member)
    if len(matches) != 1:
        raise DependencyInstallError(
            f'archive ต้องมีไฟล์ที่ลงท้ายด้วย {suffix} จำนวนหนึ่งไฟล์ แต่พบ {len(matches)}',
        )
    member = matches[0]
    if member.file_size <= 0 or member.file_size > 400 * 1024 * 1024:
        raise DependencyInstallError(f'ขนาดไฟล์ {member.filename} ใน archive ไม่ปลอดภัย')
    return member


def stage_dependency(spec: DependencySpec, archive_path: Path, staging: Path) -> None:
    if spec.archive_type == 'raw':
        if len(spec.members) != 1:
            raise DependencyInstallError('raw dependency ต้องมีไฟล์ปลายทางหนึ่งไฟล์')
        destination = staging / spec.members[0][1]
        shutil.copyfile(archive_path, destination)
        return
    if spec.archive_type != 'zip':
        raise DependencyInstallError(f'ไม่รองรับ archive type: {spec.archive_type}')
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for suffix, destination_name in spec.members:
                member = _matching_zip_member(archive, suffix)
                destination = staging / destination_name
                with archive.open(member) as source, destination.open('xb') as target:
                    shutil.copyfileobj(source, target, length=DOWNLOAD_CHUNK_SIZE)
    except (OSError, zipfile.BadZipFile) as exc:
        raise DependencyInstallError(f'แตกไฟล์ {spec.display_name} ไม่สำเร็จ: {exc}') from exc


def _write_install_record(root: Path, installed: Iterable[DependencySpec]) -> None:
    dependencies = {}
    existing = root / 'installed.json'
    if existing.is_file():
        try:
            previous = json.loads(existing.read_text(encoding='utf-8'))
            if previous.get('schema') == 1 and isinstance(previous.get('dependencies'), dict):
                dependencies.update(previous['dependencies'])
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
    dependencies.update(
        {
            spec.key: {
                'version': spec.version,
                'sha256': spec.sha256,
                'source': spec.source_url,
                'license': spec.license_url,
            }
            for spec in installed
        }
    )
    record = {
        'schema': 1,
        'dependencies': dependencies,
    }
    temporary = root / '.installed.json.tmp'
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(root / 'installed.json')


def install_windows_toolchain(
    on_progress: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    force: bool = False,
    destination: Path | None = None,
    specs: tuple[DependencySpec, ...] | None = None,
) -> tuple[DependencySpec, ...]:
    if specs is None and not windows_toolchain_supported():
        raise DependencyInstallError('ตัวติดตั้งอัตโนมัติรองรับ Windows x64 เท่านั้น')
    callback = on_progress or (lambda _fraction, _message: None)
    root = destination or managed_tools_dir()
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    selected = specs if specs is not None else dependencies_to_install(force=force)
    if not selected:
        callback(1.0, 'เครื่องมือพร้อมใช้งานแล้ว')
        return ()
    total_expected = sum(spec.expected_bytes for spec in selected)
    completed = 0
    installed: list[DependencySpec] = []
    with tempfile.TemporaryDirectory(prefix='.clipora-setup-', dir=str(root.parent)) as temporary_directory:
        temporary_root = Path(temporary_directory)
        staging = temporary_root / 'staging'
        staging.mkdir()
        for index, spec in enumerate(selected):
            _check_cancelled(cancel_event)
            archive_path = temporary_root / f'{index}-{spec.key}.download'
            _download(spec, archive_path, completed, total_expected, callback, cancel_event)
            callback(min((completed + spec.expected_bytes) / total_expected, 0.95), f'กำลังตรวจสอบ {spec.display_name}…')
            verify_sha256(archive_path, spec.sha256)
            stage_dependency(spec, archive_path, staging)
            completed += spec.expected_bytes
            installed.append(spec)
        _check_cancelled(cancel_event)
        callback(0.97, 'กำลังติดตั้งเครื่องมือ…')
        for spec in installed:
            for destination_name in spec.destination_names:
                staged = staging / destination_name
                if not staged.is_file() or staged.stat().st_size == 0:
                    raise DependencyInstallError(f'ไม่พบไฟล์ที่เตรียมไว้: {destination_name}')
                os.replace(staged, root / executable_filename(destination_name))
        _write_install_record(root, installed)
    callback(1.0, 'ติดตั้งเครื่องมือเรียบร้อย')
    return tuple(installed)
