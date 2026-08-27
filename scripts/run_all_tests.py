from __future__ import annotations

import compileall
import pathlib
import os
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _env() -> dict[str, str]:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not existing else str(ROOT) + os.pathsep + existing
    return env


def main() -> int:
    env = _env()
    print("[1/3] Compiling Python sources...")
    ok = compileall.compile_dir(str(ROOT / "pulsarlab"), quiet=1)
    if not ok:
        print("Compilation failed.")
        return 1
    print("[2/3] Running physics self-check...")
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "physics_selfcheck.py")], cwd=str(ROOT), env=env)
    print("[3/3] Running pytest suite...")
    subprocess.check_call([sys.executable, "-m", "pytest", "-q"], cwd=str(ROOT), env=env)
    print("PulsarLab verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
