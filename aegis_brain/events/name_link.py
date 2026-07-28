"""Point-in-time EDGAR-filer-name -> CRSP permno link.

Why name matching and not CIK: the WRDS pull this module holds carries NO cik
column anywhere (comp_funda / comp_funda_ext / pit_names_us / crsp_stocknames all
lack it), so there is no gvkey<-cik bridge on disk. The obvious shortcut —
SEC's `company_tickers.json` — maps CIK to ticker for filers that are CURRENT,
which silently drops exactly the names a distress study is about. Name matching
against `crsp_stocknames` is survivorship-neutral: CRSP keeps the historical name
rows of dead firms, and both sides are point-in-time (EDGAR's index carries the
filer name as of the filing; CRSP's comnam is date-bounded by namedt/nameenddt).

LIMITATION, reported not hidden: normalized-name matching is lossy in both
directions. Rows matching >1 permno inside the date window are DROPPED as
ambiguous and counted; unmatched filers are counted. The match rate is a reported
statistic of any run that uses this, never a silent filter.
"""

from __future__ import annotations

import re

import pandas as pd

from aegis_brain.config import MODULE_ROOT

_FAR_FUTURE = pd.Timestamp("2100-01-01")

# EDGAR appends state-of-incorporation / vintage tags; CRSP appends share-class
# and status tags. Neither is part of the company's identity.
_TAG_RE = re.compile(r"/[A-Z]{2,3}/?$|\\[A-Z]{2}\\?$")
_SUFFIXES = {
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "COMPANIES",
    "LTD", "LIMITED", "LLC", "LP", "PLC", "SA", "NV", "AG", "AB", "OY", "ASA",
    "THE", "NEW", "OLD", "DEL", "ADR", "ADS", "CL", "A", "B", "C", "SPONSORED",
    "COM", "CORPO", "CP", "HLDG", "HLDGS",
}
# Token-level spelling harmonisation (CRSP abbreviates aggressively).
_CANON = {
    "HOLDINGS": "HLD", "HOLDING": "HLD", "HOLDINGSS": "HLD",
    "INTERNATIONAL": "INTL", "INTL": "INTL",
    "TECHNOLOGIES": "TECH", "TECHNOLOGY": "TECH", "TECHNOLOGIE": "TECH",
    "INDUSTRIES": "IND", "INDUSTRIAL": "IND", "INDUSTRIES INC": "IND",
    "SERVICES": "SVC", "SERVICE": "SVC", "SVCS": "SVC", "SVC": "SVC",
    "SYSTEMS": "SYS", "SYSTEM": "SYS", "SYS": "SYS",
    "COMMUNICATIONS": "COMM", "COMMUNICATION": "COMM", "COMMUN": "COMM",
    "PHARMACEUTICALS": "PHARM", "PHARMACEUTICAL": "PHARM", "PHARMS": "PHARM",
    "RESOURCES": "RES", "RESOURCE": "RES",
    "FINANCIAL": "FIN", "FINL": "FIN", "FINANCE": "FIN",
    "BANCORPORATION": "BANCORP", "BANCORP": "BANCORP", "BANKSHARES": "BANCORP",
    "AND": "&",
    "PRODUCTS": "PROD", "PRODUCT": "PROD",
    "LABORATORIES": "LAB", "LABORATORY": "LAB", "LABS": "LAB", "LAB": "LAB",
    "ENTERPRISES": "ENTR", "ENTERPRISE": "ENTR",
    "PARTNERS": "PTNR", "PARTNER": "PTNR",
    "MANAGEMENT": "MGMT", "MGMT": "MGMT",
    "GROUP": "GRP", "GRP": "GRP",
}


def normalize_name(name: str) -> str:
    """Company name -> comparable key. Empty string means 'unusable'."""
    if not isinstance(name, str):
        return ""
    s = name.upper().strip()
    s = _TAG_RE.sub("", s).strip()
    s = re.sub(r"[^A-Z0-9&]+", " ", s)
    tokens = [_CANON.get(t, t) for t in s.split() if t]
    while tokens and tokens[-1] in _SUFFIXES:
        tokens.pop()
    while tokens and tokens[0] in {"THE"}:
        tokens.pop(0)
    tokens = [t for t in tokens if t not in {"&"}] or tokens
    return " ".join(tokens)


def crsp_name_windows() -> pd.DataFrame:
    """(name_key, permno, namedt, nameenddt) from CRSP's historical name rows."""
    sn = pd.read_parquet(
        MODULE_ROOT / "data" / "wrds_raw" / "crsp_stocknames.parquet",
        columns=["permno", "namedt", "nameenddt", "comnam"],
    ).dropna(subset=["permno", "comnam"])
    sn["permno"] = sn["permno"].astype(int)
    sn["namedt"] = pd.to_datetime(sn["namedt"])
    sn["nameenddt"] = pd.to_datetime(sn["nameenddt"]).fillna(_FAR_FUTURE)
    sn["name_key"] = sn["comnam"].map(normalize_name)
    sn = sn[sn["name_key"] != ""]
    return sn[["name_key", "permno", "namedt", "nameenddt"]].drop_duplicates()


