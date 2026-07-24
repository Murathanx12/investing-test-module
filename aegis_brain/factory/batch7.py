"""Factory batch 7 — column-unblocked fundamentals + conc mirror (frozen in
docs/STRATEGY_FACTORY.md BEFORE any scan). Built from comp_funda_ext_cols
(WRDS batch-4 harvest 2026-07-25) joined to the base funda pull; PIT =
datadate + 6 months, ffill <= 18 months; market equity from the panel."""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.batch6 import _cust_conc
from aegis_brain.factory.signals import FactorySignal

RAW = MODULE_ROOT / "data" / "wrds_raw"
_FAR_FUTURE = pd.Timestamp("2262-01-01")
_CACHE: dict = {}


def _annual_wide(panel: Panel, col_frame: pd.DataFrame, val: str) -> pd.DataFrame:
    """(gvkey, datadate, val) -> PIT [month x permno] wide frame."""
    link = pd.read_parquet(RAW / "ccm_link.parquet").dropna(subset=["permno", "gvkey"])
    link["gvkey"] = link["gvkey"].astype(str).str.strip()
    link["sym"] = link["permno"].astype("Int64").astype(str)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"]).fillna(_FAR_FUTURE)
    m = col_frame.merge(link, on="gvkey")
    m = m[(m["datadate"] >= m["linkdt"]) & (m["datadate"] <= m["linkenddt"])]
    m["avail"] = (m["datadate"] + pd.DateOffset(months=6)).dt.to_period("M").dt.to_timestamp("M")
    wide = m.pivot_table(index="avail", columns="sym", values=val, aggfunc="last")
    return (wide.reindex(panel.monthly_ret.index).ffill(limit=18)
            .reindex(columns=panel.monthly_ret.columns))


def _ext() -> pd.DataFrame:
    if "ext" not in _CACHE:
        e = pd.read_parquet(RAW / "comp_funda_ext_cols.parquet")
        e["gvkey"] = e["gvkey"].astype(str).str.strip()
        e["datadate"] = pd.to_datetime(e["datadate"])
        base = pd.read_parquet(RAW / "comp_funda.parquet",
                               columns=["gvkey", "datadate", "sale", "at", "csho"])
        base["gvkey"] = base["gvkey"].astype(str).str.strip()
        base["datadate"] = pd.to_datetime(base["datadate"])
        f = e.merge(base, on=["gvkey", "datadate"], how="inner")
        f = f.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"])
        _CACHE["ext"] = f
    return _CACHE["ext"]


def build_batch7(panel: Panel) -> list[FactorySignal]:
    f = _ext()
    g = f.groupby("gvkey", sort=False)
    at_lag = g["at"].shift(1)

    f = f.assign(
        inv_div=((f["invt"] - g["invt"].shift(1)) - (f["sale"] - g["sale"].shift(1)))
        / at_lag.where(at_lag > 0),
        rect_div=((f["rect"] - g["rect"].shift(1)) - (f["sale"] - g["sale"].shift(1)))
        / at_lag.where(at_lag > 0),
        payout=(f["dvc"].fillna(0) + f["prstkc"].fillna(0)),
        re_val=f["re"],
        csho_v=f["csho"],
    )
    for c in ("inv_div", "rect_div"):
        lo, hi = f[c].quantile([0.005, 0.995])
        f[c] = f[c].clip(lo, hi)

    re_w = _annual_wide(panel, f[["gvkey", "datadate", "re_val"]].dropna(), "re_val")
    csho_w = _annual_wide(panel, f[["gvkey", "datadate", "csho_v"]].dropna(), "csho_v")
    payout_w = _annual_wide(panel, f[["gvkey", "datadate", "payout"]].dropna(), "payout")
    inv_w = _annual_wide(panel, f[["gvkey", "datadate", "inv_div"]].dropna(), "inv_div")
    rect_w = _annual_wide(panel, f[["gvkey", "datadate", "rect_div"]].dropna(), "rect_div")

    px = panel.month_end_price.abs()
    me = (csho_w * px).where(csho_w > 0)  # $M: csho millions x price

    def re_me(p: Panel) -> pd.DataFrame:
        r = re_w / me.where(me > 0)
        # negative retained earnings = accumulated losses; keep (informative tail)
        lo, hi = r.stack().quantile([0.005, 0.995])
        return r.clip(lo, hi)

    def payout_yield(p: Panel) -> pd.DataFrame:
        y = payout_w / me.where(me > 0)
        return y.clip(0, y.stack().quantile(0.995))

    def conc_low(p: Panel) -> pd.DataFrame:
        return _cust_conc(p)

    return [
        FactorySignal("re_me", "Retained earnings / market equity — the "
                      "component through which B/M predicts (Ball et al. "
                      "2020); horizon annual.", re_me, +1),
        FactorySignal("inv_div", "Inventory growth minus sales growth, "
                      "asset-scaled — demand shortfall / channel stuffing "
                      "(Abarbanell-Bushee); horizon annual.",
                      lambda p: inv_w, -1),
        FactorySignal("rect_div", "Receivables growth minus sales growth — "
                      "aggressive revenue recognition; horizon annual.",
                      lambda p: rect_w, -1),
        FactorySignal("payout_yield", "Net payout (dividends + repurchases) "
                      "/ market equity (Boudoukh et al. 2007); horizon "
                      "annual.", payout_yield, +1),
        FactorySignal("conc_low", "Mirror of batch-6 cust_conc reversal "
                      "(book-inspected IC t −7.4): diversified-customer "
                      "suppliers outperform; horizon annual.", conc_low, -1),
    ]
