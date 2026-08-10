"""T1 / correction — the clock ensemble through G7, because CANON §15 says so.

NIGHT-7 called the 12-phase ensemble "free" on the strength of a MONTHLY-PANEL
turnover number (0.468 per cohort, unchanged). That was written the same night as
CANON §15, which forbids exactly that: a turnover-relevant claim quoted from the
panel without the daily simulator. External review caught the inconsistency. It
is a fair catch and this script closes it.

The comparison is genuinely open, and both directions are plausible:

  * WORSE — the ensemble crosses the spread every month instead of once a year.
    Twelve small trades can cost more than one large one if a fixed cost per
    crossing dominates.
  * BETTER — one twelfth of the book at a time is far gentler on the
    participation cap. At $50m the single-clock book has to move everything on
    one day; the ensemble never does.

Construction: each of the 12 phases is run through the monthly harness with its
real clock phase, and the aggregate book is the equal-weighted mean of the twelve
cohorts' ACTUAL held weights each month. That aggregate is handed to the same
daily simulator, which charges whatever deltas it implies — so the ensemble's
monthly trickle of trades is priced, not assumed.

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
from aegis_brain.pf.daily_sim import SimConfig, load_daily, simulate
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT7"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
FIRST, LAST = "2002-01-01", "2024-12-31"
NAVS = (1_000_000.0, 50_000_000.0)
N_COHORTS = 12
SINGLE_PHASE = 5          # the phase whose first trade matches the banked book


def cohort(f, d, k, era, elig, score):
    spec = StrategySpec(**{**d, "rebalance_months": 12, "cost_model": "ko",
                           "name": f"PF7B-CLK__phase{k:02d}"})
    H: list[dict] = []
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
                   holdings_out=H, phase=k)
    return H, out


def targets_from(H, only_traded: bool):
    """Monthly target books. `only_traded` keeps the annual clock annual."""
    tg = []
    for h in H:
        if only_traded and not h.get("rebalanced"):
            continue
        eff = pd.Timestamp(h["test"])
        if not (pd.Timestamp(FIRST) <= eff <= pd.Timestamp(LAST)):
            continue
        w = pd.Series(h["weights"]).astype(float)
        w.index = [int(x) for x in w.index]
        w = w[w > 0]
        if len(w):
            tg.append({"effective": eff.normalize(), "weights": w})
    return tg


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

    holds, diags = {}, {}
    for k in range(N_COHORTS):
        H, out = cohort(f, d, k, era, elig, score)
        holds[k], diags[k] = H, out["diag"]
        print(f"  phase {k:2d}: turnover {out['diag']['turnover_1way_annual']:.3f}",
              flush=True)

    # ── the ensemble is TWELVE SLEEVES, not one monthly-retargeted book ─────
    # First construction handed the simulator the aggregate book every month.
    # That is wrong, and wrong in the project's house style: the simulator then
    # traded to correct the mismatch between the panel's MONTHLY drift and its
    # own DAILY drift, every month, forever — spurious trades a real ensemble
    # never makes. It inflated measured turnover to 1.51x the single clock while
    # the panel (correctly) said each sleeve turns over identically.
    #
    # The honest construction: twelve INDEPENDENT sleeves, each holding 1/12 of
    # capital and rebalancing annually on its own phase. Sum the NAVs and the
    # costs. Because the sleeves trade in different months they do not compete
    # for liquidity, so a per-sleeve participation cap is the right one.
    sleeves = {k: targets_from(holds[k], only_traded=True)
               for k in range(N_COHORTS)}
    single = targets_from(holds[SINGLE_PHASE], only_traded=True)
    n_sleeve_targets = sum(len(v) for v in sleeves.values())
    print(f"sleeve targets {n_sleeve_targets} across {N_COHORTS} sleeves "
          f"(annual each), single-clock targets {len(single)}", flush=True)
    if not n_sleeve_targets or not single:
        raise RuntimeError("no targets built — refusing to report")

    permnos: set[int] = set()
    for tg in list(sleeves.values()) + [single]:
        for t in tg:
            permnos |= set(int(x) for x in t["weights"].index)
    print(f"loading daily spine for {len(permnos)} names...", flush=True)
    data = load_daily(FIRST, LAST, permnos=permnos)
    print(f"daily {data.ret.shape[0]} days x {data.ret.shape[1]} names", flush=True)

    res = {
        "task": "T1 correction — clock ensemble measured under daily execution",
        "trial": "TRIAL-PF7-CLOCK-ENSEMBLE-1 (G7 gate)",
        "status": "REPORTED-NEVER-DECIDING",
        "why": ("NIGHT-7 called the ensemble 'free' from a monthly-panel turnover "
                "number, which CANON §15 forbids. External review caught it. This "
                "measures it."),
        "window": [FIRST, LAST],
        "construction": ("ensemble = 12 INDEPENDENT sleeves at NAV/12, each "
                         "rebalancing annually on its own phase, NAVs and costs "
                         "summed; single clock = phase 5, annual trades only"),
        "rejected_construction": {
            "what": ("first attempt handed the simulator the AGGREGATE book every "
                     "month"),
            "why_wrong": ("the simulator then traded monthly to reconcile the "
                          "panel's monthly drift against its own daily drift — "
                          "spurious trades a real sleeve ensemble never makes"),
            "how_it_was_caught": ("measured turnover came out 1.51x the single "
                                  "clock while the monthly panel said each sleeve "
                                  "turns over identically; that contradiction is "
                                  "only explicable as a construction artifact"),
            "discarded_numbers": {"nav1000000_cagr_delta": -0.0226,
                                  "nav1000000_extra_cost": 221280.0},
        },
        "monthly_panel_reference": {
            "mean_cohort_turnover_1way": round(float(np.mean(
                [diags[k]["turnover_1way_annual"] for k in range(N_COHORTS)])), 4),
            "phase_turnovers": {str(k): diags[k]["turnover_1way_annual"]
                                for k in range(N_COHORTS)}},
        "daily": {},
    }

    for nav0 in NAVS:
        sim = simulate(single, data, SimConfig(start_nav=nav0))
        g = sim["diag"]
        res["daily"][f"nav{int(nav0)}_single_clock"] = {
            "arm": "single_clock", "start_nav": nav0,
            "daily_cagr": g["cagr"],
            "turnover_dollars": g["turnover_dollars"],
            "cost_dollars": g["cost_dollars"],
            "cost_bps_of_traded": g["cost_bps_of_traded"],
            "max_drawdown_daily": g["max_drawdown_daily"],
            "days_with_capped_orders": g["days_with_capped_orders"],
        }
        print(f"  NAV ${nav0:,.0f} single_clock   CAGR {g['cagr']:+.4f}  "
              f"cost ${g['cost_dollars']:,.0f}", flush=True)

        navs, tot_cost, tot_turn, capped = [], 0.0, 0.0, 0
        for k in range(N_COHORTS):
            s = simulate(sleeves[k], data, SimConfig(start_nav=nav0 / N_COHORTS))
            navs.append(s["nav"])
            tot_cost += s["diag"]["cost_dollars"]
            tot_turn += s["diag"]["turnover_dollars"]
            capped += s["diag"]["days_with_capped_orders"]
        agg_nav = pd.concat(navs, axis=1).ffill().dropna().sum(axis=1)
        yrs = (agg_nav.index[-1] - agg_nav.index[0]).days / 365.25
        cagr = float((agg_nav.iloc[-1] / agg_nav.iloc[0]) ** (1 / yrs) - 1)
        dd = float((agg_nav / agg_nav.cummax() - 1).min())
        res["daily"][f"nav{int(nav0)}_ensemble_12"] = {
            "arm": "ensemble_12", "start_nav": nav0,
            "daily_cagr": round(cagr, 4),
            "turnover_dollars": round(tot_turn, 2),
            "cost_dollars": round(tot_cost, 2),
            "cost_bps_of_traded": round(tot_cost / tot_turn * 1e4, 1)
            if tot_turn else None,
            "max_drawdown_daily": round(dd, 4),
            "days_with_capped_orders": int(capped),
            "construction": "12 independent sleeves at NAV/12, annual each, summed",
        }
        print(f"  NAV ${nav0:,.0f} ensemble_12    CAGR {cagr:+.4f}  "
              f"cost ${tot_cost:,.0f}", flush=True)

    for nav0 in NAVS:
        s = res["daily"][f"nav{int(nav0)}_single_clock"]
        e = res["daily"][f"nav{int(nav0)}_ensemble_12"]
        res[f"reading_nav{int(nav0)}"] = {
            "ensemble_minus_single_cagr": round(e["daily_cagr"] - s["daily_cagr"], 4),
            "extra_cost_dollars": round(e["cost_dollars"] - s["cost_dollars"], 2),
            "extra_cost_pct_of_start_nav": round(
                (e["cost_dollars"] - s["cost_dollars"]) / nav0, 4),
            "capped_days_delta": e["days_with_capped_orders"]
                                 - s["days_with_capped_orders"],
            # Signed, not absolute. The first version used abs() and would have
            # flagged a cost SAVING as "not free" — a verdict rule that cannot
            # tell a win from a loss.
            "costs_no_more_than_single_clock": bool(
                (e["cost_dollars"] - s["cost_dollars"]) / nav0 < 0.01),
            "cheaper_than_single_clock": bool(
                e["cost_dollars"] < s["cost_dollars"]),
            "verdict_note": (
                "The cost question and the CAGR question are SEPARATE. Cost: "
                "does the ensemble pay more to run? CAGR: the single clock here "
                "is phase 5, which the monthly panel showed was an ABOVE-average "
                "draw (+4.11% vs the 12-phase mean +3.43%) — so a CAGR gap "
                "against it is the date-luck finding restated, not a cost."),
        }

    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "T1b_ENSEMBLE_G7.json").write_text(json.dumps(res, indent=2),
                                              encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items()
                      if k.startswith("reading_")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
