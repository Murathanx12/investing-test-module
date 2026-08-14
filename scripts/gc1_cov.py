"""GRAPH-COVARIANCE-1 — the covariance and portfolio primitives.

Everything in this module is a PURE FUNCTION of arrays. No file reads, no
network, no configuration lookups at call time. That is deliberate: the whole
decision in this trial rests on `model_semantic` and `model_numeric` receiving
IDENTICAL treatment everywhere except the feature block, and the cheapest way to
guarantee that is to have exactly one implementation of each step, called the
same way for every arm, testable offline against a planted answer.

The three primitives:

  repair_correlation   a ridge predicts each entry independently, so a predicted
                       matrix is not PSD. Symmetrise, unit diagonal, clip
                       eigenvalues, rescale. Applied to EVERY arm.
  gmv_weights          global minimum variance, fully invested, unconstrained
                       sign. Closed form.
  gmv_long_only        the same objective under 0 <= w <= cap, solved by
                       accelerated projected gradient onto the capped simplex.
                       Every arm gets the same iteration budget, so an arm
                       cannot win by being solved harder.

WHY REALISED MINIMUM-VARIANCE VOLATILITY IS THE LOSS FUNCTION
=============================================================
It is the standard criterion for covariance quality (Ledoit-Wolf; Engle-
Colacito) and it contains NO return forecast. Given two covariance estimates,
the one whose minimum-variance portfolio realises lower variance out of sample
is the better estimate, and no other property of the estimator enters. That is
the entire reason this trial can make a portfolio-level claim without ever
predicting a return.
"""

from __future__ import annotations

import numpy as np


# ── matrix repair ───────────────────────────────────────────────────────────

def repair_correlation(P: np.ndarray, eig_floor_rel: float = 0.10,
                       shrink: float = 0.0,
                       corr_clip: float = 0.99) -> tuple[np.ndarray, dict]:
    """Nearest usable correlation matrix, by the same route for every arm.

    Steps, in order: clip entries to `[-corr_clip, corr_clip]`; symmetrise;
    force a unit diagonal; optionally shrink toward the identity; floor the
    eigenvalues; rescale to a unit diagonal.

    THE FLOOR IS RELATIVE, AND THAT IS THE WHOLE POINT
    --------------------------------------------------
    A correlation matrix has mean eigenvalue exactly 1, so `eig_floor_rel` reads
    directly as a fraction of the average eigenvalue. An ABSOLUTE floor near
    zero does not repair an indefinite matrix — it manufactures directions of
    almost-zero variance, and a minimum-variance solve is precisely the machine
    that finds such directions and levers into them without bound. Measured on
    this trial's own first run at a 1e-8 floor: predicted portfolio volatility
    0.13% annualised against 2.7% realised, a calibration ratio of 4,519, and a
    condition number of 7.1e8. The repair ran green and destroyed the object.

    Entry clipping exists for the same reason at one level up: the ridge that
    predicts these entries is unconstrained and returned correlations as large
    as 1.0119, which no correlation matrix may contain.

    Returns the repaired matrix and a diagnostics dict. Diagnostics are
    descriptive; the only one any rule reads is the calibration void assertion,
    which lives in the grading script.
    """
    A = np.asarray(P, dtype=np.float64)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError(f"expected a square matrix, got {A.shape}")
    n = A.shape[0]
    # Counted OFF the diagonal only: the diagonal is 1.0 by definition and
    # exceeds any clip, so counting it would report every matrix as damaged and
    # the diagnostic would carry no information.
    n_out_of_range = int((np.abs(A) > corr_clip).sum()
                         - (np.abs(np.diag(A)) > corr_clip).sum())
    A = np.clip(A, -corr_clip, corr_clip)
    A = 0.5 * (A + A.T)
    np.fill_diagonal(A, 1.0)
    if shrink:
        A = (1.0 - shrink) * A + shrink * np.eye(n)
        np.fill_diagonal(A, 1.0)

    w, V = np.linalg.eigh(A)
    min_eig_raw = float(w.min())
    floor = float(eig_floor_rel)          # mean eigenvalue of a corr matrix = 1
    n_clipped = int((w < floor).sum())
    clipped_mass = float(np.clip(floor - w, 0.0, None).sum())
    w = np.clip(w, floor, None)
    B = (V * w) @ V.T
    B = 0.5 * (B + B.T)

    d = np.sqrt(np.clip(np.diag(B), 1e-12, None))
    B = B / np.outer(d, d)
    np.fill_diagonal(B, 1.0)

    w2 = np.linalg.eigvalsh(B)
    return B, {
        "min_eig_raw": min_eig_raw,
        "min_eig_repaired": float(w2.min()),
        "eig_floor_used": floor,
        "n_eigs_clipped": n_clipped,
        "clipped_mass": clipped_mass,
        "n_entries_out_of_range": n_out_of_range,
        "cond": float(w2.max() / max(w2.min(), 1e-300)),
        "n": n,
    }


