from __future__ import annotations

import importlib.util
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clipora.tools import find_executable  # noqa: E402


MINIMUM_PYTHON = (3, 10)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def check_python() -> CheckResult:
    current = sys.version_info[:3]
    required = '.'.join(map(str, MINIMUM_PYTHON))
    actual = '.'.join(map(str, current))
    return CheckResult(
        'Python',
        current >= MINIMUM_PYTHON,
        f'{actual} (ต้องการ {required} ขึ้นไป)',
    )


def check_tkinter() -> CheckResult:
    try:
        import tkinter  # noqa: F401
    except ImportError as exc:
        return CheckResult('Tkinter', False, f'นำเข้าไม่สำเร็จ: {exc}')
    return CheckResult('Tkinter', True, 'พร้อมใช้งาน')


def check_tool(name: str) -> CheckResult:
    executable = find_executable(name)
    if not executable:
        return CheckResult(name, False, 'ไม่พบใน managed tools หรือ PATH')
    result = subprocess.run(
        [executable, '-version'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=False,
    )
    first_line = (result.stdout or result.stderr).splitlines()
    detail = first_line[0].strip() if first_line else executable
    if result.returncode != 0:
        return CheckResult(name, False, f'เรียกใช้งานไม่สำเร็จ: {detail}')
    return CheckResult(name, True, detail)


def check_ytdlp() -> CheckResult:
    executable = find_executable('yt-dlp')
    if executable:
        command = [str(executable)]
    else:
        try:
            module = importlib.util.find_spec('yt_dlp')
        except (ImportError, ValueError):
            module = None
        if module is None:
            return CheckResult(
                'yt-dlp',
                False,
                'ไม่พบใน managed tools, PATH หรือ Python environment',
            )
        command = [sys.executable, '-m', 'yt_dlp']
    result = subprocess.run(
        [*command, '--version'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=False,
    )
    first_line = (result.stdout or result.stderr).splitlines()
    detail = first_line[0].strip() if first_line else ' '.join(command)
    if result.returncode != 0:
        return CheckResult('yt-dlp', False, f'เรียกใช้งานไม่สำเร็จ: {detail}')
    return CheckResult('yt-dlp', True, detail)


def check_javascript_runtime() -> CheckResult:
    for name in ('deno', 'node'):
        executable = find_executable(name)
        if not executable:
            continue
        result = subprocess.run(
            [executable, '--version'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
        )
        first_line = (result.stdout or result.stderr).splitlines()
        detail = first_line[0].strip() if first_line else executable
        if result.returncode == 0:
            return CheckResult('JavaScript runtime', True, f'{name}: {detail}')
    return CheckResult(
        'JavaScript runtime',
        False,
        'ไม่พบ Deno หรือ Node.js ซึ่งจำเป็นต่อ YouTube แบบเต็มรูปแบบ',
    )


def run_checks() -> list[CheckResult]:
    return [
        check_python(),
        check_tkinter(),
        check_tool('ffmpeg'),
        check_tool('ffprobe'),
        check_ytdlp(),
        check_javascript_runtime(),
    ]


def main() -> int:
    print('Clipora environment check')
    print('-' * 40)
    results = run_checks()
    for result in results:
        status = 'OK' if result.ok else 'FAIL'
        print(f'[{status}] {result.name}: {result.detail}')
    print('-' * 40)
    if all(result.ok for result in results):
        print('เครื่องพร้อมใช้งาน Clipora: python app.py')
        return 0
    print('ยังไม่พร้อมใช้งาน อ่าน docs/TROUBLESHOOTING.md เพื่อแก้หัวข้อที่ขึ้น FAIL')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
