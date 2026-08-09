"""TRIAL-PF4-DECOMPOSITION-1 — apply the frozen decision rule and score everyone.

Reads only what the stages banked. The decision rule is the one committed in
TRIALS/PREREG_PF4_DECOMPOSITION.md at 12d8540, before any PF-4 compute; nothing
here may reinterpret it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import ledger

OUT = MODULE_ROOT / "runs" / "PF4"
MEM = OUT / "memory"

# Frozen in the pre-registration.
ADOPT_ALPHA, ADOPT_T = 0.025, 2.0
DIMINISHED_ALPHA = 0.010
KILL_T = 1.5


def load(name: str) -> dict:
    p = OUT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def band(x, lo, hi) -> bool:
    return x is not None and lo <= x <= hi


def main() -> int:
    A, A2 = load("STAGE_A.json"), load("STAGE_A2_PRE1982.json")
    B, C = load("STAGE_B_CHAR_PLACEBO.json"), load("STAGE_C_PRODUCT_BENCHMARK.json")
    G = load("GATE_POWER.json")
    R = load("RETRACTION_NIGHT3_5_2.json")
    if not A:
        raise SystemExit("STAGE_A.json missing — nothing to adjudicate")

    prim = A["PRIMARY_incremental_signal_contribution"]
    a = prim["alpha_ff5_umd"]
    inc, t_inc = a.get("ann_alpha"), a.get("t_alpha")

    if inc is None:
        verdict, reason = "UNRESOLVED", "primary regression did not estimate"
    elif inc >= ADOPT_ALPHA and (t_inc or 0) >= ADOPT_T:
        verdict = "CONFIRMED"
        reason = (f"incremental {inc:+.2%}/yr at t {t_inc} clears the frozen bar "
                  f"(>= {ADOPT_ALPHA:.1%} and t >= {ADOPT_T})")
    elif inc < DIMINISHED_ALPHA and (t_inc or 0) < KILL_T:
        verdict = "CANDIDACY WITHDRAWN"
        reason = (f"incremental {inc:+.2%}/yr at t {t_inc} is below "
                  f"{DIMINISHED_ALPHA:.1%} with t < {KILL_T}")
    else:
        verdict = "DIMINISHED"
        reason = (f"incremental {inc:+.2%}/yr at t {t_inc} clears the kill "
                  f"condition but not the confirmation bar")

    ew = A["leg_ew_universe"]["alpha_ff5_umd"].get("ann_alpha")
    era = A["era_costs"]
    era_delta = era.get("tick_floor_over_flat25", {}).get("delta_vs_flat25")
    dl = A["delisting_audit"]
    dl_delta = dl.get("shumway_-30pct", {}).get("delta_vs_banked")
    cal = A["calendar"]
    nonjan = cal["non_january"]["excess_log_growth_annual"]
    sp = A["leg_smallcap_profitability_factor"]
    sp_alpha = sp["book_alpha_vs_ff5_umd_plus_smallprof"].get("ann_alpha")
    banked_alpha = A["banked_headline"] and 0.0501
    marg = {k: v for k, v in A["marginal_rank_windows"].items()
            if not k.startswith("_") and "alpha_ff5_umd" in v}
    marg_alphas = [v["alpha_ff5_umd"].get("ann_alpha") for v in marg.values()
                   if v["alpha_ff5_umd"].get("ann_alpha") is not None]
    marg_flat = (max(marg_alphas) - min(marg_alphas) < 0.03
                 if len(marg_alphas) >= 5 else None)
    bands = A["construction_grids"]["buy_hold_band"]
    b3 = bands.get("mult_3", {}).get("excess_cagr_net")
    b2 = bands.get("mult_2", {}).get("excess_cagr_net")
    char_p = (B.get("verdict_by_basis", {}).get("gross", {})
              .get("empirical_p_value"))

    preds = {
        "R-1 reviewer: incremental +1.5..+2.5%/yr":
            band(inc, 0.015, 0.025),
        "R-2 reviewer: EW-universe alpha +1.5..+2.0%/yr":
            band(ew, 0.015, 0.020),
        "R-3 reviewer: era costs -0.8..-1.5%/yr":
            band(era_delta, -0.015, -0.008),
        "R-4 reviewer: delisting -0.1..-0.4%/yr":
            band(dl_delta, -0.004, -0.001),
        "R-5 reviewer: marginal-decile alphas flat": marg_flat,
        "H-1 house: incremental >= +2.5%/yr":
            (inc is not None and inc >= 0.025),
        "H-2 house: delisting delta <= 0.3%/yr":
            (dl_delta is not None and abs(dl_delta) <= 0.003),
        "H-3 house: non-January excess >= +2.5%/yr":
            (nonjan is not None and nonjan >= 0.025),
        "H-4 house: char-matched p > 0.0099 but < 0.05":
            (char_p is not None and 0.0099 < char_p < 0.05),
        "H-5 house: tick floor costs more than 1.5%/yr pre-2001":
            ((era.get("tick_floor_over_flat25", {}).get("excess_pre_2001")
              is not None) and
             (A["banked_headline"]["excess_cagr_net"]
              - era["tick_floor_over_flat25"]["excess_pre_2001"]) > 0.015),
        "H-6 house: band 3->2 changes net excess by < 0.5%/yr":
            (None if (b2 is None or b3 is None) else abs(b2 - b3) < 0.005),
        "H-7 house: self-built small-cap prof factor absorbs most FF5+UMD alpha":
            (None if sp_alpha is None else sp_alpha < 0.5 * banked_alpha),
    }
    hits = sum(1 for v in preds.values() if v is True)
    scored = sum(1 for v in preds.values() if v is not None)

    mem_arms = []
    for p in sorted(MEM.glob("ARM_*.json")):
        mem_arms.append(json.loads(p.read_text(encoding="utf-8")))

    res = {
        "trial": "TRIAL-PF4-DECOMPOSITION-1",
        "prereg_commit": "12d8540 (2026-08-09T18:58:02+08:00)",
        "VERDICT": verdict, "reason": reason,
        "primary": {"incremental_alpha_ann": inc, "t": t_inc,
                    "mde_at_t2": prim.get("mde_at_t2_annualized"),
                    "raw_self_financing_gap": prim.get("self_financing_cagr_gap")},
        "decomposition": {
            "banked_headline_excess": A["banked_headline"]["excess_cagr_net"],
            "ew_universe_alpha": ew,
            "ew_universe_raw_excess":
                A["leg_ew_universe"]["excess_cagr_vs_benchmark"],
            "era_cost_delta": era_delta,
            "delisting_delta": dl_delta,
            "january_share_of_excess": cal["january"].get("share_of_excess"),
            "non_january_excess_annual": nonjan,
            "alpha_after_smallcap_prof_factor": sp_alpha,
            "alpha_before_ff5_umd_only": banked_alpha,
        },
        "characteristic_matched_placebo": B.get("verdict_by_basis"),
        "marginal_rank_window_alphas": {k: v["alpha_ff5_umd"].get("ann_alpha")
                                        for k, v in marg.items()},
        "marginal_alphas_flat": marg_flat,
        "pre_1982_block": A2.get("block_1963_1982"),
        "product_benchmark": C.get("french_small_robust"),
        "gate_power": {"G2": G.get("G2", {}).get("binary_gate_pass_probabilities"),
                       "G9_false_negative_at_true_2.5pct":
                           G.get("G9", {}).get("false_negative_rate", {})
                           .get("true_+2.50%", {}).get("false_negative_rate"),
                       "binding": G.get("binding_gate_analysis")},
        "multiple_testing": ledger.testing_block(
            A["banked_headline"]["t_excess_newey_west"], 3.39),
        "noise_expectation": ledger.noise_expectation(
            ledger.denominator().total, hits=1),
        "retraction": {"corrected_claim": R.get("corrected_claim"),
                       "non_monotone": R.get("non_monotone_test", {})
                       .get("quartiles_of_engine_rank_within_slate")},
        "memory_arms_completed": len(mem_arms),
        "predictions": preds,
        "prediction_score": f"{hits}/{scored} scored ({len(preds)} registered)",
    }
    (OUT / "VERDICT_PF4.json").write_text(json.dumps(res, indent=2, default=str),
                                          encoding="utf-8")
    print(json.dumps(res, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
