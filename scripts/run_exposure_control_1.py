"""EXPOSURE-CONTROL-1 — book-keyed exposure ladder, calibrated on six drawdowns,
judged on the one it was built for.

Pre-registered 2026-08-11 in TRIALS/PREREG_EXPOSURE_CONTROL_1.md at commit
c5b81aa BEFORE this file existed. Spec is frozen there; this runner implements
it verbatim and has no tuning knobs on the command line.

    python -m scripts.run_exposure_control_1

Order of operations is the prereg's: calibration grid on the levered-market
proxy -> selection per SS3 -> calibration artifact WRITTEN TO DISK -> only then
is the holdout (real conviction book) opened, once. If no candidate covers,
CALIBRATION_FAILED and the holdout is never loaded.

Causality: every weight decided at t uses book data <= t and is applied at
t+1 (one-day lag). `assert_causal()` proves it by perturbation — the decided
weight at a named probe date must be BIT-IDENTICAL after perturbing all later
data — and aborts the run on failure. Proven on the proxy AND on the holdout
book before either is evaluated.

SS18: managed-vs-unmanaged claims are paired differences on the same path with
their own bootstrap SE (same block indices both legs). SS19: every dd/wealth
number prints beside a measured 80%-power MDE (circular block bootstrap, 21td,
planted effects — dd MDEs planted as constant-exposure shaves scored against
the 5pp bar; wealth MDEs planted as drift on the demeaned daily log-diff).
Per-episode numbers are descriptive n=1 receipts and say so.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODULE_ROOT = Path(__file__).resolve().parents[1]
FF_PATH = MODULE_ROOT / "data" / "wrds_raw" / "ff_factors_daily.parquet"
OUT_DIR = MODULE_ROOT / "data" / "factory"
AEGIS = Path(r"C:\Users\mrthn\aegis-finance")
CONVICTION_CSV = AEGIS / "backend" / "data" / "conviction_prices.csv"
EXPOSURE_CONTROLLER_PY = AEGIS / "backend" / "services" / "exposure_controller.py"
V0_ARTIFACT = AEGIS / "docs" / "conviction_replay" / "exposure_controller_v0.json"

PREREG = "TRIALS/PREREG_EXPOSURE_CONTROL_1.md @ c5b81aa"

# ---- frozen parameters (prereg SS1-SS3) ----------------------------------
PROXY_BETA = 2.15               # r_book = 2.15*mktrf + rf
BETA_STAR = 1.5                 # frozen prior, NOT tuned
VOL_WINDOW = 63
ANNUALIZER = 252
DD_HYSTERESIS = 0.05            # re-enter above -(D* - 5pp)
MIN_DWELL = 10                  # trading days
LAG = 1                         # one-day lag, always
LEV_CAP = 1.0
SIGMA_GRID = (0.15, 0.20, 0.25)
DD_GRID = (0.10, 0.15, 0.20)
COST_BPS_BASE = 10.0            # one-way, decides
COST_BPS_STRESS = 50.0          # reported, never deciding
BURN_IN_TD = 252                # before each episode window
RECOVERY_TD = 252               # ~12mo after trough
V0_EXTRA_WARM_TD = 300          # extra bench history so the CONTROL is warm
                                # at episode start (disclosed; control-only)

# ---- frozen coverage / decision bars (prereg SS3-SS4) --------------------
DD_BAR_PP = 0.05                # material maxDD reduction
COVERAGE_MIN = 4                # of 6 episodes
TW_REJECT = 0.60                # any episode below this -> REJECT
TW_HOLDOUT_BAR = 0.85           # full holdout window

# ---- bootstrap (SS19) ----------------------------------------------------
BLOCK = 21
N_BOOT = 2000
BOOT_SEED = 20260811

HOLDOUT_START = pd.Timestamp("2025-11-07")
HOLDOUT_END = pd.Timestamp("2026-08-10")
WAR_START = pd.Timestamp("2026-06-04")
WAR_END = pd.Timestamp("2026-07-29")

#: CONVICTION-REPLAY-1 primary picks; book = picks minus synthetic names.
PICKS = ["ALMS", "AMPX", "AMZN", "APLT", "DKNG", "FSLR", "MRVL", "MSTR",
         "NTLA", "RGTI", "SLDP", "TTWO", "TVTX"]
SYNTHETIC = {"APLT", "SLNO"}    # reconstructed series: excluded from daily stats

#: Episode search windows (calendar brackets only; peak/trough derived from
#: the PROXY path inside each bracket, never hand-set).
EPISODE_BRACKETS = {
    "1973-74": ("1972-01-01", "1975-12-31"),
    "1987": ("1987-01-01", "1988-12-31"),
    "2000-02": ("1999-01-01", "2003-12-31"),
    "2007-09": ("2007-01-01", "2009-12-31"),
    "2020": ("2019-06-01", "2020-12-31"),
    "2022": ("2021-06-01", "2023-12-31"),
}


# ==========================================================================
# the rule (prereg SS1) — pure function of history
# ==========================================================================
def ladder_signal(r_book: pd.Series, r_bench: pd.Series | None,
                  sigma_star: float, d_star: float) -> pd.DataFrame:
    """Decided weight at each date t from data <= t. Applied at t+1 by caller.

    ExposurePolicy invariant inherited: re-entry strictly inside exit.
    """
    if not (d_star - DD_HYSTERESIS > 0):
        raise ValueError("re-entry threshold must sit strictly inside the "
                         "exit threshold (hysteresis band collapsed)")
    if MIN_DWELL < 1:
        raise ValueError("a reduction with no minimum dwell has no re-entry")

    vol = r_book.rolling(VOL_WINDOW).std(ddof=1) * np.sqrt(ANNUALIZER)
    w_vol = (sigma_star / vol).clip(upper=LEV_CAP)
    w_vol = w_vol.where(vol.notna(), LEV_CAP)          # warmup: full risk

    if r_bench is not None:
        beta = (r_book.rolling(VOL_WINDOW).cov(r_bench)
                / r_bench.rolling(VOL_WINDOW).var(ddof=1))
        w_beta = pd.Series(
            np.where(beta > 0, np.minimum(LEV_CAP, BETA_STAR / beta), LEV_CAP),
            index=r_book.index)
        w_beta = w_beta.where(beta.notna(), LEV_CAP)   # warmup: full risk
    else:
        beta = pd.Series(np.nan, index=r_book.index)
        w_beta = pd.Series(LEV_CAP, index=r_book.index)

    cum = (1 + r_book).cumprod()
    dd = cum / cum.cummax() - 1.0

    ddv = dd.to_numpy(float)
    cap = np.ones(len(ddv))
    capped, dwell = False, 0
    for i, x in enumerate(ddv):
        if capped:
            dwell += 1
            if dwell >= MIN_DWELL and x > -(d_star - DD_HYSTERESIS):
                capped = False
        elif x < -d_star:
            capped, dwell = True, 0
        cap[i] = 0.5 if capped else 1.0
    w_dd = pd.Series(cap, index=r_book.index)

    w = pd.concat([w_vol, w_beta, w_dd], axis=1).min(axis=1)
    # binding term (priority dd > vol > beta on exact ties), for rung receipts
    binding = np.where(w >= LEV_CAP - 1e-12, "full",
              np.where(w_dd <= w + 1e-12, "dd_cap",
              np.where(w_vol <= w + 1e-12, "vol", "beta")))
    return pd.DataFrame({"w": w, "w_vol": w_vol, "w_beta": w_beta,
                         "w_dd": w_dd, "dd": dd, "beta": beta,
                         "binding": binding,
                         "warmup": vol.isna().to_numpy()},
                        index=r_book.index)


def overlay(r_book: pd.Series, w_signal: pd.Series, bps: float,
            w0: float = 1.0) -> pd.DataFrame:
    """Yesterday's decided weight applied to today's return. Cash earns 0."""
    w_app = w_signal.shift(LAG)
    w_app.iloc[0] = w0
    traded = w_app.diff().abs()
    traded.iloc[0] = abs(w_app.iloc[0] - 1.0)   # from fully invested
    net = w_app * r_book - traded * bps / 1e4
    return pd.DataFrame({"net": net, "w_app": w_app, "traded": traded})


# ==========================================================================
# causality proof (COND-VT's perturbation proof, reproduced)
# ==========================================================================
def assert_causal(r_book: pd.Series, r_bench: pd.Series | None,
                  sigma_star: float, d_star: float,
                  probe: pd.Timestamp, tag: str) -> dict:
    """Perturb every return STRICTLY AFTER `probe`; the weight decided at
    `probe` must be bit-identical. Aborts the run on failure."""
    idx = r_book.index
    t = idx[idx <= probe][-1]
    base = float(ladder_signal(r_book, r_bench, sigma_star, d_star)["w"].loc[t])

    rng = np.random.default_rng(1)
    pert = r_book.copy()
    after = pert.index > t
    pert.loc[after] = ((1 + pert.loc[after].to_numpy(float))
                       * rng.uniform(0.3, 3.0, int(after.sum())) - 1)
    pb = None
    if r_bench is not None:
        pb = r_bench.copy()
        pb.loc[after] = ((1 + pb.loc[after].to_numpy(float))
                         * rng.uniform(0.3, 3.0, int(after.sum())) - 1)
    shocked = float(ladder_signal(pert, pb, sigma_star, d_star)["w"].loc[t])

    if base != shocked:
        raise SystemExit(f"CAUSALITY VIOLATION [{tag}] at {t.date()}: "
                         f"{base!r} -> {shocked!r} after perturbing t+1..T")
    return {"bed": tag, "probe_date": str(t.date()), "weight": base,
            "weight_after_post_t_shock": shocked, "identical": True}


# ==========================================================================
# bootstrap machinery (SS18/SS19): 21td circular blocks, paired indices
# ==========================================================================
_IDX_CACHE: dict[int, np.ndarray] = {}


def boot_idx(n: int) -> np.ndarray:
    if n not in _IDX_CACHE:
        rng = np.random.default_rng(BOOT_SEED + n)
        n_blocks = int(np.ceil(n / BLOCK))
        starts = rng.integers(0, n, (N_BOOT, n_blocks))
        offs = np.arange(BLOCK)
        idx = (starts[:, :, None] + offs[None, None, :]).reshape(N_BOOT, -1) % n
        _IDX_CACHE[n] = idx[:, :n]
    return _IDX_CACHE[n]


def _maxdd_mat(R: np.ndarray) -> np.ndarray:
    W = np.cumprod(1.0 + R, axis=1)
    M = np.maximum.accumulate(W, axis=1)
    return (W / M - 1.0).min(axis=1)


def _maxdd(r: np.ndarray) -> float:
    w = np.cumprod(1.0 + r)
    return float((w / np.maximum.accumulate(w) - 1.0).min())


def paired_receipt(r_m: np.ndarray, r_u: np.ndarray) -> dict:
    """Point + 90% CI + SE for dd-avoided (pp) and terminal wealth ratio,
    paired on the same block indices (SS18)."""
    n = len(r_m)
    idx = boot_idx(n)
    RM, RU = r_m[idx], r_u[idx]
    # maxDD is negative; avoided = dd_m - dd_u > 0 when managed is shallower
    dd_av = _maxdd_mat(RM) - _maxdd_mat(RU)
    twr = np.prod(1.0 + RM, axis=1) / np.prod(1.0 + RU, axis=1)

    def ci(a, point):
        return {"point": round(float(point), 4),
                "ci90": [round(float(np.quantile(a, 0.05)), 4),
                         round(float(np.quantile(a, 0.95)), 4)],
                "se": round(float(a.std(ddof=1)), 4)}

    return {
        "dd_avoided_pp": ci(dd_av * 100, (_maxdd(r_m) - _maxdd(r_u)) * 100),
        "tw_ratio": ci(twr, float(np.prod(1 + r_m) / np.prod(1 + r_u))),
    }


def mde_dd_vs_bar(r_u: np.ndarray) -> dict:
    """80%-power MDE for 'dd avoided >= 5pp', planted effects.

    Planted effect = constant exposure shave (1-c) of the unmanaged path
    (cost-free probe, not a strategy); true effect size s(c) read off the
    original path; power(c) = P(resampled dd-avoided >= 5pp)."""
    n = len(r_u)
    idx = boot_idx(n)
    RU = r_u[idx]
    dd_u_star = _maxdd_mat(RU)
    dd_u = _maxdd(r_u)
    grid = []
    for c in np.linspace(0.05, 0.90, 18):
        # planted size on the original path: shaved dd is shallower (less
        # negative), so avoided = dd_shaved - dd_u > 0
        s = _maxdd((1 - c) * r_u) - dd_u
        power = float((_maxdd_mat((1 - c) * RU) - dd_u_star >= DD_BAR_PP).mean())
        grid.append((float(s), power))
    grid.sort()
    mde = None
    for (s0, p0), (s1, p1) in zip(grid, grid[1:]):
        if p0 < 0.8 <= p1:
            mde = s0 + (s1 - s0) * (0.8 - p0) / (p1 - p0) if p1 > p0 else s1
            break
    if mde is None:
        if grid and grid[0][1] >= 0.8:
            mde = grid[0][0]                       # already powered at smallest
            note = f"<= {mde*100:.1f}pp (smallest planted size already at 80%)"
        else:
            note = "NOT MEASURABLE at 80% power on this path (no planted size reaches it)"
            return {"mde80_pp": None, "note": note}
    else:
        note = "planted-shave MDE vs the 5pp bar"
    return {"mde80_pp": round(float(mde) * 100, 2), "note": note}


def mde_wealth(r_m: np.ndarray, r_u: np.ndarray) -> dict:
    """80%-power MDE for the paired terminal log-wealth difference.

    Null = demeaned daily log-diff; planted drift delta shifts every
    resampled mean by delta, so power(delta) = P(null_mean > q95 - delta)
    and MDE = q95 - q20 of the null mean distribution."""
    d = np.log1p(r_m) - np.log1p(r_u)
    n = len(d)
    d0 = d - d.mean()
    means = d0[boot_idx(n)].mean(axis=1)
    mde_daily = float(np.quantile(means, 0.95) - np.quantile(means, 0.20))
    total = float(d.sum())
    se_total = float(d[boot_idx(n)].sum(axis=1).std(ddof=1))
    return {
        "logwealth_diff_total": round(total, 4),
        "se": round(se_total, 4),
        "mde80_total_log": round(mde_daily * n, 4),
        "mde80_as_tw_ratio": round(float(np.exp(mde_daily * n)), 4),
        "note": ("smallest true log-wealth gap detectable at 80% power; "
                 "one-sided 5% bootstrap test on the paired daily diff"),
    }


# ==========================================================================
# EXPOSURE-CONTROLLER-V0 control (imported from aegis-finance, read-only)
# ==========================================================================
def load_v0():
    spec = importlib.util.spec_from_file_location(
        "exposure_controller", EXPOSURE_CONTROLLER_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod          # dataclass decorator needs this
    spec.loader.exec_module(mod)
    return mod


# ==========================================================================
# episode machinery
# ==========================================================================
def derive_episodes(cum: pd.Series) -> dict[str, dict]:
    """Peak/trough from the PROXY path's own drawdown inside each bracket."""
    out = {}
    idx = cum.index
    for name, (a, b) in EPISODE_BRACKETS.items():
        sub = cum.loc[a:b]
        dd = sub / sub.cummax() - 1.0
        trough = dd.idxmin()
        peak = sub.loc[:trough].idxmax()
        p_pos = idx.get_loc(peak)
        t_pos = idx.get_loc(trough)
        rec_pos = min(t_pos + RECOVERY_TD, len(idx) - 1)
        burn_pos = max(p_pos - BURN_IN_TD, 0)
        out[name] = {
            "burnin_start": idx[burn_pos], "peak": peak, "trough": trough,
            "recovery_end": idx[rec_pos],
            "proxy_peak_to_trough": round(float(cum.loc[trough]
                                                / cum.loc[peak] - 1), 4),
        }
    return out


