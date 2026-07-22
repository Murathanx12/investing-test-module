"""Factory batch 1 — 20 price/volume signals (frozen list, docs/STRATEGY_FACTORY.md).

Everything here is computable from the CRSP panel alone (monthly_ret,
month_end_price, monthly_dollar_vol). Values at row t use information through
month-end t only; the scan pairs them with the return of month t+1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.signals import FactorySignal
from aegis_brain.signals.price_signals import (
    illiquidity,
    momentum_12_1,
    short_term_reversal,
    volatility_6m,
)


def _mom(panel: Panel, months: int, skip: int = 1) -> pd.DataFrame:
    log1p = np.log1p(panel.monthly_ret)
    return np.expm1(log1p.rolling(months - skip, min_periods=max(2, (months - skip) * 2 // 3))
                    .sum().shift(skip))


def mom_6_1(panel: Panel) -> pd.DataFrame:
    return _mom(panel, 6)


def dip_3m(panel: Panel) -> pd.DataFrame:
    """Trailing 3-month return (long the biggest losers via direction=-1)."""
    return _mom(panel, 3, skip=0)


def dd_from_12m_high(panel: Panel) -> pd.DataFrame:
    """Depth of drawdown from the trailing 12m month-end high, in [0, 1]."""
    p = panel.month_end_price
    return 1.0 - p / p.rolling(12, min_periods=6).max()


def high_52wk_prox(panel: Panel) -> pd.DataFrame:
    """Price / trailing 12m high (George-Hwang 2004). Mirror of dd_from_12m_high."""
    p = panel.month_end_price
    return p / p.rolling(12, min_periods=6).max()


def seasonality(panel: Panel) -> pd.DataFrame:
    """Mean same-calendar-month return over the prior 3 years (Heston-Sadka 2008)."""
    r = panel.monthly_ret
    stack = pd.concat([r.shift(12), r.shift(24), r.shift(36)])
    return stack.groupby(stack.index).mean().reindex(r.index).where(
        r.shift(24).notna()  # require >= 2 usable years
    )


def consistency_12m(panel: Panel) -> pd.DataFrame:
    """Fraction of up-months in the trailing 12 (steady-winner / frog-in-the-pan)."""
    return (panel.monthly_ret > 0).where(panel.monthly_ret.notna()).rolling(
        12, min_periods=9
    ).mean()


def max_ret_6m(panel: Panel) -> pd.DataFrame:
    """Largest single monthly return in the trailing 6 (lottery demand, BCW 2011)."""
    return panel.monthly_ret.rolling(6, min_periods=4).max()


def skew_12m(panel: Panel) -> pd.DataFrame:
    return panel.monthly_ret.rolling(12, min_periods=9).skew()


def ltr_36_13(panel: Panel) -> pd.DataFrame:
    """Cumulative return t-36..t-13 (De Bondt-Thaler long-term reversal)."""
    log1p = np.log1p(panel.monthly_ret)
    return np.expm1(log1p.rolling(24, min_periods=16).sum().shift(12))


def amihud_3m(panel: Panel) -> pd.DataFrame:
    """|monthly ret| per dollar of daily volume, 3m mean (Amihud 2002 flavor)."""
    dv = panel.monthly_dollar_vol.where(panel.monthly_dollar_vol > 0)
    return (panel.monthly_ret.abs() / dv).rolling(3, min_periods=2).mean()


def vol_change(panel: Panel) -> pd.DataFrame:
    """Recent vol vs own 12m vol (rising uncertainty; long LOW via direction)."""
    r = panel.monthly_ret
    return r.rolling(3, min_periods=3).std() / r.rolling(12, min_periods=9).std()


def volume_trend(panel: Panel) -> pd.DataFrame:
    """Log ratio of 3m to 12m mean dollar volume (attention/high-volume premium)."""
    dv = panel.monthly_dollar_vol.where(panel.monthly_dollar_vol > 0)
    return np.log(dv.rolling(3, min_periods=2).mean() / dv.rolling(12, min_periods=9).mean())


def sharpe_12m(panel: Panel) -> pd.DataFrame:
    r = panel.monthly_ret
    return r.rolling(12, min_periods=9).mean() / r.rolling(12, min_periods=9).std()


def price_level(panel: Panel) -> pd.DataFrame:
    return np.log(panel.month_end_price.where(panel.month_end_price > 0))


def trend_above_ma10(panel: Panel) -> pd.DataFrame:
    """Price vs 10-month moving average (Faber trend, used cross-sectionally)."""
    p = panel.month_end_price
    return p / p.rolling(10, min_periods=7).mean() - 1.0


def vol_12m(panel: Panel) -> pd.DataFrame:
    return panel.monthly_ret.rolling(12, min_periods=9).std()


BATCH1: list[FactorySignal] = [
    # -- calibration references (already adjudicated over the confirm window
    #    by TRIAL-BRAIN-001/002 as a GBM combo; cannot graduate) --
    FactorySignal("mom_12_1", "Intermediate momentum (Jegadeesh-Titman; GKX top family).",
                  momentum_12_1, +1, contaminated=True),
    FactorySignal("st_reversal", "1-month reversal from liquidity provision (Jegadeesh 1990).",
                  short_term_reversal, -1, contaminated=True),
    FactorySignal("vol_6m_low", "Low-vol anomaly / leverage constraints (Ang et al.).",
                  volatility_6m, -1, contaminated=True),
    FactorySignal("illiq", "Illiquidity premium (Amihud 2002), log-dollar-vol proxy.",
                  illiquidity, +1, contaminated=True),
    # -- fresh candidates --
    FactorySignal("mom_6_1", "Shorter-horizon momentum; faster echo of the 12-1 effect.",
                  mom_6_1, +1),
    FactorySignal("dip_3m", "Murat's dip-buy: 3m losers overshoot and mean-revert "
                  "(medium-horizon overreaction).", dip_3m, -1),
    FactorySignal("dd_from_12m_high", "Murat's '50% dropper': deep drawdowns overshoot "
                  "fundamentals and recover.", dd_from_12m_high, +1),
    FactorySignal("high_52wk_prox", "Anchoring UNDER-reaction near the 52wk high — the "
                  "literature's side of the same variable (George-Hwang 2004).",
                  high_52wk_prox, +1),
    FactorySignal("seasonality", "Same-calendar-month persistence (Heston-Sadka 2008).",
                  seasonality, +1),
    FactorySignal("consistency_12m", "Steady winners drift: gradual info discounted "
                  "(frog-in-the-pan, Da-Gurun-Warachka 2014).", consistency_12m, +1),
    FactorySignal("max_ret_low", "Avoid lottery spikes: high recent MAX overpriced "
                  "(Bali-Cakici-Whitelaw 2011).", max_ret_6m, -1),
    FactorySignal("skew_low", "Skewness preference overprices right tails; long "
                  "negative skew (Boyer-Mitton-Vorkink).", skew_12m, -1),
    FactorySignal("ltr_36_13", "Long-term reversal: 2-3y losers rebound "
                  "(De Bondt-Thaler 1985).", ltr_36_13, -1),
    FactorySignal("amihud_3m", "Price-impact illiquidity premium (Amihud 2002).",
                  amihud_3m, +1),
    FactorySignal("vol_calm", "Falling own-vol regime = uncertainty resolving; long "
                  "calming names.", vol_change, -1),
    FactorySignal("volume_trend", "High-volume premium: attention shocks precede drift "
                  "(Gervais-Kaniel-Mingelgrin 2001).", volume_trend, +1),
    FactorySignal("sharpe_12m", "Trend quality: smooth risk-adjusted winners persist.",
                  sharpe_12m, +1),
    FactorySignal("price_level", "Penny-stock avoidance: nominal low-price names are "
                  "lottery-like and underperform.", price_level, +1),
    FactorySignal("trend_ma10", "Above own 10m MA = uptrend intact (Faber, applied "
                  "cross-sectionally).", trend_above_ma10, +1),
    FactorySignal("vol_12m_low", "Low-vol anomaly at the 12m horizon (fresh horizon, "
                  "distinct from contaminated vol_6m).", vol_12m, -1),
]
