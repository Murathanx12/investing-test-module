"""Batch 3b stores — customer momentum, 13F best ideas, price-target upside.

PIT conventions:
  - Segment customer links: srcdate (the fiscal disclosure vintage) + 6 months
    -> valid for 24 months (annual refresh cadence). Customer NAME -> gvkey via
    normalized exact match (the Cohen-Frazzini matching problem; match rate is
    logged — unmatched customers simply drop, which UNDERSTATES the signal).
  - 13F top-10: fdate + 2 months (45-day filing allowance).
  - IBES price targets: announcement date anndats; trailing-90d consensus.
"""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.altstores import _map_on_cusip

logger = logging.getLogger(__name__)

RAW = MODULE_ROOT / "data" / "wrds_raw"

_SUFFIX = re.compile(
    r"\b(INC|INCORPORATED|CORP|CORPORATION|CO|COMPANY|LTD|LIMITED|PLC|LP|LLC|"
    r"HOLDINGS|HLDGS|GROUP|GRP|THE|SA|AG|NV|SE)\b")
_NONALNUM = re.compile(r"[^A-Z0-9 ]")


def _norm_name(s: pd.Series) -> pd.Series:
    up = s.astype(str).str.upper()
    up = up.map(lambda x: _NONALNUM.sub(" ", x))
    up = up.map(lambda x: _SUFFIX.sub(" ", x))
    return up.str.split().str.join(" ")


def _gvkey_to_sym() -> pd.DataFrame:
    link = pd.read_parquet(RAW / "ccm_link.parquet").dropna(subset=["permno"])
    link["linkenddt"] = link["linkenddt"].fillna(pd.Timestamp("2262-01-01"))
    link["sym"] = link["permno"].astype("Int64").astype(str)
    return link[["gvkey", "sym", "linkdt", "linkenddt"]]


def load_customer_momentum(panel: Panel) -> pd.DataFrame:
    """Supplier score at month m = salecs-weighted mean of its matched
    customers' month-m returns (Cohen-Frazzini 2008: investors underreact to
    customer news; supplier drifts next month). Long high (direction +1)."""
    seg = pd.read_parquet(RAW / "seg_customer.parquet")
    seg = seg[(seg["ctype"] == "COMPANY") & seg["cnms"].notna()].copy()

    # customer name -> gvkey via normalized exact match against Compustat names
    funda = pd.read_parquet(RAW / "comp_funda.parquet")[["gvkey", "conm"]]
    names = funda.drop_duplicates()
    names["norm"] = _norm_name(names["conm"])
    names = names[names["norm"].str.len() > 2].drop_duplicates("norm", keep=False)

    seg["norm"] = _norm_name(seg["cnms"])
    m = seg.merge(names[["norm", "gvkey"]].rename(columns={"gvkey": "cust_gvkey"}),
                  on="norm", how="inner")
    match_rate = len(m) / max(len(seg), 1)
    logger.info("customer-name match: %d/%d rows (%.0f%%)",
                len(m), len(seg), 100 * match_rate)

    gs = _gvkey_to_sym()
    m = m.merge(gs.rename(columns={"gvkey": "cust_gvkey", "sym": "cust_sym"})
                [["cust_gvkey", "cust_sym", "linkdt", "linkenddt"]], on="cust_gvkey")
    m = m[(m["srcdate"] >= m["linkdt"]) & (m["srcdate"] <= m["linkenddt"])]
    m = m.merge(gs.rename(columns={"sym": "supp_sym"})
                [["gvkey", "supp_sym", "linkdt", "linkenddt"]], on="gvkey",
                suffixes=("", "_s"))
    m = m[(m["srcdate"] >= m["linkdt_s"]) & (m["srcdate"] <= m["linkenddt_s"])]

    links = m[["supp_sym", "cust_sym", "salecs", "srcdate"]].copy()
    links["w"] = links["salecs"].clip(lower=0).fillna(0) + 1e-9
    links["valid_from"] = links["srcdate"] + pd.DateOffset(months=6)
    links["valid_to"] = links["srcdate"] + pd.DateOffset(months=30)
    links = links[links["cust_sym"] != links["supp_sym"]]
    logger.info("customer-momentum links: %d (suppliers %d)",
                len(links), links["supp_sym"].nunique())

    ret = panel.monthly_ret
    out = pd.DataFrame(np.nan, index=ret.index, columns=ret.columns)
    for mth in ret.index:
        sub = links[(links["valid_from"] <= mth) & (links["valid_to"] >= mth)]
        if sub.empty:
            continue
        cret = ret.loc[mth]
        sub = sub.assign(cret=sub["cust_sym"].map(cret)).dropna(subset=["cret"])
        if sub.empty:
            continue
        sub["wc"] = sub["w"] * sub["cret"]
        agg = sub.groupby("supp_sym").agg(wc=("wc", "sum"), w=("w", "sum"))
        score = agg["wc"] / agg["w"]
        out.loc[mth, score.index.intersection(out.columns)] = score
    return out


def load_best_ideas(panel: Panel) -> pd.DataFrame:
    """# distinct 13F managers holding the stock among their top-3 positions
    (their 'best ideas', Cohen-Polk-Silli 2010), 45d filing lag."""
    top = pd.read_parquet(RAW / "tr13f_top10.parquet")
    top = top[top["rn"] <= 3]
    m = _map_on_cusip(top, "fdate")
    m["avail"] = m["fdate"] + pd.DateOffset(months=2) + pd.offsets.MonthEnd(0)
    g = (m.groupby(["avail", "sym"])["mgrno"].nunique().unstack()
           .reindex(panel.monthly_ret.index.union(
               m["avail"].unique()).sort_values())
           .ffill(limit=3)
           .reindex(index=panel.monthly_ret.index,
                    columns=panel.monthly_ret.columns))
    return g


def load_target_upside(panel: Panel) -> pd.DataFrame:
    """Trailing-90d mean 12-month price target / current price - 1
    (Brav-Lehavy 2003). Long high implied upside. Murat's 'sell near the
    target' instinct is the mirror read of the same variable."""
    tg = pd.read_parquet(RAW / "ibes_ptgdet.parquet")
    # horizon arrives as a STRING from WRDS ('12') — compare as str or get an
    # empty frame and a silent zero-month scan.
    tg = tg[(tg["horizon"].astype(str) == "12") & tg["value"].notna() & (tg["value"] > 0)]
    m = _map_on_cusip(tg, "anndats")
    m["month"] = m["anndats"] + pd.offsets.MonthEnd(0)
    monthly = (m.groupby(["month", "sym"])["value"].mean().unstack()
                 .reindex(index=panel.monthly_ret.index,
                          columns=panel.monthly_ret.columns))
    tgt90 = monthly.rolling(3, min_periods=1).mean()
    return tgt90 / panel.month_end_price - 1.0
