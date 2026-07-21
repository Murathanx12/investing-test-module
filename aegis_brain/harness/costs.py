"""ADV / liquidity-conditional transaction-cost model.

Flat 25 bps is a fiction for microcaps: a $50M name can carry a 100-200 bps effective
half-spread while a mega-cap is <5 bps. The five-AI review flagged this as a source of
false-positive net alpha precisely in the microcap corner we fish. This model maps a
name's dollar volume to a per-side cost in basis points, monotone-decreasing in
liquidity, so the backtest pays realistic costs where they actually bite.

Form: cost_bps(ddv) = clip(a - b * log10(dollar_volume_per_day), floor, cap).
Default anchors (calibrated to the microcap-cost literature; override per trial):
  ~$10M/day  -> ~15 bps   (liquid small/mid)
  ~$1M/day   -> ~55 bps
  ~$200k/day -> ~150 bps  (thin microcap floor of our eligibility filter)
Clipped to [floor=8 bps, cap=300 bps]. This is a deliberately conservative,
transparent proxy — refine against Corwin-Schultz / effective-spread estimates when
tick data is available. The flat-25 run is always reported alongside as the optimistic bound.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Solved so that log10(1e7)->~15 and log10(2e5)->~150 bps.
_A = 570.0
_B = 79.4
_FLOOR = 8.0
_CAP = 300.0


def one_way_cost_bps(dollar_volume, a: float = _A, b: float = _B,
                     floor: float = _FLOOR, cap: float = _CAP):
    """Per-side cost in bps from daily dollar volume. Accepts a scalar, Series, or
    DataFrame; NaN/<=0 volume -> the cap (treat unknown liquidity as worst-case)."""
    if isinstance(dollar_volume, (pd.Series, pd.DataFrame)):
        ddv = dollar_volume.astype(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            bps = a - b * np.log10(ddv.where(ddv > 0))
        return bps.clip(lower=floor, upper=cap).fillna(cap)
    ddv = float(dollar_volume)
    if not np.isfinite(ddv) or ddv <= 0:
        return cap
    return float(min(cap, max(floor, a - b * np.log10(ddv))))


def cost_matrix(monthly_dollar_vol: pd.DataFrame, **kw) -> pd.DataFrame:
    """Per-name, per-month one-way cost (bps) aligned to the panel's dollar-volume
    matrix. Feed this to the walk-forward harness in place of a flat scalar."""
    return one_way_cost_bps(monthly_dollar_vol, **kw)
