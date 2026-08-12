"""EXPOSURE-ARENA-1 controller G — the LEARNED exposure policy.

Three families, chosen with the KNOWN-WORLDS §5 trust table open on the desk:

  ridge         TRUSTED as a detector, never as an explainer.
  lightgbm      TRUSTED with the stated caveat (its one conditional recovery
                failed the mirror world; anything conditional it reports needs
                independent confirmation).
  evolutionary  CONDITIONALLY TRUSTED — "it invented a timing rule in world L
                that only matched-exposure comparison plus an MDE refused.
                Never report an evolutionary result without both." It is here
                BECAUSE it is the learner that did that, and both disciplines
                are the primary metric of this trial.

DECLARED NON-RUN: conservative offline-Q. KNOWN-WORLDS §5 rates it NOT TRUSTED
for action work — a pessimism penalty has nothing to subtract from cash's
certain zero, so it is structurally biased toward the do-nothing action. In an
exposure trial that bias is the failure mode under test; running it would add a
broken instrument, not a learner.

PROTOCOL (prereg §7.1, frozen). Expanding-window walk-forward. Target = the
forward 21-trading-day book EXCESS log return. Purge + embargo = 42 trading
days, twice the label horizon, between the last training row and the first test
row. Every imputer, scaler, quantile and standardisation is fitted INSIDE the
training fold. Predictions are used out-of-fold only. Exposure mapping is frozen
before the run: w = clip(0.5 + 0.5·z, 0, 1) with z standardised by the TRAINING
fold's own prediction mean and sd.

The labels overlap (21-day horizon, daily rows). That dependence is not removed
and is declared: it inflates any apparent in-sample fit, and it is one of the
reasons the primary metric is an out-of-fold wealth difference against a matched
control rather than an R² or an IC.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.exposure_arena_core import book_features

LABEL_H = 21
EMBARGO = 42                      # twice the label horizon
SEED = 20260812

RIDGE_ALPHA = 1.0
LGB_PARAMS = dict(n_estimators=200, learning_rate=0.05, num_leaves=15,
                  min_child_samples=200, subsample=0.8, subsample_freq=1,
                  colsample_bytree=0.8, reg_lambda=1.0, verbose=-1,
                  random_state=SEED)

EVO_POP = 200
EVO_GENS = 40
EVO_RULES = 3
EVO_ELITE = 0.25


def make_folds(index: pd.DatetimeIndex, first_train_end: str,
               retrain_years: int) -> list[dict]:
    """Expanding train, contiguous non-overlapping test blocks."""
    fte = pd.Timestamp(first_train_end)
    y0 = fte.year + 1
    y_last = index[-1].year
    folds = []
    y = y0
    while y <= y_last:
        t0 = pd.Timestamp(f"{y}-01-01")
        t1 = pd.Timestamp(f"{min(y + retrain_years - 1, y_last)}-12-31")
        test = index[(index >= t0) & (index <= t1)]
        if len(test) < 63:
            break
        first_test_pos = index.get_loc(test[0])
        train_end_pos = first_test_pos - EMBARGO
        if train_end_pos < 504:
            y += retrain_years
            continue
        folds.append({"fold": len(folds),
                      "train_lo": 0, "train_hi": train_end_pos,
                      "test_lo": first_test_pos,
                      "test_hi": index.get_loc(test[-1]) + 1,
                      "test_span": [str(test[0].date()), str(test[-1].date())],
                      "n_train": train_end_pos, "n_test": len(test)})
        y += retrain_years
    return folds


def _xy(bed: dict) -> tuple[pd.DataFrame, np.ndarray]:
    X = book_features(bed)
    ex = (bed["r_book"] - bed["rf"]).to_numpy(float)
    lg = np.log1p(ex)
    c = np.r_[0.0, np.cumsum(lg)]
    n = len(ex)
    y = np.full(n, np.nan)
    y[:n - LABEL_H] = c[LABEL_H:n] - c[:n - LABEL_H]
    return X, y


def _map_weight(pred: np.ndarray, mu: float, sd: float) -> np.ndarray:
    z = (pred - mu) / sd if sd > 0 else np.zeros_like(pred)
    return np.clip(0.5 + 0.5 * z, 0.0, 1.0)


# ── evolutionary policy search ────────────────────────────────────────────
def _evo_weights(Xv: np.ndarray, feat: np.ndarray, thr: np.ndarray,
                 w_lo: np.ndarray, w_hi: np.ndarray) -> np.ndarray:
    """(n_days, pop) weights: each genome is min over EVO_RULES threshold rules."""
    n = Xv.shape[0]
    P = feat.shape[0]
    W = np.ones((n, P), dtype=np.float32)
    for j in range(EVO_RULES):
        cols = Xv[:, feat[:, j]]                       # (n, P)
        cond = cols <= thr[:, j][None, :]
        Wj = np.where(cond, w_hi[:, j][None, :], w_lo[:, j][None, :])
        np.minimum(W, Wj.astype(np.float32), out=W)
    return W


def _evo_fitness(W: np.ndarray, r: np.ndarray, rf: np.ndarray,
                 bps: float) -> np.ndarray:
    wa = np.vstack([np.ones((1, W.shape[1]), np.float32), W[:-1]])
    traded = np.abs(np.diff(np.vstack([np.ones((1, W.shape[1]), np.float32),
                                       wa]), axis=0))
    net = (wa * r[:, None] + (1 - wa) * rf[:, None] - traded * bps)
    return np.log1p(net).sum(axis=0)


def evolve(Xtr: np.ndarray, r: np.ndarray, rf: np.ndarray, bps: float,
           qgrid: np.ndarray, rng) -> dict:
    """Population search on the TRAINING fold only. Thresholds are training-fold
    quantiles, so a genome carries no test-fold scale information."""
    nF = Xtr.shape[1]
    feat = rng.integers(0, nF, (EVO_POP, EVO_RULES))
    qq = rng.random((EVO_POP, EVO_RULES))
    w_lo = rng.random((EVO_POP, EVO_RULES)).astype(np.float32)
    w_hi = rng.random((EVO_POP, EVO_RULES)).astype(np.float32)
    n_elite = max(2, int(EVO_POP * EVO_ELITE))
    best = None
    for _ in range(EVO_GENS):
        thr = qgrid[feat, (qq * (qgrid.shape[1] - 1)).astype(int)]
        W = _evo_weights(Xtr, feat, thr, w_lo, w_hi)
        fit = _evo_fitness(W, r, rf, bps)
        order = np.argsort(-fit)
        if best is None or fit[order[0]] > best["fit"]:
            best = {"fit": float(fit[order[0]]),
                    "feat": feat[order[0]].copy(), "qq": qq[order[0]].copy(),
                    "w_lo": w_lo[order[0]].copy(), "w_hi": w_hi[order[0]].copy()}
        e = order[:n_elite]
        pa = rng.choice(e, EVO_POP)
        pb = rng.choice(e, EVO_POP)
        cx = rng.random((EVO_POP, EVO_RULES)) < 0.5
        feat = np.where(cx, feat[pa], feat[pb])
        qq = np.where(cx, qq[pa], qq[pb])
        w_lo = np.where(cx, w_lo[pa], w_lo[pb])
        w_hi = np.where(cx, w_hi[pa], w_hi[pb])
        mut = rng.random((EVO_POP, EVO_RULES)) < 0.15
        feat = np.where(mut, rng.integers(0, nF, (EVO_POP, EVO_RULES)), feat)
        qq = np.clip(qq + rng.normal(0, 0.12, qq.shape) * mut, 0, 1)
        w_lo = np.clip(w_lo + rng.normal(0, 0.12, w_lo.shape) * mut, 0, 1
                       ).astype(np.float32)
        w_hi = np.clip(w_hi + rng.normal(0, 0.12, w_hi.shape) * mut, 0, 1
                       ).astype(np.float32)
        feat[:n_elite] = best["feat"]
        qq[:n_elite] = best["qq"]
        w_lo[:n_elite] = best["w_lo"]
        w_hi[:n_elite] = best["w_hi"]
    return best


def run_learned(bed: dict, first_train_end: str, retrain_years: int,
                families=("ridge", "lightgbm", "evolutionary"),
                log=print) -> dict:
    """Out-of-fold exposure series per family, plus fold receipts."""
    from sklearn.linear_model import Ridge
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler

    X, y = _xy(bed)
    idx = X.index
    Xv = X.to_numpy(float)
    r = bed["r_book"].to_numpy(float)
    rf = bed["rf"].to_numpy(float)
    bps = bed["cost_bps"] / 1e4
    folds = make_folds(idx, first_train_end, retrain_years)
    if not folds:
        return {"error": "no folds", "folds": []}

    out = {f: np.full(len(idx), np.nan) for f in families}
    receipts = []
    n_fits = 0
    for fd in folds:
        tr = slice(fd["train_lo"], fd["train_hi"])
        te = slice(fd["test_lo"], fd["test_hi"])
        ytr = y[tr]
        ok = np.isfinite(ytr)
        Xtr_raw, Xte_raw = Xv[tr][ok], Xv[te]
        ytr_ok = ytr[ok]
        if len(ytr_ok) < 504:
            continue
        imp = SimpleImputer(strategy="median").fit(Xtr_raw)
        Xtr = imp.transform(Xtr_raw)
        Xte = imp.transform(Xte_raw)
        rec = {**{k: fd[k] for k in ("fold", "test_span", "n_train", "n_test")}}

        if "ridge" in families:
            sc = StandardScaler().fit(Xtr)
            m = Ridge(alpha=RIDGE_ALPHA).fit(sc.transform(Xtr), ytr_ok)
            ptr = m.predict(sc.transform(Xtr))
            p = m.predict(sc.transform(Xte))
            out["ridge"][te] = _map_weight(p, ptr.mean(), ptr.std(ddof=1))
            rec["ridge_train_r2"] = round(float(m.score(sc.transform(Xtr),
                                                        ytr_ok)), 4)
            n_fits += 1
        if "lightgbm" in families:
            import lightgbm as lgb
            m = lgb.LGBMRegressor(**LGB_PARAMS).fit(Xtr, ytr_ok)
            ptr = m.predict(Xtr)
            p = m.predict(Xte)
            out["lightgbm"][te] = _map_weight(p, ptr.mean(), ptr.std(ddof=1))
            n_fits += 1
        if "evolutionary" in families:
            rng = np.random.default_rng(SEED + fd["fold"])
            imp_tr_full = imp.transform(Xv[tr])
            qgrid = np.nanquantile(imp_tr_full, np.linspace(0.02, 0.98, 49),
                                   axis=0).T                # (nF, 49)
            best = evolve(imp_tr_full.astype(np.float32), r[tr], rf[tr], bps,
                          qgrid, rng)
            thr = qgrid[best["feat"],
                        (best["qq"] * (qgrid.shape[1] - 1)).astype(int)]
            W = _evo_weights(Xte.astype(np.float32),
                             best["feat"][None, :], thr[None, :],
                             best["w_lo"][None, :], best["w_hi"][None, :])
            out["evolutionary"][te] = W[:, 0]
            rec["evo_train_logwealth"] = round(best["fit"], 4)
            rec["evo_genome"] = {"features": [X.columns[i] for i
                                              in best["feat"].tolist()],
                                 "thresholds": [round(float(t), 5) for t in thr],
                                 "w_lo": [round(float(v), 3) for v
                                          in best["w_lo"].tolist()],
                                 "w_hi": [round(float(v), 3) for v
                                          in best["w_hi"].tolist()]}
            n_fits += 1
        receipts.append(rec)
        log(f"    fold {fd['fold']} test {fd['test_span'][0]}.."
            f"{fd['test_span'][1]}  train {fd['n_train']}  test {fd['n_test']}")

    series = {}
    for f in families:
        s = pd.Series(out[f], index=idx)
        series[f] = s
    first_oof = idx[folds[0]["test_lo"]]
    return {"series": series, "folds": receipts, "n_model_fits": n_fits,
            "first_oof_date": str(first_oof.date()),
            "feature_names": list(X.columns),
            "protocol": {"label_horizon_td": LABEL_H, "embargo_td": EMBARGO,
                         "first_train_end": first_train_end,
                         "retrain_years": retrain_years,
                         "ridge_alpha": RIDGE_ALPHA, "lgb_params": LGB_PARAMS,
                         "evo": {"pop": EVO_POP, "gens": EVO_GENS,
                                 "rules": EVO_RULES, "elite": EVO_ELITE,
                                 "seed": SEED}},
            "declared_non_run": ("conservative offline-Q — KNOWN-WORLDS §5 "
                                 "rates it NOT TRUSTED for action work "
                                 "(structural bias toward the do-nothing "
                                 "action); it would enter as a broken "
                                 "instrument, not a learner")}