def cik_permno_windows() -> pd.DataFrame:
    """(cik, permno, namedt, nameenddt) — the CIK<->permno bridge.

    Built by joining CRSP's historical name rows to EDGAR's `cik-lookup-data.txt`,
    which lists EVERY name a CIK has ever filed under (including former names).
    That makes the bridge rename-proof and survivorship-neutral: it is built from
    two historical registries, not from any 'currently listed' snapshot. Once a
    CIK is attached, filings join by exact identifier — the lossy name comparison
    happens once, offline, instead of per filing.
    """
    ed = pd.read_parquet(MODULE_ROOT / "data" / "events" / "cik_lookup.parquet")
    ed = ed[["name_key", "cik"]].drop_duplicates()
    sn = crsp_name_windows()
    out = sn.merge(ed, on="name_key", how="inner")
    return out[["cik", "permno", "namedt", "nameenddt"]].drop_duplicates()


def link_filings_by_cik(filings: pd.DataFrame, cik_col: str, date_col: str,
                        slack_days: int = 180) -> tuple[pd.DataFrame, dict]:
    """Attach `permno` to filings via the CIK bridge, date-bounded and unique.

    A filing is kept only when exactly ONE permno's name window (widened
    symmetrically by `slack_days`) covers its filing date. Filings whose CIK maps
    to several permnos at that moment are DROPPED as ambiguous and counted —
    never silently assigned to the first candidate.
    """
    f = filings.copy()
    f["_cik"] = f[cik_col].astype(int)
    f["_d"] = pd.to_datetime(f[date_col])
    f["_row"] = range(len(f))
    n_in = len(f)

    bridge = cik_permno_windows()
    slack = pd.Timedelta(days=slack_days)
    m = f.merge(bridge, left_on="_cik", right_on="cik", how="inner")
    m = m[(m["_d"] >= m["namedt"] - slack) & (m["_d"] <= m["nameenddt"] + slack)]

    nper = m.groupby("_row")["permno"].nunique()
    unique_rows = set(nper[nper == 1].index)
    n_ambiguous = int((nper > 1).sum())

    linked = (m[m["_row"].isin(unique_rows)]
              .drop_duplicates(subset=["_row"])
              .drop(columns=["namedt", "nameenddt", "cik"]))
    linked["permno"] = linked["permno"].astype(int)

    report = {
        "n_filings_in": int(n_in),
        "n_linked": int(len(linked)),
        "n_ambiguous_dropped": n_ambiguous,
        "n_unmatched": int(n_in - len(linked) - n_ambiguous),
        "match_rate": round(len(linked) / n_in, 4) if n_in else 0.0,
        "slack_days": slack_days,
    }
    return linked, report


def link_by_name(events: pd.DataFrame, name_col: str, date_col: str,
                 slack_days: int = 180) -> tuple[pd.DataFrame, dict]:
    """Attach `permno` to `events`. Returns (linked_rows, match_report).

    `slack_days` widens the CRSP name window on BOTH sides: CRSP stamps a name row
    from the date the name became effective in its own records, which can lag or
    lead an EDGAR filing made around a rename. Widening is symmetric, so it cannot
    manufacture a directional (look-ahead) advantage.
    """
    ev = events.copy()
    ev["name_key"] = ev[name_col].map(normalize_name)
    ev["_d"] = pd.to_datetime(ev[date_col])
    n_in = len(ev)
    ev = ev[ev["name_key"] != ""]

    windows = crsp_name_windows()
    slack = pd.Timedelta(days=slack_days)
    merged = ev.merge(windows, on="name_key", how="left")
    in_window = (merged["_d"] >= merged["namedt"] - slack) & \
                (merged["_d"] <= merged["nameenddt"] + slack)
    merged = merged[in_window | merged["permno"].isna()]

    # An event row is usable only if the window match is UNIQUE.
    key = merged.index.name or "index"
    counts = merged.groupby(merged.index)["permno"].nunique(dropna=True)
    unique_idx = counts[counts == 1].index
    ambiguous_idx = counts[counts > 1].index

    linked = merged.loc[merged.index.isin(unique_idx)].drop_duplicates(
        subset=[c for c in merged.columns if c != "permno"] + ["permno"])
    linked = linked[linked["permno"].notna()].copy()
    linked["permno"] = linked["permno"].astype(int)

    report = {
        "n_events_in": int(n_in),
        "n_name_usable": int(len(ev)),
        "n_linked": int(len(linked)),
        "n_ambiguous_dropped": int(len(ambiguous_idx)),
        "n_unmatched": int(n_in - len(linked) - len(ambiguous_idx)),
        "match_rate": round(len(linked) / n_in, 4) if n_in else 0.0,
        "slack_days": slack_days,
        "_key": key,
    }
    return linked.drop(columns=["namedt", "nameenddt"]), report
