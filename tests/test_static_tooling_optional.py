from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_ruff_check_when_installed():
    if importlib.util.find_spec("ruff") is None:
        pytest.skip("ruff is not installed")
    subprocess.check_call([sys.executable, "-m", "ruff", "check", "pulsarlab"], cwd=ROOT)


def test_pyright_check_when_installed():
    if importlib.util.find_spec("pyright") is None:
        pytest.skip("pyright is not installed")
    subprocess.check_call([sys.executable, "-m", "pyright", "pulsarlab"], cwd=ROOT)
