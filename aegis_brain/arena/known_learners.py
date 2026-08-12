"""GRAND-ARENA-1 PHASE 1 — the learners, the splitter, and the statistics.

Three things live here and nothing else:

1. **`purged_walk_forward`** — temporal splits with a purge and an embargo.
   Never random k-fold; the house rule is not negotiable and on a panel whose
   label is a forward return, a shuffled fold trains on the answer.
2. **The learners.** Every one of them fits its own scaler, its own feature
   selection and its own hyper-parameters INSIDE the fold. Full-sample fitting
   of a scaler is the leakage defect this programme has already been bitten by
   and it is the defect that would make a known-answer test pass for the wrong
   reason.
3. **`effect_block`** — the CANON §19 power block. Every number reported by this
   phase carries the 80%-power minimum detectable effect computed on the SAME
   variance estimator as its t-stat, and MDE = t_bar x max(HAC, IID) per the
   NIGHT-11 ruling. A result below its MDE is NOT DETECTABLE. It is never a kill
   and it is never a pass.

DELIBERATE ORDERING: the simple learners come first and the neural network last.
A net that beats LightGBM on a world with a linear planted rule is a red flag
about the harness, not a win.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

from aegis_brain.arena.known_worlds import FEATURES         # noqa: E402
from aegis_brain.harness.benchmark import newey_west_tstat  # noqa: E402

T_BAR = 2.0            # house standard: the bar a t-stat must clear
NW_LAGS = 6


# ── splits ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Fold:
    k: int
    train_t: np.ndarray
    test_t: np.ndarray


def purged_walk_forward(t_max: int, *, n_folds: int = 8, min_train: int = 96,
                        embargo: int = 3, horizon: int = 1) -> list[Fold]:
    """Expanding-window walk-forward with a purge and an embargo.

    The label at month `t` is the return realised over `t+1`, so a training row
    at `t` overlaps any test month at or before `t + horizon`. `purge` removes
    that overlap; `embargo` removes a further `embargo` months so that slow
    state variables (f_val has an AR(1) coefficient of 0.95) cannot carry the
    test period's information backwards into the fit.
    """
    usable = t_max + 1
    first_test = min_train + horizon + embargo
    span = usable - first_test
    if span < n_folds:
        raise ValueError(f"{span} test months cannot make {n_folds} folds")
    block = span // n_folds
    folds = []
    for k in range(n_folds):
        ts = first_test + k * block
        te = ts + block if k < n_folds - 1 else usable
        train_end = ts - horizon - embargo          # exclusive
        folds.append(Fold(k=k, train_t=np.arange(0, train_end),
                          test_t=np.arange(ts, te)))
    return folds


# ── the CANON §19 power block ───────────────────────────────────────────────
def effect_block(x: pd.Series | np.ndarray, *, label: str, unit: str,
                 annualize: bool = False, lags: int = NW_LAGS) -> dict:
    """Mean of a per-period series with its t, its SE and its 80%-power MDE.

    MDE = t_bar x max(se_hac, se_iid). NIGHT-11: the MDE and the t must share a
    variance estimator, and taking the max refuses the free power that a
    short-sample negative autocovariance would otherwise hand over.
    """
    s = pd.Series(x).dropna().astype(float)
    n = len(s)
    if n < 12 or s.std(ddof=1) == 0:
        return {"label": label, "unit": unit, "n": int(n), "mean": None,
                "mde": None, "detected": None,
                "note": "fewer than 12 periods — reported, never interpreted"}
    nw = newey_west_tstat(s, lags=lags)
    se_iid = float(s.std(ddof=1) / np.sqrt(n))
    se_hac = float(nw["se"]) if nw["se"] else se_iid
    se = max(se_hac, se_iid)
    mean = float(s.mean())
    k = 12.0 if annualize else 1.0
    return {
        "label": label, "unit": unit + ("/yr" if annualize else ""),
        "n": int(n),
        "mean": round(mean * k, 6),
        "se": round(se * k, 6),
        "se_iid": round(se_iid * k, 6),
        "se_hac": round(se_hac * k, 6),
        "t": round(mean / se, 3),
        "mde": round(T_BAR * se * k, 6),
        "detected": bool(abs(mean) > T_BAR * se),
        "sign": int(np.sign(mean)),
        "estimator": f"Newey-West({lags}); MDE = {T_BAR} x max(HAC, IID)",
    }


# ── cross-sectional scoring ─────────────────────────────────────────────────
def _month_groups(t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Start offsets and sizes for a t-sorted array (for np.add.reduceat)."""
    change = np.flatnonzero(np.diff(t)) + 1
    starts = np.concatenate([[0], change])
    sizes = np.diff(np.concatenate([starts, [len(t)]]))
    return starts, sizes


