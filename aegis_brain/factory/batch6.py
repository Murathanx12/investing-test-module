"""Factory batch 6 — reversal mirrors + panel-adopted novelties (frozen list
in docs/STRATEGY_FACTORY.md BEFORE any scan; horizon+decay declared per
signal). Reuses batch5's audited frame builders where the underlying data is
identical — mirrors are NEW candidates by the sign-flip rule, not retries.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.batch5 import _dtc, _inst_persist, _si_ratio_raw_shares  # noqa: F401
from aegis_brain.factory.fundamentals import FundStore
from aegis_brain.factory.signals import FactorySignal

RAW = MODULE_ROOT / "data" / "wrds_raw"
_FAR_FUTURE = pd.Timestamp("2262-01-01")


def _cg_overhang(panel: Panel) -> pd.DataFrame:
    """Grinblatt-Han gain-overhang PROXY: (P - trailing 60-month dollar-volume-
    weighted average price) / P. True GH turnover weights need shrout (not on
    disk) — proxy declared in the freeze doc."""
    px = panel.month_end_price.abs()
    dv = panel.monthly_dollar_vol
    num = (px * dv).rolling(60, min_periods=24).sum()
    den = dv.rolling(60, min_periods=24).sum()
    vwap = num / den.where(den > 0)
    return (px - vwap) / px.where(px > 0)


def _cust_conc(panel: Panel) -> pd.DataFrame:
    """Max customer salecs / supplier annual sale (Patatoukas 2012), PIT:
    available 6 months after srcdate fiscal year, ffill <=18mo."""
    seg = pd.read_parquet(RAW / "seg_customer.parquet")
    seg = seg[(seg["ctype"] == "COMPANY") & seg["salecs"].notna()].copy()
    seg["gvkey"] = seg["gvkey"].astype(str).str.strip()
    seg["srcdate"] = pd.to_datetime(seg["srcdate"])
    seg["fy"] = seg["srcdate"].dt.year
    mx = seg.groupby(["gvkey", "fy"])["salecs"].max().reset_index()
    f = pd.read_parquet(RAW / "comp_funda.parquet", columns=["gvkey", "datadate", "sale"])
    f = f.dropna().copy()
    f["gvkey"] = f["gvkey"].astype(str).str.strip()
    f["datadate"] = pd.to_datetime(f["datadate"])
    f["fy"] = f["datadate"].dt.year
    m = mx.merge(f, on=["gvkey", "fy"])
    m["conc"] = (m["salecs"] / m["sale"].where(m["sale"] > 0)).clip(0, 1)
    link = pd.read_parquet(RAW / "ccm_link.parquet").dropna(subset=["permno", "gvkey"])
    link["gvkey"] = link["gvkey"].astype(str).str.strip()
    link["sym"] = link["permno"].astype("Int64").astype(str)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"]).fillna(_FAR_FUTURE)
    m = m.merge(link, on="gvkey")
    m = m[(m["datadate"] >= m["linkdt"]) & (m["datadate"] <= m["linkenddt"])]
    m["avail"] = (m["datadate"] + pd.DateOffset(months=6)).dt.to_period("M").dt.to_timestamp("M")
    wide = m.pivot_table(index="avail", columns="sym", values="conc", aggfunc="last")
    return (wide.reindex(panel.monthly_ret.index).ffill(limit=18)
            .reindex(columns=panel.monthly_ret.columns))


def build_batch6(panel: Panel, store: FundStore) -> list[FactorySignal]:
    gp = store.get("gross_prof")

    def dtc_qual(p: Panel) -> pd.DataFrame:
        dtc = _dtc(p, store)
        top_half_gp = gp.ge(gp.median(axis=1), axis=0)
        return dtc.where(top_half_gp)

    return [
        FactorySignal("dtc_high", "Mirror of batch-5 dtc_low: crowded shorts "
                      "(high days-to-cover) carry a shorting premium and "
                      "covering flow; horizon 1-6mo.",
                      lambda p: _dtc(p, store), +1),
        FactorySignal("inst_persist_high", "Mirror of batch-5 "
                      "inst_persist_low: consecutive quarters of net 13F "
                      "buying = durable information; horizon quarters.",
                      _inst_persist, +1),
        FactorySignal("dtc_qual", "High days-to-cover INSIDE top-half gross "
                      "profitability — shorts trapped in sound businesses "
                      "(squeeze asymmetry); horizon quarters.", dtc_qual, +1),
        FactorySignal("cg_overhang", "Grinblatt-Han 2005 gain overhang "
                      "(VWAP-60m proxy): disposition-effect underreaction "
                      "sustains drift in big unrealized winners; horizon "
                      "months.", _cg_overhang, +1),
        FactorySignal("cust_conc", "Customer concentration premium "
                      "(Patatoukas 2012): max customer revenue share; "
                      "compensated relationship risk; horizon annual.",
                      _cust_conc, +1),
    ]