def episode_receipt(r_book: pd.Series, sig: pd.DataFrame, ov: pd.DataFrame,
                    lo: pd.Timestamp, hi: pd.Timestamp, bps: float) -> dict:
    """Descriptive n=1 receipt over [lo, hi] (episode or holdout window)."""
    r_u = r_book.loc[lo:hi]
    m = ov.loc[lo:hi]
    r_m = m["net"]
    up = r_u > 0
    dn = r_u < 0
    binding = sig["binding"].shift(LAG).loc[lo:hi]   # rung actually held today
    rungs = {k: int((binding == k).sum())
             for k in ("full", "beta", "vol", "dd_cap")}
    return {
        "n_days": int(len(r_u)),
        "dd_unmanaged": round(_maxdd(r_u.to_numpy(float)), 4),
        "dd_managed": round(_maxdd(r_m.to_numpy(float)), 4),
        "dd_avoided_pp": round((_maxdd(r_m.to_numpy(float))
                                - _maxdd(r_u.to_numpy(float))) * 100, 2),
        "tw_unmanaged": round(float((1 + r_u).prod()), 4),
        "tw_managed": round(float((1 + r_m).prod()), 4),
        "tw_ratio": round(float((1 + r_m).prod() / (1 + r_u).prod()), 4),
        "up_capture_kept": (round(float(r_m[up].mean() / r_u[up].mean()), 3)
                            if up.sum() >= 5 else None),
        "down_capture": (round(float(r_m[dn].mean() / r_u[dn].mean()), 3)
                         if dn.sum() >= 5 else None),
        "turnover_oneway_x_nav": round(float(m["traded"].sum()), 3),
        "turnover_cost_bps_nav": round(float(m["traded"].sum() * bps), 1),
        "mean_exposure": round(float(m["w_app"].mean()), 3),
        "min_exposure": round(float(m["w_app"].min()), 3),
        "days_at_rung": rungs,
        "note": "descriptive receipt, n=1 episode",
    }


