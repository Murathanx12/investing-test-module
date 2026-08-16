"""R13e — the axis N9 died on, checked at registration.

N9 held out six securities no prior slice had read and scored them over
1999-2026, a calendar it had selected its rules on. Split at the selection
boundary: 1.464 (p=0.010) overlapping, 0.765 (p=0.771) disjoint. The slice
register stored the period all along, but its reuse identity was `shared
securities AND overlapping period`, so a confirmation on fresh tickers over the
same calendar was clean BY CONSTRUCTION.

These tests pin the axis. Every one of them would have refused N9's Amendment 1
before it ran.
"""

from __future__ import annotations

import pytest

from aegis_brain.discipline import prereg_lint as PL
from aegis_brain.discipline.prereg_power import (
    CALENDAR_DAYS_PER_TRADING_DAY, HOLIDAY_BUFFER_DAYS,
    check_calendar_disjointness, parse_window, required_gap_days)


def _doc(**kw) -> str:
    body = "\n".join(f"{k} = {v}" for k, v in kw.items())
    return f"# PREREG — synthetic\n\n```\n{body}\n```\n"


_CONFIRM = dict(slice_purpose="CONFIRM",
                slice_securities="DIA XLV XLI XLP XLU XLB",
                information_cutoff="2026-08-15",
                outcome_horizon_days=20)


# ── the N9 receipt ─────────────────────────────────────────────────────────
def test_n9_amendment_1_would_have_been_refused():
    """The exact design, in the exact fields, refused before compute."""
    r = check_calendar_disjointness(_doc(
        **_CONFIRM,
        selection_period="1999-01-01 .. 2015-12-31",
        slice_period="1999-01-01 .. 2026-08-15"))
    assert r["verdict"] == "CALENDAR_OVERLAPPING_CONFIRMATION"
    assert r["blocked"]
    assert r["overlap_days"] > 6000              # seventeen years of it
    assert "SECURITIES is not holding out DATA" in r["why"]


def test_the_disjoint_half_of_n9_passes():
    """The half that answered 0.765 is the half R13e would have allowed."""
    r = check_calendar_disjointness(_doc(
        **_CONFIRM,
        selection_period="1999-01-01 .. 2015-12-31",
        slice_period="2016-03-01 .. 2026-08-15"))
    assert r["verdict"] == "CALENDAR_DISJOINT"
    assert not r["blocked"]


# ── silence, and the ways round it ─────────────────────────────────────────
def test_silence_is_refused_for_a_confirm():
    r = check_calendar_disjointness(_doc(**_CONFIRM,
                                         slice_period="1999-01-01 .. 2026-08-15"))
    assert r["verdict"] == "UNDECLARED_SELECTION_WINDOW"
    assert r["blocked"]


def test_explore_is_not_asked():
    """R13e gates transfer claims. Exploration has nothing to confound."""
    r = check_calendar_disjointness(_doc(slice_purpose="EXPLORE"))
    assert r["verdict"] == "NOT_APPLICABLE"
    assert not r["blocked"]


def test_no_prior_fit_is_declarable_and_is_a_claim():
    r = check_calendar_disjointness(_doc(**_CONFIRM,
                                         slice_period="2016-01-01 .. 2026-08-15",
                                         selection_period="NONE"))
    assert r["verdict"] == "CALENDAR_DISJOINT_BY_CONSTRUCTION"
    assert not r["blocked"]
    assert "the declaration is false" in r["why"]


def test_no_prior_fit_contradicts_a_named_parent():
    """The one derivation available at registration: a descendant inherits."""
    r = check_calendar_disjointness(_doc(**_CONFIRM,
                                         slice_period="2016-01-01 .. 2026-08-15",
                                         selection_period="NONE",
                                         parent_trial="N9"))
    assert r["verdict"] == "SELECTION_WINDOW_CONTRADICTS_PARENT"
    assert r["blocked"]


def test_a_parent_declared_as_none_is_not_a_contradiction():
    r = check_calendar_disjointness(_doc(**_CONFIRM,
                                         slice_period="2016-01-01 .. 2026-08-15",
                                         selection_period="NONE",
                                         parent_trial="NONE"))
    assert not r["blocked"]


def test_an_unparseable_window_is_refused_not_assumed():
    r = check_calendar_disjointness(_doc(**_CONFIRM,
                                         slice_period="the modern era",
                                         selection_period="early history"))
    assert r["verdict"] == "UNPARSEABLE_WINDOW"
    assert r["blocked"]


# ── the horizon gap: zero overlap is necessary, not sufficient ─────────────
def test_a_confirmation_abutting_selection_is_refused():
    """Labels run forward; the last selection rows reach into the next window."""
    r = check_calendar_disjointness(_doc(
        **_CONFIRM,
        selection_period="1999-01-01 .. 2015-12-31",
        slice_period="2016-01-04 .. 2026-08-15"))
    assert r["verdict"] == "CONFIRMATION_WINDOW_ABUTS_SELECTION"
    assert r["blocked"]
    assert r["gap_days"] == 4
    assert r["required_gap_days"] == required_gap_days(20)


def test_the_gap_is_the_measured_one_not_one_point_five():
    """1.5x was measured failing on 15.7% of 20-bar boundaries."""
    assert required_gap_days(20) == 42                 # 28 + 14, vs 1.5x = 30
    assert required_gap_days(60) == 98                 # 84 + 14, vs 1.5x = 90
    assert required_gap_days(20) > 1.5 * 20
    assert CALENDAR_DAYS_PER_TRADING_DAY == 7.0 / 5.0
    assert HOLIDAY_BUFFER_DAYS == 14


