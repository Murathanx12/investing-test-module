"""Calibration layer — raw LLM probabilities are inputs, never truth.

Frozen defaults (R1 + §1.3.1 of the roadmap adjudication):
  * Fixed Platt slope alpha = sqrt(3) applied on LOG-ODDS from day 1. The
    documented LLM failure is a log-odds SLOPE error, which a hit-rate
    posterior cannot fix.
  * NO extremization (a = 1.0) until the sign of the correction is measured on
    our OWN resolutions. Published advice points both ways (ensembles hedge to
    0.5; single-shot news-anchored claims run overconfident) and our regime is
    the second one.
  * Clamp to [0.02, 0.98]. Never isotonic at our n.
  * Coverage/abstention is accounted explicitly, and calibration is reported
    SELECTION-ADJUSTED: the score on answered claims, printed next to the
    coverage rate, so an LLM cannot farm calibration by answering only the easy
    ones.
"""

from __future__ import annotations

import math

import numpy as np

PLATT_ALPHA = math.sqrt(3.0)
CLAMP = (0.02, 0.98)


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def platt(p: float, alpha: float = PLATT_ALPHA, beta: float = 0.0) -> float:
    """Shrink (alpha > 1) or sharpen (alpha < 1) a probability on log-odds.

    alpha = sqrt(3) shrinks toward 0.5: a stated 0.90 becomes 0.72.
    """
    z = (_logit(p) - beta) / alpha
    q = 1.0 / (1.0 + math.exp(-z))
    return min(max(q, CLAMP[0]), CLAMP[1])


def fit_platt(p: np.ndarray, y: np.ndarray, *, min_n: int = 300
              ) -> dict:
    """Refit alpha/beta once enough resolutions exist; refuse before that.

    Below `min_n` the fitted slope is noise, and a noisy calibrator is worse
    than the fixed prior slope — so this returns the frozen defaults with a
    reason rather than a fitted number.
    """
    n = len(p)
    if n < min_n:
        return {"fitted": False, "alpha": PLATT_ALPHA, "beta": 0.0, "n": n,
                "reason": f"n={n} < {min_n}: keeping the fixed alpha=sqrt(3); "
                          "a slope fitted on this little data is noise"}
    from sklearn.linear_model import LogisticRegression
    z = np.array([_logit(v) for v in p]).reshape(-1, 1)
    m = LogisticRegression(max_iter=1000).fit(z, y)
    slope = float(m.coef_[0][0])
    return {"fitted": True, "alpha": (1.0 / slope) if slope else PLATT_ALPHA,
            "beta": float(-m.intercept_[0] / slope) if slope else 0.0, "n": n}


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error over equal-width bins."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= 1.0)
        if m.sum() == 0:
            continue
        total += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(total)


def reliability(p: np.ndarray, y: np.ndarray, bins: int = 5) -> list[dict]:
    p, y = np.asarray(p, float), np.asarray(y, float)
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= 1.0)
        if m.sum() == 0:
            continue
        out.append({"bin": f"{edges[i]:.1f}-{edges[i+1]:.1f}", "n": int(m.sum()),
                    "mean_p": round(float(p[m].mean()), 3),
                    "realized": round(float(y[m].mean()), 3)})
    return out


def report(p_raw, y, *, n_abstain: int = 0, alpha: float = PLATT_ALPHA) -> dict:
    """Selection-adjusted calibration report for one arm / claim class."""
    p_raw = np.asarray(p_raw, float)
    y = np.asarray(y, int)
    n_answered = len(p_raw)
    n_total = n_answered + n_abstain
    p_cal = np.array([platt(v, alpha) for v in p_raw])
    return {
        "coverage": round(n_answered / n_total, 3) if n_total else None,
        "n_answered": n_answered, "n_abstain": n_abstain,
        "raw": {"brier": round(brier(p_raw, y), 4),
                "log_loss": round(log_loss(p_raw, y), 4),
                "ece": round(ece(p_raw, y), 4),
                "mean_p": round(float(p_raw.mean()), 3),
                "realized_rate": round(float(y.mean()), 3)},
        "calibrated": {"brier": round(brier(p_cal, y), 4),
                       "log_loss": round(log_loss(p_cal, y), 4),
                       "ece": round(ece(p_cal, y), 4),
                       "alpha": round(alpha, 4)},
        "reliability_raw": reliability(p_raw, y),
        "note": "calibration is computed on ANSWERED claims only; read it "
                "next to coverage — a high score at low coverage is claim "
                "selection, not skill",
    }
