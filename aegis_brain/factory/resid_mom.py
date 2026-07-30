"""Residual (idiosyncratic) momentum — INSTR-RESID-MOM, spec frozen 2026-07-30.

Blitz, Huij & Martens, "Residual Momentum" (Journal of Empirical Finance 18,
2011), followed verbatim. Nothing here is invented:

  1. At formation month-end m, regress the name's EXCESS return on the FF3
     factors (mktrf, smb, hml) over months m-35 .. m — 36 observations, all
     required.
  2. Take the OLS residuals over months m-11 .. m-1 (the standard 12-1 skip;
     month m itself is excluded).
  3. resid_mom = mean(residual) / stdev(residual) over that same 11-month
     window.  Direction +1.

The standardisation by the residual standard deviation over the *same* window
is BHM's definition, not a normalisation choice, and is part of the frozen
spec.

DECLARED DEPARTURE (plumbing, disclosed at implementation): the 36-month
estimation window is drawn from the SPLICED CRSP return history
(crsp_panel_1963 for months <= 2001-12, crsp_panel_2002 thereafter) so that the
window is fully available from the first explore test month. Without the splice
the first computable formation month would be 2004-12 and the explore window
would silently lose its first year, breaking comparability with the other 159
candidates. The traded universe, eligibility mask, segment bounds, costs and
benchmark all come from crsp_panel_2002 alone and are untouched — only the
lookback used to FIT the model is longer. Every input remains information known
at month-end m.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel, load_cached_panel

logger = logging.getLogger(__name__)

EST_MONTHS = 36          # frozen
# Window positions inside the 36-month estimation slice: position 0 = m-35 and
# position 35 = m, so position p is month m-(35-p). The signal window m-11..m-1
# is therefore positions 24..34 — position 35 is the FORMATION month itself and
# must be excluded (the 12-1 skip). Getting this wrong folds one-month reversal
# into a momentum signal; tests/test_resid_mom.py pins it.
SIG_START, SIG_END = 24, 34
FF_COLS = ["mktrf", "smb", "hml"]      # FF3, frozen — FF5/FF6 are not a retune option


def spliced_returns(panel: Panel) -> pd.DataFrame:
    """Panel returns extended backwards with the 1963 CRSP panel (see module docstring)."""
    hist_dir = MODULE_ROOT / "data" / "crsp_panel_1963"
    try:
        hist = load_cached_panel(hist_dir).monthly_ret
    except Exception as exc:  # noqa: BLE001 — fail LOUD, never silently short-window
        raise RuntimeError(
            f"resid_mom requires the spliced history at {hist_dir}: {exc!r}"
        ) from exc
    cur = panel.monthly_ret
    hist = hist.loc[hist.index < cur.index.min(), :]
    out = pd.concat([hist.reindex(columns=cur.columns), cur], axis=0).sort_index()
    logger.info("spliced return history: %d months (%s..%s), %d names",
                len(out), out.index.min().date(), out.index.max().date(),
                out.shape[1])
    return out


def compute_resid_mom(panel: Panel, ff: pd.DataFrame | None = None) -> pd.DataFrame:
    """[month x sym] residual-momentum score aligned to the panel's index."""
    if ff is None:
        ff = pd.read_parquet(MODULE_ROOT / "data" / "ff_factors.parquet")
    rets = spliced_returns(panel)

    ff = ff.reindex(rets.index)
    excess = rets.sub(ff["rf"], axis=0)
    X_all = np.column_stack([np.ones(len(ff)), ff[FF_COLS].to_numpy(float)])

    out = pd.DataFrame(np.nan, index=panel.monthly_ret.index,
                       columns=panel.monthly_ret.columns, dtype=float)
    positions = {m: i for i, m in enumerate(rets.index)}

    for m in panel.monthly_ret.index:
        i = positions[m]
        if i + 1 < EST_MONTHS:
            continue                      # not enough history yet
        sl = slice(i + 1 - EST_MONTHS, i + 1)
        X = X_all[sl]
        if not np.isfinite(X).all():
            continue                      # missing factor month — no scores
        Y = excess.iloc[sl].to_numpy(float)          # [36 x N]
        ok = np.isfinite(Y).all(axis=0)               # ALL 36 required (frozen)
        if ok.sum() == 0:
            continue
        Yk = Y[:, ok]
        beta, *_ = np.linalg.lstsq(X, Yk, rcond=None)  # [4 x n_ok]
        resid = Yk - X @ beta
        win = resid[SIG_START:SIG_END + 1]             # m-11 .. m-1, 11 rows
        assert win.shape[0] == 11, "signal window must be 11 months (12-1 skip)"
        mu = win.mean(axis=0)
        sd = win.std(axis=0, ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            score = np.where(sd > 0, mu / sd, np.nan)
        out.loc[m, excess.columns[ok]] = score

    cov = out.notna().sum(axis=1)
    logger.info("resid_mom: mean monthly coverage %.0f names (first scored %s)",
                cov.mean(), cov[cov > 0].index.min())
    return out
