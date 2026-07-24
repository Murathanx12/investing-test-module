"""TRIAL-BRAIN-010-conclow-confirm — the ONE confirm run (frozen spec).

Pre-registration: TRIALS/TRIAL-BRAIN-010-conclow-confirm.md (committed +
pushed BEFORE this runs; book inspection passed return-blind). Confirm
window 2019-01..2024-12, LARGEMID segment, 50 bps stress costs, top decile,
30% hold-band, signal = batch-7 conc_low byte-identical. Reruns forbidden.
Usage:  .venv\Scripts\python -m scripts.run_confirm_conclow
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.discipline.overfitting import deflated_sharpe_from_returns
from aegis_brain.factory.batch7 import build_batch7
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.harness.benchmark import factor_alpha, load_ff_factors, newey_west_tstat

N_TRIALS = 140  # cumulative explore candidates through batch 7

CFG = ScanConfig(cost_bps_one_way=50.0,
                 first_test_month="2019-01-31", last_test_month="2024-12-31")


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    sig = [s for s in build_batch7(panel) if s.name == "conc_low"][0]
    res = scan_signal(panel, sig, "largemid", CFG)
    monthly, summary = res["monthly"], res["summary"]

    nw = newey_west_tstat(monthly["excess_net"])
    ic_nw = newey_west_tstat(monthly["ic"])

    srs = []
    for f in sorted((MODULE_ROOT / "data" / "factory").glob("batch*_summary.csv")):
        t = pd.read_csv(f)
        t = t[t["months"] > 0]
        srs.extend((t["t_excess_net"] / np.sqrt(t["months"])).tolist())
    sr_var = float(np.var(srs, ddof=1))

    dsr = deflated_sharpe_from_returns(
        monthly["excess_net"].dropna().values, n_trials=N_TRIALS, sr_variance=sr_var)

    ff = load_ff_factors(MODULE_ROOT / "data")
    excess = (monthly["net"] - ff["rf"].reindex(monthly.index)).dropna()
    alpha = factor_alpha(excess, ff, ["mktrf", "smb", "hml", "rmw", "cma", "umd"])

    out = {"trial": "TRIAL-BRAIN-010-conclow-confirm", "summary": summary,
           "nw_t_excess_net": nw, "nw_t_ic": ic_nw,
           "dsr": dsr, "sr_variance_batch": round(sr_var, 6),
           "n_trials": N_TRIALS, "ff6_alpha": alpha}
    (MODULE_ROOT / "data" / "factory" / "confirm_conclow.json").write_text(
        json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))

    t_net, t_ic = summary["t_excess_net"], summary["t_ic"]
    pos = summary["mean_excess_net_bps"] > 0 and summary["ic_mean"] > 0
    if not pos:
        verdict = "KILL"
    elif t_net >= 0.8 and t_ic >= 1.5:
        verdict = "STRONG PASS" if t_net >= 1.5 else "PASS"
    else:
        verdict = "FAIL (thresholds not met)"
    print(f"\nVERDICT (frozen rule): {verdict}")


if __name__ == "__main__":
    main()
