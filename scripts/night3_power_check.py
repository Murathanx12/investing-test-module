"""How much room is there to win? The oracle bracket on the decision environment.

A null result for M1 has two very different meanings and they must not be
conflated:

  * "the LLM cannot out-pick the engine" — informative, and the registered
    question;
  * "nothing could out-pick the engine here, because the slate's 40 names are
    too alike for any selector to separate" — a statement about the TEST, not
    about the LLM.

This script measures which one is true, using no LLM at all. It computes, per
month, the best possible 20 of 40 and the worst possible 20 of 40 with perfect
hindsight. Those two numbers bracket everything any decider could ever achieve
on this environment. The engine's position inside that bracket is the headroom.

Hindsight arms can never be candidates and are never registered as such. They
exist to tell us whether the instrument can resolve anything.

    python scripts/night3_power_check.py
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.night3.slate import (PROF_SIGNALS, book_return,
                                      build_slates, build_slates_stratified)
from aegis_brain.pf.panel63 import annualize, eligibility, load_spine
from aegis_brain.pf.signals import SignalLibrary, composite_score

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("power")

RUN_DIR = MODULE_ROOT / "runs" / "NIGHT3"
COST_BPS = 25.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", default="2005-01-31")
    ap.add_argument("--last", default="2021-12-31")
    ap.add_argument("--slate", type=int, default=40)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--stratified", action="store_true")
    args = ap.parse_args()

    spine = load_spine("2003-01-31", "2022-12-31")
    lib = SignalLibrary(spine.panel)
    lib.preload(["native:mom_12_1", "native:vol_12m_low", "osap:GP", "osap:BM",
                 "osap:OperProfRD", "osap:CBOperProf"])
    elig = eligibility(spine, "small")
    score, _ = composite_score(lib, PROF_SIGNALS, elig)
    builder = build_slates_stratified if args.stratified else build_slates
    slates = builder(spine, lib, score, elig, first=args.first,
                     last=args.last, slate_n=args.slate)

    idx = [pd.Timestamp(s.realized_month) for s in slates]
    bench = pd.Series([s.benchmark_fwd for s in slates], index=idx)

    rng = np.random.default_rng(20260809)
    series: dict[str, list] = {k: [] for k in
                               ("ORACLE", "ANTI_ORACLE", "ENGINE_TOP",
                                "ENGINE_BOTTOM", "EW40", "RANDOM_MEAN")}
    spread_gross = []
    for s in slates:
        cs = sorted(s.candidates, key=lambda c: c.engine_rank)
        labs_top = [c.label for c in cs[:args.top]]
        labs_bot = [c.label for c in cs[-args.top:]]
        by_ret = sorted(s.candidates, key=lambda c: -c.fwd_ret)
        labs_best = [c.label for c in by_ret[:args.top]]
        labs_worst = [c.label for c in by_ret[-args.top:]]
        # costs are irrelevant to the bracket's WIDTH, so charge none here and
        # say so — mixing turnover into a hindsight bound would muddy it
        series["ORACLE"].append(book_return(s, labs_best, 0.0)[0])
        series["ANTI_ORACLE"].append(book_return(s, labs_worst, 0.0)[0])
        series["ENGINE_TOP"].append(book_return(s, labs_top, 0.0)[0])
        series["ENGINE_BOTTOM"].append(book_return(s, labs_bot, 0.0)[0])
        series["EW40"].append(book_return(s, [c.label for c in s.candidates], 0.0)[0])
        draws = [book_return(s, list(rng.choice([c.label for c in s.candidates],
                                                size=args.top, replace=False)),
                             0.0)[0] for _ in range(20)]
        series["RANDOM_MEAN"].append(float(np.mean(draws)))
        spread_gross.append(series["ENGINE_TOP"][-1] - series["ENGINE_BOTTOM"][-1])

    out = {"environment": "stratified" if args.stratified else "engine_top40",
           "n_months": len(slates), "cost_bps_charged": 0.0,
           "note": ("Gross of costs by design: this measures the WIDTH of the "
                    "achievable band, not a tradable return."),
           "benchmark_cagr": round(annualize(bench), 4), "arms": {}}
    for k, v in series.items():
        ser = pd.Series(v, index=idx)
        out["arms"][k] = {
            "cagr": round(annualize(ser), 4),
            "excess_cagr": round(annualize(ser) - annualize(bench), 4),
            "mean_monthly": round(float(ser.mean()), 5)}

    orc = out["arms"]["ORACLE"]["excess_cagr"]
    ant = out["arms"]["ANTI_ORACLE"]["excess_cagr"]
    eng = out["arms"]["ENGINE_TOP"]["excess_cagr"]
    rnd = out["arms"]["RANDOM_MEAN"]["excess_cagr"]
    out["headroom"] = {
        "achievable_band_excess_cagr": [ant, orc],
        "band_width_pct_per_year": round(orc - ant, 4),
        "engine_position_in_band": round((eng - ant) / (orc - ant), 3)
        if orc > ant else None,
        "engine_minus_random_selection": round(eng - rnd, 4),
        "engine_top_minus_engine_bottom": round(
            eng - out["arms"]["ENGINE_BOTTOM"]["excess_cagr"], 4),
        "mean_monthly_top_minus_bottom": round(float(np.mean(spread_gross)), 5),
        "t_top_minus_bottom": round(float(
            np.mean(spread_gross) / (np.std(spread_gross) / np.sqrt(len(spread_gross)))), 2),
    }
    h = out["headroom"]
    out["interpretation"] = (
        f"Any decider on this environment is confined to a band "
        f"{h['achievable_band_excess_cagr'][0]:+.1%} .. "
        f"{h['achievable_band_excess_cagr'][1]:+.1%} of excess CAGR. The engine's "
        f"own ranking is worth {h['engine_top_minus_engine_bottom']:+.2%}/yr "
        f"(top-20 minus bottom-20 of the same slate, t="
        f"{h['t_top_minus_bottom']}). If that ordering value is near zero, a null "
        f"M1 means the TEST cannot separate deciders, not that the LLM adds "
        f"nothing — and the verdict must be UNRESOLVED, not REJECT.")

    (RUN_DIR / ("POWER_CHECK_STRATIFIED.json" if args.stratified else "POWER_CHECK.json")).write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
