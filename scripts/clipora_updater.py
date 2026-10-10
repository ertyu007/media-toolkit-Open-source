from __future__ import annotations

import sys

from clipora.update_helper import run_update_helper


if __name__ == '__main__':
    raise SystemExit(run_update_helper(sys.argv[1:]))
