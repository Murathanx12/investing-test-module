"""DIAG-PF4-MEMORY-PLACEBO-2 — aggregate the four-arm memory ladder.

The four arms, in order of how much they are told:

    A                no memory block at all
    situations_only  the block, the neighbours, the counts — no outcomes
    shuffled(seed)   the block, the neighbours, the counts, outcomes with the
                     SAME marginal distribution but the situation->outcome
                     mapping destroyed (within regime), one arm per seed
    E                the real thing

Reading the ladder is the whole point, and it is what one seed could not do:

  * E ≈ shuffled ≈ situations_only  -> only the PRESENCE of a memory block
    matters. Nothing in it is being used.
  * situations_only < shuffled ≈ E  -> what memory contributes is BASE-RATE
    CALIBRATION, which a permutation preserves by construction. The first
    control over-controlled and "block, not content" was the wrong conclusion.
  * situations_only ≈ shuffled < E  -> situation-specific content matters after
    all, and NIGHT-3's conclusion was a one-seed artifact.

E is located inside the shuffled arms' own permutation distribution, so the
comparison finally has a null instead of a single draw.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.pf.panel63 import annualize

MEM = MODULE_ROOT / "runs" / "PF4" / "memory"
NIGHT3 = MODULE_ROOT / "runs" / "NIGHT3"


def nw(x):
    r = newey_west_tstat(pd.Series(x).dropna(), lags=12)
    return None if r.get("t") is None else round(float(r["t"]), 2)


def main() -> int:
    arms = [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(MEM.glob("ARM_*.json"))]
    if not arms:
        raise SystemExit("no memory arms on disk yet")
    shuf = [a for a in arms if a["mode"] == "shuffled"]
    sit = [a for a in arms if a["mode"] == "situations_only"]

    ref = json.loads((NIGHT3 / "DECISION_REPLAY.json").read_text(encoding="utf-8"))
    e_excess = ref["arms"]["E"]["excess_cagr_net"]
    a_excess = ref["arms"]["A"]["excess_cagr_net"]
    old = json.loads((NIGHT3 / "MEMORY_PLACEBO.json").read_text(encoding="utf-8"))

    ex = np.array([a["excess_cagr_net"] for a in shuf], dtype=float)
    res = {
        "diagnostic": "DIAG-PF4-MEMORY-PLACEBO-2", "is_gate": False,
        "supersedes_reading_of": "DIAG-NIGHT3-MEMORY-PLACEBO-1 (one seed, "
                                 "global permutation, no situations-only arm)",
        "arms_completed": {"shuffled_seeds": len(shuf),
                           "situations_only": len(sit)},
        "ladder": {
            "A_no_memory": a_excess,
            "situations_only": (sit[0]["excess_cagr_net"] if sit else None),
            "shuffled_mean": (round(float(ex.mean()), 4) if len(ex) else None),
            "E_real_memory": e_excess,
        },
    }
    if len(ex):
        res["shuffled_permutation_distribution"] = {
            "n_seeds": len(ex),
            "mean": round(float(ex.mean()), 4),
            "sd": round(float(ex.std(ddof=1)), 4) if len(ex) > 1 else None,
            "min": round(float(ex.min()), 4), "max": round(float(ex.max()), 4),
            "p05": round(float(np.percentile(ex, 5)), 4),
            "p95": round(float(np.percentile(ex, 95)), 4),
            "single_seed_used_by_the_old_control": old["arm_Eshuffled"][
                "excess_cagr_net"],
            "draws": [round(float(v), 5) for v in np.sort(ex)]}
        beat = int((ex < e_excess).sum())
        res["E_vs_shuffled_distribution"] = {
            "E_excess": e_excess,
            "seeds_E_beats": f"{beat}/{len(ex)}",
            "empirical_p_value": round((len(ex) - beat + 1) / (len(ex) + 1), 4),
            "E_minus_shuffled_mean": round(e_excess - float(ex.mean()), 4),
            "z_of_E_in_shuffled_distribution": (
                round((e_excess - float(ex.mean())) / float(ex.std(ddof=1)), 2)
                if len(ex) > 1 and ex.std(ddof=1) > 0 else None)}

    # THE DECIDING STATISTIC, and the one the seed distribution cannot give.
    # Seed-to-seed spread measures PERMUTATION noise only: every seed shares the
    # same months and the same slates, so its sd is tiny and a z-score against it
    # answers "is E outside the permutation cloud" — not "would this hold on new
    # data". The month-level paired difference answers the second question, which
    # is the one that matters, and it is the statistic NIGHT-3's M2 used.
    arm_e = pd.read_csv(NIGHT3 / "arm_monthly_returns.csv", index_col=0,
                        parse_dates=True)["E"]
    series = []
    for p in sorted(MEM.glob("arm_shuf*_monthly.csv")):
        s = pd.read_csv(p, index_col=0, parse_dates=True).iloc[:, 0]
        series.append(s)
    if series:
        pooled = pd.concat(series, axis=1).mean(axis=1)
        d = (arm_e - pooled).dropna()
        sd = float(d.std(ddof=1))
        res["E_minus_pooled_shuffled_monthly"] = {
            "n_months": len(d), "n_seeds_pooled": len(series),
            "cagr_difference": round(annualize(arm_e.dropna())
                                     - annualize(pooled.dropna()), 4),
            "mean_monthly": round(float(d.mean()), 5),
            "t_nw": nw(d),
            "mde_at_t2_annualized": round(2 * sd / np.sqrt(len(d)) * 12, 4),
            "why_this_and_not_the_z": (
                "the seed z-score is against permutation noise, which shares "
                "every month and every slate and is therefore far too tight to "
                "support an out-of-sample claim. This is the same estimator as "
                "the registered M2 metric."),
        }
    if sit:
        s = sit[0]["excess_cagr_net"]
        res["reading"] = _read(a_excess, s, float(ex.mean()) if len(ex) else None,
                               e_excess)
        res["situations_only_detail"] = {
            "excess_cagr_net": s, "t_excess_nw": sit[0]["t_excess_nw"],
            "E_minus_situations_only": round(e_excess - s, 4),
            "situations_only_minus_A": round(s - a_excess, 4)}
    else:
        res["reading"] = "situations-only arm not yet complete"

    res["standing_caveat"] = (
        "every arm here carries the same small-cap profitability premium, so "
        "these standalone excesses are not the LLM's contribution. The paired "
        "differences are, and the registered gate metric remains M2 from "
        "NIGHT-3, which this diagnostic cannot overturn.")
    (MEM / "MEMORY_LADDER.json").write_text(json.dumps(res, indent=2),
                                            encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


def _read(a: float, s: float, shufmean: float | None, e: float) -> str:
    if shufmean is None:
        return "shuffled arms not yet complete"
    tol = 0.01
    if abs(e - shufmean) < tol and abs(s - shufmean) < tol:
        return ("PRESENCE ONLY — real, scrambled and outcome-free memory are "
                "indistinguishable. Nothing inside the block is being used; the "
                "block itself is doing the work, consistent with Min et al. "
                "(2022) on in-context demonstrations.")
    if s < shufmean - tol and abs(e - shufmean) < tol:
        return ("BASE-RATE CALIBRATION — withholding outcomes hurts, but "
                "scrambling which outcome belongs to which situation does not. "
                "The first control over-controlled: a permutation preserves the "
                "marginal distribution and therefore hands the placebo the whole "
                "benefit. 'Block, not content' was the wrong conclusion; the "
                "right one is 'distribution, not mapping'.")
    if e > shufmean + tol and e > s + tol:
        return ("REOPENED — real memory beats BOTH controls on standalone "
                "excess, and NIGHT-3's single shuffled seed sits above the "
                "whole new seed distribution, so that control was an outlier "
                "draw. This does NOT establish content: the deciding statistic "
                "is the month-level paired difference (see "
                "E_minus_pooled_shuffled_monthly), because seed-to-seed spread "
                "measures permutation noise, not sampling noise. Read that "
                "number, then claim only what it supports.")
    return ("MIXED — the ladder does not fall into a clean pattern; report the "
            "numbers and claim nothing.")


if __name__ == "__main__":
    raise SystemExit(main())
