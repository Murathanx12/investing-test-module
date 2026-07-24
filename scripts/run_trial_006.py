"""TRIAL-BRAIN-006-fda-approval-drift — one execution, results final.

Long-only calendar-time portfolio of NDA/BLA approval names on CRSP 2002-2024:
flag in the approval month (harness earns ret.shift(-1) -> approval-month pop
excluded), 3-month hold-band, ADV costs, benchmark = pharma/biotech coverage
universe (SIC 2830-2836 / 8731) EW within segment. Arms: B = all matched
in-panel events; B_PRI = PRIORITY reviews; noise = per-name approval months
permuted within each permno's panel-live months (timing placebo).
min_names=5 (events are sparse — ~2.6/mo raw; disclosed, not hidden).
Usage: .venv\\Scripts\\python -m scripts.run_trial_006
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

START, END, HOLD, MIN_NAMES = "2002-01-01", "2024-12-31", 3, 5
PHARMA_SIC = set(range(2830, 2837)) | {8731}


def pharma_coverage(months, cols) -> pd.DataFrame:
    """[month x permno] True while the permno's date-valid CRSP name row carries a
    pharma/biotech SIC — the benchmark universe (and noise pool)."""
    sn = pd.read_parquet(MODULE_ROOT / "data" / "wrds_raw" / "crsp_stocknames.parquet",
                         columns=["permno", "namedt", "nameenddt", "siccd"])
    sn = sn[sn["siccd"].isin(PHARMA_SIC)].dropna(subset=["permno"])
    sn["permno"] = sn["permno"].astype(int).astype(str)
    sn["namedt"] = pd.to_datetime(sn["namedt"])
    sn["nameenddt"] = pd.to_datetime(sn["nameenddt"]).fillna(pd.Timestamp("2100-01-01"))
    cov = pd.DataFrame(False, index=months, columns=cols)
    for p, g in sn.groupby("permno"):
        if p not in cov.columns:
            continue
        m = pd.Series(False, index=months)
        for _, r in g.iterrows():
            m |= (months >= r["namedt"].to_period("M").to_timestamp("M")) & \
                 (months <= r["nameenddt"])
        cov[p] = m.values
    return cov


def main() -> None:
    t0 = time.time()
    OUT = MODULE_ROOT / "runs" / "TRIAL-BRAIN-006"; OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    months, cols = panel.monthly_ret.index, panel.monthly_ret.columns

    cw = pd.read_parquet(MODULE_ROOT / "data" / "events" / "fda_crosswalk.parquet")
    ev = cw[cw["permno"].notna() & cw["in_panel_universe"] &
            (cw["approval_date"] <= END)].copy()
    ev["m"] = ev["approval_date"].dt.to_period("M").dt.to_timestamp("M")
    ev["p"] = ev["permno"].astype("Int64").astype(str)
    ev = ev[ev["p"].isin(cols)]
    n_events = int(len(ev))

    F_B = pd.DataFrame(False, index=months, columns=cols)
    for _, r in ev.iterrows():
        if r["m"] in months:
            F_B.loc[r["m"], r["p"]] = True
    pri = ev[ev["review_priority"] == "PRIORITY"]
    F_P = pd.DataFrame(False, index=months, columns=cols)
    for _, r in pri.iterrows():
        if r["m"] in months:
            F_P.loc[r["m"], r["p"]] = True

    # noise arm: permute each event's month within that permno's panel-live months
    rng = np.random.default_rng(20260724)
    live = panel.monthly_ret.notna()
    F_N = pd.DataFrame(False, index=months, columns=cols)
    for p, g in ev.groupby("p"):
        alive = months[live[p].reindex(months).fillna(False).values]
        if len(alive):
            for m in rng.choice(alive, size=len(g), replace=True):
                F_N.loc[m, p] = True

    cov = pharma_coverage(months, cols)
    arms = {"B": hold_band(F_B, HOLD), "B_PRI": hold_band(F_P, HOLD),
            "noise": hold_band(F_N, HOLD)}
    res = run_arms(panel, arms, START, END, MODULE_ROOT / "data",
                   min_names=MIN_NAMES, factor_alpha_arms=("B", "B_PRI"), coverage=cov)
    res.pop("nets", None)

    out = {"trial": "TRIAL-BRAIN-006-fda-approval-drift", "window": f"{START}..{END}",
           "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "n_matched_in_panel_events": n_events,
           "n_priority_events": int(len(pri)),
           "coverage_floor_600_met": n_events >= 600,
           "min_names": MIN_NAMES, **res,
           "elapsed_s": round(time.time() - t0, 1)}
    (OUT / "results.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
