"""The guards have to be tested, or they are prose again.

Every test here is a sentence the project actually wrote, or nearly wrote, and
should not have.
"""
from __future__ import annotations

import pytest

from aegis_brain.verdicts import (MEANING, Finding, Verdict,
                                  VerdictLanguageError, check_language,
                                  classify, enforce)


def test_every_state_has_a_meaning():
    assert set(MEANING) == set(Verdict)
    for v, m in MEANING.items():
        assert len(m) > 40, v


# ── the NIGHT-4 failure, as a test ──────────────────────────────────────────
def test_unresolved_may_not_print_reject():
    """The exact sentence that caused the NIGHT-3 retraction."""
    bad = check_language(
        Verdict.UNRESOLVED,
        "The ordering contribution is +1.46%/yr at t=0.43, so we REJECT the "
        "hypothesis that ordering matters.")
    assert bad
    assert any("reject" in b.lower() for b in bad)


def test_unresolved_phrased_honestly_passes():
    enforce(Verdict.UNRESOLVED,
            "The ordering contribution is +1.46%/yr at t 0.43 against an MDE "
            "of 6.2%/yr: unmeasured at this power, not zero.")


def test_no_state_may_say_proves():
    for v in Verdict:
        assert check_language(v, "This proves the strategy has an edge.")


def test_confirmed_may_still_not_overclaim():
    with pytest.raises(VerdictLanguageError):
        enforce(Verdict.CONFIRMED,
                "The result proves the signal works and is risk-free.")


def test_confirmed_phrased_honestly_passes():
    enforce(Verdict.CONFIRMED,
            "The primary metric cleared its pre-registered bar at +4.23%/yr, "
            "t 3.65 over 482 months.")


# ── the FACTOR_EXPLAINED distinction PF-4 needed and the old taxonomy lacked ─
def test_factor_explained_may_not_be_written_as_no_edge():
    bad = check_language(
        Verdict.FACTOR_EXPLAINED,
        "A small-cap profitability factor absorbs the alpha, so there is no "
        "edge here.")
    assert bad


def test_factor_explained_may_not_deny_the_return():
    bad = check_language(
        Verdict.FACTOR_EXPLAINED,
        "Spanned by the factor — zero return to this strategy.")
    assert any("denies a return" in b for b in bad)


def test_factor_explained_phrased_honestly_passes():
    enforce(Verdict.FACTOR_EXPLAINED,
            "Incremental alpha falls from +4.23%/yr (t 3.65) to +1.04% "
            "(t 1.07) once a small-cap profitability factor is included: the "
            "return is real and already paid by a known factor. A harvest, "
            "honestly named.")


def test_power_failed_may_not_be_written_as_refuted():
    assert check_language(Verdict.POWER_FAILED,
                          "The signal was refuted by the scan.")


def test_implementation_failed_may_not_say_the_idea_is_dead():
    assert check_language(Verdict.IMPLEMENTATION_FAILED,
                          "Turnover ate it, so the idea is dead.")


# ── the MDE requirement ─────────────────────────────────────────────────────
def test_unresolved_finding_requires_an_mde():
    with pytest.raises(VerdictLanguageError):
        Finding(name="x", state=Verdict.UNRESOLVED, primary_metric="excess")


def test_power_failed_finding_requires_an_mde():
    with pytest.raises(VerdictLanguageError):
        Finding(name="x", state=Verdict.POWER_FAILED, primary_metric="excess")


def test_unresolved_finding_with_mde_is_fine():
    f = Finding(name="x", state=Verdict.UNRESOLVED, primary_metric="excess",
                point_estimate=1.4, mde=6.2, bar=3.0)
    assert f.mde == 6.2


# ── classify() ──────────────────────────────────────────────────────────────
def test_never_ran_is_data_failed():
    v, why = classify(months=0, point=None, mde=None, bar=3.0)
    assert v is Verdict.DATA_FAILED
    assert "never produced" in why


def test_clearly_negative_and_adequately_powered_is_rejected():
    v, _ = classify(months=180, point=-6.0, mde=2.0, bar=3.0)
    assert v is Verdict.REJECTED


def test_a_wide_interval_does_not_rescue_an_estimate_far_below_the_bar():
    """The search's median row: -1.4%/yr point, 3.7%/yr MDE, 3% bar.

    Written first as `POWER_FAILED` and the implementation disagreed. The
    implementation is right and the expectation was the wishful one: an upper
    bound of +2.3% excludes a +3.0% bar, so the bar IS refuted, and a large MDE
    does not launder a point estimate that far below it. Recorded as a test so
    the hopeful reading cannot come back.
    """
    v, why = classify(months=180, point=-1.4, mde=3.7, bar=3.0)
    assert v is Verdict.REJECTED
    assert "excludes" in why


def test_underpowered_straddle_is_power_failed_not_rejected():
    """Point near the null with an MDE wider than the bar: genuinely blind."""
    v, why = classify(months=180, point=0.4, mde=3.7, bar=3.0)
    assert v is Verdict.POWER_FAILED
    assert "says nothing" in why


def test_cost_killed_is_implementation_failed():
    v, _ = classify(months=180, point=0.5, mde=3.0, bar=3.0,
                    gross_t=2.64, net_t=0.48)
    assert v is Verdict.IMPLEMENTATION_FAILED


def test_information_without_money_is_implementation_failed():
    """t_ic 6.63 with net t 0.37 — price_level, small. Real information."""
    v, why = classify(months=180, point=0.7, mde=3.0, bar=3.0,
                      gross_t=0.65, net_t=0.37, ic_t=6.63)
    assert v is Verdict.IMPLEMENTATION_FAILED
    assert "does not convert" in why


def test_strong_net_result_is_not_swept_into_implementation_failed():
    """conc_low, small: t_ic 7.41 WITH net t 2.31 — the money leg did show up.

    The first implementation used `ic_t >= 3.0 > net_t`, a Python chained
    comparison meaning `net_t < 3.0`, and so labelled this IMPLEMENTATION_FAILED
    — a result whose net t beat most of the search. Pinned here.
    """
    v, _ = classify(months=180, point=2.6, mde=2.2, bar=3.0,
                    gross_t=2.6, net_t=2.31, ic_t=7.41)
    assert v is not Verdict.IMPLEMENTATION_FAILED


def test_adequately_powered_straddle_is_unresolved():
    v, _ = classify(months=180, point=2.0, mde=2.0, bar=3.0)
    assert v is Verdict.UNRESOLVED


def test_classification_is_deterministic():
    args = dict(months=180, point=0.4, mde=3.7, bar=3.0)
    assert {classify(**args)[0] for _ in range(50)} == {Verdict.POWER_FAILED}
