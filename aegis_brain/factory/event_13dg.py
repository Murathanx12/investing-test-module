"""TRIAL-EVENT-13DG — activist intent vs passive disclosure. Spec frozen
2026-08-02 (TRIALS/TRIAL-EVENT-13DG.md, module commit 98c99e2, BEFORE this file
existed).

Three arms, each a counted candidate (175-177):

  175  13d_all    every initial SC 13D, event date = filing date
  176  13g_all    every initial SC 13G — the intent placebo, and it is COUNTED,
                  because a control that cannot lose is not a control
  177  13d_first  SC 13D with no prior 13D on the name within 24 months

Arm construction is the only thing in this module. The event study itself is
`factory/daily_events.py`, which is placebo-validated and control-armed; the
differenced CAR it produces is the only deciding number in this trial.

FROZEN RULINGS IMPLEMENTED HERE (the draft's three open questions, ruled at
freeze):

  1. Amendments (SC 13D/A, SC 13G/A) are EXCLUDED FROM ALL ARMS. Only initial
     filings are events. An amendment is a continuation of a position already
     disclosed, so it carries no new crossing of the 5% threshold.
  2. The 13G arm is counted as a candidate in its own right.
  3. The announcement window -1..0 is REPORTED, NEVER DECIDING. It exists as
     the live check that the event dates are real: 13Ds are filed within 10
     days of crossing 5% and the announcement reaction concentrates at or
     before the filing, so a 13D arm showing NO announcement-window action at
     all indicts the pipeline before it indicts the hypothesis.

DISCLOSED DISCREPANCY (found before the run, no CAR seen at the time). The
frozen doc quotes "explore 13D-first-in-24m 6,826". That number cannot be
reproduced from the banked parquet under any reading of the rule the doc
states: prior = initial 13D gives 7,360; prior = 13D and 13D/A gives 5,601;
de-duplicating (permno, date) gives 6,591 and 4,981; a 730/731/720-day
lookback moves each by a handful. The doc's OTHER counts all reproduce exactly
(13D 12,447; 13G 73,340; 8,542 distinct permnos), so the base is right and only
this derived figure is off. The trial is therefore run on the RULE as written —
prior = a prior INITIAL SC 13D on the same permno, strictly earlier, within 24
calendar months — because ruling (1) excludes amendments from all arms, and the
count is reported as measured rather than forced to match. No window, control,
bar or arm definition is changed by this.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT

logger = logging.getLogger(__name__)
EVENTS = MODULE_ROOT / "data" / "events" / "edgar_13dg_events.parquet"

# ── FROZEN CONSTANTS (registration text; a change here is a new trial) ───────
ARMS = ("13d_all", "13g_all", "13d_first")
INITIAL_13D, INITIAL_13G = "SC 13D", "SC 13G"
AMENDMENTS = ("SC 13D/A", "SC 13G/A")
FIRST_GAP_MONTHS = 24
EXPLORE_START, EXPLORE_END = "2004-01-01", "2018-12-31"
ERA_SPLIT = "2011-01-01"                    # 2004-2010 vs 2011-2018, declared
DECIDING_WINDOWS = ((1, 5), (1, 20), (1, 60))
ANNOUNCEMENT_WINDOW = (-1, 0)               # reported, NEVER deciding
CONTRAST_T_BAR = 2.0                        # 13D-minus-13G kill condition


def load_events(path=None) -> pd.DataFrame:
    df = pd.read_parquet(path or EVENTS)
    df["event_date"] = pd.to_datetime(df["event_date"])
    return df


def initial_only(df: pd.DataFrame, form: str) -> pd.DataFrame:
    """Initial filings of one form. Amendments are excluded from ALL arms."""
    return df[df["form_type"] == form].copy()


def in_explore(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["event_date"] >= pd.Timestamp(EXPLORE_START))
              & (df["event_date"] <= pd.Timestamp(EXPLORE_END))].copy()


def first_in_24m(df: pd.DataFrame, gap_months: int = FIRST_GAP_MONTHS
                 ) -> pd.DataFrame:
    """Initial SC 13Ds with no prior initial SC 13D on the same permno inside
    the preceding `gap_months` calendar months.

    The lookback reads the FULL banked history (2002+), not just the explore
    window, so a 2004 filing is correctly disqualified by a 2003 predecessor.
    Strictly earlier: a same-day sibling filing is not a "prior" filing.
    """
    d13 = initial_only(df, INITIAL_13D)
    prior = {p: np.sort(g["event_date"].to_numpy())
             for p, g in d13.groupby("permno")}
    ex = in_explore(d13)
    keep = []
    for permno, ed in zip(ex["permno"], ex["event_date"]):
        arr = prior.get(permno)
        cut = np.datetime64(ed - pd.DateOffset(months=gap_months))
        e = np.datetime64(ed)
        keep.append(arr is None or not ((arr < e) & (arr >= cut)).any())
    return ex[np.asarray(keep)].copy()


def build_arms(df: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """{arm -> events frame with permno + event_date}, explore window only."""
    df = load_events() if df is None else df
    arms = {
        "13d_all": in_explore(initial_only(df, INITIAL_13D)),
        "13g_all": in_explore(initial_only(df, INITIAL_13G)),
        "13d_first": first_in_24m(df),
    }
    for name, a in arms.items():
        logger.info("arm %s: %d events, %d permnos, %s..%s", name, len(a),
                    a["permno"].nunique(), a["event_date"].min().date(),
                    a["event_date"].max().date())
    return {k: v[["permno", "event_date"]].reset_index(drop=True)
            for k, v in arms.items()}


def era(dates: pd.Series) -> pd.Series:
    """Declared BEFORE any number existed: 13D volume falls 2,756/yr ->
    1,024/yr across the sample, so a pooled result is early-weighted."""
    return np.where(pd.to_datetime(dates) < pd.Timestamp(ERA_SPLIT),
                    "2004-2010", "2011-2018")


# ── the 13D-minus-13G contrast ───────────────────────────────────────────────
def clustered_ols(y: np.ndarray, X: np.ndarray,
                  clusters: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS with a cluster-robust sandwich variance; returns (beta, se).

    Same convention as `daily_events.clustered_t`: the G/(G-1) finite-sample
    correction only, so a constant-only design here reproduces that function
    exactly (pinned by a test).
    """
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    u = y - X @ beta
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(clusters):
        m = clusters == g
        s = X[m].T @ u[m]
        meat += np.outer(s, s)
    G = len(np.unique(clusters))
    V = XtX_inv @ meat @ XtX_inv
    if G > 1:
        V *= G / (G - 1)
    return beta, np.sqrt(np.maximum(np.diag(V), 0.0))


