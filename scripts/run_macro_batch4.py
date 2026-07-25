"""Batch-4 macro instruments — ONE pre-registered explore/descriptive run.

Frozen in TRIALS/INSTR-MACRO-BATCH4.md BEFORE running. Explore window
2004-01..2018-12 ONLY; confirm 2019-2024 held out for future one-shot
registrations. Four instruments:
  1. INSTR-REGIME-JM   — 2-state statistical jump model SPY/TLT rotation
  2. INSTR-TSMOM-XA    — 12-1 cross-asset time-series momentum overlay
  3. INSTR-SBCORR      — stock-bond correlation regime gate (descriptive)
  4. INSTR-GPR-EVENT   — CAR after >2-sigma GPR spikes (descriptive)

Usage:  .venv\\Scripts\\python -m scripts.run_macro_batch4
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.macro.daily_harness import (EXPLORE_END, EXPLORE_START,
                                             backtest, daily_returns,
                                             load_closes, load_gpr_daily,
                                             stats, t_excess_monthly)
from aegis_brain.macro.jump_model import filter_states, fit_jm

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("macro4")
OUT = MODULE_ROOT / "data" / "factory"

COST_BPS = 5.0
LAM_PRIMARY = 50.0
LAM_SENS = (10.0, 100.0)


# ---------------------------------------------------------------- features
def jm_features(r: pd.Series) -> pd.DataFrame:
    f1 = r.ewm(halflife=10).mean()
    f2 = np.sqrt((r ** 2).ewm(halflife=21).mean())
    f3 = np.sqrt((r.clip(upper=0) ** 2).ewm(halflife=21).mean())
    return pd.DataFrame({"ret": f1, "vol": f2, "ddev": f3}).dropna()


def run_jm(rets: pd.DataFrame, lam: float) -> tuple[pd.Series, int]:
    """Causal monthly-expanding-refit filtered states -> daily SPY/TLT weights.
    Returns (state series over explore days, n_refits)."""
    r = rets["SPY"].dropna()
    feats = jm_features(r)
    month_ends = pd.date_range("2003-12-31", EXPLORE_END, freq="ME")
    states: list[pd.Series] = []
    n = 0
    for i, me in enumerate(month_ends[:-1]):
        nxt = month_ends[i + 1]
        hist = feats[feats.index <= me]
        if len(hist) < 252:
            continue
        mu_, sd_ = hist.mean(), hist.std(ddof=1)   # stats through m-1 only
        Xfit = ((hist - mu_) / sd_).to_numpy()
        mu = fit_jm(Xfit, lam)
        risk_off = int(np.argmax(mu[:, 1]))        # higher standardized vol
        allfeat = feats[feats.index <= nxt]
        Xall = ((allfeat - mu_) / sd_).to_numpy()
        s = filter_states(Xall, mu, lam)
        month_mask = (allfeat.index > me) & (allfeat.index <= nxt)
        st = pd.Series(s, index=allfeat.index)[month_mask]
        states.append((st == risk_off).astype(int))  # 1 = risk-off
        n += 1
    return pd.concat(states), n


# ---------------------------------------------------------------- TSMOM
def run_tsmom(closes: pd.DataFrame, rets: pd.DataFrame) -> pd.DataFrame:
    assets = ["SPY", "TLT", "GLD", "USO"]
    month_ends = rets.index[rets.index.isin(
        pd.Series(rets.index).groupby(rets.index.to_period("M")).max())]
    vol60 = rets[assets].rolling(60).std() * np.sqrt(252)
    w_rows = {}
    for me in month_ends:
        pos = closes.index.get_loc(me)
        if pos < 253:
            continue
        row = {}
        for a in assets:
            c = closes[a]
            if pd.isna(c.iloc[pos - 252]) or pd.isna(c.iloc[pos - 21]):
                continue
            sig = np.sign(c.iloc[pos - 21] / c.iloc[pos - 252] - 1)
            v = vol60[a].loc[me]
            if pd.isna(v) or v <= 0:
                continue
            row[a] = sig * min(0.10 / v, 1.5)
        if row:
            k = len(row)
            w_rows[me] = {a: x / k for a, x in row.items()}
    w = pd.DataFrame(w_rows).T.reindex(rets.index).ffill().shift(1).fillna(0.0)
    return w[assets].fillna(0.0)


# ---------------------------------------------------------------- main
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    closes = load_closes()
    rets = daily_returns(closes)
    ex = slice(EXPLORE_START, EXPLORE_END)
    spy_ex = rets["SPY"].loc[ex].dropna()
    out: dict = {}

    # -- 1. INSTR-REGIME-JM ------------------------------------------------
    jm_out = {}
    for lam in (LAM_PRIMARY, *LAM_SENS):
        risk_off, n_refits = run_jm(rets, lam)
        w = pd.DataFrame({"SPY": 1.0 - risk_off, "TLT": risk_off.astype(float)})
        w = w.shift(1).dropna()                      # trade next day
        bt = backtest(w, rets, COST_BPS)
        net = bt["net"].loc[ex]
        switches = int(risk_off.loc[ex].diff().abs().sum())
        jm_out[f"lam_{lam:g}"] = {
            **stats(net, f"JM lam={lam:g}"),
            "switches_per_yr": round(switches / 15, 1),
            "pct_risk_off": round(float(risk_off.loc[ex].mean()), 3),
            "t_excess_vs_spy_monthly": round(t_excess_monthly(net, spy_ex), 2),
            "n_refits": n_refits,
        }
        log.info("JM lam=%g done: %s", lam, jm_out[f"lam_{lam:g}"])
    out["INSTR_REGIME_JM"] = {
        "primary": f"lam_{LAM_PRIMARY:g}", **jm_out,
        "benchmarks": {
            "spy_bh": stats(spy_ex, "SPY B&H"),
            "6040": stats((0.6 * rets["SPY"] + 0.4 * rets["TLT"]).loc[ex].dropna(),
                          "60/40 daily-rebal"),
        },
    }

    # -- 2. INSTR-TSMOM-XA -------------------------------------------------
    w_ts = run_tsmom(closes, rets)
    bt_ts = backtest(w_ts, rets, COST_BPS)
    ts_net = bt_ts["net"].loc[ex]
    overlay = (0.5 * spy_ex + 0.5 * ts_net.reindex(spy_ex.index).fillna(0.0))
    y2008 = float((1 + ts_net.loc["2008"]).prod() - 1)
    out["INSTR_TSMOM_XA"] = {
        "standalone": stats(ts_net, "TSMOM XA net"),
        "corr_spy_daily": round(float(ts_net.corr(spy_ex)), 3),
        "calendar_2008": round(y2008, 4),
        "overlay_50_50": stats(overlay, "50 SPY / 50 TSMOM"),
        "spy_bh": stats(spy_ex, "SPY B&H"),
        "t_overlay_vs_spy_monthly": round(t_excess_monthly(overlay, spy_ex), 2),
    }

    # -- 3. INSTR-SBCORR (descriptive) ------------------------------------
    corr = rets["SPY"].rolling(60).corr(rets["TLT"])
    fwd21 = closes["SPY"].shift(-21) / closes["SPY"] - 1
    gld_fwd21 = closes["GLD"].shift(-21) / closes["GLD"] - 1
    m = (corr.index >= EXPLORE_START) & (corr.index <= EXPLORE_END - pd.Timedelta(days=35))
    c, f = corr[m], fwd21[m]
    dd63 = closes["SPY"] / closes["SPY"].rolling(63).max() - 1
    dip = (dd63[m] <= -0.05)
    flip = (c > 0) & (c.shift(1) <= 0) & (c.shift(5) <= 0)
    out["INSTR_SBCORR"] = {
        "pct_days_corr_pos": round(float((c > 0).mean()), 3),
        "spy_fwd21_corr_pos": round(float(f[c > 0].mean()), 4),
        "spy_fwd21_corr_neg": round(float(f[c <= 0].mean()), 4),
        "dip_fwd21_corr_pos": {"mean": round(float(f[dip & (c > 0)].mean()), 4),
                               "n": int((dip & (c > 0)).sum())},
        "dip_fwd21_corr_neg": {"mean": round(float(f[dip & (c <= 0)].mean()), 4),
                               "n": int((dip & (c <= 0)).sum())},
        "gld_fwd21_after_flip_pos": {
            "mean": round(float(gld_fwd21[m][flip].dropna().mean()), 4),
            "n": int(gld_fwd21[m][flip].dropna().shape[0])},
        "n_days": int(len(c.dropna())),
    }

    # -- 4. INSTR-GPR-EVENT (descriptive) ---------------------------------
    g = load_gpr_daily()
    thr = g.rolling(756).mean() + 2 * g.rolling(756).std()
    is_spike = (g > thr) & (g == g.rolling(30).max())
    spikes = g.index[is_spike.fillna(False)]
    kept, dropped = [], 0
    for d in spikes:
        if kept and (d - kept[-1]).days <= 30:
            dropped += 1
            continue
        kept.append(d)
    cutoff = EXPLORE_END - pd.Timedelta(days=45)
    events = [d for d in kept if pd.Timestamp("2002-06-01") <= d <= cutoff]
    cars: dict[str, list] = {"SPY": [], "USO_ex": [], "ITA_ex": []}
    for d in events:
        idx = rets.index.searchsorted(d)
        if idx + 30 >= len(rets.index):
            continue
        win = rets.iloc[idx:idx + 31]
        spy_car = float((1 + win["SPY"].fillna(0)).prod() - 1)
        cars["SPY"].append(spy_car)
        for a, key in (("USO", "USO_ex"), ("ITA", "ITA_ex")):
            if win[a].notna().sum() >= 25:
                cars[key].append(float((1 + win[a].fillna(0)).prod() - 1) - spy_car)
    out["INSTR_GPR_EVENT"] = {
        "n_events": len(events), "n_clustered_dropped": dropped,
        "spy_car30_mean": round(float(np.mean(cars["SPY"])), 4),
        "spy_car30_hit_pos": round(float(np.mean([x > 0 for x in cars["SPY"]])), 3),
        "uso_excess_car30_mean": round(float(np.mean(cars["USO_ex"])), 4) if cars["USO_ex"] else None,
        "uso_n": len(cars["USO_ex"]),
        "ita_excess_car30_mean": round(float(np.mean(cars["ITA_ex"])), 4) if cars["ITA_ex"] else None,
        "ita_n": len(cars["ITA_ex"]),
    }

    with open(OUT / "macro_batch4.json", "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))
    print(f"\n-> {OUT / 'macro_batch4.json'}")


if __name__ == "__main__":
    main()
