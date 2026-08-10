"""Dimensional invariants for the typed paired statistics.

These tests exist because of a real bug: NIGHT-7's published trigger receipts
reported MDEs of 43%-143%/yr, because one generic helper annualised whatever it
was handed. The point of this file is that mixing the types is now impossible to
do silently — every result names its own unit, and only the return-typed path
multiplies by twelve.
"""
import numpy as np
import pandas as pd
import pytest

from aegis_brain.pf.stats import (is_typed, paired_brier_stats,
                                  paired_ic_stats, paired_probability_stats,
                                  paired_return_stats)


def series(mean, sd, n=240, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1990-01-31", periods=n, freq="ME")
    return pd.Series(rng.normal(mean, sd, n), index=idx)


def test_a_monthly_return_difference_annualises_by_twelve():
    a = series(0.001, 0.02, seed=1)
    b = series(0.0, 0.02, seed=2)
    r = paired_return_stats(a, b)
    # both fields are rounded for the receipt, so compare at printed precision
    assert r["annualized_pct"] == pytest.approx(r["mean_monthly"] * 12, abs=1e-4)
    assert r["unit"].startswith("simple return")


def test_an_ic_difference_is_never_annualised():
    a = series(0.03, 0.15, seed=3)
    b = series(0.0, 0.15, seed=4)
    r = paired_ic_stats(a, b)
    assert not any("annual" in k for k in r if k != "annualization")
    assert r["annualization"].startswith("none")
    # the headline number is the raw mean, not twelve times it
    assert r["dic_mean"] == pytest.approx(float((a - b).mean()), abs=1e-5)


def test_ic_mde_stays_in_ic_units():
    d = series(0.0, 0.15, n=450, seed=5)
    r = paired_ic_stats(d, pd.Series(0.0, index=d.index))
    se = d.std(ddof=1) / np.sqrt(len(d))
    assert r["mde_ic_units"] == pytest.approx(2 * se, abs=1e-5)
    # an IC MDE of 0.014 must NOT come back as 0.17
    assert r["mde_ic_units"] < 0.05


def test_every_typed_result_carries_its_unit():
    a, b = series(0.001, 0.02, seed=6), series(0.0, 0.02, seed=7)
    for fn in (paired_return_stats, paired_ic_stats, paired_probability_stats,
               paired_brier_stats):
        assert is_typed(fn(a, b)), fn.__name__


def test_brier_declares_its_direction():
    a, b = series(0.20, 0.05, seed=8), series(0.25, 0.05, seed=9)
    r = paired_brier_stats(a, b)
    assert r["delta_brier"] < 0
    assert "lower is better" in r["direction"]


def test_short_series_refuse_rather_than_report():
    a = series(0.001, 0.02, n=6, seed=10)
    b = series(0.0, 0.02, n=6, seed=11)
    r = paired_return_stats(a, b)
    assert r["insufficient"] is True
    assert "mean_monthly" not in r


def test_the_night7_shape_of_bug_cannot_recur():
    """Feeding an ALREADY-annualised return series to the return path raises.

    The guard lives in `mde_annualized`; this asserts the typed wrapper does not
    route around it.
    """
    a = series(0.001 * 12, 0.02 * 12, n=120, seed=12)
    b = series(0.0, 0.02 * 12, n=120, seed=13)
    with pytest.raises(ValueError, match="units error"):
        paired_return_stats(a, b)
