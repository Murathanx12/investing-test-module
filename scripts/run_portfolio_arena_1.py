"""PORTFOLIO-ARENA-1 — the runner. Fifteen systems, five matchings, four notionals.

    python -m scripts.run_portfolio_arena_1                 # full universe arena
    python -m scripts.run_portfolio_arena_1 --sub           # the 40-name sub-arena

The sub-arena exists because the LLM-fed systems (P6/P7/P8) can only choose from
the 40 names per date that ABLATION-1's declared panel covers. Running them
against systems that chose from 1,500 would compare opportunity sets, not
systems. So the arena is run TWICE on the identical machinery: once on the full
eligible set for the eleven systems that can see it, and once on the 40-name set
where every system — LLM-fed or not — sees exactly the same names.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from scripts.arena_core import (BENCH_BPS, MDE_Z, SCALE_CLIP, Book, cagr,
                                max_drawdown, partial_rebalance, ruler)
from scripts import arena_systems as S

FACTORY = MODULE_ROOT / "data" / "factory"
PANEL = FACTORY / "arena_panel.parquet"
MARKET = FACTORY / "arena_market.parquet"
LLM_CELLS = FACTORY / "arena_llm_cells.parquet"
WG1 = FACTORY / "wg1_panel.npz"
AUX = FACTORY / "exit_lab_1_aux.npz"

PROFILES = {"conservative": dict(K=40, wmax=0.05),
            "base": dict(K=20, wmax=0.10),
            "concentrated": dict(K=10, wmax=0.20)}
PRIMARY_PROFILE = "base"
NOTIONALS = [10_000, 40_000, 100_000, 1_000_000]
MATCHINGS = ["raw", "beta", "vol", "turnover"]


# ── the shared spine ────────────────────────────────────────────────────────

def load(sub: bool):
    panel = pd.read_parquet(PANEL)
    mkt = pd.read_parquet(MARKET)
    if sub:
        cells = pd.read_parquet(LLM_CELLS)[["date_ix", "permno"]]
        panel = panel.merge(cells, on=["date_ix", "permno"], how="inner")
        keep = sorted(panel["date_ix"].unique())
        mkt = mkt[mkt["date_ix"].isin(keep)].reset_index(drop=True)
    panel["log_mcap"] = np.log(panel["mcap"].clip(lower=1.0))
    panel["log_adv"] = np.log(panel["adv"].clip(lower=1.0))
    by_date = {int(k): g.set_index("permno") for k, g in panel.groupby("date_ix")}
    mkt = mkt.set_index("date_ix")
    return panel, mkt, by_date


def load_lc():
    """Cumulative log wealth per name — for EX-ANTE portfolio vol and beta."""
    z = np.load(WG1, allow_pickle=False)
    dates = pd.DatetimeIndex(z["dates"].astype("datetime64[ns]"))
    from scripts.exit_lab_core import build_position_factors, cum_series
    ff = pd.read_parquet(MODULE_ROOT / "data" / "wrds_raw" /
                         "ff_factors_daily.parquet",
                         columns=["date", "mktrf", "rf"])
    ff["date"] = pd.to_datetime(ff["date"])
    ff = ff.set_index("date").reindex(dates)
    rf = pd.to_numeric(ff["rf"], errors="coerce").fillna(0.0).to_numpy()
    mk = (pd.to_numeric(ff["mktrf"], errors="coerce").fillna(0.0).to_numpy()
          + rf)
    LC, _, _ = build_position_factors(z["RET"], z["first_obs"], z["last_obs"],
                                      z["delist_day"], rf)
    aux = np.load(AUX, allow_pickle=False)
    # cum_series, NOT log1p. `exante` differences this to recover daily log
    # returns; handed the daily series it differenced them AGAIN and produced
    # an ex-ante beta of ~0.56 for a RANDOM 20-name equal-weight portfolio
    # whose realised monthly beta is 1.20. The symptom that exposed it was
    # beta-matching levering long-only equity books to 1.4-2.0x gross.
    return LC, aux["dec_ix"].astype(int), cum_series(mk)


def exante(LC, dec_ix, mkt_log, k: int, cols: np.ndarray,
           w: np.ndarray) -> tuple[float, float]:
    """Trailing-252-day portfolio volatility and beta, computed at the decision
    date from data ENDING at it. Nothing after T0 enters."""
    t = int(dec_ix[k])
    win = LC[t - 252:t + 1, cols].astype(np.float64)
    r = np.diff(win, axis=0)
    r = np.nan_to_num(r, nan=0.0)
    p = r @ w
    m = np.diff(mkt_log[t - 252:t + 1])
    vol = float(p.std(ddof=1) * np.sqrt(252.0))
    mv = float(m.var(ddof=1))
    beta = float(np.cov(p, m, ddof=1)[0, 1] / mv) if mv > 0 else np.nan
    return vol, beta


def pick(score: pd.Series, K: int, wmax: float) -> pd.Series:
    s = score.dropna()
    if len(s) == 0:
        return pd.Series(dtype="float64")
    top = s.sort_values(ascending=False).head(K)
    w = pd.Series(1.0 / len(top), index=top.index)
    return w.clip(upper=wmax) / w.clip(upper=wmax).sum()


# ── one system, one matching, one profile ───────────────────────────────────

def run_system(name: str, weights_fn, by_date, mkt, dates_k, LC, dec_ix,
               mkt_log, *, matching: str = "raw", turnover_budget: float = 1.0,
               notional: float = 0.0, whole_shares: bool = False,
               impact: bool = False, sys_scale=None,
               cost_mult: float = 1.0) -> pd.DataFrame:
    bk = Book(notional=notional, whole_shares=whole_shares, impact=impact,
              cost_mult=cost_mult)
    for k in dates_k:
        d = by_date[k]
        w = weights_fn(k, d)
        if w is None or len(w) == 0:
            continue
        cols = d.loc[w.index, "col"].to_numpy().astype(int)
        scale = 1.0
        if sys_scale is not None:
            scale = sys_scale(k, d, w, cols)
        if matching in ("beta", "vol"):
            vol, beta = exante(LC, dec_ix, mkt_log, k, cols, w.to_numpy())
            if matching == "beta":
                tgt = 1.0 / beta if np.isfinite(beta) and beta > 0 else 1.0
            else:
                mv = float(mkt.loc[k, "mkt_vol_252"])
                tgt = mv / vol if np.isfinite(vol) and vol > 0 else 1.0
            scale = float(np.clip(scale * tgt, *SCALE_CLIP))
        if matching == "turnover":
            w = partial_rebalance(w * scale, bk.w, turnover_budget)
            scale = 1.0
        bk.step(k, w, scale, ret=d["fwd_ret_1m"], hs_bps=d["hs_bps"],
                sig_d=d["vol_252"] / np.sqrt(252.0), adv=d["adv"],
                price=d["price"], r_cash=float(mkt.loc[k, "cash_fwd_1m"]))
    return bk.frame()


def run_index(col: str, mkt, dates_k) -> pd.DataFrame:
    bk = Book()
    for i, k in enumerate(dates_k):
        r = float(mkt.loc[k, col])
        w = pd.Series({-1: 1.0})
        bk.step(k, w, 1.0, ret=pd.Series({-1: r}),
                hs_bps=pd.Series(dtype="float64"),
                sig_d=pd.Series(dtype="float64"), adv=pd.Series(dtype="float64"),
                price=pd.Series({-1: 1.0}),
                r_cash=float(mkt.loc[k, "cash_fwd_1m"]), bench=True)
    return bk.frame()


# ── the learned meta-model, purged expanding walk-forward ───────────────────

def learned_scores(panel: pd.DataFrame, dates_k, n_folds: int = 5,
                   purge: int = 2, extra: list[str] | None = None) -> dict:
    """Out-of-fold predicted forward return. Never in-fold, never full-sample.

    The embargo is 2 decision dates — longer than the 1-month label horizon —
    so a training row's label cannot overlap a test row's features.
    """
    import lightgbm as lgb
    feats = list(S.LEARNED_FEATURES) + list(extra or [])
    feats = [f for f in feats if f in panel.columns]
    ks = np.array(sorted(dates_k))
    bounds = np.array_split(ks, n_folds)
    out: dict[int, pd.Series] = {}
    fold_log = []
    for i, test in enumerate(bounds):
        if i == 0:
            continue                       # nothing to train on yet
        tr_hi = int(test[0]) - purge
        tr = panel[panel["date_ix"] < tr_hi]
        te = panel[panel["date_ix"].isin(test)]
        if len(tr) < 2000 or len(te) == 0:
            continue
        X = tr[feats].to_numpy(dtype="float32")
        y = tr["fwd_ret_1m"].to_numpy(dtype="float32")
        ok = np.isfinite(y)
        m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03,
                              num_leaves=31, min_child_samples=200,
                              subsample=0.8, subsample_freq=1,
                              colsample_bytree=0.8, random_state=20260812,
                              verbose=-1)
        m.fit(X[ok], y[ok])
        p = m.predict(te[feats].to_numpy(dtype="float32"))
        te = te.assign(pred=p)
        for k, g in te.groupby("date_ix"):
            out[int(k)] = g.set_index("permno")["pred"]
        fold_log.append({"fold": i, "train_dates_below": tr_hi,
                         "train_rows": int(ok.sum()),
                         "test_dates": [int(test[0]), int(test[-1])],
                         "test_rows": int(len(te))})
    return {"scores": out, "folds": fold_log, "features": feats}


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    t0 = time.time()
    panel, mkt, by_date = load(a.sub)
    dates_k = sorted(by_date)
    LC, dec_ix, mkt_log = load_lc()
    dec_dates = pd.DatetimeIndex(
        np.load(AUX, allow_pickle=False)["dec_dates"].astype("datetime64[ns]"))
    years = np.array([dec_dates[k].year for k in dates_k])
    print(f"arena {'SUB' if a.sub else 'FULL'}: {len(dates_k)} dates, "
          f"{len(panel):,} rows, loaded in {time.time()-t0:.0f}s", flush=True)

    lrn = learned_scores(panel, dates_k)
    print(f"learned: {len(lrn['scores'])} out-of-fold dates, "
          f"{len(lrn['folds'])} folds", flush=True)

    prof = PROFILES[PRIMARY_PROFILE]
    K, wmax = prof["K"], prof["wmax"]

    def wf(scorer):
        return lambda k, d: pick(scorer(d), K, wmax)

    def wf_random(k, d):
        return pick(S.random_score(d, k), K, wmax)

    def wf_learned(k, d):
        s = lrn["scores"].get(k)
        if s is None:
            return None
        return pick(s.reindex(d.index), K, wmax)

    def scale_to_market_vol(k, d, w, cols):
        vol, _ = exante(LC, dec_ix, mkt_log, k, cols, w.to_numpy())
        mv = float(mkt.loc[k, "mkt_vol_252"])
        return float(np.clip(mv / vol, *SCALE_CLIP)) if vol > 0 else 1.0

    def scale_to_p5_vol(k, d, w, cols):
        w5 = pick(S.aegis_deterministic(d), K, wmax)
        c5 = d.loc[w5.index, "col"].to_numpy().astype(int)
        v5, _ = exante(LC, dec_ix, mkt_log, k, c5, w5.to_numpy())
        vol, _ = exante(LC, dec_ix, mkt_log, k, cols, w.to_numpy())
        return float(np.clip(v5 / vol, *SCALE_CLIP)) if vol > 0 else 1.0

    systems: dict[str, dict] = {
        "P2_equal_weight_all": dict(fn=lambda k, d: pd.Series(
            1.0 / len(d), index=d.index)),
        "P3_random": dict(fn=wf_random),
        "P4_volmatched_random": dict(fn=wf_random, scale=scale_to_p5_vol),
        "P5_aegis_deterministic": dict(fn=wf(S.aegis_deterministic)),
        "P9_learned_meta": dict(fn=wf_learned),
        "P11_momentum_event": dict(fn=wf(S.momentum_event)),
        "P12_revision": dict(fn=wf(S.revision)),
        "P13_positive_skew": dict(fn=wf(S.positive_skew)),
        "P14_risk_targeted_positive_skew": dict(fn=wf(S.positive_skew),
                                                scale=scale_to_market_vol),
    }
    if a.sub:
        llm = _llm_systems(K, wmax)
        systems.update(llm)

    # turnover budget: the median realised one-way turnover across the
    # SELECTION systems, computed on the RAW pass and then applied to all.
    results: dict[str, dict] = {}
    raw_frames: dict[str, pd.DataFrame] = {}
    for name, spec in systems.items():
        raw_frames[name] = run_system(name, spec["fn"], by_date, mkt, dates_k,
                                      LC, dec_ix, mkt_log, matching="raw",
                                      sys_scale=spec.get("scale"))
        print(f"  raw {name}: {len(raw_frames[name])} months "
              f"({time.time()-t0:.0f}s)", flush=True)
    sel = [n for n in raw_frames if n not in ("P2_equal_weight_all",)]
    tbudget = float(np.median([raw_frames[n]["turnover_1way"].median()
                               for n in sel]))
    print(f"turnover budget (median across selection systems): "
          f"{tbudget:.4f} one-way/month", flush=True)

    idx = {"P0_SPY": run_index("spy_fwd_1m", mkt, dates_k),
           "P1_QQQ": run_index("qqq_fwd_1m", mkt, dates_k)}

    r_mkt = mkt.loc[dates_k, "mkt_fwd_1m"].to_numpy()
    r_cash = mkt.loc[dates_k, "cash_fwd_1m"].to_numpy()

    def summarise(fr: pd.DataFrame, label: str) -> dict:
        net = fr["net"].to_numpy()
        kk = fr["date_ix"].to_numpy()
        mm = mkt.loc[kk, "mkt_fwd_1m"].to_numpy()
        yy = np.array([dec_dates[int(x)].year for x in kk])
        ex = net - mm
        r = ruler(ex, yy)
        out = {
            "label": label, "n_months": int(len(net)),
            "cagr_net_pct": round(cagr(net) * 100, 3),
            "cagr_market_pct": round(cagr(mm) * 100, 3),
            "excess_cagr_pct": round((cagr(net) - cagr(mm)) * 100, 3),
            "vol_ann_pct": round(float(np.std(net, ddof=1)
                                       * np.sqrt(12) * 100), 2),
            "max_drawdown_pct": round(max_drawdown(net) * 100, 2),
            "turnover_1way_mean": round(float(fr["turnover_1way"].mean()), 4),
            "cost_bps_per_month": round(float(fr["cost"].mean()) * 1e4, 2),
            "cost_pct_per_year": round(float(fr["cost"].mean()) * 12 * 100, 3),
            "gross_exposure_mean": round(float(fr["gross_exposure"].mean()), 4),
            "eff_n_mean": round(float(fr["eff_n"].mean()), 2),
            "scale_mean": round(float(fr["scale"].mean()), 4),
            "excess_ruler": r,
        }
        return out

    for name, fr in {**raw_frames, **idx}.items():
        results.setdefault(name, {})["raw"] = summarise(fr, "raw")

    for m in ("beta", "vol", "turnover"):
        for name, spec in systems.items():
            fr = run_system(name, spec["fn"], by_date, mkt, dates_k, LC, dec_ix,
                            mkt_log, matching=m, turnover_budget=tbudget,
                            sys_scale=spec.get("scale"))
            results[name][m] = summarise(fr, m)
        print(f"  matched:{m} done ({time.time()-t0:.0f}s)", flush=True)

    # realised beta of every raw system, so "gross/beta matched" is MEASURED
    for name, fr in {**raw_frames, **idx}.items():
        net = fr["net"].to_numpy()
        kk = fr["date_ix"].to_numpy()
        mm = mkt.loc[kk, "mkt_fwd_1m"].to_numpy()
        cc = mkt.loc[kk, "cash_fwd_1m"].to_numpy()
        X = np.column_stack([np.ones(len(mm)), mm - cc])
        b, *_ = np.linalg.lstsq(X, net - cc, rcond=None)
        resid = (net - cc) - X @ b
        se_a = float(np.sqrt((resid @ resid) / max(len(mm) - 2, 1)
                             * np.linalg.inv(X.T @ X)[0, 0]))
        results[name]["capm"] = {
            "alpha_ann_pct": round(float(b[0]) * 12 * 100, 3),
            "alpha_mde_ann_pct": round(MDE_Z * se_a * 12 * 100, 3),
            "beta_realised": round(float(b[1]), 3),
            "alpha_detectable": bool(abs(b[0]) > MDE_Z * se_a),
        }

    # § pairwise, against the volatility-matched random control (H3)
    pair = {}
    ctrl = raw_frames.get("P4_volmatched_random")
    for name, fr in raw_frames.items():
        if ctrl is None or name == "P4_volmatched_random":
            continue
        j = fr.set_index("date_ix")["net"].reindex(
            ctrl["date_ix"]).to_numpy() - ctrl["net"].to_numpy()
        yy = np.array([dec_dates[int(x)].year for x in ctrl["date_ix"]])
        pair[name] = ruler(j, yy)

    # cost sensitivity: 0x isolates the COST term of the A10 decomposition.
    # At 0x every arm is gross, so "did the ranking earn anything at all"
    # is separated from "did trading it give the earnings back".
    costs = {}
    for cm in (0.0, 1.0, 2.0):
        costs[f"{cm:g}x"] = {}
        for name, spec in systems.items():
            fr = run_system(name, spec["fn"], by_date, mkt, dates_k, LC,
                            dec_ix, mkt_log, matching="raw",
                            sys_scale=spec.get("scale"), cost_mult=cm)
            costs[f"{cm:g}x"][name] = summarise(fr, f"cost_{cm:g}x")
            if cm == 0.0:
                raw_frames[name + "__gross"] = fr
        print(f"  cost {cm:g}x done ({time.time()-t0:.0f}s)", flush=True)

    # H3 at ZERO cost: does the RANKING beat an equally-concentrated random
    # draw before either pays to trade? This is the clean selection test.
    pair_gross = {}
    cg = raw_frames.get("P4_volmatched_random__gross")
    r3 = raw_frames.get("P3_random__gross")
    for name in list(systems):
        for ctrl_name, ctrl_fr in (("volmatched_random", cg),
                                   ("plain_random", r3)):
            g = raw_frames.get(name + "__gross")
            if g is None or ctrl_fr is None or name.startswith("P3")                     or name.startswith("P4"):
                continue
            j = (g.set_index("date_ix")["net"].reindex(ctrl_fr["date_ix"])
                 .to_numpy() - ctrl_fr["net"].to_numpy())
            yy = np.array([dec_dates[int(x)].year for x in ctrl_fr["date_ix"]])
            pair_gross[f"{name}_vs_{ctrl_name}"] = ruler(j, yy)

    # notional sweep, base profile, raw
    sweep = {}
    for nz in NOTIONALS:
        sweep[str(nz)] = {}
        for name, spec in systems.items():
            fr = run_system(name, spec["fn"], by_date, mkt, dates_k, LC,
                            dec_ix, mkt_log, matching="raw", notional=nz,
                            whole_shares=(nz <= 40_000), impact=True,
                            sys_scale=spec.get("scale"))
            sweep[str(nz)][name] = summarise(fr, f"notional_{nz}")
        print(f"  notional {nz} done ({time.time()-t0:.0f}s)", flush=True)

    # sensitivity: the other two risk profiles, RAW only, never decisive
    prof_out = {}
    for pname, p in PROFILES.items():
        if pname == PRIMARY_PROFILE:
            continue
        K2, wm2 = p["K"], p["wmax"]
        prof_out[pname] = {}
        for name, scorer in (("P5_aegis_deterministic", S.aegis_deterministic),
                             ("P11_momentum_event", S.momentum_event),
                             ("P12_revision", S.revision),
                             ("P13_positive_skew", S.positive_skew)):
            fr = run_system(name, lambda k, d, sc=scorer: pick(sc(d), K2, wm2),
                            by_date, mkt, dates_k, LC, dec_ix, mkt_log)
            prof_out[pname][name] = summarise(fr, pname)
        fr = run_system("P3_random",
                        lambda k, d: pick(S.random_score(d, k), K2, wm2),
                        by_date, mkt, dates_k, LC, dec_ix, mkt_log)
        prof_out[pname]["P3_random"] = summarise(fr, pname)

    out = {
        "arena": "sub_40names" if a.sub else "full_universe",
        "profile_primary": PRIMARY_PROFILE, "K": K, "wmax": wmax,
        "n_dates": len(dates_k),
        "first_date": str(dec_dates[dates_k[0]].date()),
        "last_date": str(dec_dates[dates_k[-1]].date()),
        "turnover_budget_1way": round(tbudget, 4),
        "aegis_available_weight_share": round(S.AVAILABLE_WEIGHT_SHARE, 4),
        "aegis_unavailable_branches": list(S.UNAVAILABLE_PIT),
        "learned_folds": lrn["folds"], "learned_features": lrn["features"],
        "systems": results,
        "vs_volmatched_random": pair,
        "cost_sensitivity": costs,
        "vs_random_gross": pair_gross,
        "notional_sweep": sweep,
        "profile_sensitivity": prof_out,
        "declared_non_run": {
            "P10_evolutionary_survivor":
                "chunk 8 has not run; there is no survivor. Fabricating one "
                "would be inventing a competitor."},
        "wall_seconds": round(time.time() - t0, 1),
    }
    p = Path(a.out) if a.out else (
        FACTORY / f"portfolio_arena_1_{'sub' if a.sub else 'full'}.json")
    p.write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {p}  ({time.time()-t0:.0f}s)")
    return 0


def _llm_systems(K: int, wmax: float) -> dict:
    """P6/P7/P8 — only definable where the LLM panel exists. Filled by the
    ablation runner, which owns the scores; here they are declared absent so a
    sub-arena run before the LLM panel lands cannot silently omit them."""
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
