"""TRIAL-COND-VT — conditional (extremes-only) volatility targeting on SPY.

Pre-registered 2026-07-29 in TRIALS/TRIAL-COND-VT.md + TRIALS/registry.jsonl
BEFORE this file existed. Spec is frozen there; this runner implements it
verbatim and has no tuning knobs exposed on the command line.

    python -m scripts.trial_cond_vt            # explore 2004-01-01..2018-12-31
    python -m scripts.trial_cond_vt --confirm  # HELD OUT 2019-01-01..2024-12-31
                                               # (only on an explore pass)

Causality: the vol signal and the expanding-window breakpoint at month-end t
use data <= t only; the resulting weight is applied to the FOLLOWING month's
returns. `assert_causal()` proves it by perturbation and aborts the run on
failure. Data after CONFIRM_END is never loaded (forward reserve).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODULE_ROOT = Path(__file__).resolve().parents[1]
ETF_PATH = MODULE_ROOT / "data" / "macro" / "etf_daily_close.parquet"
OUT_DIR = MODULE_ROOT / "data" / "factory"

# ---- frozen parameters (TRIAL-COND-VT §7) --------------------------------
VOL_WINDOW = 63           # trailing trading days for realized vol
ANNUALIZER = 252
BURN_IN = 756             # vol observations required before first signal
QUANTILE_HI = 0.80        # extreme high-vol breakpoint (top quintile)
QUANTILE_MED = 0.50       # descriptive unconditional arm only
LEV_CAP = 1.0             # hard leverage cap, long-only
COST_BPS_BASE = 2.0       # one-sided, decides the bars
COST_BPS_STRESS = 10.0    # reported, never deciding
BLOCK = 21                # circular block bootstrap block length (td)
N_BOOT = 2000
BOOT_SEED = 20260729

EXPLORE_START = pd.Timestamp("2004-01-01")
EXPLORE_END = pd.Timestamp("2018-12-31")
CONFIRM_START = pd.Timestamp("2019-01-01")
CONFIRM_END = pd.Timestamp("2024-12-31")   # forward reserve beyond this

# ---- frozen bars (TRIAL-COND-VT §8) --------------------------------------
BAR_SHARPE_TOL = 0.05     # net Sharpe >= SPY net Sharpe - 0.05
BAR_DD_PP = 0.05          # maxDD shallower than SPY by >= 5 percentage points
BAR_TURNOVER = 0.50       # avg one-sided turnover <= 50%/month


# ==========================================================================
# data
# ==========================================================================
def load_closes(as_of: pd.Timestamp) -> pd.DataFrame:
    """SPY/TLT closes truncated at `as_of` — nothing beyond it is ever read."""
    df = pd.read_parquet(ETF_PATH).sort_index()
    return df.loc[:as_of, ["SPY", "TLT"]]


def realized_vol(px: pd.Series) -> pd.Series:
    r = px.pct_change(fill_method=None)
    return r.rolling(VOL_WINDOW).std(ddof=1) * np.sqrt(ANNUALIZER)


def month_ends(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last trading day present in the index for each calendar month."""
    s = pd.Series(idx, index=idx)
    return pd.DatetimeIndex(s.groupby([idx.year, idx.month]).last().values)


# ==========================================================================
# weights (causal by construction)
# ==========================================================================
def _causal_weight(vol_hist: pd.Series, q: float, conditional: bool) -> float:
    """vol_hist = ALL realized-vol observations <= month-end t (inclusive)."""
    v = vol_hist.dropna()
    if len(v) < BURN_IN:
        return LEV_CAP                       # burn-in: unscaled, no trading
    cur = float(v.iloc[-1])
    bp = float(v.quantile(q))
    if conditional and cur < bp:
        return LEV_CAP                       # not in the extreme state
    if cur <= 0:
        return LEV_CAP
    return float(min(LEV_CAP, bp / cur))


def weight_path(vol: pd.Series, idx: pd.DatetimeIndex, *, conditional: bool,
                q: float) -> tuple[pd.Series, pd.Series]:
    """Daily SPY weight. Weight decided at month-end t applies to the days
    AFTER t through the next month-end (inclusive)."""
    mes = month_ends(idx)
    decided = {t: _causal_weight(vol.loc[:t], q, conditional) for t in mes}
    w = pd.Series(np.nan, index=idx, dtype=float)
    pos = idx.get_indexer(mes)
    for k, t in enumerate(mes):
        start = pos[k] + 1
        end = pos[k + 1] if k + 1 < len(mes) else len(idx) - 1
        if start <= end:
            w.iloc[start:end + 1] = decided[t]
    w.iloc[:pos[0] + 1] = LEV_CAP            # before the first decision: SPY
    return w.ffill().fillna(LEV_CAP), pd.Series(decided)


