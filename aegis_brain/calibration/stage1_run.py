"""Stage 1 — DGP-A generator + fidelity gate F1-F8 (design §6).

Kill criterion (pre-registered): any batch-1 signal shows |mean rank-IC| >
2 MC-SE on alpha=0 panels, or F1/F2 miss by >30% -> DGP-A rejected; fall back
to DGP-B and report that alpha-injection power analysis is unsupported.

Run:  .venv/Scripts/python.exe -m aegis_brain.calibration.stage1_run
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import numpy as np

from aegis_brain.calibration import fidelity as F
from aegis_brain.calibration.config import (
    REAL_PANEL_DIR,
    RUNS_DIR,
    SEED_BASE,
    assert_production_constants,
)
from aegis_brain.calibration.panel_gen import build_dgpa_inputs, gen_null_panel
from aegis_brain.calibration.stage0_seam import subset_panel_to_eligible
from aegis_brain.data.eodhd_panel import load_cached_panel

N_F8_REPS = 5


def main() -> dict:
    t0 = time.time()
    print("STAGE 1 — DGP-A fidelity gate")
    print("=" * 70)
    assert_production_constants()

    real = subset_panel_to_eligible(load_cached_panel(REAL_PANEL_DIR))
    print(f"real panel (eligible subset): {real.monthly_ret.shape[0]} months x "
          f"{real.monthly_ret.shape[1]:,} symbols")

    print("building DGP-A inputs (one-time beta/residual decomposition)...")
    inputs = build_dgpa_inputs(real)
    print(f"  beta defaults (thin history -> market-only): "
          f"{inputs.n_beta_defaulted:,} of {len(inputs.symbols):,}")

    rng = np.random.default_rng(SEED_BASE)
    synth = gen_null_panel(inputs, rng)
    print("generated fidelity reference panel (rep 0)")

    results = []
    results.append(F.f1_pairwise_corr(real, synth, np.random.default_rng(SEED_BASE + 900)))
    results.append(F.f2_dispersion(real, synth))
    results.append(F.f3_tails(real, synth))
    results.append(F.f4_firm_vol_ks(real, synth))
    results.append(F.f5_factor_path(inputs))
    results.append(F.f6_eligibility(real, synth))
    results.append(F.f7_vol_clustering(real, synth, np.random.default_rng(SEED_BASE + 901)))
    print("F1-F7 done; running F8 null-payoff gate "
          f"({N_F8_REPS} panels x 20 signals x ~180 months)...")
    results.append(F.f8_null_payoff(inputs, N_F8_REPS, SEED_BASE + 1000))

    print()
    killed = False
    tolerance_fail = False
    for r in results:
        flag = "PASS" if r["pass"] else ("KILL" if r.get("kill") else "FAIL")
        killed |= bool(r.get("kill"))
        tolerance_fail |= not r["pass"]
        print(f"  [{flag:4s}] {r['metric']}")
        if r["metric"].startswith("F8"):
            for name, row in r["detail"].items():
                if not row["pass"]:
                    print(f"          leak: {name} "
                          f"excess={row['mean_excess_bps']}bps "
                          f"|t|={row['abs_t']} n={row['n']}")
            if r.get("warned_2to3se"):
                print(f"          2-3 SE warnings: {r['warned_2to3se']}")

    verdict = ("DGP-A REJECTED (kill criterion)" if killed
               else "FIDELITY FAIL — fix DGP before Stage 2" if tolerance_fail
               else "STAGE 1 PASS — DGP-A certified for injection")
    print("=" * 70)
    print(verdict)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "stage": 1,
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_f8_reps": N_F8_REPS,
        "seed_base": SEED_BASE,
        "beta_defaulted": inputs.n_beta_defaulted,
        "results": results,
        "verdict": verdict,
        "wall_seconds": round(time.time() - t0, 1),
    }
    out = RUNS_DIR / "stage1_fidelity.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"report -> {out}")
    return report


if __name__ == "__main__":
    main()
