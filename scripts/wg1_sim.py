"""WINNER-GENOME-1 — stage 3: the tournament simulator.

Vectorised over teams. Everything the 2025 Bloomberg handbook forbids is
enforced here rather than assumed: long-only, weights sum to <=1 (remainder in
cash at rf), no single position above 20%, ranked on total return over 25
trading days.
"""

from __future__ import annotations

import numpy as np

CAP_EPS = 1e-9


# ── name drawing ────────────────────────────────────────────────────────
def draw_names(rng, bucket_ids, bstart, bcount, kmask):
    """Draw one name per active slot from that slot's bucket, without
    within-team replacement. Buckets are stored CSR-style (bstart/bcount into
    a flat array of universe positions)."""
    B, K = bucket_ids.shape
    u = rng.random((B, K))
    pos = bstart[bucket_ids] + np.minimum(
        (u * bcount[bucket_ids]).astype(np.int64),
        np.maximum(bcount[bucket_ids] - 1, 0))
    for _ in range(40):
        dup = np.zeros((B, K), dtype=bool)
        for j in range(1, K):
            dup[:, j] = (pos[:, :j] == pos[:, j:j + 1]).any(axis=1)
        dup &= kmask
        if not dup.any():
            break
        n = int(dup.sum())
        b = bucket_ids[dup]
        u2 = rng.random(n)
        pos[dup] = bstart[b] + np.minimum(
            (u2 * bcount[b]).astype(np.int64), np.maximum(bcount[b] - 1, 0))
    pos[~kmask] = bstart[0]          # parked; masked out downstream
    return pos


def flat_buckets(name_lists):
    """CSR pack a list of arrays of universe positions."""
    bcount = np.array([len(a) for a in name_lists], dtype=np.int64)
    bstart = np.concatenate([[0], np.cumsum(bcount)[:-1]]).astype(np.int64)
    bflat = (np.concatenate(name_lists) if len(name_lists)
             else np.zeros(0, dtype=np.int64)).astype(np.int64)
    return bstart, bcount, bflat


# ── weighting ───────────────────────────────────────────────────────────
def cap_project(w, kmask, cap, iters=60):
    """Water-fill a weight vector to satisfy an upper cap, mass preserved."""
    w = np.where(kmask, w, 0.0).astype(np.float64)
    for _ in range(iters):
        over = w > cap + CAP_EPS
        if not over.any():
            break
        excess = np.where(over, w - cap, 0.0).sum(axis=1)
        w = np.where(over, cap, w)
        free = kmask & ~over
        s = np.where(free, w, 0.0).sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            prop = np.where(free, w, 0.0) / np.where(s[:, None] > 0, s[:, None], 1.0)
        nfree = free.sum(axis=1)
        even = np.where(free, 1.0 / np.maximum(nfree, 1)[:, None], 0.0)
        share = np.where(s[:, None] > 0, prop, even)
        w = w + share * excess[:, None]
    return np.where(kmask, w, 0.0)


def dirichlet_weights(rng, kmask, cap):
    e = rng.exponential(size=kmask.shape) * kmask
    w = e / np.maximum(e.sum(axis=1, keepdims=True), 1e-12)
    return cap_project(w, kmask, cap)


def equal_weights(kmask):
    k = kmask.sum(axis=1)
    return np.where(kmask, 1.0 / np.maximum(k, 1)[:, None], 0.0)


def inverse_vol_weights(vol_sel, kmask, cap):
    iv = np.where(kmask, 1.0 / np.maximum(vol_sel, 1e-6), 0.0)
    w = iv / np.maximum(iv.sum(axis=1, keepdims=True), 1e-12)
    return cap_project(w, kmask, cap)


