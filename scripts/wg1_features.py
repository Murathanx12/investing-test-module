"""WINNER-GENOME-1 — stage 2: point-in-time cross-sectional features.

Everything here is computed from data STRICTLY BEFORE the formation date T0.
`perturbation_proof()` in the runner checks that by corrupting every return
after T0 and requiring the pools to come back bit-identical.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ── Fama-French 12 industry definition (SIC ranges) ──────────────────────
FF12 = {
    "NoDur": [(100, 999), (2000, 2399), (2700, 2749), (2770, 2799),
              (3100, 3199), (3940, 3989)],
    "Durbl": [(2500, 2519), (2590, 2599), (3630, 3659), (3710, 3711),
              (3714, 3714), (3716, 3716), (3750, 3751), (3792, 3792),
              (3900, 3939), (3990, 3999)],
    "Manuf": [(2520, 2589), (2600, 2699), (2750, 2769), (3000, 3099),
              (3200, 3569), (3580, 3629), (3700, 3709), (3712, 3713),
              (3715, 3715), (3717, 3749), (3752, 3791), (3793, 3799),
              (3830, 3839), (3860, 3899)],
    "Enrgy": [(1200, 1399), (2900, 2999)],
    "Chems": [(2800, 2829), (2840, 2899)],
    "BusEq": [(3570, 3579), (3660, 3692), (3694, 3699), (3810, 3829),
              (7370, 7379)],
    "Telcm": [(4800, 4899)],
    "Utils": [(4900, 4949)],
    "Shops": [(5000, 5999), (7200, 7299), (7600, 7699)],
    "Hlth": [(2830, 2839), (3693, 3693), (3840, 3859), (8000, 8099)],
    "Money": [(6000, 6999)],
}
FF12_NAMES = list(FF12) + ["Other"]
#: the Drexel-2025 sub-arm: pharma + biological products + commercial biological
#: research. Defined by SIC directly, NOT by an FF12 bucket.
BIOTECH_SIC = [(2833, 2836), (8731, 8731)]


def ff12_of(siccd: np.ndarray) -> np.ndarray:
    """Map SIC codes to FF12 index (11 = Other)."""
    out = np.full(len(siccd), 11, dtype=np.int8)
    for k, (name, ranges) in enumerate(FF12.items()):
        m = np.zeros(len(siccd), dtype=bool)
        for lo, hi in ranges:
            m |= (siccd >= lo) & (siccd <= hi)
        out[m & (out == 11)] = k
    return out


def is_biotech(siccd: np.ndarray) -> np.ndarray:
    m = np.zeros(len(siccd), dtype=bool)
    for lo, hi in BIOTECH_SIC:
        m |= (siccd >= lo) & (siccd <= hi)
    return m


def pct_rank(x: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1); NaNs get NaN."""
    out = np.full(len(x), np.nan)
    ok = np.isfinite(x)
    n = int(ok.sum())
    if n == 0:
        return out
    order = np.argsort(x[ok], kind="mergesort")
    r = np.empty(n)
    r[order] = np.arange(n)
    out[ok] = r / n
    return out


class SicResolver:
    """siccd valid at a date, from crsp_stocknames name rows."""

    def __init__(self, path):
        sn = pd.read_parquet(path, columns=["permno", "namedt", "nameenddt",
                                            "siccd"])
        sn = sn.dropna(subset=["permno", "namedt"])
        sn["permno"] = sn["permno"].astype("int64")
        self.sn = sn.sort_values(["permno", "namedt"]).reset_index(drop=True)

    def at(self, t0: np.datetime64, permnos: np.ndarray) -> np.ndarray:
        ts = pd.Timestamp(t0)
        v = self.sn[(self.sn["namedt"] <= ts) &
                    (self.sn["nameenddt"].fillna(pd.Timestamp("2100-01-01"))
                     >= ts)]
        m = dict(zip(v["permno"].values, v["siccd"].values))
        return np.array([m.get(int(p), -1) for p in permnos], dtype=np.int32)


class QualityResolver:
    """ROE and debt/equity from Compustat annual, PIT with a 6-month lag on
    datadate, linked to permno through CCM (LC/LU primary links only)."""

    def __init__(self, funda_path, link_path, lag_months: int = 6):
        fu = pd.read_parquet(funda_path,
                             columns=["gvkey", "datadate", "ib", "ceq",
                                      "dlc", "dltt"])
        fu = fu.dropna(subset=["gvkey", "datadate"])
        for c in ("ib", "ceq", "dlc", "dltt"):
            fu[c] = pd.to_numeric(fu[c], errors="coerce")
        lk = pd.read_parquet(link_path)
        lk = lk[lk["linktype"].isin(["LC", "LU"]) &
                lk["linkprim"].isin(["P", "C"])].dropna(subset=["permno"])
        lk["permno"] = lk["permno"].astype("int64")
        lk["linkenddt"] = lk["linkenddt"].fillna(pd.Timestamp("2100-01-01"))

        m = fu.merge(lk[["gvkey", "permno", "linkdt", "linkenddt"]], on="gvkey")
        m = m[(m["datadate"] >= m["linkdt"]) & (m["datadate"] <= m["linkenddt"])]
        m["avail"] = m["datadate"] + pd.DateOffset(months=lag_months)
        ceq = m["ceq"].where(m["ceq"] > 0)
        m["roe"] = m["ib"] / ceq
        m["de"] = (m["dlc"].fillna(0) + m["dltt"].fillna(0)) / ceq
        m = m.dropna(subset=["roe", "de"])
        self.tbl = (m[["permno", "avail", "roe", "de"]]
                    .sort_values(["permno", "avail"]).reset_index(drop=True))

    def at(self, t0: np.datetime64, permnos: np.ndarray):
        ts = pd.Timestamp(t0)
        v = self.tbl[self.tbl["avail"] <= ts]
        v = v.drop_duplicates("permno", keep="last")
        m_roe = dict(zip(v["permno"].values, v["roe"].values))
        m_de = dict(zip(v["permno"].values, v["de"].values))
        roe = np.array([m_roe.get(int(p), np.nan) for p in permnos])
        de = np.array([m_de.get(int(p), np.nan) for p in permnos])
        return roe, de