def _zscore_by_month(v: np.ndarray, starts: np.ndarray,
                     sizes: np.ndarray) -> np.ndarray:
    m = np.repeat(np.add.reduceat(v, starts) / sizes, sizes)
    d = v - m
    sd = np.sqrt(np.repeat(np.add.reduceat(d * d, starts) / sizes, sizes))
    sd[sd == 0] = 1.0
    return d / sd


def _rank_by_month(v: np.ndarray, t: np.ndarray) -> np.ndarray:
    return pd.Series(v).groupby(t).rank(pct=True).to_numpy() - 0.5


def monthly_ic(score: np.ndarray, y: np.ndarray, t: np.ndarray) -> pd.Series:
    """Per-month cross-sectional Spearman IC. t must be sorted ascending."""
    sr = _rank_by_month(score, t)
    yr = _rank_by_month(y, t)
    starts, sizes = _month_groups(t)
    a = _zscore_by_month(sr, starts, sizes)
    b = _zscore_by_month(yr, starts, sizes)
    ic = np.add.reduceat(a * b, starts) / sizes
    return pd.Series(ic, index=t[starts])


def decile_spread(score: np.ndarray, y: np.ndarray, t: np.ndarray,
                  *, frac: float = 0.2, cost_bps: float = 0.0
                  ) -> tuple[pd.Series, pd.Series, float]:
    """Top-frac minus bottom-frac monthly spread, gross and net of turnover.

    Turnover is measured against the previous month's actual membership, so a
    fast signal pays for its own churn rather than being charged a guess.

    The turnover returned is TWO-SIDED PER LEG — the symmetric difference over
    the leg size — so it runs 0 to 2 and reaches 2 when a leg is completely
    replaced (100% sold, 100% bought). The cost charge is
    `2 (legs) x turnover x cost_bps`, which for a fully-replaced long-short book
    at 65 bps is 2 x 2 x 65 = 260 bps per month. Naming it `1way` would have
    made a correct charge look like a doubled one.
    """
    df = pd.DataFrame({"t": t, "score": score, "y": y})
    gross, net, turns = {}, {}, []
    prev_l: set = set()
    prev_s: set = set()
    idx_names = np.arange(len(df))
    df["_i"] = idx_names
    for tt, g in df.groupby("t", sort=True):
        k = max(int(len(g) * frac), 5)
        srt = g.sort_values("score", ascending=False)
        lo_i, hi_i = set(srt["_i"].to_numpy()[:k]), set(srt["_i"].to_numpy()[-k:])
        gsp = float(srt["y"].to_numpy()[:k].mean() - srt["y"].to_numpy()[-k:].mean())
        # membership is compared by rank position, not by name id, because the
        # id space is identical every month; positions are what turn over
        turn = 0.5 * (len(lo_i ^ prev_l) / max(len(lo_i), 1)
                      + len(hi_i ^ prev_s) / max(len(hi_i), 1)) if prev_l else 1.0
        turns.append(turn)
        gross[tt] = gsp
        net[tt] = gsp - 2.0 * turn * cost_bps / 1e4
        prev_l, prev_s = lo_i, hi_i
    return (pd.Series(gross), pd.Series(net),
            float(np.mean(turns)) if turns else float("nan"))


def score_feature_corr(score: np.ndarray, panel: pd.DataFrame,
                       cols: list[str] | None = None,
                       mask: np.ndarray | None = None) -> dict[str, float]:
    """Mean per-month Spearman correlation of the model's score with each feature.

    This is the model-agnostic mechanism probe. It works identically for a ridge,
    a forest, an evolved weight vector and a bandit, which is the point: the
    recovery test must not depend on a learner exposing coefficients.
    """
    # market-level columns are CONSTANT within a month, so their
    # cross-sectional correlation is undefined rather than zero. Including them
    # put NaN into the receipt and into the JSON artifact; excluding them says
    # the true thing, which is that this probe cannot see them.
    cols = cols or [c for c in FEATURES
                    if not c.startswith(("sec_", "m_"))]
    d = panel if mask is None else panel[mask]
    s = pd.Series(score if mask is None else score[mask], index=d.index)
    out = {}
    for c in cols:
        v = d.groupby("t").apply(
            lambda g, c=c: pd.Series(s.loc[g.index]).corr(g[c], method="spearman"),
            include_groups=False)
        out[c] = round(float(v.mean()), 4)
    return out