# ==========================================================================
# backtest mechanics
# ==========================================================================
def run_arm(weights: pd.DataFrame, rets: pd.DataFrame, bps: float) -> pd.DataFrame:
    w = weights.reindex(rets.index).fillna(0.0)
    gross = (w * rets[w.columns]).sum(axis=1)
    traded = w.diff().abs().sum(axis=1).fillna(w.iloc[0].abs().sum())
    net = gross - traded * bps / 1e4
    return pd.DataFrame({"gross": gross, "net": net, "traded": traded})


def stats(net: pd.Series, traded: pd.Series | None = None,
          gross: pd.Series | None = None) -> dict:
    net = net.dropna()
    cum = (1 + net).cumprod()
    years = len(net) / ANNUALIZER
    dd = cum / cum.cummax() - 1
    sd = net.std(ddof=1)
    roll12 = (1 + net).rolling(ANNUALIZER).apply(np.prod, raw=True) - 1
    cagr = float(cum.iloc[-1] ** (1 / years) - 1)
    mdd = float(dd.min())
    out = {
        "days": int(len(net)),
        "cagr": round(cagr, 4),
        "vol_ann": round(float(sd * np.sqrt(ANNUALIZER)), 4),
        "sharpe": round(float(net.mean() / sd * np.sqrt(ANNUALIZER)), 3),
        "max_dd": round(mdd, 4),
        "calmar": round(cagr / abs(mdd), 3) if mdd < 0 else None,
        "worst_roll_12m": round(float(roll12.min()), 4),
    }
    if traded is not None:
        t = traded.reindex(net.index).fillna(0.0)
        n_months = len(t.resample("ME").sum())
        out["turnover_per_month"] = round(float(t.sum() / n_months), 4)
        out["turnover_per_year"] = round(float(t.sum() / (len(net) / ANNUALIZER)), 3)
    if gross is not None:
        g = gross.reindex(net.index)
        out["cost_drag_ann_bps"] = round(float((g.mean() - net.mean())
                                               * ANNUALIZER * 1e4), 2)
    return out


def sharpe(x: np.ndarray) -> float:
    s = x.std(ddof=1)
    return float(x.mean() / s * np.sqrt(ANNUALIZER)) if s > 0 else np.nan


def block_bootstrap_ci(a: pd.Series, b: pd.Series, alpha: float = 0.10) -> dict:
    """Circular block bootstrap (block=21td) 90% CI on Sharpe(a) - Sharpe(b).
    Same block indices for both series -> paired dependence preserved."""
    x, y = a.dropna().values, b.reindex(a.dropna().index).values
    n = len(x)
    n_blocks = int(np.ceil(n / BLOCK))
    rng = np.random.default_rng(BOOT_SEED)
    diffs = np.empty(N_BOOT)
    for i in range(N_BOOT):
        starts = rng.integers(0, n, n_blocks)
        idx = np.concatenate([(np.arange(s, s + BLOCK) % n) for s in starts])[:n]
        diffs[i] = sharpe(x[idx]) - sharpe(y[idx])
    return {
        "point": round(sharpe(x) - sharpe(y), 3),
        "lo": round(float(np.quantile(diffs, alpha / 2)), 3),
        "hi": round(float(np.quantile(diffs, 1 - alpha / 2)), 3),
        "p_neg": round(float((diffs < 0).mean()), 3),
    }


# ==========================================================================
# causality proof
# ==========================================================================
def assert_causal(closes: pd.DataFrame, probe: pd.Timestamp) -> dict:
    """Perturb every close STRICTLY AFTER `probe`; the weight decided at
    `probe` must be bit-identical. Aborts the run on failure."""
    idx = closes.index
    t = idx[idx <= probe][-1]
    base = _causal_weight(realized_vol(closes["SPY"]).loc[:t], QUANTILE_HI, True)

    rng = np.random.default_rng(1)
    pert = closes.copy()
    after = pert.index > t
    pert.loc[after, "SPY"] = (pert.loc[after, "SPY"].values
                              * rng.uniform(0.3, 3.0, after.sum()))
    shocked = _causal_weight(realized_vol(pert["SPY"]).loc[:t], QUANTILE_HI, True)

    if base != shocked:
        raise SystemExit(f"CAUSALITY VIOLATION at {t.date()}: "
                         f"{base!r} -> {shocked!r} after perturbing t+1..T")
    return {"probe_date": str(t.date()), "weight": round(base, 6),
            "weight_after_post_t_shock": round(shocked, 6), "identical": True}


