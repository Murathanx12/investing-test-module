"""PF-2 harness extensions: blend, meta-portfolio, spec hash v2.

These test the arithmetic and the refusals, not the strategies. Every case
here runs on constructed series so a failure means the machinery is wrong, not
that the market was unkind.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.pf import meta
from aegis_brain.pf.blend import blend_monthly
from aegis_brain.pf.spec import StrategySpec


def _book(rets, months=None) -> pd.DataFrame:
    n = len(rets)
    idx = months if months is not None else pd.date_range("2000-01-31", periods=n, freq="ME")
    return pd.DataFrame({"gross": rets, "net": rets, "cost": 0.0,
                         "traded": 0.0, "n_held": 25, "cash_w": 0.0,
                         "risk_on": True}, index=idx)


# ── blend ───────────────────────────────────────────────────────────────────

def test_blend_of_identical_sleeves_is_the_sleeve_minus_fee():
    """If strategy and market return the same thing, no rebalancing trade can
    occur — the only drag left is the index fee."""
    r = np.full(24, 0.01)
    idx = pd.date_range("2000-01-31", periods=24, freq="ME")
    out, diag = blend_monthly(_book(r, idx), pd.Series(r, index=idx), 0.4,
                              fee_bps_annual=3.0)
    fee_m = (3.0 / 1e4) / 12 * 0.4
    assert np.allclose(out["net"], 0.01 - fee_m)
    assert diag["blend_rebalance_turnover_1way_annual"] == 0.0


def test_blend_charges_the_rebalancing_trade_when_sleeves_diverge():
    idx = pd.date_range("2000-01-31", periods=24, freq="ME")
    strat = np.full(24, 0.03)
    mkt = pd.Series(np.full(24, -0.01), index=idx)
    out, diag = blend_monthly(_book(strat, idx), mkt, 0.5, fee_bps_annual=0.0)
    naive = 0.5 * -0.01 + 0.5 * 0.03
    assert (out["net"] < naive).all(), "divergent sleeves must cost something"
    assert diag["blend_rebalance_turnover_1way_annual"] > 0


def test_blend_share_of_one_is_refused():
    idx = pd.date_range("2000-01-31", periods=12, freq="ME")
    with pytest.raises(ValueError):
        blend_monthly(_book(np.full(12, 0.01), idx), pd.Series(0.0, index=idx), 1.0)


def test_blend_refuses_a_benchmark_hole():
    idx = pd.date_range("2000-01-31", periods=12, freq="ME")
    mkt = pd.Series(0.01, index=idx)
    mkt.iloc[5] = np.nan
    with pytest.raises(RuntimeError, match="gaps"):
        blend_monthly(_book(np.full(12, 0.01), idx), mkt, 0.3)


def test_spec_rejects_blend_of_one():
    with pytest.raises(ValueError, match="benchmark, not a strategy"):
        StrategySpec(name="x", signals=(("osap:GP", 1.0),), blend_market=1.0)


# ── spec hash v2 ────────────────────────────────────────────────────────────

def test_default_valued_fields_do_not_change_the_hash():
    """The property that lets PF-3 add a knob without renaming PF-2's runs."""
    a = StrategySpec(name="x", signals=(("osap:GP", 1.0),))
    b = StrategySpec(name="x", signals=(("osap:GP", 1.0),), blend_market=0.0,
                     top_n=25)
    assert a.spec_hash() == b.spec_hash()


def test_a_real_parameter_change_changes_the_hash():
    a = StrategySpec(name="x", signals=(("osap:GP", 1.0),))
    assert a.spec_hash() != a.variant(name="x", blend_market=0.3).spec_hash()
    assert a.spec_hash() != a.variant(name="x", top_n=50).spec_hash()


def test_hypothesis_text_is_not_part_of_identity():
    a = StrategySpec(name="x", signals=(("osap:GP", 1.0),), hypothesis="one")
    b = StrategySpec(name="x", signals=(("osap:GP", 1.0),), hypothesis="two")
    assert a.spec_hash() == b.spec_hash()


# ── meta-portfolio ──────────────────────────────────────────────────────────

def _rets(**cols) -> pd.DataFrame:
    n = len(next(iter(cols.values())))
    return pd.DataFrame(cols, index=pd.date_range("2000-01-31", periods=n, freq="ME"))


def test_meta_follows_the_trailing_winner():
    """A always beats B for two years, then they swap. The rule must switch —
    and only after the evidence exists, never before."""
    n = 72
    a = np.concatenate([np.full(36, 0.02), np.full(36, -0.01)])
    b = np.concatenate([np.full(36, -0.01), np.full(36, 0.02)])
    rets = _rets(A=a, B=b)
    book = meta.meta_book(rets, lookback_months=12, hold_top=1, switch_bps=0.0)
    held = book["holding"]
    assert held.iloc[0] == "A"
    assert held.iloc[-1] == "B"
    # It must not switch before the regime actually turned (that would be
    # clairvoyance), and it must have switched by the time the trailing window
    # is entirely inside the new regime (that would be blindness).
    first_b = held[held == "B"].index[0]
    turn = rets.index[36]
    assert first_b > turn, "switched before the regime turned"
    assert first_b <= rets.index[48], "never noticed a 12-month-old change"


def test_meta_switching_costs_are_charged():
    n = 60
    rng = np.random.default_rng(7)
    a, b = rng.normal(0.01, 0.05, n), rng.normal(0.01, 0.05, n)
    free = meta.meta_book(_rets(A=a, B=b), lookback_months=6, switch_bps=0.0)
    paid = meta.meta_book(_rets(A=a, B=b), lookback_months=6, switch_bps=50.0)
    assert (paid["net"] <= free["net"] + 1e-12).all()
    assert paid["cost"].sum() > 0, "the winner-chaser traded but paid nothing"


def test_meta_uses_only_past_returns():
    """Shuffling the FUTURE must not change any earlier decision."""
    n = 60
    rng = np.random.default_rng(11)
    a, b = rng.normal(0.01, 0.04, n), rng.normal(0.01, 0.04, n)
    rets = _rets(A=a, B=b)
    base = meta.meta_book(rets, lookback_months=12)
    a2, b2 = a.copy(), b.copy()
    a2[40:], b2[40:] = a2[40:][::-1], b2[40:][::-1]
    alt = meta.meta_book(_rets(A=a2, B=b2), lookback_months=12)
    # a decision in month m reads months m-12..m-1, so every decision up to and
    # including month 40 must be untouched by rewriting months 40 onward
    cutoff = rets.index[40]
    same = base.loc[base.index <= cutoff, "holding"]
    assert len(same) > 12, "the comparison window collapsed — test is vacuous"
    assert (same == alt.loc[alt.index <= cutoff, "holding"]).all()


def test_equal_weight_control_holds_everything():
    book = meta.equal_weight_book(_rets(A=np.full(24, 0.02), B=np.full(24, 0.0)))
    assert (book["n_held"] == 2).all()
    assert np.allclose(book["gross"], 0.01)


def test_meta_without_a_full_lookback_fails_loudly():
    with pytest.raises(RuntimeError, match="never established"):
        meta.meta_book(_rets(A=np.full(6, 0.01)), lookback_months=24)


def test_strategy_that_dies_is_dropped_not_carried():
    a = np.full(36, 0.01)
    b = np.concatenate([np.full(24, 0.05), np.full(12, np.nan)])
    book = meta.meta_book(_rets(A=a, B=b), lookback_months=12, hold_top=1,
                          switch_bps=0.0)
    assert book["holding"].iloc[-1] == "A"
    assert book["net"].notna().all()