def receipt_with_uncertainty(r_book: pd.Series, ov: pd.DataFrame,
                             lo, hi) -> dict:
    r_u = r_book.loc[lo:hi].to_numpy(float)
    r_m = ov["net"].loc[lo:hi].to_numpy(float)
    out = paired_receipt(r_m, r_u)
    out["dd_avoided_pp"]["mde"] = mde_dd_vs_bar(r_u)
    out["wealth"] = mde_wealth(r_m, r_u)
    return out


# ==========================================================================
# main
# ==========================================================================
def main() -> None:
    t0 = time.time()
    if not FF_PATH.exists():
        raise SystemExit(f"REFUSAL: calibration data missing at {FF_PATH} — "
                         f"nothing is substituted")

    ff = pd.read_parquet(FF_PATH)
    ff["date"] = pd.to_datetime(ff["date"])
    ff = ff.set_index("date").sort_index()
    mktrf = ff["mktrf"].astype(float)
    rf = ff["rf"].astype(float)
    r_proxy = PROXY_BETA * mktrf + rf            # frozen proxy book
    r_mkt = mktrf + rf                           # market leg (for beta & V0)
    cum_proxy = (1 + r_proxy).cumprod()

    episodes = derive_episodes(cum_proxy)
    print("=== EXPOSURE-CONTROL-1 ===  prereg:", PREREG)
    print("\nDerived episode boundaries (from the PROXY path, not hand-set):")
    for name, e in episodes.items():
        print(f"  {name:<8} burnin {e['burnin_start'].date()}  "
              f"peak {e['peak'].date()}  trough {e['trough'].date()}  "
              f"recovery_end {e['recovery_end'].date()}  "
              f"proxy peak->trough {e['proxy_peak_to_trough']:+.1%}")

    # ---- causality proof on the proxy (2007-09 episode, probe in the fall)
    e08 = episodes["2007-09"]
    sl = slice(e08["burnin_start"], e08["recovery_end"])
    causal_proxy = assert_causal(r_proxy.loc[sl], r_mkt.loc[sl],
                                 0.20, 0.15, pd.Timestamp("2008-10-15"),
                                 "proxy-2007-09")
    print(f"\ncausality assertion PASS [{causal_proxy['bed']}] at "
          f"{causal_proxy['probe_date']}: w={causal_proxy['weight']:.6f} "
          f"bit-identical after post-t perturbation")

    v0 = load_v0()
    policy = v0.ExposurePolicy()                 # frozen V0 defaults

    # ---- calibration grid ------------------------------------------------
    grid_rows = []
    per_candidate = {}
    for s_star in SIGMA_GRID:
        for d_star in DD_GRID:
            key = f"sigma{s_star:.2f}_dd{int(d_star*100)}"
            eps = {}
            for name, e in episodes.items():
                rb = r_proxy.loc[e["burnin_start"]:e["recovery_end"]]
                rm_ = r_mkt.loc[e["burnin_start"]:e["recovery_end"]]
                sig = ladder_signal(rb, rm_, s_star, d_star)
                ov = overlay(rb, sig["w"], COST_BPS_BASE)
                ovs = overlay(rb, sig["w"], COST_BPS_STRESS)
                rec = episode_receipt(rb, sig, ov, e["peak"],
                                      e["recovery_end"], COST_BPS_BASE)
                recs = episode_receipt(rb, sig, ovs, e["peak"],
                                       e["recovery_end"], COST_BPS_STRESS)
                rec["stress_50bps"] = {k: recs[k] for k in
                                       ("dd_managed", "tw_ratio",
                                        "turnover_cost_bps_nav")}
                eps[name] = rec
            covered = sum(1 for r in eps.values()
                          if r["dd_avoided_pp"] >= DD_BAR_PP * 100)
            tws = [r["tw_ratio"] for r in eps.values()]
            row = {"candidate": key, "sigma_star": s_star, "d_star": d_star,
                   "episodes_covered": covered,
                   "coverage_met": covered >= COVERAGE_MIN,
                   "mean_tw_ratio": round(float(np.mean(tws)), 4),
                   "min_tw_ratio": round(float(np.min(tws)), 4),
                   "mean_turnover_cost_bps":
                       round(float(np.mean([r["turnover_cost_bps_nav"]
                                            for r in eps.values()])), 1)}
            grid_rows.append(row)
            per_candidate[key] = eps

    print(f"\nCalibration grid (base {COST_BPS_BASE:.0f}bps decides; coverage "
          f"= dd avoided >= {DD_BAR_PP*100:.0f}pp in >= {COVERAGE_MIN}/6):")
    hdr = (f"{'candidate':<18}{'covered':>8}{'meanTWR':>9}{'minTWR':>8}"
           f"{'TOcost bps':>11}")
    print(hdr)
    for row in sorted(grid_rows, key=lambda r: (-r["episodes_covered"],
                                                -r["mean_tw_ratio"])):
        print(f"{row['candidate']:<18}{row['episodes_covered']:>7}/6"
              f"{row['mean_tw_ratio']:>9.3f}{row['min_tw_ratio']:>8.3f}"
              f"{row['mean_turnover_cost_bps']:>11.1f}")

    # ---- selection (SS3, frozen) ----------------------------------------
    eligible = [r for r in grid_rows if r["coverage_met"]]
    chosen = None
    verdict = None
    if not eligible:
        verdict = "CALIBRATION_FAILED"
        print("\nNO candidate meets coverage -> CALIBRATION_FAILED; "
              "the holdout is NOT opened.")
    else:
        eligible.sort(key=lambda r: (-r["mean_tw_ratio"],
                                     r["mean_turnover_cost_bps"]))
        chosen = eligible[0]
        if chosen["min_tw_ratio"] < TW_REJECT:
            verdict = "REJECT"
            print(f"\nChosen candidate {chosen['candidate']} has an episode "
                  f"TW ratio {chosen['min_tw_ratio']:.3f} < {TW_REJECT} -> "
                  f"REJECT (the cure costs more than the disease); holdout "
                  f"NOT opened.")
        else:
            print(f"\nCHOSEN (SS3): {chosen['candidate']} — covered "
                  f"{chosen['episodes_covered']}/6, mean TWR "
                  f"{chosen['mean_tw_ratio']:.3f}, min TWR "
                  f"{chosen['min_tw_ratio']:.3f}")

    # ---- controls + uncertainty for the chosen candidate (proxy) ---------
    chosen_detail = {}
    if chosen is not None and verdict is None:
        s_star, d_star = chosen["sigma_star"], chosen["d_star"]
        for name, e in episodes.items():
            rb = r_proxy.loc[e["burnin_start"]:e["recovery_end"]]
            rm_ = r_mkt.loc[e["burnin_start"]:e["recovery_end"]]
            sig = ladder_signal(rb, rm_, s_star, d_star)
            ov = overlay(rb, sig["w"], COST_BPS_BASE)
            lo, hi = e["peak"], e["recovery_end"]

            # V0 corpse control, keyed to the MARKET leg, extra warm history
            p0 = max(ff.index.get_loc(e["burnin_start"]) - V0_EXTRA_WARM_TD, 0)
            bench_px = (1 + r_mkt.loc[ff.index[p0]:e["recovery_end"]]).cumprod()
            cls = v0.classify(bench_px, policy)
            expo = cls["exposure"].reindex(rb.index).ffill().fillna(1.0)
            ov_v0 = overlay(rb, expo, COST_BPS_BASE)
            r_u_ep = rb.loc[lo:hi]
            v0_states = cls["state"].reindex(r_u_ep.index)

            # constant-exposure control at the managed path's own mean
            wbar = float(ov["w_app"].loc[lo:hi].mean())
            r_const = wbar * r_u_ep
            r_const.iloc[0] -= abs(wbar - 1.0) * COST_BPS_BASE / 1e4

            rec = per_candidate[chosen["candidate"]][name]
            unc = receipt_with_uncertainty(rb, ov, lo, hi)
            rm_np = ov["net"].loc[lo:hi].to_numpy(float)
            rc_np = r_const.to_numpy(float)
            # ladder vs constant: the timing content (SS16-adjacent)
            idx_ = boot_idx(len(rm_np))
            # positive = ladder's dd shallower than the static control's
            dd_diff = (_maxdd_mat(rm_np[idx_]) - _maxdd_mat(rc_np[idx_]))
            chosen_detail[name] = {
                "receipt": rec,
                "uncertainty": unc,
                "controls": {
                    "v0_index_keyed": {
                        "dd": round(_maxdd(ov_v0["net"].loc[lo:hi]
                                           .to_numpy(float)), 4),
                        "tw_ratio": round(float((1 + ov_v0["net"].loc[lo:hi])
                                                .prod()
                                                / (1 + r_u_ep).prod()), 4),
                        "pct_days_derisked":
                            round(float((expo.loc[lo:hi] < 0.999).mean()), 3),
                        "min_exposure": round(float(expo.loc[lo:hi].min()), 3),
                        "state_days": v0_states.value_counts().to_dict(),
                    },
                    "constant_at_managed_mean": {
                        "wbar": round(wbar, 3),
                        "dd": round(_maxdd(rc_np), 4),
                        "tw_ratio": round(float((1 + r_const).prod()
                                                / (1 + r_u_ep).prod()), 4),
                        "ladder_dd_minus_const_dd_pp": {
                            "point": round((_maxdd(rm_np) - _maxdd(rc_np))
                                           * 100, 2),
                            "ci90": [round(float(np.quantile(dd_diff, q))
                                           * 100, 2) for q in (0.05, 0.95)],
                            "se": round(float(dd_diff.std(ddof=1)) * 100, 2),
                            "note": ("positive = ladder's dd shallower than "
                                     "its own mean exposure held statically"),
                        },
                        "wealth_vs_ladder": mde_wealth(rm_np, rc_np),
                    },
                },
            }

    # ---- write calibration artifact BEFORE the holdout runs --------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cal_path = OUT_DIR / "exposure_control_1_calibration.json"
    cal_payload = {
        "trial": "EXPOSURE-CONTROL-1", "prereg": PREREG,
        "bed": "proxy r_book = 2.15*mktrf + rf (ff_factors_daily); carries "
               "the right vol and beta but NO idiosyncratic gap risk — "
               "disclosed limitation",
        "frozen_params": {
            "beta_star": BETA_STAR, "dwell_td": MIN_DWELL, "lag_td": LAG,
            "hysteresis_pp": DD_HYSTERESIS * 100, "vol_window": VOL_WINDOW,
            "sigma_grid": list(SIGMA_GRID), "dd_grid_pp":
                [int(d * 100) for d in DD_GRID],
            "cost_bps_base": COST_BPS_BASE, "cost_bps_stress": COST_BPS_STRESS,
            "coverage": f">= {DD_BAR_PP*100:.0f}pp dd reduction in >= "
                        f"{COVERAGE_MIN}/6 episodes",
        },
        "beta_note": "on the proxy realized 63d beta is ~2.15 by construction "
                     "-> w_beta binds trivially at ~0.698 everywhere; it is a "
                     "constant de-lever there, not a signal",
        "causality_assertion": causal_proxy,
        "episode_boundaries": {k: {kk: str(vv.date()) if
                                   isinstance(vv, pd.Timestamp) else vv
                                   for kk, vv in e.items()}
                               for k, e in episodes.items()},
        "grid": grid_rows,
        "per_candidate_episodes": per_candidate,
        "selection": {"criterion": "SS3 frozen: coverage then max mean episode "
                                   "TW ratio, ties -> lowest turnover",
                      "chosen": chosen, "verdict_so_far": verdict},
        "chosen_detail": chosen_detail,
        "mde_note": "SS19: per-episode numbers are descriptive n=1 receipts; "
                    "MDEs measured by planted effects under 21td circular "
                    "block bootstrap, N=2000",
        "runtime_secs": round(time.time() - t0, 1),
    }
    cal_path.write_text(json.dumps(cal_payload, indent=1, default=str),
                        encoding="utf-8")
    print(f"\nwrote {cal_path}  (grid committed BEFORE holdout)")

    if verdict is not None:
        print(f"\nVERDICT: {verdict} — holdout not opened.")
        return

    # =====================================================================
    # HOLDOUT — opened once, after the calibration artifact is on disk
    # =====================================================================
    if not CONVICTION_CSV.exists():
        raise SystemExit(f"REFUSAL: holdout data missing at {CONVICTION_CSV}")
    px = pd.read_csv(CONVICTION_CSV, index_col=0,
                     parse_dates=True).sort_index()
    book_names = [t for t in PICKS if t not in SYNTHETIC]
    missing = [t for t in book_names if t not in px.columns]
    if missing:
        raise SystemExit(f"REFUSAL: book names missing from panel: {missing}")
    r_names = px[book_names].pct_change(fill_method=None)
    r_book = r_names.mean(axis=1).iloc[1:]       # EW, daily rebalanced
    r_spy = px["SPY"].pct_change(fill_method=None).reindex(r_book.index)

    s_star, d_star = chosen["sigma_star"], chosen["d_star"]
    causal_hold = assert_causal(r_book, r_spy, s_star, d_star,
                                pd.Timestamp("2026-06-19"), "holdout-book")
    print(f"causality assertion PASS [{causal_hold['bed']}] at "
          f"{causal_hold['probe_date']}: w={causal_hold['weight']:.6f} "
          f"bit-identical after post-t perturbation")

    sig = ladder_signal(r_book, r_spy, s_star, d_star)
    ov = overlay(r_book, sig["w"], COST_BPS_BASE)
    ovs = overlay(r_book, sig["w"], COST_BPS_STRESS)

    lo, hi = HOLDOUT_START, HOLDOUT_END
    full = episode_receipt(r_book, sig, ov, lo, hi, COST_BPS_BASE)
    full_s = episode_receipt(r_book, sig, ovs, lo, hi, COST_BPS_STRESS)
    war = episode_receipt(r_book, sig, ov, WAR_START, WAR_END, COST_BPS_BASE)
    war_s = episode_receipt(r_book, sig, ovs, WAR_START, WAR_END,
                            COST_BPS_STRESS)
    warmup_days = int(sig["warmup"].loc[lo:hi].sum())

    unc_full = receipt_with_uncertainty(r_book, ov, lo, hi)
    unc_war = receipt_with_uncertainty(r_book, ov, WAR_START, WAR_END)

    # constant-exposure control on the full window
    wbar = float(ov["w_app"].loc[lo:hi].mean())
    r_u_full = r_book.loc[lo:hi]
    r_const = wbar * r_u_full
    r_const.iloc[0] -= abs(wbar - 1.0) * COST_BPS_BASE / 1e4
    const_war = r_const.loc[WAR_START:WAR_END]

    # V0 control on the real book: the parent artifact measured it — SPY
    # held above trend all window, controller never left risk_on.
    v0_art = json.loads(V0_ARTIFACT.read_text(encoding="utf-8"))
    v0_holdout = {
        "source": str(V0_ARTIFACT),
        "mean_exposure": v0_art.get("mean_exposure"),
        "finding": v0_art.get("THE_FINDING"),
        "consequence": "exposure == 1.0 all window -> V0-managed book == "
                       "unmanaged book on the holdout; the index-keyed corpse "
                       "never fires while the book-keyed ladder does",
    }

    # decision (SS4, frozen) — on UNROUNDED values; receipts show 4dp
    war_u = r_book.loc[WAR_START:WAR_END].to_numpy(float)
    war_m = ov["net"].loc[WAR_START:WAR_END].to_numpy(float)
    war_dd_avoided = (_maxdd(war_m) - _maxdd(war_u)) * 100
    tw_full = float(np.prod(1 + ov["net"].loc[lo:hi].to_numpy(float))
                    / np.prod(1 + r_u_full.to_numpy(float)))
    adopt = (war_dd_avoided >= DD_BAR_PP * 100) and (tw_full >= TW_HOLDOUT_BAR)
    verdict = "ADOPT_AS_SHADOW_DEFAULT" if adopt else "UNRESOLVED"

    hold_payload = {
        "trial": "EXPOSURE-CONTROL-1", "prereg": PREREG,
        "opened_after_calibration_committed": True,
        "calibration_artifact": str(cal_path),
        "chosen_candidate": chosen,
        "book": {"names": book_names, "excluded_synthetic": sorted(SYNTHETIC),
                 "construction": "equal-weighted, daily rebalanced, from "
                                 "conviction_prices.csv",
                 "window": [str(lo.date()), str(hi.date())],
                 "war_episode": [str(WAR_START.date()), str(WAR_END.date())]},
        "causality_assertion": causal_hold,
        "warmup_days_full_risk_in_window": warmup_days,
        "full_window": {"base_10bps": full, "stress_50bps":
                        {k: full_s[k] for k in ("dd_managed", "tw_ratio",
                                                "turnover_cost_bps_nav")},
                        "uncertainty": unc_full},
        "war_episode": {"base_10bps": war, "stress_50bps":
                        {k: war_s[k] for k in ("dd_managed", "tw_ratio",
                                               "turnover_cost_bps_nav")},
                        "uncertainty": unc_war,
                        "note": "n=1 descriptive; 39td window under 21td "
                                "blocks -> the bootstrap has ~2 blocks"},
        "controls": {
            "unmanaged": {"dd_full": full["dd_unmanaged"],
                          "dd_war": war["dd_unmanaged"],
                          "tw_full": full["tw_unmanaged"]},
            "constant_at_managed_mean": {
                "wbar": round(wbar, 3),
                "dd_full": round(_maxdd(r_const.to_numpy(float)), 4),
                "dd_war": round(_maxdd(const_war.to_numpy(float)), 4),
                "tw_ratio_full": round(float((1 + r_const).prod()
                                             / (1 + r_u_full).prod()), 4),
                "wealth_vs_ladder": mde_wealth(
                    ov["net"].loc[lo:hi].to_numpy(float),
                    r_const.to_numpy(float)),
            },
            "v0_index_keyed": v0_holdout,
        },
        "decision": {
            "war_dd_avoided_pp_exact": war_dd_avoided,
            "war_bar_pp": DD_BAR_PP * 100,
            "tw_ratio_full_exact": tw_full, "tw_bar": TW_HOLDOUT_BAR,
            "compared_unrounded": True,
            "verdict": verdict,
        },
        "limitations": [
            "calibration proxy has no idiosyncratic gap risk (biotech "
            "binaries) — a book-level overnight gap jumps THROUGH a daily "
            "ladder",
            "holdout is ONE window containing ONE war episode: n=1, "
            "descriptive (SS19)",
            "no alpha claim, no crash-prediction claim: path-risk shaping "
            "priced in forgone terminal wealth",
        ],
        "runtime_secs": round(time.time() - t0, 1),
    }
    hold_path = OUT_DIR / "exposure_control_1_holdout.json"
    hold_path.write_text(json.dumps(hold_payload, indent=1, default=str),
                         encoding="utf-8")

    print(f"\n=== HOLDOUT (real book, ONE evaluation) ===")
    print(f"full window {lo.date()}..{hi.date()}  warmup(full-risk) days in "
          f"window: {warmup_days}")
    print(f"  unmanaged: dd {full['dd_unmanaged']:.2%}  TW "
          f"{full['tw_unmanaged']:.4f}")
    print(f"  managed:   dd {full['dd_managed']:.2%}  TW "
          f"{full['tw_managed']:.4f}  TWR {full['tw_ratio']:.4f}  "
          f"mean w {full['mean_exposure']:.3f}  TO cost "
          f"{full['turnover_cost_bps_nav']:.1f}bps")
    print(f"war episode {WAR_START.date()}..{WAR_END.date()}:")
    print(f"  unmanaged dd {war['dd_unmanaged']:.2%}  managed dd "
          f"{war['dd_managed']:.2%}  avoided {war['dd_avoided_pp']:.2f}pp  "
          f"TWR {war['tw_ratio']:.4f}")
    print(f"\nDECISION (SS4 frozen): war dd avoided "
          f"{war_dd_avoided:.2f}pp vs bar {DD_BAR_PP*100:.0f}pp; full-window "
          f"TWR {tw_full:.4f} vs bar {TW_HOLDOUT_BAR}")
    print(f"VERDICT: {verdict}")
    print(f"\nwrote {hold_path}")


if __name__ == "__main__":
    main()
