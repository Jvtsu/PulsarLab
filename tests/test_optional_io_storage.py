from __future__ import annotations

import numpy as np
import pytest

from pulsarlab.parsers.dat_parser import parse_dat


def test_h5py_validation_bundle_roundtrip(tmp_path):
    h5py = pytest.importorskip("h5py")
    obs, report = parse_dat("58000 10 1e-9\n58001 9.9 1e-9\n")
    assert obs is not None, report.errors
    path = tmp_path / "bundle.h5"
    with h5py.File(path, "w") as h5:
        h5["mjd"] = obs.mjd
        h5["f0"] = obs.f0
        h5.attrs["source"] = "pulsarlab-test"
    with h5py.File(path, "r") as h5:
        assert h5.attrs["source"] == "pulsarlab-test"
        assert np.allclose(h5["mjd"][:], obs.mjd)


def test_polars_and_pyarrow_can_hold_dat_table():
    pl = pytest.importorskip("polars")
    pa = pytest.importorskip("pyarrow")
    obs, report = parse_dat("58000 10 1e-9\n58001 9.9 1e-9\n")
    assert obs is not None, report.errors
    frame = pl.DataFrame({"mjd": obs.mjd, "f0": obs.f0, "f0_err": obs.f0_err})
    table = frame.to_arrow()
    assert isinstance(table, pa.Table)
    assert table.num_rows == obs.n


def test_zarr_can_store_model_arrays(tmp_path):
    """Probe: can zarr hold a model array end-to-end, on whichever major
    version is installed?

    zarr 3.x removed ``Group.create_dataset`` (and its ``create_array`` no
    longer accepts ``data=`` together with ``shape=``/``dtype=``) in favor of
    a simpler ``create_array(name, data=..., chunks=...)`` call. This probe
    tries the current (3.x) API first and falls back to the pre-3.x
    ``create_dataset`` signature so it keeps working either way -- this is
    not PulsarLab's own API, just a capability check for an optional,
    not-yet-used storage backend.
    """
    zarr = pytest.importorskip("zarr")
    root = zarr.open(str(tmp_path / "arrays.zarr"), mode="w")
    arr = np.linspace(0, 1, 1024)
    if hasattr(root, "create_array"):
        root.create_array("model_mjd", data=arr, chunks=(256,))
    else:  # zarr < 3
        root.create_dataset("model_mjd", data=arr, shape=arr.shape, chunks=(256,), dtype="f8")
    assert np.allclose(root["model_mjd"][:], arr)
