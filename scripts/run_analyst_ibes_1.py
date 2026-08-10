"""ANALYST-IBES-1 — target LEVELS vs target REVISIONS on point-in-time IBES.

Registered in TRIALS/PREREG_ANALYST_IBES_1.md. Read that before reading a
number out of this script: two of the four arms are REPLICATION arms whose job
is to reproduce a known kill, they accrue nothing to the search denominator,
and if they come out positive the whole trial is void.

    python -m scripts.run_analyst_ibes_1 [--placebo 100] [--quick]

Writes runs/ARENA1/ANALYST_IBES_1/*.json plus a verdict summary.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.run import Factory
from aegis_brain.pf.spec import StrategySpec

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "ARENA1" / "ANALYST_IBES_1"

FIRST = "2002-01-31"
LAST = "2022-12-31"          # holdout stays locked; Factory refuses past it

# (arm, signal key, accrues to the denominator?, what it must show)
ARMS: list[tuple[str, str, bool, str]] = [
    ("A1_tgt_upside", "ibes:tgt_upside", False,
     "REPLICATION: must be NEGATIVE (analyst_target_upside_xs, TRIAL-TGT-REBUILD)"),
    ("R1_eps_rev_breadth", "ibes:eps_rev_breadth", False,
     "REPLICATION: must have net t < 1 (TRIAL-BRAIN-005-revisions)"),
    ("A2_tgt_rev_breadth", "ibes:tgt_rev_breadth", True,
     "ACCRUING: registered positive gross, net-dead"),
    ("A3_tgt_rev_3m", "ibes:tgt_rev_3m", True,
     "ACCRUING: registered positive gross, net-dead"),
]

SEGMENTS = ("small", "largemid")
CLOCKS = (1, 3)
COSTS = ("flat25", "ko")


def headline(card: dict) -> dict:
    h, imp, risk = card["headline"], card["implementation"], card["risk"]
    gross = imp.get("gross_cagr")
    bench = h.get("benchmark_cagr")
    return {
        "excess_cagr_net": round(100 * h["excess_cagr_net"], 3),
        # The registered predictions are about GROSS and NET separately, so
        # both are carried: "positive gross, net-dead" is unfalsifiable if only
        # the net number is kept.
        "excess_cagr_gross": (None if gross is None or bench is None
                              else round(100 * (gross - bench), 3)),
        "t_excess_monthly": round(h.get("t_excess_monthly", float("nan")), 3),
        "t_excess_nw": round(h.get("t_excess_newey_west", float("nan")), 3),
        "cagr_net": round(100 * h.get("cagr_net", float("nan")), 3),
        "gross_cagr": None if gross is None else round(100 * gross, 3),
        "benchmark_cagr": None if bench is None else round(100 * bench, 3),
        "max_drawdown": round(100 * risk.get("max_drawdown", float("nan")), 2),
        "ann_vol": round(100 * risk.get("ann_vol", float("nan")), 2),
        "turnover_1way_annual": imp.get("turnover_1way_annual"),
        "cost_drag_annual_bps": imp.get("cost_drag_annual_bps"),
        "mean_scored_names": (imp.get("signal_coverage") or {}).get(
            "mean_scored_names_per_month"),
        "n_months": card["window"].get("months"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--placebo", type=int, default=0)
    ap.add_argument("--quick", action="store_true",
                    help="one segment, one clock, one cost model — smoke test")
    ap.add_argument("--top-n", type=int, default=50)
    a = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)

    segments = ("small",) if a.quick else SEGMENTS
    clocks = (1,) if a.quick else CLOCKS
    costs = ("flat25",) if a.quick else COSTS

    t0 = time.time()
    fac = Factory(FIRST, LAST, out_dir=OUT)
    results: list[dict] = []

    for arm, key, accrues, note in ARMS:
        for seg in segments:
            for clock in clocks:
                for cost in costs:
                    name = f"AIBES1_{arm}_{seg}_m{clock}_{cost}"
                    spec = StrategySpec(
                        name=name,
                        signals=((key, 1.0),),
                        segment=seg,
                        top_n=a.top_n,
                        weighting="ew",
                        rebalance_months=clock,
                        cost_model=cost,
                        first_month=FIRST,
                        last_month=LAST,
                        family="ANALYST-IBES-1",
                        hypothesis=note,
                        tags=("analyst", "ibes",
                              "accruing" if accrues else "replication"),
                    )
                    try:
                        card = fac.run(spec, placebo_draws=a.placebo, write=True)
                    except Exception as exc:  # noqa: BLE001 - a dead arm is data
                        logger.error("%s FAILED: %s: %s", name,
                                     type(exc).__name__, exc)
                        results.append({"arm": arm, "signal": key, "segment": seg,
                                        "clock": clock, "cost": cost,
                                        "accrues": accrues, "status": "FAILED",
                                        "error": f"{type(exc).__name__}: {exc}"})
                        continue
                    row = {"arm": arm, "signal": key, "segment": seg,
                           "clock": clock, "cost": cost, "accrues": accrues,
                           "status": "OK", "spec_hash": card["spec_hash"],
                           **headline(card)}
                    if "placebo_verdict" in card:
                        row["placebo_verdict"] = card["placebo_verdict"]
                    results.append(row)

    payload = {
        "trial": "ANALYST-IBES-1",
        "prereg": "TRIALS/PREREG_ANALYST_IBES_1.md",
        "window": [FIRST, LAST],
        "top_n": a.top_n,
        "denominator_accruing": sum(1 for r in results if r.get("accrues")),
        "denominator_note": (
            "Replication arms accrue ZERO: their registered outcome is a kill "
            "that already exists, so they can confirm or impeach the "
            "instrument but cannot be a search for a winner."),
        "runtime_secs": round(time.time() - t0, 1),
        "results": results,
    }
    (OUT / "results.json").write_text(json.dumps(payload, indent=2),
                                      encoding="utf-8")

    ok = [r for r in results if r["status"] == "OK"]
    print(f"\n{'arm':22s} {'seg':9s} {'clk':4s} {'cost':7s} "
          f"{'excess%':>8s} {'t':>7s} {'turn':>6s} {'bps':>7s}")
    for r in sorted(ok, key=lambda x: (x["arm"], x["segment"], x["clock"])):
        print(f"{r['arm']:22s} {r['segment']:9s} {r['clock']:<4d} {r['cost']:7s} "
              f"{r['excess_cagr_net']:>8.2f} {r['t_excess_monthly']:>7.2f} "
              f"{str(r['turnover_1way_annual']):>6s} "
              f"{str(r['cost_drag_annual_bps']):>7s}")
    print(f"\nwrote {OUT / 'results.json'}  ({payload['runtime_secs']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
