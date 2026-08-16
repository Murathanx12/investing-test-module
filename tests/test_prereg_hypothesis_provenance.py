"""R13f — a prior result that CAUSED the question is not the same as one quoted.

The case that produced this rule: IV-ORACLE-GAP-1 declares `parent_trial = NONE`
truthfully (every rung is literature-specified, WM0 fitted nothing here) and
`benchmark_source = WM0` (it divides by WM0's 0.17766 constant). Both correct.

And both together still miss that **WM0's 21.4% oracle-gap measurement is the
entire reason the question exists**, and WM0 read the panel end to end. A later
slice inside those dates is not pristine confirmation. R13e cannot see it —
nothing was selected — so it passes, which is exactly the shape of the N9 error
one level up: the coordinate that mattered was not the one being varied.

R13f does not refuse it. It names the claim level: ADAPTIVE_HISTORICAL_VALIDATION.
"""

from __future__ import annotations

import pytest

from aegis_brain.discipline.prereg_power import (ADAPTIVE_VALIDATION,
                                                 check_hypothesis_provenance)


def doc(**fields) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in fields.items())


# ── the motivating case ────────────────────────────────────────────────────
def test_the_iv_phase_b_design_is_adaptive_validation_not_confirmation():
    """Phase B, written as it would have been before this rule existed."""
    r = check_hypothesis_provenance(doc(
        slice_purpose="CONFIRM",
        slice_period="2020-06-01 .. 2026-07-17",
        selection_period="2006-01-03 .. 2019-12-31",
        parent_trial="IV-ORACLE-GAP-1",
        hypothesis_source="WM0",
        hypothesis_source_period="2006-01-03 .. 2026-07-17",
    ))
    assert r["verdict"] == ADAPTIVE_VALIDATION
    assert r["blocked"] is False, "it may run — nothing was fitted there"
    assert r["may_claim_independent_confirmation"] is False
    assert r["overlap"] == ("2020-06-01", "2026-07-17")


def test_the_downgrade_is_not_a_refusal():
    """The distinction the rule exists to make. A gate that refused here would
    be indistinguishable from R13e and would kill answerable questions."""
    r = check_hypothesis_provenance(doc(
        slice_purpose="CONFIRM", slice_period="2020-01-01 .. 2024-12-31",
        selection_period="NONE",
        hypothesis_source="WM0", hypothesis_source_period="2006-2026"))
    assert r["verdict"] == ADAPTIVE_VALIDATION
    assert r["blocked"] is False


# ── citation is not causation, in both directions ──────────────────────────
def test_a_benchmark_source_alone_does_not_downgrade_anything():
    """Quoting a constant spends no calendar. If it did, every trial that ever
    cited a prior measurement would be un-confirmable."""
    r = check_hypothesis_provenance(doc(
        slice_purpose="CONFIRM", slice_period="2020-01-01 .. 2024-12-31",
        selection_period="NONE", benchmark_source="WM0",
        hypothesis_source="NONE"))
    assert r["verdict"] == "NO_HYPOTHESIS_SOURCE_DECLARED"
    assert r["may_claim_independent_confirmation"] is True


def test_a_source_that_read_other_dates_leaves_confirmation_available():
    r = check_hypothesis_provenance(doc(
        slice_purpose="CONFIRM", slice_period="2020-01-01 .. 2024-12-31",
        selection_period="NONE",
        hypothesis_source="N9", hypothesis_source_period="1999-2015"))
    assert r["verdict"] == "HYPOTHESIS_SOURCE_DISJOINT"
    assert r["may_claim_independent_confirmation"] is True


# ── silence is not NONE ────────────────────────────────────────────────────
def test_an_undeclared_source_is_refused_not_assumed_absent():
    """Same reasoning as R13e's `parents=None` vs `()`: the design that will
    not say what made it exist is the one where it matters."""
    r = check_hypothesis_provenance(doc(
        slice_purpose="CONFIRM", slice_period="2020-01-01 .. 2024-12-31",
        selection_period="NONE"))
    assert r["verdict"] == "UNDECLARED_HYPOTHESIS_SOURCE"
    assert r["blocked"] is True
    assert r["may_claim_independent_confirmation"] is False


