"""Offline tests for the LLM perception layer and the forward realized-return provider.

Network-touching functions (DeepSeek chat, yfinance download) are NOT called here —
we test the deterministic pieces: entity-neutering, and the maturity/adjustment logic
of the realized-return function (with a synthetic price source injected).
"""

from __future__ import annotations

import pandas as pd
import pytest

from aegis_brain.llm.event_call import neuter
from aegis_brain.events import realized


def test_neuter_strips_years_and_dates():
    out = neuter("Drug approved in 2023, decision on 04/15/2023.")
    assert "2023" not in out
    assert "[YEAR]" in out and "[DATE]" in out


def _series(start: str, rets):
    """Build a daily close series from a start date and a list of daily returns."""
    idx = pd.bdate_range(start=start, periods=len(rets) + 1)
    px = [100.0]
    for r in rets:
        px.append(px[-1] * (1 + r))
    return pd.Series(px, index=idx)


def test_realized_none_before_maturity(monkeypatch):
    # only 5 sessions of data but horizon is 21 -> not matured -> None
    monkeypatch.setattr(realized, "_closes",
                        lambda t, s, e: _series("2026-06-01", [0.01] * 5))
    assert realized.market_adjusted_forward_return("X", "2026-06-01", 21) is None


def test_realized_market_adjusted_when_matured(monkeypatch):
    def fake_closes(ticker, start, end):
        if ticker == "SPY":
            return _series("2026-06-01", [0.0] * 25)          # flat market
        return _series("2026-06-01", [0.005] * 25)            # stock drifts up
    monkeypatch.setattr(realized, "_closes", fake_closes)
    r = realized.market_adjusted_forward_return("X", "2026-06-01", 21)
    assert r is not None
    # stock compounded 0.5%/day for 21 days, market flat -> ~ +11% abnormal
    assert r == pytest.approx((1.005 ** 21) - 1.0, rel=1e-6)


def test_realized_none_on_missing_data(monkeypatch):
    monkeypatch.setattr(realized, "_closes", lambda t, s, e: pd.Series(dtype=float))
    assert realized.market_adjusted_forward_return("X", "2026-06-01", 21) is None
