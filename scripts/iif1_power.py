"""INTERNET-INVESTIGATOR-FWD-1 — how long until this trial can say anything?

    python -m scripts.iif1_power

WHY THIS RUNS BEFORE THE PRE-REGISTRATION IS WRITTEN
====================================================
GRAPH-COVARIANCE-1 spent a session discovering that its pre-registered oracle
was undetectable, and only a declared power gate turned that into information
instead of a wasted escalation. The lesson generalises one step earlier: for a
FORWARD trial, the ceiling is not an oracle, it is the CLOCK. A forward trial
that needs three years to clear its own MDE is not a trial, it is a standing
order to spend money — and the only honest moment to discover that is before
the first dollar.

So this computes, for the design under consideration, how many nights of
accrual are needed before `arm_B - arm_A` clears its own 80%-power MDE, as a
function of how much genuine information the arms differ by.

THE STATISTIC BEING POWERED
---------------------------
Brier score, paired on identical (ticker, date, observable, horizon) cells —
every arm forecasts the SAME cells, so the difference is within-cell and the
enormous common variance of "was the market up that day" cancels before any SE
is taken (§18). Cells are then collapsed to ONE number per grading day, and the
SE is taken over days with a Newey-West correction. n is the number of graded
DAYS, and it is printed beside every number (§19).

THE ALGEBRA THAT MAKES THIS INTERPRETABLE
-----------------------------------------
For a binary outcome `y ~ Bernoulli(pi)` and a forecast `p`:

    E[(p - y)^2] = (p - pi)^2 + pi(1 - pi)

The irreducible term `pi(1-pi)` is IDENTICAL for both arms on a paired cell, so
it cancels exactly. **The Brier difference between two arms is precisely the
difference in their squared error against the true probability.** Nothing about
market volatility enters. That is why pairing is worth so much here.

It also gives the honest upper bound. If `pi = base + z` with `sd(z) = sigma_pi`,
then a PERFECT forecaster beats a constant-base-rate forecaster by exactly
`sigma_pi^2`. So `sigma_pi` — how much genuine day-to-day variation in the true
probability exists at all — is the entire budget both arms are competing over,
and every number below is quoted against it.

WHY THE OBSERVABLE CHOICE IS A POWER DECISION, NOT A TASTE DECISION
-------------------------------------------------------------------
`sigma_pi` for one-day DIRECTION is tiny; this programme has measured the LLM
at a coin flip on direction twice. `sigma_pi` for one-day MAGNITUDE is much
larger, because whether a stock moves more than x% tomorrow is genuinely
forecastable when you know an FDA decision or an earnings date is Thursday —
which is exactly the kind of thing an investigation tool can find and an
engineered snapshot may not carry. The simulation is run across a range of
`sigma_pi` so the design can be chosen against the clock rather than hoped at.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT              # noqa: E402
from scripts.mg1_grade import stat_block                # noqa: E402

OUT = MODULE_ROOT / "runs" / "INTERNET-INVESTIGATOR-FWD-1"

SEED = 20260814

#: Grid. `sigma_pi` is the sd of the TRUE probability around its base rate —
#: the whole budget the two arms compete over.
SIGMA_PI_GRID = (0.02, 0.05, 0.10, 0.15)

#: Fraction of that budget each arm captures. A = the engineered snapshot,
#: B = snapshot + investigation. The gap is what the trial is trying to see.
CAPTURE_A = 0.30
CAPTURE_B_GRID = (0.35, 0.40, 0.50, 0.60)

#: Design knobs the trial actually controls.
TRIGGERS_PER_NIGHT_GRID = (10, 20, 40)
CELLS_PER_TRIGGER = 6          #: e.g. 2 observables x 3 short horizons

#: Correlation of the true-probability shock across cells of the SAME trigger.
#: Two horizons on one ticker on one night are not independent draws, and
#: pretending they are is the commonest way a power calculation lies.
WITHIN_TRIGGER_RHO = 0.70

#: Correlation of forecast ERROR across triggers on the same night (a shared
#: "the model was having a bad night" component). Also inflates the SE.
WITHIN_NIGHT_RHO = 0.20

MAX_NIGHTS = 500
NW_LAGS = 2
MDE_Z = 2.80
N_SIMS = 200


def _correlated(rng: np.random.Generator, n_groups: int, per_group: int,
                rho: float) -> np.ndarray:
    """Unit-variance draws with equicorrelation `rho` inside each group."""
    common = rng.standard_normal((n_groups, 1))
    idio = rng.standard_normal((n_groups, per_group))
    return np.sqrt(rho) * common + np.sqrt(1.0 - rho) * idio


def simulate(nights: int, triggers: int, sigma_pi: float, cap_a: float,
             cap_b: float, rng: np.random.Generator) -> float:
    """One realisation of the trial. Returns the per-night mean paired Brier
    difference series' t-statistic against its own MDE ruler.

    Positive `d` means arm A had the LARGER squared error, i.e. arm B was
    better — the sign convention is fixed here and read nowhere else.
    """
    per_night = []
    for _ in range(nights):
        # true probability shock, correlated within each trigger
        z = _correlated(rng, triggers, CELLS_PER_TRIGGER,
                        WITHIN_TRIGGER_RHO) * sigma_pi
        pi = np.clip(0.5 + z, 0.01, 0.99)

        # each arm captures a fraction of z, plus its own noise. The shared
        # night-level error component is what WITHIN_NIGHT_RHO injects.
        na = _correlated(rng, triggers, CELLS_PER_TRIGGER, WITHIN_NIGHT_RHO)
        nb = _correlated(rng, triggers, CELLS_PER_TRIGGER, WITHIN_NIGHT_RHO)
        noise = 0.5 * sigma_pi
        pa = np.clip(0.5 + cap_a * z + noise * na, 0.01, 0.99)
        pb = np.clip(0.5 + cap_b * z + noise * nb, 0.01, 0.99)

        y = (rng.random(pi.shape) < pi).astype(float)
        d = (pa - y) ** 2 - (pb - y) ** 2
        per_night.append(float(d.mean()))
    st = stat_block(np.array(per_night), lags=NW_LAGS)
    return st


def nights_to_detect(triggers: int, sigma_pi: float, cap_a: float,
                     cap_b: float, rng: np.random.Generator) -> int | None:
    """Smallest night count at which the median simulation clears its MDE."""
    for nights in (20, 40, 60, 90, 120, 180, 250, 350, MAX_NIGHTS):
        hits = 0
        for _ in range(N_SIMS):
            st = simulate(nights, triggers, sigma_pi, cap_a, cap_b, rng)
            if np.isfinite(st["mean"]) and st["mean"] >= st["mde"]:
                hits += 1
        if hits / N_SIMS >= 0.80:            # 80% power, the house standard
            return nights
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rows = []
    print(f"nights to reach 80% power (arm A captures {CAPTURE_A:.0%} of the "
          f"signal; MDE = {MDE_Z} x max(HAC, IID) SE over nights)\n")
    header = ("sigma_pi  ceiling(Brier)   cap_B  " +
              "  ".join(f"k={k:<3d}" for k in TRIGGERS_PER_NIGHT_GRID))
    print(header)
    print("-" * len(header))
    for sp in SIGMA_PI_GRID:
        for cb in CAPTURE_B_GRID:
            cells = []
            for k in TRIGGERS_PER_NIGHT_GRID:
                n = nights_to_detect(k, sp, CAPTURE_A, cb, rng)
                cells.append("never" if n is None else str(n))
                rows.append({"sigma_pi": sp, "capture_a": CAPTURE_A,
                             "capture_b": cb, "triggers_per_night": k,
                             "cells_per_trigger": CELLS_PER_TRIGGER,
                             "nights_to_80pct_power": n})
            print(f"{sp:<9.2f} {sp ** 2:<15.5f} {cb:<6.2f} " +
                  "  ".join(f"{c:<6s}" for c in cells))

    meta = {
        "what": "nights of accrual to reach 80% power on the paired Brier "
                "difference between two arms, by how much true-probability "
                "variation exists (sigma_pi) and how much of it the "
                "investigating arm captures",
        "seed": SEED, "n_sims_per_cell": N_SIMS,
        "within_trigger_rho": WITHIN_TRIGGER_RHO,
        "within_night_rho": WITHIN_NIGHT_RHO,
        "cells_per_trigger": CELLS_PER_TRIGGER,
        "nw_lags": NW_LAGS, "mde_z": MDE_Z,
        "note": "The Brier ceiling column is sigma_pi^2 — what a PERFECT "
                "forecaster beats a constant base rate by. Both arms compete "
                "inside that budget; nothing can exceed it.",
        "grid": rows,
    }
    (OUT / "power.json").write_text(json.dumps(meta, indent=2),
                                    encoding="utf-8")
    print(f"\nwrote {OUT / 'power.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
