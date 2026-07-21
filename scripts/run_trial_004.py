"""TRIAL-BRAIN-004-pead-sue — one execution, results final.

Top vs bottom SUE quintile flag portfolios on CRSP 2006-2024, cap-segmented, entered the
month AFTER the earnings announcement (rdq month flag -> earns next-month return, skipping
the announcement jump), 3-month hold-band, ADV costs. Arm B top / Arm A bottom / Arm C noise.
Uses the shared audited flag-portfolio harness. Usage: .venv\\Scripts\\python -m scripts.run_trial_004
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.harness.flag_portfolio import hold_band, quintile_flag, run_arms

START, END, HOLD = "2006-01-01", "2024-12-31", 3


def main() -> None:
    t0 = time.time()
    OUT = MODULE_ROOT / "runs" / "TRIAL-BRAIN-004"; OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    sue = pd.read_parquet(MODULE_ROOT / "data" / "sue_events.parquet")
    sue = sue[sue["permno"].notna() & sue["sue_ts"].notna()].copy()
    sue["m"] = sue["rdq"].dt.to_period("M").dt.to_timestamp("M")
    sue["p"] = sue["permno"].astype("Int64").astype(str)

    months, cols = panel.monthly_ret.index, panel.monthly_ret.columns
    # SUE[month, permno] = last announcement's sue_ts that month (winsorize extreme tails)
    sue["sue_w"] = sue["sue_ts"].clip(-10, 10)
    S = sue.pivot_table(index="m", columns="p", values="sue_w", aggfunc="last")
    S = S.reindex(index=months, columns=cols)
    announcer = S.notna()

    F_B = quintile_flag(S, announcer, top=True)
    F_A = quintile_flag(S, announcer, top=False)
    rng = np.random.default_rng(20260721)
    F_N = pd.DataFrame(False, index=months, columns=cols)
    for m in months:
        pool = cols[announcer.loc[m].values]
        k = int(F_B.loc[m].sum())
        if k and len(pool):
            F_N.loc[m, rng.choice(pool, size=min(k, len(pool)), replace=False)] = True

    arms = {"B": hold_band(F_B, HOLD), "A": hold_band(F_A, HOLD), "noise": hold_band(F_N, HOLD)}
    res = run_arms(panel, arms, START, END, MODULE_ROOT / "data", factor_alpha_arms=("B", "A"))

    best = res["best_B_segment"]
    spread = (res["nets"][f"B_{best}"] - res["nets"][f"A_{best}"]).dropna()
    res["B_minus_A_spread_t"] = newey_west_tstat(spread)["t"]
    res["B_minus_A_spread_bps"] = round(float(spread.mean()) * 1e4, 1)
    res.pop("nets", None)
    out = {"trial": "TRIAL-BRAIN-004-pead-sue", "window": f"{START}..{END}",
           "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           **res, "elapsed_s": round(time.time() - t0, 1)}
    (OUT / "results.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
