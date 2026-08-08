"""INSTR-COST-LM-1 — the largemid cost wedge, measured.

Registered in TRIALS/registry.jsonl (commit 6200d7d) before compute.
DIAGNOSTIC: reads only already-examined largemid batch-1 rows; recomputes
their books under the certified KO half-spread frame; no adoption/kill.

Run:  python scripts/run_instr_cost_lm_1.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.batch1_price import BATCH1
from aegis_brain.factory.explore import ScanConfig, scan_signal, segment_mask

# already-examined largemid batch-1 signals across the turnover spectrum
PROBE = ["price_level", "vol_12m_low", "mom_12_1", "st_reversal",
         "sharpe_12m", "high_52wk_prox"]
OUT = MODULE_ROOT / "runs" / "ERA" / "instr_cost_lm_1.json"


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} exists — one shot.")
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    ko = build_spread_frame(panel)
    cfg = ScanConfig()

    # measured largemid spread distribution over the explore window,
    # formation-month membership
    months = panel.monthly_ret.index
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    lm = panel.eligible() & segment_mask(panel, "largemid")
    vals = []
    for m in months[(months >= lo) & (months <= hi)]:
        e = lm.loc[m]
        s = ko.loc[m].reindex(e[e].index).dropna()
        if len(s):
            vals.append(s)
    allv = pd.concat(vals)
    dist = {"n_obs": int(len(allv)),
            "mean_bps": round(float(allv.mean()), 2),
            "median_bps": round(float(allv.median()), 2),
            "p25_bps": round(float(allv.quantile(0.25)), 2),
            "p75_bps": round(float(allv.quantile(0.75)), 2),
            "p95_bps": round(float(allv.quantile(0.95)), 2),
            "flat_arm_bps": 25.0}
    print("largemid KO half-spread (2004-2018):", json.dumps(dist))

    sigs = {s.name: s for s in BATCH1}
    rows = []
    for name in PROBE:
        flat = scan_signal(panel, sigs[name], "largemid", cfg)["summary"]
        koh = scan_signal(panel, sigs[name], "largemid", cfg,
                          cost_frame=ko)["summary"]
        rows.append({"signal": name,
                     "t_net_flat25": flat["t_excess_net"],
                     "t_net_ko": koh["t_excess_net"],
                     "t_gross": flat["t_excess_gross"],
                     "lift": round(koh["t_excess_net"]
                                   - flat["t_excess_net"], 2),
                     "turnover": flat["turnover_1way"]})
        print(json.dumps(rows[-1]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "instrument": "INSTR-COST-LM-1", "spread_distribution": dist,
        "probes": rows,
        "note": ("diagnostic only; a replay-class re-adjudication of "
                 "largemid kills under KO costs would be a NEW registered "
                 "trial with its own error control")}, indent=2),
        encoding="utf-8")
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
