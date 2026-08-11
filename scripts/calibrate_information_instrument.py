"""Operating characteristics of the Layer-1 information instrument.

An MDE is a PROMISE: "at an effect of this size, this design finds it 80% of the
time." Nothing in this programme has ever checked that promise against a world
where the answer is known. The MDE has been an analytical formula, and NIGHT-10
found the formula was being fed the wrong standard error for months without
anyone noticing, precisely because no measurement ever contradicted it.

So before `information.py` is allowed to issue a verdict on real data, it is run
against synthetic worlds with planted effects, and asked:

  1. **False positives.** In a world where the signal predicts NOTHING, how
     often does it say INFORMATION_PRESENT? The threshold is 2.8 SE, so this
     should land near 0.5%, not 5%.
  2. **Does the MDE mean what it says?** At a planted effect exactly equal to
     the instrument's own reported MDE, detection should be ~80%. This is the
     one measurement that can falsify the central claim of CANON §19.
  3. **Bias.** Is the recovered effect the planted one, or is the estimator
     shrinking or inflating it?
  4. **NO_INFORMATION safety.** How often does a null world get correctly
     called, and does a world with a REAL effect ever get killed?

THE PLANT IS VERIFIED BEFORE IT IS USED. ARENA-1's synthetic generator cancelled
its own plant, so every known-answer test it ran was silently executed on a null
world and would have "passed" no matter what the instrument did. Here, each
world's realised spread is measured directly from the returns, independent of
the estimator under test, and the run ABORTS if the planted effect is not
present. A calibration harness that cannot see its own plant is worse than none:
it launders an unchecked instrument as a checked one.

    python -m scripts.calibrate_information_instrument [--draws 200]

Writes runs/INSTRUMENT/information_calibration.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.information import (LARGEST_CREDIBLE_EFFECT_ANN,
                                        cross_sectional_information)

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "INSTRUMENT"

N_NAMES = 1200
N_MONTHS = 252
IDIO_SD_M = 0.12          # monthly idiosyncratic vol, ~42%/yr — small-cap-ish
MKT_SD_M = 0.045
SIGNAL_PERSIST = 0.85     # month-to-month AR(1) in the signal


def make_world(rng: np.random.Generator, effect_ann: float,
               *, n_names: int = N_NAMES, n_months: int = N_MONTHS
               ) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """A panel where the signal's true breadth-weighted spread is `effect_ann`.

    Returns (signal, monthly_ret, realised_spread_ann). The third value is
    measured from the generated returns WITHOUT using the estimator under test,
    and is what the caller checks the plant against.

    Construction: an AR(1) latent signal, market factor shared by all names, and
    a return whose conditional mean is proportional to the signal's
    cross-sectional normal score. The market factor is deliberately large —
    it is the term the cross-sectional demeaning is supposed to remove, and a
    world without it would flatter the instrument.
    """
    idx = pd.date_range("2002-01-31", periods=n_months, freq="ME")
    cols = [str(i) for i in range(n_names)]

    z = np.empty((n_months, n_names))
    prev = rng.normal(size=n_names)
    innov = np.sqrt(1.0 - SIGNAL_PERSIST ** 2)
    for t in range(n_months):
        prev = SIGNAL_PERSIST * prev + innov * rng.normal(size=n_names)
        z[t] = prev

    # cross-sectional normal scores of the latent signal, which is the scale the
    # planted coefficient is defined against
    order = np.argsort(np.argsort(z, axis=1), axis=1)
    from scipy import stats as sps
    zs = sps.norm.ppf((order + 0.5) / n_names)

    # beta such that the breadth-weighted spread is the target. The algebra is
    # E[w.r] = beta * sum(z^2)/sum|z| * 2; it is NOT relied upon — the realised
    # spread is measured below and that is what the caller checks.
    w = zs / np.abs(zs).sum(axis=1, keepdims=True) * 2.0
    implied_per_beta = float((w * zs).sum(axis=1).mean())
    beta_m = (effect_ann / 12.0) / implied_per_beta if implied_per_beta else 0.0

    mkt = rng.normal(0.0, MKT_SD_M, size=(n_months, 1))
    eps = rng.normal(0.0, IDIO_SD_M, size=(n_months, n_names))
    # the return in month t+1 is driven by the signal observed at t
    ret = np.empty((n_months, n_names))
    ret[0] = mkt[0, 0] + eps[0]
    ret[1:] = beta_m * zs[:-1] + mkt[1:] + eps[1:]

    signal = pd.DataFrame(z, index=idx, columns=cols)
    rets = pd.DataFrame(ret, index=idx, columns=cols)

    # realised plant, measured from the returns themselves
    realised = float((w[:-1] * ret[1:]).sum(axis=1).mean() * 12.0)
    return signal, rets, realised


def one_draw(seed: int, effect_ann: float) -> dict:
    rng = np.random.default_rng(seed)
    sig, ret, realised = make_world(rng, effect_ann)
    res = cross_sectional_information(sig, ret, horizon=1, name="synthetic")
    t = res.long_short_spread_t
    return {
        "seed": seed,
        "planted_ann": effect_ann,
        "realised_plant_ann": realised,
        "estimated_ann": res.long_short_spread_ann,
        "mde_ann": res.long_short_spread_mde_ann,
        "t": t,
        "verdict": res.verdict,
        # the instrument's own rule: |effect| >= MDE, i.e. 2.8 SE
        "detected": res.verdict == "INFORMATION_PRESENT",
        # the conventional rule the MDE is DEFINED against: 1.96 SE
        "significant": bool(t is not None and abs(t) >= 1.96),
        "killed": res.verdict == "NO_INFORMATION",
    }


def verify_plant(rows: list[dict], effect_ann: float,
                 null_rows: list[dict]) -> float:
    """Abort unless the planted effect is actually in the generated returns.

    This is the ARENA-1 lesson as an assertion. A generator that cancels its own
    plant produces a calibration run in which every world is null; the harness
    then reports whatever the instrument does on noise and calls it validated.

    **Checked as a PAIRED difference against the null world of the same seed.**
    Every cell reuses the same seeds — common random numbers, so that a
    difference in detection rate between two effect levels is not partly a
    difference in which noise was drawn. The consequence is that each cell's
    realised spread is `planted + the SAME noise offset`, and comparing a cell's
    level against its target therefore tests the noise, not the plant. The first
    version of this check did exactly that and failed a generator that was
    correct: it asked for 1.00 %/yr, measured 0.52, and the missing 0.48 was the
    null world's own draw, present identically in every cell.

    Differencing against the paired null cancels it exactly — which is CANON §18
    (a claim about two constructions agreeing is a claim about their DIFFERENCE)
    applied to the harness rather than to a result.
    """
    got = float(np.mean([r["realised_plant_ann"] for r in rows]))
    base = float(np.mean([r["realised_plant_ann"] for r in null_rows]))
    delta = got - base
    if effect_ann == 0.0:
        return delta
    if not (0.9 * effect_ann <= delta <= 1.1 * effect_ann):
        raise RuntimeError(
            f"PLANT NOT PRESENT: asked for {100*effect_ann:.2f}%/yr, the "
            f"generated returns realise {100*delta:.2f}%/yr above the paired "
            f"null. Every known-answer result from this harness would be a "
            f"measurement on the wrong world (the ARENA-1 defect).")
    return delta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=120)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # A first draw tells us what this design's MDE actually is, so that the
    # 80%-power point can be probed at the instrument's OWN reported threshold
    # rather than at a number guessed in advance.
    probe = one_draw(20260811, 0.0)
    mde = probe["mde_ann"]
    logger.info("this design reports an MDE of %.2f%%/yr — probing there",
                100 * mde)

    mde_probe = round(mde, 5)
    grid = [0.0, 0.01, 0.02, 0.03, mde_probe, 0.05, 0.08]
    cells, null_rows = [], None
    for effect in grid:
        # common random numbers across cells: the same worlds, differing only
        # by the planted effect, so a change in detection rate is the plant and
        # not the draw.
        rows = [one_draw(700000 + 1000 * i, effect) for i in range(args.draws)]
        if null_rows is None:
            null_rows = rows
        plant_delta = verify_plant(rows, effect, null_rows)
        det = float(np.mean([r["detected"] for r in rows]))
        sig = float(np.mean([r["significant"] for r in rows]))
        kill = float(np.mean([r["killed"] for r in rows]))
        est = np.array([r["estimated_ann"] for r in rows])
        real = float(np.mean([r["realised_plant_ann"] for r in rows]))
        cell = {
            "planted_ann": effect,
            "realised_plant_ann": round(real, 5),
            "realised_plant_vs_paired_null_ann": round(plant_delta, 5),
            "draws": len(rows),
            "detection_rate": round(det, 4),
            "significance_rate": round(sig, 4),
            "no_information_rate": round(kill, 4),
            "unresolved_rate": round(1.0 - det - kill, 4),
            "mean_estimate_ann": round(float(est.mean()), 5),
            "bias_ann": round(float(est.mean()) - real, 5),
            "sd_of_estimate_ann": round(float(est.std(ddof=1)), 5),
            "mean_mde_ann": round(float(np.mean([r["mde_ann"] for r in rows])), 5),
            "is_the_mde_probe": abs(effect - mde_probe) < 1e-9,
        }
        cells.append(cell)
        logger.info("effect %5.2f%%/yr (realised %5.2f) -> detected %5.1f%% | "
                    "NO_INFORMATION %5.1f%% | est %+.2f%% (bias %+.2f)",
                    100 * effect, 100 * real, 100 * det, 100 * kill,
                    100 * cell["mean_estimate_ann"], 100 * cell["bias_ann"])

    null = next(c for c in cells if c["planted_ann"] == 0.0)
    at_mde = next(c for c in cells if c["is_the_mde_probe"])
    checks = {
        # ── the MDE label means what it says ────────────────────────────────
        # An MDE is DEFINED against a 5% significance test: at an effect of
        # 2.8 SE, the rule "reject when |t| >= 1.96" fires 80% of the time.
        # That is the promise CANON §19 makes, and this is the measurement that
        # can falsify it. Nothing in this programme had ever checked it.
        "power_at_own_mde_significance_rule": at_mde["significance_rate"],
        "power_target": 0.80,
        "mde_label_ok": 0.70 <= at_mde["significance_rate"] <= 0.92,

        # ── the VERDICT rule is deliberately stricter than that ─────────────
        # INFORMATION_PRESENT requires |effect| >= MDE, i.e. 2.8 SE, not the
        # 1.96 SE the MDE is defined against. At a true effect of exactly the
        # MDE the estimate lands above it about half the time, so ~50% here is
        # the CORRECT reading and not a fault. The extra strictness is the
        # winner's-curse guard: among low-powered studies the results that
        # clear mere significance systematically overstate their effects, which
        # is the region NIGHT-10 found 21 of 21 configurations sitting in.
        "detection_at_own_mde_verdict_rule": at_mde["detection_rate"],
        "verdict_rule_is_stricter_than_significance": bool(
            at_mde["detection_rate"] < at_mde["significance_rate"]),
        "verdict_rule_expected_near_50pct": bool(
            0.38 <= at_mde["detection_rate"] <= 0.62),

        # ── it does not invent effects ──────────────────────────────────────
        "false_positive_rate_at_zero": null["detection_rate"],
        "false_positive_budget": 0.02,
        "false_positive_ok": null["detection_rate"] <= 0.02,

        # ── it recovers the size it was given ───────────────────────────────
        "worst_abs_bias_ann": round(
            float(max(abs(c["bias_ann"]) for c in cells)), 5),
        "bias_ok": max(abs(c["bias_ann"]) for c in cells) < 0.005,

        # ── it never kills something real ──────────────────────────────────
        "never_killed_a_real_effect": all(
            c["no_information_rate"] == 0.0
            for c in cells if c["planted_ann"] >= LARGEST_CREDIBLE_EFFECT_ANN),
    }
    checks["INSTRUMENT_CALIBRATED"] = bool(
        checks["mde_label_ok"] and checks["verdict_rule_expected_near_50pct"]
        and checks["false_positive_ok"] and checks["bias_ok"]
        and checks["never_killed_a_real_effect"])

    payload = {
        "instrument": "aegis_brain.pf.information.cross_sectional_information",
        "question": "does the reported MDE mean what it claims?",
        "world": {"n_names": N_NAMES, "n_months": N_MONTHS,
                  "idio_sd_monthly": IDIO_SD_M, "mkt_sd_monthly": MKT_SD_M,
                  "signal_ar1": SIGNAL_PERSIST},
        "plant_verified": True,
        "plant_verification": ("each world's realised spread is measured from "
                               "the generated returns independently of the "
                               "estimator, and the run aborts if it is absent"),
        "draws_per_cell": args.draws,
        "cells": cells,
        "checks": checks,
        "accrues_to_denominator": 0,
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "information_calibration.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8")
    logger.info("CALIBRATED=%s | false-positive %.1f%% | at its own MDE: "
                "significance rule %.1f%% (target 80), verdict rule %.1f%% "
                "(expected ~50, stricter on purpose) | worst bias %+.3f%%/yr",
                checks["INSTRUMENT_CALIBRATED"],
                100 * checks["false_positive_rate_at_zero"],
                100 * checks["power_at_own_mde_significance_rule"],
                100 * checks["detection_at_own_mde_verdict_rule"],
                100 * checks["worst_abs_bias_ann"])
    return 0 if checks["INSTRUMENT_CALIBRATED"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
