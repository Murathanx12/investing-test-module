"""G8 — the impact term, calibrated, then pointed at the capacity question.

TRIAL-G8-IMPACT-AND-CAPACITY-1, prereg `TRIALS/PREREG_G8_IMPACT_AND_CAPACITY.md`.

Part A re-runs NIGHT-8's synthetic null: the same worlds whose liquidity differs
by a factor of a million, through G7 (which returned 31.00 bps at every one of
them) and through G8 (which must not).

Part B re-simulates the real book's capacity ladder. Rungs are re-simulated,
never scaled — CANON 16.

Every number here is quoted with the coefficient that produced it. A capacity
figure without its scenario is not a result, it is a rumour.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))
sys.path.insert(0, str(HERE))
logging.basicConfig(level=logging.ERROR)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.daily_sim import SimConfig, load_daily, simulate
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.impact import SCENARIOS, describe
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

from n7_capacity_instrument_calibration import build_world     # the same worlds

OUT = MODULE_ROOT / "runs" / "NIGHT9"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
G7_RECEIPT = MODULE_ROOT / "runs" / "G7" / "G7_DAILY.json"
FIRST, LAST = "2002-01-01", "2024-12-31"
SEED = 20260810

ADV_RUNGS = (1e6, 100.0, 5.0, 1.0)
NAV_RUNGS = (1_000_000.0, 10_000_000.0, 50_000_000.0, 100_000_000.0,
             250_000_000.0)
#: the low/high band is run at the rungs where the answer is decided
BAND_RUNGS = (50_000_000.0, 250_000_000.0)

#: The frozen operational definition of capacity. All three must hold.
LIMIT_COST_DRAG_PCT_YR = 1.00
LIMIT_UNFILLED_FRAC = 0.01
LIMIT_CAGR_GAP_PT = 1.00


def norm(sim: dict, nav0: float) -> dict:
    """CANON 16: drag on AVERAGE NAV and bps of traded, never dollar totals."""
    nav, g = sim["nav"], sim["diag"]
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    avg = float(nav.mean())
    daily = sim["daily"]
    unfilled = float(daily["pending_abs"].mean() / avg) if len(daily) else None
    return {
        "start_nav": nav0,
        "final_nav": g["final_nav"],
        "execution_model": g["execution_model"],
        "cagr": g["cagr"],
        "cost_bps_of_traded": g["cost_bps_of_traded"],
        "impact_bps_of_traded": g["impact_bps_of_traded"],
        "explicit_bps_of_traded": g["explicit_bps_of_traded"],
        "cost_drag_pct_per_year": round(
            g["cost_dollars"] / (avg * yrs) * 100, 4),
        "impact_drag_pct_per_year": round(
            g["impact_dollars"] / (avg * yrs) * 100, 4),
        "turnover_rate_1way_annual": round(
            g["turnover_dollars"] / (avg * yrs), 4),
        "mean_unfilled_frac_of_nav": round(unfilled, 5)
        if unfilled is not None else None,
        "days_with_capped_orders": g["days_with_capped_orders"],
        "max_drawdown_daily": g["max_drawdown_daily"],
        "impact_warmup_orders": g["impact_warmup_orders"],
        "average_nav": round(avg, 0),
    }


def part_a() -> dict:
    """NIGHT-8's synthetic null, re-run with the term that was missing."""
    rows = {}
    for adv in ADV_RUNGS:
        data, targets, _ = build_world(SEED, adv_multiple=adv,
                                       half_spread_bps=25.0)
        for tag, coef in [("G7", 0.0)] + [(f"G8_{k}", v)
                                          for k, v in SCENARIOS.items()]:
            cfg = SimConfig(start_nav=1_000_000.0, impact_coef=coef,
                            slippage_bps=0.0, commission_bps=0.0)
            g = simulate(targets, data, cfg)["diag"]
            rows.setdefault(tag, {})[f"adv_x{adv:g}"] = {
                "cost_bps_of_traded": g["cost_bps_of_traded"],
                "impact_bps_of_traded": g["impact_bps_of_traded"],
                "cagr": g["cagr"]}
        print(f"  ADV x{adv:<10g} " + "  ".join(
            f"{t}={rows[t][f'adv_x{adv:g}']['cost_bps_of_traded']}bps"
            for t in rows), flush=True)
    g7_row = [v["cost_bps_of_traded"] for v in rows["G7"].values()]
    g8_row = [v["cost_bps_of_traded"] for v in rows["G8_base"].values()]
    return {
        "rows": rows,
        "g7_is_flat_across_a_million_fold_liquidity_range":
            max(g7_row) - min(g7_row) < 0.05,
        "g7_range_bps": round(max(g7_row) - min(g7_row), 3),
        "g8_base_range_bps": round(max(g8_row) - min(g8_row), 3),
        "reading": ("G7's cost per dollar traded is unchanged by liquidity; "
                    "G8's is not. That difference IS the instrument."),
    }


