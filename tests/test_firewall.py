"""The firewall must fail loudly. These tests are the firewall.

Standing rule (CANON): a guard without a callable entry point and a test is a
comment. Each test below is one way the boundary could be crossed by accident.
"""
from __future__ import annotations

import pytest

from aegis_brain.firewall import (
    CHANNELS,
    LLM_CHANNELS,
    Adjudication,
    Extraction,
    ExtractionRequest,
    FirewallViolation,
    LearningSample,
    ProvenanceStamp,
    VetoProposal,
)


def stamp(as_of="2015-03-01T00:00:00Z") -> ProvenanceStamp:
    return ProvenanceStamp(as_of_ts=as_of, source_doc_id="0000320193-15-000356",
                           source_type="10-K", model_ver="test-model-1",
                           prompt_hash="abc123", extractor_ver="0.1.0")


# ── Layer 1 inputs ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("key", [
    "fwd_return_1m", "realized_vol", "price_close", "sharpe", "y_true",
    "future_drawdown", "pnl_usd", "excess_cagr", "winner_flag",
])
def test_request_rejects_outcome_shaped_context(key):
    with pytest.raises(FirewallViolation):
        ExtractionRequest(request_id="r1", masked_text="Company A said...",
                          schema_name="risk_v1", context={key: 0.1})


def test_request_accepts_clean_context():
    r = ExtractionRequest(request_id="r1", masked_text="Company A said...",
                          schema_name="risk_v1",
                          context={"fiscal_year": 2015, "sic": "3571"})
    assert r.schema_name == "risk_v1"


def test_entity_masking_alone_is_not_alpha_certifiable():
    """The NIGHT-7 correction: masking the name does not mask the date."""
    r = ExtractionRequest(request_id="r1", masked_text="t", schema_name="s",
                          leak_controls=("entity",))
    assert r.alpha_certifiable is False
    r2 = ExtractionRequest(request_id="r2", masked_text="t", schema_name="s",
                           leak_controls=("entity", "date"))
    assert r2.alpha_certifiable is True


def test_unknown_leak_control_rejected():
    with pytest.raises(ValueError):
        ExtractionRequest(request_id="r", masked_text="t", schema_name="s",
                          leak_controls=("vibes",))


# ── Layer 1 outputs ─────────────────────────────────────────────────────────
def test_extraction_requires_provenance():
    with pytest.raises(FirewallViolation):
        Extraction(request_id="r", schema_name="s", fields={"a": 1},
                   confidence={"a": 0.9}, provenance=None)  # type: ignore[arg-type]


def test_provenance_rejects_blank_field():
    with pytest.raises(FirewallViolation):
        ProvenanceStamp(as_of_ts="2015-01-01", source_doc_id="",
                        source_type="10-K", model_ver="m", prompt_hash="h",
                        extractor_ver="v")


def test_extraction_rejects_outcome_shaped_field():
    with pytest.raises(FirewallViolation):
        Extraction(request_id="r", schema_name="s",
                   fields={"forward_return": 0.02},
                   confidence={"forward_return": 0.8}, provenance=stamp())


def test_every_field_needs_a_confidence():
    with pytest.raises(ValueError):
        Extraction(request_id="r", schema_name="s",
                   fields={"risk_tone": -1.0, "customer_concentration": True},
                   confidence={"risk_tone": 0.7}, provenance=stamp())


def test_confidence_must_be_a_probability():
    with pytest.raises(ValueError):
        Extraction(request_id="r", schema_name="s", fields={"a": 1},
                   confidence={"a": 1.4}, provenance=stamp())


def test_clean_extraction_round_trips():
    e = Extraction(request_id="r", schema_name="risk_v1",
                   fields={"political_risk_score": 0.42, "litigation_flag": True},
                   confidence={"political_risk_score": 0.6,
                               "litigation_flag": 0.9},
                   provenance=stamp())
    d = e.as_dict()
    assert d["provenance"]["source_type"] == "10-K"
    assert d["fields"]["litigation_flag"] is True


# ── the boundary itself ─────────────────────────────────────────────────────
def _clean_extraction() -> Extraction:
    return Extraction(request_id="r", schema_name="s", fields={"tone": 0.1},
                      confidence={"tone": 0.8}, provenance=stamp())


