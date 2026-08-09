"""G7 on BOTH clocks — the annual-vs-monthly question, under daily execution.

NIGHT-5 established that the six rebalance clocks are statistically
indistinguishable on the monthly panel: none of 15 pairwise differences was
significant, level correlations 0.958-0.993. The claim that survived was the
MECHANICAL one — annual trades a fifth as much, so it pays a quarter of the
cost — and that claim was asserted from a modelled cost frame, never measured
under execution.

G7 can measure it. Running the same book on the monthly and annual clocks
through the daily simulator charges each one the spread it would actually have
paid, on the days it would actually have traded, with orders capped by real
volume. If annual's advantage is real anywhere, it is here, and it should be
LARGER under daily execution than under the monthly model, because the monthly
harness cannot see participation limits at all.

The prereg's grid is not re-opened: this is the SAME two clocks already
registered, measured with a different instrument. Reported, never deciding.
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

OUT = MODULE_ROOT / "runs" / "G7"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
FIRST, LAST = "2002-01-01", "2024-12-31"
CLOCKS = (1, 12)
NAVS = (1_000_000.0, 50_000_000.0)


def targets_for(f, base_d, reb, era, elig, score):
    spec = StrategySpec(**{**base_d, "rebalance_months": reb, "cost_model": "ko",
                           "name": f"PF-PROF-COMPOSITE-150__clk{reb}"})
    H: list[dict] = []
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
                   holdings_out=H)
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

    built, permnos = {}, set()
    for reb in CLOCKS:
        spec, tg, net, diag = targets_for(f, d, reb, era, elig, score)
        built[reb] = {"spec": spec, "targets": tg, "monthly_net": net,
                      "diag": diag}
        for t in tg:
            permnos |= set(int(x) for x in t["weights"].index)
        print(f"clock {reb:2d}m: {len(tg)} rebalances, monthly CAGR "
              f"{annualize(net):+.4f}, modelled turnover "
              f"{diag['turnover_1way_annual']:.3f}", flush=True)

    print(f"loading daily spine for {len(permnos)} names...", flush=True)
    data = load_daily(FIRST, LAST, permnos=permnos)
    print(f"daily {data.ret.shape[0]} days x {data.ret.shape[1]} names",
          flush=True)

    res = {"diagnostic": "G7-CLOCK-COMPARE",
           "status": "REPORTED-NEVER-DECIDING",
           "question": ("does annual's mechanical cost advantage survive being "
                        "MEASURED under daily execution, rather than modelled?"),
           "clocks": {}}
    navs_out = {}
    for nav0 in NAVS:
        for reb in CLOCKS:
            sim = simulate(built[reb]["targets"], data, SimConfig(start_nav=nav0))
            g = sim["diag"]
            key = f"nav{int(nav0)}_clk{reb}"
            navs_out[key] = sim["nav"]
            mnet = built[reb]["monthly_net"]
            res["clocks"][key] = {
                "clock_months": reb, "start_nav": nav0,
                "daily_cagr": g["cagr"],
                "monthly_harness_cagr": round(annualize(mnet), 4),
                "daily_minus_monthly": round(g["cagr"] - annualize(mnet), 4),
                "turnover_dollars": g["turnover_dollars"],
                "cost_dollars": g["cost_dollars"],
                "cost_bps_of_traded": g["cost_bps_of_traded"],
                "max_drawdown_daily": g["max_drawdown_daily"],
                "days_with_capped_orders": g["days_with_capped_orders"],
                "delistings_handled": g["delistings_handled"]}
            print(f"  NAV {nav0:>12,.0f} clock {reb:2d}m: daily CAGR "
                  f"{g['cagr']:+.4f}  cost ${g['cost_dollars']:,.0f}  "
                  f"capped {g['days_with_capped_orders']}", flush=True)

    # the comparison the monthly panel could not make
    for nav0 in NAVS:
        a = res["clocks"][f"nav{int(nav0)}_clk12"]
        m = res["clocks"][f"nav{int(nav0)}_clk1"]
        na = navs_out[f"nav{int(nav0)}_clk12"]
        nm = navs_out[f"nav{int(nav0)}_clk1"]
        idx = na.index.intersection(nm.index)
        dd = (na.reindex(idx).pct_change() - nm.reindex(idx).pct_change()).dropna()
        res[f"annual_minus_monthly_nav{int(nav0)}"] = {
            "daily_cagr_gap": round(a["daily_cagr"] - m["daily_cagr"], 4),
            "cost_dollars_saved": round(m["cost_dollars"] - a["cost_dollars"], 0),
            "cost_saved_as_pct_of_start_nav": round(
                (m["cost_dollars"] - a["cost_dollars"]) / nav0, 3),
            "turnover_ratio_annual_over_monthly": round(
                a["turnover_dollars"] / m["turnover_dollars"], 3)
            if m["turnover_dollars"] else None,
            "t_paired_daily_nw": round(float(
                dd.mean() / (dd.std() / np.sqrt(len(dd)))), 2) if len(dd) > 30
            else None,
            "reading": ("the cost saving is MECHANICAL and certain; the CAGR "
                        "gap is a return difference and must be read against "
                        "its own noise, not against the cost saving")}
        print(f"\nNAV {nav0:,.0f} annual-minus-monthly: "
              f"{json.dumps(res[f'annual_minus_monthly_nav{int(nav0)}'], indent=1)}",
              flush=True)

    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "G7_CLOCK_COMPARE.json").write_text(json.dumps(res, indent=2,
                                                          default=str),
                                               encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
