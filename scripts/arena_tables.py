"""Emit the report's tables straight from the receipts, so no number is retyped.

    python -m scripts.arena_tables > data/factory/arena_tables.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from aegis_brain.config import MODULE_ROOT

F = MODULE_ROOT / "data" / "factory"


def load(p):
    q = F / p
    return json.load(open(q, encoding="utf-8")) if q.exists() else None


def fnum(x, d=2):
    try:
        return f"{float(x):+.{d}f}"
    except (TypeError, ValueError):
        return "—"


def arena_tables(d, tag):
    print(f"\n### {tag} — raw, and every matching (excess CAGR %/yr vs CRSP VW)\n")
    print("| system | raw | beta-matched | vol-matched | turnover-matched | "
          "MDE (raw) | verdict (raw) |")
    print("|---|---:|---:|---:|---:|---:|---|")
    for n, v in d["systems"].items():
        r = v["raw"]
        g = lambda m: (fnum(v[m]["excess_cagr_pct"]) if m in v else "—")
        print(f"| `{n}` | {fnum(r['excess_cagr_pct'])} | {g('beta')} | "
              f"{g('vol')} | {g('turnover')} | "
              f"{r['excess_ruler']['mde_ann_pct']:.2f} | "
              f"{r['excess_ruler']['verdict']} |")

    print(f"\n### {tag} — the five A3 dimensions, MEASURED\n")
    print("| system | vol %/yr | realised beta | gross exposure | effective N |"
          " turnover 1-way/mo | cost %/yr | max DD % |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for n, v in d["systems"].items():
        r = v["raw"]
        print(f"| `{n}` | {r['vol_ann_pct']:.1f} | "
              f"{v['capm']['beta_realised']:.2f} | "
              f"{r['gross_exposure_mean']:.2f} | {r['eff_n_mean']:.1f} | "
              f"{r['turnover_1way_mean']:.2f} | {r['cost_pct_per_year']:.2f} | "
              f"{r['max_drawdown_pct']:.1f} |")

    if "cost_sensitivity" in d:
        cs = d["cost_sensitivity"]
        print(f"\n### {tag} — cost sensitivity (excess CAGR %/yr)\n")
        print("| system | 0× (gross) | 1× (decides) | 2× | cost drag |")
        print("|---|---:|---:|---:|---:|")
        for n in cs["1x"]:
            a = cs["0x"][n]["excess_cagr_pct"]
            b = cs["1x"][n]["excess_cagr_pct"]
            print(f"| `{n}` | {fnum(a)} | {fnum(b)} | "
                  f"{fnum(cs['2x'][n]['excess_cagr_pct'])} | {fnum(b - a)} |")

    if "vs_random_gross" in d:
        print(f"\n### {tag} — H3, GROSS: does the ranking beat an "
              f"equally-concentrated random draw?\n")
        print("| contrast (gross of costs) | Δ %/yr | its MDE | t | blocks | "
              "halves | verdict |")
        print("|---|---:|---:|---:|:--:|:--:|---|")
        for n, v in d["vs_random_gross"].items():
            print(f"| {n.replace('_', ' ')} | {fnum(v['mean_ann_pct'])} | "
                  f"{v['mde_ann_pct']:.2f} | {v['t']} | "
                  f"{v.get('blocks', '—')} | "
                  f"{'yes' if v.get('halves_agree') else 'no'} | "
                  f"{v['verdict']} |")

    print(f"\n### {tag} — H3, NET: every system against P4, the "
          f"volatility-matched random control\n")
    print("| system − P4 | Δ %/yr | its MDE | t | blocks | verdict |")
    print("|---|---:|---:|---:|:--:|---|")
    for n, v in d["vs_volmatched_random"].items():
        print(f"| `{n}` | {fnum(v['mean_ann_pct'])} | {v['mde_ann_pct']:.2f} | "
              f"{v['t']} | {v.get('blocks', '—')} | {v['verdict']} |")

    sw = d["notional_sweep"]
    print(f"\n### {tag} — H5, the notional sweep (excess CAGR %/yr, DECLARED "
          f"impact model C=1.0)\n")
    print("| system | " + " | ".join(f"${int(k):,}" for k in sw) + " |")
    print("|---|" + "---:|" * len(sw))
    for n in sw[list(sw)[0]]:
        print(f"| `{n}` | " + " | ".join(
            fnum(sw[k][n]["excess_cagr_pct"]) for k in sw) + " |")


def decomposition(d):
    print("\n### Amendment A10 — the decomposition, each term beside its own MDE\n")
    print("| system | term | Δ %/yr | its MDE | t | blocks | verdict |")
    print("|---|---|---:|---:|---:|:--:|---|")
    label = {"selection_gross_vs_random": "**selection** (gross vs random)",
             "exposure_raw_minus_betamatched": "**exposure** (raw − beta-matched)",
             "sizing_K10_minus_K40": "**sizing** (K=10 − K=40)",
             "execution_raw_minus_turnovermatched":
                 "**execution** (raw − turnover-matched)",
             "costs_1x_minus_0x": "**costs** (1× − 0×)",
             "beta_style_contribution": "**beta/style**"}
    for n, v in d["terms"].items():
        for t, lab in label.items():
            r = v[t]
            print(f"| `{n}` | {lab} | {fnum(r['mean_ann_pct'])} | "
                  f"{r['mde_ann_pct']:.2f} | {r['t']} | "
                  f"{r.get('blocks', '—')} | {r['verdict']} |")
        print(f"| `{n}` | **timing** | — | — | — | — | NOT_MEASURED (chunk 6) |")
        print(f"| `{n}` | **LLM** | — | — | — | — | see ABLATION-1 |")


def main():
    full = load("portfolio_arena_1_full.json")
    sub = load("portfolio_arena_1_sub.json")
    dec = load("arena_decomposition.json")
    pert = load("arena_perturbation.json")
    pmeta = load("arena_panel_meta.json")
    if full:
        arena_tables(full, "FULL ARENA (1,500-name eligible set, 263 months)")
    if sub:
        arena_tables(sub, "SUB-ARENA (40-name eligible set, 119 months)")
    if dec:
        decomposition(dec)
    print("\n### receipts\n")
    for k, v in (("panel", pmeta), ("perturbation", pert)):
        print(f"```json\n{k} = {json.dumps(v, indent=1)}\n```")


if __name__ == "__main__":
    main()