# ── cross-sectional learners ────────────────────────────────────────────────
def _xy(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return df[FEATURES].to_numpy(np.float64), df["y"].to_numpy(np.float64)


def learn_ridge(tr, te, seed):
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    Xtr, ytr = _xy(tr)
    m = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    m.fit(Xtr, ytr)
    return m.predict(te[FEATURES].to_numpy(np.float64))


def learn_logistic(tr, te, seed):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    Xtr, ytr = _xy(tr)
    med = tr.groupby("t")["y"].transform("median").to_numpy()
    lab = (ytr > med).astype(int)
    m = make_pipeline(StandardScaler(),
                      LogisticRegression(C=0.1, max_iter=2000))
    m.fit(Xtr, lab)
    return m.predict_proba(te[FEATURES].to_numpy(np.float64))[:, 1]


def learn_rf(tr, te, seed):
    from sklearn.ensemble import RandomForestRegressor
    Xtr, ytr = _xy(tr)
    m = RandomForestRegressor(n_estimators=200, max_depth=7,
                              min_samples_leaf=200, max_features=0.5,
                              n_jobs=-1, random_state=seed)
    m.fit(Xtr, ytr)
    return m.predict(te[FEATURES].to_numpy(np.float64))


def learn_lgbm(tr, te, seed):
    import lightgbm as lgb
    Xtr, ytr = _xy(tr)
    m = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.02, num_leaves=15,
                          min_child_samples=200, subsample=0.7,
                          subsample_freq=1, colsample_bytree=0.7,
                          reg_lambda=5.0, random_state=seed, verbose=-1,
                          n_jobs=-1)
    m.fit(Xtr, ytr)
    return m.predict(te[FEATURES].to_numpy(np.float64))


def learn_mlp(tr, te, seed):
    """Small torch net. Early stopping on the temporally LAST 20% of train.

    The validation slice is the tail of the training window, never a random
    slice: a randomly chosen validation month sits between training months and
    the state variables are persistent, so a random split leaks.
    """
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    Xtr, ytr = _xy(tr)
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd[sd == 0] = 1.0
    ysd = ytr.std() or 1.0
    cut = int(len(Xtr) * 0.8)
    ts = tr["t"].to_numpy()
    cut = int(np.searchsorted(ts, ts[cut]))          # cut on a month boundary

    def T(a):        # torch 2.2 + numpy 2.x on this box has no numpy bridge
        return torch.tensor(np.asarray(a, dtype=np.float64).tolist(),
                            dtype=torch.float32)

    Xa, Xb = T((Xtr[:cut] - mu) / sd), T((Xtr[cut:] - mu) / sd)
    ya, yb = T((ytr[:cut] / ysd)[:, None]), T((ytr[cut:] / ysd)[:, None])
    net = nn.Sequential(nn.Linear(len(FEATURES), 32), nn.ReLU(), nn.Dropout(0.2),
                        nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1))
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    lossf = nn.MSELoss()
    best, best_state, bad = float("inf"), None, 0
    n, bs = len(Xa), 1024
    g = torch.Generator().manual_seed(seed)
    for epoch in range(60):
        net.train()
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, bs):
            j = perm[i:i + bs]
            opt.zero_grad()
            lossf(net(Xa[j]), ya[j]).backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            v = float(lossf(net(Xb), yb))
        if v < best - 1e-6:
            best, bad = v, 0
            best_state = {k: t.clone() for k, t in net.state_dict().items()}
        else:
            bad += 1
            if bad >= 8:
                break
    if best_state is not None:
        net.load_state_dict(best_state)
    Xte = (te[FEATURES].to_numpy(np.float64) - mu) / sd
    net.eval()
    with torch.no_grad():
        return np.asarray(net(T(Xte)).squeeze(-1).tolist())


