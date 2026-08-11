"""The Layer-1 information instrument: alignment, units, and what it may claim.

The incumbent instrument (EW top-50, monthly, minus benchmark) resolves 6.5 to
24.8 %/yr at 80% power. 195 experiments were killed with it. This module exists
to measure the same question on the cross-section instead, and these tests pin
the three things that would make it worse than useless:

  * a look-ahead in the forward-return alignment, which would manufacture
    information out of nothing;
  * an over-claim in the verdict, where "the cross-section carries information"
    quietly becomes "this makes money";
  * a null issued by a design too blunt to support one, which is the exact
    defect the instrument was built to end.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.pf.information import (LARGEST_CREDIBLE_EFFECT_ANN,
                                        cross_sectional_information,
                                        forward_return, instrument_comparison,
                                        top_n_long_only_excess)


def _frames(n_names=300, n_months=180, effect=0.0, seed=3, idio=0.10):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2002-01-31", periods=n_months, freq="ME")
    cols = [str(i) for i in range(n_names)]
    z = rng.normal(size=(n_months, n_names))
    ret = rng.normal(0.0, idio, size=(n_months, n_names))
    ret[1:] += effect * z[:-1]
    return (pd.DataFrame(z, index=idx, columns=cols),
            pd.DataFrame(ret, index=idx, columns=cols))


# ── alignment ───────────────────────────────────────────────────────────────
def test_forward_return_is_aligned_to_the_formation_month():
    """`fwd.loc[t]` must be the return AFTER t, never including t itself.

    An off-by-one here is not a small error — it hands the estimator the return
    it is trying to predict, and every signal on the panel becomes significant.
    """
    idx = pd.date_range("2020-01-31", periods=5, freq="ME")
    r = pd.DataFrame({"A": [0.10, 0.20, 0.30, 0.40, 0.50]}, index=idx)
    f1 = forward_return(r, 1)
    assert f1.loc[idx[0], "A"] == pytest.approx(0.20)
    assert np.isnan(f1.loc[idx[-1], "A"])
    f2 = forward_return(r, 2)
    assert f2.loc[idx[0], "A"] == pytest.approx(1.20 * 1.30 - 1.0)
    assert np.isnan(f2.loc[idx[-2], "A"])


def test_a_signal_that_knows_nothing_finds_nothing():
    sig, ret = _frames(effect=0.0)
    out = cross_sectional_information(sig, ret, name="noise")
    assert out.verdict != "INFORMATION_PRESENT"
    assert abs(out.long_short_spread_ann) < out.long_short_spread_mde_ann


def test_a_planted_effect_is_found_and_its_size_recovered():
    sig, ret = _frames(effect=0.004)
    out = cross_sectional_information(sig, ret, name="planted")
    assert out.verdict == "INFORMATION_PRESENT"
    assert out.long_short_spread_ann > 0
    assert out.lambda_t is not None and out.lambda_t > 2


def test_a_reversed_signal_is_found_with_the_opposite_sign():
    """Direction sensitivity. The OSAP adapter shipped a double-sign bug that a
    magnitude-only check could not have caught."""
    sig, ret = _frames(effect=0.004)
    pos = cross_sectional_information(sig, ret, name="p")
    neg = cross_sectional_information(-sig, ret, name="n")
    assert pos.long_short_spread_ann > 0 > neg.long_short_spread_ann
    assert pos.long_short_spread_ann == pytest.approx(
        -neg.long_short_spread_ann, rel=0.05)


# ── what it may claim ───────────────────────────────────────────────────────
def test_the_result_never_licenses_a_money_claim():
    sig, ret = _frames(effect=0.004)
    out = cross_sectional_information(sig, ret)
    assert "LAYER 1 ONLY" in out.licenses
    assert "no money claim" in out.licenses
    assert "INFORMATION result" in out.reading


def test_an_underpowered_design_may_not_issue_a_kill():
    """The whole point. A blunt design returns UNRESOLVED, never NO_INFORMATION.

    Made blunt by giving it a handful of very volatile names, which is how a
    real underpowered slice arises — a thin segment, not a short window.
    """
    sig, ret = _frames(n_names=40, n_months=60, effect=0.0, idio=0.45)
    out = cross_sectional_information(sig, ret, min_names=30)
    assert out.long_short_spread_mde_ann > LARGEST_CREDIBLE_EFFECT_ANN
    assert out.verdict == "UNRESOLVED"
    assert "may NOT be recorded as a kill" in out.reading
    assert out.diagnostics["powered_to_issue_a_kill"] is False


def test_a_powered_design_may_issue_a_kill():
    sig, ret = _frames(n_names=800, n_months=240, effect=0.0, idio=0.08)
    out = cross_sectional_information(sig, ret)
    assert out.long_short_spread_mde_ann <= LARGEST_CREDIBLE_EFFECT_ANN
    assert out.verdict == "NO_INFORMATION"
    assert "ruled OUT" in out.reading


def test_a_significant_effect_is_never_called_evidence_of_absence():
    """A defect this rule actually had, found on real data and kept as a test.

    The first version issued NO_INFORMATION whenever the effect missed the MDE
    and the MDE happened to be small. Run against analyst revisions at a
    12-month horizon it labelled an arm with **t = 2.21** "evidence of absence".
    An effect that is significantly different from zero cannot be evidence that
    there is no effect, however fine the ruler.

    NO_INFORMATION is an equivalence claim: the whole 95% interval must lie
    inside the region already declared not worth having.
    """
    # a small, real, significant effect in a design fine enough to see it
    sig, ret = _frames(n_names=900, n_months=252, effect=0.0016, idio=0.08)
    out = cross_sectional_information(sig, ret)
    assert out.long_short_spread_t is not None
    assert abs(out.long_short_spread_t) >= 1.96, "test needs a significant arm"
    assert out.verdict != "NO_INFORMATION", (
        "a significantly non-zero effect was recorded as evidence of absence")


def test_a_kill_requires_the_whole_interval_inside_the_uninteresting_region():
    """The equivalence bound, stated directly: |effect| + 1.96 SE < 5 %/yr."""
    sig, ret = _frames(n_names=800, n_months=240, effect=0.0, idio=0.08)
    out = cross_sectional_information(sig, ret)
    se = out.long_short_spread_mde_ann / 2.8
    upper = abs(out.long_short_spread_ann) + 1.96 * se
    assert upper < LARGEST_CREDIBLE_EFFECT_ANN
    assert out.verdict == "NO_INFORMATION"


def test_the_kill_threshold_is_frozen_in_the_module():
    """A caller must not be able to widen the credible-effect ceiling to make
    its own null decisive — so it is a module constant, not a parameter."""
    import inspect
    sig = inspect.signature(cross_sectional_information)
    assert "largest_credible_effect" not in sig.parameters
    assert LARGEST_CREDIBLE_EFFECT_ANN == 0.05


# ── units ───────────────────────────────────────────────────────────────────
def test_the_rank_ic_carries_no_per_year_reading():
    """NIGHT-8: a Spearman correlation multiplied by 12 is not 'per year', it
    is nothing at all. The units dict must say so."""
    sig, ret = _frames(effect=0.002)
    out = cross_sectional_information(sig, ret)
    assert "NOT annualisable" in out.units["rank_ic_mean"]
    assert -1.0 <= out.rank_ic_mean <= 1.0


def test_a_longer_horizon_is_not_counted_twelve_times_over():
    """An h-month spread is earned h months at a time, so it annualises by 12/h.

    Scaling a 12-month holding return by 12 would report a 6%/yr effect as 72%.
    """
    sig, ret = _frames(n_months=240, effect=0.004)
    h1 = cross_sectional_information(sig, ret, horizon=1)
    h6 = cross_sectional_information(sig, ret, horizon=6)
    # the plant only acts on the first month of any window, so the 6-month
    # annualised spread must be far SMALLER, never ~6x larger
    assert h6.long_short_spread_ann < h1.long_short_spread_ann
    assert h6.units["estimator"].startswith("Fama-MacBeth")


def test_overlapping_horizons_get_at_least_2h_hac_lags():
    sig, ret = _frames(n_months=240)
    out = cross_sectional_information(sig, ret, horizon=12)
    assert out.diagnostics["hac_lags"] >= 24


# ── the power claim, measured rather than asserted ──────────────────────────
def test_the_cross_section_resolves_a_smaller_effect_than_the_top_50_book():
    """The claim that justifies the module — pinned at the size it actually is.

    This test was first written asserting a factor above 2 and it FAILED, at
    1.31. The failure was informative and is recorded here rather than tuned
    away: in a world of exchangeable names the cross-sectional instrument's only
    advantage is breadth (600 names against 50), which is worth roughly
    sqrt-of-something and not an order of magnitude. Adding beta dispersion,
    sector factors and correlated within-basket residuals to the synthetic world
    moved the ratio between 1.29 and 1.52 and no further.

    So the large gain the design was argued for is NOT a property of the
    estimator that can be demonstrated on synthetic data. Whether it exists at
    all is a question about the real panel — how much of a real top-50 book's
    variance is incidental exposure rather than disagreement about the signal —
    and it is measured there, on a real signal, by
    `scripts/run_revision_information.py`. Nothing in this module may quote a
    power gain that has not been measured on the data it is claimed for.
    """
    sig, ret = _frames(n_names=600, n_months=240, effect=0.0, idio=0.10)
    bench = ret.mean(axis=1)
    cmp = instrument_comparison(sig, ret, bench, name="noise")
    ratio = cmp["mde_ratio_incumbent_over_cross_sectional"]
    assert ratio > 1.15, (
        "the cross-sectional instrument is not resolving a smaller effect than "
        "the top-50 book even on breadth alone — the premise of Layer 1 is "
        "unsupported and the incumbent should be kept")
    assert ratio < 3.0, (
        "an exchangeable-names world cannot produce a large power gain; a big "
        "ratio here means the comparison is measuring something other than "
        "what it claims")
    # the breadth that produces even this much: ~600 names x 240 months
    assert cmp["cross_sectional"]["n_obs"] > 100 * cmp[
        "incumbent_top_n_long_only"]["n_months"]


def test_the_incumbent_reproduction_is_a_long_only_book_minus_the_benchmark():
    sig, ret = _frames(n_names=200, n_months=120, effect=0.01)
    bench = ret.mean(axis=1)
    ex = top_n_long_only_excess(sig, ret, bench, top_n=50)
    assert len(ex) > 100
    assert ex.mean() > 0          # a planted effect must show in the incumbent too


def test_eligibility_is_respected():
    sig, ret = _frames(n_names=200, n_months=120)
    elig = pd.DataFrame(True, index=sig.index, columns=sig.columns)
    elig.iloc[:, 100:] = False
    out = cross_sectional_information(sig, ret, eligible=elig)
    assert out.mean_names_per_month == pytest.approx(100, abs=1)


# ── the leg decomposition: what a long-only book can actually hold ──────────
def _legs(out):
    return out.diagnostics["long_only_decomposition"]


def test_the_legs_sum_to_the_spread_exactly():
    """An identity, not an estimate. If the legs stop summing to the spread the
    decomposition is measuring something other than the spread it decomposes,
    and every share quoted from it would be wrong by an unknown amount."""
    out = cross_sectional_information(*_frames(effect=0.004), name="planted")
    legs = _legs(out)
    assert legs["legs_sum_to_spread"] is True
    assert legs["long_leg_ann"] + legs["short_leg_ann"] == pytest.approx(
        out.long_short_spread_ann, abs=1e-9)


def test_a_symmetric_effect_splits_roughly_evenly_between_the_legs():
    """The planted effect here is linear in the signal and symmetric, so neither
    leg should carry the spread on its own. This is the CONTROL for the real
    finding: when a real signal comes back 90/10, that asymmetry is a property
    of the data and not of the estimator."""
    out = cross_sectional_information(*_frames(effect=0.004), name="planted")
    share = _legs(out)["short_leg_share_of_spread"]
    assert 0.3 < share < 0.7


def test_a_long_only_verdict_is_never_issued_from_the_dollar_neutral_spread():
    """The whole point. A spread can clear its MDE while the long leg does not,
    and in that case the long-only answer is UNRESOLVED — never a pass inherited
    from the spread."""
    out = cross_sectional_information(*_frames(effect=0.004), name="planted")
    legs = _legs(out)
    assert out.verdict == "INFORMATION_PRESENT"
    if abs(legs["long_leg_ann"]) < legs["long_leg_mde_ann"]:
        assert legs["verdict"] == "LONG_LEG_UNRESOLVED"
    else:
        assert legs["verdict"] == "LONG_LEG_SURVIVES"


def test_the_leg_difference_is_tested_as_a_difference_not_read_off_the_share():
    """CANON §18. The share has no standard error; the difference does, and it
    is estimated from the paired monthly series so the legs' common market
    exposure cancels instead of being carried into the comparison."""
    out = cross_sectional_information(*_frames(effect=0.004), name="planted")
    legs = _legs(out)
    assert legs["difference_mde_ann"] > 0
    assert legs["difference_t"] is not None
    # and the difference must not be a restatement of the two MDEs added up
    assert legs["difference_mde_ann"] < (
        legs["long_leg_mde_ann"] + legs["short_leg_mde_ann"])


def test_a_signal_that_knows_nothing_gives_neither_leg_an_edge():
    out = cross_sectional_information(*_frames(effect=0.0), name="noise")
    legs = _legs(out)
    assert legs["verdict"] == "LONG_LEG_UNRESOLVED"
    assert abs(legs["long_leg_ann"]) < legs["long_leg_mde_ann"]