def test_no_horizon_declared_means_no_gap_required():
    """R13e does not invent a horizon; R13 is the gate that requires one."""
    assert required_gap_days(None) == 0
    r = check_calendar_disjointness(_doc(
        slice_purpose="CONFIRM", slice_securities="QQQ",
        information_cutoff="2026-08-15",
        selection_period="1999-01-01 .. 2015-12-31",
        slice_period="2016-01-01 .. 2026-08-15"))
    assert r["verdict"] == "CALENDAR_DISJOINT"


def test_a_window_before_selection_is_checked_too():
    """Backwards is not automatically safe: the parent's labels run forward."""
    r = check_calendar_disjointness(_doc(
        **_CONFIRM,
        selection_period="2016-01-01 .. 2026-08-15",
        slice_period="1999-01-01 .. 2015-12-20"))
    assert r["verdict"] == "CONFIRMATION_WINDOW_ABUTS_SELECTION"
    assert r["direction"] == "precedes"
    r2 = check_calendar_disjointness(_doc(
        **_CONFIRM,
        selection_period="2016-01-01 .. 2026-08-15",
        slice_period="1999-01-01 .. 2015-10-01"))
    assert r2["verdict"] == "CALENDAR_DISJOINT"


# ── FOREIGN is labelled, not blocked ───────────────────────────────────────
def test_foreign_overlap_is_recorded_and_not_blocked():
    """N9's foreign slice was 2016+ and clean BY LUCK; the next one is asked."""
    r = check_calendar_disjointness(_doc(
        slice_purpose="FOREIGN", outcome_horizon_days=20,
        selection_period="1999-01-01 .. 2015-12-31",
        slice_period="1999-01-01 .. 2026-08-15"))
    assert r["verdict"] == "CALENDAR_OVERLAPPING_FOREIGN_SLICE"
    assert not r["blocked"]
    assert r["may_claim_transfer"] is False


def test_transfer_claims_are_blocked_like_confirm():
    r = check_calendar_disjointness(_doc(
        slice_purpose="TRANSFER", outcome_horizon_days=20,
        selection_period="1999-01-01 .. 2015-12-31",
        slice_period="2010-01-01 .. 2026-08-15"))
    assert r["verdict"] == "CALENDAR_OVERLAPPING_CONFIRMATION"
    assert r["blocked"]


# ── window parsing ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("1999-01-01 .. 2015-12-31", ("1999-01-01", "2015-12-31")),
    ("1999-01-01 to 2015-12-31", ("1999-01-01", "2015-12-31")),
    ("from 2015-12-31 back to 1999-01-01", ("1999-01-01", "2015-12-31")),
    ("1999-2015", ("1999-01-01", "2015-12-31")),
    ("2016", ("2016-01-01", "2016-12-31")),
    ("2016-03-01 .. 2026", ("2016-03-01", "2026-12-31")),
])
def test_windows_parse(raw, expected):
    assert parse_window(raw) == expected


def test_a_year_range_expands_to_its_widest_reading():
    """Ambiguous edges must FAIL disjointness, not scrape past it."""
    r = check_calendar_disjointness(_doc(
        **_CONFIRM, selection_period="1999-2015", slice_period="2015-2026"))
    assert r["verdict"] == "CALENDAR_OVERLAPPING_CONFIRMATION"


def test_unparseable_returns_none():
    assert parse_window("") is None
    assert parse_window("last winter") is None


# ── the gate, end to end ───────────────────────────────────────────────────
_POWER = dict(event_frequency_per_year=2.0, declared_effect_size="3.0pp",
              outcome_dispersion="4.936pp", outcome_horizon_days=20,
              corpus_years=20, dependence_unit="one 20-day calendar block")


def test_lint_refuses_an_overlapping_confirmation_end_to_end():
    doc = _doc(**_POWER, **{k: v for k, v in _CONFIRM.items()
                            if k != "outcome_horizon_days"},
               selection_period="1999-01-01 .. 2015-12-31",
               slice_period="1999-01-01 .. 2026-08-15")
    res = PL.lint(doc, corpus=[])
    assert res["verdict"] == "CALENDAR_OVERLAPPING_CONFIRMATION"
    assert res["calendar"]["blocked"]


def test_the_exit_code_is_the_guard():
    """A verdict the CLI prints and returns 0 on is a comment."""
    import scripts.lint_prereg as CLI
    for v in ("UNDECLARED_SELECTION_WINDOW", "CALENDAR_OVERLAPPING_CONFIRMATION",
              "CONFIRMATION_WINDOW_ABUTS_SELECTION", "UNPARSEABLE_WINDOW",
              "SELECTION_WINDOW_CONTRADICTS_PARENT"):
        assert v in CLI.REFUSALS


def test_the_gap_constant_matches_the_register():
    """Duplicated across two repos on purpose; pinned so it cannot drift."""
    try:
        import sys
        from pathlib import Path
        fin = Path(r"C:\Users\mrthn\aegis-finance")
        if not fin.exists():
            pytest.skip("aegis-finance not present next to this repo")
        sys.path.insert(0, str(fin))
        from backend.services.research_gym.slice_register import (
            required_gap_days as reg_gap)
    except Exception as exc:                                     # noqa: BLE001
        pytest.skip(f"slice_register not importable: {exc}")
    for h in (5, 20, 60, 126, 252):
        assert reg_gap(h) == required_gap_days(h)
