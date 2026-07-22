"""FundStore PIT alignment: a fiscal year must not be visible before
datadate + 6 months, must be visible after, and must go stale after 18m."""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.fundamentals import FundStore


def _panel(months, syms):
    idx = pd.date_range(months[0], periods=len(months), freq="ME")
    ret = pd.DataFrame(0.01, index=idx, columns=syms)
    return Panel(monthly_ret=ret, month_end_price=ret * 0 + 50,
                 monthly_dollar_vol=ret * 0 + 1e6,
                 delist_month={s: idx[-1] for s in syms})


def _chars(sym: str, datadate: str, gross_prof: float) -> pd.DataFrame:
    avail = (pd.Timestamp(datadate) + pd.DateOffset(months=6)) + pd.offsets.MonthEnd(0)
    row = {c: np.nan for c in ["gross_prof", "oper_prof", "asset_growth",
                               "accruals_cf", "net_issuance", "btm", "roe",
                               "cash_prof", "capx_at", "fscore_lite"]}
    row.update({"sym": sym, "datadate": pd.Timestamp(datadate),
                "avail_month": avail, "gross_prof": gross_prof})
    return pd.DataFrame([row])


def test_pit_lag_and_staleness():
    panel = _panel(pd.date_range("2010-01-31", periods=40, freq="ME"), ["1", "2"])
    chars = _chars("1", "2010-12-31", 0.42)
    store = FundStore(panel, chars)
    gp = store.get("gross_prof")

    avail = pd.Timestamp("2011-06-30")           # datadate + 6m
    before = gp.loc[:avail - pd.offsets.MonthEnd(1), "1"]
    assert before.isna().all(), "fundamental visible before reporting lag"
    assert gp.loc[avail, "1"] == 0.42
    # stale after 18 months of ffill
    last_ok = avail + pd.offsets.MonthEnd(18)
    assert gp.loc[last_ok, "1"] == 0.42
    assert np.isnan(gp.loc[last_ok + pd.offsets.MonthEnd(1), "1"])
    # untouched symbol stays NaN
    assert gp["2"].isna().all()


def test_newer_fiscal_year_supersedes():
    panel = _panel(pd.date_range("2010-01-31", periods=48, freq="ME"), ["1"])
    chars = pd.concat([_chars("1", "2010-12-31", 0.10),
                       _chars("1", "2011-12-31", 0.99)], ignore_index=True)
    store = FundStore(panel, chars)
    gp = store.get("gross_prof")
    assert gp.loc[pd.Timestamp("2012-05-31"), "1"] == 0.10   # old year still live
    assert gp.loc[pd.Timestamp("2012-06-30"), "1"] == 0.99   # new year lands
