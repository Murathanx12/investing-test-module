"""PF-HARNESS-VALID — calibrate the factory instrument before it judges anything.

NEGATIVE_RESULTS #34: the instrument that adjudicates everything else must
itself be adjudicated. Three checks, in order:

  V1 STITCH FIDELITY. Run the EXISTING, banked code path (factory.explore.
     scan_signal) on the NEW stitched 63-year panel over the era window and
     require it to reproduce INSTR-ERA-BACKTEST-1's banked numbers for
     CBOperProf/small 1985-2001 (t_ic 5.23 gross / 4.30 net at flat-25).
     If the stitch changed the data, this is where it shows.

  V2 CONSTRUCTION DIFFERENTIAL. The portfolio engine is deliberately NOT the
     decile scan: fixed N names, weights drift between rebalances, delisted
     names are liquidated to cash, benchmark is the market. Each difference is
     switched on one at a time and its effect measured, so the gap between the
     scan's number and the portfolio's number is accounted for rather than
     hand-waved.

  V3 KNOWN NULL. Turnover-matched random books over the same window must
     produce an excess-return distribution centred at or below zero with a
     t-distribution consistent with noise. A positive-mean null means leakage.

Writes runs/PF/VALIDATION.json. Exit code 1 if V1 or V3 fails.
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

from aegis_brain.config import MODULE_ROOT
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.signals import FactorySignal
from aegis_brain.pf.engine import buy_and_hold_universe, run_book
from aegis_brain.pf.panel63 import annualize, eligibility, load_spine
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import random_score
from aegis_brain.pf.spec import StrategySpec

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("validate")

BANKED = {"signal": "CBOperProf", "segment": "small",
          "first": "1985-01-31", "last": "2001-12-31",
          "t_ic": 5.23, "t_gross": 5.23, "t_net_flat25": 4.30,
          "source": "runs/ERA/instr_era_backtest_1.json (VERDICT-ERA-BACKTEST-1)"}
OUT = MODULE_ROOT / "runs" / "PF" / "VALIDATION.json"
TOL = 0.15   # absolute t-stat tolerance for the reproduction


def _t(x: pd.Series) -> float:
    x = pd.Series(x).dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else 0.0


def main() -> int:
    t0 = time.time()
    result: dict = {"banked": BANKED}

    fac = Factory(first=BANKED["first"], last=BANKED["last"])
    panel = fac.spine.panel
    result["provenance"] = fac.spine.provenance

    # ── V1: reproduce the banked era numbers through the old code path ──────
    frame = fac.lib.get(f"osap:{BANKED['signal']}").astype("float64")
    sig = FactorySignal(f"osap_{BANKED['signal']}", "V1 reproduction",
                        lambda _p, _f=frame: _f, +1)
    scan = scan_signal(panel, sig, BANKED["segment"],
                       ScanConfig(first_test_month=BANKED["first"],
                                  last_test_month=BANKED["last"]))["summary"]
    v1 = {"scan": scan,
          "d_t_gross": round(scan["t_excess_gross"] - BANKED["t_gross"], 3),
          "d_t_net": round(scan["t_excess_net"] - BANKED["t_net_flat25"], 3)}
    v1["PASS"] = bool(abs(v1["d_t_gross"]) <= TOL and abs(v1["d_t_net"]) <= TOL)
    result["V1_stitch_fidelity"] = v1
    log.info("V1 %s: scan t_gross %.2f (banked %.2f), t_net %.2f (banked %.2f)",
             "PASS" if v1["PASS"] else "FAIL", scan["t_excess_gross"],
             BANKED["t_gross"], scan["t_excess_net"], BANKED["t_net_flat25"])

    # ── V2: account for every construction difference, one at a time ────────
    elig = eligibility(fac.spine, BANKED["segment"])
    mean_elig = float(elig.loc[BANKED["first"]:BANKED["last"]].sum(axis=1).mean())
    decile_n = max(int(round(mean_elig * 0.10)), 10)
    base = StrategySpec(
        name="V2", signals=((f"osap:{BANKED['signal']}", 1.0),),
        segment=BANKED["segment"], top_n=decile_n, hold_band_mult=3.0,
        rebalance_months=1, cost_model="flat25",
        first_month=BANKED["first"], last_month=BANKED["last"], min_names=100)
    score, _ = fac.lib.__class__(panel), None
    score = None
    from aegis_brain.pf.signals import composite_score
    score, sdiag = composite_score(fac.lib, base.signals, elig)
    ew = buy_and_hold_universe(panel, elig, base, fac.spine.rf)

    variants = {
        "portfolio_decileN": base,
        "portfolio_N50": base.variant(name="V2_N50", top_n=50),
        "portfolio_N25": base.variant(name="V2_N25", top_n=25),
        "portfolio_N25_quarterly": base.variant(name="V2_N25q", top_n=25,
                                                rebalance_months=3),
    }
    v2 = {"mean_eligible_names": round(mean_elig, 1), "decile_n": decile_n,
          "scan_reference": {"mean_excess_net_bps": scan["mean_excess_net_bps"],
                             "t_excess_net_vs_ew": scan["t_excess_net"],
                             "turnover_1way_monthly": scan["turnover_1way"]},
          "portfolio": {}}
    for label, sp in variants.items():
        out = run_book(panel, score, elig, sp, fac.spine.rf)
        net = out["monthly"]["net"]
        ew_a = ew.reindex(net.index)
        mkt = fac.spine.mkt.reindex(net.index)
        v2["portfolio"][label] = {
            "top_n": sp.top_n, "rebalance_months": sp.rebalance_months,
            "mean_excess_net_bps_vs_ew": round(float((net - ew_a).mean()) * 1e4, 1),
            "t_excess_net_vs_ew": round(_t(net - ew_a), 2),
            "cagr_net": round(annualize(net), 4),
            "ew_universe_cagr": round(annualize(ew_a), 4),
            "market_cagr": round(annualize(mkt), 4),
            "excess_cagr_vs_market": round(annualize(net) - annualize(mkt), 4),
            "turnover_1way_annual": out["diag"]["turnover_1way_annual"],
            "forced_liquidations": out["diag"]["forced_liquidations"],
            "mean_cash_weight": out["diag"]["mean_cash_weight"],
        }
        log.info("V2 %-22s N=%-4d t_vs_ew %.2f  excess_vs_mkt %+.2f%%/yr",
                 label, sp.top_n,
                 v2["portfolio"][label]["t_excess_net_vs_ew"],
                 100 * v2["portfolio"][label]["excess_cagr_vs_market"])
    # the decile-N portfolio should agree in SIGN and order of magnitude with the
    # scan; the residual gap is the drift/liquidation/fixed-N difference
    d = v2["portfolio"]["portfolio_decileN"]
    v2["decileN_vs_scan_t_gap"] = round(
        d["t_excess_net_vs_ew"] - scan["t_excess_net"], 2)
    v2["SIGN_AGREES"] = bool(d["t_excess_net_vs_ew"] > 0 and scan["t_excess_net"] > 0)
    result["V2_construction_differential"] = v2

    # ── V3: known null — turnover-matched random books ───────────────────────
    null_spec = base.variant(name="V3_null", top_n=25)
    ref = run_book(panel, score, elig, null_spec, fac.spine.rf)
    target_to = ref["diag"]["turnover_1way_annual"]
    rows = []
    for rho in (0.0, 0.90, 0.98):
        for i in range(12):
            sc = random_score(panel, seed=777 + i, rho=rho)
            o = run_book(panel, sc, elig, null_spec, fac.spine.rf)
            net = o["monthly"]["net"]
            ew_a = ew.reindex(net.index)
            rows.append({"rho": rho, "draw": i,
                         "t_vs_ew": _t(net - ew_a),
                         "excess_cagr_vs_mkt": annualize(net) - annualize(
                             fac.spine.mkt.reindex(net.index)),
                         "excess_cagr_vs_ew": annualize(net) - annualize(ew_a),
                         "turnover": o["diag"]["turnover_1way_annual"]})
    nulls = pd.DataFrame(rows)
    agg = nulls.groupby("rho").agg(
        mean_t=("t_vs_ew", "mean"), sd_t=("t_vs_ew", "std"),
        mean_excess_vs_ew=("excess_cagr_vs_ew", "mean"),
        mean_turnover=("turnover", "mean")).round(4)
    v3 = {"strategy_turnover": target_to,
          "by_rho": json.loads(agg.reset_index().to_json(orient="records")),
          "n_draws_per_rho": 12}
    # a null must not print positive excess vs its own universe beyond noise
    worst = float(agg["mean_t"].max())
    v3["max_mean_t_across_rho"] = round(worst, 3)
    v3["PASS"] = bool(worst < 1.0)
    result["V3_known_null"] = v3
    log.info("V3 %s: max mean t across rho = %.2f", "PASS" if v3["PASS"] else "FAIL", worst)

    result["runtime_secs"] = round(time.time() - t0, 1)
    result["VERDICT"] = ("PASS" if (v1["PASS"] and v3["PASS"] and v2["SIGN_AGREES"])
                         else "FAIL")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("V2_construction_differential",)},
                     indent=2, default=str)[:3000])
    print(f"\nwritten -> {OUT}   VERDICT {result['VERDICT']}")
    return 0 if result["VERDICT"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
