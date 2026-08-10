"""Typed paired statistics — the unit travels with the number.

Why this module exists. NIGHT-8 found that `mde_annualized()` annualises its own
input and five call sites had already annualised theirs, so NIGHT-7's published
trigger receipts reported minimum detectable effects of 43% to 143% per year.
The bug was fixed. The *design* that produced it was not: one generic helper,
`paired()`, was copy-pasted across scripts and fed monthly returns in some places
and monthly rank-IC in others, while its output fields were named for returns
throughout. N1's ordering table therefore carried an `mde_annualized` on a
Spearman correlation — a quantity for which "per year" is meaningless.

The fix is not another guard. It is that **there is no generic entry point.**
Each function below accepts one kind of series, and the annualising arithmetic
is reachable only from the return-typed one. Every result carries `unit`,
`frequency`, `annualization` and `estimator` so a downstream reader — human,
manifest, or referee — can see what it is holding.

Dimensional invariants, asserted in `tests/test_stats_units.py`:

  a 0.001 monthly RETURN difference  ->  ~1.2% per year
  a 0.001 monthly IC difference      ->  0.001, still, for ever
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.pf.decomp import mde_annualized, nw_t

MONTHS_PER_YEAR = 12
T_BAR = 2.0


def _align(a: pd.Series, b: pd.Series) -> pd.Series:
    return (pd.Series(a) - pd.Series(b)).dropna()


def _corr(a: pd.Series, b: pd.Series) -> float | None:
    """None rather than NaN when an arm is constant — a receipt reads better."""
    c = pd.Series(a).corr(pd.Series(b))
    return None if c is None or not np.isfinite(c) else round(float(c), 4)


def _core(d: pd.Series, lags: int) -> dict:
    se = float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else float("nan")
    return {"n": int(len(d)), "mean": float(d.mean()), "se_iid": se,
            "t_newey_west": nw_t(pd.Series(d.to_numpy()), lags=lags),
            "t_iid": (round(float(d.mean() / se), 2)
                      if se and np.isfinite(se) and se > 0 else None)}


def paired_return_stats(a: pd.Series, b: pd.Series, *, lags: int = 12,
                        min_n: int = 24) -> dict:
    """Paired difference of two MONTHLY return series.

    This is the only function here that annualises, because a return is the only
    input type for which annualising means anything.
    """
    d = _align(a, b)
    if len(d) < min_n:
        return {"n": int(len(d)), "insufficient": True, "unit": "return",
                "frequency": "monthly"}
    c = _core(d, lags)
    return {
        "n": c["n"],
        "mean_monthly": round(c["mean"], 6),
        "annualized_pct": round(c["mean"] * MONTHS_PER_YEAR, 4),
        "t_newey_west": c["t_newey_west"],
        "t_iid": c["t_iid"],
        "mde_annualized": mde_annualized(d, T_BAR),
        "correlation": _corr(a, b),
        "unit": "simple return, fraction of NAV",
        "frequency": "monthly",
        "annualization": f"mean x {MONTHS_PER_YEAR}",
        "estimator": f"Newey-West({lags}) on the paired difference",
    }


def paired_ic_stats(a: pd.Series, b: pd.Series, *, lags: int = 12,
                    min_n: int = 12) -> dict:
    """Paired difference of two MONTHLY rank-IC series.

    **There is deliberately no annualised field.** A correlation does not
    accumulate over twelve months, so `0.034 x 12 = 0.41` is not "0.41 per year"
    — it is nothing at all. N1's published ordering table carried exactly that
    number and it should never have had a `/yr` shaped name.
    """
    d = _align(a, b)
    if len(d) < min_n:
        return {"n": int(len(d)), "insufficient": True, "unit": "correlation",
                "frequency": "monthly"}
    c = _core(d, lags)
    return {
        "n": c["n"],
        "dic_mean": round(c["mean"], 5),
        "t_newey_west": c["t_newey_west"],
        "t_iid": c["t_iid"],
        "mde_ic_units": round(T_BAR * c["se_iid"], 5),
        "correlation": _corr(a, b),
        "unit": "Spearman rank correlation",
        "frequency": "monthly, cross-sectional",
        "annualization": "none — a correlation is not annualisable",
        "estimator": f"Newey-West({lags}) on the paired difference",
    }


def paired_probability_stats(a: pd.Series, b: pd.Series, *, lags: int = 12,
                             min_n: int = 12) -> dict:
    """Paired difference of two probability series (hit rates, veto rates)."""
    d = _align(a, b)
    if len(d) < min_n:
        return {"n": int(len(d)), "insufficient": True,
                "unit": "probability", "frequency": "per period"}
    c = _core(d, lags)
    return {
        "n": c["n"],
        "delta_probability": round(c["mean"], 5),
        "t_newey_west": c["t_newey_west"],
        "t_iid": c["t_iid"],
        "mde_probability_units": round(T_BAR * c["se_iid"], 5),
        "unit": "probability in [0, 1]",
        "frequency": "per period",
        "annualization": "none — a probability is not a rate per year",
        "estimator": f"Newey-West({lags}) on the paired difference",
    }


def paired_brier_stats(a: pd.Series, b: pd.Series, *, lags: int = 12,
                       min_n: int = 12) -> dict:
    """Paired difference of two Brier-score series. LOWER is better."""
    out = paired_probability_stats(a, b, lags=lags, min_n=min_n)
    if out.get("insufficient"):
        out["unit"] = "Brier score"
        return out
    out["delta_brier"] = out.pop("delta_probability")
    out["mde_brier_units"] = out.pop("mde_probability_units")
    out["unit"] = "Brier score in [0, 1]"
    out["direction"] = "lower is better — a NEGATIVE delta favours the first arm"
    return out


#: Every typed result must be self-describing. A receipt writer can assert this.
REQUIRED_FIELDS = ("unit", "frequency")


def is_typed(result: dict) -> bool:
    return all(k in result for k in REQUIRED_FIELDS)
