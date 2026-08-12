"""REGIME-ARENA-1 — GRAND-ARENA-1 chunk 5. States, options, and the conditioner.

Pre-registered `TRIALS/PREREG_REGIME_ARENA_1.md` at commit 9e5dd09, BEFORE this
file existed.

THE ONE IDEA IN THIS MODULE
===========================
Chunk 6 tested a regime rule as an EXPOSURE dial and found nothing observable.
This module never varies exposure — gross is 1.00 in every arm and the runner
verifies it. What varies is whether a *cross-sectional* decision (which names,
which signal weights, which risk model) is made from the whole realised past or
from the part of the past that carried the current state label.

So every conditioned arm has an exact twin that runs the identical machinery
with the state label deleted. "Regime-conditioned X beats regime-conditioned
nothing" is not a result and is not computed anywhere in this file.

WHAT IS POINT-IN-TIME, AND WHY THE TRIPWIRE MATTERS MORE THAN THE PROOF
----------------------------------------------------------------------
Every state label at date k is a function of rows <= k, and the conditioning set
at k is {m <= k-1 : state(m) == state(k)} — month m's forward return is realised
at m+1, so m <= k-1 is exactly the set of outcomes known at k.

Two arms are built to VIOLATE that, and the harness is required to catch them:
`S_ORACLE2` (the label is the sign of NEXT month's market return) and `S_LEAKY3`
(tercile breakpoints fitted on the full sample). A causality proof that could not
have produced a violation is worthless — WORLD-I's argument about null verdicts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT))

FACTORY = MODULE_ROOT / "data" / "factory"
PANEL = FACTORY / "arena_panel.parquet"
MARKET = FACTORY / "arena_market.parquet"
FRED = MODULE_ROOT / "data" / "macro" / "fred_macro_snap20260726.parquet"
AEGIS_FINANCE = Path(r"C:\Users\mrthn\aegis-finance")

# ── frozen constants (prereg §3-§5) ────────────────────────────────────────
SEED = 20260812
BURN_IN = 36                 # decision dates held at the frozen default
MIN_IN_STATE = 12            # months required before an arm may condition
K_PRIMARY = 20
K_GRID = (20, 40)
WMAX = {20: 0.10, 40: 0.05}
COST_MULTS = (0.0, 1.0, 2.0)
N_SHUFFLE_SEEDS = 20
BOCPD_HAZARD = 1.0 / 24.0    # 2-year expected regime, declared, never tuned
BOCPD_AGE_SPLIT = 6.0        # months
#: DECLARED, NEVER FITTED. The first build passed the FULL-SAMPLE variance of
#: the monthly market series as the BOCPD prior — a full-sample statistic used
#: to label every month, i.e. exactly the look-ahead §6 exists to catch. The
#: decision-level perturbation proof caught it (S_BOCPD2 moved the D2 blend at
#: 3/3 probes with its own label unchanged: the corrupted future changed PAST
#: labels, and the conditioning SET is built from past labels). Replaced by a
#: constant: 5% monthly sd ~ 17.3% annualised, the order of magnitude of US
#: equity vol, chosen once and never tuned against any result.
BOCPD_VAR_PRIOR = 0.05 ** 2
SOFTMAX_TAU = 1.0            # frozen
KMEANS_K = 3
HMM_REFIT_YEARS = 1

#: the six base signals. (id, panel column, +1 = high is good)
SIGNALS = (("MOM", "mom_12_1", 1.0),
           ("REV", "rev_score", 1.0),
           ("SUE", "sue", 1.0),
           ("TGT", "tgt_upside", 1.0),
           ("LOWVOL", "vol_252", -1.0),
           ("NMAX", "max5", -1.0))
SIG_IDS = tuple(s[0] for s in SIGNALS)

#: the five risk schemes, applied INSIDE a selection held fixed
RISK_IDS = ("EW", "IVOL", "IVAR", "MINVAR1F", "IBETA")

STATE_CLASS = {
    "S_NONE": "CONTROL",
    "S_VOL3": "observable", "S_DD2": "observable", "S_TREND2": "observable",
    "S_YC2": "observable_snapshot_vintage", "S_BREADTH3": "observable",
    "S_KMEANS3": "clustering", "S_BOCPD2": "changepoint",
    "S_HMM2": "HMM_CONTROL_NOT_TRUSTED", "S_HMM3": "HMM_CONTROL_NOT_TRUSTED",
    "S_SUP2": "supervised",
    "S_SUPSIG6": "supervised",
    "S_SHUFFLE3": "PLACEBO",
    "S_ORACLE2": "IMPOSSIBLE", "S_LEAKY3": "TRIPWIRE_LOOKAHEAD",
}
REAL_STATES = tuple(k for k, v in STATE_CLASS.items()
                    if v not in ("IMPOSSIBLE", "TRIPWIRE_LOOKAHEAD"))
LEAKY_STATES = ("S_ORACLE2", "S_LEAKY3")


# ══════════════════════════════════════════════════════════════════════════
# the bed
# ══════════════════════════════════════════════════════════════════════════
def zscore(v: np.ndarray) -> np.ndarray:
    """Cross-sectional rank-normal score; NaN -> 0 (the cross-sectional median).

    Ranks, not levels: one 4000% analyst target must not define the scale for
    1,499 other names. Copied in behaviour from `arena_systems.z`.
    """
    from scipy.stats import norm
    out = np.zeros(len(v), dtype="float64")
    ok = np.isfinite(v)
    n = int(ok.sum())
    if n < 3:
        return out
    r = pd.Series(v[ok]).rank(method="average").to_numpy() / (n + 1.0)
    out[ok] = norm.ppf(r)
    return out


def load_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """The three raw surfaces, loaded once so the tripwire can corrupt them.

    Split out of `load_bed` by the runner: the perturbation proof has to feed
    CORRUPTED frames through the identical construction path. A proof that runs
    a second, tidier code path proves something about the second path.
    """
    panel = pd.read_parquet(PANEL)
    mkt = pd.read_parquet(MARKET)
    d = pd.read_parquet(FRED, columns=["DGS10", "DGS2"])
    yc = (pd.to_numeric(d["DGS10"], errors="coerce")
          - pd.to_numeric(d["DGS2"], errors="coerce")).dropna()
    yc.index = pd.to_datetime(yc.index)
    return panel, mkt, yc


def load_bed(panel: pd.DataFrame | None = None,
             mkt: pd.DataFrame | None = None) -> dict:
    if panel is None:
        panel = pd.read_parquet(PANEL)
    if mkt is None:
        mkt = pd.read_parquet(MARKET)
    dates_k = sorted(int(k) for k in panel["date_ix"].unique())
    by_date = {int(k): g.set_index("permno")
               for k, g in panel.groupby("date_ix")}
    Z, FWD, BREADTH = {}, {}, {}
    for k in dates_k:
        d = by_date[k]
        z = np.empty((len(d), len(SIGNALS)))
        for j, (_, col, sgn) in enumerate(SIGNALS):
            z[:, j] = zscore(sgn * pd.to_numeric(d[col], errors="coerce")
                             .to_numpy(dtype="float64"))
        Z[k] = z
        FWD[k] = pd.to_numeric(d["fwd_ret_1m"], errors="coerce").to_numpy(float)
        m = pd.to_numeric(d["mom_12_1"], errors="coerce").to_numpy(float)
        BREADTH[k] = float(np.nanmean(m > 0))
    return {"panel": panel, "mkt": mkt.set_index("date_ix"),
            "dates": pd.DatetimeIndex(mkt.sort_values("date_ix")["date"]),
            "dates_k": dates_k, "by_date": by_date, "Z": Z, "FWD": FWD,
            "breadth": BREADTH}


# ══════════════════════════════════════════════════════════════════════════
# the option sets (prereg §4)
# ══════════════════════════════════════════════════════════════════════════
def _pick(score: np.ndarray, K: int) -> np.ndarray:
    """Indices of the top-K finite scores."""
    s = np.where(np.isfinite(score), score, -np.inf)
    K = min(K, int(np.isfinite(s).sum()))
    if K <= 0:
        return np.array([], dtype=int)
    idx = np.argpartition(-s, K - 1)[:K]
    return idx[np.argsort(-s[idx])]


def _ew(n: int) -> np.ndarray:
    return np.full(n, 1.0 / n) if n else np.array([])


def risk_weights(scheme: str, d: pd.DataFrame, sel: np.ndarray,
                 mkt_var: float) -> np.ndarray:
    """Weights inside a FIXED selection. Long-only, sums to 1."""
    n = len(sel)
    if n == 0:
        return np.array([])
    vol = pd.to_numeric(d["vol_252"], errors="coerce").to_numpy(float)[sel]
    ivol = pd.to_numeric(d["ivol_252"], errors="coerce").to_numpy(float)[sel]
    beta = pd.to_numeric(d["beta_252"], errors="coerce").to_numpy(float)[sel]
    vol = np.where(np.isfinite(vol) & (vol > 1e-4), vol, np.nanmedian(vol))
    ivol = np.where(np.isfinite(ivol) & (ivol > 1e-4), ivol, np.nanmedian(ivol))
    beta = np.where(np.isfinite(beta), beta, 1.0)
    if scheme == "EW":
        w = _ew(n)
    elif scheme == "IVOL":
        w = 1.0 / vol
    elif scheme == "IVAR":
        w = 1.0 / vol ** 2
    elif scheme == "IBETA":
        w = 1.0 / np.maximum(beta, 0.2)
    elif scheme == "MINVAR1F":
        # Sigma = mkt_var*bb' + diag(ivol^2); w ∝ Sigma^-1 1 by Sherman-Morrison
        dinv = 1.0 / ivol ** 2
        a = float(beta @ (dinv * beta))
        b = float(dinv @ beta)
        w = dinv - mkt_var * dinv * beta * b / (1.0 + mkt_var * a)
        w = np.clip(w, 0.0, None)          # long-only
        if w.sum() <= 0:
            w = _ew(n)
    else:
        raise ValueError(scheme)
    w = np.clip(w, 0.0, None)
    return w / w.sum()


def precompute_options(bed: dict) -> dict:
    """Gross forward return of every option at every month, path-independent.

    The trailing score a conditioner reads must not depend on which arm is
    asking, so it is the GROSS return of the option's own portfolio. Cost is
    path-dependent (it depends on last month's holdings) and is charged in the
    simulator, never in the score.
    """
    dates_k = bed["dates_k"]
    nK = len(dates_k)
    out = {"sel_ret": {}, "sel_idx": {}, "risk_ret": {}, "risk_w": {},
           "comp_idx": {}, "ic": np.full((nK, len(SIGNALS)), np.nan)}
    for K in K_GRID:
        out["sel_ret"][K] = np.full((nK, len(SIGNALS)), np.nan)
        out["sel_idx"][K] = {}
        out["risk_ret"][K] = np.full((nK, len(RISK_IDS)), np.nan)
        out["risk_w"][K] = {}
        out["comp_idx"][K] = {}
    from scipy.stats import spearmanr
    for k in dates_k:
        d = bed["by_date"][k]
        z = bed["Z"][k]
        fwd = bed["FWD"][k]
        mv = float(bed["mkt"].loc[k, "mkt_vol_252"]) ** 2
        for j in range(len(SIGNALS)):
            ok = np.isfinite(fwd)
            if ok.sum() > 30:
                out["ic"][k, j] = float(spearmanr(z[ok, j], fwd[ok]).statistic)
        for K in K_GRID:
            for j in range(len(SIGNALS)):
                sel = _pick(z[:, j], K)
                out["sel_idx"][K][(k, j)] = sel
                out["sel_ret"][K][k, j] = float(np.nanmean(fwd[sel])) \
                    if len(sel) else np.nan
            comp = z.mean(axis=1)
            csel = _pick(comp, K)
            out["comp_idx"][K][k] = csel
            for j, scheme in enumerate(RISK_IDS):
                w = risk_weights(scheme, d, csel, mv)
                out["risk_w"][K][(k, j)] = w
                r = fwd[csel]
                good = np.isfinite(r)
                out["risk_ret"][K][k, j] = float((w[good] * r[good]).sum()
                                                 / max(w[good].sum(), 1e-12))
    return out


# ══════════════════════════════════════════════════════════════════════════
# the state definitions (prereg §5). label(k) uses rows <= k. Twice-declared
# exceptions: S_ORACLE2 and S_LEAKY3, which exist to be caught.
# ══════════════════════════════════════════════════════════════════════════
def state_features(bed: dict) -> pd.DataFrame:
    m = bed["mkt"]
    f = pd.DataFrame(index=m.index)
    f["vol63"] = m["mkt_vol_63"]
    f["volratio"] = m["mkt_vol_63"] / m["mkt_vol_252"]
    f["ret252"] = m["mkt_ret_252"]
    f["dd252"] = m["mkt_dd_252"]
    f["breadth"] = pd.Series(bed["breadth"])
    return f


def _expanding_terciles(x: np.ndarray, min_obs: int = 24) -> np.ndarray:
    """Label k from the empirical terciles of x[:k+1]. Strictly PIT."""
    out = np.ones(len(x), dtype=int)
    for k in range(len(x)):
        h = x[:k + 1]
        h = h[np.isfinite(h)]
        if len(h) < min_obs or not np.isfinite(x[k]):
            out[k] = 1
            continue
        q1, q2 = np.quantile(h, [1 / 3, 2 / 3])
        out[k] = 0 if x[k] <= q1 else (1 if x[k] <= q2 else 2)
    return out


def load_yield_curve(dates: pd.DatetimeIndex,
                     raw: pd.Series | None = None) -> pd.Series:
    """DGS10 - DGS2 as of each decision date. SNAPSHOT VINTAGE, declared.

    ffill from the last quote AT OR BEFORE the decision date, so a corrupted
    future quote cannot reach back — which is what the tripwire checks.
    """
    if raw is None:
        d = pd.read_parquet(FRED, columns=["DGS10", "DGS2"])
        raw = (pd.to_numeric(d["DGS10"], errors="coerce")
               - pd.to_numeric(d["DGS2"], errors="coerce")).dropna()
        raw.index = pd.to_datetime(raw.index)
    s = raw.sort_index()
    return s.reindex(s.index.union(dates)).ffill().reindex(dates)


def bocpd_age(monthly_ret: np.ndarray) -> np.ndarray:
    """Expected run length at each month from the Adams-MacKay recursion.

    IMPORTED, not reimplemented: `aegis-finance/backend/services/
    anomaly_detector.BayesianChangepoint`. The recursion is causal — the value
    at t is a function of x[:t+1] — and the perturbation proof checks that
    claim rather than trusting it.
    """
    sys.path.insert(0, str(AEGIS_FINANCE))
    from backend.services.anomaly_detector import BayesianChangepoint
    bc = BayesianChangepoint(hazard_rate=BOCPD_HAZARD, mu_prior=0.0,
                             var_prior=BOCPD_VAR_PRIOR)
    s = pd.Series(monthly_ret)
    res = bc.detect(s, window=0)
    return res["regime_age"].to_numpy(float)


def _canonical_hmm_states(model, X: np.ndarray, n: int) -> np.ndarray:
    """Sort HMM states by mean so labels are comparable across refits.

    Without this, a refit relabels the states and the conditioning set becomes
    a random partition — which is exactly the placebo, arriving by accident.
    """
    order = np.argsort(model.means_.ravel())
    remap = np.empty(n, dtype=int)
    remap[order] = np.arange(n)
    post = model.predict_proba(X)
    return remap[post[-1].argmax()]


def build_states(bed: dict, feats: pd.DataFrame, opts: dict,
                 yc_raw: pd.Series | None = None) -> dict:
    """All fourteen label sequences. Every one is an int array over dates_k."""
    ks = np.array(bed["dates_k"])
    n = len(ks)
    mkt = bed["mkt"]
    out: dict[str, np.ndarray] = {}

    out["S_NONE"] = np.zeros(n, dtype=int)
    out["S_VOL3"] = _expanding_terciles(feats["vol63"].to_numpy(float))
    out["S_DD2"] = (feats["dd252"].to_numpy(float) <= -0.10).astype(int)
    out["S_TREND2"] = (feats["ret252"].to_numpy(float) > 0).astype(int)
    yc = load_yield_curve(bed["dates"], yc_raw).to_numpy(float)
    out["S_YC2"] = np.where(np.isfinite(yc), (yc > 0).astype(int), 1)
    out["S_BREADTH3"] = _expanding_terciles(feats["breadth"].to_numpy(float))

    # ── clustering: refit annually on rows <= k, predict row k ──────────────
    from sklearn.cluster import KMeans
    X = feats[["vol63", "volratio", "ret252", "dd252", "breadth"]].to_numpy(float)
    X = np.where(np.isfinite(X), X, 0.0)
    lab = np.zeros(n, dtype=int)
    model = mu = sd = None
    years = bed["dates"].year.to_numpy()
    last_fit_year = None
    for k in range(n):
        if k < BURN_IN:
            lab[k] = 0
            continue
        if last_fit_year is None or years[k] != last_fit_year:
            tr = X[:k + 1]
            mu, sd = tr.mean(0), tr.std(0) + 1e-12
            model = KMeans(KMEANS_K, n_init=10, random_state=SEED).fit(
                (tr - mu) / sd)
            # canonical order by cluster mean vol, so refits stay comparable
            order = np.argsort(model.cluster_centers_[:, 0])
            remap = np.empty(KMEANS_K, dtype=int)
            remap[order] = np.arange(KMEANS_K)
            model._remap = remap
            last_fit_year = years[k]
        lab[k] = int(model._remap[model.predict(((X[k] - mu) / sd)[None, :])[0]])
    out["S_KMEANS3"] = lab

    # ── change point ───────────────────────────────────────────────────────
    mret = mkt["mkt_fwd_1m"].to_numpy(float)
    # the return REALISED by month k is the forward return of month k-1
    realised = np.r_[0.0, mret[:-1]]
    age = bocpd_age(realised)
    out["S_BOCPD2"] = (age > BOCPD_AGE_SPLIT).astype(int)

    # ── HMM: the A2 CONTROL. Refit annually on rows <= k, FILTERED state ────
    from hmmlearn.hmm import GaussianHMM
    for ns in (2, 3):
        lab = np.zeros(n, dtype=int)
        model = None
        last_fit_year = None
        for k in range(n):
            if k < BURN_IN:
                lab[k] = 0
                continue
            Xh = realised[:k + 1].reshape(-1, 1)
            if last_fit_year is None or years[k] != last_fit_year:
                try:
                    model = GaussianHMM(n_components=ns, covariance_type="diag",
                                        n_iter=200, random_state=SEED).fit(Xh)
                except Exception:
                    model = None
                last_fit_year = years[k]
            lab[k] = 0 if model is None else int(
                _canonical_hmm_states(model, Xh, ns))
        out[f"S_HMM{ns}"] = lab

    # ── supervised, TWO of them, and the reason is a prereg deviation ──────
    # Prereg §5 defines S_SUP2 as "LightGBM trained on state features to
    # predict WHICH BASE SIGNAL WINS next month". The inherited build predicts
    # the SIGN OF NEXT MONTH'S MARKET RETURN instead — the observable twin of
    # S_ORACLE2. That is a different state and the deviation is recorded, not
    # tidied: the market-sign version is KEPT (it is the honest observable
    # counterpart of the impossible arm) and the PRE-REGISTERED definition is
    # ALSO built, as S_SUPSIG6, so the registered arm actually runs.
    out["S_SUP2"] = _supervised_state(X, mret, years)
    out["S_SUPSIG6"] = _supervised_winner_state(
        X, opts["sel_ret"][K_PRIMARY], years)

    # ── PLACEBO: S_VOL3's marginals and block persistence, permuted in time ─
    out["S_SHUFFLE3"] = shuffled_state(out["S_VOL3"], seed=0)

    # ── the two arms that MUST be caught ───────────────────────────────────
    out["S_ORACLE2"] = (mret > 0).astype(int)          # next month's return
    v = feats["vol63"].to_numpy(float)
    q1, q2 = np.nanquantile(v, [1 / 3, 2 / 3])         # FULL SAMPLE. Leaky.
    out["S_LEAKY3"] = np.where(v <= q1, 0, np.where(v <= q2, 1, 2))
    return out


def _supervised_state(X: np.ndarray, mret: np.ndarray,
                      years: np.ndarray, purge: int = 2) -> np.ndarray:
    """LightGBM sign-of-next-month-market, expanding walk-forward, OOF only.

    The observable twin of S_ORACLE2: same state definition, one learned and
    one known. A 2-month purge is longer than the 1-month label horizon, so a
    training row's label cannot overlap the prediction date.
    """
    import lightgbm as lgb
    n = len(mret)
    lab = np.zeros(n, dtype=int)
    y = (mret > 0).astype(int)
    model = None
    last_fit_year = None
    for k in range(n):
        if k < BURN_IN:
            continue
        if last_fit_year is None or years[k] != last_fit_year:
            hi = k - purge
            if hi >= 24:
                model = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.03,
                                           num_leaves=7, min_child_samples=20,
                                           random_state=SEED, verbose=-1)
                model.fit(X[:hi], y[:hi])
            last_fit_year = years[k]
        if model is not None:
            lab[k] = int(model.predict(X[k][None, :])[0])
    return lab


def _supervised_winner_state(X: np.ndarray, sel_ret: np.ndarray,
                             years: np.ndarray, purge: int = 2) -> np.ndarray:
    """The PRE-REGISTERED S_SUP2: predicted winner among the six base signals.

    y[m] = argmax_j (option j's realised return over month m), known at m+1.
    Trained on rows <= k-purge only, refit annually, out-of-fold by
    construction. Six states, so the 12-month in-state minimum bites hard and
    the fallback rate is the number that says whether this arm conditioned at
    all.
    """
    import lightgbm as lgb
    n = len(years)
    lab = np.zeros(n, dtype=int)
    y = np.where(np.isfinite(sel_ret).any(axis=1),
                 np.nanargmax(np.where(np.isfinite(sel_ret), sel_ret, -np.inf),
                              axis=1), 0)
    model = None
    last_fit_year = None
    for k in range(n):
        if k < BURN_IN:
            continue
        if last_fit_year is None or years[k] != last_fit_year:
            hi = k - purge
            if hi >= 24 and len(np.unique(y[:hi])) > 1:
                model = lgb.LGBMClassifier(n_estimators=200,
                                           learning_rate=0.03, num_leaves=7,
                                           min_child_samples=20,
                                           random_state=SEED, verbose=-1)
                model.fit(X[:hi], y[:hi])
            last_fit_year = years[k]
        if model is not None:
            lab[k] = int(model.predict(X[k][None, :])[0])
    return lab


def shuffled_state(base: np.ndarray, seed: int) -> np.ndarray:
    """Circular block permutation, block = 12 months.

    Preserves the marginal frequencies and most of the persistence of the real
    label sequence, and destroys only its alignment with the market. If a real
    state cannot beat this, "conditioning" is a partition of the trailing
    window, not information.
    """
    rng = np.random.default_rng(SEED + 1000 + seed)
    n = len(base)
    blocks = [base[i:i + 12] for i in range(0, n, 12)]
    order = rng.permutation(len(blocks))
    out = np.concatenate([blocks[i] for i in order])
    return out[:n]


# ══════════════════════════════════════════════════════════════════════════
# the conditioner — identical for every state, so the state is the only
# thing that varies (prereg §4)
# ══════════════════════════════════════════════════════════════════════════
def conditioned_choice(labels: np.ndarray, score: np.ndarray, k: int,
                       ) -> tuple[int | None, str]:
    """argmax over the conditioning set, with the declared fallback ladder.

    `score[m, o]` is option o's realised outcome in month m; only m <= k-1 is
    available at k. Returns (option, how) where `how` records whether the arm
    actually conditioned — an arm that never conditioned is not evidence about
    conditioning, so the rate is reported.
    """
    if k < BURN_IN:
        return None, "burn_in"
    past = np.arange(k)
    sel = past[labels[past] == labels[k]]
    if len(sel) >= MIN_IN_STATE:
        v = np.nanmean(score[sel], axis=0)
        if np.isfinite(v).any():
            return int(np.nanargmax(v)), "conditioned"
    v = np.nanmean(score[past], axis=0)
    if len(past) >= MIN_IN_STATE and np.isfinite(v).any():
        return int(np.nanargmax(v)), "fallback_uncond"
    return None, "fallback_default"


def conditioned_blend(labels: np.ndarray, ic: np.ndarray, k: int
                      ) -> tuple[np.ndarray | None, str]:
    """Softmax blend over the six signals' trailing rank-IC. tau frozen at 1.0."""
    if k < BURN_IN:
        return None, "burn_in"
    past = np.arange(k)
    sel = past[labels[past] == labels[k]]
    how = "conditioned"
    if len(sel) < MIN_IN_STATE:
        sel, how = past, "fallback_uncond"
    if len(sel) < MIN_IN_STATE:
        return None, "fallback_default"
    v = np.nanmean(ic[sel], axis=0)
    if not np.isfinite(v).all():
        v = np.where(np.isfinite(v), v, np.nanmin(v[np.isfinite(v)])
                     if np.isfinite(v).any() else 0.0)
    sd = v.std()
    zz = (v - v.mean()) / (sd if sd > 1e-12 else 1.0)
    e = np.exp(zz / SOFTMAX_TAU)
    return e / e.sum(), how
