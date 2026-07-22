"""Alt-data stores for factory batch 3a — wide (month × permno) frames from the
2026-07-22 WRDS/congress harvest, PIT-lagged where the source requires it.

PIT conventions (stated here, tested in tests/test_altstores.py):
  - dsf monthly aggregates: computed FROM month m's daily data → usable at
    month-end m (no extra lag).
  - short interest: settlement datadate → usable at that month-end.
  - 13F holdings: fdate is quarter-end but filings arrive up to 45 days later
    → usable at fdate + 2 months.
  - IBES recdsum: statpers is the summary compute date → usable at that
    month-end.
  - congress (senate archive): transaction_date + 45 days (the STOCK Act
    disclosure allowance; the archive lacks reliable disclosure dates).
"""

from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel

logger = logging.getLogger(__name__)

RAW = MODULE_ROOT / "data" / "wrds_raw"
CONGRESS = MODULE_ROOT / "data" / "congress"


def _pivot_to_panel(df: pd.DataFrame, val: str, panel: Panel,
                    when: str = "month") -> pd.DataFrame:
    wide = df.pivot_table(index=when, columns="sym", values=val, aggfunc="last")
    return wide.reindex(index=panel.monthly_ret.index,
                        columns=panel.monthly_ret.columns)


def load_daily_agg(panel: Panel) -> dict[str, pd.DataFrame]:
    """{'vol_d','max_dret','amihud_d'} monthly frames from real daily data."""
    df = pd.read_parquet(RAW / "dsf_monthly_agg.parquet")
    df = df[df["n_days"] >= 15]                     # thin months are noise
    df["sym"] = df["permno"].astype(int).astype(str)
    # WRDS date_trunc arrives tz-aware with DST-shifted clock times (01:00
    # -0400) — strip tz THEN snap to month-end or nothing aligns to the panel.
    df["month"] = (df["month"].dt.tz_localize(None)
                   .dt.to_period("M").dt.to_timestamp("M"))
    return {v: _pivot_to_panel(df, v, panel) for v in ("vol_d", "max_dret", "amihud_d")}


def _ncusip_map() -> pd.DataFrame:
    nm = pd.read_parquet(RAW / "crsp_stocknames.parquet")
    nm = nm[nm["ncusip"].notna()].copy()
    nm["sym"] = nm["permno"].astype("Int64").astype(str)
    nm["nameenddt"] = nm["nameenddt"].fillna(pd.Timestamp("2262-01-01"))
    return nm[["sym", "ncusip", "ticker", "namedt", "nameenddt"]]


def _map_on_cusip(df: pd.DataFrame, datecol: str) -> pd.DataFrame:
    """Attach sym via 8-char ncusip with date-valid name records."""
    nm = _ncusip_map()
    df = df.copy()
    df["ncusip"] = df["cusip"].astype(str).str[:8]
    m = df.merge(nm, on="ncusip", how="inner")
    m = m[(m[datecol] >= m["namedt"]) & (m[datecol] <= m["nameenddt"])]
    return m


def load_short_interest_chg(panel: Panel) -> pd.DataFrame:
    """log(SI / SI 3m ago) — rising short interest is bearish (long falling)."""
    si = pd.read_parquet(RAW / "short_interest.parquet")
    link = pd.read_parquet(RAW / "ccm_link.parquet").dropna(subset=["permno"])
    link["linkenddt"] = link["linkenddt"].fillna(pd.Timestamp("2262-01-01"))
    m = si.merge(link[["gvkey", "permno", "linkdt", "linkenddt"]], on="gvkey")
    m = m[(m["datadate"] >= m["linkdt"]) & (m["datadate"] <= m["linkenddt"])]
    m["sym"] = m["permno"].astype("Int64").astype(str)
    m["month"] = m["datadate"] + pd.offsets.MonthEnd(0)
    m["si"] = m["shortintadj"].fillna(m["shortint"])
    wide = (m.pivot_table(index="month", columns="sym", values="si", aggfunc="last")
            .reindex(index=panel.monthly_ret.index,
                     columns=panel.monthly_ret.columns))
    wide = wide.where(wide > 0)
    return np.log(wide / wide.shift(3))


