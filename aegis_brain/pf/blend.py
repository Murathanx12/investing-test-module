"""Core-satellite blending — a FIXED market share, rebalanced monthly.

Why this exists: PF-1's ENGINE-ALPHA failed exactly one gate, regime breadth,
because a quality/value/momentum book lags mega-cap-led melt-ups. The obvious
fix is to hold some of the market. The non-obvious requirement is that the fix
must not smuggle in market timing — timing destroyed 3.34%/yr in PF-1 and has
failed every test this project has run. So `blend_market` is a CONSTANT frozen
in the spec before the run: it never reads a regime, a trailing return, or a
volatility state. It is an allocation, not a decision.

Blending happens at the monthly-return level, which is exact for a two-sleeve
book rebalanced monthly, and charges three costs that a naive `X*a + (1-X)*b`
would silently give away:

  1. the strategy sleeve's own trading costs (already inside its net return),
  2. an index-fund expense on the market sleeve (`blend_fee_bps`, annual),
  3. the *rebalancing* trade between sleeves — the sleeves drift apart every
     month and pulling them back to X costs real money at the same 25bps the
     satellite pays.

(3) is small but it is exactly the term that makes "just add some index fund"
look free when it is not.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REBAL_BPS = 25.0            # charged on sleeve-rebalancing trades


def blend_monthly(monthly: pd.DataFrame, mkt: pd.Series, x: float,
                  fee_bps_annual: float = 3.0,
                  rebal_bps: float = REBAL_BPS) -> tuple[pd.DataFrame, dict]:
    """Blend a strategy book with a constant `x` share of the market.

    Args:
        monthly: the strategy's monthly frame (needs 'gross', 'net', 'cost').
        mkt: benchmark total return, same index basis.
        x: constant market share in [0, 1).
        fee_bps_annual: index-fund expense charged on the market sleeve.
        rebal_bps: one-way cost on the monthly sleeve-rebalancing trade.

    Returns:
        (blended monthly frame, diagnostics)
    """
    if not 0.0 <= x < 1.0:
        raise ValueError(f"blend share {x} outside [0, 1)")
    out = monthly.copy()
    b = mkt.reindex(out.index)
    if b.isna().any():
        raise RuntimeError("benchmark has gaps over the strategy window — "
                           "refusing to blend against a hole")

    rs_net, rs_gross = out["net"].astype(float), out["gross"].astype(float)
    fee_m = (fee_bps_annual / 1e4) / 12.0

    # portfolio return BEFORE the fee and the sleeve-rebalancing trade
    core = x * b
    r_net = core + (1.0 - x) * rs_net
    r_gross = core + (1.0 - x) * rs_gross

    # sleeve drift: market sleeve ends the month at x(1+b) of a book worth
    # (1 + r_net); pulling it back to x trades the difference, both ways.
    v = 1.0 + r_net
    w_end = x * (1.0 + b) / v.where(v > 0, np.nan)
    traded_1way = (w_end - x).abs().fillna(0.0)
    rebal_cost = 2.0 * traded_1way * (rebal_bps / 1e4)
    fee_cost = x * fee_m

    out["gross"] = r_gross
    out["net"] = r_net - rebal_cost - fee_cost
    out["cost"] = (1.0 - x) * out["cost"].astype(float) + rebal_cost + fee_cost
    out["traded"] = (1.0 - x) * out["traded"].astype(float) + 2.0 * traded_1way
    out["cash_w"] = (1.0 - x) * out["cash_w"].astype(float)

    n_years = max(len(out) / 12.0, 1e-9)
    diag = {
        "blend_market_share": round(float(x), 4),
        "blend_fee_bps_annual": float(fee_bps_annual),
        "blend_rebalance_bps": float(rebal_bps),
        "blend_rebalance_turnover_1way_annual":
            round(float(traded_1way.sum()) / n_years, 4),
        "blend_total_drag_bps_annual":
            round(float((rebal_cost + fee_cost).sum()) / n_years * 1e4, 2),
    }
    return out, diag
