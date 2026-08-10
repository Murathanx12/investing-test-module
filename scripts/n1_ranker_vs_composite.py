"""N1 — does learning the weights beat writing them?

TRIAL-N1-RANKER-VS-COMPOSITE-1. Every strategy this factory has adopted uses
weights a human wrote. The surviving book is three profitability signals at equal
weight. This is the first test of the alternative on our own book.

Four arms, everything downstream of the score identical:

  R0  the banked hand-written composite                        (control)
  R1  GBM ranker on the SAME three features    -> learning, at fixed information
  R2  GBM ranker on the three + seven natives  -> learning, with more information
  R3  one-hidden-layer MLP on the same shelf   -> model class

Two questions, two instruments, because conflating them is how a factory
concludes "ML doesn't work" from a portfolio-construction null:

  MONEY     paired monthly net excess vs R0. MDE is 2-4%/yr by construction
            (power check in the prereg), so this can only see a LARGE effect.
  ORDERING  monthly rank-IC against the forward 12m return, paired across arms.
            ~700 observations, no construction noise, far higher power.

Walk-forward with a 13-month purge: the label is a forward 12-month return, so a
model fitted at month f may only see labels from months <= f-13. Nothing in this
script is allowed near the holdout.

Reported, never deciding.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.ERROR)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT8"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"

SEED = 20260810
LABEL_MONTHS = 12
PURGE = LABEL_MONTHS + 1          # 13: the label window plus one month embargo
MIN_TRAIN_MONTHS = 120
MAX_TRAIN_ROWS = 300_000
BAR = 0.03                        # the standard's own adoption bar, %/yr
WIDE = ("native:mom_12_1", "native:rev_1m", "native:vol_12m_low",
        "native:max_ret_low", "native:price_level", "native:liq_high",
        "native:mom_36_13_low")

GBM_PARAMS = dict(n_estimators=400, max_depth=3, learning_rate=0.03,
                  min_child_samples=200, subsample=0.7, subsample_freq=1,
                  verbose=-1, random_state=SEED)


def rank_frames(lib, keys, elig) -> dict[str, pd.DataFrame]:
    """Cross-sectional percentile ranks inside the eligible set, per month."""
    lib.preload(list(keys))
    out = {}
    for k in keys:
        out[k] = lib.get(k).where(elig).rank(axis=1, pct=True)
    return out


def stack(feats: dict[str, pd.DataFrame], months, label: pd.DataFrame | None):
    """Long (month, permno) matrix for a set of months."""
    keys = list(feats)
    cols, idx = [], None
    for k in keys:
        f = feats[k].loc[months]
        s = f.stack(future_stack=True)
        idx = s.index if idx is None else idx
        cols.append(s.to_numpy(dtype=np.float32))
    X = np.column_stack(cols)
    y = (label.loc[months].stack(future_stack=True).to_numpy(dtype=np.float32)
         if label is not None else None)
    return X, y, idx


def fit_predict(kind, feats, months, label, fit_months, rng):
    """Expanding-window walk-forward. Returns a month x permno score frame."""
    from lightgbm import LGBMRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.neural_network import MLPRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    any_frame = next(iter(feats.values()))
    pred = pd.DataFrame(np.nan, index=any_frame.index,
                        columns=any_frame.columns, dtype=np.float32)
    mlist = list(months)
    for i, f in enumerate(fit_months):
        # labels must be fully observed AND embargoed: a model fitted at f may
        # only see months whose forward-12m window closed before f
        train_months = [m for m in mlist if m <= f - pd.DateOffset(months=PURGE)]
        if len(train_months) < MIN_TRAIN_MONTHS:
            continue
        X, y, _ = stack(feats, train_months, label)
        ok = np.isfinite(y) & np.isfinite(X).any(axis=1)
        X, y = X[ok], y[ok]
        if len(y) > MAX_TRAIN_ROWS:
            take = rng.choice(len(y), MAX_TRAIN_ROWS, replace=False)
            X, y = X[take], y[take]
        if len(y) < 5000:
            continue

        if kind == "gbm":
            model = LGBMRegressor(**GBM_PARAMS)
            model.fit(X, y)
        else:
            model = make_pipeline(
                SimpleImputer(strategy="median"), StandardScaler(),
                MLPRegressor(hidden_layer_sizes=(16,), activation="relu",
                             early_stopping=True, validation_fraction=0.15,
                             max_iter=60, random_state=SEED))
            model.fit(X, y)

        # predict every month until the next refit; the model stays valid
        # because its training labels closed before f
        nxt = fit_months[i + 1] if i + 1 < len(fit_months) else mlist[-1] + \
            pd.DateOffset(days=1)
        span = [m for m in mlist if f <= m < nxt]
        if not span:
            continue
        Xp, _, idxp = stack(feats, span, None)
        keep = np.isfinite(Xp).any(axis=1)
        p = np.full(len(Xp), np.nan, dtype=np.float32)
        if keep.sum():
            p[keep] = model.predict(Xp[keep])
        s = pd.Series(p, index=idxp).unstack()
        pred.loc[s.index, s.columns] = s.to_numpy(dtype=np.float32)
        print(f"    {kind} fit {f.date()}  train {len(y):,} rows  "
              f"predict {len(span)} months", flush=True)
    return pred


def rank_ic(score: pd.DataFrame, label: pd.DataFrame, elig) -> pd.Series:
    """Monthly cross-sectional Spearman of score against the forward return."""
    out = {}
    for m in score.index:
        if m not in label.index:
            continue
        s = score.loc[m].where(elig.loc[m]).dropna()
        y = label.loc[m].reindex(s.index).dropna()
        s = s.reindex(y.index)
        if len(y) >= 50:
            out[m] = float(s.rank().corr(y.rank()))
    return pd.Series(out).dropna()


def paired(a: pd.Series, b: pd.Series, lags: int = 12) -> dict:
    d = (a - b).dropna()
    if len(d) < 24:
        return {"months": int(len(d)), "insufficient": True}
    return {
        "months": int(len(d)),
        "mean_monthly": round(float(d.mean()), 6),
        "annualized_pct": round(float(d.mean()) * 12, 4),
        "t_newey_west": D.nw_t(pd.Series(d.to_numpy()), lags=lags),
        "mde_annualized": D.mde_annualized(d * 12),
        "correlation": round(float(a.corr(b)), 4),
    }


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()
    narrow = tuple(k for k, _ in d["signals"])

    f = Factory()
    elig = f.eligible(d["segment"])
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())
    ret = f.spine.panel.monthly_ret
    months = ret.index

    # forward 12m log return, demeaned WITHIN month: the model learns ordering,
    # never the market's direction
    logret = np.log1p(ret.clip(lower=-0.99))
    fwd = logret.rolling(LABEL_MONTHS).sum().shift(-LABEL_MONTHS)
    fwd = fwd.where(elig)
    label = fwd.sub(fwd.mean(axis=1), axis=0)

    feats_narrow = rank_frames(f.lib, narrow, elig)
    feats_wide = {**feats_narrow, **rank_frames(f.lib, WIDE, elig)}
    print(f"features: narrow {len(feats_narrow)}, wide {len(feats_wide)}",
          flush=True)

    # refit on the annual clock, aligned to the book's own rebalance months
    lo = pd.Timestamp(d["first_month"])
    usable = [m for m in months if m >= lo]
    fit_months = [m for i, m in enumerate(usable)
                  if i % 12 == 0 and i >= MIN_TRAIN_MONTHS]
    print(f"refits: {len(fit_months)}  {fit_months[0].date()} -> "
          f"{fit_months[-1].date()}", flush=True)

    scores = {"R0_composite": composite_score(f.lib, d["signals"], elig)[0]}
    print("  fitting R1 (gbm, narrow)...", flush=True)
    scores["R1_gbm_narrow"] = fit_predict("gbm", feats_narrow, usable, label,
                                          fit_months, rng)
    print("  fitting R2 (gbm, wide)...", flush=True)
    scores["R2_gbm_wide"] = fit_predict("gbm", feats_wide, usable, label,
                                        fit_months, rng)
    print("  fitting R3 (mlp, wide)...", flush=True)
    scores["R3_mlp_wide"] = fit_predict("mlp", feats_wide, usable, label,
                                        fit_months, rng)

    # the arms must share a window: the learned arms cannot score before their
    # first refit, and comparing R0's extra decade to nothing is not a pair
    first = min(s.notna().any(axis=1).idxmax() for k, s in scores.items()
                if k != "R0_composite")
    spec_window = {"first_month": str(first.date()), "last_month": d["last_month"]}
    print(f"common window {spec_window}", flush=True)

    monthly, diags, ics = {}, {}, {}
    for name, sc in scores.items():
        spec = StrategySpec(**{**d, **spec_window, "rebalance_months": 12,
                               "cost_model": "ko", "name": f"N1__{name}"})
        out = run_book(f.spine.panel, sc.astype(np.float32), elig, spec,
                       f.spine.rf, era)
        monthly[name] = out["monthly"]["net"]
        diags[name] = out["diag"]
        ics[name] = rank_ic(sc.loc[sc.index >= first], label, elig)
        print(f"  {name:16s} months {out['diag']['months']:4d}  "
              f"turnover {out['diag']['turnover_1way_annual']:.3f}  "
              f"mean IC {ics[name].mean():+.4f}", flush=True)

    base, base_ic = monthly["R0_composite"], ics["R0_composite"]
    res = {
        "trial": "TRIAL-N1-RANKER-VS-COMPOSITE-1",
        "question": "does learning the weights beat writing them?",
        "status": "REPORTED-NEVER-DECIDING",
        "prereg": "TRIALS/PREREG_N1_RANKER_VS_COMPOSITE.md",
        "data_grade": "crsp",
        "window": spec_window,
        "protocol": {
            "label": "forward 12m log return, demeaned within month",
            "purge_months": PURGE, "min_train_months": MIN_TRAIN_MONTHS,
            "max_train_rows": MAX_TRAIN_ROWS, "refits": len(fit_months),
            "seed": SEED, "gbm": GBM_PARAMS},
        "bar_pct_yr": BAR,
        "diagnostics": diags,
        "money": {}, "ordering": {},
    }
    for name in scores:
        if name == "R0_composite":
            continue
        res["money"][name] = paired(monthly[name], base)
        res["ordering"][name] = paired(ics[name], base_ic, lags=LABEL_MONTHS)

    # leak check FIRST: a spectacular result is the symptom of a failed purge
    leaks = [k for k, v in res["money"].items()
             if v.get("annualized_pct", 0) > 0.10]
    res["leak_check"] = {
        "arms_over_10pct_yr": leaks,
        "verdict": ("PASS — no arm posts an implausible paired excess"
                    if not leaks else
                    f"VOID {leaks} — treat as a purge failure until proven "
                    "otherwise; the 13-month embargo is the only thing between "
                    "a forward-12m label and its own prediction month")}

    def state(m: dict, o: dict) -> str:
        t, eff = m.get("t_newey_west"), m.get("annualized_pct")
        mde = m.get("mde_annualized")
        ot = o.get("t_newey_west")
        if t is not None and eff is not None:
            if eff >= BAR and t >= 2.0:
                return "CONFIRMED"
            if eff <= -BAR and t <= -2.0:
                return "REJECTED"
        if ot is not None and abs(ot) >= 2.0 and o.get("annualized_pct", 0) > 0:
            return "IMPLEMENTATION_FAILED"
        if mde is not None and mde > BAR:
            return "POWER_FAILED"
        return "UNRESOLVED"

    res["verdicts"] = {k: (state(res["money"][k], res["ordering"][k])
                           if not leaks else "LEAKAGE_FAILED")
                       for k in res["money"]}
    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "N1_RANKER_VS_COMPOSITE.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")

    print("\n" + "=" * 72)
    print(res["leak_check"]["verdict"])
    for k in res["money"]:
        m, o = res["money"][k], res["ordering"][k]
        print(f"{k:16s} {res['verdicts'][k]:22s} money {m.get('annualized_pct')}"
              f" (NW t {m.get('t_newey_west')}, MDE {m.get('mde_annualized')},"
              f" rho {m.get('correlation')})   ordering dIC "
              f"{o.get('mean_monthly')} (t {o.get('t_newey_west')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