# ==========================================================================
# episodes
# ==========================================================================
def episode(net: pd.Series, w: pd.Series, year: int) -> dict:
    m = net.index.year == year
    if not m.any():
        return {}
    r = net[m]
    cum = (1 + r).cumprod()
    ww = w.reindex(r.index)
    return {
        "year": year,
        "return": round(float(cum.iloc[-1] - 1), 4),
        "in_year_max_dd": round(float((cum / cum.cummax() - 1).min()), 4),
        "min_weight": round(float(ww.min()), 3),
        "mean_weight": round(float(ww.mean()), 3),
        "pct_days_derisked": round(float((ww < 0.999).mean()), 3),
    }


# ==========================================================================
# main
# ==========================================================================
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="open the HELD-OUT 2019-2024 window (explore pass only)")
    args = ap.parse_args()

    if args.confirm:
        tag, w_start, w_end, data_end = "confirm", CONFIRM_START, CONFIRM_END, CONFIRM_END
    else:
        tag, w_start, w_end, data_end = "explore", EXPLORE_START, EXPLORE_END, EXPLORE_END

    closes = load_closes(data_end)
    print(f"[{tag}] data loaded {closes.index[0].date()}..{closes.index[-1].date()} "
          f"({len(closes)} rows)  SPY/TLT")

    causal = assert_causal(closes, pd.Timestamp("2010-06-30"))
    print(f"[{tag}] causality assertion PASS at {causal['probe_date']}: "
          f"w={causal['weight']} unchanged by post-t perturbation")

    idx = closes.index
    rets = closes.pct_change(fill_method=None)
    rets["CASH"] = 0.0
    vol = realized_vol(closes["SPY"])

    w_cond, dec_cond = weight_path(vol, idx, conditional=True, q=QUANTILE_HI)
    w_unc, dec_unc = weight_path(vol, idx, conditional=False, q=QUANTILE_MED)

    def frame(spy_w: pd.Series, tlt_w: pd.Series | None = None) -> pd.DataFrame:
        d = {"SPY": spy_w, "CASH": 1.0 - spy_w - (0.0 if tlt_w is None else tlt_w)}
        if tlt_w is not None:
            d["TLT"] = tlt_w
        return pd.DataFrame(d)

    ones = pd.Series(1.0, index=idx)
    mes = month_ends(idx)
    sixty = pd.Series(np.nan, index=idx); sixty.loc[mes] = 0.6
    forty = pd.Series(np.nan, index=idx); forty.loc[mes] = 0.4
    sixty.iloc[0], forty.iloc[0] = 0.6, 0.4
    sixty, forty = sixty.ffill(), forty.ffill()

    arms = {
        "COND_VT": frame(w_cond),
        "SPY_BH": frame(ones),
        "SIXTY_FORTY": frame(sixty, forty),
        "UNCOND_VT_desc": frame(w_unc),
    }

    win = (idx >= w_start) & (idx <= w_end)
    results, results_stress = {}, {}
    nets = {}
    for name, wf in arms.items():
        bt = run_arm(wf, rets, COST_BPS_BASE)
        bts = run_arm(wf, rets, COST_BPS_STRESS)
        sub, subs = bt[win], bts[win]
        results[name] = stats(sub["net"], sub["traded"], sub["gross"])
        results_stress[name] = stats(subs["net"], subs["traded"], subs["gross"])
        nets[name] = sub["net"]

    spy_s = results["SPY_BH"]["sharpe"]
    spy_dd = results["SPY_BH"]["max_dd"]
    c = results["COND_VT"]
    bars = {
        "a_sharpe": {"value": c["sharpe"], "bar": round(spy_s - BAR_SHARPE_TOL, 3),
                     "pass": bool(c["sharpe"] >= spy_s - BAR_SHARPE_TOL)},
        "b_maxdd": {"value": c["max_dd"], "bar": round(spy_dd + BAR_DD_PP, 4),
                    "pass": bool(abs(c["max_dd"]) <= abs(spy_dd) - BAR_DD_PP)},
        "c_turnover": {"value": c["turnover_per_month"], "bar": BAR_TURNOVER,
                       "pass": bool(c["turnover_per_month"] <= BAR_TURNOVER)},
    }
    bars["ALL_PASS"] = all(v["pass"] for v in bars.values() if isinstance(v, dict))

    boot = {k: block_bootstrap_ci(nets[k], nets["SPY_BH"])
            for k in ("COND_VT", "SIXTY_FORTY", "UNCOND_VT_desc")}

    w_sub = w_cond[win]
    dec_win = dec_cond[(dec_cond.index >= w_start) & (dec_cond.index <= w_end)]
    exposure = {
        "months": int(len(dec_win)),
        "months_derisked": int((dec_win < 0.999).sum()),
        "pct_months_derisked": round(float((dec_win < 0.999).mean()), 3),
        "min_month_weight": round(float(dec_win.min()), 3),
        "mean_month_weight": round(float(dec_win.mean()), 3),
        "first_tradable_signal": (str(dec_cond[dec_cond.index >= w_start].index[0].date())
                                  if len(dec_win) else None),
        "first_derisked_month": (str(dec_win[dec_win < 0.999].index[0].date())
                                 if (dec_win < 0.999).any() else None),
    }

    episodes = {}
    for yr in (2020, 2022, 2008):
        e_c = episode(nets["COND_VT"], w_cond, yr)
        if e_c:
            episodes[str(yr)] = {"COND_VT": e_c,
                                 "SPY_BH": episode(nets["SPY_BH"], ones, yr),
                                 "UNCOND_VT_desc": episode(nets["UNCOND_VT_desc"], w_unc, yr)}

    eq = {k: {str(d.date()): round(float(v), 5)
              for d, v in (1 + nets[k]).cumprod().resample("ME").last().items()}
          for k in nets}

    payload = {
        "trial": "TRIAL-COND-VT", "window": tag,
        "window_start": str(w_start.date()), "window_end": str(w_end.date()),
        "data_end_loaded": str(closes.index[-1].date()),
        "causality_assertion": causal,
        "params": {"vol_window": VOL_WINDOW, "burn_in": BURN_IN,
                   "quantile_hi": QUANTILE_HI, "lev_cap": LEV_CAP,
                   "cost_bps_base": COST_BPS_BASE, "cost_bps_stress": COST_BPS_STRESS},
        "stats_base_2bps": results, "stats_stress_10bps": results_stress,
        "bars": bars, "bootstrap_sharpe_diff_vs_spy_90ci": boot,
        "exposure": exposure, "episodes": episodes, "equity_curve_month_end": eq,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"trial_cond_vt_{tag}.json"
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    print(f"\n=== TRIAL-COND-VT [{tag}] {w_start.date()}..{w_end.date()} ===")
    hdr = f"{'arm':<16}{'CAGR':>8}{'vol':>8}{'Sharpe':>8}{'maxDD':>9}{'Calmar':>8}{'w12m':>9}{'TO/mo':>8}{'cost bp':>9}"
    print(hdr)
    for k, v in results.items():
        print(f"{k:<16}{v['cagr']:>8.2%}{v['vol_ann']:>8.2%}{v['sharpe']:>8.2f}"
              f"{v['max_dd']:>9.2%}{(v['calmar'] or 0):>8.2f}{v['worst_roll_12m']:>9.2%}"
              f"{v['turnover_per_month']:>8.1%}{v['cost_drag_ann_bps']:>9.1f}")
    print("\nBARS (base 2bps, vs SPY B&H):")
    print(f"  (a) net Sharpe {bars['a_sharpe']['value']:.3f} >= {bars['a_sharpe']['bar']:.3f} "
          f"-> {'PASS' if bars['a_sharpe']['pass'] else 'FAIL'}")
    print(f"  (b) maxDD {bars['b_maxdd']['value']:.2%} shallower than SPY by >=5pp "
          f"(need <= {bars['b_maxdd']['bar']:.2%}) -> {'PASS' if bars['b_maxdd']['pass'] else 'FAIL'}")
    print(f"  (c) turnover {bars['c_turnover']['value']:.1%}/mo <= 50% "
          f"-> {'PASS' if bars['c_turnover']['pass'] else 'FAIL'}")
    print(f"  ALL_PASS = {bars['ALL_PASS']}")
    print("\nBootstrap 90% CI on Sharpe difference vs SPY:")
    for k, v in boot.items():
        print(f"  {k:<16} {v['point']:+.3f}  [{v['lo']:+.3f}, {v['hi']:+.3f}]  P(diff<0)={v['p_neg']:.2f}")
    print(f"\nExposure: {exposure}")
    for yr, e in episodes.items():
        print(f"\n{yr}: " + " | ".join(
            f"{a} ret {d['return']:+.2%} dd {d['in_year_max_dd']:.2%} "
            f"minw {d['min_weight']:.2f} derisked {d['pct_days_derisked']:.0%}"
            for a, d in e.items()))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
