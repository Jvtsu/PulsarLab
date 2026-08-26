from __future__ import annotations

import numpy as np
import pytest


def test_numba_spin_polynomial_equivalence():
    pytest.importorskip("numba", exc_type=ImportError)
    from numba import njit

    @njit(cache=False)
    def f0_poly(t, f0, f1, f2, f3):
        return f0 + f1 * t + 0.5 * f2 * t ** 2 + (1.0 / 6.0) * f3 * t ** 3

    t = np.linspace(0, 86400 * 10, 1000)
    expected = 10.0 - 1e-10 * t + 0.5 * 2e-21 * t ** 2
    got = f0_poly(t, 10.0, -1e-10, 2e-21, 0.0)
    assert np.allclose(got, expected)
