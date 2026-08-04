"""Fidelity gate F1-F8 (design §2.4) — real vs synthetic, each raises rather
than returning a sentinel (house rule S4: no silently skipped metric).

F8 is the single most important assertion in the build: mean rank-IC of every
batch-1 signal on alpha=0 panels must be statistically zero, or the DGP leaks
real alpha and every downstream number is meaningless.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, spearmanr

from aegis_brain.calibration.panel_gen import DGPAInputs, gen_null_panel
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.batch1_price import BATCH1
from aegis_brain.factory.explore import ScanConfig

# Tolerances, frozen from the design table (§2.4).
TOL_F1_REL = 0.20
TOL_F2_REL = 0.15
TOL_F3_KURT_REL = 0.30
TOL_F4_KS = 0.10
TOL_F6_REL = 0.05
# Stage-1 kill escalation: F1/F2 miss by >30% -> DGP-A rejected outright.
KILL_F12_REL = 0.30

N_CORR_SAMPLE = 400       # firms sampled for the pairwise-correlation metric
MIN_COMMON_MONTHS = 100


def _rel_err(a: float, b: float) -> float:
    return abs(a - b) / abs(b) if b != 0 else np.inf


def _sample_corr_firms(ret: pd.DataFrame, rng: np.random.Generator) -> pd.Index:
    counts = ret.notna().sum()
    ok = counts[counts >= MIN_COMMON_MONTHS].index
    if len(ok) < 50:
        raise ValueError(f"only {len(ok)} firms with >= {MIN_COMMON_MONTHS} months")
    take = min(N_CORR_SAMPLE, len(ok))
    return pd.Index(rng.choice(ok, size=take, replace=False))


def f1_pairwise_corr(real: Panel, synth: Panel, rng: np.random.Generator) -> dict:
    firms = _sample_corr_firms(real.monthly_ret, rng)
    out = {}
    dv_mean = real.monthly_dollar_vol[firms].mean()
    terciles = pd.qcut(dv_mean.rank(method="first"), 3, labels=["small", "mid", "large"])
    for label, cols in [("overall", firms)] + [
        (str(lb), firms[terciles == lb]) for lb in ["small", "mid", "large"]
    ]:
        vals = {}
        for name, pnl in (("real", real), ("synth", synth)):
            c = pnl.monthly_ret[cols].corr(min_periods=60)
            iu = np.triu_indices(len(cols), k=1)
            vals[name] = float(np.nanmean(c.to_numpy()[iu]))
        out[label] = {**vals, "rel_err": _rel_err(vals["synth"], vals["real"])}
    worst = max(v["rel_err"] for v in out.values())
    return {"metric": "F1 mean pairwise corr", "detail": out, "worst_rel_err": worst,
            "pass": worst <= TOL_F1_REL, "kill": worst > KILL_F12_REL}


def f2_dispersion(real: Panel, synth: Panel) -> dict:
    out = {}
    for name, pnl in (("real", real), ("synth", synth)):
        disp = pnl.monthly_ret.std(axis=1, ddof=1).dropna()
        out[name] = {"median": float(disp.median()),
                     "p95": float(disp.quantile(0.95))}
    errs = {k: _rel_err(out["synth"][k], out["real"][k]) for k in ("median", "p95")}
    worst = max(errs.values())
    return {"metric": "F2 within-month dispersion", "detail": {**out, "rel_err": errs},
            "worst_rel_err": worst, "pass": worst <= TOL_F2_REL,
            "kill": worst > KILL_F12_REL}


def f3_tails(real: Panel, synth: Panel) -> dict:
    out = {}
    for name, pnl in (("real", real), ("synth", synth)):
        pooled = pnl.monthly_ret.to_numpy().ravel()
        pooled = pooled[~np.isnan(pooled)]
        s = pd.Series(pooled)
        out[name] = {"kurtosis": float(s.kurtosis()), "skew": float(s.skew())}
    kurt_err = _rel_err(out["synth"]["kurtosis"], out["real"]["kurtosis"])
    skew_same_sign = np.sign(out["synth"]["skew"]) == np.sign(out["real"]["skew"])
    return {"metric": "F3 pooled kurtosis/skew",
            "detail": {**out, "kurt_rel_err": kurt_err,
                       "skew_same_sign": bool(skew_same_sign)},
            "pass": kurt_err <= TOL_F3_KURT_REL and skew_same_sign, "kill": False}


def f4_firm_vol_ks(real: Panel, synth: Panel) -> dict:
    def firm_vols(pnl: Panel) -> np.ndarray:
        v = pnl.monthly_ret.iloc[-60:].std(ddof=1)
        n = pnl.monthly_ret.iloc[-60:].notna().sum()
        return v[n >= 36].dropna().to_numpy()
    rv, sv = firm_vols(real), firm_vols(synth)
    ks = float(ks_2samp(rv, sv).statistic)
    return {"metric": "F4 firm 60m-vol KS", "detail": {"ks": ks, "n_real": len(rv),
            "n_synth": len(sv)}, "pass": ks <= TOL_F4_KS, "kill": False}


def f5_factor_path(inputs: DGPAInputs) -> dict:
    """The factor path is real BY CONSTRUCTION; assert the vintage pin exists
    and the matrix is finite — the strongest exactly-checkable form of
    'market path identical'."""
    ok = bool(np.isfinite(inputs.fac).all() and np.isfinite(inputs.rf).all()
              and inputs.vintage)
    return {"metric": "F5 factor path pinned+finite",
            "detail": {"vintage": inputs.vintage.get("retrieved",
                                                     str(inputs.vintage)[:80])},
            "pass": ok, "kill": not ok}


def f6_eligibility(real: Panel, synth: Panel) -> dict:
    from aegis_brain.factory.explore import segment_mask
    cfg = ScanConfig()
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    out = {}
    for name, pnl in (("real", real), ("synth", synth)):
        elig = pnl.eligible()
        elig = elig.loc[(elig.index >= lo) & (elig.index <= hi)]
        lm = (elig & segment_mask(pnl, "largemid").reindex(elig.index)).sum(axis=1)
        sm = (elig & segment_mask(pnl, "small").reindex(elig.index)).sum(axis=1)
        out[name] = {"eligible": float(elig.sum(axis=1).mean()),
                     "largemid": float(lm.mean()), "small": float(sm.mean())}
    errs = {k: _rel_err(out["synth"][k], out["real"][k])
            for k in ("eligible", "largemid", "small")}
    worst = max(errs.values())
    return {"metric": "F6 eligible names/month", "detail": {**out, "rel_err": errs},
            "worst_rel_err": worst, "pass": worst <= TOL_F6_REL, "kill": False}


def f7_vol_clustering(real: Panel, synth: Panel,
                      rng: np.random.Generator) -> dict:
    """|return| autocorr lags 1-6 — REPORTED, not gating (known DGP-A gap)."""
    firms = _sample_corr_firms(real.monthly_ret, rng)[:200]
    out = {}
    for name, pnl in (("real", real), ("synth", synth)):
        acs = []
        a = pnl.monthly_ret[firms].abs()
        for lag in range(1, 7):
            acs.append(float(a.apply(lambda s: s.autocorr(lag)).mean()))
        out[name] = [round(x, 4) for x in acs]
    return {"metric": "F7 |ret| autocorr 1-6 (report-only)", "detail": out,
            "pass": True, "kill": False}


def f8_null_payoff(inputs: DGPAInputs, n_reps: int, seed_base: int) -> dict:
    """THE null check, v4 metric: the PAYOFF null.

    For every batch-1 signal on alpha=0 panels: mean next-month excess return
    of the equal-weight top-decile book vs the eligible-universe EW — the
    quantity the factory's t_excess_net gate actually trades on.

    Why not rank-IC (the design's original metric): with per-firm sigma
    preserved (a realism REQUIREMENT, R3), high-vol firms have right-skewed
    months — equal means but negative medians — so sigma-correlated signals
    show nonzero mean rank-IC with zero extractable money. Zero-alpha does
    not imply zero-rank-IC under heteroskedastic skew. Rank-IC is reported
    alongside as a diagnostic (and note: the factory's own t_ic gate shares
    this exposure — a pipeline property the grid will measure, not hide).

    Gate (pre-registered before the v4 run): KILL if any signal's
    |mean excess| > 3 x MC-SE; signals in (2, 3] x SE are warned and listed
    (with 20 signals, ~1 false 2-SE trip is expected under a true null).
    """
    cfg = ScanConfig()
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    payoff: dict[str, list[float]] = {s.name: [] for s in BATCH1}
    ics: dict[str, list[float]] = {s.name: [] for s in BATCH1}

    for rep in range(n_reps):
        rng = np.random.default_rng(seed_base + rep)
        pnl = gen_null_panel(inputs, rng)
        elig = pnl.eligible()
        months = pnl.monthly_ret.index
        test = [m for m in months if lo <= m <= hi]
        scores = {}
        for sig in BATCH1:
            scores[sig.name] = sig.compute(pnl) * float(sig.direction)
        for m in test:
            pos = months.get_loc(m)
            if pos == 0:
                continue
            fm = months[pos - 1]
            e = elig.loc[fm]
            realized = pnl.monthly_ret.loc[m]
            for sig in BATCH1:
                s = scores[sig.name].loc[fm].dropna()
                s = s[s.index.isin(e[e].index)]
                fwd = realized.reindex(s.index)
                ok = fwd.notna()
                if ok.sum() < 100:
                    continue
                s2, f2 = s[ok], fwd[ok]
                top = f2.reindex(
                    s2.nlargest(max(int(len(s2) * cfg.top_frac), 10)).index)
                payoff[sig.name].append(float(top.mean() - f2.mean()))
                ics[sig.name].append(float(spearmanr(s2, f2).statistic))

    rows = {}
    any_kill = False
    warned = []
    for name in payoff:
        arr = np.asarray(payoff[name])
        if arr.size == 0:
            raise ValueError(f"F8 produced no payoffs for {name}")
        mean = float(arr.mean())
        se = float(arr.std(ddof=1) / np.sqrt(arr.size))
        ratio = abs(mean) / se if se > 0 else np.inf
        if ratio > 3:
            any_kill = True
        elif ratio > 2:
            warned.append(name)
        ica = np.asarray(ics[name])
        rows[name] = {
            "mean_excess_bps": round(mean * 1e4, 2), "se_bps": round(se * 1e4, 2),
            "abs_t": round(ratio, 2), "n": int(arr.size),
            "diag_mean_ic": round(float(ica.mean()), 5),
            "pass": ratio <= 3,
        }
    return {"metric": "F8 null payoff (THE gate; IC diagnostic alongside)",
            "detail": rows, "warned_2to3se": warned,
            "pass": not any_kill, "kill": any_kill}