def learn_evo(tr, te, seed):
    """Evolutionary policy search over a linear score on rank-transformed features.

    Present because it is the programme's overfitting canary: it optimises the
    IN-SAMPLE version of the exact statistic the scorer reports out of sample,
    with no regularisation beyond a small population and a fitness that is an
    average over months. If any learner invents an edge in the null worlds, the
    prior says it is this one.
    """
    rng = np.random.default_rng(seed)
    t = tr["t"].to_numpy()
    R = np.column_stack([_rank_by_month(tr[c].to_numpy(), t) for c in FEATURES])
    starts, sizes = _month_groups(t)
    yz = _zscore_by_month(_rank_by_month(tr["y"].to_numpy(), t), starts, sizes)
    sz = sizes.astype(float)

    def fitness(W):                      # W: (n_feat, pop)
        S = R @ W
        m = np.repeat(np.add.reduceat(S, starts, axis=0) / sz[:, None], sizes, 0)
        D = S - m
        sd = np.sqrt(np.repeat(np.add.reduceat(D * D, starts, axis=0) / sz[:, None],
                               sizes, 0))
        sd[sd == 0] = 1.0
        Z = D / sd
        return (np.add.reduceat(Z * yz[:, None], starts, axis=0)
                / sz[:, None]).mean(axis=0)

    pop, gens, elite = 80, 30, 12
    W = rng.normal(0, 1, (len(FEATURES), pop))
    W /= np.linalg.norm(W, axis=0, keepdims=True)
    for _ in range(gens):
        f = fitness(W)
        keep = W[:, np.argsort(f)[::-1][:elite]]
        kids = keep[:, rng.integers(0, elite, pop - elite)]
        kids = kids + rng.normal(0, 0.25, kids.shape)
        kids /= np.linalg.norm(kids, axis=0, keepdims=True)
        W = np.column_stack([keep, kids])
    best = W[:, int(np.argmax(fitness(W)))]
    tt = te["t"].to_numpy()
    Rte = np.column_stack([_rank_by_month(te[c].to_numpy(), tt) for c in FEATURES])
    return Rte @ best


def learn_hmm_regime(tr, te, seed):
    """Gaussian HMM on market-level observables, then a Ridge PER STATE.

    The state is FILTERED, never smoothed: the weight applied at month t uses
    `predict` on the history up to and including t only. A smoothed state uses
    the future to label the present and would make the regime world trivially
    recoverable for the wrong reason.
    """
    from hmmlearn.hmm import GaussianHMM
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    mk_tr = tr.groupby("t")[["mkt", "m_vol"]].first()
    mk_te = te.groupby("t")[["mkt", "m_vol"]].first()
    obs_tr = mk_tr.to_numpy()
    # FIVE RESTARTS, selected on the TRAINING log-likelihood. Baum-Welch is EM
    # and EM finds local optima: on this world a single arbitrary seed landed at
    # 52% state accuracy — chance — while the best of five reached 70%, and the
    # spread across seeds was the entire difference between "HMMs cannot find
    # this regime" and "HMMs can". Restart selection uses training likelihood
    # only, so nothing about the test period enters the choice.
    hmm, best_ll = None, -np.inf
    for r in range(5):
        try:
            h = GaussianHMM(n_components=2, covariance_type="diag", n_iter=200,
                            random_state=seed + 977 * r)
            h.fit(obs_tr)
            ll = float(h.score(obs_tr))
        except Exception as exc:                            # pragma: no cover
            logger.warning("HMM restart %d failed: %s", r, exc)
            continue
        if np.isfinite(ll) and ll > best_ll:
            hmm, best_ll = h, ll
    if hmm is None:                                         # pragma: no cover
        logger.warning("every HMM restart failed — falling back to a pooled ridge")
        return learn_ridge(tr, te, seed)
    st_tr = hmm.predict(obs_tr)

    # FILTERED state on test: the forward posterior at the end of each growing
    # prefix. Not the smoothed path — a smoothed state uses the future to label
    # the present, which would make the regime world recoverable for a reason
    # that does not exist in production.
    full = np.vstack([obs_tr, mk_te.to_numpy()])
    st_te = np.empty(len(mk_te), dtype=int)
    for i in range(len(mk_te)):
        st_te[i] = int(hmm.predict_proba(full[: len(obs_tr) + i + 1])[-1].argmax())

    smap_tr = dict(zip(mk_tr.index, st_tr))
    smap_te = dict(zip(mk_te.index, st_te))
    tr_state = tr["t"].map(smap_tr).to_numpy()
    te_state = te["t"].map(smap_te).to_numpy()

    out = np.zeros(len(te))
    for s in (0, 1):
        a, b = tr_state == s, te_state == s
        if a.sum() < 2000 or b.sum() == 0:
            if b.sum():
                out[b] = learn_ridge(tr, te[b], seed)
            continue
        m = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        m.fit(tr.loc[a, FEATURES].to_numpy(np.float64),
              tr.loc[a, "y"].to_numpy(np.float64))
        out[b] = m.predict(te.loc[b, FEATURES].to_numpy(np.float64))
    # store the decoded states so the scorer can grade the regime itself
    learn_hmm_regime.last_states = (smap_tr, smap_te)
    return out


