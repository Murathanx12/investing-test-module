"""The corpse check must fail loudly, and must not fail on everything.

A linter that blocks every proposal gets switched off in a week, and a linter
that clears every proposal was never doing anything. Both directions are tested.
"""
from __future__ import annotations

from collections import Counter

import pytest

from aegis_brain.discipline import prereg_lint as _pl
from aegis_brain.discipline.prereg_lint import Corpse, load_corpus, _tokens


def lint(proposal, **kw):
    """The WORDING check alone — the other two gates are off in this file.

    `prereg_lint.lint` runs three checks and defaults R13 and the slice claim
    ON, which is right for every real caller. These tests are about the corpse
    check specifically, and leaving the others armed here would make all of
    them fail on missing declarations rather than on the thing under test. Each
    has its own file (`test_prereg_power.py`, `test_prereg_slice_claim.py`) and
    the defaults are asserted there — which is the part that matters, since a
    gate that is only ever exercised with itself disabled is not a gate.
    """
    kw.setdefault("require_power", False)
    kw.setdefault("require_slice", False)
    return _pl.lint(proposal, **kw)


def corpse(ident, verdict, text, source="graveyard") -> Corpse:
    c = Corpse(ident=ident, source=source, verdict=verdict, text=text,
               detail={"why": "receipt"})
    c.tokens = Counter(_tokens(text))
    return c


REFUTED = corpse(
    "vol_managed_momentum/small", "REJECTED",
    "volatility managed momentum scaling exposure by inverse realised "
    "variance in the small capitalisation segment, adequately powered and "
    "refuted at the three percent bar")
UNDERPOWERED = corpse(
    "accruals_low/small", "POWER_FAILED",
    "low accruals ranking in the small capitalisation segment, minimum "
    "detectable effect exceeded the bar so the null says nothing")
UNRELATED = corpse(
    "gdelt_conflict/large", "CONFIRMED",
    "geopolitical conflict event counts from gdelt against large "
    "capitalisation industrial exporters")
CORPUS = [REFUTED, UNDERPOWERED, UNRELATED]


def test_a_refuted_idea_is_blocked_with_its_receipt():
    res = lint("We propose volatility managed momentum, scaling exposure by "
               "inverse realised variance, in the small capitalisation "
               "segment.", corpus=CORPUS)
    assert res["verdict"] == "BLOCKED"
    assert res["blocking"][0]["id"] == "vol_managed_momentum/small"
    assert res["blocking"][0]["detail"]["why"] == "receipt"


def test_an_underpowered_idea_is_a_resurrection_not_a_block():
    """31 POWER + 29 IMPL + 14 DATA rows never answered their question."""
    # min_shared is calibrated for full-length preregs; these fixtures are two
    # sentences, so the production floor of 8 informative shared terms would
    # drop every match below it and report a vacuous PASS.
    res = lint("A book ranked on low accruals, held across the small "
               "capitalisation universe on an annual clock.", corpus=CORPUS,
               min_shared=3)
    assert res["verdict"] == "RESURRECTION"
    assert res["resurrections"][0]["class"] == "unanswered"


def test_declaring_a_new_instrument_clears_the_resurrection():
    res = lint(
        "We propose ranking on low accruals within the small capitalisation "
        "segment, minimum detectable effect permitting.\n"
        "Resurrects: accruals_low/small — new instrument: the CRSP 1962-2001 "
        "era spine triples the sample and takes the MDE below the bar\n",
        corpus=CORPUS)
    assert res["verdict"] == "PASS"
    assert res["matches"][0]["declared_new_instrument"].startswith("the CRSP")


def test_a_hyphenated_ident_can_be_declared():
    """Nearly every registry ident contains hyphens (TRIAL-COND-VT). The
    original corpse-group regex stopped at the first hyphen, so declaring one
    parsed as corpse="TRIAL" and the block silently survived (NIGHT-13)."""
    hyphenated = corpse(
        "TRIAL-COND-VT", "REJECTED",
        "volatility managed momentum scaling exposure by inverse realised "
        "variance in the small capitalisation segment, adequately powered and "
        "refuted at the three percent bar")
    res = lint(
        "We propose volatility managed momentum, scaling exposure by inverse "
        "realised variance, in the small capitalisation segment.\n"
        "Resurrects: TRIAL-COND-VT — new instrument: keyed to the book's own "
        "path on a daily clock rather than the index on a month-end clock\n",
        corpus=[hyphenated, UNDERPOWERED, UNRELATED])
    assert res["verdict"] == "PASS"
    assert res["matches"][0]["declared_new_instrument"].startswith("keyed to")


