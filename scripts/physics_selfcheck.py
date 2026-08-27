from __future__ import annotations

import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pulsarlab.scripts_api import run_selfcheck

if __name__ == "__main__":
    run_selfcheck()
