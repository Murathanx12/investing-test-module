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


# ── the HAC correction ──────────────────────────────────────────────────────
# As shipped on NIGHT-10 this block divided by sigma/sqrt(n) while every t-stat
# beside it was Newey-West. The two estimators answer different questions about
# the same series, and the design's power was being certified by the one the
# design refused to trust for inference. Re-audited: the ten ANALYST-IBES-1 arms
# move from 6.47-20.66 %/yr to 6.47-24.82 %/yr, HAC/IID ratio up to 1.24.


def _ar1(rho: float, sd_m: float = 0.04, n: int = 252, mean_m: float = 0.0,
         seed: int = 11) -> pd.Series:
    """AR(1) monthly series with the unconditional sd held at `sd_m`."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2002-01-31", periods=n, freq="ME")
    innov = sd_m * np.sqrt(1.0 - rho ** 2)
    x, prev = np.empty(n), 0.0
    for i in range(n):
        prev = rho * prev + rng.normal(0.0, innov)
        x[i] = prev
    x = x - x.mean() + mean_m
    return pd.Series(x, index=idx)


def test_newey_west_returns_the_standard_error_behind_its_t():
    """Power and significance must be computable from the same estimator.

    They could not be before: `newey_west_tstat` returned only `t`, so any
    caller wanting an MDE had to re-derive an SE, and every one of them
    re-derived the IID one.
    """
    from aegis_brain.harness.benchmark import newey_west_tstat
    s = _ar1(0.3, mean_m=0.004)
    nw = newey_west_tstat(s, lags=12)
    assert nw["se"] is not None and nw["se"] > 0
    assert nw["se_iid"] == pytest.approx(
        float(s.std(ddof=1)) / np.sqrt(len(s)), rel=1e-12)
    assert nw["t"] == pytest.approx(float(s.mean()) / nw["se"], rel=1e-12)


def test_positive_autocorrelation_widens_the_detection_threshold():
    """The defect, as a unit test: a persistent series is harder to resolve
    than an IID one of the same variance, and the IID formula cannot see it."""
    out = _power_block(_ar1(0.35))
    assert out["hac_over_iid"] > 1.15
    assert out["mde_80pct_power_annual_hac"] > out["mde_80pct_power_annual_iid"]
    assert out["mde_estimator"] == "HAC"
    assert out["mde_80pct_power_annual"] == pytest.approx(
        out["mde_80pct_power_annual_hac"], abs=1e-9)


def test_the_mde_never_falls_below_the_iid_threshold():
    """A below-IID HAC standard error is not banked as free power.

    When the Bartlett sum comes out net-negative — common in finite samples —
    the HAC SE drops below IID. Adopting it would narrow the MDE, which would
    license a stronger NULL on the strength of noise in the autocovariances.
    Three of the ten re-audited arms are in exactly this state.
    """
    found_below = False
    for seed in range(40):
        out = _power_block(_ar1(-0.05, seed=seed))
        assert out["mde_80pct_power_annual"] >= (
            out["mde_80pct_power_annual_iid"] - 1e-9), (
            "the MDE dipped below the IID threshold — a null licensed by a "
            "smaller-than-IID HAC SE is licensed by estimation noise")
        if out["mde_80pct_power_annual_hac"] < out["mde_80pct_power_annual_iid"]:
            found_below = True
            assert out["mde_estimator"].startswith("IID")
    assert found_below, "no below-IID HAC draw appeared; the guard went untested"


def test_significance_uses_the_hac_standard_error():
    """Inference stays HAC even where the MDE takes the conservative one — the
    two numbers serve different purposes and are allowed to differ."""
    out = _power_block(_ar1(0.35, mean_m=0.004))
    assert out["sig_threshold_annual"] == pytest.approx(
        SIG_Z * out["se_annual_hac"], abs=1e-4)
    assert out["t_newey_west"] is not None


def test_the_power_block_does_not_reintroduce_a_bare_iid_mde():
    """Source-level guard, matching the one above it.

    The failure was not that someone doubted HAC; it was that the IID formula
    was the only one written down. If both estimators stop being reported, the
    next reader has no way to see which one is binding.
    """
    import inspect
    from aegis_brain.pf import scorecard as SC
    src = inspect.getsource(SC._power_block)
    assert "newey_west_tstat" in src, (
        "the power block stopped computing a HAC standard error — its MDE is "
        "IID again, which is the NIGHT-10 defect")
    for field in ("mde_80pct_power_annual_iid", "mde_80pct_power_annual_hac",
                  "mde_estimator"):
        assert field in src, f"{field} is no longer reported"