def part_b() -> dict:
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
    run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
             holdings_out=holdings)

    targets = []
    for h in holdings:
        if not h.get("rebalanced"):
            continue
        eff = pd.Timestamp(h["test"])
        if eff < pd.Timestamp(FIRST) or eff > pd.Timestamp(LAST):
            continue
        w = pd.Series(h["weights"]).astype(float)
        w.index = [int(x) for x in w.index]
        targets.append({"effective": eff.normalize(), "weights": w[w > 0]})
    permnos = {int(x) for t in targets for x in t["weights"].index}
    print(f"  targets {len(targets)}, permnos {len(permnos)}; loading daily...",
          flush=True)
    data = load_daily(FIRST, LAST, permnos=permnos)
    print(f"  daily {data.ret.shape[0]}d x {data.ret.shape[1]}n", flush=True)

    plan = [("G7", 0.0, NAV_RUNGS), ("G8_base", SCENARIOS["base"], NAV_RUNGS),
            ("G8_low", SCENARIOS["low"], BAND_RUNGS),
            ("G8_high", SCENARIOS["high"], BAND_RUNGS)]
    ladder: dict = {}
    for tag, coef, navs in plan:
        for nav0 in navs:
            cfg = SimConfig(start_nav=nav0, impact_coef=coef)
            r = norm(simulate(targets, data, cfg), nav0)
            ladder.setdefault(tag, {})[f"{int(nav0)}"] = r
            print(f"  {tag:9s} ${nav0:>13,.0f}  CAGR {r['cagr']:+.4f}  "
                  f"cost {r['cost_bps_of_traded']}bps "
                  f"(impact {r['impact_bps_of_traded']})  drag "
                  f"{r['cost_drag_pct_per_year']:.3f}%/yr", flush=True)
    return {"ladder": ladder, "targets": len(targets)}


def capacity(ladder: dict, tag: str) -> dict:
    """The frozen operational definition, applied. All three limits must hold."""
    rows = ladder.get(tag, {})
    if not rows:
        return {"tag": tag, "insufficient": True}
    base_cagr = rows[str(int(NAV_RUNGS[0]))]["cagr"]
    passing, detail = [], {}
    for k in sorted(rows, key=lambda x: int(x)):
        r = rows[k]
        checks = {
            "cost_drag_pct_per_year": (r["cost_drag_pct_per_year"],
                                       r["cost_drag_pct_per_year"]
                                       <= LIMIT_COST_DRAG_PCT_YR),
            "unfilled_frac": (r["mean_unfilled_frac_of_nav"],
                              (r["mean_unfilled_frac_of_nav"] or 0)
                              <= LIMIT_UNFILLED_FRAC),
            "cagr_gap_pt": (round((base_cagr - r["cagr"]) * 100, 3),
                            (base_cagr - r["cagr"]) * 100 <= LIMIT_CAGR_GAP_PT),
        }
        detail[k] = {"checks": {a: {"value": b[0], "pass": bool(b[1])}
                                for a, b in checks.items()},
                     "pass": all(b[1] for b in checks.values())}
        if detail[k]["pass"]:
            passing.append(int(k))
    return {
        "tag": tag,
        "limits": {"cost_drag_pct_per_year": LIMIT_COST_DRAG_PCT_YR,
                   "unfilled_frac_of_nav": LIMIT_UNFILLED_FRAC,
                   "cagr_gap_vs_1m_pt": LIMIT_CAGR_GAP_PT},
        "largest_passing_start_nav": max(passing) if passing else None,
        "rungs_tested": [int(k) for k in rows],
        "detail": detail,
        "caveat": ("this is the largest RUNG TESTED that passes, not a "
                   "continuous frontier; and it is a STARTING nav — the $1m "
                   "rung ends the window at roughly $18m"),
    }


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    print("PART A — the synthetic null, re-run", flush=True)
    a = part_a()
    print("\nPART B — the real ladder, re-simulated", flush=True)
    b = part_b()

    published = json.loads(G7_RECEIPT.read_text(encoding="utf-8"))["capacity_ladder"]
    regression = {}
    for k in ("1000000", "10000000", "100000000"):
        got = b["ladder"]["G7"].get(k, {}).get("cost_bps_of_traded")
        want = published.get(k, {}).get("cost_bps_of_traded")
        regression[k] = {"reproduced": got, "published": want,
                         "pass": got is not None and want is not None
                         and abs(got - want) <= 0.1}

    res = {
        "trial": "TRIAL-G8-IMPACT-AND-CAPACITY-1",
        "prereg": "TRIALS/PREREG_G8_IMPACT_AND_CAPACITY.md",
        "status": "REPORTED-NEVER-DECIDING",
        "data_grade": "crsp",
        "impact_model": describe(SCENARIOS["base"]),
        "part_a_synthetic": a,
        "part_b_ladder": b["ladder"],
        "g7_regression_vs_published_receipt": regression,
        "capacity": {t: capacity(b["ladder"], t)
                     for t in ("G7", "G8_base")},
        "how_to_quote_this": (
            "a capacity number from this receipt is only quotable WITH its "
            "coefficient and scenario band. 'The book holds $Xm' is not a "
            "sentence this trial licenses; 'under a base square-root impact "
            "coefficient of 0.50, the tested rungs up to $Xm meet the frozen "
            "cost/fill/CAGR limits' is."),
    }
    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "G8_IMPACT_AND_CAPACITY.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")
    print("\nG7 regression vs published:", json.dumps(regression))
    for t in ("G7", "G8_base"):
        print(f"capacity[{t}] largest passing start NAV: "
              f"{res['capacity'][t]['largest_passing_start_nav']}")
    print(f"written. {res['runtime_secs']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
