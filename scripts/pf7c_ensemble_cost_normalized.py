"""T1c — the ensemble cost claim, normalised. A correction to a correction.

NIGHT-7 said the clock ensemble was "free" from a monthly-panel turnover number.
CANON §15 forbids that, external review caught it, and NIGHT-7B re-measured it
through G7 and said the ensemble is CHEAPER: $313,775 vs $333,165 per $1m.

That second claim is also unsafe, and the flaw is arithmetic rather than
statistical. Both arms start at the same NAV but do NOT end there — the single
clock (phase 5) compounds at 13.45%/yr against the ensemble's 12.90%. A book
that grows larger trades larger dollars for the same turnover RATE. So a
comparison of total cost DOLLARS silently rewards the arm that made less money.

The panel says the two arms turn over at nearly identical rates (0.468 vs 0.468
one-way). If the rates are equal and the dollar totals are not, the difference is
the NAV path, not the clock.

Three normalisations, all reported:

  cost_dollars                  the NIGHT-7B number, kept for continuity
  cost_bps_of_traded            price paid per dollar actually traded
  cost_drag_pct_per_year        cost / (average NAV x years) — the number an
                                owner of the account would feel

`days_with_capped_orders` is ALSO not comparable and is relabelled. For the
ensemble it was summed across twelve sleeves, so twelve sleeves each capped on
the same day counted twelve times. The comparable quantity is the fraction of
desired notional that failed to execute, which is computed here instead.

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
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT8"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
FIRST, LAST = "2002-01-01", "2024-12-31"
NAVS = (1_000_000.0, 50_000_000.0)
N_COHORTS = 12
SINGLE_PHASE = 5


def targets_from(H):
    tg = []
    for h in H:
        if not h.get("rebalanced"):
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


def norm(nav: pd.Series, cost: float, traded: float, unfilled: float) -> dict:
    """Everything that makes two NAV paths comparable."""
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    avg = float(nav.mean())
    return {
        "years": round(yrs, 2),
        "avg_nav": round(avg, 0),
        "final_nav": round(float(nav.iloc[-1]), 0),
        "cost_dollars": round(cost, 0),
        "turnover_dollars": round(traded, 0),
        "cost_bps_of_traded": round(cost / traded * 1e4, 2) if traded else None,
        "turnover_rate_1way_annual": round(traded / (avg * yrs), 4),
        "cost_drag_pct_per_year": round(cost / (avg * yrs) * 100, 4),
        "unfilled_notional_pct_of_desired": round(unfilled, 4),
    }


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

    sleeves, diags = {}, {}
    for k in range(N_COHORTS):
        spec = StrategySpec(**{**d, "rebalance_months": 12, "cost_model": "ko",
                               "name": f"PF7C-CLK__phase{k:02d}"})
        H: list[dict] = []
        out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
                       holdings_out=H, phase=k)
        sleeves[k] = targets_from(H)
        diags[k] = out["diag"]
    single = sleeves[SINGLE_PHASE]
    firsts = {k: v[0]["effective"] for k, v in sleeves.items() if v}
    if len(set(firsts.values())) < N_COHORTS:
        raise RuntimeError(f"cohorts did not stagger: {sorted(set(firsts.values()))}")

    permnos: set[int] = set()
    for tg in sleeves.values():
        for t in tg:
            permnos |= set(int(x) for x in t["weights"].index)
    print(f"loading daily spine, {len(permnos)} names...", flush=True)
    data = load_daily(FIRST, LAST, permnos=permnos)

    res = {
        "task": "T1c — the ensemble cost claim, normalised for the NAV path",
        "status": "REPORTED-NEVER-DECIDING",
        "corrects": ("NIGHT-7B's 'the ensemble is CHEAPER' ($313,775 vs "
                     "$333,165). Both arms start at the same NAV and end at "
                     "different ones, so total cost DOLLARS reward the arm that "
                     "compounded less. The panel says the turnover RATES are "
                     "equal (0.468 vs 0.468), which is the tell."),
        "capital_treatment": ("each NAV rung is INDEPENDENTLY re-simulated — "
                              "costs are never scaled from another rung, because "
                              "participation caps and impact are nonlinear in "
                              "size"),
        "window": [FIRST, LAST],
        "panel_turnover_rates": {str(k): diags[k]["turnover_1way_annual"]
                                 for k in range(N_COHORTS)},
        "arms": {},
    }

    for nav0 in NAVS:
        s = simulate(single, data, SimConfig(start_nav=nav0))
        g = s["diag"]
        unf = float(s["daily"]["pending_abs"].mean() / s["daily"]["nav"].mean())
        res["arms"][f"nav{int(nav0)}_single_clock_phase5"] = norm(
            s["nav"], g["cost_dollars"], g["turnover_dollars"], unf * 100)
        print(f"  ${nav0:,.0f} single  ", flush=True)

        navs, cost, turn, unfs = [], 0.0, 0.0 , []
        for k in range(N_COHORTS):
            sv = simulate(sleeves[k], data, SimConfig(start_nav=nav0 / N_COHORTS))
            navs.append(sv["nav"])
            cost += sv["diag"]["cost_dollars"]
            turn += sv["diag"]["turnover_dollars"]
            unfs.append(float(sv["daily"]["pending_abs"].mean()))
        agg = pd.concat(navs, axis=1).ffill().dropna().sum(axis=1)
        res["arms"][f"nav{int(nav0)}_ensemble_12"] = norm(
            agg, cost, turn, float(np.sum(unfs)) / float(agg.mean()) * 100)
        print(f"  ${nav0:,.0f} ensemble", flush=True)

    for nav0 in NAVS:
        a = res["arms"][f"nav{int(nav0)}_single_clock_phase5"]
        b = res["arms"][f"nav{int(nav0)}_ensemble_12"]
        res[f"reading_nav{int(nav0)}"] = {
            "dollar_cost_delta": round(b["cost_dollars"] - a["cost_dollars"], 0),
            "bps_of_traded_delta": round(b["cost_bps_of_traded"]
                                         - a["cost_bps_of_traded"], 2),
            "cost_drag_pct_yr_delta": round(b["cost_drag_pct_per_year"]
                                            - a["cost_drag_pct_per_year"], 4),
            "turnover_rate_delta": round(b["turnover_rate_1way_annual"]
                                         - a["turnover_rate_1way_annual"], 4),
            "cheaper_on_dollars": bool(b["cost_dollars"] < a["cost_dollars"]),
            "cheaper_on_bps_of_traded": bool(b["cost_bps_of_traded"]
                                             < a["cost_bps_of_traded"]),
            "cheaper_on_drag": bool(b["cost_drag_pct_per_year"]
                                    < a["cost_drag_pct_per_year"]),
        }

    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "T1c_ENSEMBLE_COST_NORMALIZED.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k.startswith("reading")},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