def test_learning_sample_rejects_lookahead_outcome():
    with pytest.raises(FirewallViolation):
        LearningSample(extraction=_clean_extraction(), outcome=0.05,
                       outcome_as_of_ts="2014-01-01T00:00:00Z")


def test_learning_sample_accepts_later_outcome():
    s = LearningSample(extraction=_clean_extraction(), outcome=0.05,
                       outcome_as_of_ts="2016-03-01T00:00:00Z")
    assert s.outcome == 0.05


def test_outcomes_cannot_flow_back_to_layer_1():
    s = LearningSample(extraction=_clean_extraction(), outcome=0.05,
                       outcome_as_of_ts="2016-03-01T00:00:00Z")
    with pytest.raises(FirewallViolation):
        s.to_layer1_payload()


# ── Layer 3 ─────────────────────────────────────────────────────────────────
def test_adjudicator_cannot_set_weights():
    a = Adjudication(subject_id="x", verdict="FLAG", probability=0.3,
                     rationale="thin disclosure", provenance=stamp())
    with pytest.raises(FirewallViolation):
        a.set_weight("feature", 1.0)


def test_veto_needs_a_rationale():
    with pytest.raises(ValueError):
        Adjudication(subject_id="x", verdict="VETO", probability=0.9,
                     rationale="   ", provenance=stamp())


def test_bad_verdict_rejected():
    with pytest.raises(ValueError):
        Adjudication(subject_id="x", verdict="SELL", probability=0.5,
                     rationale="r", provenance=stamp())


def test_adjudication_probability_is_brier_scoreable():
    a = Adjudication(subject_id="x", verdict="VETO", probability=0.75,
                     rationale="customer concentration disclosure deleted",
                     provenance=stamp())
    brier = (a.probability - 1.0) ** 2      # resolved TRUE
    assert 0.0 <= brier <= 1.0


# ── the veto channel (external review 2026-08-10) ───────────────────────────
# A veto moves the book even though it never calls set_weight(). These tests
# close that loophole.
def _veto() -> VetoProposal:
    return VetoProposal(
        subject_id="x", reason_code="customer_concentration_removed",
        probability=0.7, resolves_at="2016-06-30T00:00:00Z",
        rationale="the customer-concentration paragraph was deleted",
        provenance=stamp())


def test_veto_proposal_cannot_be_applied_to_the_book():
    with pytest.raises(FirewallViolation):
        _veto().apply_to_book({"x": 0.0})


def test_veto_reason_code_must_be_in_the_frozen_vocabulary():
    with pytest.raises(ValueError):
        VetoProposal(subject_id="x", reason_code="i_dont_like_it",
                     probability=0.7, resolves_at="2016-06-30T00:00:00Z",
                     rationale="vibes", provenance=stamp())


def test_veto_proposal_cannot_claim_another_channel():
    with pytest.raises(FirewallViolation):
        VetoProposal(subject_id="x", reason_code="auditor_change",
                     probability=0.5, resolves_at="2016-06-30T00:00:00Z",
                     rationale="r", provenance=stamp(),
                     channel="portfolio_action")


def test_veto_is_brier_scoreable_both_ways():
    v = _veto()
    assert v.brier(True) == pytest.approx((0.7 - 1.0) ** 2)
    assert v.brier(False) == pytest.approx(0.7 ** 2)


def test_only_a_veto_verdict_becomes_a_proposal():
    a = Adjudication(subject_id="x", verdict="FLAG", probability=0.3,
                     rationale="thin", provenance=stamp())
    with pytest.raises(ValueError):
        a.to_veto_proposal("auditor_change", "2016-06-30T00:00:00Z")


def test_veto_verdict_converts_and_stays_unappliable():
    a = Adjudication(subject_id="x", verdict="VETO", probability=0.8,
                     rationale="auditor resigned mid-year", provenance=stamp())
    p = a.to_veto_proposal("auditor_change", "2016-06-30T00:00:00Z")
    assert p.channel == "veto_proposal"
    with pytest.raises(FirewallViolation):
        p.apply_to_book()


def test_portfolio_action_is_not_an_llm_channel():
    assert "portfolio_action" in CHANNELS
    assert "portfolio_action" not in LLM_CHANNELS
