"""Are adjacent points on the rebalance frontier actually different?

TRIAL-PF5-REBAL-FRONTIER-1 read UNRESOLVED: the incremental-alpha t rises with
holding period (3.12 -> 5.60) but the 18-month point dips below the 12-month
point, so the curve is neither single-peaked nor monotone, and the argmax sits
on the grid boundary where the prereg forbids extending.

Before any of that is interpreted, one question has to be answered: is the
ranking of adjacent points even measurable? These books hold the same names
from the same slate and differ only in when they trade, so their returns are
enormously correlated and their t-statistics are NOT independent draws. A
0.5 t-unit gap between neighbours may be nothing at all.

Paired monthly differences with a Newey-West t, which is the only honest way to
compare two configurations of one strategy. Reported, never deciding — the
registered verdict stands as UNRESOLVED whatever this shows.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.panel63 import annualize

OUT = MODULE_ROOT / "runs" / "PF5"
GRID = (1, 3, 6, 12, 18, 24)


def main() -> int:
    nets = {}
    for k in GRID:
        p = OUT / f"frontier_reb{k:02d}.csv"
        df = pd.read_csv(p, index_col=0, parse_dates=True)
        nets[k] = df["net"].dropna()

    common = None
    for s in nets.values():
        common = s.index if common is None else common.intersection(s.index)
    nets = {k: s.reindex(common) for k, s in nets.items()}

    rows = []
    for a, b in combinations(GRID, 2):
        d = (nets[b] - nets[a]).dropna()
        rows.append({
            "pair": f"{b}m_minus_{a}m",
            "ann_diff": round(annualize(nets[b]) - annualize(nets[a]), 4),
            "t_nw": D.nw_t(d),
            "mde_annualized": round(D.mde_annualized(d), 4),
            "corr_of_levels": round(float(nets[a].corr(nets[b])), 4),
        })

    key = [r for r in rows if r["pair"] == "24m_minus_12m"][0]
    sig = [r for r in rows if abs(r["t_nw"] or 0) >= 2.0]
    res = {
        "diagnostic": "DIAG-PF5-FRONTIER-PAIRWISE-1",
        "status": "REPORTED-NEVER-DECIDING",
        "months": int(len(common)),
        "pairs": rows,
        "headline_24_vs_12": key,
        "pairs_significant_at_t2": [r["pair"] for r in sig],
        "reading": (
            "if 24m_minus_12m is not significant, then '24 months beats annual' "
            "is not established, and the annual choice is not displaced by this "
            "grid — it is simply not shown to be the optimum either. The "
            "correlation column is the reason: these are the same names traded "
            "on different clocks, so neighbouring t-statistics move together "
            "and their ordering carries far less information than it appears."),
    }
    (OUT / "T2b_FRONTIER_PAIRWISE.json").write_text(json.dumps(res, indent=2),
                                                    encoding="utf-8")
    print(json.dumps({"headline_24_vs_12": key,
                      "significant_pairs": res["pairs_significant_at_t2"],
                      "months": res["months"]}, indent=2))
    for r in rows:
        print(f"  {r['pair']:>16s}  {r['ann_diff']:+.4f}  t {r['t_nw']:+.2f}  "
              f"MDE {r['mde_annualized']:.4f}  rho {r['corr_of_levels']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