def corr_to_cov(P: np.ndarray, vol: np.ndarray) -> np.ndarray:
    """`D P D`. The volatility block is identical across arms by construction —
    it is a different estimation problem and holding it fixed is what makes the
    measured difference attributable to correlation structure alone."""
    v = np.asarray(vol, dtype=np.float64)
    if v.ndim != 1 or v.shape[0] != P.shape[0]:
        raise ValueError(f"vol {v.shape} does not match P {P.shape}")
    return np.asarray(P, dtype=np.float64) * np.outer(v, v)


# ── portfolios ──────────────────────────────────────────────────────────────

def gmv_weights(Sigma: np.ndarray) -> np.ndarray:
    """Global minimum variance, fully invested, no sign constraint.

    `w = S^-1 1 / (1' S^-1 1)`. Solved rather than inverted. In residual space
    this is a real holdable portfolio: it is market- and sector-neutral by
    construction, so `w' r_resid` is exactly what it earns.
    """
    S = np.asarray(Sigma, dtype=np.float64)
    n = S.shape[0]
    one = np.ones(n)
    try:
        x = np.linalg.solve(S, one)
    except np.linalg.LinAlgError:
        x = np.linalg.lstsq(S, one, rcond=None)[0]
    denom = float(one @ x)
    if not np.isfinite(denom) or abs(denom) < 1e-300:
        return np.full(n, 1.0 / n)
    return x / denom


def project_capped_simplex(v: np.ndarray, cap: float,
                           tol: float = 1e-12) -> np.ndarray:
    """Euclidean projection onto `{w : sum(w) = 1, 0 <= w <= cap}`.

    `w_i(lam) = clip(v_i - lam, 0, cap)` is non-increasing in `lam`, so the
    unique `lam` with `sum(w) = 1` is found by bisection. Exact to `tol`, and
    deterministic — no arm can get a different projection than another.

    Raises if the box cannot contain a unit sum, because silently returning
    something that does not sum to one would make every downstream realised
    variance wrong in a way that looks like a result.
    """
    v = np.asarray(v, dtype=np.float64)
    n = v.size
    if cap * n < 1.0 - 1e-12:
        raise ValueError(f"cap {cap} x n {n} = {cap * n} cannot reach sum 1")
    lo, hi = float(v.min() - 1.0), float(v.max())
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        s = float(np.clip(v - mid, 0.0, cap).sum())
        if abs(s - 1.0) < tol:
            break
        if s > 1.0:
            lo = mid
        else:
            hi = mid
    return np.clip(v - 0.5 * (lo + hi), 0.0, cap)


def gmv_long_only(Sigma: np.ndarray, cap: float, max_iters: int = 5000,
                  tol: float = 1e-10) -> np.ndarray:
    """Minimum variance under `sum(w) = 1, 0 <= w <= cap`, by FISTA.

    A convex QP on a convex set, so accelerated projected gradient converges to
    the global optimum; the step is `1/L` with `L` the largest eigenvalue of
    `Sigma`. The iteration budget is FIXED and shared by every arm — an arm must
    not be able to win by being solved harder — and the achieved objective is
    returned to the caller through `gmv_long_only_report` when that matters.
    """
    S = np.asarray(Sigma, dtype=np.float64)
    n = S.shape[0]
    L = float(np.linalg.eigvalsh(S).max())
    if not np.isfinite(L) or L <= 0:
        return np.full(n, 1.0 / n)
    step = 1.0 / L

    w = project_capped_simplex(np.full(n, 1.0 / n), cap)
    y, t_k = w.copy(), 1.0
    for _ in range(max_iters):
        g = S @ y
        w_new = project_capped_simplex(y - step * g, cap)
        t_next = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * t_k * t_k))
        y = w_new + ((t_k - 1.0) / t_next) * (w_new - w)
        shift = float(np.abs(w_new - w).max())
        w, t_k = w_new, t_next
        if shift < tol:
            break
    return w


# ── realised outcomes ───────────────────────────────────────────────────────

def realised_vol(R: np.ndarray, w: np.ndarray, annualise: int = 252) -> float:
    """Annualised realised volatility of a FIXED weight vector over `R`.

    Weights are set at `t` and held: this is the out-of-sample realised risk of
    a decision, not a rebalanced simulation. Rows with any missing return among
    the held names are dropped and the count is the caller's to check.
    """
    R = np.asarray(R, dtype=np.float64)
    w = np.asarray(w, dtype=np.float64)
    p = R @ w
    p = p[np.isfinite(p)]
    if p.size < 3:
        return float("nan")
    return float(p.std(ddof=1) * np.sqrt(annualise))


