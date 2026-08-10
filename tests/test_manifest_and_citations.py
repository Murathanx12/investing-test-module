"""The NIGHT manifest and the citation ledger, as tests rather than intentions.

Both exist because of failures external review found in this repository: run
receipts that live only on one laptop, and correctly-transcribed numbers whose
qualifiers had been dropped. A guard without a callable entry point and a test is
a comment (CANON).
"""
from __future__ import annotations

import json

import pytest

from aegis_brain.config import MODULE_ROOT
from aegis_brain.discipline.citations import (Citation, CitationError,
                                              check_use, load)
from aegis_brain.discipline.manifest import (build, calibrate, claim_coverage,
                                             walk_scalars)


# ── the citation ledger ─────────────────────────────────────────────────────
def test_shipped_ledger_loads():
    led = load()
    assert len(led) >= 15
    assert "LAZY-PRICES-188BPS" in led


def _kw(**over) -> dict:
    base = dict(id="X", claim="c", source="s", verdict="V",
                qualifier="a qualifier long enough to say something real",
                transfers_to_aegis=True, how="it transfers because ...")
    base.update(over)
    return base


def test_a_stub_qualifier_is_refused():
    with pytest.raises(CitationError, match="qualifier"):
        Citation(**_kw(qualifier="see paper"))


def test_transferring_citation_must_say_how():
    with pytest.raises(CitationError, match="how"):
        Citation(**_kw(how=""))


def test_blocked_citation_must_say_why_not():
    with pytest.raises(CitationError, match="why_not"):
        Citation(**_kw(transfers_to_aegis=False, how=None))


def test_unknown_verdict_refused():
    with pytest.raises(CitationError, match="verdict"):
        Citation(**_kw(verdict="PROBABLY"))


def test_invented_numbers_cannot_be_quoted():
    """The review bps tables are in the ledger precisely so they fail here."""
    with pytest.raises(CitationError, match="may not be quoted"):
        check_use("REVIEW-BPS-TABLES")


def test_non_transferring_citation_cannot_become_an_expectation():
    # a long-short spread is real and may not be an expectation for a long-only
    # book; likewise a rebalancing premium measured against buy-and-hold
    for cid in ("LAZY-PRICES-188BPS", "MAESO-MARTELLINI-REBAL", "3S-TRADER-131"):
        with pytest.raises(CitationError, match="does not transfer"):
            check_use(cid)


def test_a_transferring_citation_returns():
    c = check_use("HARVEY-LIU-ZHU-T3")
    assert c.value == 3.0 and c.transfers_to_aegis


def test_missing_citation_is_an_error_not_a_shrug():
    with pytest.raises(CitationError, match="not in the ledger"):
        check_use("SOMETHING-I-REMEMBER-READING")


def test_dsr_entry_records_the_night7_wording_error():
    """The correction has to live somewhere a future session will read."""
    c = load()["DSR-BAILEY-LOPEZ-DE-PRADO"]
    assert "not" in c.qualifier.lower() and "posterior" in c.qualifier.lower()


# ── the manifest ────────────────────────────────────────────────────────────
def test_walk_scalars_skips_bools():
    got = dict(walk_scalars({"a": 1.5, "flag": True, "n": {"b": 2}}))
    assert got == {"a": 1.5, "n.b": 2.0}


def test_build_refuses_a_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        build(tmp_path / "nope", tmp_path, "NIGHTX")


def test_build_refuses_an_empty_directory(tmp_path):
    """An empty manifest would read as a verified night with nothing in it."""
    (tmp_path / "runs").mkdir()
    with pytest.raises(RuntimeError, match="empty"):
        build(tmp_path / "runs", tmp_path, "NIGHTX")


def test_manifest_hashes_and_embeds(tmp_path):
    d = tmp_path / "runs"
    d.mkdir()
    (d / "a.json").write_text(json.dumps({"cagr": 0.1345}), encoding="utf-8")
    (d / "b.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    man = build(d, tmp_path, "NIGHTX")
    by = {a["name"]: a for a in man["artifacts"]}
    assert by["a.json"]["embedded"] and not by["b.csv"]["embedded"]
    assert len(by["a.json"]["sha256"]) == 64
    assert man["receipts"]["a.json"]["cagr"] == 0.1345


def test_claim_check_finds_a_real_number_and_flags_an_invented_one():
    scalars = {"r.cagr": 0.1345, "r.cost": 743599.0}
    doc = "The book returned 13.45%/yr and the stop cost $743,599, not $935k."
    cc = claim_coverage(doc, scalars, collision_draws=20)
    unbacked = {u["raw"] for u in cc["unbacked"]}
    assert "$935k" in unbacked
    backed = {b["raw"] for b in cc["backed"]} | {
        u["raw"] for u in cc["uninformative"]}
    assert "13.45%" in backed and "$743,599" in backed


def test_identifiers_are_not_read_as_claims():
    """NIGHT-7 scanned naively yields a claim of '-7' and buries the real list."""
    doc = "NIGHT-7 §15 T2c arm A3 on 2026-08-10 (2018) [3] PF-7B"
    cc = claim_coverage(doc, {"x": 1.0}, collision_draws=5)
    assert cc["claims_found"] == 0


def test_magnitude_suffixes_are_part_of_the_number():
    """'$91.2m' must reach 91,236,586 — and '482 months' must not."""
    cc = claim_coverage("traded $91.2m over 482 months",
                        {"r.turnover": 91_236_586.0, "r.months": 482.0},
                        collision_draws=5)
    assert cc["unbacked"] == []


def test_calibration_reports_a_false_positive_rate():
    """A gate that has not been measured against a known answer is a decoration.

    The first version of this checker used a relative tolerance and 'backed'
    86.6% of fabricated numbers. This test is what stops that shipping again.
    """
    scalars = dict(build(MODULE_ROOT / "runs" / "NIGHT7", MODULE_ROOT,
                         "NIGHT7")["receipts"].items())
    flat = {f"{n}:{p}": v for n, b in scalars.items()
            for p, v in walk_scalars(b)}
    cal = calibrate(flat, None, n=120)
    assert cal["fabricated_numbers_tested"] > 50
    assert cal["false_positive_rate"] < 0.15, cal
