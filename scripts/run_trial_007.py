"""TRIAL-BRAIN-007-fusion — one execution under the 2026-07-21 frozen spec.

Re-opened 2026-07-22: BRAIN-008 (gross_prof) survived its own pre-registered
kill conditions, so membership = {opportunistic_insider, gross_prof} per the
frozen membership rule. Everything below implements the spec as written:
equal-weight mean of per-month cross-sectional z-scores (winsorized +/-3),
long-only top-quintile in LARGE/MID (003's above-median-dollar-vol def),
3-month hold (003-style rolling membership), ADV one-way costs, benchmark =
large/mid EW, Arm C noise matched to book size (gross-t leak bar). Member
singles run under IDENTICAL mechanics for kill-condition #3. Ambiguities
resolved a priori (documented in the trial doc) — no tuning on returns.

Window: 2006-01..2024-12 (intersection of member data; 003's window).

Usage:  .venv\\Scripts\\python -m scripts.run_trial_007
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

PANEL_CACHE = MODULE_ROOT / "data" / "crsp_panel_2002"
INSIDER = MODULE_ROOT / "data" / "insider_panel.parquet"
OUT = MODULE_ROOT / "runs" / "TRIAL-BRAIN-007"
START, END = "2006-01-01", "2024-12-31"
INSIDER_HOLD_M = 12    # the member signal is BRAIN-003's 12m-hold flag
BAND_M = 3             # spec: 3-month hold on the composite book
TOP_Q = 0.20
MIN_NAMES = 20


def zscore(frame: pd.DataFrame) -> pd.DataFrame:
    z = frame.sub(frame.mean(axis=1), axis=0).div(frame.std(axis=1, ddof=1), axis=0)
    return z.clip(-3, 3)


def insider_flag(panel, months, cols) -> pd.DataFrame:
    ins = pd.read_parquet(INSIDER)
    ins = ins[ins["permno"].notna() & ins["is_classifiable"] & ~ins["is_routine"]]
    ins = ins[(ins["filing_date"] >= START) & (ins["filing_date"] <= END)].copy()
    ins["m"] = ins["filing_date"].dt.to_period("M").dt.to_timestamp("M")
    ins["p"] = ins["permno"].astype("Int64").astype(str)
    g = ins.groupby(["m", "p"]).size().reset_index(name="n")
    F = pd.DataFrame(False, index=months, columns=cols)
    g = g[g["m"].isin(months) & g["p"].isin(cols)]
    for m, p in zip(g["m"], g["p"]):
        F.at[m, p] = True
    return F.astype(float).rolling(INSIDER_HOLD_M, min_periods=1).max().fillna(0) > 0


def backtest(score, eligible, seg, ret_fwd, dvol):
    """Top-quintile of score, 3m rolling membership, EW, ADV costs, seg-EW bench."""
    s = score.where(eligible & seg)
    q = s.rank(axis=1, pct=True, ascending=True)
    top = q >= (1 - TOP_Q)
    held = top.astype(float).rolling(BAND_M, min_periods=1).max().fillna(0) > 0
    held = held & eligible & seg

    cost_bps = one_way_cost_bps(dvol)
    valid = held & ret_fwd.notna()
    n_held = valid.sum(axis=1)
    w = valid.div(n_held.where(n_held > 0), axis=0).fillna(0.0)
    gross = (w * ret_fwd.fillna(0.0)).sum(axis=1)
    cost = (w.diff().abs() * (cost_bps / 1e4)).sum(axis=1)
    net = gross - cost

    bpool = eligible & seg & ret_fwd.notna()
    nb = bpool.sum(axis=1)
    bw = bpool.div(nb.where(nb > 0), axis=0).fillna(0.0)
    bench = (bw * ret_fwd.fillna(0.0)).sum(axis=1)

    idx = net.index[n_held >= MIN_NAMES]
    ex_net, ex_gross = (net - bench)[idx], (gross - bench)[idx]
    return {
        "n_months": int(len(idx)), "mean_names": round(float(n_held[idx].mean()), 1),
        "excess_net_bps": round(float(ex_net.mean()) * 1e4, 1),
        "t_excess_net": newey_west_tstat(ex_net)["t"],
        "t_excess_gross": newey_west_tstat(ex_gross)["t"],
        "_ex_net": ex_net,
    }


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
    large = elig & dv_elig.ge(dv_elig.median(axis=1), axis=0)   # 003's large/mid

    gp = FundStore(panel).get("gross_prof").loc[months]
    flag = insider_flag(panel, months, cols)

    z_gp = zscore(gp.where(elig & large))
    z_in = zscore(flag.astype(float).where(elig & large))
    composite = pd.concat([z_gp, z_in]).groupby(level=0).mean()  # mean of available z
    composite = composite.where(gp.notna())  # universe = fundamentals coverage

    rng = np.random.default_rng(20260722)
    arms = {
        "composite": composite,
        "single_insider": z_in.where(gp.notna()),
        "single_gp": z_gp.where(gp.notna()),
    }
    results = {}
    for name, score in arms.items():
        r = backtest(score, elig, large, ret_fwd, dvol)
        results[name] = {k: v for k, v in r.items() if not k.startswith("_")}

    # Arm C noise: random score, same universe (gross-t leak bar)
    noise = pd.DataFrame(rng.standard_normal(composite.shape),
                         index=composite.index, columns=composite.columns
                         ).where(composite.notna())
    r_noise = backtest(noise, elig, large, ret_fwd, dvol)
    results["noise"] = {k: v for k, v in r_noise.items() if not k.startswith("_")}

    # frozen kill conditions
    tg_noise = abs(r_noise["t_excess_gross"] or 0)
    t_comp = results["composite"]["t_excess_net"] or -9
    best_single = max(results["single_insider"]["t_excess_net"] or -9,
                      results["single_gp"]["t_excess_net"] or -9)
    verdict = ("VOID (leak)" if tg_noise >= 3 else
               "REJECT (net t<1)" if t_comp < 1 else
               "SURVIVES; fusion adds nothing (<= best single)" if t_comp <= best_single
               else "SURVIVES; fusion beats best single")

    out = {"trial": "TRIAL-BRAIN-007-fusion",
           "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "window": f"{START}..{END}", "members": ["opportunistic_insider", "gross_prof"],
           "arms": results, "verdict": verdict,
           "elapsed_s": round(time.time() - t0, 1)}
    (OUT / "results.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