def test_a_named_source_with_no_window_is_refused():
    r = check_hypothesis_provenance(doc(
        slice_purpose="CONFIRM", slice_period="2020-01-01 .. 2024-12-31",
        selection_period="NONE", hypothesis_source="WM0"))
    assert r["verdict"] == "UNDECLARED_HYPOTHESIS_SOURCE_WINDOW"
    assert r["blocked"] is True


def test_an_explicit_none_is_a_real_answer_and_passes():
    r = check_hypothesis_provenance(doc(
        slice_purpose="CONFIRM", slice_period="2020-01-01 .. 2024-12-31",
        selection_period="NONE", hypothesis_source="NONE"))
    assert r["blocked"] is False
    assert r["verdict"] == "NO_HYPOTHESIS_SOURCE_DECLARED"


# ── scope ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("purpose", ["EXPLORE", "FOREIGN", "REANALYSIS"])
def test_only_transfer_claiming_purposes_are_asked(purpose):
    """An EXPLORE claims no independence, so it has none to qualify. Asking it
    would make the gate noise, and a noisy gate gets bypassed."""
    r = check_hypothesis_provenance(doc(
        slice_purpose=purpose, slice_period="2020-01-01 .. 2024-12-31"))
    assert r["verdict"] == "NOT_APPLICABLE"
    assert r["blocked"] is False


def test_an_unparseable_source_window_is_refused_not_guessed():
    r = check_hypothesis_provenance(doc(
        slice_purpose="CONFIRM", slice_period="2020-01-01 .. 2024-12-31",
        selection_period="NONE",
        hypothesis_source="WM0", hypothesis_source_period="sometime recently"))
    assert r["verdict"] == "UNPARSEABLE_WINDOW"
    assert r["blocked"] is True


def test_a_one_day_touch_still_downgrades():
    """Overlap is overlap. A rule with a tolerance here would need a reason for
    the tolerance, and there is none — the source either saw those outcomes or
    it did not."""
    r = check_hypothesis_provenance(doc(
        slice_purpose="CONFIRM", slice_period="2020-01-01 .. 2024-12-31",
        selection_period="NONE",
        hypothesis_source="WM0",
        hypothesis_source_period="2015-01-01 .. 2020-01-01"))
    assert r["verdict"] == ADAPTIVE_VALIDATION
    assert r["overlap"] == ("2020-01-01", "2020-01-01")


# ── wired into the lint, not just importable ───────────────────────────────
def test_the_lint_carries_r13f_and_blocks_on_it():
    from aegis_brain.discipline.prereg_lint import lint
    body = doc(
        slice_purpose="CONFIRM", slice_period="2020-06-01 .. 2026-07-17",
        slice_securities="SPY QQQ IWM XLF XLE XLK",
        information_cutoff="close of the decision date",
        selection_period="2006-01-03 .. 2019-12-31",
        parent_trial="IV-ORACLE-GAP-1",
        outcome_horizon_days=20,
        event_frequency_per_year=6.37, declared_effect_size="5.35pp",
        outcome_dispersion="4.105pp", corpus_years=6.1,
        cross_sectional_n=1, dependence_unit="40-trading-day block")
    res = lint("A confirmation of the IV oracle gap.\n" + body, corpus=[])
    assert res["verdict"] == "UNDECLARED_HYPOTHESIS_SOURCE"
    assert res["provenance"]["blocked"] is True

    res2 = lint("A confirmation of the IV oracle gap.\n" + body
                + "\n- hypothesis_source: WM0"
                + "\n- hypothesis_source_period: 2006-01-03 .. 2026-07-17")
    assert res2["provenance"]["verdict"] == ADAPTIVE_VALIDATION
    assert res2["provenance"]["blocked"] is False
    assert res2["verdict"] != ADAPTIVE_VALIDATION, (
        "the downgrade must not masquerade as the document's overall verdict — "
        "it is a claim-level annotation, not a refusal")