def load_breadth_chg(panel: Panel) -> pd.DataFrame:
    """Quarterly change in # institutions holding (Chen-Hong-Stein), 45d lag."""
    ow = pd.read_parquet(RAW / "tr13f_ownership.parquet")
    m = _map_on_cusip(ow, "fdate")
    m["avail"] = m["fdate"] + pd.DateOffset(months=2) + pd.offsets.MonthEnd(0)
    q = (m.groupby(["sym", "fdate"], as_index=False)
           .agg(n_inst=("n_inst", "max"), avail=("avail", "max"))
           .sort_values(["sym", "fdate"]))
    q["chg"] = q.groupby("sym")["n_inst"].diff()
    wide = (q.pivot_table(index="avail", columns="sym", values="chg", aggfunc="last")
            .reindex(panel.monthly_ret.index.union(q["avail"].unique()).sort_values())
            .ffill(limit=3)
            .reindex(index=panel.monthly_ret.index,
                     columns=panel.monthly_ret.columns))
    return wide


def load_rec_momentum(panel: Panel) -> pd.DataFrame:
    """(upgrades - downgrades) / #recs from the IBES monthly summary."""
    rec = pd.read_parquet(RAW / "ibes_recdsum.parquet")
    rec = rec[rec["numrec"].fillna(0) > 0]
    m = _map_on_cusip(rec, "statpers")
    m["month"] = m["statpers"] + pd.offsets.MonthEnd(0)
    m["recmom"] = (m["numup"].fillna(0) - m["numdown"].fillna(0)) / m["numrec"]
    return _pivot_to_panel(m, "recmom", panel)


def load_congress_buys(panel: Panel) -> pd.DataFrame:
    """# distinct senators with a disclosed Purchase, trailing 3 months, PIT at
    transaction_date + 45 days. Coverage starts ~2013 (STOCK Act archives)."""
    path = CONGRESS / "senate-stock-watcher-data" / "aggregate" / "all_transactions.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame(rows)
    df = df[df["type"].str.contains("Purchase", case=False, na=False)]
    df = df[df["ticker"].notna() & (df["ticker"] != "--")]
    df["ticker"] = df["ticker"].str.upper().str.strip()
    df["tdate"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df.dropna(subset=["tdate"])
    df["avail"] = df["tdate"] + pd.Timedelta(days=45)
    df["month"] = df["avail"] + pd.offsets.MonthEnd(0)

    nm = _ncusip_map()
    m = df.merge(nm[["sym", "ticker", "namedt", "nameenddt"]], on="ticker")
    m = m[(m["tdate"] >= m["namedt"]) & (m["tdate"] <= m["nameenddt"])]
    g = (m.groupby(["month", "sym"])["senator"].nunique()
           .unstack().reindex(index=panel.monthly_ret.index,
                              columns=panel.monthly_ret.columns))
    return g.fillna(0.0).rolling(3, min_periods=1).sum()


def insider_flag_12m(panel: Panel) -> pd.DataFrame:
    """Opportunistic-insider filing in trailing 12 months (BRAIN-003's member)."""
    ins = pd.read_parquet(MODULE_ROOT / "data" / "insider_panel.parquet")
    ins = ins[ins["permno"].notna() & ins["is_classifiable"] & ~ins["is_routine"]].copy()
    ins["month"] = ins["filing_date"].dt.to_period("M").dt.to_timestamp("M")
    ins["sym"] = ins["permno"].astype("Int64").astype(str)
    g = (ins.groupby(["month", "sym"]).size().unstack()
            .reindex(index=panel.monthly_ret.index,
                     columns=panel.monthly_ret.columns))
    return (g.fillna(0.0).rolling(12, min_periods=1).sum() > 0).astype(float)


def gemini_score(panel: Panel, congress: pd.DataFrame,
                 insider: pd.DataFrame) -> pd.DataFrame:
    """Gemini's literal point score (INSTR-GEMINI-SCORE): +5 for a >=40%
    drawdown from the 12m high, +10 for an insider flag, +10 for a congress
    buy. The 'LLM narrative +5' component is omitted (no PIT historical
    narrative exists) — documented, not silently approximated."""
    p = panel.month_end_price
    dd = 1.0 - p / p.rolling(12, min_periods=6).max()
    return ((dd >= 0.40).astype(float) * 5.0
            + insider * 10.0
            + (congress > 0).astype(float) * 10.0)
