"""EXPOSURE-ARENA-1 — turn the artifacts into the tables the report quotes.

Prints markdown. Writes nothing except stdout, so a table in
`aegis-finance/docs/GRAND_ARENA_EXPOSURE.md` can always be regenerated from the
receipts rather than retyped.

    python -m scripts.exposure_arena_report            # everything
    python -m scripts.exposure_arena_report --bed BED1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(__file__).resolve().parents[1] / "data" / "factory"


def rd(name):
    p = OUT / f"exposure_arena_1_{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def frontier_table(fr, bed):
    print(f"\n### Frontier — {bed} (constant exposure, built before any "
          f"controller)\n")
    print("| w̄ | net CAGR pp/yr | maxDD | CVaR5 monthly | P(ruin) | vol% |")
    print("|---:|---:|---:|---:|---:|---:|")
    for r in fr["frontier"][bed]:
        print(f"| {r['wbar']:.2f} | {r['net_cagr_pp']:.3f} | "
              f"{r['max_drawdown']:.1%} | {r['cvar5_monthly']:.2%} | "
              f"{r['p_ruin']:.3f} | {r['vol_ann_pct']:.1f} |")


def headline_table(sc, bed, primary_only=True):
    arms = [a for a in sc["beds"][bed]["arms"]
            if (a.get("primary") or not primary_only)]
    arms.sort(key=lambda a: -a["D_matched"]["delta_pp_yr"])
    print(f"\n### {bed} — the matched-exposure comparison (the headline)\n")
    print("| controller | w̄ | net CAGR | matched CAGR | **D_matched pp/yr** | "
          "**its MDE** | t | blocks | halves | verdict |")
    print("|---|---:|---:|---:|---:|---:|---:|:--:|:--:|---|")
    for a in arms:
        d = a["D_matched"]
        s = a["sign_consistency_vs_matched"]
        print(f"| `{a['id']}` | {a['metrics']['mean_exposure']:.3f} | "
              f"{a['metrics']['net_cagr_pp']:.3f} | "
              f"{a['matched_control']['metrics']['net_cagr_pp']:.3f} | "
              f"**{d['delta_pp_yr']:+.3f}** | {d['mde80_pp_yr']:.3f} | "
              f"{d['t'] if d['t'] is not None else '—'} | "
              f"{s['n_blocks_same_sign']}/{s['n_blocks']} | "
              f"{'yes' if s['both_halves_same_sign'] else 'no'} | "
              f"{a['verdict']} |")


def risk_table(sc, bed):
    arms = [a for a in sc["beds"][bed]["arms"] if a.get("primary")]
    arms.sort(key=lambda a: a["metrics"]["max_drawdown"])
    print(f"\n### {bed} — risk profiles, controller vs its OWN matched cousin\n")
    print("| controller | maxDD | matched maxDD | Δdd pp [MDE] | CVaR5 | "
          "matched CVaR5 | P(ruin) | matched P(ruin) | % days de-risked | "
          "turnover/yr | cost bps/yr |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for a in arms:
        m, mm = a["metrics"], a["matched_control"]["metrics"]
        dd = a["dd_vs_matched"]
        print(f"| `{a['id']}` | {m['max_drawdown']:.1%} | "
              f"{mm['max_drawdown']:.1%} | {dd['dd_diff_pp']:+.1f} "
              f"[{dd['mde80_pp'] if dd['mde80_pp'] is not None else 'n/a'}] | "
              f"{m['cvar5_monthly']:.2%} | {mm['cvar5_monthly']:.2%} | "
              f"{a['p_ruin']['p_ruin']:.3f} | "
              f"{a['p_ruin_matched']['p_ruin']:.3f} | "
              f"{m['pct_days_derisked']:.1%} | "
              f"{m['turnover_oneway_yr']:.2f} | {m['costs_bps_yr']:.1f} |")


def decomp_table(sc, bed):
    arms = [a for a in sc["beds"][bed]["arms"] if a.get("primary")]
    arms.sort(key=lambda a: -a["D_vs_full"]["delta_pp_yr"])
    print(f"\n### {bed} — the §A10 decomposition (vs 100% exposure)\n")
    print("| controller | Δ vs FULL pp/yr | its MDE | avoided-loss | "
          "missed-upside | costs | bull cap | bear cap | re-entry eff pp/yr | "
          "spells |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for a in arms:
        m = a["metrics"]
        d = a["D_vs_full"]
        print(f"| `{a['id']}` | {d['delta_pp_yr']:+.3f} | "
              f"{d['mde80_pp_yr']:.3f} | {m['avoided_loss_pp_yr']:+.3f} | "
              f"{m['missed_upside_pp_yr']:+.3f} | "
              f"{m['costs_bps_yr']/100:.3f} | "
              f"{m['bull_capture']:.3f} | {m['bear_capture']:.3f} | "
              f"{m['reentry_efficiency_pp_yr'] if m['reentry_efficiency_pp_yr'] is not None else '—'} | "
              f"{m['n_derisk_spells']} |")


def cost_table(sc, bed):
    arms = [a for a in sc["beds"][bed]["arms"]
            if a.get("cost_sensitivity_D_matched_pp_yr")]
    print(f"\n### {bed} — cost sensitivity of D_matched (pp/yr)\n")
    print("| controller | 0x (gross) | 1x (decides) | 2x | 4x |")
    print("|---|---:|---:|---:|---:|")
    for a in arms:
        c = a["cost_sensitivity_D_matched_pp_yr"]
        print(f"| `{a['id']}` | {c['0x']:+.3f} | {c['1x']:+.3f} | "
              f"{c['2x']:+.3f} | {c['4x']:+.3f} |")


def full_grid(sc, bed):
    arms = sorted(sc["beds"][bed]["arms"],
                  key=lambda a: -a["D_matched"]["delta_pp_yr"])
    print(f"\n### {bed} — EVERY executed configuration, best D_matched first\n")
    print("| # | controller | w̄ | D_matched pp/yr | its MDE | ratio | verdict |")
    print("|---:|---|---:|---:|---:|---:|---|")
    for i, a in enumerate(arms, 1):
        d = a["D_matched"]
        ratio = (abs(d["delta_pp_yr"]) / d["mde80_pp_yr"]
                 if d["mde80_pp_yr"] else float("nan"))
        print(f"| {i} | `{a['id']}` | {a['metrics']['mean_exposure']:.3f} | "
              f"{d['delta_pp_yr']:+.3f} | {d['mde80_pp_yr']:.3f} | "
              f"{ratio:.2f}x | {a['verdict']} |")


def blocks_table(sc, bed):
    arms = [a for a in sc["beds"][bed]["arms"] if a.get("primary")]
    keys = None
    for a in arms:
        keys = list(a["sign_consistency_vs_matched"]["blocks"])
        break
    print(f"\n### {bed} — D_matched by regime block (pp/yr)\n")
    print("| controller | " + " | ".join(keys) + " | H1 | H2 |")
    print("|---" * (len(keys) + 3) + "|")
    for a in arms:
        s = a["sign_consistency_vs_matched"]
        cells = []
        for k in keys:
            v = s["blocks"][k]
            cells.append("—" if v is None else f"{v:+.2f}")
        print(f"| `{a['id']}` | " + " | ".join(cells) +
              f" | {s['half1_pp_yr']:+.2f} | {s['half2_pp_yr']:+.2f} |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bed", default=None)
    a = ap.parse_args()
    sc, fr, su = rd("scored"), rd("frontier"), rd("summary")
    beds = [a.bed] if a.bed else list(sc["beds"])
    for b in beds:
        frontier_table(fr, b)
        headline_table(sc, b)
        risk_table(sc, b)
        decomp_table(sc, b)
        cost_table(sc, b)
        blocks_table(sc, b)
        full_grid(sc, b)
        print(f"\n§20 batch self-check {b}: "
              f"{json.dumps(sc['beds'][b]['batch_selfcheck'])}")
    if su:
        print("\n### summary\n")
        print(json.dumps({k: su[k] for k in ("search_denominator", "headline",
                                             "per_bed")}, indent=1))


if __name__ == "__main__":
    main()
