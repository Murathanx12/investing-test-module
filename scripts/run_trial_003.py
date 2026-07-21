"""TRIAL-BRAIN-003-opportunistic-insider — one execution, results final.

Long-only opportunistic-insider flag portfolios on paper-grade CRSP 2006-2024, in two
cap segments, with a 12-month hold-band and ADV-conditional costs. Three arms:
  Arm B  opportunistic buys (hypothesis)
  Arm A  routine buys       (placebo — CMP says ~0)
  Arm C  noise              (random flags matched to Arm B count — gross-t leak bar)

Audit fixes baked in: signal stamped at FILING date (M7); NaN forward returns dropped +
weights renormalized, count logged (M4); PBO computed across the batch and DSR deflated
against the honest config count (M2/M3); CRSP panel now return-hygiene-guarded (H1).

Usage:  .venv\\Scripts\\python -m scripts.run_trial_003
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
from aegis_brain.gate.adoption import evaluate_candidate
from aegis_brain.harness.benchmark import factor_alpha, load_ff_factors, newey_west_tstat
from aegis_brain.harness.costs import one_way_cost_bps

PANEL_CACHE = MODULE_ROOT / "data" / "crsp_panel_2002"
INSIDER = MODULE_ROOT / "data" / "insider_panel.parquet"
OUT = MODULE_ROOT / "runs" / "TRIAL-BRAIN-003"
START, END = "2006-01-01", "2024-12-31"
HOLD_MONTHS = 12
MIN_NAMES = 20
FF_COLS = ["mktrf", "smb", "hml", "rmw", "cma", "umd"]


def monthly_flags(insider: pd.DataFrame, mask: pd.Series, months, cols) -> pd.DataFrame:
    """Boolean [month x permno]: True if a qualifying purchase was FILED that month."""
    sub = insider[mask].copy()
    sub["m"] = sub["filing_date"].dt.to_period("M").dt.to_timestamp("M")
    sub["p"] = sub["permno"].astype("Int64").astype(str)
    g = sub.groupby(["m", "p"]).size().reset_index(name="n")
    F = pd.DataFrame(False, index=months, columns=cols)
    g = g[g["m"].isin(months) & g["p"].isin(cols)]
    for m, p in zip(g["m"], g["p"]):
        F.at[m, p] = True
    return F


def hold_band(F: pd.DataFrame) -> pd.DataFrame:
    """12-month hold: held if flagged in any of the trailing HOLD_MONTHS months."""
    return F.astype(float).rolling(HOLD_MONTHS, min_periods=1).max().fillna(0) > 0


def backtest(held_raw, eligible, seg, ret_fwd, dvol):
    """One arm×segment. Returns dict with monthly series + summary. Long-only EW,
    ADV cost on traded fraction, benchmarked to the cap-segment EW."""
    held = held_raw & eligible & seg
    bench_pool = eligible & seg
    cost_bps = one_way_cost_bps(dvol)

    # M4: only names with a valid forward return are investable; renormalize over them.
    valid = held & ret_fwd.notna()
    n_held = valid.sum(axis=1)
    w = valid.div(n_held.where(n_held > 0), axis=0).fillna(0.0)
    gross = (w * ret_fwd.fillna(0.0)).sum(axis=1)
    dw = w.diff().abs()
    cost = (dw * (cost_bps / 1e4)).sum(axis=1)
    net = gross - cost

    bvalid = bench_pool & ret_fwd.notna()
    nb = bvalid.sum(axis=1)
    bw = bvalid.div(nb.where(nb > 0), axis=0).fillna(0.0)
    bench = (bw * ret_fwd.fillna(0.0)).sum(axis=1)

    live = n_held >= MIN_NAMES
    idx = net.index[live]
    ex_net = (net - bench)[idx]
    ex_gross = (gross - bench)[idx]
    nan_dropped = int((held & ret_fwd.isna()).sum().sum())
    post = ex_net[ex_net.index >= "2016-01-01"]

    return {
        "net": net[idx], "excess_net": ex_net,
        "n_months": int(len(idx)), "mean_names": round(float(n_held[live].mean()), 1),
        "nan_returns_dropped": nan_dropped,
        "excess_net_bps": round(float(ex_net.mean()) * 1e4, 1),
        "t_excess_net": newey_west_tstat(ex_net)["t"],
        "t_excess_gross": newey_west_tstat(ex_gross)["t"],
        "t_excess_net_post2015": newey_west_tstat(post)["t"] if len(post) >= 12 else None,
        "sharpe_net_ann": round(float(net[idx].mean() / net[idx].std(ddof=1) * np.sqrt(12)), 3)
        if net[idx].std(ddof=1) else None,
    }


def main() -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(PANEL_CACHE)
    ins = pd.read_parquet(INSIDER)
    ins = ins[ins["permno"].notna() & ins["is_classifiable"]].copy()
    ins = ins[(ins["filing_date"] >= START) & (ins["filing_date"] <= END)]

    months = panel.monthly_ret.index
    months = months[(months >= START) & (months <= END)]
    cols = panel.monthly_ret.columns
    ret = panel.monthly_ret.loc[months]
    ret_fwd = ret.shift(-1)
    dvol = panel.monthly_dollar_vol.loc[months]
    elig = panel.eligible().loc[months]

    # cap segments by within-month eligible dollar-volume median (liquidity proxy for cap)
    dv_elig = dvol.where(elig)
    med = dv_elig.median(axis=1)
    large = elig & dv_elig.ge(med, axis=0)
    micro = elig & dv_elig.lt(med, axis=0)

    opp_mask = ins["is_classifiable"] & ~ins["is_routine"]
    rou_mask = ins["is_classifiable"] & ins["is_routine"]
    H_opp = hold_band(monthly_flags(ins, opp_mask, months, cols))
    H_rou = hold_band(monthly_flags(ins, rou_mask, months, cols))

    # Arm C noise: per month, random eligible names matched to opp flag count.
    rng = np.random.default_rng(20260721)
    F_noise = pd.DataFrame(False, index=months, columns=cols)
    Fopp_raw = monthly_flags(ins, opp_mask, months, cols)
    for m in months:
        k = int(Fopp_raw.loc[m].sum())
        pool = cols[elig.loc[m].values]
        if k and len(pool):
            pick = rng.choice(pool, size=min(k, len(pool)), replace=False)
            F_noise.loc[m, pick] = True
    H_noise = hold_band(F_noise)

    arms = {"opp": H_opp, "routine": H_rou, "noise": H_noise}
    segs = {"large_mid": large, "micro": micro}
    results, series_for_pbo = {}, []
    for aname, H in arms.items():
        for sname, seg in segs.items():
            r = backtest(H, elig, seg, ret_fwd, dvol)
            results[f"{aname}_{sname}"] = {k: v for k, v in r.items()
                                           if k not in ("net", "excess_net")}
            series_for_pbo.append(r["net"].rename(f"{aname}_{sname}"))
            # factor alpha on the arm's net excess-over-rf (only for opp/routine)
            if aname in ("opp", "routine"):
                ff = load_ff_factors(MODULE_ROOT / "data")
                port_rf = (r["net"] - ff["rf"]).dropna()
                fa = factor_alpha(port_rf, ff, FF_COLS)
                results[f"{aname}_{sname}"]["ff5umd_alpha_bps_m"] = (
                    round(fa["alpha_m"] * 1e4, 1) if fa["alpha_m"] is not None else None)
                results[f"{aname}_{sname}"]["ff5umd_alpha_t"] = (
                    round(fa["t_alpha"], 2) if fa["t_alpha"] is not None else None)

    # M2/M3: PBO across the batch + DSR against the honest config count.
    perf = pd.concat(series_for_pbo, axis=1).dropna().astype(float)
    n_configs = perf.shape[1]
    best_seg = max(("large_mid", "micro"),
                   key=lambda s: results[f"opp_{s}"]["t_excess_net"] or -9)
    opp_net = pd.concat([s for s in series_for_pbo if s.name == f"opp_{best_seg}"], axis=1).iloc[:, 0].astype(float)
    from aegis_brain.gate.registry import cumulative_trial_count
    n_tr = cumulative_trial_count() + n_configs
    gate = evaluate_candidate(opp_net.dropna().values, perf_matrix=perf.values, n_trials=n_tr)

    out = {
        "trial": "TRIAL-BRAIN-003-opportunistic-insider",
        "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "window": f"{START}..{END}", "hold_months": HOLD_MONTHS,
        "n_configs_added_to_trialcount": n_configs, "best_opp_segment": best_seg,
        "arms": results,
        "gate_opp_best": {"n_trials": n_tr, "dsr": gate["dsr"]["dsr"],
                          "pbo": (gate["pbo"] or {}).get("pbo"), "verdict": gate["verdict"],
                          "reasons": gate["reasons"]},
        "elapsed_s": round(time.time() - t0, 1),
    }
    (OUT / "results.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
