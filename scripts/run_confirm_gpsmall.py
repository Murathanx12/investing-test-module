"""TRIAL-BRAIN-008-grossprof-small — the ONE confirm run (frozen spec).

Pre-registration: docs/STRATEGY_FACTORY.md (committed before this runs).
Confirm window 2019-01..2024-12, small segment, 50 bps, top decile, 30%
hold-band. Re-running with tweaked parameters is the overfitting machine —
this script exists so the run is reproducible, not repeatable-until-liked.

Usage:  .venv\\Scripts\\python -m scripts.run_confirm_gpsmall
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
from aegis_brain.factory.batch2_fundamentals import build_batch2
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.fundamentals import FundStore
from aegis_brain.harness.benchmark import factor_alpha, load_ff_factors, newey_west_tstat

N_TRIALS = 61  # cumulative explore candidates (batch1 40 + batch2 20 + HC 1)

CFG = ScanConfig(cost_bps_one_way=50.0,
                 first_test_month="2019-01-31", last_test_month="2024-12-31")


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    store = FundStore(panel)
    gp = [s for s in build_batch2(store) if s.name == "gross_prof"][0]

    res = scan_signal(panel, gp, "small", CFG)
    monthly, summary = res["monthly"], res["summary"]

    nw = newey_west_tstat(monthly["excess_net"])
    ic_nw = newey_west_tstat(monthly["ic"])

    # sr_variance from the cross-section of batch 1+2 explore Sharpes
    srs = []
    for f in ("batch1_summary.csv", "batch2_summary.csv"):
        t = pd.read_csv(MODULE_ROOT / "data" / "factory" / f)
        t = t[t["months"] > 0]
        srs.extend((t["t_excess_net"] / np.sqrt(t["months"])).tolist())  # monthly-scale SR
    sr_var = float(np.var(srs, ddof=1))

    dsr = deflated_sharpe_from_returns(
        monthly["excess_net"].dropna().values, n_trials=N_TRIALS, sr_variance=sr_var)

    ff = load_ff_factors(MODULE_ROOT / "data")
    excess = (monthly["net"] - ff["rf"].reindex(monthly.index)).dropna()
    alpha = factor_alpha(excess, ff, ["mktrf", "smb", "hml", "rmw", "cma", "umd"])

    out = {
        "trial": "TRIAL-BRAIN-008-grossprof-small",
        "summary": summary,
        "nw_t_excess_net": nw, "nw_t_ic": ic_nw,
        "dsr": dsr, "sr_variance_batch": round(sr_var, 6),
        "ff6_alpha": alpha,
    }
    path = MODULE_ROOT / "data" / "factory" / "confirm_gpsmall.json"
    path.write_text(json.dumps(out, indent=2, default=str))
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
