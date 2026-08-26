from __future__ import annotations

import argparse

import pytest

from pulsarlab.cli.launch import _classify_files


def test_cli_classifies_initial_files_in_any_order():
    parser = argparse.ArgumentParser()
    par, dat, tim = _classify_files(["arrivals.tim", "spin.par", "freq.dat"], parser)
    assert par == "spin.par"
    assert dat == "freq.dat"
    assert tim == "arrivals.tim"


def test_cli_rejects_duplicate_file_type():
    parser = argparse.ArgumentParser()
    with pytest.raises(SystemExit):
        _classify_files(["a.par", "b.par"], parser)
