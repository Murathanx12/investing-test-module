"""G7 — run the shippable book through daily reality.

First workload, per the night's instruction: PF-PROF-COMPOSITE-150 on the
ANNUAL clock with era-appropriate costs. The window is 2002-2024, because that
is where a real daily CRSP spine exists; the monthly comparison is restricted to
exactly the same months so the two numbers answer the same question.

The design decision that makes this a gate rather than a demo: G7 consumes the
SAME target holdings the monthly harness produced. It is not a re-implementation
of the strategy, so any difference in the outcome is attributable to daily
reality — the fill happening a day after the decision, the participation cap,
the spread actually paid, the intra-month drawdown — and not to a different
strategy having been simulated.

Reported, never deciding. G7 does not promote anything to a lane.
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
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "G7"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
FIRST, LAST = "2002-01-01", "2024-12-31"
NAV_LADDER = (1_000_000.0, 10_000_000.0, 100_000_000.0, 500_000_000.0)


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()
    d.update({"rebalance_months": 12, "cost_model": "ko",
              "name": "PF-PROF-COMPOSITE-150__ann_era"})
    spec = StrategySpec(**d)

    f = Factory()
    elig = f.eligible(spec.segment)
    score, _ = composite_score(f.lib, spec.signals, elig)
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())

    holdings: list[dict] = []
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
                   holdings_out=holdings)
    monthly_net = out["monthly"]["net"].dropna()
    print(f"monthly harness: {len(monthly_net)} months, "
          f"{len(holdings)} holdings snapshots", flush=True)

    # target books effective on the first trading day AFTER the formation close
    targets = []
    for h in holdings:
        eff = pd.Timestamp(h["test"])
        if eff < pd.Timestamp(FIRST) or eff > pd.Timestamp(LAST):
            continue
        w = pd.Series(h["weights"]).astype(float)
        w.index = [int(x) for x in w.index]
        targets.append({"effective": eff.normalize(), "weights": w[w > 0]})
    if not targets:
        raise RuntimeError("no target books inside the daily window")
    permnos = set()
    for t in targets:
        permnos |= set(int(x) for x in t["weights"].index)
    print(f"targets {len(targets)}, distinct permnos {len(permnos)}", flush=True)

    print("loading daily spine...", flush=True)
    data = load_daily(FIRST, LAST, permnos=permnos)
    print(f"daily: {data.ret.shape[0]} days x {data.ret.shape[1]} names, "
          f"{len(data.delist_ret)} delistings", flush=True)

    # monthly comparison restricted to the same months
    mn = monthly_net[(monthly_net.index >= pd.Timestamp(FIRST))
                     & (monthly_net.index <= pd.Timestamp(LAST))]
    bench = f.spine.mkt.reindex(mn.index)

    res = {
        "gate": "G7 sequential daily simulator",
        "status": "REPORTED-NEVER-DECIDING — G7 promotes nothing to a lane",
        "strategy": spec.name,
        "spec_hash": spec.spec_hash(),
        "window": [FIRST, LAST],
        "monthly_reference": {
            "months": int(len(mn)),
            "cagr": round(annualize(mn), 4),
            "excess_vs_benchmark": round(annualize(mn) - annualize(bench), 4),
            "max_drawdown_monthend": round(float(
                ((1 + mn).cumprod() / (1 + mn).cumprod().cummax() - 1).min()), 4),
            "modelled_cost_bps_annual": out["diag"]["cost_drag_annual_bps"],
            "turnover_1way_annual": out["diag"]["turnover_1way_annual"],
        },
        "capacity_ladder": {},
    }

    for nav0 in NAV_LADDER:
        cfg = SimConfig(start_nav=nav0)
        sim = simulate(targets, data, cfg)
        g = sim["diag"]
        g["excess_vs_monthly_harness_cagr"] = round(
            g["cagr"] - res["monthly_reference"]["cagr"], 4)
        res["capacity_ladder"][f"{int(nav0):d}"] = g
        sim["nav"].to_frame("nav").to_csv(OUT / f"g7_nav_{int(nav0)}.csv")
        print(f"  NAV ${nav0:,.0f}: CAGR {g['cagr']:+.4f} "
              f"(monthly {res['monthly_reference']['cagr']:+.4f})  "
              f"maxDD daily {g['max_drawdown_daily']:.3f} vs month-end "
              f"{g['max_drawdown_monthend']:.3f}  capped days "
              f"{g['days_with_capped_orders']}  cost "
              f"{g['cost_bps_of_traded']}bps", flush=True)

    small = res["capacity_ladder"][str(int(NAV_LADDER[0]))]
    res["readings"] = {
        "daily_vs_monthend_drawdown_gap": round(
            small["max_drawdown_daily"]
            - res["monthly_reference"]["max_drawdown_monthend"], 4),
        "what_the_gap_means": (
            "the monthly scorecard reports the worst MONTH-END mark. A holder "
            "lives through the daily path. The gap is the part of the "
            "experience the monthly harness never showed."),
        "capacity_reading": (
            "the NAV at which days_with_capped_orders stops being ~0 is where "
            "this book runs out of liquidity. Below that the strategy is "
            "implementable as simulated; above it, the backtest is describing "
            "a portfolio that could not have been built."),
    }
    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "G7_DAILY.json").write_text(json.dumps(res, indent=2, default=str),
                                       encoding="utf-8")
    print(json.dumps({"monthly_reference": res["monthly_reference"],
                      "readings": res["readings"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
