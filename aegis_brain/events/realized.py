"""Forward realized-return provider for the calibration ledger (yfinance-backed).

The ledger scores a call ONLY when its horizon has fully elapsed AND price data is
available; otherwise the call stays pending (never a faux-0). This module supplies the
`realized_fn(ticker, event_date, horizon_days) -> float | None` the ledger expects:
the market-adjusted (vs SPY) cumulative return over the `horizon_days` trading days
after the event. Returns None if not yet matured or data missing — the honest "pending".

Forward use only. yfinance is a LIVE source (today's prices), which is exactly what a
forward ledger needs — it is never used to backtest historical LLM calls.
"""

from __future__ import annotations

import datetime as _dt
from functools import lru_cache

import pandas as pd

_BENCH = "SPY"


def _as_date(d) -> _dt.date:
    if isinstance(d, _dt.date):
        return d
    return pd.Timestamp(d).date()


@lru_cache(maxsize=256)
def _closes(ticker: str, start: str, end: str) -> pd.Series:
    import yfinance as yf

    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    close = df["Close"]
    if isinstance(close, pd.DataFrame):  # yfinance sometimes returns a 1-col frame
        close = close.iloc[:, 0]
    return close.dropna()


def market_adjusted_forward_return(ticker: str, event_date, horizon_days: int) -> float | None:
    """Stock minus SPY cumulative return over `horizon_days` TRADING days starting the
    first session on/after event_date. None if the window hasn't fully elapsed or data
    is missing (→ the ledger keeps the call pending)."""
    ev = _as_date(event_date)
    # pad the fetch window generously for weekends/holidays; require horizon+slack sessions.
    start = (ev - _dt.timedelta(days=5)).isoformat()
    end = (ev + _dt.timedelta(days=horizon_days * 2 + 15)).isoformat()
    px = _closes(ticker, start, end)
    spy = _closes(_BENCH, start, end)
    if px.empty or spy.empty:
        return None
    px = px[px.index.date >= ev]
    spy = spy[spy.index.date >= ev]
    if len(px) < horizon_days + 1 or len(spy) < horizon_days + 1:
        return None  # not yet matured (or thin data) → pending
    stock_ret = float(px.iloc[horizon_days] / px.iloc[0] - 1.0)
    bench_ret = float(spy.iloc[horizon_days] / spy.iloc[0] - 1.0)
    return stock_ret - bench_ret


# The callable the ledger consumes: signature (ticker, event_date, horizon_days).
realized_fn = market_adjusted_forward_return
