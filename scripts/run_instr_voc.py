"""INSTR-VOC — falsification test of 'virtue of complexity' market timing
(Kelly-Malamud-Zhou JF 2024) on OUR data, against the Nagel-class critique.

Frozen BEFORE run (TRIALS/INSTR-VOC.md). EW CRSP market 1963-2024
(delisting-adjusted, spliced msf_ext + msf; EW disclosed — no shrout pre-2002
on disk). Features: 12 monthly lags, standardized on the training window.
Random Fourier features (drawn ONCE, seed 0), dual-space ridge (T x T solve).
Rolling 120m training. Position = forecast scaled to trailing strategy vol =
market vol, capped [-1, 2]. Benchmarks: B&H, sign-TSMOM(12), vol-managed
(Moreira-Muir). Reads: pre-window 1974-2003 (outside both walls, declared),
explore 2004-2018; confirm 2019-2024 read ONLY if the explore reading
supports the claim (frozen gate).

Usage:  .venv\\Scripts\\python -m scripts.run_instr_voc
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT

RAW = MODULE_ROOT / "data" / "wrds_raw"
OUT = MODULE_ROOT / "data" / "factory"

TRAIN = 120
LAGS = 12
P_GRID = (12, 100, 1000, 6000)     # 12 = raw features (no RFF), the low-complexity anchor
Z_PRIMARY = 1e-3
GAMMA = 2.0                        # KMZ RFF scale
SEED = 0


def ew_market() -> pd.Series:
    def _ew(path: str) -> pd.Series:
        d = pd.read_parquet(RAW / path, columns=["permno", "date", "ret", "dlret"]
                            if "ext" in path else ["permno", "date", "ret"])
        d["date"] = pd.to_datetime(d["date"])
        r = d["ret"].astype(float)
        if "dlret" in d.columns:
            dl = d["dlret"].astype(float)
            r = (1 + r.fillna(0)) * (1 + dl.fillna(0)) - 1
            r = r.where(d["ret"].notna() | d["dlret"].notna())
        d = d.assign(r=r)
        m = d.dropna(subset=["r"]).groupby(d["date"].dt.to_period("M"))["r"].mean()
        m.index = m.index.to_timestamp("M")
        return m
    a = _ew("crsp_msf_ext.parquet")          # 1963-2001
    b = _ew("crsp_msf.parquet")              # 2002-2024
    return pd.concat([a[a.index < "2002-01-01"], b]).sort_index()


def stats(x: pd.Series, label: str) -> dict:
    x = x.dropna()
    if len(x) < 12:
        return {"label": label, "months": len(x)}
    sr = float(x.mean() / x.std(ddof=1) * np.sqrt(12))
    cum = (1 + x).cumprod()
    return {"label": label, "months": int(len(x)),
            "cagr": round(float(cum.iloc[-1] ** (12 / len(x)) - 1), 4),
            "sharpe": round(sr, 2),
            "max_dd": round(float((cum / cum.cummax() - 1).min()), 3)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mkt = ew_market()
    r = mkt.dropna()
    X_raw = pd.DataFrame({f"l{k}": r.shift(k) for k in range(1, LAGS + 1)}).dropna()
    y = r.reindex(X_raw.index)

    rng = np.random.default_rng(SEED)
    omega = {p: rng.normal(0, GAMMA, size=(LAGS, p // 2)) for p in P_GRID if p > LAGS}

    fcst = {p: pd.Series(np.nan, index=X_raw.index) for p in P_GRID}
    idx = X_raw.index
    for i in range(TRAIN, len(idx)):
        Xtr = X_raw.iloc[i - TRAIN:i].to_numpy()
        ytr = y.iloc[i - TRAIN:i].to_numpy()
        xte = X_raw.iloc[i:i + 1].to_numpy()
        mu, sd = Xtr.mean(0), Xtr.std(0, ddof=1)
        sd[sd == 0] = 1.0
        Xtr = (Xtr - mu) / sd
        xte = (xte - mu) / sd
        for p in P_GRID:
            if p <= LAGS:
                S_tr, S_te = Xtr, xte
            else:
                w = omega[p]
                S_tr = np.hstack([np.sin(Xtr @ w), np.cos(Xtr @ w)]) / np.sqrt(p)
                S_te = np.hstack([np.sin(xte @ w), np.cos(xte @ w)]) / np.sqrt(p)
            # dual ridge: f = s_te' S_tr' (S_tr S_tr' + zI)^-1 y
            K = S_tr @ S_tr.T
            alpha = np.linalg.solve(K + Z_PRIMARY * np.eye(TRAIN), ytr)
            fcst[p].iloc[i] = float(S_te @ (S_tr.T @ alpha))

    var12 = r.rolling(12).var()
    out = {"spec": {"train": TRAIN, "lags": LAGS, "z": Z_PRIMARY,
                    "gamma": GAMMA, "p_grid": list(P_GRID), "market": "EW CRSP"}}

    def strat_returns(f: pd.Series) -> pd.Series:
        pos_raw = f / var12.reindex(f.index)
        scale = pos_raw.abs().rolling(60, min_periods=24).mean()
        pos = (pos_raw / scale).clip(-1, 2)
        return (pos.shift(1) * r.reindex(f.index)).dropna()

    # Nagel mechanical twin: linearly-declining weights on last 12 returns
    # (position pipeline identical to the RFF strategies)
    lin_w = np.arange(LAGS, 0, -1, dtype=float)
    lin_w /= lin_w.sum()
    nagel_f = sum(lin_w[k - 1] * r.shift(k) for k in range(1, LAGS + 1))
    nagel_f = nagel_f.reindex(X_raw.index)
    nagel_ret = strat_returns(nagel_f)

    windows = {"prewindow_1974_2003": ("1974-01-01", "2003-12-31"),
               "explore_2004_2018": ("2004-01-01", "2018-12-31")}
    bench_all = {}
    strat_all = {}
    for wname, (lo, hi) in windows.items():
        sl = slice(pd.Timestamp(lo), pd.Timestamp(hi))
        rr = r.loc[sl]
        tsmom = (np.sign((1 + r).rolling(12).apply(np.prod, raw=True) - 1)
                 .shift(1) * r).loc[sl]
        vm_raw = (1.0 / var12).shift(1)
        vm_pos = (vm_raw / vm_raw.rolling(60, min_periods=24).mean()).clip(0, 2)
        volmg = (vm_pos.shift(1) * r).loc[sl]
        bench_all[wname] = {"bh": stats(rr, "B&H"), "tsmom12": stats(tsmom, "TSMOM"),
                            "vol_managed": stats(volmg, "VolMg"),
                            "nagel_twin": stats(nagel_ret.loc[sl], "NagelTwin")}
        strat_all[wname] = {f"P{p}": stats(strat_returns(fcst[p]).loc[sl], f"P={p}")
                            for p in P_GRID}
    out["benchmarks"] = bench_all
    out["voc"] = strat_all
    big = strat_returns(fcst[P_GRID[-1]])
    corr_twin = float(big.corr(nagel_ret.reindex(big.index)))
    out["corr_highest_p_vs_nagel_twin"] = round(corr_twin, 3)

    ex_sr = {p: strat_all["explore_2004_2018"][f"P{p}"].get("sharpe", np.nan)
             for p in P_GRID}
    bench_max = max(v.get("sharpe", -9) for v in bench_all["explore_2004_2018"].values())
    monotone = all(ex_sr[P_GRID[i]] <= ex_sr[P_GRID[i + 1]] + 0.05
                   for i in range(len(P_GRID) - 1))
    supported = (ex_sr[P_GRID[-1]] > bench_max) and monotone and corr_twin < 0.9
    out["explore_reading"] = {
        "highest_p_sharpe": ex_sr[P_GRID[-1]], "bench_max_sharpe": bench_max,
        "monotone_in_p": monotone, "corr_vs_twin": round(corr_twin, 3),
        "verdict": "SUPPORTED -> confirm read runs" if supported
                   else "NOT SUPPORTED (claim fails on our data — beaten by a "
                        "benchmark, non-monotone, or ~= the mechanical twin; "
                        "confirm stays sealed)"}

    if supported:   # frozen gate
        sl = slice(pd.Timestamp("2019-01-01"), pd.Timestamp("2024-12-31"))
        out["confirm"] = {
            "benchmarks": {"bh": stats(r.loc[sl], "B&H")},
            "voc": {f"P{p}": stats(strat_returns(fcst[p]).loc[sl], f"P={p}")
                    for p in P_GRID}}

    with open(OUT / "instr_voc.json", "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
