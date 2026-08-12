"""EXIT-LAB-1 — stages 3-5: baselines, the learned action-value policy, and the
five pre-declared conditional questions.

    python -m scripts.exit_lab_learn --stage baselines
    python -m scripts.exit_lab_learn --stage questions
    python -m scripts.exit_lab_learn --stage learn
    python -m scripts.exit_lab_learn --stage all

THE RULER, stated once and used everywhere. The sampling unit is the **decision
date** (n <= 264), never the position: 6,000 states inside one month share a
market factor and counting them as independent observations manufactures
significance out of a common shock. Every comparison is a PAIRED per-date
difference against `HOLD` on exactly the same states, and every one carries

    MDE = 2.80 x max(Newey-West SE, IID SE)      (CANON §19)

Below its own MDE is NOT DETECTABLE and is never reported as a kill.

BASELINES ARE NOT A FORMALITY. `NEVER_SELL` is the reference policy and several
baselines are expected to beat every learner. The trailing stop is present as a
declared CORPSE control (CANON §15: −3.08%/yr under G7), not as a candidate.
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
from scripts.exit_lab_core import A, ACTIONS, FEATURE_COLS, HORIZONS, PRIMARY_H

FACT = MODULE_ROOT / "data" / "factory"
MDE_Z = 2.80
#: 8 pre-declared regime blocks, by calendar year (identical to WINNER-GENOME-1)
REGIME_BLOCKS = [(2002, 2003), (2004, 2006), (2007, 2009), (2010, 2012),
                 (2013, 2015), (2016, 2018), (2019, 2021), (2022, 2024)]
#: walk-forward: 5 expanding-train test blocks, 13 decision dates of embargo
#: (>= the 252-trading-day label horizon) purged between train and test
N_FOLDS = 5
EMBARGO_DATES = 13


# ── loading ───────────────────────────────────────────────────────────────
def load_all(horizons=tuple(HORIZONS)) -> dict:
    t0 = time.time()
    sf = sorted(FACT.glob("exit_lab_1_states_*.parquet"))
    of = sorted(FACT.glob("exit_lab_1_outcomes_*.parquet"))
    if not sf or len(sf) != len(of):
        raise SystemExit("run `--stage factory` first")
    states = pd.concat([pd.read_parquet(f) for f in sf], ignore_index=True)
    nA = len(ACTIONS)
    out = {}
    cols = [f"r{h}" for h in horizons]
    parts = {c: [] for c in cols}
    for f in of:
        d = pd.read_parquet(f, columns=cols)
        for c in cols:
            parts[c].append(d[c].to_numpy(dtype=np.float32))
        del d
    for h, c in zip(horizons, cols):
        out[h] = np.concatenate(parts[c]).reshape(-1, nA)
        parts[c] = None
    assert out[horizons[0]].shape[0] == len(states), "row misalignment"

    dec = np.load(FACT / "exit_lab_1_aux.npz", allow_pickle=False)
    dec_dates = pd.DatetimeIndex(dec["dec_dates"].astype("datetime64[ns]"))
    date_ix = states["date_ix"].to_numpy()
    years = dec_dates.year.to_numpy()[date_ix]
    # cross-sectional momentum rank inside each decision date: PIT (it uses only
    # T0 information) and needed by the replacement-edge baseline
    states["mom_rank"] = (states.groupby("date_ix")["mom_12_1"]
                          .rank(pct=True).astype(np.float32))
    print(f"loaded {len(states):,} states x {nA} actions x {len(horizons)} "
          f"horizons in {time.time()-t0:.0f}s", flush=True)
    return {"states": states, "out": out, "dec_dates": dec_dates,
            "date_ix": date_ix, "years": years, "n_dates": len(dec_dates)}


# ── the ruler ─────────────────────────────────────────────────────────────
def per_date_mean(v: np.ndarray, date_ix: np.ndarray, n_dates: int):
    ok = np.isfinite(v)
    s = np.bincount(date_ix[ok], weights=v[ok].astype(np.float64),
                    minlength=n_dates)
    c = np.bincount(date_ix[ok], minlength=n_dates)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    return m, c


def newey_west_se(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 8:
        return float("nan")
    L = int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    d = x - x.mean()
    s = float(d @ d) / n
    for l in range(1, L + 1):
        g = float(d[l:] @ d[:-l]) / n
        s += 2.0 * (1.0 - l / (L + 1.0)) * g
    s = max(s, 0.0)
    return float(np.sqrt(s / n))


def paired(diff: np.ndarray, years: np.ndarray | None = None) -> dict:
    """Mean paired per-date difference in pp, with its own 80%-power MDE."""
    d = diff[np.isfinite(diff)]
    n = len(d)
    if n < 8:
        return {"n_dates": n, "delta_pp": None, "mde_pp": None, "t": None}
    iid = float(d.std(ddof=1) / np.sqrt(n))
    nw = newey_west_se(d)
    se = max(nw, iid) if np.isfinite(nw) else iid
    mean = float(d.mean())
    res = {"n_dates": n, "delta_pp": round(mean * 100, 4),
           "mde_pp": round(MDE_Z * se * 100, 4),
           "t": round(mean / se, 3) if se > 0 else None,
           "se_nw_pp": round(nw * 100, 4), "se_iid_pp": round(iid * 100, 4),
           "detectable": bool(abs(mean) > MDE_Z * se)}
    if years is not None:
        yy = years[np.isfinite(diff)]
        agree = 0
        blocks = 0
        for lo, hi in REGIME_BLOCKS:
            m = (yy >= lo) & (yy <= hi)
            if m.sum() >= 4:
                blocks += 1
                if np.sign(d[m].mean()) == np.sign(mean):
                    agree += 1
        half = len(d) // 2
        res["regime_blocks_agree"] = f"{agree}/{blocks}"
        res["halves_agree"] = bool(
            np.sign(d[:half].mean()) == np.sign(d[half:].mean()))
    return res


def verdict(r: dict) -> str:
    if r.get("delta_pp") is None:
        return "NO_DATA"
    if not r.get("detectable"):
        return "NOT_DETECTABLE"
    if r["delta_pp"] < 0:
        return "DETECTABLE_NEGATIVE"
    a, b = (r.get("regime_blocks_agree") or "0/0").split("/")
    if int(a) >= 5 and r.get("halves_agree"):
        return "DIRECTION_SUPPORTED"
    return "DETECTABLE_UNSTABLE"


def compare(vals: np.ndarray, ref: np.ndarray, D: dict, label: str,
            mask: np.ndarray | None = None) -> dict:
    di, nd, yrs = D["date_ix"], D["n_dates"], D["years"]
    if mask is not None:
        vals, ref, di, yrs = vals[mask], ref[mask], di[mask], yrs[mask]
    a, ca = per_date_mean(vals, di, nd)
    b, _ = per_date_mean(ref, di, nd)
    diff = a - b
    yv = np.array([np.nan] * nd)
    okd = np.unique(di)
    yv[okd] = D["dec_dates"].year.to_numpy()[okd]
    r = paired(diff, yv)
    r["label"] = label
    r["mean_policy_pp"] = round(float(np.nanmean(a)) * 100, 4)
    r["mean_ref_pp"] = round(float(np.nanmean(b)) * 100, 4)
    r["n_states"] = int(np.isfinite(vals).sum())
    r["verdict"] = verdict(r)
    return r


# ── baseline policies ─────────────────────────────────────────────────────
def policy_actions(S: pd.DataFrame) -> dict[str, np.ndarray]:
    """Each policy is an action index per state. Pure functions of T0 state."""
    n = len(S)
    hold = np.full(n, A["HOLD"], dtype=np.int8)

    def where(cond, act, base=None):
        b = hold.copy() if base is None else base
        b[np.asarray(cond, dtype=bool)] = A[act]
        return b

    dd = S["dd_from_peak"].to_numpy()
    gain = S["gain_since_entry"].to_numpy()
    mom = S["mom_12_1"].to_numpy()
    rev = S["rev_score"].to_numpy()
    tgt = S["tgt_upside"].to_numpy()
    v63 = S["vol_63"].to_numpy()
    v252 = S["vol_252"].to_numpy()
    rank = S["mom_rank"].to_numpy()
    coh = S["cohort_days"].to_numpy()

    P = {
        "NEVER_SELL": hold,
        "ALWAYS_CASH": np.full(n, A["SELL_CASH"], dtype=np.int8),
        "ALWAYS_BENCH": np.full(n, A["SELL_BENCH"], dtype=np.int8),
        "ALWAYS_REDUCE_BETA": np.full(n, A["REDUCE_BETA"], dtype=np.int8),
        "FIXED_HOLD_252": where(coh >= 252, "SELL_CASH"),
        "FIXED_HOLD_63": where(coh >= 63, "SELL_CASH"),
        # CANON §15 corpse, present as a CONTROL, not a candidate
        "TRAILING_STOP_20": where(dd <= -0.20, "SELL_CASH"),
        "TRAILING_STOP_10": where(dd <= -0.10, "SELL_CASH"),
        "STOP_LOSS_ENTRY_20": where(gain <= -0.20, "SELL_CASH"),
        "MOMENTUM_SELL_LOSERS": where(mom < 0, "SELL_CASH"),
        "MOMENTUM_TRIM_LOSERS": where(mom < 0, "TRIM_50"),
        "VOL_SPIKE_TRIM": where(np.isfinite(v63) & np.isfinite(v252)
                                & (v63 > 1.5 * v252), "TRIM_50"),
        "REVISION_SELL_NEG": where(np.isfinite(rev) & (rev < 0), "SELL_CASH"),
        "TARGET_SELL_NEG": where(np.isfinite(tgt) & (tgt < 0), "SELL_CASH"),
        "REPLACE_EDGE_BOTTOM_HALF": where(rank < 0.50, "REPLACE_1W"),
        "REPLACE_EDGE_BOTTOM_DECILE": where(rank < 0.10, "REPLACE_1W"),
        "TAKE_PROFIT_50": where(gain > 0.50, "TRIM_25"),
        "TAKE_PROFIT_100": where(gain > 1.00, "TRIM_50"),
        "ADD_TO_WINNERS": where(mom > 0, "ADD_50"),
        "DD_AND_REVISION": where((dd <= -0.20) & np.isfinite(rev) & (rev < 0),
                                 "SELL_CASH"),
    }
    return P


def policy_value(out: np.ndarray, act: np.ndarray) -> np.ndarray:
    return out[np.arange(out.shape[0]), act]


def run_baselines(D: dict) -> dict:
    S = D["states"]
    P = policy_actions(S)
    res = {"policies": {}, "actions": {}, "n_configs": 0}
    for h in HORIZONS:
        out = D["out"][h]
        ref = out[:, A["HOLD"]]
        # every single action, as its own policy
        for a in ACTIONS:
            r = compare(out[:, A[a]], ref, D, f"ACTION::{a}@{h}")
            res["actions"].setdefault(str(h), {})[a] = r
            res["n_configs"] += 1
        for name, act in P.items():
            r = compare(policy_value(out, act), ref, D, f"{name}@{h}")
            r["trade_share"] = round(float((act != A["HOLD"]).mean()), 4)
            res["policies"].setdefault(str(h), {})[name] = r
            res["n_configs"] += 1
        print(f"  baselines h={h} done", flush=True)
    return res


# ── the five pre-declared questions ───────────────────────────────────────
def run_questions(D: dict) -> dict:
    S = D["states"]
    out = D["out"]
    Q: dict = {}
    gain = S["gain_since_entry"].to_numpy()
    dd = S["dd_from_peak"].to_numpy()
    rev = S["rev_score"].to_numpy()
    age = S["days_since_rdq"].to_numpy()
    sue = S["sue"].to_numpy()
    mom = S["mom_12_1"].to_numpy()
    vol = S["vol_252"].to_numpy()
    n_cfg = 0

    # Q1 — when does holding a large winner beat trimming it?
    q1 = {}
    buckets = [("gain<0", gain < 0), ("0-25%", (gain >= 0) & (gain < 0.25)),
               ("25-50%", (gain >= 0.25) & (gain < 0.50)),
               ("50-100%", (gain >= 0.50) & (gain < 1.0)),
               (">100%", gain >= 1.0)]
    for h in HORIZONS:
        o = out[h]
        for bname, m in buckets:
            for opp in ("TRIM_25", "TRIM_50", "SELL_BENCH", "SELL_CASH"):
                r = compare(o[:, A["HOLD"]], o[:, A[opp]], D,
                            f"Q1 HOLD-{opp} | gain {bname} @{h}", mask=m)
                q1.setdefault(str(h), {}).setdefault(bname, {})[opp] = r
                n_cfg += 1
        # the winner x momentum interaction: is it the gain or the trend?
        for bname, m in [("winner>50% & mom>0", (gain > 0.5) & (mom > 0)),
                         ("winner>50% & mom<=0", (gain > 0.5) & (mom <= 0))]:
            r = compare(o[:, A["HOLD"]], o[:, A["TRIM_25"]], D,
                        f"Q1 HOLD-TRIM_25 | {bname} @{h}", mask=m)
            q1.setdefault(str(h), {}).setdefault(bname, {})["TRIM_25"] = r
            n_cfg += 1
    Q["Q1_large_winners"] = q1

    # Q2 — when does an event close the expectation gap?
    q2 = {}
    ab = [("0-5d", age <= 5), ("6-20d", (age > 5) & (age <= 20)),
          ("21-60d", (age > 20) & (age <= 60)), (">60d", age > 60)]
    for h in HORIZONS:
        o = out[h]
        for bname, m in ab:
            for sname, sm in [("all", np.ones(len(S), bool)),
                              ("sue>0", sue > 0), ("sue<=0", sue <= 0)]:
                mm = m & sm & np.isfinite(age)
                if mm.sum() < 5000:
                    continue
                r = compare(o[:, A["HOLD"]], o[:, A["SELL_CASH"]], D,
                            f"Q2 HOLD-CASH | {bname} {sname} @{h}", mask=mm)
                q2.setdefault(str(h), {}).setdefault(bname, {})[sname] = r
                n_cfg += 1
    Q["Q2_events"] = q2

    # Q3 — drawdown: thesis damage or noise?
    q3 = {}
    db = [("dd 0 to -10%", dd > -0.10), ("-10 to -25%", (dd <= -0.10) & (dd > -0.25)),
          ("-25 to -50%", (dd <= -0.25) & (dd > -0.50)), ("<-50%", dd <= -0.50)]
    for h in HORIZONS:
        o = out[h]
        for bname, m in db:
            for sname, sm in [("all", np.ones(len(S), bool)),
                              ("rev>0", rev > 0), ("rev<0", rev < 0),
                              ("hi vol", vol > 0.5), ("lo vol", vol <= 0.5)]:
                mm = m & sm
                if mm.sum() < 5000:
                    continue
                for opp in ("SELL_CASH", "TRIM_50"):
                    r = compare(o[:, A["HOLD"]], o[:, A[opp]], D,
                                f"Q3 HOLD-{opp} | {bname} {sname} @{h}", mask=mm)
                    q3.setdefault(str(h), {}).setdefault(bname, {})\
                        .setdefault(sname, {})[opp] = r
                    n_cfg += 1
    Q["Q3_drawdown"] = q3

    # Q4 — is replacement superior to cash? (the NIGHT-12 null's denominator)
    q4 = {}
    for h in HORIZONS:
        o = out[h]
        for arm in ("REPLACE_1", "REPLACE_2", "REPLACE_1N", "REPLACE_REV",
                    "REPLACE_1W", "REPLACE_2W", "REPLACE_RND", "REPLACE_RNDW",
                    "SELL_BENCH", "HOLD"):
            r = compare(o[:, A[arm]], o[:, A["SELL_CASH"]], D,
                        f"Q4 {arm}-CASH @{h}")
            q4.setdefault(str(h), {})[f"{arm}_vs_CASH"] = r
            n_cfg += 1
        # the clause that matters: is the RANKER doing anything, or is it just
        # being invested? each basket against its equally-concentrated random
        for arm, ctl in (("REPLACE_1", "REPLACE_RND"), ("REPLACE_2", "REPLACE_RND"),
                         ("REPLACE_REV", "REPLACE_RND"),
                         ("REPLACE_1W", "REPLACE_RNDW"),
                         ("REPLACE_2W", "REPLACE_RNDW")):
            r = compare(o[:, A[arm]], o[:, A[ctl]], D, f"Q4 {arm}-{ctl} @{h}")
            q4.setdefault(str(h), {})[f"{arm}_vs_{ctl}"] = r
            n_cfg += 1
        # and inside the state partitions that matter for an exit decision
        for bname, m in [("held loser (gain<0)", gain < 0),
                         ("held winner (gain>50%)", gain > 0.5),
                         ("deep dd (<-25%)", dd <= -0.25),
                         ("neg revision", rev < 0)]:
            r = compare(o[:, A["REPLACE_1W"]], o[:, A["SELL_CASH"]], D,
                        f"Q4 REPLACE_1W-CASH | {bname} @{h}", mask=m)
            q4.setdefault(str(h), {})[f"REPLACE_1W_vs_CASH|{bname}"] = r
            n_cfg += 1
    Q["Q4_replacement_vs_cash"] = q4

    # Q5 — when is re-entry after de-risking justified?
    # A state that sold to cash at T0 can buy the SAME name back at +20 days.
    # The re-entry sleeve is cash for 20 days, then the name for h-20 days;
    # it pays the round trip. Built here rather than in the factory because it
    # is a two-step policy, not a single disposition.
    q5 = {}
    Q["Q5_reentry"] = q5
    Q["_n_configs"] = n_cfg
    return Q


def run_reentry(D: dict) -> dict:
    """Q5: cash vs buying the same name back 20 trading days after de-risking."""
    S = D["states"]
    o20 = D["out"][20]
    res = {}
    n_cfg = 0
    dd = S["dd_from_peak"].to_numpy()
    rev = S["rev_score"].to_numpy()
    mom = S["mom_12_1"].to_numpy()
    for h in (60, 120, 252):
        oh = D["out"][h]
        # cash all the way: SELL_CASH at T0, held to h
        stay = oh[:, A["SELL_CASH"]]
        # re-enter: the 20-day cash leg, then the name's return from +20 to +h,
        # recovered as (1+r_h)/(1+r_20) on the HOLD leg, minus one more round trip
        with np.errstate(invalid="ignore"):
            leg = (1.0 + oh[:, A["HOLD"]]) / (1.0 + o20[:, A["HOLD"]]) - 1.0
        cost = (S["hs_bps"].to_numpy() + 6.0) / 1e4
        cash20 = o20[:, A["SELL_CASH"]]
        reenter = (1.0 + cash20) * (1.0 + leg - cost) - 1.0
        for bname, m in [("all de-risked states", np.ones(len(S), bool)),
                         ("de-risked in drawdown <-25%", dd <= -0.25),
                         ("de-risked with neg revision", rev < 0),
                         ("de-risked with pos momentum", mom > 0),
                         ("de-risked with neg momentum", mom <= 0)]:
            r = compare(reenter, stay, D, f"Q5 re-enter@+20 - stay cash | "
                                          f"{bname} @{h}", mask=m)
            res.setdefault(str(h), {})[bname] = r
            n_cfg += 1
        # and against never having de-risked at all
        r = compare(reenter, oh[:, A["HOLD"]], D, f"Q5 re-enter@+20 - HOLD @{h}")
        res.setdefault(str(h), {})["vs NEVER de-risked"] = r
        n_cfg += 1
    res["_n_configs"] = n_cfg
    return res


# ── the learned action-value policy ───────────────────────────────────────
def folds(n_dates: int):
    """Expanding-train walk-forward with a purged embargo before each test."""
    first_test = n_dates // (N_FOLDS + 1)
    edges = np.linspace(first_test, n_dates, N_FOLDS + 1).astype(int)
    for i in range(N_FOLDS):
        lo, hi = int(edges[i]), int(edges[i + 1])
        tr_hi = lo - EMBARGO_DATES
        if tr_hi < 20:
            continue
        yield {"train": (0, tr_hi), "test": (lo, hi)}


def _fit_lgb(X, y, seed):
    import lightgbm as lgb
    m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=63,
                          min_child_samples=200, subsample=0.8,
                          subsample_freq=1, colsample_bytree=0.8,
                          reg_lambda=1.0, n_jobs=16, verbose=-1,
                          random_state=seed)
    m.fit(X, y)
    return m


def _fit_mlp(X, y, seed, rng, cap=250_000):
    from sklearn.impute import SimpleImputer
    from sklearn.neural_network import MLPRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    if len(X) > cap:
        s = rng.choice(len(X), cap, replace=False)
        X, y = X[s], y[s]
    p = Pipeline([("imp", SimpleImputer(strategy="median")),
                  ("sc", StandardScaler()),
                  ("nn", MLPRegressor(hidden_layer_sizes=(64, 32),
                                      max_iter=40, early_stopping=True,
                                      n_iter_no_change=4, random_state=seed))])
    p.fit(X, y)
    return p


def run_learn(D: dict, h: int = PRIMARY_H, do_mlp: bool = True) -> dict:
    """Q(s,a) with one model per action, fitted only inside the training fold.

    Checkpointed per fold to `exit_lab_1_pred_fold{i}.npz`: 160 model fits on up
    to 1.3M rows is hours of CPU, and a crash in the last fold must not throw
    away the first four.
    """
    S = D["states"]
    out = D["out"][h]
    X = S[FEATURE_COLS + ["mom_rank"]].to_numpy(dtype=np.float32)
    di = D["date_ix"]
    n_cfg = 0
    rng = np.random.default_rng(20260812)

    pred = {k: np.full(out.shape, np.nan, dtype=np.float32)
            for k in ("lgb", "mlp")}
    tested = np.zeros(len(S), dtype=bool)
    fold_log = []
    for fi, f in enumerate(folds(D["n_dates"])):
        tr = (di >= f["train"][0]) & (di < f["train"][1])
        te = (di >= f["test"][0]) & (di < f["test"][1])
        tested |= te
        ck = FACT / f"exit_lab_1_pred_fold{fi}_h{h}.npz"
        if ck.exists():
            z = np.load(ck, allow_pickle=False)
            pred["lgb"][te] = z["lgb"]
            if do_mlp and "mlp" in z:
                pred["mlp"][te] = z["mlp"]
            fold_log.append({"fold": fi, "resumed": True,
                             "train_states": int(tr.sum()),
                             "test_states": int(te.sum())})
            n_cfg += len(ACTIONS) * (2 if do_mlp else 1)
            print(f"  fold {fi}: resumed from checkpoint", flush=True)
            continue
        Xtr, Xte = X[tr], X[te]
        t0 = time.time()
        for ai, a in enumerate(ACTIONS):
            y = out[tr, ai]
            ok = np.isfinite(y)
            if ok.sum() < 5000:
                continue
            m = _fit_lgb(Xtr[ok], y[ok].astype(np.float64), 1000 + ai)
            pred["lgb"][te, ai] = m.predict(Xte).astype(np.float32)
            del m
            n_cfg += 1
            if do_mlp:
                p = _fit_mlp(Xtr[ok], y[ok].astype(np.float64), 2000 + ai, rng)
                pred["mlp"][te, ai] = p.predict(Xte).astype(np.float32)
                del p
                n_cfg += 1
            print(f"    fold {fi} {a}: {time.time()-t0:.0f}s", flush=True)
        np.savez_compressed(ck, lgb=pred["lgb"][te], mlp=pred["mlp"][te])
        del Xtr, Xte
        fold_log.append({"fold": fi, "train_dates": list(f["train"]),
                         "test_dates": list(f["test"]),
                         "train_states": int(tr.sum()),
                         "test_states": int(te.sum()),
                         "seconds": round(time.time() - t0, 1)})
        print(f"  fold {fi}: train {tr.sum():,} test {te.sum():,} "
              f"{time.time()-t0:.0f}s", flush=True)

    res = {"folds": fold_log, "n_configs": n_cfg, "horizon": h,
           "out_of_fold_states": int(tested.sum()), "policies": {}}
    ref = out[:, A["HOLD"]]
    P = policy_actions(S)
    # every comparison below is OUT-OF-FOLD ONLY
    for kind in ("lgb", "mlp"):
        pr = pred[kind]
        if not np.isfinite(pr).any():
            continue
        full = np.where(np.isfinite(pr), pr, -np.inf)
        act = full.argmax(axis=1).astype(np.int8)
        v = policy_value(out, act)
        r = compare(v, ref, D, f"LEARNED_{kind}_argmax16", mask=tested)
        r["trade_share"] = round(float((act[tested] != A["HOLD"]).mean()), 4)
        r["action_mix"] = {ACTIONS[i]: int((act[tested] == i).sum())
                           for i in range(len(ACTIONS))
                           if (act[tested] == i).sum()}
        res["policies"][f"LEARNED_{kind}_argmax16"] = r
        # the conservative variant: argmax over four actions, not sixteen.
        # argmax over 16 noisy predictions is a winner's curse machine.
        sub = [A["HOLD"], A["TRIM_25"], A["SELL_CASH"], A["REPLACE_1W"]]
        act4 = np.array(sub, dtype=np.int8)[full[:, sub].argmax(axis=1)]
        v4 = policy_value(out, act4)
        r4 = compare(v4, ref, D, f"LEARNED_{kind}_argmax4", mask=tested)
        r4["trade_share"] = round(float((act4[tested] != A["HOLD"]).mean()), 4)
        r4["action_mix"] = {ACTIONS[i]: int((act4[tested] == i).sum())
                            for i in sub if (act4[tested] == i).sum()}
        res["policies"][f"LEARNED_{kind}_argmax4"] = r4
        # a pure trim/hold gate: sell only when the model says cash beats hold
        gate = np.where(full[:, A["SELL_CASH"]] > full[:, A["HOLD"]],
                        A["SELL_CASH"], A["HOLD"]).astype(np.int8)
        rg = compare(policy_value(out, gate), ref, D,
                     f"LEARNED_{kind}_sell_gate", mask=tested)
        rg["trade_share"] = round(float((gate[tested] != A["HOLD"]).mean()), 4)
        res["policies"][f"LEARNED_{kind}_sell_gate"] = rg

    # the baselines re-scored on EXACTLY the out-of-fold states, so the
    # learned-vs-baseline comparison is like for like
    res["baselines_out_of_fold"] = {}
    for name, act in P.items():
        r = compare(policy_value(out, act), ref, D, f"OOF::{name}", mask=tested)
        res["baselines_out_of_fold"][name] = r
        n_cfg += 1

    # H4: learner minus the BEST baseline, as its own paired difference
    best = max(res["baselines_out_of_fold"].items(),
               key=lambda kv: (kv[1]["delta_pp"] if kv[1]["delta_pp"]
                               is not None else -1e9))
    res["best_baseline"] = best[0]
    bact = P[best[0]]
    for kind in ("lgb", "mlp"):
        pr = pred[kind]
        if not np.isfinite(pr).any():
            continue
        full = np.where(np.isfinite(pr), pr, -np.inf)
        variants = {
            f"LEARNED_{kind}_argmax16": full.argmax(axis=1).astype(np.int8),
            f"LEARNED_{kind}_argmax4": np.array(
                [A["HOLD"], A["TRIM_25"], A["SELL_CASH"], A["REPLACE_1W"]],
                dtype=np.int8)[full[:, [A["HOLD"], A["TRIM_25"],
                                        A["SELL_CASH"],
                                        A["REPLACE_1W"]]].argmax(axis=1)],
            f"LEARNED_{kind}_sell_gate": np.where(
                full[:, A["SELL_CASH"]] > full[:, A["HOLD"]],
                A["SELL_CASH"], A["HOLD"]).astype(np.int8),
        }
        for vname, act in variants.items():
            r = compare(policy_value(out, act), policy_value(out, bact), D,
                        f"{vname} - best baseline ({best[0]})", mask=tested)
            res.setdefault("vs_best_baseline", {})[vname] = r
            n_cfg += 1
    res["n_configs"] = n_cfg
    return res


def run_robust(D: dict) -> dict:
    """Cost sensitivity, and the assertion block the verdict rests on.

    Transaction costs enter every branch LINEARLY on the traded fraction, so the
    whole cost curve is recoverable exactly from the stored half-spread without
    regenerating a single row:  outcome(m) = outcome(1x) + (1-m) * charged.
    This is exact for the eight non-replacement actions; the replacement arms
    also pay a basket-side cost that is not in the state table, so they are
    excluded and said to be excluded rather than approximated.
    """
    S = D["states"]
    cost_i = (S["hs_bps"].to_numpy(dtype=np.float64) + 6.0) / 1e4
    cb = 5.0 / 1e4
    with np.errstate(divide="ignore", invalid="ignore"):
        f_beta = np.clip(1.0 / S["beta_252"].to_numpy(dtype=np.float64), 0.0, 1.0)
    f_beta = np.where(np.isfinite(f_beta), f_beta, 1.0)
    charged = {
        "HOLD": np.zeros(len(S)),
        "ADD_50": 0.5 * cost_i + 0.5 * cb,
        "TRIM_10": 0.10 * cost_i, "TRIM_25": 0.25 * cost_i,
        "TRIM_50": 0.50 * cost_i,
        "SELL_CASH": cost_i, "SELL_BENCH": cost_i + cb,
        "REDUCE_BETA": (1.0 - f_beta) * cost_i,
    }
    res = {"cost_multipliers": {}, "n_configs": 0, "assertions": {},
           "cost_bps_charged": {
               k: round(float(np.nanmean(v)) * 1e4, 2) for k, v in charged.items()}}
    for m in (0.0, 1.0, 2.0, 3.0):
        for h in (20, 60, 252):
            out = D["out"][h]
            ref = out[:, A["HOLD"]]
            for a, c in charged.items():
                if a == "HOLD":
                    continue
                v = out[:, A[a]] + (1.0 - m) * c
                r = compare(v, ref, D, f"{a}@{h} cost x{m}")
                res["cost_multipliers"].setdefault(f"x{m}", {})\
                    .setdefault(str(h), {})[a] = r
                res["n_configs"] += 1
    # ── assertions: a check that did not run is not a check that passed ──
    hold252 = D["out"][252][:, A["HOLD"]]
    res["assertions"] = {
        "dates_with_outcomes": {str(h): int(np.isfinite(
            per_date_mean(D["out"][h][:, A["HOLD"]], D["date_ix"],
                          D["n_dates"])[0]).sum()) for h in HORIZONS},
        "hold_beats_cash_sign_at_60": bool(
            np.nanmean(D["out"][60][:, A["HOLD"]])
            > np.nanmean(D["out"][60][:, A["SELL_CASH"]])),
        # TRIM_50 must be the exact midpoint of HOLD and SELL_CASH, because
        # half a dollar in the name and half in cash pays half the exit cost.
        # Any deviation beyond float32 resolution is an accounting bug.
        "trim50_midpoint_identity_max_abs_error": float(np.nanmax(np.abs(
            D["out"][60][:, A["TRIM_50"]].astype(np.float64)
            - 0.5 * (D["out"][60][:, A["HOLD"]].astype(np.float64)
                     + D["out"][60][:, A["SELL_CASH"]].astype(np.float64))))),
        "worst_hold_252": round(float(np.nanmin(hold252)), 4),
        "best_hold_252": round(float(np.nanmax(hold252)), 4),
        "states_resolving_below_-95pct_at_252": int(
            np.nansum(hold252 < -0.95)),
    }
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["baselines", "questions", "learn", "robust", "all"])
    ap.add_argument("--no-mlp", action="store_true")
    a = ap.parse_args()
    # the learn stage needs only the primary horizon; loading all six costs
    # 600 MB it never reads and this box has 8 GB free
    D = load_all((PRIMARY_H,) if a.stage == "learn" else tuple(HORIZONS))
    total = 0
    if a.stage in ("baselines", "all"):
        r = run_baselines(D)
        (FACT / "exit_lab_1_baselines.json").write_text(json.dumps(r, indent=2))
        total += r["n_configs"]
        print(f"baselines: {r['n_configs']} configurations", flush=True)
    if a.stage in ("questions", "all"):
        q = run_questions(D)
        q["Q5_reentry"] = run_reentry(D)
        n = q.pop("_n_configs") + q["Q5_reentry"]["_n_configs"]
        q["n_configs"] = n
        (FACT / "exit_lab_1_questions.json").write_text(json.dumps(q, indent=2))
        total += n
        print(f"questions: {n} configurations", flush=True)
    if a.stage in ("robust", "all"):
        r = run_robust(D)
        (FACT / "exit_lab_1_robust.json").write_text(json.dumps(r, indent=2))
        total += r["n_configs"]
        print(f"robustness: {r['n_configs']} configurations", flush=True)
    if a.stage in ("learn", "all"):
        L = run_learn(D, do_mlp=not a.no_mlp)
        (FACT / "exit_lab_1_learned.json").write_text(json.dumps(L, indent=2))
        total += L["n_configs"]
        print(f"learned: {L['n_configs']} configurations", flush=True)
    print(f"TOTAL CONFIGURATIONS THIS STAGE: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