def contrast(car_13d: pd.Series, month_13d: pd.Series,
             car_13g: pd.Series, month_13g: pd.Series) -> dict:
    """13D-minus-13G differenced-CAR contrast, clustered by event month.

    Pooled regression of the differenced CAR on a 13D indicator. The intercept
    is the 13G mean, the slope is the contrast the kill condition reads. Both
    arms' events share the calendar, so clustering must be on the POOLED event
    month rather than done arm by arm — otherwise the same month's market shock
    is counted as two independent draws.
    """
    y = np.concatenate([car_13d.to_numpy(float), car_13g.to_numpy(float)])
    d = np.concatenate([np.ones(len(car_13d)), np.zeros(len(car_13g))])
    g = np.concatenate([month_13d.astype(str).to_numpy(),
                        month_13g.astype(str).to_numpy()])
    ok = np.isfinite(y)
    y, d, g = y[ok], d[ok], g[ok]
    X = np.column_stack([np.ones(len(y)), d])
    beta, se = clustered_ols(y, X, g)
    return {
        "n_13d": int(d.sum()), "n_13g": int(len(d) - d.sum()),
        "n_clusters": int(len(np.unique(g))),
        "car_13g_bps": round(float(beta[0]) * 1e4, 1),
        "contrast_bps": round(float(beta[1]) * 1e4, 1),
        "t_clustered": (round(float(beta[1] / se[1]), 2)
                        if se[1] > 0 else float("nan")),
    }
