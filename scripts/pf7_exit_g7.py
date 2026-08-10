"""TRIAL-PF7-EXIT-SWEEP-1, gate step — A1's churn cost, MEASURED not modelled.

The monthly sweep put the trailing stop at the TOP of the arms (+0.34%/yr net
over the baseline) while trading 2.7x as much. NIGHT-6's G7 clock compare found
the monthly panel understates the cost of frequent trading by roughly 2.7x, so
that ranking is exactly the kind that the panel is known to fabricate. The
prereg's turnover gate therefore forbids quoting A1's net number until the
daily simulator has measured it.

This runs A0 and A1 through the SAME daily spine on the same window, consuming
the target books the monthly harness produced (no re-implementation), so the
difference is attributable to daily execution and nothing else.

Reported, never deciding.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.ERROR)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.daily_sim import SimConfig, load_daily, simulate
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.exits import build_arms
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT7"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
FIRST, LAST = "2002-01-01", "2024-12-31"
NAVS = (1_000_000.0, 50_000_000.0)
ARMS = ("A0_baseline", "A1_trailing_stop")


def build(f, base_d, key, rule, era, elig, score, mom):
    spec = StrategySpec(**{**base_d, "rebalance_months": 12, "cost_model": "ko",
                           "name": f"PF7-EXIT__{key}"})
    H: list[dict] = []
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
                   exit_rule=rule, mom=mom, holdings_out=H)
    tg = []
    for h in H:
        if not h.get("rebalanced"):
            continue
        eff = pd.Timestamp(h["test"])
        if not (pd.Timestamp(FIRST) <= eff <= pd.Timestamp(LAST)):
            continue
        w = pd.Series(h["weights"]).astype(float)
        w.index = [int(x) for x in w.index]
        tg.append({"effective": eff.normalize(), "weights": w[w > 0]})
    net = out["monthly"]["net"].dropna()
    net = net[(net.index >= FIRST) & (net.index <= LAST)]
    return spec, tg, net, out["diag"]


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
    mom = f.lib.get("native:mom_12_1")
    arms = build_arms(top_n=d["top_n"], hold_band_mult=d["hold_band_mult"])

    built, permnos = {}, set()
    for k in ARMS:
        spec, tg, net, diag = build(f, d, k, arms[k], era, elig, score, mom)
        built[k] = {"spec": spec, "targets": tg, "monthly_net": net, "diag": diag}
        for t in tg:
            permnos |= set(int(x) for x in t["weights"].index)
        print(f"{k:20s}: {len(tg)} trade dates in window, monthly CAGR "
              f"{annualize(net):+.4f}, modelled turnover "
              f"{diag['turnover_1way_annual']:.3f}, modelled cost "
              f"{diag['cost_drag_annual_bps']}bps", flush=True)

    print(f"loading daily spine for {len(permnos)} names...", flush=True)
    data = load_daily(FIRST, LAST, permnos=permnos)
    print(f"daily {data.ret.shape[0]} days x {data.ret.shape[1]} names",
          flush=True)

    res = {"gate": "G7 daily execution — PF-7 exit arms",
           "trial": "TRIAL-PF7-EXIT-SWEEP-1",
           "status": "REPORTED-NEVER-DECIDING",
           "question": ("the monthly panel ranks the trailing stop FIRST while "
                        "it trades 2.7x as much. Does that survive measurement "
                        "under daily execution?"),
           "window": [FIRST, LAST], "arms": {}}

    for nav0 in NAVS:
        for k in ARMS:
            sim = simulate(built[k]["targets"], data, SimConfig(start_nav=nav0))
            g = sim["diag"]
            mnet = built[k]["monthly_net"]
            res["arms"][f"nav{int(nav0)}_{k}"] = {
                "arm": k, "start_nav": nav0,
                "daily_cagr": g["cagr"],
                "monthly_harness_cagr": round(annualize(mnet), 4),
                "daily_minus_monthly": round(g["cagr"] - annualize(mnet), 4),
                "turnover_dollars": g["turnover_dollars"],
                "cost_dollars": g["cost_dollars"],
                "cost_bps_of_traded": g["cost_bps_of_traded"],
                "max_drawdown_daily": g["max_drawdown_daily"],
                "days_with_capped_orders": g["days_with_capped_orders"],
                "modelled_cost_bps_annual": built[k]["diag"][
                    "cost_drag_annual_bps"],
                "modelled_turnover": built[k]["diag"]["turnover_1way_annual"],
            }
            print(f"  NAV ${nav0:,.0f} {k:20s} daily CAGR {g['cagr']:+.4f} "
                  f"(monthly {annualize(mnet):+.4f}) cost ${g['cost_dollars']:,.0f}",
                  flush=True)

    for nav0 in NAVS:
        a0 = res["arms"][f"nav{int(nav0)}_A0_baseline"]
        a1 = res["arms"][f"nav{int(nav0)}_A1_trailing_stop"]
        res[f"reading_nav{int(nav0)}"] = {
            "monthly_panel_says_A1_minus_A0": round(
                a1["monthly_harness_cagr"] - a0["monthly_harness_cagr"], 4),
            "daily_execution_says_A1_minus_A0": round(
                a1["daily_cagr"] - a0["daily_cagr"], 4),
            "flip": bool(
                (a1["monthly_harness_cagr"] - a0["monthly_harness_cagr"]) > 0
                > (a1["daily_cagr"] - a0["daily_cagr"])),
            "extra_dollars_of_cost_A1_pays": round(
                a1["cost_dollars"] - a0["cost_dollars"], 2),
            "extra_cost_as_pct_of_start_nav": round(
                (a1["cost_dollars"] - a0["cost_dollars"]) / nav0, 4),
        }

    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "T2b_EXIT_G7.json").write_text(json.dumps(res, indent=2),
                                          encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items()
                      if k.startswith("reading_")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
