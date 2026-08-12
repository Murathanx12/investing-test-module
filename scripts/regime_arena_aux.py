"""REGIME-ARENA-1 — the four hypothesis tests that are DIFFERENCES, not levels.

Split out of the runner because each of these is a comparison between two arms
rather than an arm against its control, and §18 requires a difference to be
tested as a difference with its OWN standard error rather than by eyeballing
two point estimates that happen to sit on opposite sides of zero.

  H2  real state          minus the placebo (seed 0, and the 20-seed pool)
  H3  HMM                 minus the best simple observable in the same family
  H6  S_LEAKY3            minus its point-in-time twin S_VOL3
  P   the placebo ITSELF  minus the unconditional control — does a RANDOM
      partition of the trailing window change the answer at all?

    python -m scripts.regime_arena_aux
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scripts import arena_core as A                              # noqa: E402
from scripts import regime_arena_core as R                       # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "factory"
FAM = ("D1_SELECTION", "D2_WEIGHTING", "D3_RISKMODEL")
REAL = ("S_VOL3", "S_DD2", "S_TREND2", "S_YC2", "S_BREADTH3", "S_KMEANS3",
        "S_BOCPD2", "S_HMM2", "S_HMM3", "S_SUP2", "S_SUPSIG6")


def main() -> None:
    big = pd.read_parquet(OUT / "regime_arena_1_paths.parquet")
    mkt = pd.read_parquet(OUT / "arena_market.parquet").sort_values("date_ix")
    years = pd.DatetimeIndex(mkt["date"]).year.to_numpy()[R.BURN_IN:]
    g = {k: v[v.date_ix >= R.BURN_IN]["net"].to_numpy(float)
         for k, v in big.groupby("arm")}

    def L(a):
        return np.log1p(g[a])

    def test(x, y):
        r = A.ruler(x - y, years)
        return {k: r[k] for k in ("mean_ann_pct", "mde_ann_pct", "t",
                                  "detectable", "blocks", "halves_agree",
                                  "verdict")}

    out = {"trial": "REGIME-ARENA-1", "placebo_itself": {}, "H2": {},
           "H3": {}, "H6": {}}
    best_simple = {"D1_SELECTION": "S_DD2", "D2_WEIGHTING": "S_TREND2",
                   "D3_RISKMODEL": "S_VOL3"}
    for f in FAM:
        c = L(f"{f}|S_NONE|K20|c1")
        P = np.vstack([L(f"{f}|SHUF{s}|K20|c1") - c
                       for s in range(R.N_SHUFFLE_SEEDS)])
        per = P.mean(1) * 12 * 100
        out["placebo_itself"][f] = {
            "n_seeds": int(P.shape[0]),
            "seeds_positive": int((per > 0).sum()),
            "mean_pp_yr": round(float(per.mean()), 4),
            "min_pp_yr": round(float(per.min()), 4),
            "max_pp_yr": round(float(per.max()), 4),
            "pooled": test(c + P.mean(0), c),
        }
        out["H2"][f] = {}
        for s in REAL:
            d = L(f"{f}|{s}|K20|c1")
            out["H2"][f][s] = {
                "vs_placebo_seed0": test(d, L(f"{f}|S_SHUFFLE3|K20|c1")),
                "vs_placebo_pooled": test(d, c + P.mean(0)),
                "percentile_of_20_seeds": round(float(
                    (per < (d - c).mean() * 12 * 100).mean()), 3),
            }
        out["H3"][f] = {h: test(L(f"{f}|{h}|K20|c1"),
                                L(f"{f}|{best_simple[f]}|K20|c1"))
                        for h in ("S_HMM2", "S_HMM3")}
        out["H3"][f]["compared_against"] = best_simple[f]
        out["H6"][f] = test(L(f"{f}|S_LEAKY3|K20|c1"),
                            L(f"{f}|S_VOL3|K20|c1"))
    out["note"] = ("every entry is a PAIRED monthly difference between two "
                   "simulated arms, annualised x12, beside its own 80%-power "
                   "MDE. None of these is the pre-registered PRIMARY metric "
                   "(§2), which is the arm against its unconditional twin; "
                   "nothing here may promote anything.")
    p = OUT / "regime_arena_1_aux.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {p.name}")
    print(json.dumps(out["placebo_itself"], indent=1))


if __name__ == "__main__":
    main()
