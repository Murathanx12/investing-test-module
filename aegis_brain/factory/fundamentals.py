"""PIT-safe fundamentals store for factory batch 2.

Maps annual Compustat (comp_funda) characteristics onto the CRSP panel's
(month × permno) grid:

  - gvkey → permno via the CCM link (LC/LU linktypes; primary links preferred;
    link must cover datadate).
  - A fiscal year ending at `datadate` becomes USABLE at month-end
    datadate + REPORTING_LAG_MONTHS (6 — the standard conservative annual-data
    convention; Compustat preliminary filings arrive earlier, but 6 months is
    unimpeachably PIT).
  - Values persist (ffill) for at most STALE_LIMIT_MONTHS (18) so a dead or
    non-filing firm drops out instead of carrying stale fundamentals forever.

Everything is computed once into a FundStore of wide frames aligned to the
panel index/columns; batch-2 signals are cheap lookups on top.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel

logger = logging.getLogger(__name__)

REPORTING_LAG_MONTHS = 6
STALE_LIMIT_MONTHS = 18

RAW = MODULE_ROOT / "data" / "wrds_raw"


def _book_equity(f: pd.DataFrame) -> pd.Series:
    """Fama-French book equity: SEQ (fallback CEQ+PSTK? -> CEQ) + TXDITC - PSTK."""
    seq = f["seq"].fillna(f["ceq"])
    return seq + f["txditc"].fillna(0.0) - f["pstk"].fillna(0.0)


def load_characteristics(funda_path=None, link_path=None) -> pd.DataFrame:
    """Per (permno, datadate) characteristic rows with availability month."""
    f = pd.read_parquet(funda_path or RAW / "comp_funda.parquet")
    link = pd.read_parquet(link_path or RAW / "ccm_link.parquet")

    f = f.sort_values(["gvkey", "datadate"]).reset_index(drop=True)
    g = f.groupby("gvkey")

    be = _book_equity(f)
    at_lag = g["at"].shift(1)
    be_lag = be.groupby(f["gvkey"]).shift(1)

    out = pd.DataFrame({
        "gvkey": f["gvkey"], "datadate": f["datadate"],
        # Novy-Marx gross profitability
        "gross_prof": (f["gp"].fillna(f["revt"] - f["cogs"])) / f["at"],
        # FF operating profitability (rev - cogs - sga) / book equity
        "oper_prof": (f["revt"] - f["cogs"].fillna(0) - f["xsga"].fillna(0))
                      / be.where(be > 0),
        "asset_growth": f["at"] / at_lag.where(at_lag > 0) - 1.0,
        # cash-flow accruals (Sloan-style, statement-of-cash-flows version)
        "accruals_cf": (f["ib"] - f["oancf"]) / f["at"].where(f["at"] > 0),
        "net_issuance": np.log(f["csho"] / g["csho"].shift(1)),
        "btm": be.where(be > 0) / (f["prcc_f"] * f["csho"]).where(
            (f["prcc_f"] * f["csho"]) > 0),
        "roe": f["ib"] / be_lag.where(be_lag > 0),
        "cash_prof": f["oancf"] / f["at"].where(f["at"] > 0),
        "capx_at": f["capx"] / f["at"].where(f["at"] > 0),
    })

    # F-score-lite (0-9, Piotroski flavor from annual data)
    roa = f["ib"] / f["at"].where(f["at"] > 0)
    d_roa = roa - roa.groupby(f["gvkey"]).shift(1)
    lev = f["dltt"] / f["at"].where(f["at"] > 0)
    d_lev = lev - lev.groupby(f["gvkey"]).shift(1)
    cr = f["act"] / f["lct"].where(f["lct"] > 0)
    d_cr = cr - cr.groupby(f["gvkey"]).shift(1)
    gm = (f["revt"] - f["cogs"]) / f["revt"].where(f["revt"] > 0)
    d_gm = gm - gm.groupby(f["gvkey"]).shift(1)
    at_turn = f["revt"] / f["at"].where(f["at"] > 0)
    d_turn = at_turn - at_turn.groupby(f["gvkey"]).shift(1)
    out["fscore_lite"] = (
        (f["ib"] > 0).astype(float) + (f["oancf"] > 0).astype(float)
        + (f["oancf"] > f["ib"]).astype(float) + (d_roa > 0).astype(float)
        + (d_lev < 0).astype(float) + (d_cr > 0).astype(float)
        + (out["net_issuance"] <= 0).astype(float) + (d_gm > 0).astype(float)
        + (d_turn > 0).astype(float)
    ).where(f["ib"].notna() & f["oancf"].notna())

    # gvkey -> permno (primary links first, link window must cover datadate)
    link = link.dropna(subset=["permno"]).copy()
    link["linkenddt"] = link["linkenddt"].fillna(pd.Timestamp("2262-01-01"))
    m = out.merge(link[["gvkey", "permno", "linkprim", "linkdt", "linkenddt"]],
                  on="gvkey", how="inner")
    m = m[(m["datadate"] >= m["linkdt"]) & (m["datadate"] <= m["linkenddt"])]
    m["prim"] = (m["linkprim"] == "P").astype(int)
    m = (m.sort_values(["permno", "datadate", "prim"])
           .drop_duplicates(["permno", "datadate"], keep="last"))
    m["sym"] = m["permno"].astype(int).astype(str)
    m["avail_month"] = (m["datadate"] + pd.DateOffset(months=REPORTING_LAG_MONTHS)
                        ) + pd.offsets.MonthEnd(0)
    logger.info("characteristics: %d firm-years matched to %d permnos",
                len(m), m["sym"].nunique())
    return m.drop(columns=["gvkey", "linkprim", "linkdt", "linkenddt", "prim",
                           "permno"])


CHARACTERISTICS = ["gross_prof", "oper_prof", "asset_growth", "accruals_cf",
                   "net_issuance", "btm", "roe", "cash_prof", "capx_at",
                   "fscore_lite"]


class FundStore:
    """Wide (panel-month × permno) frames per characteristic, PIT-aligned."""

    def __init__(self, panel: Panel, chars: pd.DataFrame | None = None):
        chars = chars if chars is not None else load_characteristics()
        chars = chars[chars["sym"].isin(panel.monthly_ret.columns)]
        idx = panel.monthly_ret.index
        self.frames: dict[str, pd.DataFrame] = {}
        for c in CHARACTERISTICS:
            wide = (chars.pivot_table(index="avail_month", columns="sym",
                                      values=c, aggfunc="last")
                    .reindex(idx.union(chars["avail_month"].unique()).sort_values())
                    .ffill(limit=STALE_LIMIT_MONTHS)
                    .reindex(index=idx, columns=panel.monthly_ret.columns))
            self.frames[c] = wide
        cov = self.frames["gross_prof"].notna().sum(axis=1)
        logger.info("FundStore built: mean monthly coverage %.0f names "
                    "(min %d, max %d)", cov.mean(), cov.min(), cov.max())

    def get(self, name: str) -> pd.DataFrame:
        return self.frames[name]