def realised_max_drawdown(R: np.ndarray, w: np.ndarray) -> float:
    """Max drawdown of the held portfolio's compounded path over the window.

    Reported, never deciding — it is here because a covariance estimate that
    lowers variance while deepening drawdown is worth seeing, not because any
    verdict reads it.
    """
    R = np.asarray(R, dtype=np.float64)
    p = R @ np.asarray(w, dtype=np.float64)
    p = p[np.isfinite(p)]
    if p.size < 3:
        return float("nan")
    nav = np.cumprod(1.0 + p)
    return float((nav / np.maximum.accumulate(nav) - 1.0).min())


def predicted_vol(Sigma: np.ndarray, w: np.ndarray,
                  annualise: int = 252) -> float:
    """What the matrix SAID the portfolio's volatility would be.

    Paired with `realised_vol` this gives the calibration ratio: a matrix that
    calls a single economic bet "diversified" prints a ratio above one.
    """
    w = np.asarray(w, dtype=np.float64)
    v = float(w @ np.asarray(Sigma, dtype=np.float64) @ w)
    return float(np.sqrt(max(v, 0.0)) * np.sqrt(annualise))


def effective_bets(w: np.ndarray) -> float:
    """`1 / sum(w^2)`. Reported, never deciding."""
    w = np.asarray(w, dtype=np.float64)
    s = float((w * w).sum())
    return float(1.0 / s) if s > 0 else float("nan")


# ── context-arm estimators ──────────────────────────────────────────────────

def ledoit_wolf_corr(X: np.ndarray, return_intensity: bool = False):
    """Ledoit-Wolf shrinkage of a sample correlation toward the identity.

    Context arm only. The shrinkage intensity is ESTIMATED from the data by the
    standard formula rather than chosen, which is the point of including it:
    it is what a practitioner would do with no graph at all.

    `return_intensity` exists for the tests. The intensity is the estimator's
    actual behaviour; the LEVEL of the resulting off-diagonals is not, because a
    short sample has noisier raw correlations to begin with and can end up above
    a long sample's even after being shrunk harder. Testing the level instead of
    the intensity is a real trap and this signature exists so the test does not
    fall into it.
    """
    X = np.asarray(X, dtype=np.float64)
    X = X[np.isfinite(X).all(axis=1)]
    T, n = X.shape
    if T < 3:
        return (np.eye(n), 1.0) if return_intensity else np.eye(n)
    Xc = X - X.mean(axis=0)
    sd = Xc.std(axis=0, ddof=0)
    sd[sd < 1e-12] = 1.0
    Z = Xc / sd
    S = (Z.T @ Z) / T
    F = np.eye(n)
    # pi: sum of asymptotic variances of the sample correlation entries
    Z2 = Z * Z
    pi_mat = (Z2.T @ Z2) / T - S * S
    # The diagonal is excluded from BOTH sums. Shrinking toward the identity
    # leaves the diagonal exactly where it was, so its estimation variance is
    # not part of what the intensity is trading off; pairing a full-matrix `pi`
    # with a zero-diagonal `gamma` would inflate delta for no reason.
    off = ~np.eye(n, dtype=bool)
    pi_hat = float(pi_mat[off].sum())
    gamma = float(((S - F)[off] ** 2).sum())
    if gamma <= 0:
        return (S, 0.0) if return_intensity else S
    delta = float(np.clip(pi_hat / (T * gamma), 0.0, 1.0))
    C = (1.0 - delta) * S + delta * F
    np.fill_diagonal(C, 1.0)
    return (C, delta) if return_intensity else C


def rmt_denoise_corr(C: np.ndarray, T: int) -> np.ndarray:
    """Marchenko-Pastur denoising: replace the sub-MP-edge eigenvalues by their
    common average, keep the rest, rescale to a unit diagonal.

    Context arm only. `q = n/T` fixes the MP edge; no parameter is chosen.
    """
    C = np.asarray(C, dtype=np.float64)
    n = C.shape[0]
    if T <= 1:
        return C
    q = n / float(T)
    lam_plus = (1.0 + np.sqrt(q)) ** 2
    w, V = np.linalg.eigh(C)
    noise = w < lam_plus
    if noise.any() and not noise.all():
        w = w.copy()
        w[noise] = float(w[noise].mean())
    D = (V * w) @ V.T
    D = 0.5 * (D + D.T)
    d = np.sqrt(np.clip(np.diag(D), 1e-12, None))
    D = D / np.outer(d, d)
    np.fill_diagonal(D, 1.0)
    return D
