"""NIGHT-3 unit tests — the EXPERIENCE contract, the embargo, and the graders.

The tests that matter here are the ones that assert a REFUSAL: a missing field
must raise, an overwrite must raise, and an un-resolved experience must be
invisible. A store that silently accepts a malformed experience would poison
every posterior downstream with a number nobody chose.
"""
from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from aegis_brain.night3 import coherence as coh
from aegis_brain.night3 import persistence as pers
from aegis_brain.night3.decide import Decision, build_book, parse_decisions
from aegis_brain.night3.experience import (FINGERPRINT_FEATURES, Experience,
                                           ExperienceStore, attribute,
                                           classify_outcome)
from aegis_brain.night3.llmcache import SpendGuard, parse_json, prompt_hash
from aegis_brain.night3.slate import Candidate, Slate, book_return, render_slate


def _exp(**kw) -> Experience:
    base = dict(
        ts="2010-01-31", information_state_hash="abc123", market_regime="risk_on",
        event_class="monthly_slate", fingerprint=(50.0,) * len(FINGERPRINT_FEATURES),
        model_id="deepseek-chat", brain_version="night3-1.0-armE",
        thesis="profitability", direction="BUY", confidence=0.7,
        expected_return=0.01, horizon_months=1, target=0.01, invalidation=-0.05,
        resolved_ts="2010-02-28", realized_return=0.03, benchmark_return=0.01,
        abnormal_return=0.02, error=0.01, attribution="thesis_played_out",
        outcome_class="win", lesson_text="ok", entity_key="10001")
    base.update(kw)
    return Experience(**base)


# ── the contract ────────────────────────────────────────────────────────────
class TestExperienceContract:
    def test_valid_experience_builds_and_hashes_stably(self):
        e1, e2 = _exp(), _exp()
        assert e1.experience_id == e2.experience_id
        assert len(e1.experience_id) == 16

    def test_identity_changes_with_the_decision(self):
        assert _exp().experience_id != _exp(direction="SELL").experience_id

    @pytest.mark.parametrize("kw", [
        {"direction": "MAYBE"}, {"thesis": "vibes"},
        {"attribution": "because"}, {"outcome_class": "meh"}])
    def test_bad_enum_raises(self, kw):
        with pytest.raises(ValueError):
            _exp(**kw)

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError):
            _exp(confidence=1.4)

    def test_nan_numeric_raises_rather_than_defaulting(self):
        with pytest.raises(ValueError):
            _exp(abnormal_return=float("nan"))

    def test_short_fingerprint_raises(self):
        with pytest.raises(ValueError):
            _exp(fingerprint=(1.0, 2.0))

    def test_resolution_before_decision_is_a_lookahead_bug(self):
        with pytest.raises(ValueError, match="look-ahead"):
            _exp(ts="2010-03-31", resolved_ts="2010-02-28")

    def test_empty_required_string_raises(self):
        with pytest.raises(ValueError):
            _exp(market_regime="  ")


