"""G8 invariants — the instrument is calibrated before its verdicts are trusted.

NIGHT-8's finding was that G7 returns 31.00 bps of traded value at ADV multiples
of 1,000,000x, 100x, 5x and 1x — identical across a million-fold range of
liquidity, because it prices scarcity as delay and never as price. These tests
pin the properties G8 must have for that to stop being true, and the first one
pins the property it must NOT break: at `impact_coef = 0` it is still G7.
"""
import numpy as np
import pandas as pd
import pytest

from aegis_brain.pf.daily_sim import DailyData, SimConfig, simulate
from aegis_brain.pf.impact import (MAX_IMPACT_BPS, SCENARIOS, describe,
                                   square_root_impact_bps, trailing_adv,
                                   trailing_sigma)

N_NAMES = 20
N_DAYS = 756          # three years
REBAL = 252
#: the book starts trading after a warm-up, the way a real sample does; an
#: order placed on day 0 has no trailing ADV and would exercise the fallback
#: rather than the model
WARMUP = 60


def world(*, adv_multiple: float, vol_annual: float = 0.35, seed: int = 7):
    """A market with known liquidity and a known equal-weight annual book.

    `adv_multiple` is each name's daily dollar volume as a multiple of the
    position it holds at $1m of NAV, so the participation cap binds by design.
    """
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2002-01-01", periods=N_DAYS)
    cols = list(range(10_000, 10_000 + N_NAMES))
    sd = vol_annual / np.sqrt(252)
    r = pd.DataFrame(rng.normal(0.10 / 252, sd, (N_DAYS, N_NAMES)),
                     index=days, columns=cols)
    px = 30.0 * (1.0 + r).cumprod()
    pos = 1_000_000.0 / N_NAMES
    data = DailyData(ret=r, prc=px, opn=px,
                     dvol=pd.DataFrame(pos * adv_multiple, index=days,
                                       columns=cols),
                     half_spread=pd.DataFrame(10.0, index=days, columns=cols),
                     rf=pd.Series(0.0, index=days), delist_ret={})
    w = pd.Series(1.0 / N_NAMES, index=cols)
    targets = [{"effective": days[i], "weights": w}
               for i in range(WARMUP, N_DAYS, REBAL)]
    return data, targets


def run(nav0=1_000_000.0, coef=0.0, adv_multiple=50.0, vol_annual=0.35):
    data, targets = world(adv_multiple=adv_multiple, vol_annual=vol_annual)
    cfg = SimConfig(start_nav=nav0, impact_coef=coef, slippage_bps=0.0,
                    commission_bps=0.0)
    return simulate(targets, data, cfg)["diag"]


# ── the law itself ─────────────────────────────────────────────────────────

def test_zero_coefficient_charges_nothing():
    assert square_root_impact_bps(1e6, 1e7, 0.03, 0.0) == 0.0


def test_impact_is_monotone_increasing_in_order_size():
    b = [square_root_impact_bps(q, 1e7, 0.03, 0.5)
         for q in (1e4, 1e5, 1e6, 1e7)]
    assert all(x < y for x, y in zip(b, b[1:]))


def test_impact_is_monotone_decreasing_in_volume():
    b = [square_root_impact_bps(1e6, v, 0.03, 0.5)
         for v in (1e5, 1e6, 1e7, 1e8)]
    assert all(x > y for x, y in zip(b, b[1:]))


def test_impact_is_monotone_increasing_in_volatility():
    b = [square_root_impact_bps(1e6, 1e7, s, 0.5)
         for s in (0.01, 0.02, 0.04, 0.08)]
    assert all(x < y for x, y in zip(b, b[1:]))


def test_it_is_concave_so_capacity_degrades_smoothly():
    """Doubling the order must raise cost per dollar, but by less than double."""
    a = square_root_impact_bps(1e6, 1e8, 0.03, 0.5)
    b = square_root_impact_bps(2e6, 1e8, 0.03, 0.5)
    assert a < b < 2 * a
    assert b == pytest.approx(a * np.sqrt(2), rel=1e-9)


def test_a_name_with_no_volume_is_the_most_expensive_case_not_the_cheapest():
    assert square_root_impact_bps(1e6, 0.0, 0.03, 0.5) == MAX_IMPACT_BPS
    assert square_root_impact_bps(1e6, np.nan, 0.03, 0.5) == MAX_IMPACT_BPS


def test_trailing_windows_do_not_peek():
    idx = pd.bdate_range("2020-01-01", periods=60)
    v = pd.DataFrame(1.0, index=idx, columns=[1])
    v.iloc[-1, 0] = 1e9                       # a huge print on the last day
    assert trailing_adv(v).iloc[-1, 0] < 2.0  # it must not be in today's ADV
    r = pd.DataFrame(0.0, index=idx, columns=[1])
    assert np.isnan(trailing_sigma(r).iloc[0, 0])


def test_the_receipt_block_declares_what_is_not_modelled():
    d = describe(0.5)
    assert d["execution_model"] == "G8"
    assert describe(0.0)["execution_model"] == "G7"
    assert any("urgency" in x for x in d["not_modelled"])
    assert d["scenarios"] == SCENARIOS


# ── the simulator ──────────────────────────────────────────────────────────

def test_zero_impact_is_still_g7():
    g = run(coef=0.0)
    assert g["execution_model"] == "G7"
    assert g["impact_dollars"] == 0
    assert g["explicit_bps_of_traded"] == pytest.approx(
        g["cost_bps_of_traded"], abs=0.01)


def test_impact_only_ever_costs_money():
    g7, g8 = run(coef=0.0), run(coef=0.5)
    assert g8["cost_dollars"] > g7["cost_dollars"]
    assert g8["cagr"] <= g7["cagr"]
    assert g8["execution_model"] == "G8"


def test_costs_decompose_exactly():
    g = run(coef=0.5)
    # cost_bps is rounded to one decimal for the receipt, the parts to two
    assert (g["impact_bps_of_traded"] + g["explicit_bps_of_traded"]
            == pytest.approx(g["cost_bps_of_traded"], abs=0.06))


def test_the_thing_g7_could_not_do_bigger_aum_costs_more_per_dollar():
    """G7 returned the same bps at every rung. G8 must not."""
    bps = [run(nav0=n, coef=0.5)["impact_bps_of_traded"]
           for n in (1e6, 1e7, 1e8)]
    assert all(x < y for x, y in zip(bps, bps[1:])), bps
    assert bps[-1] > 2 * bps[0]


def test_more_liquidity_is_cheaper_at_the_same_size():
    bps = [run(coef=0.5, adv_multiple=m)["impact_bps_of_traded"]
           for m in (5.0, 50.0, 500.0)]
    assert all(x > y for x, y in zip(bps, bps[1:])), bps


def test_no_order_in_a_warmed_up_world_uses_the_fallback():
    """The fallback exists for day one of a sample and must not be load-bearing."""
    assert run(coef=0.5)["impact_warmup_orders"] == 0


def test_the_scenario_band_is_ordered_and_the_middle_is_the_middle():
    bps = {k: run(coef=c, adv_multiple=5.0)["impact_bps_of_traded"]
           for k, c in SCENARIOS.items()}
    assert bps["low"] < bps["base"] < bps["high"]