XS_LEARNERS = {
    "ridge": learn_ridge,
    "logistic": learn_logistic,
    "random_forest": learn_rf,
    "lightgbm": learn_lgbm,
    "mlp_torch": learn_mlp,
    "evolutionary": learn_evo,
    "hmm_regime": learn_hmm_regime,
}


# ── exposure-policy learners (worlds D and L) ───────────────────────────────
MKT_FEATURES = ["m_vol", "m_ret12", "m_precursor", "mkt"]


def _mkt_frame(world) -> pd.DataFrame:
    m = world.market.copy()
    m["y_mkt"] = m["mkt"].shift(-1)
    m["y_shock"] = m["shock_next"]
    return m.dropna(subset=["y_mkt"]).reset_index(drop=True)


def _clip01(w):
    return np.clip(w, 0.0, 1.0)


def pol_static(tr, te, seed):
    return np.full(len(te), 0.7)


def pol_ridge(tr, te, seed):
    """Predict next month's market return, then size linearly in the forecast."""
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    m = make_pipeline(StandardScaler(), Ridge(alpha=5.0))
    m.fit(tr[MKT_FEATURES], tr["y_mkt"])
    p = m.predict(te[MKT_FEATURES])
    sd = float(tr["y_mkt"].std(ddof=1)) or 1.0
    return _clip01(0.7 + 3.0 * (p - float(tr["y_mkt"].mean())) / sd * 0.3)


