"""Each test here is one error this programme actually made in a write-up."""
from __future__ import annotations

from aegis_brain.discipline.referee import review


def test_night4_error_a_null_that_prints_reject():
    r = review("The arm is UNRESOLVED, so the idea is dead and we reject it. "
               "MDE 3.4%/yr.")
    assert any(f["check"] == "verdict-language" for f in r["blockers"])


def test_a_null_must_carry_its_mde():
    r = review("Arm A is UNRESOLVED at +0.4%/yr.")
    assert any(f["check"] == "mde-missing" for f in r["blockers"])


def test_a_null_with_an_mde_nearby_passes_that_check():
    r = review("Arm A is UNRESOLVED at +0.4%/yr.\nMDE 2.9%/yr, NW t 0.31.")
    assert not any(f["check"] == "mde-missing" for f in r["findings"])


def test_a_non_transferring_citation_is_blocked():
    """A long-short spread quoted as an expectation for a long-only book."""
    r = review("We expect 188 bps/month, per `LAZY-PRICES-188BPS`. MDE n/a.")
    assert any(f["check"] == "citation-does-not-transfer" for f in r["blockers"])


def test_a_transferring_citation_is_not_blocked():
    r = review("The bar is t > 3.0 (`HARVEY-LIU-ZHU-T3`).")
    assert not any(f["check"] == "citation-does-not-transfer"
                   for f in r["findings"])


def test_night7b_error_a_dollar_cost_comparison_with_no_denominator():
    r = review("The ensemble is cheaper: it pays $313,775 against $333,165.")
    assert any(f["check"] == "cost-denominator" for f in r["blockers"])


def test_the_same_claim_with_a_normalised_figure_passes():
    r = review("The ensemble is cheaper: $313,775 against $333,165 — and "
               "0.2216% vs 0.2232% of cost drag per year on average NAV.")
    assert not any(f["check"] == "cost-denominator" for f in r["findings"])


def test_branches_must_move_the_denominator():
    r = review("We ran three arms.", expected_new_branches=3,
               denominator_before=827)
    assert any(f["check"] == "branch-accounting" for f in r["blockers"])
    r2 = review("We ran three arms; the denominator moves to 830.",
                expected_new_branches=3, denominator_before=827)
    assert not any(f["check"] == "branch-accounting" for f in r2["findings"])


def test_unbacked_numbers_are_questions_not_blockers():
    """Derived and literature numbers land here; they are a reading list."""
    r = review("The book returned 13.45%/yr and something cost $935k.",
               scalars={"r.cagr": 0.1345}, collision_draws=10)
    unb = [f for f in r["findings"] if f["check"] == "unbacked-number"]
    assert unb and all(f["severity"] == "question" for f in unb)


def test_a_clean_document_is_clean():
    r = review("Arm A is UNRESOLVED at +0.4%/yr; MDE 2.9%/yr. The bar is "
               "t > 3.0 (`HARVEY-LIU-ZHU-T3`). Denominator moves to 830.",
               expected_new_branches=3, denominator_before=827)
    assert r["clean"], r["blockers"]


def test_the_referee_states_what_it_cannot_check():
    r = review("nothing to see")
    assert any("HONEST" in s for s in r["not_checked"])


# ── the MDE units guard (NIGHT-8) ───────────────────────────────────────────
def test_mde_annualized_refuses_a_pre_annualised_series():
    """NIGHT-7's trigger receipts reported MDEs of 43% to 143% per year.

    `mde_annualized` multiplies by 12 itself. Handing it a series already
    multiplied by 12 inflates the answer twelvefold — absurd in hindsight and
    invisible inside a JSON blob at the time. It now refuses.
    """
    import numpy as np
    import pandas as pd
    import pytest

    from aegis_brain.pf.decomp import mde_annualized

    rng = np.random.default_rng(0)
    monthly = pd.Series(rng.normal(0.0, 0.02, 400))
    assert 0.0 < mde_annualized(monthly) < 0.1
    with pytest.raises(ValueError, match="units error"):
        mde_annualized(monthly * 12)
