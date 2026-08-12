"""PORTFOLIO-ARENA-1 — the fifteen systems, frozen.

Every system is a function from ONE date's eligible panel to a score over its
names. The arena then applies the identical position budget, the identical
equal weighting inside the selection, the identical simulator and the identical
cost model. A weighting scheme or a budget chosen per system would make the
arena a search over weightings, and the search would not be in the denominator.

P5 IS THE REPO'S OWN ARITHMETIC, NOT A RE-DERIVATION
=====================================================
`aegis_deterministic` ports the per-stock branches of
`backend/services/signal_engine.py` **verbatim** — the same clips, the same
divisors, the same `config.stock_signal_weights`. That matters: "the Aegis
deterministic system" has to mean the system that actually ships, not a tidy
composite invented for the arena that would flatter it.

Five of the eleven declared per-stock weights have **no point-in-time input on
this spine** and are recorded as unavailable rather than substituted:

    pe_bonus 0.10 · earnings_growth 0.30 · options_iv 0.12 ·
    insider_trading 0.10 · technical_analysis 0.08

That is **0.70 of the 1.532 declared weight — 45.7% of the production
cross-sectional stack that cannot be run point-in-time on 2003-2024.** The
remaining branches are renormalised, and the share is printed in the report,
because a composite quietly missing nearly half its weight is a different
object from the one whose name it carries.

Two DECLARED substitutions, both flagged:
  * the market crash probability is fixed at `config.crash_base_rate_pct`
    (12%). There is no point-in-time market crash probability for 2003-2024 and
    `crash_model.pkl` is recorded broken in CANON. Cross-sectionally this is a
    constant, so it changes the ORDERING not at all and the level by a fixed
    scale — stated rather than hidden.
  * `earnings_quality` is fed the standardised earnings surprise (SUE) through
    `clip(sue/3, -1, 1)`. The production score is built from a surprise
    HISTORY; SUE is the last surprise. A proxy, named as one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ── config, copied from backend/config.py so the arena has no import-time
#    dependency on a running backend. Values are the SHIPPING ones.
STOCK_W = {"analyst_target": 0.12, "sector_momentum": 0.012, "pe_bonus": 0.10,
           "earnings_growth": 0.30, "stock_crash_risk": 0.15,
           "stock_drawdown": 0.25, "stock_momentum": 0.20, "options_iv": 0.12,
           "earnings_quality": 0.10, "insider_trading": 0.10,
           "technical_analysis": 0.08}
UNAVAILABLE_PIT = ("pe_bonus", "earnings_growth", "options_iv",
                   "insider_trading", "technical_analysis")
CRASH_ADJ = {"beta_sensitivity": 0.6, "vol_sensitivity": 0.4,
             "drawdown_sensitivity": 0.3, "vol_baseline": 0.20,
             "min_multiplier": 0.4, "max_multiplier": 2.5}
CRASH_BASE_RATE = 0.12

SEED = 20260812


def z(x: pd.Series) -> pd.Series:
    """Cross-sectional rank-normal score. Ranks, not levels: one 4000% target
    upside must not be allowed to define the scale for 1,499 other names."""
    v = pd.to_numeric(x, errors="coerce")
    ok = v.notna()
    out = pd.Series(np.nan, index=v.index, dtype="float64")
    n = int(ok.sum())
    if n < 3:
        return out.fillna(0.0)
    r = v[ok].rank(method="average") / (n + 1.0)
    from scipy.stats import norm
    out[ok] = norm.ppf(r.to_numpy())
    return out.fillna(0.0)


# ── P5, ported branch by branch ─────────────────────────────────────────────

def _crash_multiplier(beta, vol, dd_pct):
    bf = 1.0 + (beta - 1.0) * CRASH_ADJ["beta_sensitivity"]
    ve = np.maximum(vol - CRASH_ADJ["vol_baseline"], 0.0)
    vf = 1.0 + ve * CRASH_ADJ["vol_sensitivity"] / CRASH_ADJ["vol_baseline"]
    df = 1.0 + np.abs(np.minimum(dd_pct, 0.0)) / 100.0 * CRASH_ADJ[
        "drawdown_sensitivity"]
    return np.clip(bf * vf * df, CRASH_ADJ["min_multiplier"],
                   CRASH_ADJ["max_multiplier"])


def aegis_deterministic(d: pd.DataFrame) -> pd.Series:
    """The shipping per-stock signal stack, on its available branches."""
    s = pd.Series(0.0, index=d.index, dtype="float64")

    up = pd.to_numeric(d["tgt_upside"], errors="coerce") * 100.0
    s = s + STOCK_W["analyst_target"] * np.clip(up / 30.0, -0.5, 0.5).fillna(0.0)

    m63 = pd.to_numeric(d["mom_63"], errors="coerce") * 100.0
    sec = d.groupby("ff12")["mom_63"].transform("mean") * 100.0
    sec_sig = np.where(sec.abs() > 3,
                       np.clip(sec * STOCK_W["sector_momentum"], -0.15, 0.15),
                       0.0)
    s = s + pd.Series(sec_sig, index=d.index).fillna(0.0)

    beta = pd.to_numeric(d["beta_252"], errors="coerce").fillna(1.0)
    vol = pd.to_numeric(d["vol_252"], errors="coerce").fillna(0.20)
    dd = pd.to_numeric(d["dist_252high"], errors="coerce").fillna(0.0) * 100.0
    mult = _crash_multiplier(beta.to_numpy(), vol.to_numpy(), dd.to_numpy())
    crash_delta = CRASH_BASE_RATE * (mult - 1.0)
    s = s + STOCK_W["stock_crash_risk"] * np.clip(
        -crash_delta / CRASH_BASE_RATE, -0.5, 0.5)

    ddv = dd.to_numpy()
    dd_sig = np.where(ddv > -3, 0.1,
             np.where(ddv > -8, 0.0,
             np.where(ddv > -20, ddv / 25.0,
                      np.clip(ddv / 30.0, -1.0, -0.6))))
    s = s + STOCK_W["stock_drawdown"] * dd_sig

    m21 = pd.to_numeric(d["mom_21"], errors="coerce").fillna(0.0) * 100.0
    mom_sig = (0.4 * np.clip(m21 / 12.0, -1, 1)
               + 0.6 * np.clip(m63.fillna(0.0) / 20.0, -1, 1))
    s = s + STOCK_W["stock_momentum"] * mom_sig

    sue = pd.to_numeric(d["sue"], errors="coerce").fillna(0.0)
    s = s + STOCK_W["earnings_quality"] * np.clip(sue / 3.0, -1, 1)

    avail = sum(v for k, v in STOCK_W.items() if k not in UNAVAILABLE_PIT)
    return s / avail


AVAILABLE_WEIGHT_SHARE = (sum(v for k, v in STOCK_W.items()
                              if k not in UNAVAILABLE_PIT)
                          / sum(STOCK_W.values()))


# ── the rest ────────────────────────────────────────────────────────────────

def equal_all(d: pd.DataFrame) -> pd.Series:
    return pd.Series(0.0, index=d.index)


def random_score(d: pd.DataFrame, k: int) -> pd.Series:
    rng = np.random.default_rng(SEED + k)
    return pd.Series(rng.standard_normal(len(d)), index=d.index)


def momentum_event(d: pd.DataFrame) -> pd.Series:
    age = pd.to_numeric(d["days_since_rdq"], errors="coerce")
    sue = pd.to_numeric(d["sue"], errors="coerce")
    recent = sue.where(age <= 21, 0.0).fillna(0.0)
    return 0.5 * z(d["mom_12_1"]) + 0.5 * z(recent)


def revision(d: pd.DataFrame) -> pd.Series:
    return z(d["rev_score"])


def positive_skew(d: pd.DataFrame) -> pd.Series:
    return 0.5 * z(d["skew_252"]) + 0.5 * z(d["max5"])


SCORERS = {
    "P2_equal_weight_all": equal_all,
    "P3_random": None,                     # needs the date index
    "P4_volmatched_random": None,          # needs the date index + a scale
    "P5_aegis_deterministic": aegis_deterministic,
    "P11_momentum_event": momentum_event,
    "P12_revision": revision,
    "P13_positive_skew": positive_skew,
    "P14_risk_targeted_positive_skew": positive_skew,
}

LEARNED_FEATURES = ["vol_63", "vol_252", "beta_252", "ivol_252", "skew_252",
                    "max5", "mom_12_1", "mom_63", "mom_21", "dist_252high",
                    "rev_score", "numest", "sue", "days_since_rdq",
                    "tgt_upside", "hs_bps", "log_mcap", "log_adv"]
