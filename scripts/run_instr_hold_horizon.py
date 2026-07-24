"""INSTR-HOLD-HORIZON — hold-band curve on the frozen BRAIN-007 composite.

Byte-identical composite construction to run_trial_007 (insider+gp z, top
quintile large/mid, ADV costs, 2006-2024); the ONLY varied parameter is the
book's hold-band length. Measurement instrument: reported only.
Usage: .venv\\Scripts\\python -m scripts.run_instr_hold_horizon
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
from aegis_brain.factory.fundamentals import FundStore
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.harness.costs import one_way_cost_bps
from scripts.run_trial_007 import (INSIDER_HOLD_M, MIN_NAMES, TOP_Q,  # noqa: F401
                                   insider_flag, zscore)

PANEL_CACHE = MODULE_ROOT / "data" / "crsp_panel_2002"
OUT = MODULE_ROOT / "runs" / "INSTR-HOLD-HORIZON"
START, END = "2006-01-01", "2024-12-31"
BANDS = (1, 3, 6, 12, 24)


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(PANEL_CACHE)
    months_all = panel.monthly_ret.index
    months = months_all[(months_all >= START) & (months_all <= END)]
    cols = panel.monthly_ret.columns
    ret_fwd = panel.monthly_ret.loc[months].shift(-1)
    dvol = panel.monthly_dollar_vol.loc[months]
    elig = panel.eligible().loc[months]
    dv_elig = dvol.where(elig)
    large = elig & dv_elig.ge(dv_elig.median(axis=1), axis=0)

    gp = FundStore(panel).get("gross_prof").loc[months]
    flag = insider_flag(panel, months, cols)
    z_gp = zscore(gp.where(elig & large))
    z_in = zscore(flag.astype(float).where(elig & large))
    composite = pd.concat([z_gp, z_in]).groupby(level=0).mean().where(gp.notna())

    s = composite.where(elig & large)
    q = s.rank(axis=1, pct=True, ascending=True)
    top = q >= (1 - TOP_Q)
    cost_bps = one_way_cost_bps(dvol)

    curve = {}
    for band in BANDS:
        held = top.astype(float).rolling(band, min_periods=1).max().fillna(0) > 0
        held = held & elig & large
        valid = held & ret_fwd.notna()
        n = valid.sum(axis=1)
        w = valid.div(n.where(n > 0), axis=0).fillna(0.0)
        gross = (w * ret_fwd.fillna(0.0)).sum(axis=1)
        turnover = w.diff().abs().sum(axis=1) / 2  # one-way fraction of book
        cost = (w.diff().abs() * (cost_bps / 1e4)).sum(axis=1)
        net = gross - cost
        bpool = elig & large & ret_fwd.notna()
        nb = bpool.sum(axis=1)
        bw = bpool.div(nb.where(nb > 0), axis=0).fillna(0.0)
        bench = (bw * ret_fwd.fillna(0.0)).sum(axis=1)
        idx = net.index[n >= MIN_NAMES]
        ex = (net - bench)[idx]
        curve[f"band_{band}m"] = {
            "excess_net_bps": round(float(ex.mean()) * 1e4, 1),
            "t_excess_net": round(newey_west_tstat(ex)["t"], 2),
            "one_way_turnover_pct_mo": round(float(turnover[idx].mean()) * 100, 1),
            "sharpe_net_ann": round(float(net[idx].mean() / net[idx].std(ddof=1)
                                          * np.sqrt(12)), 3),
            "mean_names": round(float(n[idx].mean()), 1),
        }
        print(f"band {band:>2}m: {curve[f'band_{band}m']}", flush=True)

    out = {"instrument": "INSTR-HOLD-HORIZON", "window": f"{START}..{END}",
           "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "curve": curve, "elapsed_s": round(time.time() - t0, 1)}
    (OUT / "results.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2), flush=True)


if __name__ == "__main__":
    main()
