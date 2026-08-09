"""Control arms — the gates a strategy must clear before it means anything.

The one that matters is RANDOM-SELECTION-WITH-IDENTICAL-TURNOVER: draw N names
at random from the same eligible universe, trade them at the same rate, pay the
same costs, and see what the same construction produces with no information in
it. A strategy that does not clear the placebo band is a portfolio-construction
artifact, not a signal (the §28 lesson, generalized to portfolios).

Turnover matching is done by making the random score persistent — an AR(1)
process whose ρ is searched until the placebo's realized annual turnover
matches the strategy's within tolerance. A ρ=0 placebo churns far harder than
any real book, which would flatter the strategy by charging the control more
costs; a buy-and-hold placebo would undercharge it.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.pf.engine import run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.signals import random_score
from aegis_brain.pf.spec import StrategySpec

logger = logging.getLogger(__name__)


def _turnover_of(panel, eligible, spec, rf, cost_frame, rho, seed) -> tuple[float, dict]:
    sc = random_score(panel, seed=seed, rho=rho)
    out = run_book(panel, sc, eligible, spec, rf, cost_frame)
    return out["diag"]["turnover_1way_annual"], out


def match_rho(panel, eligible, spec: StrategySpec, rf, cost_frame,
              target_turnover: float, *, tol: float = 0.10,
              max_iter: int = 8) -> float:
    """Bisection on ρ so the placebo's turnover matches the strategy's."""
    lo, hi = 0.0, 0.995
    t_lo, _ = _turnover_of(panel, eligible, spec, rf, cost_frame, lo, spec.seed + 1)
    t_hi, _ = _turnover_of(panel, eligible, spec, rf, cost_frame, hi, spec.seed + 2)
    if target_turnover >= t_lo:
        logger.warning("strategy turnover %.2f >= churning placebo %.2f; "
                       "using rho=0", target_turnover, t_lo)
        return 0.0
    if target_turnover <= t_hi:
        logger.warning("strategy turnover %.2f <= sticky placebo %.2f; "
                       "using rho=%.3f", target_turnover, t_hi, hi)
        return hi
    best, best_err = lo, abs(t_lo - target_turnover)
    for i in range(max_iter):
        mid = 0.5 * (lo + hi)
        t_mid, _ = _turnover_of(panel, eligible, spec, rf, cost_frame, mid,
                                spec.seed + 10 + i)
        err = abs(t_mid - target_turnover) / max(target_turnover, 1e-9)
        if err < best_err:
            best, best_err = mid, err
        if err <= tol:
            return mid
        if t_mid > target_turnover:      # too much churn → more persistence
            lo = mid
        else:
            hi = mid
    logger.info("rho search ended at %.3f (turnover error %.1f%%)", best,
                100 * best_err)
    return best


def placebo_band(panel, eligible, spec: StrategySpec, rf, cost_frame,
                 bench: pd.Series, target_turnover: float, *,
                 n_draws: int = 100, rho: float | None = None) -> dict:
    """Distribution of net excess CAGR for N turnover-matched random books."""
    if rho is None:
        rho = match_rho(panel, eligible, spec, rf, cost_frame, target_turnover)
    rows = []
    for i in range(n_draws):
        sc = random_score(panel, seed=spec.seed + 1000 + i, rho=rho)
        out = run_book(panel, sc, eligible, spec, rf, cost_frame)
        net = out["monthly"]["net"]
        b = bench.reindex(net.index)
        rows.append({"draw": i,
                     "cagr_net": annualize(net),
                     "excess_cagr": annualize(net) - annualize(b),
                     "turnover": out["diag"]["turnover_1way_annual"]})
    df = pd.DataFrame(rows)
    ex = df["excess_cagr"]
    return {
        "n_draws": n_draws, "rho": round(float(rho), 4),
        "placebo_turnover_mean": round(float(df["turnover"].mean()), 3),
        "strategy_turnover": round(float(target_turnover), 3),
        "excess_cagr": {
            "mean": round(float(ex.mean()), 4),
            "sd": round(float(ex.std(ddof=1)), 4),
            "p50": round(float(ex.quantile(0.50)), 4),
            "p95": round(float(ex.quantile(0.95)), 4),
            "max": round(float(ex.max()), 4)},
        "draws": [round(float(v), 5) for v in ex],
    }


def placebo_verdict(strategy_excess_cagr: float, band: dict) -> dict:
    """The gate: beat the best of N random books, not merely their average."""
    ex = np.asarray(band["draws"], dtype=float)
    n = len(ex)
    beat = int((ex < strategy_excess_cagr).sum())
    return {
        "strategy_excess_cagr": round(float(strategy_excess_cagr), 4),
        "placebo_p95": band["excess_cagr"]["p95"],
        "placebo_max": band["excess_cagr"]["max"],
        "empirical_p_value": round((n - beat + 1) / (n + 1), 4),
        "beats_placebo_max": bool(strategy_excess_cagr > band["excess_cagr"]["max"]),
        "beats_placebo_p95": bool(strategy_excess_cagr > band["excess_cagr"]["p95"]),
        "PASS": bool(strategy_excess_cagr > band["excess_cagr"]["p95"]),
    }
