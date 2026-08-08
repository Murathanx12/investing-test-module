"""Unit tests for the portfolio factory harness.

These test the MECHANICS on synthetic panels where the right answer is known
by construction: cost accounting, turnover, drift, forced liquidation of
delisted names, the placebo's turnover matching, and the loud-failure paths.
An arithmetic bug here would silently rewrite every strategy verdict.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.pf.engine import buy_and_hold_universe, run_book
from aegis_brain.pf.scorecard import scorecard
from aegis_brain.pf.signals import random_score
from aegis_brain.pf.spec import StrategySpec


def make_panel(n_months=60, n_names=200, seed=0, planted=None):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-31", periods=n_months, freq="ME")
    cols = [str(10000 + i) for i in range(n_names)]
    ret = pd.DataFrame(rng.normal(0.01, 0.06, (n_months, n_names)),
                       index=idx, columns=cols)
    if planted is not None:
        ret += planted
    price = pd.DataFrame(50.0, index=idx, columns=cols)
    dvol = pd.DataFrame(np.tile(np.arange(n_names, 0, -1) * 1e6, (n_months, 1)),
                        index=idx, columns=cols)
    return Panel(monthly_ret=ret, month_end_price=price, monthly_dollar_vol=dvol,
                 delist_month={c: idx[-1] for c in cols})


def flat_spec(**kw):
    base = dict(name="T", signals=(("x", 1.0),), segment="all", top_n=10,
                min_names=20, cost_model="flat0", hold_band_mult=1.0,
                first_month="2000-02-29", last_month="2004-12-31")
    base.update(kw)
    return StrategySpec(**base)


def const_score(panel, values):
    return pd.DataFrame(np.tile(values, (len(panel.monthly_ret), 1)),
                        index=panel.monthly_ret.index,
                        columns=panel.monthly_ret.columns)


def all_eligible(panel):
    return pd.DataFrame(True, index=panel.monthly_ret.index,
                        columns=panel.monthly_ret.columns)


def zero_rf(panel):
    return pd.Series(0.0, index=panel.monthly_ret.index)


def test_static_score_buys_once_and_holds():
    """A constant score => one initial trade, then zero turnover."""
    p = make_panel()
    sc = const_score(p, np.arange(p.monthly_ret.shape[1])[::-1])
    out = run_book(p, sc, all_eligible(p), flat_spec(), zero_rf(p))
    m = out["monthly"]
    assert m["traded"].iloc[0] == pytest.approx(1.0)
    # weights drift, so later rebalances trade only the drift back to equal weight
    assert m["traded"].iloc[1:].max() < 0.15
    assert out["diag"]["mean_n_held"] == 10


def test_costs_reduce_net_by_exactly_traded_times_bps():
    p = make_panel()
    sc = const_score(p, np.arange(p.monthly_ret.shape[1])[::-1])
    out = run_book(p, sc, all_eligible(p), flat_spec(cost_model="flat25"),
                   zero_rf(p))
    m = out["monthly"]
    expect = m["traded"] * 25.0 / 1e4
    assert np.allclose(m["cost"], expect)
    assert np.allclose(m["net"], m["gross"] - m["cost"])


def test_planted_edge_is_recovered():
    """Names with a planted +2%/mo alpha and the top score must outperform."""
    n_names = 200
    planted = np.zeros(n_names)
    planted[:10] = 0.02
    p = make_panel(planted=planted)
    sc = const_score(p, np.concatenate([np.ones(10) * 10, np.zeros(n_names - 10)]))
    out = run_book(p, sc, all_eligible(p), flat_spec(), zero_rf(p))
    ew = buy_and_hold_universe(p, all_eligible(p), flat_spec(), zero_rf(p))
    net = out["monthly"]["net"]
    assert net.mean() - ew.reindex(net.index).mean() > 0.015


def test_delisted_name_is_liquidated_not_dropped():
    p = make_panel()
    victim = p.monthly_ret.columns[0]
    p.monthly_ret.loc[p.monthly_ret.index[10]:, victim] = np.nan
    sc = const_score(p, np.arange(p.monthly_ret.shape[1])[::-1])
    # buy-and-hold: only the forced liquidation should trade after month 0
    out = run_book(p, sc, all_eligible(p), flat_spec(rebalance_months=120),
                   zero_rf(p))
    assert out["diag"]["forced_liquidations"] >= 1
    assert out["monthly"]["traded"].iloc[1:].sum() > 0


def test_quarterly_rebalance_trades_less():
    p = make_panel(seed=3)
    rng = np.random.default_rng(1)
    sc = pd.DataFrame(rng.normal(size=p.monthly_ret.shape),
                      index=p.monthly_ret.index, columns=p.monthly_ret.columns)
    m1 = run_book(p, sc, all_eligible(p), flat_spec(), zero_rf(p))
    m3 = run_book(p, sc, all_eligible(p), flat_spec(rebalance_months=3), zero_rf(p))
    assert m3["diag"]["turnover_1way_annual"] < m1["diag"]["turnover_1way_annual"]


def test_random_score_persistence_reduces_turnover():
    p = make_panel(seed=5)
    lo = run_book(p, random_score(p, 1, 0.0), all_eligible(p), flat_spec(),
                  zero_rf(p))["diag"]["turnover_1way_annual"]
    hi = run_book(p, random_score(p, 1, 0.98), all_eligible(p), flat_spec(),
                  zero_rf(p))["diag"]["turnover_1way_annual"]
    assert hi < lo


def test_ko_cost_model_without_frame_fails_loudly():
    p = make_panel()
    sc = const_score(p, np.arange(p.monthly_ret.shape[1])[::-1])
    with pytest.raises(RuntimeError, match="no cost frame"):
        run_book(p, sc, all_eligible(p), flat_spec(cost_model="ko"), zero_rf(p))


def test_thin_universe_fails_loudly_instead_of_booking_cash():
    """A universe that never reaches min_names must raise, not report the
    bill rate as strategy performance."""
    p = make_panel(n_names=30)
    sc = const_score(p, np.arange(30)[::-1])
    with pytest.raises(RuntimeError, match="never established"):
        run_book(p, sc, all_eligible(p), flat_spec(min_names=100), zero_rf(p))


def test_pre_inception_months_are_excluded_from_the_record():
    """Months before the universe is thick enough are not performance."""
    p = make_panel(n_months=60, n_names=200)
    # first 24 months: only 30 names eligible → below min_names
    elig = all_eligible(p)
    elig.iloc[:24, 30:] = False
    sc = const_score(p, np.arange(200)[::-1])
    out = run_book(p, sc, elig, flat_spec(min_names=100, last_month="2004-12-31"),
                   zero_rf(p))
    assert out["monthly"].index.min() >= p.monthly_ret.index[23]


def test_scorecard_excess_matches_manual_computation():
    p = make_panel(seed=7)
    sc = const_score(p, np.arange(p.monthly_ret.shape[1])[::-1])
    spec = flat_spec()
    out = run_book(p, sc, all_eligible(p), spec, zero_rf(p))
    net = out["monthly"]["net"]
    bench = pd.Series(0.005, index=p.monthly_ret.index)
    card = scorecard(out["monthly"], bench, diag=out["diag"],
                     spec_dict=spec.as_dict(), rf=zero_rf(p))
    manual = (1 + net).prod() ** (12 / len(net)) - 1
    assert card["headline"]["cagr_net"] == pytest.approx(manual, abs=1e-4)
    assert card["headline"]["benchmark_cagr"] == pytest.approx(
        1.005 ** 12 - 1, abs=1e-4)


def test_holdout_is_refused_by_default():
    from aegis_brain.pf.panel63 import load_spine
    with pytest.raises(RuntimeError, match="holdout"):
        load_spine(last="2024-12-31")


def test_spec_hash_is_stable_and_variant_changes_it():
    s = flat_spec()
    assert s.spec_hash() == flat_spec().spec_hash()
    assert s.variant(top_n=50).spec_hash() != s.spec_hash()
    # docstring-only fields must not change identity
    assert StrategySpec(**{**s.__dict__, "notes": "x"}).spec_hash() == s.spec_hash()


def test_bad_spec_is_rejected():
    with pytest.raises(ValueError):
        flat_spec(top_n=2)
    with pytest.raises(ValueError):
        flat_spec(segment="nano")
