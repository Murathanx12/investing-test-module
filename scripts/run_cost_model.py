"""INSTR-COST-MODEL — one shot. Protocol: TRIALS/INSTR-COST-MODEL.md.

Usage:  .venv\\Scripts\\python -m scripts.run_cost_model
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal, segment_mask
from aegis_brain.factory.signals import FactorySignal
from scripts.run_instr_anomaly_time import build_chars, wide_frame

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cost_model")
OUT = MODULE_ROOT / "data" / "factory"

EXPLORE = ScanConfig(cost_bps_one_way=50.0)
CONFIRM = ScanConfig(cost_bps_one_way=50.0, first_test_month="2019-01-31",
                     last_test_month="2024-12-31")


def spread_stats(panel, spreads) -> dict:
    out = {}
    for seg in ("largemid", "small"):
        mask = segment_mask(panel, seg) & panel.eligible()
        for era, lo, hi in [("2004-2010", "2004-01-31", "2010-12-31"),
                            ("2011-2018", "2011-01-31", "2018-12-31"),
                            ("2019-2024", "2019-01-31", "2024-12-31")]:
            sl = spreads.loc[lo:hi]
            msk = mask.loc[lo:hi]
            vals = sl.where(msk).stack().dropna()
            out[f"{seg}_{era}"] = {
                "median_bps": round(float(vals.median()), 1),
                "p90_bps": round(float(vals.quantile(0.9)), 1),
                "n": int(len(vals)),
            }
    return out


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    spreads = build_spread_frame(panel)
    stats = spread_stats(panel, spreads)
    lm = stats["largemid_2004-2010"]["median_bps"], \
        stats["largemid_2011-2018"]["median_bps"]
    gate = all(2 <= x <= 40 for x in lm) and \
        stats["small_2004-2010"]["median_bps"] > lm[0]
    log.info("sanity gate (largemid medians %s, small>largemid): %s", lm, gate)

    chars, _ = build_chars()
    sigs = {n: FactorySignal(n, "cost re-measure",
                             (lambda p, f=wide_frame(panel, chars, c): f), +1)
            for n, c in [("gp_base", "avail_month"), ("gp_ead", "avail_ead")]}

    guard = scan_signal(panel, sigs["gp_base"], "small", EXPLORE)["summary"]
    log.info("regression guard flat50: t_net %.2f net %.1f (banked 1.96/+23.2)",
             guard["t_excess_net"], guard["mean_excess_net_bps"])

    runs = []
    for name, sig in sigs.items():
        for win, cfg in [("explore", EXPLORE), ("confirm", CONFIRM)]:
            for arm, frame in [("ko_half", spreads), ("ko_full", spreads * 2)]:
                s = scan_signal(panel, sig, "small", cfg, cost_frame=frame)["summary"]
                s.update({"window": win, "cost_arm": arm})
                runs.append(s)

    results = {"sanity_gate_pass": bool(gate), "spread_stats": stats,
               "regression_guard": guard, "re_measures": runs}
    with open(OUT / "instr_cost_model.json", "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    for r in runs:
        print(f"{r['signal']:8s} {r['window']:8s} {r['cost_arm']:8s} "
              f"net {r['mean_excess_net_bps']:+7.1f} t {r['t_excess_net']:+5.2f}")
    print("gate:", gate, "| guard t_net:", guard["t_excess_net"])


if __name__ == "__main__":
    main()
