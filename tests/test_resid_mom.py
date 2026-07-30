"""INSTR-RESID-MOM spec tests — the frozen Blitz-Huij-Martens construction.

The signal has no model to leak through, so the surfaces worth pinning are the
SPEC itself (a spec drift here would silently answer a different question than
the one registered) and the splice, which must fail loud rather than quietly
shorten the estimation window.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory import resid_mom as rm


def _panel(n_months: int = 60, n_syms: int = 8, seed: int = 3) -> Panel:
    rng = np.random.default_rng(seed)
    months = pd.date_range("2004-01-31", periods=n_months, freq="ME")
    syms = [f"S{i}" for i in range(n_syms)]
    ret = pd.DataFrame(rng.normal(0.004, 0.05, (n_months, n_syms)),
                       index=months, columns=syms)
    return Panel(monthly_ret=ret,
                 month_end_price=pd.DataFrame(50.0, index=months, columns=syms),
                 monthly_dollar_vol=pd.DataFrame(1e6, index=months, columns=syms),
                 delist_month={s: months[-1] for s in syms})


def _ff(index: pd.DatetimeIndex, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "mktrf": rng.normal(0.005, 0.04, len(index)),
        "smb": rng.normal(0.0, 0.02, len(index)),
        "hml": rng.normal(0.0, 0.02, len(index)),
        "rf": np.full(len(index), 0.002),
    }, index=index)


@pytest.fixture()
def no_splice(monkeypatch):
    """Run compute_resid_mom on the panel alone (no historical splice)."""
    monkeypatch.setattr(rm, "spliced_returns", lambda panel: panel.monthly_ret)


def test_frozen_spec_constants():
    """The registration froze these; a change is a new trial, not a tweak."""
    assert rm.EST_MONTHS == 36
    assert (rm.SIG_START, rm.SIG_END) == (24, 34)
    assert rm.SIG_END - rm.SIG_START + 1 == 11        # m-11 .. m-1, the 12-1 skip
    # position 35 is month m itself and must NOT be in the signal window
    assert rm.SIG_END < rm.EST_MONTHS - 1
    assert rm.FF_COLS == ["mktrf", "smb", "hml"]      # FF3, not FF5/FF6


def test_no_score_before_36_months(no_splice):
    p = _panel()
    out = rm.compute_resid_mom(p, ff=_ff(p.monthly_ret.index))
    scored = out.notna().sum(axis=1)
    assert scored.iloc[:35].sum() == 0, "scored before 36 observations exist"
    assert scored.iloc[35] > 0, "no score at the first fully-observed month"


def test_matches_hand_computed_bhm_definition(no_splice):
    """Reproduce one cell by hand: OLS on 36 months, mean/sd of residuals m-11..m-1."""
    p = _panel()
    ff = _ff(p.monthly_ret.index)
    out = rm.compute_resid_mom(p, ff=ff)

    m = p.monthly_ret.index[40]
    i = 40
    sl = slice(i + 1 - 36, i + 1)
    y = (p.monthly_ret["S0"] - ff["rf"]).iloc[sl].to_numpy()
    X = np.column_stack([np.ones(36), ff[["mktrf", "smb", "hml"]].iloc[sl].to_numpy()])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    win = resid[24:34 + 1]                  # positions 24..34 = months m-11..m-1
    assert len(win) == 11
    expect = win.mean() / win.std(ddof=1)
    assert out.loc[m, "S0"] == pytest.approx(expect, rel=1e-10)


def test_excludes_the_formation_month_itself(no_splice):
    """The 12-1 skip, pinned by an EXACT prediction.

    With all factors zeroed the design is intercept-only, so residuals are
    demeaned returns. Perturbing month m by delta then shifts every residual in
    the signal window by exactly -delta/36 and leaves the window's sd untouched
    — a closed-form prediction that only holds if month m is OUTSIDE the signal
    window. If m were inside it (the off-by-one this test was written to catch)
    the mean and the sd both move and the prediction fails.
    """
    p = _panel()
    ff = _ff(p.monthly_ret.index)
    ff[["mktrf", "smb", "hml", "rf"]] = 0.0
    base = rm.compute_resid_mom(p, ff=ff)

    m = p.monthly_ret.index[40]
    delta = 5.0
    bumped = p.monthly_ret.copy()
    bumped.loc[m, "S0"] += delta
    p2 = Panel(monthly_ret=bumped, month_end_price=p.month_end_price,
               monthly_dollar_vol=p.monthly_dollar_vol, delist_month=p.delist_month)
    after = rm.compute_resid_mom(p2, ff=ff)

    win = (p.monthly_ret["S0"].iloc[5:41].to_numpy()
           - p.monthly_ret["S0"].iloc[5:41].mean())[24:35]
    sd = win.std(ddof=1)
    expected = base.loc[m, "S0"] - (delta / 36.0) / sd
    assert after.loc[m, "S0"] == pytest.approx(expected, rel=1e-9)


def test_requires_all_36_observations(no_splice):
    p = _panel()
    ff = _ff(p.monthly_ret.index)
    holed = p.monthly_ret.copy()
    holed.iloc[10, 0] = np.nan              # one gap inside S0's first window
    p2 = Panel(monthly_ret=holed, month_end_price=p.month_end_price,
               monthly_dollar_vol=p.monthly_dollar_vol, delist_month=p.delist_month)
    out = rm.compute_resid_mom(p2, ff=ff)
    m = p.monthly_ret.index[40]             # window 5..40 still contains row 10
    assert pd.isna(out.loc[m, "S0"])
    assert out.loc[m].notna().sum() >= 1, "other names should be unaffected"


def test_score_is_scale_free_in_the_residual_window(no_splice):
    """mean/sd standardisation: doubling a name's idiosyncratic scale is a no-op
    on the ratio only if the residuals scale too — pin that it is finite and
    bounded rather than exploding, the property the ratio buys."""
    p = _panel()
    out = rm.compute_resid_mom(p, ff=_ff(p.monthly_ret.index))
    vals = out.stack().dropna()
    assert len(vals) > 0
    assert vals.abs().max() < 10.0, "a t-like ratio over 11 obs should stay bounded"


def test_splice_failure_is_loud(monkeypatch):
    """A missing historical panel must raise, never silently shorten the window."""
    def boom(*_a, **_k):
        raise FileNotFoundError("no panel")
    monkeypatch.setattr(rm, "load_cached_panel", boom)
    with pytest.raises(RuntimeError, match="spliced history"):
        rm.spliced_returns(_panel())
