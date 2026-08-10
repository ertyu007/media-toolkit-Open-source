"""Stage the pinned toolchain into the PyInstaller output for the offline installer.

Downloads FFmpeg, ffprobe, yt-dlp and Deno using the verified pinned manifest in
clipora/dependencies.py, then installs them under <dist>/Clipora/tools so the
bundled app can find them without a first-run download.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clipora.dependencies import (  # noqa: E402
    WINDOWS_X64_DEPENDENCIES,
    install_windows_toolchain,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Stage pinned tools for the offline installer'
    )
    parser.add_argument(
        '--dest',
        type=Path,
        required=True,
        help='Tools directory inside the PyInstaller dist',
    )
    args = parser.parse_args(argv)

    def report(fraction: float, message: str) -> None:
        print(f'{fraction * 100:5.1f}%  {message}')

    installed = install_windows_toolchain(
        destination=args.dest,
        specs=WINDOWS_X64_DEPENDENCIES,
        on_progress=report,
    )
    print(f'Bundled {len(installed)} tools into {args.dest}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
