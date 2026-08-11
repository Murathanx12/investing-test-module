"""CANON §19 — every arm reports its own 80%-power MDE, on every card.

NIGHT-10 measured 21 configurations across two independent audits and found
that NOT ONE reported an effect above its own detection threshold. Writing that
down as a rule was not enough: the corpse check only started working when it
became `lint_prereg.py`. So the MDE is computed on every scorecard whether or
not anyone remembers to ask for it, and these tests fail if it stops being.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.pf.scorecard import MDE_Z, SIG_Z, _power_block


def _series(mean_m: float, sd_m: float, n: int = 252, seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2002-01-31", periods=n, freq="ME")
    x = rng.normal(mean_m, sd_m, n)
    # centre exactly so the test controls the effect it is asserting about
    x = x - x.mean() + mean_m
    return pd.Series(x, index=idx)


def test_a_tiny_effect_is_not_reliably_detectable():
    """The night's whole finding, as a unit test."""
    out = _power_block(_series(0.001, 0.05))       # +1.2%/yr against 5%/mo sd
    assert out["status"] == "OK"
    assert out["above_80pct_power_mde"] is False
    assert "NOT RELIABLY DETECTABLE" in out["reading"]
    assert "CANON" in out["reading"]


def test_a_large_effect_is_detectable():
    out = _power_block(_series(0.02, 0.03))        # +24%/yr against 3%/mo sd
    assert out["above_80pct_power_mde"] is True
    assert out["significant_at_5pct"] is True
    assert "large enough" in out["reading"]


def test_significant_but_underpowered_says_so():
    """The winner's-curse region: clears 1.96 SE, misses 2.8 SE."""
    n, sd = 252, 0.05
    se_m = sd / np.sqrt(n)
    mean_m = 2.3 * se_m                            # between SIG_Z and MDE_Z
    out = _power_block(_series(mean_m, sd))
    assert out["significant_at_5pct"] is True
    assert out["above_80pct_power_mde"] is False
    assert "systematically overstate" in out["reading"]


def test_thresholds_are_the_declared_multiples_of_the_standard_error():
    out = _power_block(_series(0.005, 0.04))
    # each field is rounded to 5dp independently, so the identity holds to
    # within that rounding and not to machine precision
    assert out["mde_80pct_power_annual"] == pytest.approx(
        MDE_Z * out["se_annual"], abs=1e-4)
    assert out["sig_threshold_annual"] == pytest.approx(
        SIG_Z * out["se_annual"], abs=1e-4)
    assert out["mde_80pct_power_annual"] > out["sig_threshold_annual"]


def test_mde_shrinks_as_the_sample_grows():
    short = _power_block(_series(0.002, 0.05, n=60))
    long = _power_block(_series(0.002, 0.05, n=600))
    assert long["mde_80pct_power_annual"] < short["mde_80pct_power_annual"]


def test_too_short_a_series_refuses_to_estimate():
    out = _power_block(_series(0.01, 0.04, n=6))
    assert out["status"] == "TOO_SHORT"
    assert "mde_80pct_power_annual" not in out


def test_the_effect_compared_is_arithmetic_not_geometric():
    """The SE is estimated from the arithmetic series, so the effect compared
    against it must be arithmetic too. Mixing the two compares a geometric
    number to an arithmetic standard error."""
    s = _series(0.01, 0.06)
    out = _power_block(s)
    assert out["arithmetic_excess_annual"] == pytest.approx(
        12 * float(s.mean()), rel=1e-9)


def test_every_scorecard_carries_a_power_block():
    """The point of the whole exercise: it cannot be forgotten."""
    import inspect
    from aegis_brain.pf import scorecard as SC
    src = inspect.getsource(SC.scorecard)
    assert '"power": _power_block' in src, (
        "the power block was removed from the scorecard — CANON §19 is only "
        "enforced if it is computed unconditionally")
