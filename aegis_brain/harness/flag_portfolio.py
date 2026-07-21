"""Reusable long-only flag-portfolio backtest for event/quintile signals.

Shared by BRAIN-003/004/005 so every signal runs through ONE audited path (audit fixes
baked in: NaN forward returns dropped + weights renormalized (M4); ADV-conditional costs;
cap-segment benchmark; leak/gross columns). A "flag" is a boolean [month x permno] telling
which names to hold that month; callers build flags from their signal (event flag, top
quintile, etc.). This module never look-ahead: it earns ret.shift(-1) on info through t.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.harness.benchmark import factor_alpha, load_ff_factors, newey_west_tstat
from aegis_brain.harness.costs import one_way_cost_bps
from aegis_brain.gate.adoption import evaluate_candidate
from aegis_brain.gate.registry import cumulative_trial_count

FF_COLS = ["mktrf", "smb", "hml", "rmw", "cma", "umd"]


def hold_band(flag: pd.DataFrame, months: int) -> pd.DataFrame:
    """Held if flagged in any of the trailing `months` months (the turnover band)."""
    return flag.astype(float).rolling(months, min_periods=1).max().fillna(0) > 0


def quintile_flag(signal: pd.DataFrame, eligible: pd.DataFrame, top: bool = True,
                  q: float = 0.2) -> pd.DataFrame:
    """Top (or bottom) q-quantile of a cross-sectional signal among eligible names, per month."""
    s = signal.where(eligible)
    if top:
        thr = s.quantile(1 - q, axis=1)
        return s.ge(thr, axis=0) & eligible
    thr = s.quantile(q, axis=1)
    return s.le(thr, axis=0) & eligible


def backtest_arm(held, eligible, seg, ret_fwd, dvol, min_names: int = 20) -> dict:
    """One arm x segment: long-only EW, ADV cost on traded fraction, cap-seg EW benchmark."""
    held = held & eligible & seg
    bench_pool = eligible & seg
    cost_bps = one_way_cost_bps(dvol)

    valid = held & ret_fwd.notna()                      # M4: only investable names
    n = valid.sum(axis=1)
    w = valid.div(n.where(n > 0), axis=0).fillna(0.0)
    gross = (w * ret_fwd.fillna(0.0)).sum(axis=1)
    cost = (w.diff().abs() * (cost_bps / 1e4)).sum(axis=1)
    net = gross - cost

    bvalid = bench_pool & ret_fwd.notna()
    nb = bvalid.sum(axis=1)
    bw = bvalid.div(nb.where(nb > 0), axis=0).fillna(0.0)
    bench = (bw * ret_fwd.fillna(0.0)).sum(axis=1)

    live = n >= min_names
    idx = net.index[live]
    ex_net = (net - bench)[idx]
    ex_gross = (gross - bench)[idx]
    post = ex_net[ex_net.index >= "2016-01-01"]
    return {
        "net": net[idx].astype(float), "excess_net": ex_net.astype(float),
        "n_months": int(len(idx)), "mean_names": round(float(n[live].mean()), 1) if live.any() else 0,
        "excess_net_bps": round(float(ex_net.mean()) * 1e4, 1),
        "t_excess_net": newey_west_tstat(ex_net)["t"],
        "t_excess_gross": newey_west_tstat(ex_gross)["t"],
        "t_excess_net_post2015": newey_west_tstat(post)["t"] if len(post) >= 12 else None,
        "sharpe_net_ann": round(float(net[idx].mean() / net[idx].std(ddof=1) * np.sqrt(12)), 3)
        if net[idx].std(ddof=1) else None,
    }


def run_arms(panel, arms: dict, start: str, end: str, ff_dir,
             min_names: int = 20, factor_alpha_arms=("B",)) -> dict:
    """Run each arm across two cap segments (large/mid vs micro), compute PBO across the
    batch, DSR against the honest config count, and FF5+UMD alpha for the requested arms.
    `arms` maps arm-label -> already-hold-banded boolean [month x permno]."""
    months = panel.monthly_ret.index
    months = months[(months >= start) & (months <= end)]
    ret_fwd = panel.monthly_ret.loc[months].shift(-1)
    dvol = panel.monthly_dollar_vol.loc[months]
    elig = panel.eligible().loc[months]
    dv_e = dvol.where(elig)
    med = dv_e.median(axis=1)
    segs = {"large_mid": elig & dv_e.ge(med, axis=0), "micro": elig & dv_e.lt(med, axis=0)}
    ff = load_ff_factors(ff_dir)

    results, nets = {}, []
    for aname, held in arms.items():
        held = held.reindex(index=months, columns=panel.monthly_ret.columns, fill_value=False)
        for sname, seg in segs.items():
            r = backtest_arm(held, elig, seg, ret_fwd, dvol, min_names)
            nets.append(r["net"].rename(f"{aname}_{sname}"))
            summ = {k: v for k, v in r.items() if k not in ("net", "excess_net")}
            if aname in factor_alpha_arms:
                fa = factor_alpha((r["net"] - ff["rf"]).dropna(), ff, FF_COLS)
                summ["ff5umd_alpha_bps_m"] = round(fa["alpha_m"] * 1e4, 1) if fa["alpha_m"] is not None else None
                summ["ff5umd_alpha_t"] = round(fa["t_alpha"], 2) if fa["t_alpha"] is not None else None
            results[f"{aname}_{sname}"] = summ

    perf = pd.concat(nets, axis=1).dropna().astype(float)
    best = max(("large_mid", "micro"), key=lambda s: results[f"B_{s}"]["t_excess_net"] or -9)
    opp_net = [n for n in nets if n.name == f"B_{best}"][0].dropna().astype(float)
    n_tr = cumulative_trial_count() + perf.shape[1]
    gate = evaluate_candidate(opp_net.values, perf_matrix=perf.values, n_trials=n_tr)
    return {
        "arms": results, "best_B_segment": best, "n_configs": perf.shape[1],
        "gate_B_best": {"n_trials": n_tr, "dsr": gate["dsr"]["dsr"],
                        "pbo": (gate["pbo"] or {}).get("pbo"), "verdict": gate["verdict"]},
        "nets": {n.name: n for n in nets},  # per-config net series (for spread tests)
    }
