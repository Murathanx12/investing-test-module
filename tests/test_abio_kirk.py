"""TRIAL-ABIO-KIRK spec tests — written BEFORE the one shot.

The arms have no model to leak through, so what is worth pinning is the SPEC:
a silent drift in the lag, the winsorisation grouping, the regression's
cross-sectional-per-quarter structure or the link rule would answer a different
question than the one registered, and the run is unrepeatable.

Precedent: tests/test_resid_mom.py, which caught an off-by-one that would have
voided that trial.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory import abio


def _panel(n_months: int = 48, n_syms: int = 6, seed: int = 11) -> Panel:
    rng = np.random.default_rng(seed)
    months = pd.date_range("2003-01-31", periods=n_months, freq="ME")
    syms = [str(10000 + i) for i in range(n_syms)]
    return Panel(
        monthly_ret=pd.DataFrame(rng.normal(0.004, 0.05, (n_months, n_syms)),
                                 index=months, columns=syms),
        month_end_price=pd.DataFrame(50.0, index=months, columns=syms),
        monthly_dollar_vol=pd.DataFrame(1e6, index=months, columns=syms),
        delist_month={s: months[-1] for s in syms})


# ── frozen constants ─────────────────────────────────────────────────────────
def test_frozen_constants():
    """Registered values. A change here is a new trial, not a tweak."""
    assert abio.LAG_DAYS == 60
    assert (abio.WINSOR_LO, abio.WINSOR_HI) == (0.01, 0.99)
    assert abio.CHARS == ["log_mktcap", "mom_12_1", "log_dvol3m",
                          "inv_price", "log_age"]
    assert len(abio.CHARS) == 5
    assert abio.ARMS == ("io_level", "io_chg", "io_abn")


# ── the availability lag ─────────────────────────────────────────────────────
def test_lag_excludes_fdate_59_days_before_month_end():
    """THE off-by-one this file exists to catch: 59 days is not enough, 60 is.

    Both boundaries pinned against the same month-end so the test cannot pass by
    the rule being uniformly too strict or too loose.
    """
    months = pd.date_range("2004-01-31", periods=36, freq="ME")
    m = pd.Timestamp("2005-03-31")

    at_59 = m - pd.Timedelta(days=59)
    assert abio.first_available_month(at_59, months) > m, \
        "a quarter 59 days old must NOT be usable at that month-end"

    at_60 = m - pd.Timedelta(days=60)
    assert abio.first_available_month(at_60, months) == m, \
        "a quarter exactly 60 days old must be usable at that month-end"


def test_real_quarter_end_lands_two_months_later():
    """2004-03-31 + 60d = 2004-05-30, so the first usable formation month-end is
    2004-05-31 — one month later than the 45-day statutory rule would give."""
    months = pd.date_range("2004-01-31", periods=36, freq="ME")
    got = abio.first_available_month(pd.Timestamp("2004-03-31"), months)
    assert got == pd.Timestamp("2004-05-31")


def test_panel_frame_never_carries_a_quarter_before_its_lag_elapsed():
    """End-to-end no-lookahead: the value appears at its availability month and
    at no earlier month."""
    p = _panel()
    long = pd.DataFrame({"fdate": [pd.Timestamp("2004-03-31")],
                         "sym": ["10000"], "io": [0.42]})
    w = abio.to_panel_frame(long, "io", p)
    avail = pd.Timestamp("2004-05-31")
    assert w.loc[:avail, "10000"].iloc[:-1].isna().all()
    assert w.loc[avail, "10000"] == pytest.approx(0.42)
    assert w.loc["2004-06-30", "10000"] == pytest.approx(0.42)  # ffill: "latest"


# ── winsorisation ────────────────────────────────────────────────────────────
def test_winsorisation_is_per_quarter_not_pooled():
    """Two quarters on different scales. Per-quarter clipping leaves the small
    quarter's values untouched; a POOLED 1/99 clip would drag them to the pooled
    quantile. Pinned by an exact prediction on both quarters.
    """
    q1 = pd.Timestamp("2004-03-31")
    q2 = pd.Timestamp("2004-06-30")
    v1 = np.linspace(0.0, 1.0, 101)          # quarter 1: spread over [0, 1]
    v2 = np.linspace(100.0, 200.0, 101)      # quarter 2: spread over [100, 200]
    s = pd.Series(np.r_[v1, v2])
    g = pd.Series([q1] * 101 + [q2] * 101)

    out = abio.winsorise_by(s, g)
    a, b = out.iloc[:101], out.iloc[101:]
    # each quarter clipped at ITS OWN 1/99 quantiles
    assert a.min() == pytest.approx(np.quantile(v1, 0.01))
    assert a.max() == pytest.approx(np.quantile(v1, 0.99))
    assert b.min() == pytest.approx(np.quantile(v2, 0.01))
    assert b.max() == pytest.approx(np.quantile(v2, 0.99))
    # a pooled clip would have flattened ALL of quarter 1 to one number
    assert a.nunique() > 50


def test_io_chg_is_a_difference_of_winsorised_levels():
    """Frozen ordering: 'io winsorised per-quarter ... before any further step'."""
    own = pd.DataFrame({
        "fdate": [pd.Timestamp("2004-03-31")] * 3 + [pd.Timestamp("2004-06-30")] * 3,
        "sym": ["1", "2", "3"] * 2,
        "inst_shares": [1e6, 2e6, 3e6, 2e6, 2e6, 2e6],
        "cusip": ["A"] * 6, "n_inst": [5] * 6,
    })
    sh = pd.DataFrame({"sym": ["1", "2", "3"] * 2,
                       "ym": [pd.Period("2004-03", "M")] * 3
                             + [pd.Period("2004-06", "M")] * 3,
                       "shrout": [10e3] * 6})           # 10e3 thousands = 1e7 sh
    io = abio.build_io(own, shrout=sh).set_index(["fdate", "sym"])

    lvl = io["io"]
    q1 = lvl.loc[pd.Timestamp("2004-03-31")]
    q2 = lvl.loc[pd.Timestamp("2004-06-30")]
    for s in ("1", "2", "3"):
        assert io.loc[(pd.Timestamp("2004-06-30"), s), "io_chg"] == \
            pytest.approx(q2[s] - q1[s])
    assert pd.isna(io.loc[(pd.Timestamp("2004-03-31"), "1"), "io_chg"])


def test_io_is_shares_over_shares_outstanding():
    """io = inst_shares / (shrout * 1000) — shrout is in THOUSANDS of shares."""
    own = pd.DataFrame({"fdate": [pd.Timestamp("2004-03-31")], "sym": ["1"],
                        "inst_shares": [2.5e6], "cusip": ["A"], "n_inst": [7]})
    sh = pd.DataFrame({"sym": ["1"], "ym": [pd.Period("2004-03", "M")],
                       "shrout": [10e3]})
    io = abio.build_io(own, shrout=sh)
    assert io["io"].iloc[0] == pytest.approx(2.5e6 / (10e3 * 1000))  # 0.25


# ── the link rule ────────────────────────────────────────────────────────────
def _names(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["sym", "cusip", "namedt", "nameenddt"])


def test_ambiguous_cusip_is_dropped_not_resolved():
    """One cusip valid for TWO permnos in the same quarter -> the name-month is
    dropped entirely. Not first-wins, not best-score, not summed."""
    own = pd.DataFrame({"fdate": [pd.Timestamp("2004-03-31")], "cusip": ["AAAA1111"],
                        "n_inst": [9], "inst_shares": [1e6]})
    nm = _names([
        ("111", "AAAA1111", pd.Timestamp("2000-01-01"), pd.Timestamp("2010-01-01")),
        ("222", "AAAA1111", pd.Timestamp("2001-01-01"), pd.Timestamp("2010-01-01")),
    ])
    assert abio.link_ownership(own, names=nm).empty


def test_unambiguous_link_survives_and_date_validity_binds():
    """The same cusip resolves cleanly when only one name record is date-valid —
    proving the drop above is the AMBIGUITY rule, not a broken join."""
    own = pd.DataFrame({"fdate": [pd.Timestamp("2004-03-31")], "cusip": ["AAAA1111"],
                        "n_inst": [9], "inst_shares": [1e6]})
    nm = _names([
        ("111", "AAAA1111", pd.Timestamp("2000-01-01"), pd.Timestamp("2010-01-01")),
        ("222", "AAAA1111", pd.Timestamp("1990-01-01"), pd.Timestamp("1995-01-01")),
    ])
    out = abio.link_ownership(own, names=nm)
    assert list(out["sym"]) == ["111"]


def test_link_excludes_quarters_outside_the_name_window():
    own = pd.DataFrame({"fdate": [pd.Timestamp("2004-03-31")], "cusip": ["AAAA1111"],
                        "n_inst": [9], "inst_shares": [1e6]})
    nm = _names([("111", "AAAA1111", pd.Timestamp("2005-01-01"),
                  pd.Timestamp("2010-01-01"))])
    assert abio.link_ownership(own, names=nm).empty


# ── the residual arm ─────────────────────────────────────────────────────────
def _resid_frame(seed: int = 4, n: int = 2000) -> pd.DataFrame:
    """Synthetic panel with a KNOWN per-quarter linear structure.

    io is generated from the WINSORISED regressors, because the frozen spec
    winsorises them inside the regression — so an exactly-recoverable fit is the
    right prediction to pin. n is set to a realistic cross-section width: the
    1%/99% quantiles are only robust when the tail holds many names (a real
    quarter carries thousands), and a test at n=200 would be pinning an artefact
    of a two-point tail rather than the spec.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for q, fdate in enumerate([pd.Timestamp("2004-03-31"),
                               pd.Timestamp("2004-06-30")]):
        X = pd.DataFrame(rng.normal(size=(n, 5)), columns=abio.CHARS)
        g = pd.Series([fdate] * n)
        Xw = X.apply(lambda c: abio.winsorise_by(c, g))
        # a DIFFERENT true loading vector per quarter — only a per-quarter refit
        # can strip both
        beta = np.array([1.0, 2.0, -1.0, 0.5, 3.0]) * (1 if q == 0 else -2)
        d = X.copy()
        d["io"] = 0.3 + Xw.to_numpy() @ beta + rng.normal(0, 0.01, n)
        d["fdate"] = fdate
        d["sym"] = [f"s{i}" for i in range(n)]
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def test_regression_is_cross_sectional_per_quarter():
    """Each quarter gets its own fit. With opposite loadings per quarter, a
    POOLED regression leaves huge residuals; a per-quarter refit strips both to
    the noise floor (sd 0.01)."""
    d = _resid_frame()
    r = abio.residualise_per_quarter(d)
    for fdate, g in d.groupby("fdate"):
        assert r.loc[g.index].std() < 0.05, "quarter not independently fitted"
        assert abs(r.loc[g.index].mean()) < 1e-8, "intercept not fitted per quarter"
        # residual orthogonal to every regressor WITHIN the quarter (against the
        # winsorised regressor — that is what the frozen spec regresses on)
        gq = pd.Series([fdate] * len(g), index=g.index)
        for c in abio.CHARS:
            xw = abio.winsorise_by(g[c], gq)
            assert abs(np.corrcoef(r.loc[g.index], xw)[0, 1]) < 1e-6