class TestStore:
    def test_append_is_idempotent_and_persists(self, tmp_path):
        s = ExperienceStore(tmp_path / "e.jsonl")
        assert s.append(_exp()) is True
        assert s.append(_exp()) is False          # same id, same content
        assert len(s) == 1
        assert len(ExperienceStore(tmp_path / "e.jsonl")) == 1

    def test_same_id_different_content_refuses_to_overwrite(self, tmp_path):
        s = ExperienceStore(tmp_path / "e.jsonl")
        s.append(_exp())
        # same (info_state, direction, ts, entity, model) but a different outcome
        with pytest.raises(ValueError, match="refusing to overwrite"):
            s.append(_exp(abnormal_return=-0.5, outcome_class="big_loss",
                          attribution="thesis_wrong"))

    def test_outcome_embargo_hides_unresolved_experiences(self, tmp_path):
        s = ExperienceStore(tmp_path / "e.jsonl")
        s.append(_exp(ts="2010-01-31", resolved_ts="2010-02-28"))
        assert s.available_at("2010-02-28") == []          # strict: not yet
        assert len(s.available_at("2010-03-31")) == 1

    def test_retrieval_respects_the_embargo(self, tmp_path):
        s = ExperienceStore(tmp_path / "e.jsonl")
        s.append(_exp())
        fp = (50.0,) * len(FINGERPRINT_FEATURES)
        assert s.retrieve(fp, "2010-02-28") == []
        assert len(s.retrieve(fp, "2010-06-30")) == 1

    def test_retrieval_is_nearest_first_and_deterministic(self, tmp_path):
        s = ExperienceStore(tmp_path / "e.jsonl")
        for i, v in enumerate((10.0, 50.0, 90.0)):
            s.append(_exp(ts=f"2010-0{i+1}-28",
                          resolved_ts=f"2010-0{i+2}-28",
                          information_state_hash=f"h{i}",
                          fingerprint=(v,) * len(FINGERPRINT_FEATURES)))
        q = (52.0,) * len(FINGERPRINT_FEATURES)
        got = s.retrieve(q, "2011-01-31", k=3)
        # |52-50|=2 < |52-90|=38 < |52-10|=42
        assert [g["fingerprint"][0] for g in got] == [50.0, 90.0, 10.0]
        assert got == s.retrieve(q, "2011-01-31", k=3)     # same query, same answer

    def test_fast_path_matches_the_scan(self, tmp_path):
        s = ExperienceStore(tmp_path / "e.jsonl")
        rng = np.random.default_rng(0)
        for i in range(60):
            s.append(_exp(ts=f"2010-01-{(i % 27) + 1:02d}",
                          resolved_ts=f"2011-{(i % 12) + 1:02d}-28",
                          information_state_hash=f"h{i}",
                          fingerprint=tuple(float(x) for x in
                                            rng.integers(1, 100, len(FINGERPRINT_FEATURES)))))
        q = (40.0,) * len(FINGERPRINT_FEATURES)
        fast = s.retrieve(q, "2011-07-31", k=5)
        brute = sorted(
            [r for r in s._rows if r["resolved_ts"] < "2011-07-31"],
            key=lambda r: (float(np.linalg.norm(
                (np.array(r["fingerprint"]) - np.array(q)) / 100.0)),
                r["experience_id"]))[:5]
        assert [f["experience_id"] for f in fast] == [b["experience_id"] for b in brute]

    def test_summary_always_carries_n(self, tmp_path):
        s = ExperienceStore(tmp_path / "e.jsonl")
        s.append(_exp())
        got = s.summarize_neighbours(s.retrieve((50.0,) * 6, "2010-06-30"))
        assert got["n"] == 1                       # a generalization without n
        assert "frac_beat_benchmark" in got        # is rejected by design


class TestGraders:
    @pytest.mark.parametrize("ab,cls", [
        (0.20, "big_win"), (0.05, "win"), (0.0, "flat"),
        (-0.05, "loss"), (-0.30, "big_loss")])
    def test_outcome_classes_are_monotone(self, ab, cls):
        assert classify_outcome(ab) == cls

    def test_attribution_flags_the_regime_when_everything_moved(self):
        assert attribute("BUY", -0.08, 0.02, -0.08) == "regime_dominated"

    def test_attribution_credits_a_working_thesis(self):
        assert attribute("BUY", 0.06, 0.02, 0.0) == "thesis_played_out"

    def test_attribution_blames_a_broken_one(self):
        assert attribute("BUY", -0.05, 0.02, 0.0) == "thesis_wrong"


class TestPersistence:
    def _r(self, **kw):
        base = dict(permno="1", ts="2010-03-31", months_ago=2,
                    prior_direction="BUY", prior_conviction=0.8,
                    prior_expected=0.02, realized_abnormal=-0.10,
                    new_direction="BUY", new_conviction=0.8)
        base.update(kw)
        return pers.grade_review(**base)

    def test_no_movement_on_strong_evidence_is_underreaction(self):
        assert self._r().verdict == "underreaction"

    def test_big_swing_on_no_evidence_is_overreaction(self):
        assert self._r(realized_abnormal=0.0, new_direction="SELL",
                       new_conviction=0.9).verdict == "overreaction"

    def test_cutting_conviction_after_a_loss_is_appropriate(self):
        assert self._r(new_conviction=0.2).verdict == "appropriate"

    def test_self_recall_is_scored_when_stated(self):
        assert self._r(stated_old_belief="BUY").recall_correct is True
        assert self._r(stated_old_belief="SELL").recall_correct is False

    def test_summary_separates_the_two_failure_modes(self):
        rs = [self._r(), self._r(permno="2"),
              self._r(permno="3", realized_abnormal=0.0,
                      new_direction="SELL", new_conviction=0.9)]
        s = pers.summarize(rs)
        assert s["counts"]["underreaction"] == 2
        assert s["counts"]["overreaction"] == 1
        assert s["underreaction_minus_overreaction"] == 1


