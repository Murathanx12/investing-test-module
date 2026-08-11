"""Append the REVINFO-2 registration + verdict rows to TRIALS/registry.jsonl.

Mechanism check, done before writing anything: recent trials (REVINFO-1, the
leg decomposition) recorded themselves as prereg docs in TRIALS/ plus a verdict
doc in docs/ — but the machine-readable registry the corpse-linter and the
multiple-testing count read is `TRIALS/registry.jsonl`, appended via
`aegis_brain.gate.registry.register_trial()` (idempotent on name, append-only,
no delete API). The NIGHT-5/6 verdict batches were recorded there as
`VERDICT-*` rows. REVINFO-2 ACCRUES ONE ARM, so unlike REVINFO-1 (accrued
zero) it must increment that count: one row for the trial, one VERDICT row
carrying the measured numbers, mirroring the VERDICT-NIGHT5-BATCH pattern.

    python -m scripts.register_revinfo_2

Reads runs/REVINFO_2/revinfo2.json; refuses to run before the trial has.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from aegis_brain.gate.registry import register_trial

RECEIPT = MODULE_ROOT / "runs" / "REVINFO_2" / "revinfo2.json"


def main() -> int:
    if not RECEIPT.exists():
        raise SystemExit("runs/REVINFO_2/revinfo2.json missing — the trial has "
                         "not run; a registry row without a receipt is a lie")
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))

    p50 = r["H2_g7"]["eps_rev_breadth_small_n50_m1"]["power"]
    row1 = register_trial(
        name="REVINFO-2",
        hypothesis=(
            "Layer-2 decision boundary for a LONG-ONLY small-cap book on "
            "eps_rev_breadth, with G7 turnover in the SAME trial. H1: "
            "E[r_entrant - r_incumbent] > 0 as a paired per-rebalance "
            "difference with its own NW SE (S18). H2: same book through "
            "daily_sim at impact_coef=0, headline = NET excess CAGR vs CRSP VW "
            "beside its own MDE (S19) + EXECUTION-STANDARD regime blocks. H3: "
            "net improves 1m->3m->6m holding, tested as adjacent-frequency "
            "DIFFERENCES each with its own SE. ACCRUES ONE ARM. Full doc "
            "TRIALS/PREREG_REVINFO_2_LAYER2.md @ 7409bff; registered "
            "expectation UNRESOLVED or NET_DEAD."),
        expected_effect=(
            "Both book sizes {50,100} run and reported, neither selected. "
            "Controls: tgt_upside corpse through the same pipeline with BOTH "
            "cross-sectional and tail-concentrated arms (must reproduce "
            "negative sign); turnover-matched pure-noise book (must earn "
            "~nothing); realised turnover reported against the "
            "ANALYST-IBES-1 prior (eps_rev_breadth small top-50 monthly = "
            "10.614x)."),
        kill_condition=(
            "Frozen: CANDIDATE iff H2 net excess >= own 80%-power MDE AND "
            ">=4/6 regime blocks; UNRESOLVED if positive below MDE (never a "
            "kill, S19); NET_DEAD if <=0 with the whole 95% interval below "
            "+3%/yr; H1 fails while H2 passes => the run is VOID and "
            "investigated, not reported."),
    )

    def cell(name):
        g = r["H2_g7"][name]
        p = g["power"]
        sm = g["regimes_gate"]["_summary"]
        return (f"{name}: net excess {100*g['excess_cagr_net']:+.2f}%/yr "
                f"(arith {100*p['arithmetic_excess_annual']:+.2f} vs MDE "
                f"{100*p['mde_80pct_power_annual']:.2f}, t "
                f"{p['t_newey_west']}), blocks "
                f"{sm['blocks_positive_excess']}/{sm['blocks_evaluated']}, "
                f"G7 turnover {g['turnover_1way_annual_g7']:.2f}x -> "
                f"{r['cell_verdicts'][name]['verdict']}")

    cells = "; ".join(cell(f"eps_rev_breadth_small_n{n}_m{c}")
                      for n in (50, 100) for c in (1, 3, 6))
    h1 = r["H1_decision_boundary"]
    h1_s = "; ".join(
        f"{k}: {100*v['mean_ann']:+.2f}%/yr (MDE {100*v['mde_ann']:.2f}, "
        f"t {v['t']}, {v['n_events']} events)"
        for k, v in h1.items() if "mean_ann" in v)
    h3 = r["H3_adjacent_frequency_differences"]
    h3_s = "; ".join(
        f"{k}: {100*v['mean_ann']:+.2f}%/yr (MDE {100*v['mde_ann']:.2f}, "
        f"t {v['t']})" for k, v in h3.items())
    c = r["controls"]
    tv = r["turnover"]["n50_m1_vs_prior"]

    row2 = register_trial(
        name="VERDICT-REVINFO-2",
        hypothesis=(
            f"REVINFO-2 verdict: {r['trial_verdict']}. H2 (G7, net vs CRSP "
            f"VW): {cells}."),
        expected_effect=(
            f"H1 decision boundary: {h1_s}. H3 adjacent-frequency "
            f"differences: {h3_s}. Controls: corpse cross-sectional "
            f"{100*c['corpse_cross_sectional']['spread_ann']:+.2f}%/yr sign "
            f"reproduced={c['corpse_cross_sectional']['negative_sign_reproduced']}; "
            f"corpse tail-concentrated gross "
            f"{100*c['corpse_tail_concentrated']['monthly_gross_excess_ann']:+.2f} "
            f"/ G7 net {100*c['corpse_tail_concentrated']['g7_net_excess_ann']:+.2f} "
            f"sign reproduced={c['corpse_tail_concentrated']['negative_sign_reproduced']}; "
            f"noise (rho {c['noise']['rho']}) G7 net "
            f"{100*c['noise']['g7_net_excess_ann']:+.2f}%/yr. Turnover n50 m1 "
            f"{tv['measured']}x vs prior {tv['prior']}x (ratio {tv['ratio']})."),
        kill_condition=(
            "May NOT conclude: REVINFO-1 confirmed; ANALYST-IBES-1 overturned; "
            "any money/Sharpe/skill claim; that anything seeds a lane. Verdict "
            "doc docs/REVINFO_2_VERDICT_2026-08-11.md; receipt "
            "runs/REVINFO_2/revinfo2.json (untracked)."),
    )
    print(json.dumps({"registered": [row1["name"], row2["name"]]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