def test_one_quarter_cannot_move_another_quarters_residuals():
    """Quarter independence, pinned directly: perturb Q2's io, Q1 must not move.
    A pooled or rolling fit would leak across the boundary."""
    d = _resid_frame()
    base = abio.residualise_per_quarter(d)
    q1 = d["fdate"] == pd.Timestamp("2004-03-31")

    d2 = d.copy()
    d2.loc[~q1, "io"] += 17.0
    after = abio.residualise_per_quarter(d2)
    pd.testing.assert_series_equal(base[q1.values], after[q1.values])


def test_names_with_any_missing_regressor_are_dropped():
    d = _resid_frame()
    d.loc[0, "log_age"] = np.nan
    r = abio.residualise_per_quarter(d)
    assert 0 not in r.dropna().index, "row with a missing regressor was kept"
    assert r.notna().sum() == len(d) - 1


def test_regressors_are_winsorised_per_quarter_inside_the_regression():
    """A single absurd outlier in one regressor must not drag the fit.

    Pinned as an EXACT no-op rather than a tolerance. Take a name already above
    its quarter's 99th percentile of log_mktcap and push it to 1e9. It was
    clipped to q99 before and is clipped to q99 now, and q99 itself is unmoved
    (it is interpolated well below the contaminated tail), so the design matrix
    is bit-identical and EVERY residual must be unchanged.

    Without the winsorisation the same edit is catastrophic — asserted as the
    control, so the test fails if the clipping is ever silently dropped.
    """
    d = _resid_frame()
    clean = abio.residualise_per_quarter(d)
    q1m = d["fdate"] == pd.Timestamp("2004-03-31")
    q1 = d.index[q1m]

    top = d.loc[q1, "log_mktcap"].idxmax()          # already in the clipped tail
    assert d.loc[top, "log_mktcap"] > d.loc[q1, "log_mktcap"].quantile(0.99)

    d2 = d.copy()
    d2.loc[top, "log_mktcap"] = 1e9
    dirty = abio.residualise_per_quarter(d2)
    pd.testing.assert_series_equal(clean[q1], dirty[q1])   # exact, not approx

    # control: the SAME edit without winsorisation destroys the fit
    raw = d2.loc[q1]
    X = np.column_stack([np.ones(len(raw)), raw[abio.CHARS].to_numpy(float)])
    beta, *_ = np.linalg.lstsq(X, raw["io"].to_numpy(float), rcond=None)
    unwins = pd.Series(raw["io"].to_numpy(float) - X @ beta, index=raw.index)
    assert np.corrcoef(clean[q1], unwins)[0, 1] < 0.9, \
        "contamination too weak to prove the winsorisation is doing the work"
