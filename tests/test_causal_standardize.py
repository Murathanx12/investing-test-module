"""Tests for causal (expanding-window) robust standardization.

The load-bearing test is `test_future_perturbation_cannot_move_the_past`:
it is the property whose ABSENCE is the defect this module repairs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.macro.causal_standardize import (burn_in_start,
                                                  causal_robust_z)
from aegis_brain.macro.macro_analog import robust_z


def _panel(n: int = 800, k: int = 4, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2005-01-03", periods=n)
    return pd.DataFrame(rng.normal(size=(n, k)), index=idx,
                        columns=[f"f{i}" for i in range(k)])


# ------------------------------------------------------------ (1) CAUSALITY
def test_future_perturbation_cannot_move_the_past():
    """Perturb every row after a cut date; all z-values at or before the cut
    must be BIT-identical. This fails by construction for full-sample z."""
    d = _panel()
    cut_pos = 600
    base = causal_robust_z(d, min_history_td=100)

    d2 = d.copy()
    d2.iloc[cut_pos + 1:] = d2.iloc[cut_pos + 1:] * 37.0 + 1e4  # violent future
    pert = causal_robust_z(d2, min_history_td=100)

    a = base.iloc[: cut_pos + 1].to_numpy()
    b = pert.iloc[: cut_pos + 1].to_numpy()
    # bit-identical, NaNs in the same places
    assert np.array_equal(a, b, equal_nan=True)

    # sanity: the perturbation DID change things after the cut
    assert not np.array_equal(base.iloc[cut_pos + 1:].to_numpy(),
                              pert.iloc[cut_pos + 1:].to_numpy(), equal_nan=True)

    # and the full-sample estimator is demonstrably NOT causal (the contrast)
    f1 = robust_z(d).iloc[: cut_pos + 1].to_numpy()
    f2 = robust_z(d2).iloc[: cut_pos + 1].to_numpy()
    assert not np.array_equal(f1, f2, equal_nan=True)


def test_single_row_perturbation_only_affects_that_row_onward():
    d = _panel(n=400, k=2)
    z0 = causal_robust_z(d, min_history_td=50)
    d2 = d.copy()
    d2.iloc[300, 0] = 500.0
    z1 = causal_robust_z(d2, min_history_td=50)
    assert np.array_equal(z0.iloc[:300].to_numpy(), z1.iloc[:300].to_numpy(),
                          equal_nan=True)
    assert not np.array_equal(z0.iloc[300:].to_numpy(), z1.iloc[300:].to_numpy(),
                              equal_nan=True)


# -------------------------------------------------------------- (2) BURN-IN
def test_burn_in_nan_behaviour():
    d = _panel(n=300, k=3)
    m = 120
    z = causal_robust_z(d, min_history_td=m)
    assert z.iloc[: m - 1].isna().all().all()          # before burn-in: all NaN
    assert z.iloc[m - 1:].notna().all().all()          # from row m onward: live
    assert burn_in_start(d, min_history_td=m) == d.index[m - 1]


def test_burn_in_counts_non_nan_observations_per_column():
    d = _panel(n=200, k=2)
    d.iloc[:50, 0] = np.nan                            # column 0 starts late
    z = causal_robust_z(d, min_history_td=60)
    assert z["f1"].iloc[59] == z["f1"].iloc[59]        # f1 live at row 60
    assert np.isnan(z["f0"].iloc[59])                  # f0 still burning in
    assert not np.isnan(z["f0"].iloc[109])             # 50 NaN + 60 obs
    assert burn_in_start(d, min_history_td=60) == d.index[109]


def test_burn_in_longer_than_sample_gives_all_nan():
    d = _panel(n=100, k=2)
    assert causal_robust_z(d, min_history_td=504).isna().all().all()


# ------------------------------------- (3) AGREEMENT ON THE FINAL ROW ONLY
def test_final_row_matches_full_sample_but_earlier_rows_do_not():
    """At the last date the expanding window IS the full sample, so the two
    estimators must agree there (up to float accumulation). Earlier rows must
    differ materially -- that gap is the contamination being removed."""
    d = _panel(n=900, k=4)
    zc = causal_robust_z(d, min_history_td=100)
    zf = robust_z(d)

    np.testing.assert_allclose(zc.iloc[-1].to_numpy(), zf.iloc[-1].to_numpy(),
                               rtol=1e-9, atol=1e-9)

    mid = (zc - zf).abs().iloc[100:400].mean().mean()
    assert mid > 1e-3, "causal and full-sample z should diverge away from the edge"


def test_causal_z_is_roughly_centred_late_in_sample():
    d = _panel(n=1500, k=3)
    zc = causal_robust_z(d, min_history_td=250)
    tail = zc.iloc[-500:]
    assert abs(float(tail.median().median())) < 0.15


# ---------------------------------------------------------- (4) IQR-0 GUARD
def test_zero_iqr_yields_nan_not_inf():
    idx = pd.bdate_range("2005-01-03", periods=300)
    const = pd.Series(5.0, index=idx)                  # IQR identically 0
    live = pd.Series(np.random.default_rng(3).normal(size=300), index=idx)
    d = pd.DataFrame({"const": const, "live": live})
    z = causal_robust_z(d, min_history_td=50)
    assert z["const"].isna().all()
    assert not np.isinf(z.to_numpy()[~np.isnan(z.to_numpy())]).any()
    assert z["live"].iloc[50:].notna().all()


def test_locally_constant_then_varying_column_recovers():
    """A column that is constant early has IQR == 0 -> NaN, and only recovers
    once enough varying observations have accumulated to lift the quartiles
    apart (>25% on each side of the constant value)."""
    idx = pd.bdate_range("2005-01-03", periods=800)
    v = np.concatenate([np.full(200, 2.0),
                        np.random.default_rng(5).normal(size=600) + 2.0])
    d = pd.DataFrame({"a": v}, index=idx)
    z = causal_robust_z(d, min_history_td=50)
    assert z["a"].iloc[50:199].isna().all()            # IQR == 0 window
    assert z["a"].iloc[-50:].notna().all()             # recovered


# ------------------------------------------------------------------- misc
def test_rejects_unsorted_index():
    d = _panel(n=120, k=2).iloc[::-1]
    with pytest.raises(ValueError):
        causal_robust_z(d, min_history_td=10)


def test_shape_and_labels_preserved():
    d = _panel(n=600, k=5)
    z = causal_robust_z(d, min_history_td=100)
    assert z.shape == d.shape
    assert list(z.columns) == list(d.columns)
    assert z.index.equals(d.index)
