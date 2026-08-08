"""Tests for the Aegis Belief Network — especially its invariants.

The important ones are not "does the math run" but "can the architecture be
violated": can P&L write a belief, can a resolution leak before it realized,
can a claim be silently edited, can a retrospective window promote.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis_brain.abn import calibration as cal
from aegis_brain.abn import gate
from aegis_brain.abn.core import Claim, ClaimLedger, Resolution, redact_entity
from aegis_brain.abn.posterior import (BetaHitRate, ExposureBrake, NormalEffect,
                                       PosteriorStore, deff)


def mk_claim(i=0, asof="2026-01-31", p=0.6, ctx="default", cls="earnings"):
    return Claim(claim_class=cls, entity_key=f"permno:{10000+i}", asof=asof,
                 kind="direction", statement=f"permno:{10000+i} beats market",
                 anchor=p, anchor_units="prob", window_days=(0, 30), p_raw=p,
                 context_key=ctx, source="test")


# ── claim schema ────────────────────────────────────────────────────────────
def test_size_claim_requires_numeric_anchor():
    with pytest.raises(ValueError, match="anchor"):
        Claim(claim_class="earnings", entity_key="x", asof="2026-01-31",
              kind="reaction_size", statement="s", anchor=None,
              anchor_units="bps", window_days=(0, 5), p_raw=0.5)


def test_abstain_requires_a_known_reason():
    with pytest.raises(ValueError, match="abstain_reason"):
        Claim(claim_class="earnings", entity_key="x", asof="2026-01-31",
              kind="direction", statement="s", anchor=None, anchor_units="prob",
              window_days=(0, 5), p_raw=None, abstain=True,
              abstain_reason="i felt unsure")


def test_claim_id_is_content_addressed():
    a, b = mk_claim(1), mk_claim(1)
    assert a.claim_id == b.claim_id
    assert mk_claim(1, p=0.7).claim_id != a.claim_id


# ── ledger ──────────────────────────────────────────────────────────────────
def test_ledger_chain_detects_tampering(tmp_path):
    led = ClaimLedger(tmp_path / "l.jsonl")
    c = mk_claim(1)
    led.add_claim(c)
    led.add_resolution(Resolution(c.claim_id, "2026-03-02", True, 0.05, "pct",
                                  "test"))
    assert led.verify()
    txt = led.path.read_text(encoding="utf-8").replace('"hit": true',
                                                       '"hit": false')
    led.path.write_text(txt, encoding="utf-8")
    assert not led.verify()


def test_claims_and_resolutions_are_write_once(tmp_path):
    led = ClaimLedger(tmp_path / "l.jsonl")
    c = mk_claim(1)
    led.add_claim(c)
    with pytest.raises(ValueError, match="already in the ledger"):
        led.add_claim(c)
    led.add_resolution(Resolution(c.claim_id, "2026-03-02", True, 0.05, "pct", "t"))
    with pytest.raises(ValueError, match="already resolved"):
        led.add_resolution(Resolution(c.claim_id, "2026-03-02", False, 0.0,
                                      "pct", "t"))


def test_outcome_embargo_hides_unrealized_resolutions(tmp_path):
    led = ClaimLedger(tmp_path / "l.jsonl")
    c = mk_claim(1, asof="2026-01-31")          # window closes 2026-03-02
    led.add_claim(c)
    led.add_resolution(Resolution(c.claim_id, "2026-03-02", True, 0.05, "pct", "t"))
    early = led.retrieve("2026-02-10")
    assert early[0]["resolution"] is None, "resolution leaked before it realized"
    later = led.retrieve("2026-04-01")
    assert later[0]["resolution"]["hit"] is True


def test_retrieval_is_ticker_blind_by_default(tmp_path):
    led = ClaimLedger(tmp_path / "l.jsonl")
    led.add_claim(mk_claim(1))
    blind = led.retrieve("2026-06-01")[0]
    assert "entity_key" not in blind and "statement" not in blind
    named = led.retrieve("2026-06-01", allow_entity=True)[0]
    assert named["entity_key"] == "permno:10001"


def test_redaction_removes_the_entity_handle():
    c = mk_claim(5)
    assert "permno:10005" not in redact_entity(c).statement


# ── posteriors ──────────────────────────────────────────────────────────────
def test_pnl_cannot_write_a_belief():
    """The D3 rule as a type check, not a comment."""
    store = PosteriorStore()
    c = mk_claim(1).__dict__ | {"claim_class": "earnings"}
    for bad in (0.42, {"pnl": 1200.0}, "profit"):
        with pytest.raises(TypeError, match="Resolution and nothing else"):
            store.update(c, bad)
    assert len(store.rejected_writes) == 3


def test_resolution_updates_hit_rate_toward_truth():
    store = PosteriorStore()
    c = mk_claim(1).__dict__
    for i in range(60):
        store.update(c, Resolution(f"id{i}", "2026-02-01", i % 4 != 0, 0.01,
                                   "pct", "t"))
    hr = store.hit_rate("earnings")
    assert 0.68 < hr["mean"] < 0.82        # true rate 0.75
    assert hr["n_eff"] > 30


def test_correlated_resolutions_are_deflated():
    assert deff(1) == 1.0
    assert deff(6) == pytest.approx(2.0)   # eta = 0.5 at six same-day
    solo, cohort = PosteriorStore(), PosteriorStore()
    c = mk_claim(1).__dict__
    for i in range(12):
        solo.update(c, Resolution(f"a{i}", "2026-02-01", True, 0.0, "pct", "t"),
                    cohort_size=1)
        cohort.update(c, Resolution(f"b{i}", "2026-02-01", True, 0.0, "pct", "t"),
                      cohort_size=6)
    assert cohort.hit_rate("earnings")["n_eff"] < solo.hit_rate("earnings")["n_eff"]


def test_fast_layer_forgets_old_evidence():
    b = BetaHitRate()
    for _ in range(400):
        b.update(True)
    assert b.n_eff < 120                    # bounded by the 75-resolution half-life
    for _ in range(150):
        b.update(False)
    assert b.mean < 0.25                    # regime change is picked up


def test_per_cell_effect_is_suppressed_when_unidentified():
    store = PosteriorStore()
    c = mk_claim(1).__dict__
    for i in range(50):
        store.update(c, Resolution(f"id{i}", "2026-02-01", True, 0.0005, "pct",
                                   "t"), obs_sd=0.002)
    eff = store.effect_size("earnings")
    assert eff["used"] == "pooled" and "unidentified" in eff["note"]


def test_changepoint_is_a_partial_reset_not_a_wipe():
    e = NormalEffect()
    for _ in range(30):
        e.update(0.001, 0.002)
    m, v, n = e.mean, e.var, e.n_eff
    e.partial_reset()
    assert e.mean == m and e.var == 2 * v and e.n_eff == 0.5 * n


def test_exposure_brake_reads_but_cannot_write():
    store = PosteriorStore()
    brake = ExposureBrake(store)
    assert brake.multiplier(-0.05) == 1.0
    assert brake.multiplier(-0.30) == 0.0
    assert 0 < brake.multiplier(-0.18) < 1
    assert not any(hasattr(v, "update") for v in brake.__dict__.values())


# ── calibration ─────────────────────────────────────────────────────────────
def test_platt_shrinks_overconfidence_and_never_extremizes():
    assert cal.platt(0.90) < 0.90
    assert cal.platt(0.10) > 0.10
    assert cal.platt(0.50) == pytest.approx(0.50, abs=1e-9)
    assert cal.CLAMP[0] <= cal.platt(0.999) <= cal.CLAMP[1]


def test_calibrator_refuses_to_fit_on_too_little_data():
    p = np.random.default_rng(0).uniform(0.2, 0.8, 50)
    y = (np.random.default_rng(1).uniform(size=50) < p).astype(int)
    out = cal.fit_platt(p, y)
    assert out["fitted"] is False and "noise" in out["reason"]


def test_report_is_selection_adjusted():
    p = np.array([0.9, 0.8, 0.7, 0.6])
    y = np.array([1, 1, 0, 1])
    r = cal.report(p, y, n_abstain=6)
    assert r["coverage"] == 0.4
    assert r["calibrated"]["brier"] != r["raw"]["brier"]


# ── promotion gate ──────────────────────────────────────────────────────────
def test_backtest_evidence_can_never_promote():
    g = gate.evaluate(gate.GateInput("earnings", t_stat=9.9, n_resolutions=5000,
                                     months_forward=600,
                                     evidence_source="backtest"))
    assert g["verdict"] == "INSUFFICIENT"
    assert any("retrospective" in r for r in g["reasons"])


def test_forward_lane_below_the_bar_holds():
    g = gate.evaluate(gate.GateInput("earnings", t_stat=2.5, n_resolutions=300,
                                     months_forward=30,
                                     evidence_source="forward_lane"))
    assert g["verdict"] == "HOLD" and any("t=2.50" in r for r in g["reasons"])


def test_forward_lane_clearing_everything_promotes():
    g = gate.evaluate(gate.GateInput("earnings", t_stat=4.5, n_resolutions=500,
                                     months_forward=26,
                                     evidence_source="forward_lane", dsr=0.97))
    assert g["verdict"] == "PROMOTE"


def test_attention_floor_keeps_losers_sampled():
    assert gate.attention_weight({"available": False}) == 0.20
    w = gate.attention_weight({"available": True, "mean": 0.5,
                               "ci95": [0.45, 0.55]})
    assert w >= 0.20
