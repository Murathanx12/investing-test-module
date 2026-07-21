"""PIT-safe opportunistic-insider scorer — the promotable BRAIN-003 signal.

Signature matches aegis-finance's `pit_score_collector` closure:
    opportunistic_insider_score(ticker: str, as_of: str) -> float

Returns the count of DISTINCT opportunistic (non-routine, Cohen-Malloy-Pomorski)
open-market insider PURCHASES in that name over the trailing 12 months, using only
filings OBSERVABLE by `as_of` (filing_date <= as_of) — a conviction-intensity score.
0.0 when none / unmatched. Never raises.

Coverage: the bundled `data/insider_panel.parquet` spans 2006-2024 (SEC bulk files).
For LIVE dates beyond the panel, wire the score to the per-ticker live Form-4 feed
(aegis-finance `backend/services/insider_form4.py` + `classify_routine_opportunistic`)
— documented handoff, same classifier, same filing-date stamping.
"""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache

import pandas as pd

from aegis_brain.config import MODULE_ROOT

_PANEL = MODULE_ROOT / "data" / "insider_panel.parquet"


@lru_cache(maxsize=1)
def _panel() -> pd.DataFrame:
    if not _PANEL.exists():
        return pd.DataFrame()
    df = pd.read_parquet(_PANEL)
    df = df[df["is_classifiable"] & ~df["is_routine"]].copy()
    df["filing_date"] = pd.to_datetime(df["filing_date"])
    df["_tk"] = df["issuer_ticker"].astype(str).str.strip().str.upper()
    return df


def opportunistic_insider_score(ticker: str, as_of: str, lookback_days: int = 365) -> float:
    """Trailing-12mo count of distinct opportunistic insider buyers OBSERVABLE by as_of.

    Matches on the filing's own issuer ticker (robust — no permno round-trip). The
    backtest path uses the fully date-bounded permno join; this live scorer matches the
    ticker directly, which is what an aegis-finance collector passes."""
    df = _panel()
    if df.empty:
        return 0.0
    tk = str(ticker).strip().upper()
    asof = pd.Timestamp(as_of)
    lo = asof - timedelta(days=lookback_days)
    sub = df[(df["_tk"] == tk) & (df["filing_date"] <= asof) & (df["filing_date"] > lo)]
    return float(sub["rptowner_cik"].nunique())  # distinct opportunistic buyers = conviction
