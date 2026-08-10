"""G8 — the price-impact term G7 does not have.

NIGHT-8 measured the hole this fills. Running G7's own book through synthetic
worlds whose liquidity differed by a factor of a million, cost per dollar traded
came back **31.00 bps at every single rung**. G7 prices scarcity as *delay*: an
order too big for the day is carried to the next day and eventually fills at the
same quoted terms. Nobody's broker works that way. Every capacity number this
programme has published is therefore a delay-only lower bound.

This module supplies the missing mechanism and nothing else. It is deliberately
separate from `daily_sim` so that G7 stays byte-frozen: `SimConfig.impact_coef`
defaults to **0.0**, at which value the arithmetic below contributes exactly
zero and G7's published outputs are reproduced. A run is G8 only when it says so.

## The model

The **metaorder** square-root law. For an order of notional `Q` in a name whose
average daily dollar volume is `V`, executed by a participant with daily return
volatility `sigma`:

    impact (fraction of price) = coef * sigma * sqrt(Q / V)

Three properties matter for what we use it for, and all three are the opposite
of G7's behaviour:

  * it is charged on the **whole order**, not the daily slice, so splitting a
    trade over more days does not escape it — which is exactly the thing G7's
    carry-forward mechanism let a book do for free;
  * it is **concave** in size, so doubling the order less than doubles the cost
    per dollar but does raise it — capacity degrades smoothly, not at a cliff;
  * it **rises with volatility** and **falls with volume**, so two books of the
    same dollar size in different names are no longer charged the same.

## What is NOT modelled, stated before anyone quotes a number

  * **Urgency / horizon.** The square-root law as written is horizon-free: it
    prices *size*, not *speed*. `urgency_exp` exists as an explicit knob and
    defaults to 0.0, meaning a slower participation cap buys no impact relief in
    G8 by default. Trading off impact against delay needs an Almgren-Chriss
    style rate term and a calibration we do not have.
  * **Permanent vs temporary decomposition.** One coefficient, charged once.
  * **Cross-impact** between correlated names traded the same day.
  * **The coefficient itself.** `coef` is a scenario, not a measurement. The
    published range for the square-root prefactor is roughly 0.25 to 1.0
    depending on market, era and estimation method, and we have no broker TCA
    data of our own. Every G8 number is therefore quoted as a low/base/high
    band, never as a point estimate, until real execution data exists.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

#: Scenario band for the square-root prefactor. NOT a measurement of our own.
#: Quote all three or quote none.
SCENARIOS: dict[str, float] = {"low": 0.25, "base": 0.50, "high": 1.00}

#: Trailing windows, both shifted by a day before use — an impact charged with
#: today's own volume is a look-ahead.
ADV_WINDOW = 21
SIGMA_WINDOW = 60

#: A name with no usable volume history. Charging 0 would make an untradeable
#: name free, which is the failure mode this whole module exists to remove.
MAX_IMPACT_BPS = 1_000.0


def square_root_impact_bps(order_notional, adv_dollar, sigma_daily,
                           coef: float, *, urgency: float = 1.0,
                           urgency_exp: float = 0.0):
    """Impact in bps of traded value for a metaorder. Vectorised or scalar.

    `order_notional` and `adv_dollar` must be in the same currency units; the
    ratio is what enters. `sigma_daily` is a fraction (0.03 = 3% a day).

    A missing or non-positive ADV is charged `MAX_IMPACT_BPS` rather than zero:
    the absence of volume is the most expensive case, not the cheapest.
    """
    q = np.abs(np.asarray(order_notional, dtype="float64"))
    v = np.asarray(adv_dollar, dtype="float64")
    s = np.asarray(sigma_daily, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        part = np.where(v > 0, q / v, np.inf)
        bps = coef * s * np.sqrt(part) * 1e4
        if urgency_exp:
            bps = bps * np.power(np.maximum(urgency, 1e-9), urgency_exp)
    bps = np.where(np.isfinite(bps), bps, MAX_IMPACT_BPS)
    bps = np.where(np.isfinite(s) & (s >= 0), bps, MAX_IMPACT_BPS)
    out = np.clip(bps, 0.0, MAX_IMPACT_BPS)
    if np.ndim(order_notional) == 0:
        return float(out)
    return out


def trailing_adv(dvol: pd.DataFrame, window: int = ADV_WINDOW) -> pd.DataFrame:
    """Median, not mean: one block print should not make a name look liquid."""
    return dvol.rolling(window, min_periods=max(3, window // 4)).median().shift(1)


def trailing_sigma(ret: pd.DataFrame, window: int = SIGMA_WINDOW) -> pd.DataFrame:
    return ret.rolling(window, min_periods=max(10, window // 4)).std().shift(1)


def describe(coef: float) -> dict:
    """The block every G8 receipt must carry, so no number travels bare."""
    return {
        "execution_model": "G8" if coef > 0 else "G7",
        "impact_law": "metaorder square root: coef * sigma_daily * sqrt(Q/ADV)",
        "impact_coef": coef,
        "coef_is": "a SCENARIO from the published range 0.25-1.0, not a "
                   "measurement on our own fills",
        "scenarios": SCENARIOS,
        "adv_window_days": ADV_WINDOW,
        "sigma_window_days": SIGMA_WINDOW,
        "charged_on": "the whole order at creation, amortised across its fills",
        "not_modelled": ["urgency / execution horizon (urgency_exp defaults 0)",
                         "permanent vs temporary decomposition",
                         "cross-impact between names",
                         "the coefficient itself"],
    }
