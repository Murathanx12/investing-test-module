"""Point-in-time issuer-ticker -> CRSP permno mapping, built OFFLINE from data we
already have (Compustat `tic`+`gvkey` and the CRSP-Compustat link), so an event
study can join to the paper-grade CRSP panel without another WRDS pull.

Path: issuer TICKER  --(comp_funda: tic->gvkey)-->  gvkey
                     --(ccm_link: gvkey->permno, date-bounded)-->  permno,
keeping only the permno whose CCM link window covers the filing date.

LIMITATION (reported, not hidden): ticker-based matching is lossy — tickers get
reused across firms over time, and Compustat `tic` is a coarse (annual, point-in-time-ish)
identifier. The date-bounded CCM link removes most ambiguity; rows that still map to >1
permno are DROPPED as ambiguous and counted. A cleaner CIK->gvkey bridge (a small
`comp.company` pull) would raise the match rate — a documented future upgrade.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT

RAW = MODULE_ROOT / "data" / "wrds_raw"
_FAR_FUTURE = pd.Timestamp("2100-01-01")


def _link_table() -> pd.DataFrame:
    """(ticker_upper, permno, linkdt, linkenddt) — every ticker a gvkey ever used,
    crossed with that gvkey's date-bounded CRSP permno link."""
    funda = pd.read_parquet(RAW / "comp_funda.parquet", columns=["gvkey", "tic"])
    ccm = pd.read_parquet(RAW / "ccm_link.parquet",
                          columns=["gvkey", "permno", "linkdt", "linkenddt"])
    funda = funda.dropna(subset=["tic", "gvkey"]).copy()
    funda["gvkey"] = funda["gvkey"].astype(str).str.strip()
    funda["ticker_u"] = funda["tic"].astype(str).str.strip().str.upper()
    pairs = funda[["gvkey", "ticker_u"]].drop_duplicates()

    ccm = ccm.dropna(subset=["gvkey", "permno"]).copy()
    ccm["gvkey"] = ccm["gvkey"].astype(str).str.strip()
    ccm["permno"] = ccm["permno"].astype(int)
    ccm["linkdt"] = pd.to_datetime(ccm["linkdt"])
    ccm["linkenddt"] = pd.to_datetime(ccm["linkenddt"]).fillna(_FAR_FUTURE)

    link = pairs.merge(ccm, on="gvkey", how="inner")
    return link[["ticker_u", "permno", "linkdt", "linkenddt"]]


def _cusip_link_table() -> pd.DataFrame:
    """(cusip8, permno, linkdt, linkenddt) — Compustat 8-digit CUSIP stem crossed with
    the date-bounded CRSP permno link. IBES/Compustat carry CUSIP, so this is the join
    path for earnings/estimate events (which have no clean ticker)."""
    funda = pd.read_parquet(RAW / "comp_funda.parquet", columns=["gvkey", "cusip"])
    ccm = pd.read_parquet(RAW / "ccm_link.parquet",
                          columns=["gvkey", "permno", "linkdt", "linkenddt"])
    funda = funda.dropna(subset=["cusip", "gvkey"]).copy()
    funda["gvkey"] = funda["gvkey"].astype(str).str.strip()
    funda["cusip8"] = funda["cusip"].astype(str).str.strip().str.upper().str[:8]
    pairs = funda[["gvkey", "cusip8"]].drop_duplicates()
    ccm = ccm.dropna(subset=["gvkey", "permno"]).copy()
    ccm["gvkey"] = ccm["gvkey"].astype(str).str.strip()
    ccm["permno"] = ccm["permno"].astype(int)
    ccm["linkdt"] = pd.to_datetime(ccm["linkdt"])
    ccm["linkenddt"] = pd.to_datetime(ccm["linkenddt"]).fillna(_FAR_FUTURE)
    link = pairs.merge(ccm, on="gvkey", how="inner")
    return link[["cusip8", "permno", "linkdt", "linkenddt"]]


def attach_permno_by_cusip(df: pd.DataFrame, cusip_col: str,
                           date_col: str) -> tuple[pd.DataFrame, dict]:
    """Add `permno` via PIT 8-digit-CUSIP matching (for IBES/Compustat events).
    Ambiguous rows (>1 permno for cusip+date) get permno=NA and are counted."""
    d = df.copy()
    d["_c8"] = d[cusip_col].astype(str).str.strip().str.upper().str[:8]
    d["_dt"] = pd.to_datetime(d[date_col])
    d["_row"] = np.arange(len(d))
    link = _cusip_link_table()
    m = d[["_row", "_c8", "_dt"]].merge(link, left_on="_c8", right_on="cusip8", how="left")
    cov = m[(m["_dt"] >= m["linkdt"]) & (m["_dt"] <= m["linkenddt"])]
    per = cov.groupby("_row")["permno"].nunique()
    uniq = per[per == 1].index
    resolved = cov[cov["_row"].isin(uniq)].drop_duplicates("_row")[["_row", "permno"]]
    d = d.merge(resolved, on="_row", how="left")
    diag = {"n": int(len(d)), "matched": int(d["permno"].notna().sum()),
            "match_rate": round(float(d["permno"].notna().mean()), 3),
            "ambiguous_dropped": int((per > 1).sum())}
    d["permno"] = d["permno"].astype("Int64")
    return d.drop(columns=["_c8", "_dt", "_row"]), diag


def attach_permno(purchases: pd.DataFrame, ticker_col: str = "issuer_ticker",
                  date_col: str = "filing_date") -> tuple[pd.DataFrame, dict]:
    """Add a `permno` column to an insider-purchase frame via PIT ticker matching.
    Returns (frame_with_permno_where_matched, diagnostics). Ambiguous (>1 permno for
    a row's ticker+date) rows get permno=NA and are counted, not silently resolved."""
    df = purchases.copy()
    df["_ticker_u"] = df[ticker_col].astype(str).str.strip().str.upper()
    df["_fdate"] = pd.to_datetime(df[date_col])
    df["_row"] = np.arange(len(df))

    link = _link_table()
    m = df[["_row", "_ticker_u", "_fdate"]].merge(
        link, left_on="_ticker_u", right_on="ticker_u", how="left")
    # keep candidate links whose window covers the filing date
    covered = m[(m["_fdate"] >= m["linkdt"]) & (m["_fdate"] <= m["linkenddt"])]
    per_row = covered.groupby("_row")["permno"].nunique()
    unique_rows = per_row[per_row == 1].index
    ambiguous_rows = per_row[per_row > 1].index

    resolved = (covered[covered["_row"].isin(unique_rows)]
                .drop_duplicates("_row")[["_row", "permno"]])
    df = df.merge(resolved, on="_row", how="left")

    diag = {
        "n_purchases": int(len(df)),
        "matched": int(df["permno"].notna().sum()),
        "match_rate": round(float(df["permno"].notna().mean()), 3),
        "ambiguous_dropped": int(len(ambiguous_rows)),
        "unmatched": int(df["permno"].isna().sum()) - int(len(ambiguous_rows)),
    }
    df["permno"] = df["permno"].astype("Int64")
    return df.drop(columns=["_ticker_u", "_fdate", "_row"]), diag
