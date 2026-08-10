"""TRIAL-PF5-REBAL-FRONTIER-1 — is annual a frontier or a fluke?

Registered in TRIALS/PREREG_PF5_REBALANCE_FRONTIER.md and committed before this
file was written. The decision rule is frozen there and read from there; nothing
in this script chooses a threshold.

The whole point is like-for-like: every point on the grid uses the SAME book
definition and the SAME era-appropriate cost frame, so the only thing that moves
is the rebalance clock. NIGHT-4 compared monthly-under-flat-25 against
annual-under-era-costs, which confounds the clock with the cost model. That
comparison is re-run here honestly, and the confound is reported as its own row.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.WARNING)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf import ledger as L
from aegis_brain.pf.engine import buy_and_hold_universe, run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "PF5"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"

GRID = (1, 3, 6, 12, 18, 24)
NEIGHBOUR_T_TOL = 1.0            # frozen in the prereg, not chosen here
SPLIT = "2001-01-01"


def point(f, base_d, k, era, elig, score) -> dict:
    """One frequency. Everything except `rebalance_months` is held fixed."""
    spec = StrategySpec(**{**base_d, "rebalance_months": k, "cost_model": "ko",
                           "name": f"PF-PROF-COMPOSITE-150__reb{k:02d}_era"})
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era)
    net = out["monthly"]["net"].dropna()
    bench = f.spine.mkt.reindex(net.index)
    ew = buy_and_hold_universe(f.spine.panel, elig, spec,
                               f.spine.rf).reindex(net.index)
    ex = (net - bench).dropna()
    pre = ex[ex.index < SPLIT]
    post = ex[ex.index >= SPLIT]

    row = {
        "rebalance_months": k,
        "spec_hash": spec.spec_hash(),
        "months": int(len(net)),
        "rebalances": out["diag"].get("rebalances"),
        "cagr_net": round(annualize(net), 4),
        "excess_cagr_net": round(annualize(net) - annualize(bench), 4),
        "t_excess_nw": D.nw_t(ex),
        "turnover_1way_annual": out["diag"]["turnover_1way_annual"],
        "cost_drag_annual_bps": out["diag"]["cost_drag_annual_bps"],
        "max_drawdown": round(float(
            ((1 + net).cumprod() / (1 + net).cumprod().cummax() - 1).min()), 4),
        "alpha_ff5_umd": D.alpha_report(net, f.factors, D.FF6, rf=f.spine.rf),
        "incremental_alpha_ff5_umd": D.alpha_report((net - ew).dropna(),
                                                    f.factors, D.FF6),
        "excess_pre_2001": round(float((1 + pre).prod() ** (12 / len(pre)) - 1), 4)
        if len(pre) else None,
        "excess_post_2001": round(float((1 + post).prod() ** (12 / len(post)) - 1),
                                  4) if len(post) else None,
        "t_excess_pre_2001_nw": D.nw_t(pre) if len(pre) > 24 else None,
        "t_excess_post_2001_nw": D.nw_t(post) if len(post) > 24 else None,
        "mde_excess_annualized": round(D.mde_annualized(ex), 4),
    }
    # the primary statistic, hoisted to the top level so read_shape sees it
    row["incr_alpha_t"] = row["incremental_alpha_ff5_umd"]["t_alpha"]
    net.to_frame("net").assign(bench=bench).to_csv(OUT / f"frontier_reb{k:02d}.csv")
    return row


def read_shape(rows: list[dict], key: str) -> dict:
    """Apply the frozen decision rule. No thresholds are invented here."""
    ts = [r[key] for r in rows]
    ks = [r["rebalance_months"] for r in rows]
    i = int(np.argmax(ts))
    peak = ts[i]

    # single-peaked = non-decreasing up to the argmax and non-increasing after
    up = all(ts[j] <= ts[j + 1] + 1e-12 for j in range(i))
    down = all(ts[j] >= ts[j + 1] - 1e-12 for j in range(i, len(ts) - 1))
    single_peaked = up and down
    monotone_up = i == len(ts) - 1 and up
    monotone_down = i == 0 and down

    nb = [ts[j] for j in (i - 1, i + 1) if 0 <= j < len(ts)]
    gaps = [round(peak - v, 3) for v in nb]
    interior = 0 < i < len(ts) - 1

    if monotone_up or monotone_down:
        verdict = "MONOTONE"
        why = ("the grid boundary is the argmax; the frontier is not interior "
               "and this grid does not contain the answer. The prereg forbids "
               "extending it on this observation.")
    elif not single_peaked:
        verdict = "UNRESOLVED"
        why = "not single-peaked and not monotone"
    elif interior and all(g > NEIGHBOUR_T_TOL for g in gaps):
        verdict = "LUCKY POINT"
        why = (f"argmax at {ks[i]}m beats BOTH neighbours by more than "
               f"{NEIGHBOUR_T_TOL} t-units (gaps {gaps}) — the win does not "
               "survive one grid step. Per the prereg the annual choice is "
               "WITHDRAWN and the shippable config reverts to undetermined.")
    else:
        verdict = "SMOOTH FRONTIER"
        why = (f"argmax at {ks[i]}m with neighbour gaps {gaps}, all within "
               f"{NEIGHBOUR_T_TOL} t-units — a broad plateau, so the frequency "
               "choice is not load-bearing.")
    return {"statistic": key, "values": dict(zip(ks, [round(v, 3) for v in ts])),
            "argmax_months": ks[i], "peak": round(peak, 3),
            "neighbour_gaps": gaps, "single_peaked": single_peaked,
            "verdict": verdict, "reading": why}


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()

    f = Factory()
    elig = f.eligible(d["segment"])
    score, _ = composite_score(f.lib, d["signals"], elig)
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())

    rows = []
    for k in GRID:
        rows.append(point(f, d, k, era, elig, score))
        print(f"  reb {k:2d}m  excess {rows[-1]['excess_cagr_net']:+.4f}  "
              f"t {rows[-1]['t_excess_nw']:.2f}  "
              f"incr-a t {rows[-1]['incremental_alpha_ff5_umd']['t_alpha']:.2f}  "
              f"turn {rows[-1]['turnover_1way_annual']:.3f}", flush=True)

    # The confound NIGHT-4 left in: monthly under FLAT 25 is not comparable to
    # annual under era costs. Re-run monthly under flat25 so the difference
    # between "the clock changed" and "the cost model changed" is visible.
    spec_flat = StrategySpec(**{**d, "rebalance_months": 1,
                                "cost_model": "flat25",
                                "name": "PF-PROF-COMPOSITE-150__reb01_flat25"})
    o = run_book(f.spine.panel, score, elig, spec_flat, f.spine.rf, f.cost_frame())
    nf = o["monthly"]["net"].dropna()
    bf = f.spine.mkt.reindex(nf.index)
    ewf = buy_and_hold_universe(f.spine.panel, elig, spec_flat,
                                f.spine.rf).reindex(nf.index)

    incr_t = [r["incr_alpha_t"] for r in rows]
    res = {
        "trial": "TRIAL-PF5-REBAL-FRONTIER-1",
        "prereg": "TRIALS/PREREG_PF5_REBALANCE_FRONTIER.md",
        "prereg_commit": "ec06dc6",
        "grid_months": list(GRID),
        "cost_model": "era-appropriate at every point (KO + mechanical tick floor)",
        "points": rows,
        "primary_read": read_shape(rows, "incr_alpha_t"),
        "secondary_read_excess_t": read_shape(rows, "t_excess_nw"),
        "confound_isolated": {
            "why": ("NIGHT-4 compared monthly/flat25 against annual/era. That "
                    "moves two things at once. These two rows isolate the "
                    "cost-model half of it."),
            "monthly_flat25": {
                "excess_cagr_net": round(annualize(nf) - annualize(bf), 4),
                "t_excess_nw": D.nw_t((nf - bf).dropna()),
                "cost_drag_annual_bps": o["diag"]["cost_drag_annual_bps"],
                "incremental_alpha_ff5_umd": D.alpha_report(
                    (nf - ewf).dropna(), f.factors, D.FF6)},
            "monthly_era": {k: rows[0][k] for k in
                            ("excess_cagr_net", "t_excess_nw",
                             "cost_drag_annual_bps",
                             "incremental_alpha_ff5_umd")},
        },
        "multiple_testing": L.testing_block(
            max(r["t_excess_nw"] for r in rows), max(incr_t)),
        "decision_branches_this_family": len(GRID) + 1,
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "T2_REBALANCE_FRONTIER.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: res[k] for k in
                      ("primary_read", "secondary_read_excess_t")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
