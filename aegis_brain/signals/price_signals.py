"""Baseline price signals — the GKX 'big three' families.

Gu-Kelly-Xiu (2020): momentum, liquidity, and volatility dominate the 900+
signal zoo. These are the direction-check backbone the combiner starts from;
event signals (insider, PEAD, FDA) join as L1/L2 collectors come online.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.signals.base import Signal


def momentum_12_1(panel: Panel) -> pd.DataFrame:
    """Cumulative return months t-11..t-1, skipping the most recent month.

    Value at row t uses monthly returns up to and including month t, excluding
    month t itself (the classic 12-1 skip avoids short-term reversal bleed).
    """
    r = panel.monthly_ret
    log1p = np.log1p(r)
    # sum of log returns over t-11..t-1 == rolling(11) ending at t-1 == shift(1)
    mom = log1p.rolling(11, min_periods=8).sum().shift(1)
    return np.expm1(mom)


def short_term_reversal(panel: Panel) -> pd.DataFrame:
    """Prior one-month return (enters negatively for reversal)."""
    return panel.monthly_ret.copy()


def volatility_6m(panel: Panel) -> pd.DataFrame:
    """Std of the last 6 monthly returns (coarse; daily vol once panel carries it)."""
    return panel.monthly_ret.rolling(6, min_periods=4).std()


def illiquidity(panel: Panel) -> pd.DataFrame:
    """Negative log median daily dollar volume (3m). Higher = less liquid.

    Amihud-flavoured size/liquidity premium proxy; also the capacity governor —
    the harness reports how much of the book sits in the illiquid tail.
    """
    dv = panel.monthly_dollar_vol.rolling(3, min_periods=2).median()
    return -np.log(dv.where(dv > 0))


PRICE_SIGNALS: list[Signal] = [
    Signal(
        "mom_12_1",
        "Intermediate-horizon momentum persists (Jegadeesh-Titman; GKX top family). "
        "Prior: main-repo TRIAL-MOM-BACKTEST #13 FAILED risk-adjusted vs SPY as a "
        "standalone lane — here it is a cross-sectional FEATURE, not a lane.",
        momentum_12_1,
    ),
    Signal(
        "st_reversal",
        "One-month reversal from liquidity provision (Jegadeesh 1990); strongest "
        "in small/illiquid names — exactly our corner.",
        short_term_reversal,
    ),
    Signal(
        "vol_6m",
        "Low-vol anomaly / leverage constraints (Ang et al.); GKX volatility family.",
        volatility_6m,
    ),
    Signal(
        "illiq",
        "Illiquidity premium (Amihud 2002); doubles as the capacity governor.",
        illiquidity,
    ),
]
