"""WINNER-GENOME-1 — render the receipt into the tables the writeup uses.

    python -m scripts.wg1_report
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT

FAC = MODULE_ROOT / "data" / "factory"
FAMS = ["F1_momentum_volume", "F2_volatility", "F3_quality_momentum",
        "F4_sector_concentrated", "F5_speculative_underdogs"]
SIZ = ["S1_cap20_tournament", "S2_cap10", "S3_cap5", "S4_inverse_vol",
       "S5_risk_parity_erc", "S6_half_kelly"]


def f(x, n=2):
    return "n/a" if x is None else f"{x:+.{n}f}"


def main() -> int:
    r = json.loads((FAC / "winner_genome_1_results.json").read_text("utf-8"))
    print(f"VERDICT: {r['trial_verdict']}")
    print(f"windows {r['n_windows']}  teams/arm {r['n_teams']}  "
          f"universe {r['universe_median_size']}  "
          f"search denominator {r['search_denominator']} "
          f"({r['search_denominator_failed']} skipped)")
    print(f"runtime {r['runtime_seconds']}s\n")

    print("=== PRIMARY: Delta-median vs own vol-matched random control ===")
    print(f"{'family':26s} {'dmed':>8s} {'MDE':>7s} {'t':>6s} {'blk':>4s} "
          f"{'halves':>7s} {'verdict':>22s}")
    for k in FAMS:
        v = r["families"][k]
        print(f"{k:26s} {f(v['delta_median_pp'],3):>8s} "
              f"{v['delta_median_mde_pp']:7.3f} {v['delta_median_t']:6.2f} "
              f"{v['regime_blocks_same_sign']:>2d}/8 "
              f"{str(v['halves_agree']):>7s} {v['verdict']:>22s}")

    print("\n=== the leaderboard numbers (reported, never deciding) ===")
    print(f"{'family':26s} {'median':>8s} {'p5':>8s} {'p95':>8s} {'MAX':>8s} "
          f"{'worst':>8s} {'skew':>6s} {'vol':>6s} {'P(win)':>7s}")
    for k in FAMS:
        v, d = r["families"][k], r["families"][k]["dist"]
        print(f"{k:26s} {d['median']:8.2f} {d['p5']:8.2f} {d['p95']:8.2f} "
              f"{d['max']:8.1f} {d['min']:8.1f} {d['skew']:6.2f} "
              f"{100*v['mean_realised_ann_vol']:6.1f} "
              f"{v['p_produces_winner']:7.3f}")
    print(f"{'--- matched controls C3 ---':26s}")
    for k in FAMS:
        d = r["families"][k]["dist_c3"]
        print(f"  C3~{k:22s} {d['median']:8.2f} {d['p5']:8.2f} {d['p95']:8.2f} "
              f"{d['max']:8.1f} {d['min']:8.1f} {d['skew']:6.2f} "
              f"{100*r['families'][k]['mean_realised_ann_vol_c3']:6.1f}")
    print("\ncontrols:")
    for k, v in r["controls"].items():
        print(f"  {k:28s} " + "  ".join(f"{a}={b:.2f}" for a, b in v.items()
                                        if isinstance(b, (int, float))))
    print("\nP(arm produces the field winner):")
    for k, v in sorted(r["p_produces_winner"].items(), key=lambda x: -x[1]):
        print(f"  {k:30s} {v:.3f}")

    print("\n=== SELECTION vs SIZING ===")
    print(f"{'arm~sizing':46s} {'medwin':>7s} {'CAGR':>8s} {'careerDD':>9s} "
          f"{'r/vol':>6s} {'ruin':>6s}")
    for base in FAMS:
        for s in SIZ:
            k = f"{base}~{s}"
            v = r["sizing"].get(k)
            if not v:
                continue
            print(f"{k:46s} {v['median_window_return_pct']:7.2f} "
                  f"{v['career_cagr_median_pct']:8.2f} "
                  f"{v['career_maxdd_median_pct']:9.2f} "
                  f"{(v['return_per_unit_vol'] or 0):6.2f} "
                  f"{v['ruin_probability']:6.3f}")
        print()
    print("=== paired family - matched control, per sizing rule ===")
    for k, v in r["sizing_paired_vs_control"].items():
        print(f"  {k:48s} {v['delta_median_pp']:+7.3f}pp  MDE {v['mde_pp']:6.3f}"
              f"  t {v['t']:+6.2f}  detectable={v['detectable']}")

    print("\n=== assertions ===")
    print(json.dumps(r["assertions"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
