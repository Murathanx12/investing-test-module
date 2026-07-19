"""L4 adoption gate — the thing that makes a result admissible.

Ship bar (inherited from the main repo): DSR >= 0.95 AND PBO < 0.5, deflated
against the CUMULATIVE trial count (main repo base + local registry). A raw
Sharpe with no trial count is inadmissible; this module simply refuses to
produce one.
"""

from __future__ import annotations

import numpy as np

from aegis_brain.discipline.overfitting import (
    deflated_sharpe_from_returns,
    probability_of_backtest_overfitting,
)
from aegis_brain.gate.registry import cumulative_trial_count

DSR_SHIP_THRESHOLD = 0.95
PBO_REJECT_THRESHOLD = 0.5

# Default cross-trial Sharpe variance when a batch estimate is unavailable.
# Matches the conservative main-repo convention of assuming meaningful
# dispersion among candidates rather than near-zero (which would deflate less).
DEFAULT_SR_VARIANCE = 0.01


def evaluate_candidate(
    monthly_net_returns,
    sr_variance: float = DEFAULT_SR_VARIANCE,
    perf_matrix: np.ndarray | None = None,
    n_trials: int | None = None,
) -> dict:
    """Gate report for one candidate's walk-forward net returns.

    Args:
        monthly_net_returns: per-month net returns from ONE pre-registered run.
        sr_variance: variance of Sharpe across the candidate batch (H0 spread).
        perf_matrix: optional (T x N) per-period returns of ALL configs tried
            in the batch — enables PBO. Without it PBO is reported as None and
            the candidate CANNOT ship (unknown selection bias != no bias).
        n_trials: override the cumulative count (testing only).
    """
    n = n_trials if n_trials is not None else cumulative_trial_count()
    r = np.asarray(monthly_net_returns, dtype=float)

    dsr_report = deflated_sharpe_from_returns(r, n_trials=n, sr_variance=sr_variance)

    pbo_report = None
    if perf_matrix is not None:
        pbo_report = probability_of_backtest_overfitting(perf_matrix)

    dsr_ok = dsr_report["dsr"] >= DSR_SHIP_THRESHOLD
    pbo_ok = pbo_report is not None and pbo_report.get("pbo", 1.0) < PBO_REJECT_THRESHOLD

    verdict = "ADOPT-CANDIDATE" if (dsr_ok and pbo_ok) else "REJECT"
    reasons = []
    if not dsr_ok:
        reasons.append(
            f"DSR {dsr_report['dsr']:.3f} < {DSR_SHIP_THRESHOLD} at n_trials={n}"
        )
    if pbo_report is None:
        reasons.append("PBO not computable (no batch perf_matrix) — cannot ship")
    elif not pbo_ok:
        reasons.append(f"PBO {pbo_report['pbo']:.3f} >= {PBO_REJECT_THRESHOLD}")

    return {
        "verdict": verdict,
        "reasons": reasons,
        "n_trials_deflated_against": n,
        "dsr": dsr_report,
        "pbo": pbo_report,
        "note": (
            "ADOPT-CANDIDATE means eligible for PROMOTION ONLY: a human commits a "
            "TRIAL-*.md in aegis-finance and the forward paper clocks decide. "
            "Backtests on the EODHD panel remain direction-check grade until WRDS."
        ),
    }


def survivorship_bound(run_full: dict, run_largest: dict) -> dict:
    """Explicit survivorship-bias bound: full-universe run vs largest-N run.

    Until WRDS/CRSP, every reported result carries this gap. A strategy whose
    edge exists only in the full universe (heavy in names most subject to
    coverage gaps) should be treated as unproven.
    """
    full = run_full["summary"]
    big = run_largest["summary"]
    return {
        "sharpe_full_universe": full["sharpe_net_ann"],
        "sharpe_largest_n": big["sharpe_net_ann"],
        "sharpe_gap": round(full["sharpe_net_ann"] - big["sharpe_net_ann"], 3),
        "excess_full": full["mean_excess_vs_universe_ew"],
        "excess_largest_n": big["mean_excess_vs_universe_ew"],
        "interpretation": (
            "gap is an upper bound on how much of the result may be "
            "survivorship/coverage artifact rather than signal"
        ),
    }
