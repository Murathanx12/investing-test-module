"""Daily-frequency macro/allocation harness — batch-4 instruments.

Loads the on-disk ETF daily closes (auto-adjusted, i.e. total-return proxy —
disclosed assumption) and provides the shared backtest mechanics: daily
position frames -> net returns at one-way bps costs on traded value, and the
standard stats block. Explore window 2004-01..2018-12; confirm 2019-2024 is
HELD OUT exactly like the factory (readable only by a pre-registered confirm
run).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT

ETF_PATH = MODULE_ROOT / "data" / "macro" / "etf_daily_close.parquet"
GPR_PATH = (MODULE_ROOT / "data" / "macro" / "gpr_snapshots"
            / "data_gpr_daily_recent_snap20260724.xls")

EXPLORE_START = pd.Timestamp("2004-01-01")
EXPLORE_END = pd.Timestamp("2018-12-31")   # confirm 2019+ HELD OUT


def load_closes() -> pd.DataFrame:
    return pd.read_parquet(ETF_PATH).sort_index()


def daily_returns(closes: pd.DataFrame) -> pd.DataFrame:
    return closes.pct_change(fill_method=None)


def backtest(weights: pd.DataFrame, rets: pd.DataFrame,
             cost_bps_one_way: float = 5.0) -> pd.DataFrame:
    """weights: daily target weights (already lagged — weight at date t is
    APPLIED to return of date t). Cost charged on |weight change|."""
    w = weights.reindex(rets.index).fillna(0.0)
    gross = (w * rets.reindex(columns=w.columns)).sum(axis=1)
    traded = w.diff().abs().sum(axis=1).fillna(0.0)
    net = gross - traded * cost_bps_one_way / 1e4
    return pd.DataFrame({"gross": gross, "net": net, "traded": traded})


def stats(net: pd.Series, label: str) -> dict:
    net = net.dropna()
    cum = (1 + net).cumprod()
    years = len(net) / 252
    monthly = net.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    return {
        "label": label, "days": int(len(net)),
        "cagr": round(float(cum.iloc[-1] ** (1 / years) - 1), 4),
        "vol_ann": round(float(net.std(ddof=1) * np.sqrt(252)), 4),
        "sharpe": round(float(net.mean() / net.std(ddof=1) * np.sqrt(252)), 2)
        if net.std(ddof=1) > 0 else np.nan,
        "max_dd": round(float((cum / cum.cummax() - 1).min()), 3),
        "worst_month": round(float(monthly.min()), 4),
    }


def t_excess_monthly(net_a: pd.Series, net_b: pd.Series) -> float:
    """t-stat of monthly return difference a-b (compounded within month)."""
    ma = net_a.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    mb = net_b.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    d = (ma - mb).dropna()
    sd = d.std(ddof=1)
    return float(d.mean() / sd * np.sqrt(len(d))) if sd > 0 else np.nan


def load_gpr_daily() -> pd.Series:
    g = pd.read_excel(GPR_PATH)
    g["date"] = pd.to_datetime(g["date"])
    return g.set_index("date")["GPRD"].dropna().sort_index()
