"""Promotion gate — what a belief must clear before it may move money.

Two independent facts, both measured by this project rather than assumed:

  * The lfdr-anchored bar. With our own measured base rate of real money legs
    (3/196 ~ 3%), Efron local-FDR <= 0.10 needs **t ~ 4.0** on the
    block-bootstrapped, cluster-deflated statistic.
  * No 72-month window can clear it. SPY itself prints t ~ 1.1 over 72 months.
    So a retrospective window CANNOT promote anything, and this gate refuses to
    try: given a retrospective evidence source it returns INSUFFICIENT with the
    reason, never PROMOTE.

Promotion therefore lives on the forward paper lane. The daily posterior layer
is scoped to attention and calibration — which is exactly what D3 says.
"""

from __future__ import annotations

from dataclasses import dataclass

LFDR_T_BAR = 4.0
MIN_FORWARD_MONTHS = 24
EVIDENCE_SOURCES = ("forward_lane", "backtest", "replay", "simulation")


@dataclass(frozen=True)
class GateInput:
    claim_class: str
    t_stat: float                  # cluster-deflated, block-bootstrapped
    n_resolutions: int
    months_forward: int
    evidence_source: str
    dsr: float | None = None       # deflated Sharpe on effective trial count


def evaluate(g: GateInput) -> dict:
    if g.evidence_source not in EVIDENCE_SOURCES:
        raise ValueError(f"evidence_source must be one of {EVIDENCE_SOURCES}")

    reasons: list[str] = []
    if g.evidence_source != "forward_lane":
        reasons.append(
            f"evidence_source={g.evidence_source}: retrospective evidence "
            "cannot promote. SPY prints t~1.1 over 72 months, so the bar "
            "t>=4.0 is unreachable in any window of that length — the "
            "adequate instrument is the forward lane (NEGATIVE_RESULTS 35).")
    if g.months_forward < MIN_FORWARD_MONTHS:
        reasons.append(f"months_forward={g.months_forward} < {MIN_FORWARD_MONTHS}: "
                       "no skill claims before 24 months of forward record.")
    if g.t_stat < LFDR_T_BAR:
        reasons.append(f"t={g.t_stat:.2f} < {LFDR_T_BAR} (lfdr<=0.10 at our "
                       "measured 3% base rate).")
    if g.dsr is not None and g.dsr < 0.95:
        reasons.append(f"DSR={g.dsr:.2f} < 0.95 on the effective trial count.")

    if not reasons:
        return {"verdict": "PROMOTE", "reasons": [], "input": g.__dict__}
    verdict = "INSUFFICIENT" if g.evidence_source != "forward_lane" else "HOLD"
    return {"verdict": verdict, "reasons": reasons, "input": g.__dict__}


def attention_weight(hit_posterior: dict, *, floor: float = 0.20) -> float:
    """Discounted-Thompson-style attention with a randomized floor.

    The floor is not decoration: without it, cells that lose early stop being
    sampled and their pooled estimates never become unbiased. Reward is
    information yield, never P&L.
    """
    if not hit_posterior.get("available"):
        return floor
    lo, hi = hit_posterior["ci95"]
    width = max(hi - lo, 0.0)
    signal = abs(hit_posterior["mean"] - 0.5) * 2.0
    return round(floor + (1 - floor) * min(signal + 0.5 * width, 1.0), 3)
