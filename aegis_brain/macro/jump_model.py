"""Statistical jump model (2-state) — Bemporad et al. 2018 / Nystrup et al.
lineage, tactical application per Shu-Yu-Mulvey (J. Asset Mgmt 2024).

Coordinate descent between (a) centroid update and (b) Viterbi-style DP
assignment with an explicit per-switch penalty lambda that forces regime
persistence — the amendment adopted at AI-panel round 4 over hmmlearn HMMs
(whipsaw). Causal use: fit on data through month-end m-1, filter FORWARD
only (V[t] depends on <=t) for days of month m.
"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans


def _dp(cost: np.ndarray, lam: float) -> tuple[np.ndarray, np.ndarray]:
    """Forward DP. Returns (V values TxK, backpointers TxK)."""
    T, K = cost.shape
    V = np.zeros((T, K))
    ptr = np.zeros((T, K), dtype=int)
    V[0] = cost[0]
    for t in range(1, T):
        for k in range(K):
            prev = V[t - 1] + lam * (np.arange(K) != k)
            j = int(prev.argmin())
            V[t, k] = cost[t, k] + prev[j]
            ptr[t, k] = j
    return V, ptr


def _assign_smoothed(X: np.ndarray, mu: np.ndarray, lam: float) -> np.ndarray:
    cost = ((X[:, None, :] - mu[None, :, :]) ** 2).sum(-1)
    V, ptr = _dp(cost, lam)
    s = np.zeros(len(X), dtype=int)
    s[-1] = int(V[-1].argmin())
    for t in range(len(X) - 1, 0, -1):
        s[t - 1] = ptr[t, s[t]]
    return s


def fit_jm(X: np.ndarray, lam: float, n_iter: int = 10, seed: int = 0) -> np.ndarray:
    """Fit 2-state centroids on X (T x d, standardized). Returns mu (2 x d)."""
    mu = KMeans(2, n_init=10, random_state=seed).fit(X).cluster_centers_
    prev: np.ndarray | None = None
    for _ in range(n_iter):
        s = _assign_smoothed(X, mu, lam)
        if prev is not None and (s == prev).all():
            break
        prev = s
        for k in (0, 1):
            if (s == k).any():
                mu[k] = X[s == k].mean(axis=0)
    return mu


def filter_states(X: np.ndarray, mu: np.ndarray, lam: float) -> np.ndarray:
    """CAUSAL filtered state path: argmin_k V[t,k] from the forward DP only —
    state at t uses information <= t exclusively (no backward pass)."""
    cost = ((X[:, None, :] - mu[None, :, :]) ** 2).sum(-1)
    V, _ = _dp(cost, lam)
    return V.argmin(axis=1)