def erc_weights(cov, kmask, cap, iters=150):
    """Equal risk contribution, long-only, by the standard fixed point
    w_i <- b_i / (Sigma w)_i followed by renormalisation."""
    B, K, _ = cov.shape
    k = kmask.sum(axis=1)
    w = np.where(kmask, 1.0 / np.maximum(k, 1)[:, None], 0.0)
    b = w.copy()
    for _ in range(iters):
        mrc = np.einsum("bij,bj->bi", cov, w)
        mrc = np.where(kmask, np.maximum(mrc, 1e-12), 1.0)
        w_new = np.where(kmask, b / mrc, 0.0)
        w_new = w_new / np.maximum(w_new.sum(axis=1, keepdims=True), 1e-12)
        if np.max(np.abs(w_new - w)) < 1e-10:
            w = w_new
            break
        w = w_new
    return cap_project(w, kmask, cap)


def half_kelly_weights(cov, mu, kmask, cap, fraction=0.5, ridge=0.10):
    """f = fraction * Sigma^-1 mu, long-only, no leverage (sum <= 1, rest in
    cash), then the tournament position cap. Sigma is ridge-shrunk toward its
    own diagonal so the inverse exists for k up to 25 on 126 observations."""
    B, K, _ = cov.shape
    d = np.einsum("bii->bi", cov)
    D = np.zeros_like(cov)
    ar = np.arange(K)
    D[:, ar, ar] = d
    S = (1.0 - ridge) * cov + ridge * D
    eye = np.eye(K)[None, :, :]
    S = np.where(kmask[:, :, None] & kmask[:, None, :], S, 0.0) + \
        eye * (~kmask)[:, :, None]
    mu_ = np.where(kmask, mu, 0.0)
    try:
        f = np.linalg.solve(S, mu_[:, :, None])[:, :, 0] * fraction
    except np.linalg.LinAlgError:
        f = np.where(kmask, mu_ / np.maximum(d, 1e-8), 0.0) * fraction
    f = np.where(kmask, np.maximum(f, 0.0), 0.0)
    tot = f.sum(axis=1, keepdims=True)
    f = np.where(tot > 1.0, f / np.maximum(tot, 1e-12), f)
    return cap_project(f, kmask, cap)


# ── the path ────────────────────────────────────────────────────────────
def simulate(Rsel, w0, kmask, rebal, rf, cost_bps, rebal_every=5):
    """Return the daily NAV path, shape (B, T+1), starting at 1 - build cost.

    Rsel (B,K,T) daily total returns of each held name (0 where inactive or
    after a delisting — the delisting return itself is already in the panel).
    """
    B, K, T = Rsel.shape
    c = cost_bps / 1e4
    R = np.where(kmask[:, :, None], np.nan_to_num(Rsel), 0.0)
    invested = w0.sum(axis=1)
    nav = 1.0 - c * invested
    h = w0 * nav[:, None]
    cash = nav - h.sum(axis=1)
    path = np.empty((B, T + 1), dtype=np.float64)
    path[:, 0] = nav
    turnover = invested.copy()          # one-way traded value / NAV
    any_rebal = bool(rebal.any())
    for t in range(T):
        h = h * (1.0 + R[:, :, t])
        cash = cash * (1.0 + rf[t])
        nav = h.sum(axis=1) + cash
        if any_rebal and (t + 1) % rebal_every == 0 and t < T - 1:
            tgt = w0 * nav[:, None]
            turn = np.abs(tgt - h).sum(axis=1)
            nav2 = nav - c * turn
            newh = w0 * nav2[:, None]
            newcash = nav2 - newh.sum(axis=1)
            h = np.where(rebal[:, None], newh, h)
            cash = np.where(rebal, newcash, cash)
            turnover = turnover + np.where(rebal, turn, 0.0)
            nav = h.sum(axis=1) + cash
        path[:, t + 1] = nav
    return path, turnover


def path_stats(path):
    """Terminal return, within-window max drawdown, realised daily vol."""
    ret = path[:, -1] - 1.0
    peak = np.maximum.accumulate(path, axis=1)
    dd = (path / peak - 1.0).min(axis=1)
    r = path[:, 1:] / path[:, :-1] - 1.0
    vol = r.std(axis=1) * np.sqrt(252.0)
    return ret, dd, vol
