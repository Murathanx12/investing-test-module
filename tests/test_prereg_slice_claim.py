"""The slice claim, checked at registration instead of at the register.

`research_gym.slice_register` can only refuse a trial that calls it, and the
trial that will not call it is the one that needs refusing. N9B was designed
after information from N9's confirmation slice had already entered the research
process, consumed it a second time, and nothing objected — because nothing was
asked. These tests pin that the asking now happens where it cannot be skipped.
"""

from __future__ import annotations

import pytest

from aegis_brain.discipline import prereg_lint as PL
from aegis_brain.discipline.prereg_power import (SLICE_PURPOSES,
                                                 check_slice_declaration)


def _doc(**kw) -> str:
    body = "\n".join(f"{k} = {v}" for k, v in kw.items())
    return f"# PREREG — synthetic\n\n```\n{body}\n```\n"


_POWER = dict(event_frequency_per_year=2.0, declared_effect_size="3.0pp",
              outcome_dispersion="4.936pp", outcome_horizon_days=126,
              corpus_years=20, dependence_unit="one 6-month calendar block")


def test_silence_is_refused():
    r = check_slice_declaration("# PREREG\n\nnothing declared here\n")
    assert r["verdict"] == "UNDECLARED_SLICE_PURPOSE"
    assert r["blocked"]


def test_explore_is_a_perfectly_good_answer():
    r = check_slice_declaration(_doc(slice_purpose="EXPLORE"))
    assert not r["blocked"]
    assert r["slice_purpose"] == "EXPLORE"
    # ... and it costs the confirmation claim, which is the point of saying it.
    assert "may NOT later be described as an independent confirmation" in r["why"]


def test_a_confirm_must_identify_the_data_it_claims():
    r = check_slice_declaration(_doc(slice_purpose="CONFIRM"))
    assert r["verdict"] == "UNIDENTIFIED_CONFIRMATION_SLICE"
    assert set(r["missing"]) == {"slice_securities", "slice_period",
                                 "information_cutoff"}


def test_the_information_cutoff_is_required_separately_from_the_period():
    """Two trials can share a price window and differ in what they knew."""
    r = check_slice_declaration(_doc(
        slice_purpose="CONFIRM", slice_securities="XRT XHB KRE",
        slice_period="2006-07-01 .. 2026-08-15"))
    assert r["blocked"]
    assert r["missing"] == ["information_cutoff"]


def test_a_complete_confirm_declaration_passes():
    r = check_slice_declaration(_doc(
        slice_purpose="CONFIRM", slice_securities="XRT XHB KRE XOP",
        slice_period="2006-07-01 .. 2026-08-15",
        information_cutoff="2026-08-15"))
    assert not r["blocked"]
    assert r["slice_purpose"] == "CONFIRM"


def test_placeholders_do_not_satisfy_the_field():
    for junk in ("n/a", "TBD", "-", "?", "<one of EXPLORE / CONFIRM>"):
        r = check_slice_declaration(_doc(slice_purpose=junk))
        assert r["verdict"] == "UNDECLARED_SLICE_PURPOSE", junk


def test_an_unknown_purpose_is_refused():
    r = check_slice_declaration(_doc(slice_purpose="PROBABLY_FINE"))
    assert r["verdict"] == "UNDECLARED_SLICE_PURPOSE"


def test_the_gate_is_ON_by_default_in_lint():
    """The property that matters: a real caller cannot skip it by omission."""
    res = PL.lint(_doc(**_POWER), corpus=[])
    assert res["verdict"] == "UNDECLARED_SLICE_PURPOSE"
    assert res["slice"]["blocked"]

    ok = PL.lint(_doc(**_POWER, slice_purpose="EXPLORE"), corpus=[])
    assert ok["verdict"] == "PASS"
    assert ok["slice"]["slice_purpose"] == "EXPLORE"


def test_the_power_gate_still_runs_first():
    """An unresolvable design is not improved by declaring its slice."""
    res = PL.lint(_doc(slice_purpose="EXPLORE"), corpus=[])
    assert res["verdict"] == "MISSING_POWER_FIELDS"


def test_the_linter_treats_both_verdicts_as_refusals():
    import scripts.lint_prereg as L

    assert "UNDECLARED_SLICE_PURPOSE" in L.REFUSALS
    assert "UNIDENTIFIED_CONFIRMATION_SLICE" in L.REFUSALS


def test_slice_purposes_match_the_register():
    """The vocabulary is duplicated across two repos; pin them together.

    `aegis-finance`'s `research_gym.slice_register` owns PURPOSES and this
    linter lives in `Aegis module`. A vocabulary that drifts would let a trial
    declare a purpose at registration that the register then rejects, or worse
    accept one the register has never heard of.
    """
    try:
        import sys
        from pathlib import Path
        fin = Path(r"C:\Users\mrthn\aegis-finance")
        if not fin.exists():
            pytest.skip("aegis-finance not present next to this repo")
        sys.path.insert(0, str(fin))
        from backend.services.research_gym.slice_register import PURPOSES
    except Exception as exc:                                     # noqa: BLE001
        pytest.skip(f"slice_register not importable: {exc}")
    # Every purpose the register knows must be declarable at registration.
    assert set(PURPOSES) <= set(SLICE_PURPOSES)
