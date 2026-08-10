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
    monthly = pd.Series(rng.normal(0.0, 0.06, 250))   # the book's own vol
    assert 0.0 < mde_annualized(monthly) < 0.15
    with pytest.raises(ValueError, match="units error"):
        mde_annualized(monthly * 12)


def test_the_mde_guard_is_a_backstop_and_says_so():
    """A twelvefold inflation of a SMALL mde still slips through. Documented."""
    import numpy as np
    import pandas as pd

    from aegis_brain.pf.decomp import _ABSURD_MDE, mde_annualized

    rng = np.random.default_rng(1)
    tiny = pd.Series(rng.normal(0.0, 0.002, 400))
    assert mde_annualized(tiny * 12) < _ABSURD_MDE     # no raise: it passes


# ── context handling (found by running the referee on its own night) ────────
def test_an_mde_in_a_table_header_counts_for_every_row():
    """A fixed three-line window never reaches a long table's column header.

    Nine of the first eleven findings this module produced on NIGHT-8's own
    write-up were that false positive.
    """
    doc = ("| arm | effect | MDE at t 2 | verdict |\n"
           "|---|---|---|---|\n"
           "| V1 | +0.62%/yr | 0.65%/yr | UNRESOLVED |\n"
           "| V2 | +0.37%/yr | 0.42%/yr | UNRESOLVED |\n"
           "| V3 | +0.02%/yr | 0.24%/yr | UNRESOLVED |\n"
           "| V4 | +0.85%/yr | 0.78%/yr | UNRESOLVED |\n"
           "| V5 | +0.00%/yr | 0.92%/yr | UNRESOLVED |\n")
    r = review(doc)
    assert not any(f["check"] == "mde-missing" for f in r["findings"]), r["blockers"]


def test_a_table_without_an_mde_column_still_fails():
    doc = ("| arm | effect | verdict |\n|---|---|---|\n"
           "| V1 | +0.62%/yr | UNRESOLVED |\n")
    r = review(doc)
    assert any(f["check"] == "mde-missing" for f in r["blockers"])


def test_a_quoted_claim_is_reported_not_asserted():
    """Otherwise the module blocks any document that quotes what it criticises."""
    r = review('NIGHT-7B said "The ensemble is CHEAPER by $19,390" and that '
               "claim is what this section retracts.")
    assert not any(f["check"] == "cost-denominator" for f in r["findings"])
