"""EXIT-LAB-1 — the counterfactual decision factory's arithmetic.

One **position-state** is `(permno, decision date, entry cohort)`: a name a book
is assumed to have bought `cohort` trading days before the decision date and
still holds. Every state is branched into the thirteen dispositions of §3 of the
prereg, and each branch is resolved at 1 / 5 / 20 / 60 / 120 / 252 trading days.

THE ACCOUNTING CONVENTION, stated once. The sleeve is **one dollar currently
sitting in the position**, and every action is a disposition of that same
dollar, so all thirteen are directly comparable and none of them silently
changes the capital base:

    HOLD          1 + R_i
    ADD_50        1 + 1.5 R_i - 0.5 R_bench          (funded by selling bench)
    TRIM_x        1 + (1-x) R_i + x R_cash
    SELL_CASH     1 + R_cash
    SELL_BENCH    1 + R_bench
    REPLACE_*     1 + R_candidate
    REDUCE_BETA   f = clip(1/beta_i, 0, 1);  1 + f R_i + (1-f) R_cash

minus the traded fraction times the round-trip cost at T0. These are exact, not
linearisations: a trimmed sleeve really does hold (1-x) of the name and x of
cash for the whole horizon.

DEATH. `LOGCUM` already carries the CRSP delisting return on the first day
after the last quote and then grows the proceeds at the risk-free rate, so a
name that dies inside a horizon resolves at its real delisting return and the
survivor's cash. Terminations are counted per horizon and printed; they are
never silently dropped.

NO LOOK-AHEAD. Every feature and every candidate ranking is computed from rows
strictly at or before the decision date. `perturbation_proof()` in the runner
corrupts every cell after T0 and requires the whole state table to come back
bit-identical.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ── the action space (prereg §3, plus the three declared controls) ─────────
ACTIONS = [
    "HOLD",          # 0
    "ADD_50",        # 1
    "TRIM_10",       # 2
    "TRIM_25",       # 3
    "TRIM_50",       # 4
    "SELL_CASH",     # 5
    "SELL_BENCH",    # 6
    "REPLACE_1",     # 7   top-5 momentum basket, excluding the held name
    "REPLACE_2",     # 8   ranks 6-10 momentum basket
    "REDUCE_BETA",   # 9
    "REPLACE_RND",   # 10  CONTROL for 7/8: 5 uniformly random eligible names
    "REPLACE_1N",    # 11  CONTROL: the literal single top-ranked name
    "REPLACE_REV",   # 12  robustness ranker: top-5 by NIGHT-11 revision score
    "REPLACE_1W",    # 13  top-20 momentum basket
    "REPLACE_2W",    # 14  ranks 21-40 momentum basket
    "REPLACE_RNDW",  # 15  CONTROL for 13/14: 20 uniformly random names
]
#: which rank slice and ranker each replacement arm draws from
REPLACE_ARMS = {
    "REPLACE_1":    ("mom", 0, 5),
    "REPLACE_2":    ("mom", 5, 5),
    "REPLACE_RND":  ("rnd", 0, 5),
    "REPLACE_1N":   ("mom", 0, 1),
    "REPLACE_REV":  ("rev", 0, 5),
    "REPLACE_1W":   ("mom", 0, 20),
    "REPLACE_2W":   ("mom", 20, 20),
    "REPLACE_RNDW": ("rnd", 0, 20),
}
A = {a: i for i, a in enumerate(ACTIONS)}

HORIZONS = [1, 5, 20, 60, 120, 252]
PRIMARY_H = 60
COHORTS = [21, 63, 126, 252]

#: eligibility, identical to WINNER-GENOME-1's universe rule
MIN_PRICE = 5.0
MIN_HISTORY = 252
MIN_MED_DV = 1_000_000.0
TOP_N = 1500

#: slippage + commission from `daily_sim.SimConfig` (5 bps + 1 bp), charged on
#: top of the Corwin-Schultz half-spread. Not a new cost model.
EXTRA_BPS = 6.0
#: all-in cost of the market leg (an index fund, not a single small cap).
#: Declared, not fitted.
BENCH_BPS = 5.0
#: basket sizes for the replacement arms. The prereg's literal reading is "the
#: best current candidate", i.e. ONE name — and `REPLACE_1N` keeps that reading.
#: It is also degenerate: with one name per date, the whole date's replacement
#: outcome is that name's outcome, so the across-date dispersion (which IS the
#: ruler, since the decision date is the sampling unit) becomes enormous and
#: every replacement verdict is UNRESOLVED by construction rather than by
#: evidence. The 5- and 20-name baskets are run beside it so the answer to
#: "is replacement better than cash" is not decided by the instrument's own
#: noise. AMENDED 2026-08-12 BEFORE any row was generated; see prereg §3a.
BASKET = 5
BASKET_WIDE = 20
#: winsorisation for the IBES target-upside FEATURE only. A mid-month statpers
#: ratioed against a month-end price straddles any split in between, which
#: prints upside in the thousands of percent. Clipped and COUNTED, never
#: silently dropped; it is a feature, never an outcome.
TGT_CLIP = (-0.95, 5.0)


# ── panel construction ────────────────────────────────────────────────────
def build_position_factors(RET: np.ndarray, first_obs: np.ndarray,
                           last_obs: np.ndarray, delist_day: np.ndarray,
                           rf: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    """Cumulative log value of ONE dollar put into each name, and its term day.

    Inside the quote window a missing return is a non-trading day, not a loss,
    so it carries at 1.0. After the terminal day the dollar is CASH and grows at
    the daily risk-free rate — which is what makes a delisted position resolve
    the way a real account resolves it rather than vanishing from the mean.
    """
    nD, nP = RET.shape
    term = np.where(delist_day >= 0, delist_day, last_obs).astype(np.int64)
    t_ix = np.arange(nD, dtype=np.int64)[:, None]

    G = np.where(np.isfinite(RET), 1.0 + RET.astype(np.float64), 1.0)
    # a -100% delisting would be log(0); floor it so the dollar goes to ~0 and
    # then sits there, rather than turning the whole column into -inf
    np.clip(G, 1e-4, None, out=G)
    after = t_ix > term[None, :]
    G[after] = np.broadcast_to((1.0 + rf.astype(np.float64))[:, None],
                               G.shape)[after]
    before = t_ix < first_obs[None, :].astype(np.int64)
    G[before] = np.nan

    LC = np.log(G)
    del G
    np.nan_to_num(LC, copy=False, nan=0.0)
    np.cumsum(LC, axis=0, out=LC)
    # mask the pre-existence region back out so a state can never form there
    LC[before] = np.nan
    diag = {
        "names_with_delisting": int((delist_day >= 0).sum()),
        "names_terminated_before_sample_end": int((term < nD - 1).sum()),
    }
    return LC.astype(np.float32), term.astype(np.int32), diag


def cum_series(x: np.ndarray) -> np.ndarray:
    """Cumulative log gross of a daily simple-return series."""
    return np.cumsum(np.log1p(np.nan_to_num(x, nan=0.0)))


def hret(LC: np.ndarray, t: int, h: int, cols: np.ndarray) -> np.ndarray:
    """Simple return of a held dollar from t to t+h, NaN past the sample."""
    if t + h >= LC.shape[0]:
        return np.full(len(cols), np.nan, dtype=np.float64)
    return np.expm1(LC[t + h, cols].astype(np.float64)
                    - LC[t, cols].astype(np.float64))


def hscalar(C: np.ndarray, t: int, h: int) -> float:
    if t + h >= len(C):
        return np.nan
    return float(np.expm1(C[t + h] - C[t]))


# ── eligibility and features ──────────────────────────────────────────────
def eligible_at(t: int, PRC: np.ndarray, DOLVOL: np.ndarray,
                first_obs: np.ndarray, term: np.ndarray) -> np.ndarray:
    px = PRC[t]
    med_dv = np.nanmedian(DOLVOL[t - 62:t + 1], axis=0)
    ok = (np.isfinite(px) & (px >= MIN_PRICE)
          & (first_obs <= t - MIN_HISTORY) & (term >= t)
          & np.isfinite(med_dv) & (med_dv >= MIN_MED_DV))
    idx = np.where(ok)[0]
    if len(idx) > TOP_N:
        order = np.argsort(-med_dv[idx], kind="mergesort")
        idx = np.sort(idx[order[:TOP_N]])
    return idx


def trailing_stats(LC: np.ndarray, t: int, cols: np.ndarray,
                   mkt_log: np.ndarray) -> dict:
    """Volatility, beta and idiosyncratic volatility from trailing log returns."""
    w = LC[t - 252:t + 1, cols].astype(np.float64)
    r = np.diff(w, axis=0)                      # 252 x n daily log returns
    m = np.diff(mkt_log[t - 252:t + 1])[:, None]
    vol252 = np.nanstd(r, axis=0) * np.sqrt(252.0)
    vol63 = np.nanstd(r[-63:], axis=0) * np.sqrt(252.0)
    mv = float(np.nanvar(m))
    with np.errstate(invalid="ignore", divide="ignore"):
        beta = np.nanmean((r - np.nanmean(r, axis=0)) * (m - np.nanmean(m)),
                          axis=0) / mv if mv > 0 else np.full(len(cols), np.nan)
        resid = r - beta[None, :] * m
        ivol = np.nanstd(resid, axis=0) * np.sqrt(252.0)
    return {"vol_63": vol63, "vol_252": vol252, "beta_252": beta, "ivol_252": ivol}


def cohort_stats(LC: np.ndarray, t: int, cols: np.ndarray, E: int) -> dict:
    """What the hypothetical holder sees: unrealised gain, peak, drawdown."""
    w = LC[t - E:t + 1, cols].astype(np.float64)
    entry = w[0]
    now = w[-1]
    peak = np.nanmax(w, axis=0)
    trough = np.nanmin(w, axis=0)
    return {
        "gain_since_entry": np.expm1(now - entry),
        "runup_max": np.expm1(peak - entry),
        "dd_from_peak": np.expm1(now - peak),
        "worst_since_entry": np.expm1(trough - entry),
    }


def basket_return(LC: np.ndarray, t: int, h: int, members: np.ndarray) -> float:
    """Equal-weighted terminal return of a fixed basket held for h days."""
    if len(members) == 0:
        return np.nan
    r = hret(LC, t, h, members)
    return float(np.nanmean(r))


def apply_actions(R_i: np.ndarray, R_cash: float, R_bm: float,
                  R_cand: dict[str, np.ndarray], cost_i: np.ndarray,
                  cost_cand: dict[str, np.ndarray],
                  f_beta: np.ndarray) -> np.ndarray:
    """(n_states x n_actions) net sleeve returns for one (date, horizon)."""
    n = len(R_i)
    out = np.full((n, len(ACTIONS)), np.nan, dtype=np.float64)
    cb = BENCH_BPS / 1e4
    out[:, A["HOLD"]] = R_i
    out[:, A["ADD_50"]] = 1.5 * R_i - 0.5 * R_bm - 0.5 * cost_i - 0.5 * cb
    for x, name in ((0.10, "TRIM_10"), (0.25, "TRIM_25"), (0.50, "TRIM_50")):
        out[:, A[name]] = (1 - x) * R_i + x * R_cash - x * cost_i
    out[:, A["SELL_CASH"]] = R_cash - cost_i
    out[:, A["SELL_BENCH"]] = R_bm - cost_i - cb
    for name in REPLACE_ARMS:
        out[:, A[name]] = R_cand[name] - cost_i - cost_cand[name]
    out[:, A["REDUCE_BETA"]] = (f_beta * R_i + (1 - f_beta) * R_cash
                                - (1 - f_beta) * cost_i)
    return out


FEATURE_COLS = [
    "price", "log_mcap", "log_dv", "turnover", "hs_bps",
    "vol_63", "vol_252", "beta_252", "ivol_252",
    "mom_12_1", "mom_63", "mom_21", "dist_252high",
    "mkt_ret_63", "mkt_vol_63", "mkt_dd_252",
    "rev_score", "numest", "sue", "days_since_rdq", "tgt_upside",
    "gain_since_entry", "runup_max", "dd_from_peak", "worst_since_entry",
    "cohort_days", "ff12",
]
