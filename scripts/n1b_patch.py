"""N1B patch — the two axes the first run reported as `None`, and why.

Both failures were mine, both were silent, and both are the kind this programme
insists on printing rather than quietly fixing:

  `membership`  the axis reported None for all three arms rather than raising —
                exactly the silent-fragility failure mode the house rules name.
                It came from reading holdings through `run_book`'s snapshot list
                and losing the alignment on the way. The FIRST attempted fix was
                wrong and made it worse: it blamed parquet for turning permno
                labels into strings and cast them to int, when the CRSP panel's
                own columns are `object` — so the cast produced zero eligible
                names a month and reproduced the same None from the opposite
                cause. Recomputed here straight from the frozen scores, labels
                untouched, verified against `elig.columns.dtype` first.

  `phase`       `run_book`'s diag block has no `cagr_net` or `excess_cagr` key.
                Reading a key that does not exist returned None twelve times
                over, and the phase range came out None. CAGR has to be
                annualised from the monthly net series.

Nothing here re-fits a model. It recomputes two decompositions of the same
frozen predictions and merges them into the existing receipt.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))
sys.path.insert(0, str(HERE))
logging.basicConfig(level=logging.ERROR)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.spec import StrategySpec

from n1b_where_does_the_ic_live import FROZEN, OUT, build_world

RECEIPT = OUT / "N1B_WHERE_DOES_THE_IC_LIVE.json"
ARMS = ("R0_composite", "R1_gbm_narrow", "R2_gbm_wide", "R3_mlp_wide")
TOP_N = 150
PHASE_ARMS = ("R0_composite", "R2_gbm_wide")


def load_frozen() -> dict[str, pd.DataFrame]:
    """Load as written. Do NOT "fix" the column dtype.

    The first version of this patch cast the permno columns to `int`, on the
    theory that parquet had corrupted them. It had not: the CRSP panel's own
    columns are `object`, so the string labels coming out of parquet were the
    ones that aligned, and the cast silently produced ZERO eligible names per
    month — the same None output the patch was written to fix, from the
    opposite cause. Verified against `elig.columns.dtype` before rerunning.
    """
    return {a: pd.read_parquet(FROZEN / f"{a}.parquet") for a in ARMS}


def top_sets(score: pd.DataFrame, elig: pd.DataFrame, months, n=TOP_N):
    sets = {}
    for m in months:
        if m not in score.index or m not in elig.index:
            continue
        s = score.loc[m].where(elig.loc[m]).dropna()
        if len(s) < n:
            continue
        sets[m] = pd.Index(s.nlargest(n).index)
    return sets


def membership(base_sets, arm_sets, label: pd.DataFrame) -> dict:
    rows = []
    for m in sorted(set(base_sets) & set(arm_sets)):
        if m not in label.index:
            continue
        A, B = base_sets[m], arm_sets[m]
        dropped, added = A.difference(B), B.difference(A)
        lab = label.loc[m]
        rd, ra = lab.reindex(dropped).dropna(), lab.reindex(added).dropna()
        if len(rd) < 5 or len(ra) < 5:
            continue
        rows.append({"month": m, "overlap": len(A.intersection(B)) / len(A),
                     "n_swapped": len(dropped),
                     "r_dropped": float(rd.mean()), "r_added": float(ra.mean()),
                     "r_common": float(lab.reindex(A.intersection(B))
                                       .dropna().mean()),
                     "loss": float(rd.mean() - ra.mean())})
    if not rows:
        return {"rebalances": 0, "insufficient": True,
                "why": "no month had five names on each side of the swap"}
    df = pd.DataFrame(rows).set_index("month")
    d = df["loss"]
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    return {
        "rebalances": int(len(df)),
        "mean_overlap": round(float(df["overlap"].mean()), 4),
        "mean_swapped_per_rebalance": round(float(df["n_swapped"].mean()), 1),
        "r_dropped": round(float(df["r_dropped"].mean()), 5),
        "r_added": round(float(df["r_added"].mean()), 5),
        "r_common": round(float(df["r_common"].mean()), 5),
        "replacement_loss": round(float(d.mean()), 5),
        "t_iid": round(float(d.mean() / se), 2) if se > 0 else None,
        "mde_at_t2": round(2.0 * se, 5),
        "share_of_rebalances_loss_positive": round(float((d > 0).mean()), 3),
        "unit": "forward 12m log return, demeaned within month",
        "reading": ("POSITIVE replacement loss means the names the learned "
                    "ranker DROPPED went on to beat the names it ADDED — the "
                    "model is worse exactly where selection happens"),
    }


def main() -> int:
    t0 = time.time()
    f, d, elig, era, ret, label = build_world()
    scores = load_frozen()
    res = json.loads(RECEIPT.read_text(encoding="utf-8"))
    window = res["reproduction_gate"]["window"]

    first = pd.Timestamp(window["first_month"])
    months = [m for m in ret.index if m >= first]
    reb = [m for i, m in enumerate(months) if i % 12 == 0]
    print(f"membership on {len(reb)} rebalance formation months", flush=True)

    base_sets = top_sets(scores["R0_composite"], elig, reb)
    fixed = {}
    for a in ARMS[1:]:
        fixed[a] = membership(base_sets, top_sets(scores[a], elig, reb), label)
        r = fixed[a]
        print(f"  {a:16s} overlap {r.get('mean_overlap')}  swapped "
              f"{r.get('mean_swapped_per_rebalance')}  dropped "
              f"{r.get('r_dropped')} vs added {r.get('r_added')}  LOSS "
              f"{r.get('replacement_loss')} (t {r.get('t_iid')}, MDE "
              f"{r.get('mde_at_t2')})", flush=True)

    print("\nphase axis, with CAGR annualised rather than read from a key "
          "that never existed", flush=True)
    bench = f.spine.mkt
    phase: dict = {}
    for a in PHASE_ARMS:
        per = {}
        for ph in range(12):
            spec = StrategySpec(**{**d, **window, "rebalance_months": 12,
                                   "cost_model": "ko",
                                   "name": f"N1Bp__{a}__ph{ph}"})
            try:
                out = run_book(f.spine.panel, scores[a].astype(np.float32),
                               elig, spec, f.spine.rf, era)
            except RuntimeError as e:
                per[ph] = {"error": str(e)[:120]}
                continue
            net = out["monthly"]["net"].dropna()
            b = bench.reindex(net.index)
            per[ph] = {"cagr_net": round(annualize(net), 4),
                       "excess_cagr": round(annualize(net) - annualize(b), 4),
                       "turnover": out["diag"]["turnover_1way_annual"],
                       "rebalances": out["diag"]["rebalances"]}
        got = [v["excess_cagr"] for v in per.values() if "excess_cagr" in v]
        phase[a] = {"per_phase": per,
                    "excess_cagr_min": min(got) if got else None,
                    "excess_cagr_max": max(got) if got else None,
                    "range_pt_per_year": round((max(got) - min(got)) * 100, 3)
                    if got else None,
                    "n_phases_positive": sum(1 for x in got if x > 0)}
        print(f"  {a:16s} excess CAGR {min(got):+.4f} .. {max(got):+.4f}  "
              f"range {phase[a]['range_pt_per_year']:.2f} pt/yr  "
              f"positive in {phase[a]['n_phases_positive']}/12", flush=True)

    res["membership"] = fixed
    res["phase"] = {"arms_run": list(PHASE_ARMS), "results": phase,
                    "note": "12 phases x 2 arms; the other two arms were not "
                            "run and nothing is claimed about them"}
    res["patch"] = {
        "applied": "2026-08-10 NIGHT-9",
        "fixed": ["membership: the axis reported None for all three arms "
                  "instead of raising. The first diagnosis (parquet corrupting "
                  "permno labels) was WRONG and its fix made the failure worse "
                  "— the panel's own columns are object, so casting to int gave "
                  "zero eligible names. Recomputed directly from the frozen "
                  "scores with the labels left alone.",
                  "phase: run_book's diag has no cagr key; CAGR is annualised "
                  "from the monthly net series against the market benchmark"],
        "models_refitted": 0,
    }
    res["runtime_secs_patch"] = round(time.time() - t0, 1)
    RECEIPT.write_text(json.dumps(res, indent=2, default=str),
                       encoding="utf-8")
    print(f"\nmerged into {RECEIPT.name}. {res['runtime_secs_patch']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
