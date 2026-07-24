"""TRIAL-BRAIN-009-insider-cluster — one execution, results final.

Flag-portfolio test (the correct instrument after batch 5's VOID-DESIGN):
B2 = names with >=2 DISTINCT opportunistic insider buyers in the trailing 3
months; B3 = >=3 distinct buyers in the current month; coverage benchmark =
names with >=1 opportunistic buyer in the trailing 3 months (so the test is
clusters-vs-single-buys, not buyers-vs-market); noise = random coverage names
at B2's monthly counts. 6-month hold band, min_names=5 (sparse, disclosed).
Usage: .venv\\Scripts\\python -m scripts.run_trial_009
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
from aegis_brain.harness.flag_portfolio import hold_band, run_arms

START, END, HOLD, MIN_NAMES = "2006-01-01", "2024-12-31", 6, 5


def main() -> None:
    t0 = time.time()
    OUT = MODULE_ROOT / "runs" / "TRIAL-BRAIN-009"; OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    months, cols = panel.monthly_ret.index, panel.monthly_ret.columns

    ip = pd.read_parquet(MODULE_ROOT / "data" / "insider_panel.parquet",
                         columns=["permno", "filing_date", "rptowner_cik",
                                  "is_opportunistic", "value"])
    ip = ip[(ip["is_opportunistic"] == True) & ip["permno"].notna()  # noqa: E712
            & (ip["value"] > 0)].copy()
    ip["m"] = pd.to_datetime(ip["filing_date"]).dt.to_period("M").dt.to_timestamp("M")
    ip["sym"] = ip["permno"].astype("Int64").astype(str)

    # distinct buyers per (month, name), then trailing-3-month distinct proxy:
    # union of buyer sets across 3 months approximated by 3-month max of the
    # monthly distinct count plus month-count>1 union bonus is NOT exact —
    # compute the exact trailing-90d distinct count instead (rolling window).
    per = ip.groupby(["m", "sym"])["rptowner_cik"].agg(set).rename("bset").reset_index()
    per = per[per["sym"].isin(cols)]
    wide_sets: dict = {}
    for _, r in per.iterrows():
        wide_sets.setdefault(r["sym"], {})[r["m"]] = r["bset"]

    F_B2 = pd.DataFrame(False, index=months, columns=cols)
    F_B3 = pd.DataFrame(False, index=months, columns=cols)
    F_COV = pd.DataFrame(False, index=months, columns=cols)
    midx = list(months)
    for sym, by_m in wide_sets.items():
        for i, m in enumerate(midx):
            u: set = set()
            for w in midx[max(0, i - 2):i + 1]:
                u |= by_m.get(w, set())
            if u:
                F_COV.loc[m, sym] = True
                if len(u) >= 2:
                    F_B2.loc[m, sym] = True
            if len(by_m.get(m, set())) >= 3:
                F_B3.loc[m, sym] = True

    rng = np.random.default_rng(20260724)
    F_N = pd.DataFrame(False, index=months, columns=cols)
    for m in months:
        pool = cols[F_COV.loc[m].values]
        k = int(F_B2.loc[m].sum())
        if k and len(pool):
            F_N.loc[m, rng.choice(pool, size=min(k, len(pool)), replace=False)] = True

    arms = {"B": hold_band(F_B2, HOLD), "B3": hold_band(F_B3, HOLD),  # B = the >=2/90d cluster arm
            "noise": hold_band(F_N, HOLD)}
    res = run_arms(panel, arms, START, END, MODULE_ROOT / "data",
                   min_names=MIN_NAMES, factor_alpha_arms=("B", "B3"),
                   coverage=hold_band(F_COV, HOLD))
    res.pop("nets", None)
    out = {"trial": "TRIAL-BRAIN-009-insider-cluster", "window": f"{START}..{END}",
           "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "min_names": MIN_NAMES, **res, "elapsed_s": round(time.time() - t0, 1)}
    (OUT / "results.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
