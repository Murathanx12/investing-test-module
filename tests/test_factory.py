"""Factory scan harness: PIT alignment, hold-band, direction handling.

The scan has no model, so the only leak surface is formation/test alignment —
these tests pin it: a signal equal to NEXT month's return must show IC ~ 1
(proves the pairing is formation-month score vs month t+1 return), and a
signal equal to the CURRENT month's return must show IC ~ 0 on iid returns
(proves the scan does not accidentally score with the test month's own data).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.signals import FactorySignal


def _synthetic_panel(n_months: int = 60, n_syms: int = 250, seed: int = 7) -> Panel:
    rng = np.random.default_rng(seed)
    months = pd.date_range("2004-01-31", periods=n_months, freq="ME")
    syms = [f"S{i}" for i in range(n_syms)]
    ret = pd.DataFrame(rng.normal(0.005, 0.06, (n_months, n_syms)),
                       index=months, columns=syms)
    price = pd.DataFrame(50.0, index=months, columns=syms)
    dv = pd.DataFrame(1e6, index=months, columns=syms)
    return Panel(monthly_ret=ret, month_end_price=price, monthly_dollar_vol=dv,
                 delist_month={s: months[-1] for s in syms})


CFG = ScanConfig(first_test_month="2004-06-30", last_test_month="2008-12-31",
                 min_names_per_month=50)


def test_oracle_signal_has_near_perfect_ic():
    panel = _synthetic_panel()
    oracle = FactorySignal("oracle", "test", lambda p: p.monthly_ret.shift(-1), +1)
    res = scan_signal(panel, oracle, "largemid", CFG)
    assert res["summary"]["ic_mean"] > 0.95
    assert res["summary"]["t_excess_gross"] > 5


def test_current_month_signal_has_no_ic_on_iid_returns():
    panel = _synthetic_panel()
    same = FactorySignal("same_month", "test", lambda p: p.monthly_ret, +1)
    res = scan_signal(panel, same, "largemid", CFG)
    assert abs(res["summary"]["ic_mean"]) < 0.05


def test_direction_flips_the_book():
    panel = _synthetic_panel()
    up = FactorySignal("up", "test", lambda p: p.monthly_ret.shift(-1), +1)
    dn = FactorySignal("dn", "test", lambda p: p.monthly_ret.shift(-1), -1)
    r_up = scan_signal(panel, up, "largemid", CFG)["summary"]
    r_dn = scan_signal(panel, dn, "largemid", CFG)["summary"]
    assert r_up["mean_excess_net_bps"] > 0 > r_dn["mean_excess_net_bps"]


def test_constant_signal_hold_band_kills_turnover():
    panel = _synthetic_panel()
    const = FactorySignal(
        "const", "test",
        lambda p: pd.DataFrame(
            np.tile(np.arange(p.monthly_ret.shape[1], dtype=float),
                    (p.monthly_ret.shape[0], 1)),
            index=p.monthly_ret.index, columns=p.monthly_ret.columns),
        +1)
    res = scan_signal(panel, const, "largemid", CFG)
    monthly = res["monthly"]
    # first month buys the book (traded=1); after that ranks never change
    assert monthly["traded"].iloc[0] == pytest.approx(1.0)
    assert monthly["traded"].iloc[1:].max() < 1e-9


def test_scan_respects_explore_boundary():
    panel = _synthetic_panel()
    sig = FactorySignal("mom", "test", lambda p: p.monthly_ret.rolling(3).mean(), +1)
    res = scan_signal(panel, sig, "largemid", CFG)
    assert res["monthly"].index.max() <= pd.Timestamp(CFG.last_test_month)
    assert res["monthly"].index.min() >= pd.Timestamp(CFG.first_test_month)
