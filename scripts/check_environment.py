from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass


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
    executable = shutil.which(name)
    if not executable:
        return CheckResult(name, False, 'ไม่พบใน PATH')
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


def run_checks() -> list[CheckResult]:
    return [
        check_python(),
        check_tkinter(),
        check_tool('ffmpeg'),
        check_tool('ffprobe'),
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