def test_trying_again_is_not_a_new_instrument():
    """The escape hatch requires naming the instrument, not asserting merit."""
    res = lint("volatility managed momentum scaling exposure by inverse "
               "realised variance small capitalisation segment\n"
               "Resurrects: vol_managed_momentum/small\n", corpus=CORPUS)
    assert res["verdict"] == "BLOCKED"


def test_an_unrelated_idea_passes():
    res = lint("We propose a supplier concentration measure built from "
               "segment disclosures in annual filings.", corpus=CORPUS)
    assert res["verdict"] == "PASS"
    assert res["blocking"] == [] and res["resurrections"] == []


def test_near_identical_wording_is_a_duplicate_whatever_the_label_says():
    """The registry has no verdict field; an already-run trial reads REGISTERED."""
    res = lint(UNRELATED.text, corpus=CORPUS)
    assert res["verdict"] == "DUPLICATE"


def test_empty_proposal_raises_rather_than_passing():
    with pytest.raises(ValueError):
        lint("   ", corpus=CORPUS)


def test_pass_language_does_not_claim_novelty():
    res = lint("supplier concentration segment disclosures", corpus=CORPUS)
    assert "not novel" in res["why"] and "literature" in res["why"]


# ── the real corpus ─────────────────────────────────────────────────────────
def test_the_shipped_corpus_is_not_empty():
    corp = load_corpus()
    assert len(corp) > 200
    assert {c.source for c in corp} == {"graveyard", "registry", "prereg"}


def test_the_real_corpus_has_verdicts_beyond_registered():
    """If every row reads REGISTERED the linter can never block anything."""
    corp = load_corpus()
    classes = Counter(c.clazz for c in corp)
    assert classes["closed"] + classes["unanswered"] > 100, classes


def test_the_blank_template_is_not_blocked():
    """A linter that blocks its own empty template blocks everything.

    TEMPLATE.md scored 0.322 against a REJECTED trial on 56 shared boilerplate
    terms until document frequency was measured within each source rather than
    across the pool. This is the regression test for that.
    """
    from pathlib import Path

    from aegis_brain.config import MODULE_ROOT
    p = MODULE_ROOT / "TRIALS" / "TEMPLATE.md"
    res = lint(p.read_text(encoding="utf-8"),
               corpus=load_corpus(exclude=p))
    assert res["verdict"] == "PASS", res["matches"][:2]


def test_a_genuinely_new_mechanism_is_not_blocked_by_the_real_corpus():
    """False-positive check against all 295 recorded experiments."""
    novel = ("We propose measuring the dispersion of delivery lead times "
             "disclosed in freight-forwarder tariff filings, aggregated to the "
             "shipper, as a proxy for inventory pipeline stress. The mechanism "
             "is that carriers reprice capacity before shippers disclose "
             "margin pressure, so the tariff record leads the income "
             "statement. No price, return, accounting ratio or filing-text "
             "feature enters the construction.")
    res = lint(novel, corpus=load_corpus())
    assert res["verdict"] == "PASS", res["matches"][:2]


def test_a_known_corpse_is_still_caught_by_the_real_corpus():
    """False-negative check: loosening the linter must not blind it."""
    corp = load_corpus()
    dead = next(c for c in corp
                if c.clazz in ("closed", "unanswered") and len(c.tokens) > 25)
    res = lint(dead.text, corpus=[c for c in corp if c is not dead])
    assert res["verdict"] in ("BLOCKED", "DUPLICATE", "RESURRECTION"), (
        dead.ident, res["verdict"], res["matches"][:2])


def test_a_decision_rule_table_is_not_a_verdict():
    """An unrun prereg lists REJECTED as a possible future, not as its result.

    Reading the first verdict token anywhere labelled every unrun prereg
    REJECTED, and the linter then BLOCKED new work against trials that had not
    happened. Caught when the IMAGE-RANK backlog item was blocked against N1's
    own preregistration.
    """
    from aegis_brain.discipline.prereg_lint import _verdict_in
    prereg = ("## 7. Decision rule (frozen)\n\n"
              "| outcome | state |\n|---|---|\n"
              "| effect >= +3%/yr | `CONFIRMED` |\n"
              "| effect <= -3%/yr | `REJECTED` |\n")
    assert _verdict_in(prereg, attributed_only=True) == "REGISTERED"


def test_a_recorded_result_still_reads_as_a_verdict():
    from aegis_brain.discipline.prereg_lint import _verdict_in
    ran = ("## Result (filled AFTER the run — never edited afterwards)\n"
           "Arm B net excess = -56 bps/mo, t = -2.80.\n\n"
           "### Verdict: **REJECT** (kill condition 2 triggered).\n")
    assert _verdict_in(ran, attributed_only=True) == "REJECTED"
