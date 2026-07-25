"""INSTR-OVERFIT-CEILING — measure what in-sample mining buys on OUR data.

Pre-registered in TRIALS/INSTR-OVERFIT-CEILING.md (committed BEFORE this runs).
Instrument, never arms. Library = CLOSED families only (insider family
EXCLUDED — live trial). Full-window scans 2004-01..2024-12 at 25 bps,
largemid; then pure post-hoc selection arms measure the self-deception
ceiling, and the explore->confirm decay curve is computed for the whole
library. Every drop is counted and printed.

Usage:  .venv\\Scripts\\python -m scripts.run_overfit_ceiling
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.batch1_price import BATCH1
from aegis_brain.factory.batch2_fundamentals import build_batch2
from aegis_brain.factory.batch5 import build_batch5
from aegis_brain.factory.batch6 import build_batch6
from aegis_brain.factory.batch7 import build_batch7
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.fundamentals import FundStore
from aegis_brain.factory.quarterly import QuarterlyStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ceiling")

OUT = MODULE_ROOT / "data" / "factory"
EXCLUDED = {"insider_cluster", "insider_si"}  # LIVE family — never contaminate
FULL = ScanConfig(first_test_month="2004-01-31", last_test_month="2024-12-31")
SPLIT_EXPLORE_END = pd.Timestamp("2018-12-31")   # protocol boundary
SPLIT_HALF = pd.Timestamp("2014-06-30")


def _t(x: pd.Series) -> float:
    x = x.dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if len(x) > 2 and sd > 0 else np.nan


def _stats(x: pd.Series) -> dict:
    x = x.dropna()
    return {"months": int(len(x)), "mean_bps": round(float(x.mean()) * 1e4, 1),
            "t": round(_t(x), 2),
            "sr_ann": round(float(x.mean() / x.std(ddof=1) * np.sqrt(12)), 2)
            if x.std(ddof=1) > 0 else np.nan}


def expected_max_sr(n: int, sr_std_monthly: float, months: int) -> dict:
    """Bailey-LdP expected max Sharpe of n zero-true-SR trials -> as a t."""
    g = 0.5772156649
    z = ((1 - g) * stats.norm.ppf(1 - 1 / n)
         + g * stats.norm.ppf(1 - 1 / (n * np.e)))
    e_sr_m = sr_std_monthly * z
    return {"n": n, "e_max_sr_ann": round(e_sr_m * np.sqrt(12), 2),
            "e_max_t": round(e_sr_m * np.sqrt(months), 2)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    store = FundStore(panel)
    qstore = QuarterlyStore(panel)

    sigs = (list(BATCH1) + build_batch2(store) + build_batch5(panel, store, qstore)
            + build_batch6(panel, store) + build_batch7(panel))
    sigs = [s for s in sigs if s.name not in EXCLUDED]
    log.info("library: %d signals (insider family excluded)", len(sigs))

    series: dict[str, pd.Series] = {}
    dropped: list[str] = []
    for s in sigs:
        try:
            r = scan_signal(panel, s, "largemid", FULL)
            series[s.name] = r["monthly"]["excess_net"]
        except Exception as exc:  # noqa: BLE001 — drops counted, never silent
            log.warning("DROPPED %s: %s", s.name, exc)
            dropped.append(s.name)
    log.info("scanned %d, dropped %d: %s", len(series), len(dropped), dropped)

    df = pd.DataFrame(series)
    full_t = df.apply(_t).sort_values(ascending=False)
    exp_t = df[df.index <= SPLIT_EXPLORE_END].apply(_t)
    conf_t = df[df.index > SPLIT_EXPLORE_END].apply(_t)

    # ---- mining arms (selection AND evaluation on the SAME full window) ----
    flip = pd.concat([df, -df.add_suffix("__flip")], axis=1)  # cost-identical proxy, disclosed
    flip_t = flip.apply(_t).sort_values(ascending=False)

    best1 = full_t.index[0]
    top5 = full_t.index[:5].tolist()
    fbest1 = flip_t.index[0]
    ftop5 = flip_t.index[:5].tolist()
    arms = {
        "A_best1": {"picked": best1, **_stats(df[best1])},
        "B_top5_ew": {"picked": top5, **_stats(df[top5].mean(axis=1))},
        "C_best1_signflip": {"picked": fbest1, **_stats(flip[fbest1])},
        "D_top5_ew_signflip": {"picked": ftop5, **_stats(flip[ftop5].mean(axis=1))},
    }
    # split-half fragility of the mined selections (selected on FULL sample)
    for k, cols, frame in (("A_best1", [best1], df), ("B_top5_ew", top5, df),
                           ("C_best1_signflip", [fbest1], flip),
                           ("D_top5_ew_signflip", ftop5, flip)):
        m = frame[cols].mean(axis=1)
        arms[k]["t_half1"] = round(_t(m[m.index <= SPLIT_HALF]), 2)
        arms[k]["t_half2"] = round(_t(m[m.index > SPLIT_HALF]), 2)

    # ---- the wall, empirically: explore-ranked -> confirm outcome ----
    order = exp_t.sort_values(ascending=False)
    decay = pd.DataFrame({"explore_t": order,
                          "confirm_t": conf_t.reindex(order.index)})
    decay["confirm_mean_bps"] = [
        round(float(df[c][df.index > SPLIT_EXPLORE_END].mean()) * 1e4, 1)
        for c in order.index]

    sr_m = df.apply(lambda x: x.dropna().mean() / x.dropna().std(ddof=1))
    h0 = {"lib_53": expected_max_sr(len(df.columns), float(sr_m.std(ddof=1)), 252),
          "with_flips": expected_max_sr(2 * len(df.columns),
                                        float(sr_m.std(ddof=1)), 252)}

    out = {
        "instrument": "INSTR-OVERFIT-CEILING", "run_at_note": "one run, final",
        "library_n": len(series), "dropped": dropped,
        "mining_arms": arms, "h0_expected_max": h0,
        "explore_confirm_decay_top15": decay.head(15).round(2).reset_index()
        .rename(columns={"index": "signal"}).to_dict("records"),
        "decay_corr_all": round(float(decay["explore_t"].corr(decay["confirm_t"])), 3),
        "full_window_t_all": {k: round(float(v), 2) for k, v in full_t.items()},
    }
    with open(OUT / "overfit_ceiling.json", "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    df.to_parquet(OUT / "overfit_ceiling_monthly.parquet")

    print(json.dumps({k: out[k] for k in
                      ("library_n", "dropped", "mining_arms", "h0_expected_max",
                       "decay_corr_all")}, indent=2, default=str))
    print("\nExplore->confirm decay (top 15 by explore t):")
    print(decay.head(15).round(2).to_string())
    print(f"\n-> {OUT / 'overfit_ceiling.json'}")


if __name__ == "__main__":
    main()
