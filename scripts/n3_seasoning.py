"""N3 — does the edge live in fresh entrants and decay in stale incumbents?

TRIAL-N3-SEASONING-1. A diagnostic, not a strategy. It settles one narrow thing:
whether the incumbency band is a lever worth tuning, or a family to close.

Two instruments, and the second is the point:

  A  decomp.event_time_profile — buckets against the benchmark. This already
     existed and is reported for continuity with prior nights.
  B  WITHIN-MONTH: a tenure bucket's mean return minus the mean return of the
     OTHER names held in the same month. Market direction, regime and the book's
     factor tilt all cancel. Same construction as the NIGHT-7B trigger study,
     which is where this programme learned that the within-month version is the
     one worth believing.

The confound is stated in the prereg and restated here because it bounds the
conclusion: TENURE IS ENDOGENOUS. A name is still held because its score stayed
high, and score persistence correlates with returns. So this is descriptive of
where returns sat, never causal — which is enough to CLOSE the band-tuning
family if flat, and not enough to adopt anything if not.

Reported, never deciding.
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
logging.basicConfig(level=logging.ERROR)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT8"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
BUCKETS = ((1, 6), (7, 12), (13, 24), (25, 10 ** 6))
LABELS = ["m1_6", "m7_12", "m13_24", "m25_plus"]
BAR = 0.02


def bucket_of(t: int) -> str:
    for (lo, hi), lab in zip(BUCKETS, LABELS):
        if lo <= t <= hi:
            return lab
    return LABELS[-1]


def within_month(holdings: list[dict], ret: pd.DataFrame) -> dict:
    """Each bucket against the OTHER names held that month. The powered read."""
    tenure: dict[str, int] = {}
    diffs: dict[str, dict] = {k: {} for k in LABELS}
    name_months = {k: 0 for k in LABELS}

    for h in holdings:
        held = set(h["weights"].index)
        for name in list(tenure):
            if name not in held:
                tenure.pop(name)
        for name in held:
            tenure[name] = tenure.get(name, 0) + 1

        m = pd.Timestamp(h["test"])
        if m not in ret.index:
            continue
        r = ret.loc[m].reindex(list(held)).dropna()
        if len(r) < 30:
            continue
        by = {k: [] for k in LABELS}
        for name in r.index:
            by[bucket_of(tenure[name])].append(name)
        for lab, names in by.items():
            name_months[lab] += len(names)
            others = [x for x in r.index if x not in names]
            # 5 names is not a bucket and 10 is not a control group; a
            # difference computed from either is noise wearing a t-statistic
            if len(names) >= 10 and len(others) >= 20:
                diffs[lab][m] = float(r.reindex(names).mean()
                                      - r.reindex(others).mean())

    out = {}
    total = sum(name_months.values()) or 1
    for lab in LABELS:
        s = pd.Series(diffs[lab]).sort_index().dropna()
        entry = {"months": int(len(s)),
                 "name_months": name_months[lab],
                 "share_of_name_months": round(name_months[lab] / total, 4)}
        if len(s) >= 24:
            entry.update({
                "annualized_diff_pct": round(float(s.mean()) * 12, 4),
                "t_newey_west": D.nw_t(pd.Series(s.to_numpy()), lags=12),
                "mde_annualized": D.mde_annualized(s * 12)})
        else:
            entry["note"] = "fewer than 24 usable months — not interpreted"
        out[lab] = entry
    return out


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

    spec = StrategySpec(**{**d, "rebalance_months": 12, "cost_model": "ko",
                           "name": "N3__seasoning"})
    H: list[dict] = []
    run_book(f.spine.panel, score, elig, spec, f.spine.rf, era, holdings_out=H)
    ret = f.spine.panel.monthly_ret
    bench = f.spine.mkt.reindex([pd.Timestamp(h["test"]) for h in H])

    A = D.event_time_profile(H, ret, bench)
    B = within_month(H, ret)

    sig = [k for k in LABELS
           if B[k].get("t_newey_west") is not None
           and abs(B[k]["t_newey_west"]) >= 2.0]
    eff = [B[k].get("annualized_diff_pct") for k in LABELS]
    have = [e for e in eff if e is not None]
    monotone = (len(have) == len(eff)
                and (all(eff[i] >= eff[i + 1] for i in range(len(eff) - 1))
                     or all(eff[i] <= eff[i + 1] for i in range(len(eff) - 1))))
    mdes = [B[k].get("mde_annualized") for k in LABELS
            if B[k].get("mde_annualized") is not None]
    worst_mde = max(mdes) if mdes else None

    if worst_mde is not None and worst_mde > BAR:
        verdict, state = ("POWER_FAILED — the weakest bucket could not have "
                          "seen a 2%/yr difference, so a flat profile here is "
                          "not evidence the family is dead"), "POWER_FAILED"
    elif not sig:
        verdict, state = ("BAND TUNING CLOSED — no tenure bucket differs from "
                          "its fellow holdings within month, and the design "
                          "could have seen 2%/yr. Returns do not vary with "
                          "tenure, so the incumbency band cannot move them "
                          "through this channel."), "REJECTED"
    elif monotone:
        verdict, state = ("SEASONING PRESENT and monotone — register a "
                          "band-tuning trial. This diagnostic adopts nothing."), \
            "CONFIRMED"
    else:
        verdict, state = ("UNRESOLVED — a bucket differs but not monotonically, "
                          "which is more readily a composition artifact than a "
                          "seasoning effect"), "UNRESOLVED"

    res = {
        "trial": "TRIAL-N3-SEASONING-1",
        "question": "does the edge live in fresh entrants and decay in stale "
                    "incumbents?",
        "status": "REPORTED-NEVER-DECIDING",
        "prereg": "TRIALS/PREREG_N3_SEASONING.md",
        "data_grade": "crsp", "bar_pct_yr": BAR,
        "confound": ("TENURE IS ENDOGENOUS — a name is still held because its "
                     "score stayed high, and score persistence correlates with "
                     "returns. Descriptive, never causal. Enough to close the "
                     "band-tuning family if flat; not enough to adopt if not."),
        "instrument_A_vs_benchmark": A,
        "instrument_B_within_month": B,
        "significant_buckets": sig,
        "monotone": monotone,
        "worst_bucket_mde": worst_mde,
        "verdict": verdict, "state": state,
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "N3_SEASONING.json").write_text(json.dumps(res, indent=2,
                                                      default=str),
                                           encoding="utf-8")
    print("\nWITHIN-MONTH (instrument B, the powered one):")
    for k in LABELS:
        b = B[k]
        print(f"  {k:10s} {str(b.get('annualized_diff_pct')):>8}%/yr  "
              f"NW t {str(b.get('t_newey_west')):>7}  MDE "
              f"{str(b.get('mde_annualized')):>7}  share of name-months "
              f"{b['share_of_name_months']:.3f}")
    print("\nvs BENCHMARK (instrument A, reported for continuity):")
    for k in LABELS:
        a = A[k]
        print(f"  {k:10s} excess {str(a.get('excess_cagr')):>8}  "
              f"t {str(a.get('t_excess')):>7}  hazard "
              f"{str(a.get('monthly_exit_hazard')):>7}")
    print("\n" + verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
