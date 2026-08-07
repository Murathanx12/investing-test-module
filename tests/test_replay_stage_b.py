"""Stage-B pure-function tests. No real panel, no candidate rows, no confirm
data — the terminal routing and resolver bookkeeping are what can fail
silently."""

import pytest

from aegis_brain.calibration.replay_stage_b import (
    CONFIRM_T_IC,
    MIN_CONFIRM_MONTHS,
    SIZE_BAND_T_IC,
    confirm_verdict,
    resolve_signal,
)


def _summary(months=72, ic_mean=0.01, t_ic=2.0):
    return {"months": months, "ic_mean": ic_mean, "t_ic": t_ic}


def test_confirm_verdict_routing():
    assert confirm_verdict(_summary(t_ic=2.0)) == ("ADOPT_075", 0.75)
    assert confirm_verdict(_summary(t_ic=1.0)) == ("ADOPT_0", 0.0)
    assert confirm_verdict(_summary(t_ic=0.4)) == ("CONFIRM_FAIL", 0.0)
    assert confirm_verdict(_summary(ic_mean=-0.001, t_ic=3.0)) == (
        "CONFIRM_FAIL", 0.0)
    assert confirm_verdict(_summary(months=20, t_ic=3.0)) == (
        "SUPPORT_INADEQUATE", 0.0)


def test_confirm_verdict_boundaries():
    # >= comparisons, frozen semantics
    assert confirm_verdict(_summary(t_ic=CONFIRM_T_IC))[0] == "ADOPT_0"
    assert confirm_verdict(_summary(t_ic=SIZE_BAND_T_IC))[0] == "ADOPT_075"
    assert confirm_verdict(_summary(months=MIN_CONFIRM_MONTHS))[0] != (
        "SUPPORT_INADEQUATE")


def test_resolver_finds_batch1_without_panel():
    sig, src = resolve_signal("vol_12m_low", panel=None)
    assert sig is not None and sig.name == "vol_12m_low"
    assert src == "batch1"


def test_resolver_reports_reasons_not_silence():
    sig, reason = resolve_signal("does_not_exist_anywhere", panel=None)
    assert sig is None
    # every probe left a trace — nothing was silently skipped
    for label in ("batch1", "batch7", "batch9"):
        assert label in reason