class TestCoherence:
    def test_a_pair_differs_in_exactly_one_rendered_line(self):
        s = coh.build_scenarios(1)[0]
        lo = coh.perturb(s, "valuation", "low").render().splitlines()
        hi = coh.perturb(s, "valuation", "high").render().splitlines()
        assert sum(a != b for a, b in zip(lo, hi)) == 1

    def test_ties_are_failures_but_are_counted_separately(self):
        pairs = [{"dimension": "valuation", "low": 0.02, "high": 0.02, "ok": True},
                 {"dimension": "valuation", "low": 0.01, "high": 0.03, "ok": True}]
        g = coh.grade(pairs)["valuation"]
        assert g["n_correct"] == 1 and g["n_tied"] == 1 and g["n_wrong"] == 0
        assert g["pass_rate"] == 0.5

    def test_wrong_direction_is_distinguished_from_a_tie(self):
        pairs = [{"dimension": "regime", "low": 0.05, "high": 0.01, "ok": True}]
        assert coh.grade(pairs)["regime"]["n_wrong"] == 1

    def test_unusable_pairs_never_inflate_the_denominator(self):
        pairs = [{"dimension": "regime", "low": None, "high": 0.01, "ok": False}]
        assert coh.grade(pairs)["regime"]["n"] == 0


class TestSpendAndCache:
    def test_guard_raises_at_the_cap_rather_than_degrading(self):
        g = SpendGuard(0.001)
        g.record({"prompt_tokens": 10_000_000, "completion_tokens": 0})
        with pytest.raises(RuntimeError, match="SPEND CAP"):
            g.check()

    def test_prompt_hash_keys_on_content_not_identity(self):
        assert prompt_hash("s", "u") == prompt_hash("s", "u")
        assert prompt_hash("s", "u") != prompt_hash("s", "u ")

    def test_parse_json_survives_fences(self):
        assert parse_json('```json\n{"a": 1}\n```')["a"] == 1


class TestSlateAndBook:
    def _slate(self, n=6):
        cs = tuple(Candidate(label=chr(65 + i), permno=str(i), sector="services",
                             engine_rank=i + 1, pct_ret_12m=50, pct_vol_12m=50,
                             pct_gross_profit=90 - i, pct_book_to_market=50,
                             pct_mom_12_1=50, pct_size=50,
                             fwd_ret=0.10 - 0.02 * i) for i in range(n))
        return Slate(formation_month="2010-01-31", realized_month="2010-02-28",
                     candidates=cs, benchmark_fwd=0.01, regime="risk_on")

    def test_masked_render_leaks_no_identity_or_date(self):
        text = render_slate(self._slate())
        assert "2010" not in text and "permno" not in text
        for token in ("engine_rank", "rank", "score"):
            assert token not in text.lower()

    def test_information_state_hash_ignores_outcomes(self):
        s = self._slate()
        moved = Slate(**{**s.__dict__,
                         "candidates": tuple(
                             Candidate(**{**c.__dict__, "fwd_ret": 99.0})
                             for c in s.candidates)})
        assert s.information_state_hash() == moved.information_state_hash()

    def test_book_is_buys_by_conviction_then_holds(self):
        d = {"A": Decision("A", "HOLD", 0.9, 0.0, "value"),
             "B": Decision("B", "BUY", 0.4, 0.0, "value"),
             "C": Decision("C", "BUY", 0.8, 0.0, "value"),
             "D": Decision("D", "SELL", 0.9, 0.0, "value")}
        assert build_book(d, self._slate(), top_n=3) == ["C", "B", "A"]

    def test_costs_are_charged_on_new_names_only(self):
        s = self._slate()
        r_fresh, traded_fresh = book_return(s, ["A", "B"], 25.0, None)
        r_held, traded_held = book_return(s, ["A", "B"], 25.0, {"0", "1"})
        assert traded_fresh == 1.0 and traded_held == 0.0
        assert r_held > r_fresh

    def test_parse_reports_missing_labels_instead_of_patching(self):
        s = self._slate()
        got, diag = parse_decisions(
            json.dumps({"decisions": [
                {"label": "A", "direction": "BUY", "conviction": 0.6,
                 "expected_excess_return": 0.01, "thesis": "value"}]}), s)
        assert len(got) == 1
        assert diag["missing"] == ["B", "C", "D", "E", "F"]

    def test_parse_drops_unknown_labels_loudly(self):
        s = self._slate()
        _, diag = parse_decisions(
            json.dumps({"decisions": [
                {"label": "ZZ", "direction": "BUY", "conviction": 0.6,
                 "expected_excess_return": 0.01, "thesis": "value"}]}), s)
        assert diag["unknown_label"] == 1
