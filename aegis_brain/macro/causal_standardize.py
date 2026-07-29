"""Causal (expanding-window) robust standardization for the analog engine.

WHY THIS EXISTS — the blocking defect it repairs
------------------------------------------------
`macro_analog.robust_z` standardizes the 15-feature descriptor panel with a
FULL-SAMPLE median/IQR computed over 2002-2026. Retrieval in that engine is
causal (candidates are strictly older than the query), but standardization is
NOT: the z-vector of a 2005 query date is expressed in units of a distribution
that includes 2026 observations. Both the query point and every library point
are moved by information that did not exist at their own timestamps, so the
metric that defines "nearest analog" is contaminated. Any scoring of the
resulting belief states is therefore not an out-of-sample statement.

`causal_robust_z` replaces the two full-sample constants (median, IQR) with
expanding-window estimates: the value at date t uses ONLY rows with index <= t.

Conventions (chosen deliberately, documented so they can be audited)
-------------------------------------------------------------------
* Expanding statistics are computed per column with pandas
  `expanding().median()` / `expanding().quantile(q)`. These skip NaN and use
  only rows up to and including the current one, which is exactly the causal
  requirement. Measured cost on the real 6179 x 15 panel is ~0.05 s total, so
  no monthly step-function approximation was needed (the fallback the brief
  allowed is not used; the exact per-row expanding estimator is).
* Burn-in is counted PER COLUMN as the expanding count of non-NaN observations
  up to and including t. A cell with fewer than `min_history_td` observations
  behind it is set to NaN. Downstream retrieval calls `z.dropna()`, so the
  effective start of the usable library is the slowest column's burn-in.
  504 trading days ~= two years of history before any scale estimate is used.
* IQR == 0 -> NaN, identical to the full-sample function's
  `iqr.replace(0, np.nan)` guard (a degenerate scale must not divide).
* At the LAST row the expanding window equals the full sample, so
  `causal_robust_z(d).iloc[-1]` coincides with `robust_z(d).iloc[-1]` up to
  floating-point accumulation. The two differ, sometimes drastically, at every
  earlier date -- that difference IS the contamination.

This module adds a new function; `macro_analog.py` is untouched and the frozen
engine keeps its declared full-sample behaviour.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CAUSAL_VERSION = "causal-robust-z-2026-07-29"
DEFAULT_MIN_HISTORY_TD = 504  # ~2 trading years before any scale is trusted


def causal_robust_z(d: pd.DataFrame,
                    min_history_td: int = DEFAULT_MIN_HISTORY_TD) -> pd.DataFrame:
    """Expanding-window robust z-score (median / IQR), strictly causal.

    Parameters
    ----------
    d
        Feature panel indexed by date (ascending). Columns are standardized
        independently. NaNs are skipped by the expanding estimators.
    min_history_td
        Minimum number of non-NaN observations (inclusive of the current row)
        a column must have accumulated before its z-value is emitted. Rows
        below that threshold are NaN (burn-in).

    Returns
    -------
    DataFrame with the same index/columns as `d`, where the value at date t is
    ``(d[t] - median(d[:t])) / IQR(d[:t])`` and no information from any row
    after t participates in the computation.
    """
    if not isinstance(d, pd.DataFrame):
        raise TypeError("causal_robust_z expects a DataFrame")
    if min_history_td < 1:
        raise ValueError("min_history_td must be >= 1")
    if not d.index.is_monotonic_increasing:
        raise ValueError("index must be sorted ascending for causal statistics")

    exp = d.expanding()
    med = exp.median()
    iqr = exp.quantile(0.75) - exp.quantile(0.25)
    iqr = iqr.mask(iqr == 0)                     # degenerate scale -> NaN

    z = (d - med) / iqr

    n_obs = d.notna().cumsum()                   # causal count of observations
    z = z.where(n_obs >= min_history_td)
    return z


def burn_in_start(d: pd.DataFrame,
                  min_history_td: int = DEFAULT_MIN_HISTORY_TD):
    """First index label at which EVERY column has cleared burn-in.

    Convenience for reporting how much library the causal rule costs.
    Returns None if no such date exists.
    """
    n_obs = d.notna().cumsum()
    ok = (n_obs >= min_history_td).all(axis=1)
    idx = ok[ok].index
    return idx[0] if len(idx) else None


def contamination_report(d: pd.DataFrame,
                         min_history_td: int = DEFAULT_MIN_HISTORY_TD) -> pd.DataFrame:
    """Per-column |causal z - full-sample z| summary over the overlapping rows.

    Descriptive only: quantifies how far the full-sample standardization moved
    each feature relative to the causal one.
    """
    med = d.median()
    iqr = (d.quantile(0.75) - d.quantile(0.25)).replace(0, np.nan)
    full = (d - med) / iqr
    causal = causal_robust_z(d, min_history_td)
    diff = (causal - full).abs()
    return pd.DataFrame({
        "n_compared": diff.notna().sum(),
        "mean_abs_diff": diff.mean(),
        "p95_abs_diff": diff.quantile(0.95),
        "max_abs_diff": diff.max(),
    })
