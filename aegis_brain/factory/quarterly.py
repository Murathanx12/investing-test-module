"""Quarterly PIT store — comp_fundq characteristics anchored at rdq.

Unlike the annual FundStore (datadate + 6-month lag), quarterly data carries
its actual report date (`rdq`): a value becomes available at the END of the
rdq month (conservative: a mid-month report is usable the following month
via the scan's month-end formation) and goes stale after STALE_Q months.

Characteristics built here (each a [month x permno] wide frame):
  roe_q       ibq / lagged ceqq (4q prior book)
  roa_mom     roa_q minus roa_q four quarters prior (fundamental momentum)
  earn_stab   NEGATIVE stdev of roe_q over trailing 20 quarters (>=12 req'd)
              — higher = more stable, so direction +1 means long-stable
  earn_accel  change in EPS growth: (eps_q - eps_{q-4}) - (eps_{q-1} - eps_{q-5}),
              scaled by price at the prior quarter (He-Narayanamoorthy 2020)
  ea_shift    earnings-announcement-date advance: (prior-year same-quarter rdq
              day-of-year) - (this rdq day-of-year); positive = ADVANCED
              schedule = good news (Johnson-So 2018), computed from rdq only
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel

logger = logging.getLogger(__name__)
RAW = MODULE_ROOT / "data" / "wrds_raw"
STALE_Q_MONTHS = 6
_FAR_FUTURE = pd.Timestamp("2262-01-01")


def _gvkey_permno() -> pd.DataFrame:
    link = pd.read_parquet(RAW / "ccm_link.parquet").dropna(subset=["permno", "gvkey"])
    link["gvkey"] = link["gvkey"].astype(str).str.strip()
    link["sym"] = link["permno"].astype("Int64").astype(str)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"]).fillna(_FAR_FUTURE)
    return link[["gvkey", "sym", "linkdt", "linkenddt"]]


def _quarterly_chars() -> pd.DataFrame:
    """Long frame: (gvkey, rdq, roe_q, roa_q, roa_mom, earn_stab), PIT at rdq."""
    q = pd.read_parquet(RAW / "comp_fundq.parquet",
                        columns=["gvkey", "datadate", "rdq", "ibq", "ceqq", "atq",
                                 "epspxq", "prccq"])
    q = q.dropna(subset=["gvkey", "datadate", "rdq"]).copy()
    q["gvkey"] = q["gvkey"].astype(str).str.strip()
    q["datadate"] = pd.to_datetime(q["datadate"])
    q["rdq"] = pd.to_datetime(q["rdq"])
    q = q.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="last")

    g = q.groupby("gvkey", sort=False)
    q["ceqq_lag4"] = g["ceqq"].shift(4)
    q["roe_q"] = q["ibq"] / q["ceqq_lag4"].where(q["ceqq_lag4"] > 0)
    q["roa_q"] = q["ibq"] / q["atq"].where(q["atq"] > 0)
    q["roa_mom"] = q["roa_q"] - g["roa_q"].shift(4)
    # trailing 20-quarter stability of ROE (min 12 obs), negated: stable = high
    q["earn_stab"] = -(g["roe_q"].transform(
        lambda s: s.rolling(20, min_periods=12).std()))
    # earnings acceleration: change in yoy EPS growth, price-scaled (H-N 2020)
    eg = q["epspxq"] - g["epspxq"].shift(4)
    q["earn_accel"] = (eg - eg.groupby(q["gvkey"]).shift(1)) / \
        g["prccq"].shift(1).where(g["prccq"].shift(1) > 0)
    # announcement-date advance vs same quarter last year (Johnson-So 2018):
    # positive = reports EARLIER than a year ago = good-news signal
    rdq_lag4 = g["rdq"].shift(4)
    q["ea_shift"] = (rdq_lag4.dt.dayofyear - q["rdq"].dt.dayofyear).astype(float)
    q.loc[q["ea_shift"].abs() > 60, "ea_shift"] = np.nan  # fiscal-change noise guard
    # guard the winsor tails — tiny lagged book blows roe_q up
    for c in ("roe_q", "roa_mom", "earn_stab", "earn_accel"):
        lo, hi = q[c].quantile([0.005, 0.995])
        q[c] = q[c].clip(lo, hi)
    return q[["gvkey", "rdq", "roe_q", "roa_mom", "earn_stab", "earn_accel", "ea_shift"]]


class QuarterlyStore:
    """[month x permno] frames per quarterly characteristic, PIT at rdq."""

    CHARS = ("roe_q", "roa_mom", "earn_stab", "earn_accel", "ea_shift")

    def __init__(self, panel: Panel):
        chars = _quarterly_chars()
        link = _gvkey_permno()
        m = chars.merge(link, on="gvkey")
        m = m[(m["rdq"] >= m["linkdt"]) & (m["rdq"] <= m["linkenddt"])]
        m = m[m["sym"].isin(panel.monthly_ret.columns)]
        m["avail_month"] = m["rdq"].dt.to_period("M").dt.to_timestamp("M")
        idx = panel.monthly_ret.index
        self.frames: dict[str, pd.DataFrame] = {}
        for c in self.CHARS:
            wide = (m.pivot_table(index="avail_month", columns="sym",
                                  values=c, aggfunc="last")
                    .reindex(idx.union(m["avail_month"].unique()).sort_values())
                    .ffill(limit=STALE_Q_MONTHS)
                    .reindex(index=idx, columns=panel.monthly_ret.columns))
            self.frames[c] = wide
        cov = self.frames["roe_q"].notna().sum(axis=1)
        logger.info("QuarterlyStore: mean monthly coverage %.0f names", cov.mean())

    def get(self, name: str) -> pd.DataFrame:
        return self.frames[name]
