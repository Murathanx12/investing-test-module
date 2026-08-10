"""T3 — the rebalance-clock ensemble. A variance claim, never an alpha claim.

NIGHT-5 measured six rebalance clocks and found them correlated 0.958-0.993 with
no significant pairwise difference. The correct response to "we cannot tell which
date is best" is NOT to pick the best-looking one - that is date-mining a
difference we have just shown we cannot measure. It is to stop choosing: split
the capital into 12 annual cohorts, one starting in each calendar month.

What this measures, and the ONLY thing it may be quoted for:

  * the ensemble's mean return should land at the AVERAGE of the individual
    clocks, not above it - there is no bonus, and if one appears it is an
    artifact worth chasing;
  * the DISPERSION across start dates - the date luck a single-clock investor is
    exposed to and cannot diversify - is removed by construction;
  * turnover and cost are UNCHANGED: each cohort trades once a year, so 1/12 of
    the book trades each month. Staggering is free.

No alpha language appears in this file or its output.
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
from aegis_brain.pf.panel63 import annualize, max_drawdown
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT7"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
N_COHORTS = 12


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
    months = f.spine.panel.monthly_ret.index

    # Cohort k is the SAME book whose first rebalance is k months later. The
    # engine forces a rebalance on the first tradable month, so shifting the
    # window start by k shifts the whole annual clock by k.
    cohorts, diags, first_trade = {}, {}, {}
    for k in range(N_COHORTS):
        spec = StrategySpec(**{**d, "rebalance_months": 12, "cost_model": "ko",
                               "name": f"PF7-CLOCK__phase{k:02d}"})
        H: list[dict] = []
        out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era,
                       holdings_out=H, phase=k)
        cohorts[k] = out["monthly"]["net"].dropna()
        diags[k] = out["diag"]
        traded = [h["test"] for h in H if h.get("rebalanced")]
        first_trade[k] = str(pd.Timestamp(traded[0]).date()) if traded else None
        print(f"  cohort phase {k:2d} first trade {first_trade[k]} "
              f"months {len(cohorts[k])} rebalances {out['diag']['rebalances']} "
              f"turnover {out['diag']['turnover_1way_annual']:.3f}", flush=True)
    if len({v for v in first_trade.values()}) < N_COHORTS:
        raise RuntimeError(
            "cohorts did not stagger — first trade dates are not distinct: "
            f"{first_trade}. Refusing to report an 'ensemble' of identical books.")

    # common window so every cohort is scored on identical months
    idx = cohorts[0].index
    for k in range(1, N_COHORTS):
        idx = idx.intersection(cohorts[k].index)
    aligned = pd.DataFrame({k: cohorts[k].reindex(idx) for k in range(N_COHORTS)})
    bench = f.spine.mkt.reindex(idx)

    # the ensemble: 1/12 in each cohort, rebalanced across cohorts monthly
    ens = aligned.mean(axis=1)

    ind_excess = {k: round(annualize(aligned[k]) - annualize(bench), 4)
                  for k in range(N_COHORTS)}
    vals = np.array(list(ind_excess.values()), dtype=float)
    ens_excess = annualize(ens) - annualize(bench)

    ind_dd = {k: round(max_drawdown(aligned[k]), 4) for k in range(N_COHORTS)}
    ind_vol = {k: round(float(aligned[k].std(ddof=1) * np.sqrt(12)), 4)
               for k in range(N_COHORTS)}

    res = {
        "task": "T3 rebalance-clock ensemble",
        "trial": "TRIAL-PF7-CLOCK-ENSEMBLE-1",
        "status": "REPORTED-NEVER-DECIDING",
        "claim_type": ("DETERMINISTIC VARIANCE REDUCTION - this is not an alpha "
                       "claim and must never be quoted as one"),
        "book": "PF-PROF-COMPOSITE-150, annual clock, era costs, small segment",
        "window": [str(idx.min().date()), str(idx.max().date())],
        "months_common": int(len(idx)),
        "cohorts": N_COHORTS,
        "first_trade_date_by_phase": first_trade,
        "individual_clocks": {
            "excess_cagr_by_start_month": ind_excess,
            "mean": round(float(vals.mean()), 4),
            "std_across_start_dates": round(float(vals.std(ddof=1)), 4),
            "min": round(float(vals.min()), 4),
            "max": round(float(vals.max()), 4),
            "range_pct_yr": round(float(vals.max() - vals.min()), 4),
            "max_drawdown_by_start_month": ind_dd,
            "ann_vol_by_start_month": ind_vol,
        },
        "ensemble": {
            "excess_cagr": round(float(ens_excess), 4),
            "cagr": round(annualize(ens), 4),
            "max_drawdown": round(max_drawdown(ens), 4),
            "ann_vol": round(float(ens.std(ddof=1) * np.sqrt(12)), 4),
            "t_excess_nw": D.nw_t((ens - bench).dropna()),
        },
        "readings": {
            "ensemble_minus_mean_of_clocks": round(
                float(ens_excess - vals.mean()), 5),
            "no_free_lunch_check": (
                "the ensemble return should equal the mean of the cohorts to "
                "within rounding; a large positive gap would mean the "
                "construction is manufacturing return, which would be a BUG"),
            "date_luck_removed_pct_yr": round(float(vals.max() - vals.min()), 4),
            "dispersion_ratio": 0.0,
            "turnover_unchanged": {
                "mean_cohort_turnover": round(float(np.mean(
                    [diags[k]["turnover_1way_annual"] for k in range(N_COHORTS)])), 4),
                "note": ("each cohort trades once a year, so the ensemble trades "
                         "1/12 of the book every month at the SAME annual "
                         "turnover and the SAME cost. Staggering is free."),
            },
            "vol_and_drawdown": {
                "mean_cohort_ann_vol": round(float(np.mean(list(ind_vol.values()))), 4),
                "ensemble_ann_vol": round(float(ens.std(ddof=1) * np.sqrt(12)), 4),
                "mean_cohort_max_dd": round(float(np.mean(list(ind_dd.values()))), 4),
                "ensemble_max_dd": round(max_drawdown(ens), 4),
                "note": ("the cohorts hold overlapping books, so the ensemble "
                         "diversifies START DATE, not market risk - vol and "
                         "drawdown should barely move, and if they collapse "
                         "the cohorts were less correlated than they should be"),
            },
        },
        "runtime_secs": round(time.time() - t0, 1),
    }
    res["readings"]["dispersion_ratio"] = (
        "N/A - the ensemble is a single portfolio and has no cross-start-date "
        "dispersion BY CONSTRUCTION. The number that matters is the range above: "
        f"an investor picking one start date faced a "
        f"{res['individual_clocks']['range_pct_yr']:.2%}/yr spread of outcomes "
        "with no way to know in advance which date they had chosen.")

    aligned.assign(ensemble=ens, benchmark=bench).to_csv(
        OUT / "T3_clock_cohorts_monthly.csv")
    (OUT / "T3_CLOCK_ENSEMBLE.json").write_text(json.dumps(res, indent=2),
                                                encoding="utf-8")
    print(json.dumps({"individual": res["individual_clocks"]["excess_cagr_by_start_month"],
                      "mean_of_clocks": res["individual_clocks"]["mean"],
                      "std_across_dates": res["individual_clocks"]["std_across_start_dates"],
                      "range": res["individual_clocks"]["range_pct_yr"],
                      "ensemble_excess": res["ensemble"]["excess_cagr"],
                      "ensemble_minus_mean": res["readings"]["ensemble_minus_mean_of_clocks"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