def pol_logistic(tr, te, seed):
    """Estimate P(bad month) and de-risk IN PROPORTION to it — never a peak call.

    The label is a DRAWDOWN month, defined mechanically as a market return below
    the training window's 10th percentile. WORLD-D's true shock flag is never
    shown to the learner; if it were, the world would be graded on a label it
    was handed.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    q = float(tr["y_mkt"].quantile(0.10))
    lab = (tr["y_mkt"] < q).astype(int)
    if lab.sum() < 8:
        return np.full(len(te), 0.7)
    m = make_pipeline(StandardScaler(),
                      LogisticRegression(C=1.0, max_iter=2000))
    m.fit(tr[MKT_FEATURES], lab)
    p = m.predict_proba(te[MKT_FEATURES])[:, 1]
    pol_logistic.last_prob = p
    return _clip01(1.0 - 2.5 * p)


def pol_lgbm(tr, te, seed):
    import lightgbm as lgb
    q = float(tr["y_mkt"].quantile(0.10))
    lab = (tr["y_mkt"] < q).astype(int)
    if lab.sum() < 8:
        return np.full(len(te), 0.7)
    m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=7,
                           min_child_samples=20, random_state=seed, verbose=-1)
    m.fit(tr[MKT_FEATURES], lab)
    p = m.predict_proba(te[MKT_FEATURES])[:, 1]
    pol_lgbm.last_prob = p
    return _clip01(1.0 - 2.5 * p)


def pol_offline_q(tr, te, seed):
    """Conservative one-step fitted-Q over an exposure grid.

    Offline, from a logged uniform-random behaviour policy, with a pessimism
    penalty proportional to the estimator's own standard error on each arm. The
    penalty is what makes it CONSERVATIVE: an arm whose value is poorly
    estimated is not allowed to win on the strength of that ignorance, which is
    the exact mechanism by which a naive value learner invents a timing edge in
    a null world.
    """
    from sklearn.linear_model import Ridge
    rng = np.random.default_rng(seed)
    grid = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    a_tr = grid[rng.integers(0, len(grid), len(tr))]        # logged behaviour
    r_tr = a_tr * tr["y_mkt"].to_numpy()
    X = np.column_stack([tr[MKT_FEATURES].to_numpy(), a_tr, a_tr ** 2,
                         a_tr * tr["m_precursor"].to_numpy(),
                         a_tr * tr["m_vol"].to_numpy()])
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    q = Ridge(alpha=10.0).fit((X - mu) / sd, r_tr)
    resid_sd = float(np.std(r_tr - q.predict((X - mu) / sd), ddof=1))
    best = np.zeros(len(te))
    Xte_base = te[MKT_FEATURES].to_numpy()
    prec, vol = te["m_precursor"].to_numpy(), te["m_vol"].to_numpy()
    vals = np.zeros((len(te), len(grid)))
    for i, a in enumerate(grid):
        Xa = np.column_stack([Xte_base, np.full(len(te), a),
                              np.full(len(te), a ** 2), a * prec, a * vol])
        n_a = max((a_tr == a).sum(), 1)
        pessimism = resid_sd / np.sqrt(n_a)      # lower confidence bound
        vals[:, i] = q.predict((Xa - mu) / sd) - pessimism
    best = grid[vals.argmax(axis=1)]
    return best


def pol_evo(tr, te, seed):
    """Evolve a sigmoid exposure rule on the market observables. The canary."""
    rng = np.random.default_rng(seed)
    Xtr = tr[MKT_FEATURES].to_numpy()
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd[sd == 0] = 1.0
    Z = (Xtr - mu) / sd
    y = tr["y_mkt"].to_numpy()
    pop, gens, elite = 60, 40, 10
    W = rng.normal(0, 1, (len(MKT_FEATURES) + 1, pop))

    def w_of(Zx, G):
        return 1.0 / (1.0 + np.exp(-(Zx @ G[:-1] + G[-1])))

    def fit(G):
        w = w_of(Z, G)
        r = w * y[:, None]
        # matched-average-exposure fitness: a genome cannot win by simply
        # holding more of a positive equity premium
        base = w.mean(axis=0)[None, :] * y[:, None]
        d = r - base
        return d.mean(axis=0) / (d.std(axis=0, ddof=1) + 1e-9)

    for _ in range(gens):
        f = fit(W)
        keep = W[:, np.argsort(f)[::-1][:elite]]
        kids = keep[:, rng.integers(0, elite, pop - elite)] + \
            rng.normal(0, 0.3, (W.shape[0], pop - elite))
        W = np.column_stack([keep, kids])
    best = W[:, int(np.argmax(fit(W)))]
    return _clip01(w_of((te[MKT_FEATURES].to_numpy() - mu) / sd, best[:, None])[:, 0])


EXPOSURE_LEARNERS = {
    "ridge": pol_ridge,
    "logistic": pol_logistic,
    "lightgbm": pol_lgbm,
    "offline_q": pol_offline_q,
    "evolutionary": pol_evo,
}


# ── action-value learners (world K) ─────────────────────────────────────────
ACTIONS = ("hold", "cash", "replace")
K_STATE = ["f_qual", "f_val", "f_mom", "f_rev", "f_n1", "m_vol", "m_precursor"]


#: 66 of the 200 names are held and the next 66 by quality are the candidate
#: set. The book size is a POWER parameter: the monthly value series averages
#: over slots, so a small book leaves the world's own optimal rule below its
#: MDE. Fixed from an oracle calculation, before any learner was scored.
K_BOOK_SIZE = 66


def build_k_logs(world, *, seed: int) -> pd.DataFrame:
    """Logged transitions under a UNIFORM-RANDOM behaviour policy.

    Uniform logging is the friendly case for offline evaluation: every action is
    observed in every state region, so nothing has to be extrapolated. Stating
    that plainly matters, because a real logged book is nothing like this and a
    learner that only works under uniform logging has not been shown to work.

    EACH SLOT GETS ITS OWN CANDIDATE. The first version handed every slot the
    same single best outsider, so the whole replace leg of a month was one
    draw of idiosyncratic noise repeated forty times. Averaging across slots
    then bought nothing, the monthly value series had the volatility of a
    single stock, and the world's minimum detectable effect came out at 14%/yr
    — larger than any effect the world contains. That was a measurement defect,
    not a hard world.
    """
    rng = np.random.default_rng(seed)
    p = world.panel
    T = int(p["t"].max()) + 1
    names = np.sort(p["name"].unique())
    cost = world.meta.get("cost_bps_one_way", 30.0) / 1e4
    wide_y = p.pivot(index="t", columns="name", values="y")
    wide_q = p.pivot(index="t", columns="name", values="f_qual")
    state_wide = {c: p.pivot(index="t", columns="name", values=c) for c in K_STATE}

    rows = []
    for t in range(T - 1):
        if t not in wide_y.index:
            continue
        qrow = wide_q.loc[t]
        # The held book is RESAMPLED each month rather than evolved. Under an
        # evolving book the uniform-random logging policy refreshes a third of
        # the slots every month, so within a few years almost nothing in the
        # book is stale and the decision the world exists to pose stops being
        # posed: the logged state distribution had 5% stale names against a
        # population 31%, and the recoverable effect collapsed from 2.6%/yr to
        # 0.4%/yr. Resampling keeps the state distribution representative and
        # makes the problem what it actually is — a ONE-STEP contextual action
        # choice, with no sequential structure that any learner here exploits.
        book = list(names[rng.choice(len(names), K_BOOK_SIZE, replace=False)])
        held = set(book)
        outside = qrow[[n for n in names if n not in held]]
        cands = list(outside.sort_values(ascending=False).index[:len(book)])
        for slot, n in enumerate(book):
            cand = cands[slot]
            r_cand = float(wide_y.loc[t, cand]) - cost
            a = ACTIONS[rng.integers(0, 3)]
            r_hold = float(wide_y.loc[t, n])
            rewards = {"hold": r_hold, "cash": 0.0, "replace": r_cand}
            row = {"t": t, "name": n, "action": a, "reward": rewards[a],
                   "r_hold": r_hold, "r_cash": 0.0, "r_replace": r_cand,
                   "cand": cand, "cand_qual": float(qrow[cand])}
            for c in K_STATE:
                row[c] = float(state_wide[c].loc[t, n])
            rows.append(row)
    df = pd.DataFrame(rows)
    # the TRUE optimal action, from the generating rule rather than from
    # realised returns: replace a stale name, hold anything else, never cash
    st = world.truth["stale_threshold"]
    df["true_best"] = np.where(df["f_qual"] < st, "replace", "hold")
    return df


def _k_fit_predict(model_kind, tr, te, seed):
    """Fit Q(s, a) on logged (state, action, reward) and return greedy actions."""
    from sklearn.linear_model import Ridge
    import lightgbm as lgb
    A = np.eye(3)
    a_idx = tr["action"].map({a: i for i, a in enumerate(ACTIONS)}).to_numpy()
    S = tr[K_STATE].to_numpy()
    X = np.column_stack([S, A[a_idx], S * A[a_idx][:, :1], S * A[a_idx][:, 2:3]])
    r = tr["reward"].to_numpy()
    if model_kind == "ridge":
        mu, sd = X.mean(0), X.std(0)
        sd[sd == 0] = 1.0
        m = Ridge(alpha=5.0).fit((X - mu) / sd, r)
        pred = lambda Z: m.predict((Z - mu) / sd)          # noqa: E731
    elif model_kind == "lightgbm":
        m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03,
                              num_leaves=15, min_child_samples=100,
                              random_state=seed, verbose=-1, n_jobs=-1)
        m.fit(X, r)
        pred = m.predict
    else:
        raise ValueError(model_kind)
    Ste = te[K_STATE].to_numpy()
    n_a = np.array([(a_idx == i).sum() for i in range(3)])
    resid = float(np.std(r - pred(X), ddof=1))
    vals = np.zeros((len(te), 3))
    for i in range(3):
        oh = np.tile(A[i], (len(te), 1))
        Z = np.column_stack([Ste, oh, Ste * oh[:, :1], Ste * oh[:, 2:3]])
        pess = resid / np.sqrt(max(n_a[i], 1)) if model_kind == "ridge" else 0.0
        vals[:, i] = pred(Z) - pess
    return np.array(ACTIONS)[vals.argmax(axis=1)]


def k_ridge(tr, te, seed):
    return _k_fit_predict("ridge", tr, te, seed)


def k_lgbm(tr, te, seed):
    return _k_fit_predict("lightgbm", tr, te, seed)


def k_offline_q(tr, te, seed):
    """Conservative fitted-Q: per-action value with an explicit pessimism term.

    Values are estimated by a gradient-boosted regressor per action on the
    subset of logs where that action was taken, and each action's value is
    penalised by its own standard error. This is the arm that is supposed to
    refuse cash, and refusing cash is the world's whole point.
    """
    import lightgbm as lgb
    Ste = te[K_STATE].to_numpy()
    vals = np.zeros((len(te), 3))
    for i, a in enumerate(ACTIONS):
        sub = tr[tr["action"] == a]
        if len(sub) < 200:
            vals[:, i] = -1e9
            continue
        m = lgb.LGBMRegressor(n_estimators=250, learning_rate=0.03,
                              num_leaves=15, min_child_samples=100,
                              random_state=seed, verbose=-1, n_jobs=-1)
        m.fit(sub[K_STATE].to_numpy(), sub["reward"].to_numpy())
        se = float(sub["reward"].std(ddof=1) / np.sqrt(len(sub)))
        vals[:, i] = m.predict(Ste) - 2.0 * se
    return np.array(ACTIONS)[vals.argmax(axis=1)]


def k_evo(tr, te, seed):
    """Evolve a linear scoring rule per action over the state. The canary again."""
    rng = np.random.default_rng(seed)
    S = tr[K_STATE].to_numpy()
    mu, sd = S.mean(0), S.std(0)
    sd[sd == 0] = 1.0
    Z = np.column_stack([(S - mu) / sd, np.ones(len(S))])
    R = tr[["r_hold", "r_cash", "r_replace"]].to_numpy()
    pop, gens, elite = 60, 40, 10
    d = Z.shape[1]
    W = rng.normal(0, 1, (pop, d, 3))

    def fit(W):
        out = np.empty(len(W))
        for i, g in enumerate(W):
            a = (Z @ g).argmax(axis=1)
            out[i] = R[np.arange(len(R)), a].mean()
        return out

    for _ in range(gens):
        f = fit(W)
        keep = W[np.argsort(f)[::-1][:elite]]
        kids = keep[rng.integers(0, elite, pop - elite)] + \
            rng.normal(0, 0.3, (pop - elite, d, 3))
        W = np.concatenate([keep, kids])
    best = W[int(np.argmax(fit(W)))]
    Ste = te[K_STATE].to_numpy()
    Zte = np.column_stack([(Ste - mu) / sd, np.ones(len(Ste))])
    return np.array(ACTIONS)[(Zte @ best).argmax(axis=1)]


ACTION_LEARNERS = {
    "ridge": k_ridge,
    "lightgbm": k_lgbm,
    "offline_q": k_offline_q,
    "evolutionary": k_evo,
}


# ── contextual bandit (worlds G, H and the null control I) ──────────────────
BANDIT_ARMS = ("f_specA", "f_specB", "f_mom", "no_tilt")


def run_linucb(world, *, alpha: float = 1.0, seed: int = 0,
               test_t: np.ndarray | None = None) -> dict:
    """LinUCB over {follow A, follow B, follow momentum, no tilt}, per sector.

    Context is the sector one-hot. The bandit runs ONLINE over the whole
    timeline and is graded only on the test months, which is the honest way to
    evaluate an online learner: there is no train/test leakage because it never
    sees a reward before it has paid for the pull.

    THE CONFIDENCE WIDTH IS SCALED BY THE OBSERVED REWARD NOISE. Textbook LinUCB
    assumes rewards in [0, 1]; these rewards are monthly long-short spreads of
    order 0.02. With an unscaled alpha the exploration bonus after 75 pulls is
    0.115 against arm-value differences of 0.005, so the bonus dominates for
    ever and the "bandit" is a uniform random policy wearing a bandit's clothes.
    The first version of this function did exactly that: it ran green, allocated
    35% to the skilled arm instead of the ~90% it should, and reported a gain
    below its own MDE. Scaling the width by the running reward sd is the
    standard correction, not a tuning knob.
    """
    rng = np.random.default_rng(seed)
    p = world.panel
    sectors = sorted(p["sector_id"].unique())
    d = len(sectors)
    A = {a: np.eye(d) for a in BANDIT_ARMS}
    b = {a: np.zeros(d) for a in BANDIT_ARMS}
    picks, rewards, uniform_rewards = [], [], []
    seen: list[float] = []
    for t, g in p.groupby("t", sort=True):
        for s in sectors:
            gs = g[g["sector_id"] == s]
            if len(gs) < 10:
                continue
            x = np.zeros(d)
            x[sectors.index(s)] = 1.0
            scale = float(np.std(seen, ddof=1)) if len(seen) > 30 else 1.0
            ucb = {}
            for a in BANDIT_ARMS:
                Ainv = np.linalg.inv(A[a])
                th = Ainv @ b[a]
                ucb[a] = float(th @ x + alpha * scale * np.sqrt(x @ Ainv @ x))
            arm = max(ucb, key=ucb.get)
            rew = {}
            for a in BANDIT_ARMS:
                if a == "no_tilt":
                    rew[a] = 0.0
                else:
                    k = max(len(gs) // 5, 2)
                    srt = gs.sort_values(a, ascending=False)["y"].to_numpy()
                    rew[a] = float(srt[:k].mean() - srt[-k:].mean())
            r = rew[arm]
            A[arm] += np.outer(x, x)
            b[arm] += r * x
            picks.append({"t": t, "sector_id": s, "arm": arm, "reward": r})
            rewards.append(r)
            seen.append(r)
            uniform_rewards.append(float(np.mean([rew[a] for a in BANDIT_ARMS])))
    df = pd.DataFrame(picks)
    df["uniform_reward"] = uniform_rewards
    if test_t is not None:
        df = df[df["t"].isin(set(test_t.tolist()))]
    return {"picks": df}
