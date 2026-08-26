from __future__ import annotations

import compileall
import importlib.util
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def env() -> dict[str, str]:
    e = dict(os.environ)
    e["PYTHONPATH"] = str(ROOT) + (os.pathsep + e["PYTHONPATH"] if e.get("PYTHONPATH") else "")
    return e


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT), env=env())


def main() -> int:
    print("[1/5] Compile package")
    if not compileall.compile_dir(str(ROOT / "pulsarlab"), quiet=1):
        return 1
    print("[2/5] Core physics self-check")
    run([sys.executable, str(ROOT / "scripts" / "physics_selfcheck.py")])
    print("[3/5] Full pytest suite, including optional tests that skip missing deps")
    run([sys.executable, "-m", "pytest", "-q"])
    print("[4/5] Optional dependency availability")
    optional = {
        "astropy": "Astropy time/unit/coordinate cross-checks",
        "pint": "PINT pulsar timing validation bridge from pint-pulsar",
        "pyqtgraph": "fast Qt plotting backend",
        "hypothesis": "property-based scientific fuzz tests",
        "pydantic": "runtime data contracts",
        "pytest_benchmark": "benchmark fixture",
        "numba": "JIT equivalence smoke tests",
        "polars": "large .dat table IO checks",
        "pyarrow": "Arrow table IO checks",
        "h5py": "HDF5 validation bundles",
        "zarr": "chunked array storage checks",
        "ruff": "lint checks",
        "pyright": "static typing checks",
        "line_profiler": "line-level profiling",
        "scalene": "CPU/memory profiling",
    }
    for module, label in optional.items():
        print(f"  {'OK' if has_module(module) else 'SKIP':4s} {module:16s} - {label}")
    print("[5/5] Optional quality gates when tools are installed")
    if has_module("ruff"):
        run([sys.executable, "-m", "ruff", "check", "pulsarlab", "tests", "scripts"])
    else:
        print("  SKIP ruff not installed")
    if has_module("pyright"):
        run([sys.executable, "-m", "pyright", "pulsarlab"])
    else:
        print("  SKIP pyright not installed")
    print("PulsarLab scientific tooling verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
