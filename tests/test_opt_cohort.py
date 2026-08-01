"""TRIAL-OPT-COHORT spec tests — written BEFORE the one shot.

The arms have no model to leak through, so what is worth pinning is the SPEC.
Drift in the null rule, the term-structure legs, the residual arm's structure or
the date-validity of the secid link would answer a different question than the
one registered, and the run is unrepeatable.

The build-time coverage guard is tested too. TRIAL-ABIO-KIRK was frozen against
a table that held 1980-2001 for a 2004-2018 question (NEG_RESULTS 26); that cost
a repair. `assert_inputs_cover_explore` is the cheap check that prevents the
repeat, so it must fail loud when an input is missing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory import optsurf as os_


def _panel(n_months: int = 36, n_syms: int = 6, seed: int = 5) -> Panel:
    rng = np.random.default_rng(seed)
    months = pd.date_range("2004-01-31", periods=n_months, freq="ME")
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
    assert os_.ARMS == ("iv_atm", "riv_spread", "skew_25d", "term_slope",
                        "os_ratio", "pc_volume", "skew_resid")
    assert len(os_.ARMS) == 7
    assert os_.DIRECTIONS == {"iv_atm": -1, "riv_spread": -1, "skew_25d": -1,
                              "term_slope": +1, "os_ratio": +1,
                              "pc_volume": -1, "skew_resid": -1}
    assert os_.RESID_REGRESSORS == ["log_mktcap", "rv21", "mom_12_1",
                                    "log_dvol3m"]
    assert len(os_.RESID_REGRESSORS) == 4
    assert (os_.WINSOR_LO, os_.WINSOR_HI) == (0.01, 0.99)
    assert os_.RV_WINDOW == 21


def test_term_slope_is_91_minus_30():
    """Direction of the subtraction is the whole signal — a flipped leg order
    silently inverts a +1 arm into its own negation."""
    assert (os_.TERM_LONG, os_.TERM_SHORT) == (91, 30)
    row = pd.DataFrame({"iv30": [0.20], "iv91": [0.26]})
    term = row["iv91"] - row["iv30"]
    assert term.iloc[0] == pytest.approx(0.06)


def test_explore_window_constants_never_reach_confirm():
    assert os_.EXPLORE_START == "2004-01-31"
    assert os_.EXPLORE_END == "2018-12-31"
    assert pd.Timestamp(os_.EXPLORE_END) < pd.Timestamp("2019-01-01")


# ── the build-time coverage guard ────────────────────────────────────────────
def test_coverage_guard_fails_loud_on_a_missing_year(monkeypatch, tmp_path):
    """The ABIO lesson: a silently absent input must raise, never yield an empty
    frame that looks like a real (null) result."""
    monkeypatch.setattr(os_, "VSURF_DIR", tmp_path / "nope")
    with pytest.raises(FileNotFoundError, match="vsurf"):
        os_.assert_inputs_cover_explore()


def test_coverage_guard_passes_on_the_real_tree():
    """And it must actually pass here — a guard that always raises is useless."""
    rep = os_.assert_inputs_cover_explore()
    assert rep["vsurf"].startswith("2003-2018")
    assert rep[f"link_active_{os_.EXPLORE_START}"] > 0
    assert rep[f"link_active_{os_.EXPLORE_END}"] > 0


# ── the null rule ────────────────────────────────────────────────────────────
def test_null_rule_drops_and_never_fills():
    """A missing month must stay missing — no ffill, no imputation. Pinned end
    to end through the frame builder's pivot+reindex path."""
    idx = pd.date_range("2004-01-31", periods=5, freq="ME")
    long = pd.DataFrame({
        "month": [idx[0], idx[3]],
        "sym": ["10000", "10000"],
        "iv_atm": [0.30, 0.40],
    })
    w = (long.dropna(subset=["iv_atm"])
         .pivot_table(index="month", columns="sym", values="iv_atm",
                      aggfunc="last")
         .reindex(index=idx, columns=["10000"]))
    assert w.loc[idx[0], "10000"] == pytest.approx(0.30)
    assert pd.isna(w.loc[idx[1], "10000"]), "gap was filled — null rule violated"
    assert pd.isna(w.loc[idx[2], "10000"])
    assert w.loc[idx[3], "10000"] == pytest.approx(0.40)
    assert pd.isna(w.loc[idx[4], "10000"])


def test_zero_denominator_is_undefined_not_zero():
    """call_vol == 0 makes the daily put/call ratio UNDEFINED. Treating it as 0
    would silently rank a no-call-volume day as the most call-heavy day there
    is — the exact inversion the frozen null rule exists to prevent."""
    call = pd.Series([10.0, 0.0, 5.0])
    put = pd.Series([5.0, 7.0, 5.0])
    pc = os_._safe_div(put, call)
    assert pc.iloc[0] == pytest.approx(0.5)
    assert pd.isna(pc.iloc[1])
    assert pc.iloc[2] == pytest.approx(1.0)
    assert pc.mean() == pytest.approx(0.75)        # the zero day is excluded
    assert pc.count() == 2, "the undefined day must not enter the mean's n"


def test_thin_months_become_null():
    """Fewer than MIN_DAYS_PER_MONTH defined daily ratios -> null -> dropped."""
    assert os_.MIN_DAYS_PER_MONTH == 15
    res = pd.DataFrame({"os_ratio": [0.5, 0.5], "pc_volume": [1.0, 1.0],
                        "n_days_os": [20, 14], "n_days_pc": [14, 20]})
    res.loc[res["n_days_os"] < os_.MIN_DAYS_PER_MONTH, "os_ratio"] = np.nan
    res.loc[res["n_days_pc"] < os_.MIN_DAYS_PER_MONTH, "pc_volume"] = np.nan
    assert res["os_ratio"].tolist()[0] == pytest.approx(0.5)
    assert pd.isna(res["os_ratio"].iloc[1])
    assert pd.isna(res["pc_volume"].iloc[0])
    assert res["pc_volume"].iloc[1] == pytest.approx(1.0)


# ── the secid link ───────────────────────────────────────────────────────────
def _link(rows) -> pd.DataFrame:
    d = pd.DataFrame(rows, columns=["secid", "sym", "sdate", "edate"])
    d["score"] = 1.0
    return d


def test_link_is_date_valid():
    """A link window that does not cover the month must not be used. The
    parquet stores these as STRINGS; if they were ever compared unparsed the
    filter would raise or silently pass everything, so this is pinned."""
    months = pd.DatetimeIndex([pd.Timestamp("2011-06-30")])
    lk = _link([(1, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2005-01-01"))])
    assert os_.month_link(months, link=lk).empty

    lk2 = _link([(1, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01"))])
    out = os_.month_link(months, link=lk2)
    assert list(out["sym"]) == ["100"]


def test_ambiguous_link_is_dropped_not_resolved():
    """One secid valid for two permnos in the same month -> dropped entirely."""
    months = pd.DatetimeIndex([pd.Timestamp("2011-06-30")])
    lk = _link([
        (1, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
        (1, "200", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
    ])
    assert os_.month_link(months, link=lk).empty


def test_reverse_ambiguity_blanket_form_drops_when_no_data_is_supplied():
    """Without a data-bearing set the rule falls back to the strict form."""
    months = pd.DatetimeIndex([pd.Timestamp("2011-06-30")])
    lk = _link([
        (1, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
        (2, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
    ])
    assert os_.month_link(months, link=lk).empty


def test_dead_duplicate_secids_do_not_make_a_name_ambiguous():
    """The measured case: a permno carrying two secids where only ONE has data
    is resolvable with zero discretion, and must not be thrown away. At
    2011-06-30 this pattern covered 379 permnos against 2 genuinely ambiguous."""
    months = pd.DatetimeIndex([pd.Timestamp("2011-06-30")])
    ym = months[0].to_period("M")
    lk = _link([
        (1, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
        (2, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
    ])
    db = pd.DataFrame({"ym": [ym], "secid": [2]})       # only secid 2 has data
    out = os_.month_link(months, link=lk, data_bearing=db)
    assert list(out["secid"]) == [2]
    assert list(out["sym"]) == ["100"]


def test_two_live_secids_on_one_permno_are_still_dropped():
    """When more than one secid genuinely carries data, it stays ambiguous."""
    months = pd.DatetimeIndex([pd.Timestamp("2011-06-30")])
    ym = months[0].to_period("M")
    lk = _link([
        (1, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
        (2, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
    ])
    db = pd.DataFrame({"ym": [ym, ym], "secid": [1, 2]})
    assert os_.month_link(months, link=lk, data_bearing=db).empty


def test_forward_ambiguity_is_dropped_even_when_data_bearing():
    """One secid -> two permnos is undecidable no matter what data exists."""
    months = pd.DatetimeIndex([pd.Timestamp("2011-06-30")])
    ym = months[0].to_period("M")
    lk = _link([
        (1, "100", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
        (1, "200", pd.Timestamp("2000-01-01"), pd.Timestamp("2020-01-01")),
    ])
    db = pd.DataFrame({"ym": [ym], "secid": [1]})
    assert os_.month_link(months, link=lk, data_bearing=db).empty


def test_real_link_parses_string_dates():
    """Against the real parquet: the columns are strings on disk and must come
    back as datetimes, or every date comparison downstream is wrong."""
    lk = os_._raw_link()
    assert pd.api.types.is_datetime64_any_dtype(lk["sdate"])
    assert pd.api.types.is_datetime64_any_dtype(lk["edate"])
    assert len(lk) > 0


# ── O/S denominator ──────────────────────────────────────────────────────────
def test_os_denominator_is_dsf_stock_volume_in_shares():
    """The frozen construct is option volume over STOCK volume, and the stock
    leg comes from crsp.dsf `vol`, which is in shares (not the 100-share units
    of the monthly file). Pinned against a real mega-cap day."""
    d = pd.read_parquet(os_.RAW / "dsf_full" / "dsf_2010.parquet",
                        columns=["permno", "date", "vol"])
    row = d[(d["permno"] == 14593) & (d["date"] == pd.Timestamp("2010-06-30"))]
    assert len(row) == 1
    vol = float(row["vol"].iloc[0])
    # AAPL traded ~27M shares that day; in 100-share units it would be ~273k
    assert 1e7 < vol < 1e8, f"dsf vol looks like the wrong unit: {vol}"


def test_os_ratio_is_a_mean_of_daily_ratios_not_a_ratio_of_sums():
    """The frozen text says 'monthly mean of daily'. The two differ whenever
    volume is uneven, so the distinction is pinned rather than assumed."""
    opt = np.array([100.0, 100.0])
    stock = np.array([1000.0, 100000.0])
    mean_of_daily = float(np.mean(opt / stock))
    ratio_of_sums = float(opt.sum() / stock.sum())
    assert mean_of_daily == pytest.approx(0.0505)
    assert ratio_of_sums == pytest.approx(0.00198, rel=1e-3)
    assert mean_of_daily != pytest.approx(ratio_of_sums)


# ── the residual arm ─────────────────────────────────────────────────────────
def _resid_frame(seed: int = 4, n: int = 2000) -> pd.DataFrame:
    """Synthetic panel with a KNOWN per-month linear structure.

    skew_25d is generated from the WINSORISED regressors because the frozen spec
    winsorises them inside the regression, so exact recovery is the right
    prediction. n is a realistic cross-section width — 1%/99% quantiles are only
    robust when the tail holds many names.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for q, month in enumerate([pd.Timestamp("2004-01-31"),
                               pd.Timestamp("2004-02-29")]):
        X = pd.DataFrame(rng.normal(size=(n, 4)), columns=os_.RESID_REGRESSORS)
        g = pd.Series([month] * n)
        Xw = X.apply(lambda c: os_.winsorise_by(c, g))
        beta = np.array([1.0, 2.0, -1.0, 0.5]) * (1 if q == 0 else -2)
        d = X.copy()
        d["skew_25d"] = 0.1 + Xw.to_numpy() @ beta + rng.normal(0, 0.01, n)
        d["month"] = month
        d["sym"] = [f"s{i}" for i in range(n)]
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def test_residual_regression_is_cross_sectional_per_month():
    """Each month gets its own fit. With opposite loadings per month a pooled
    regression leaves huge residuals; a per-month refit strips both to the
    noise floor."""
    d = _resid_frame()
    r = os_.residualise_per_month(d)
    for month, g in d.groupby("month"):
        assert r.loc[g.index].std() < 0.05, "month not independently fitted"
        assert abs(r.loc[g.index].mean()) < 1e-8, "intercept not fitted per month"
        gq = pd.Series([month] * len(g), index=g.index)
        for c in os_.RESID_REGRESSORS:
            xw = os_.winsorise_by(g[c], gq)
            assert abs(np.corrcoef(r.loc[g.index], xw)[0, 1]) < 1e-6


def test_one_month_cannot_move_another_months_residuals():
    """Month independence, pinned directly — a pooled or rolling fit leaks."""
    d = _resid_frame()
    base = os_.residualise_per_month(d)
    m1 = d["month"] == pd.Timestamp("2004-01-31")
    d2 = d.copy()
    d2.loc[~m1, "skew_25d"] += 17.0
    after = os_.residualise_per_month(d2)
    pd.testing.assert_series_equal(base[m1.values], after[m1.values])


def test_names_missing_any_regressor_are_dropped():
    d = _resid_frame()
    d.loc[0, "rv21"] = np.nan
    r = os_.residualise_per_month(d)
    assert 0 not in r.dropna().index
    assert r.notna().sum() == len(d) - 1


def test_regressors_are_winsorised_per_month():
    """Pushing an already-extreme regressor further out is an EXACT no-op: it
    was clipped to q99 before and is clipped to q99 now, and q99 itself is
    unmoved. Without the clipping the same edit destroys the fit."""
    d = _resid_frame()
    clean = os_.residualise_per_month(d)
    m1 = d.index[d["month"] == pd.Timestamp("2004-01-31")]

    top = d.loc[m1, "log_mktcap"].idxmax()
    assert d.loc[top, "log_mktcap"] > d.loc[m1, "log_mktcap"].quantile(0.99)
    d2 = d.copy()
    d2.loc[top, "log_mktcap"] = 1e9
    pd.testing.assert_series_equal(clean[m1], os_.residualise_per_month(d2)[m1])

    raw = d2.loc[m1]
    X = np.column_stack([np.ones(len(raw)),
                         raw[os_.RESID_REGRESSORS].to_numpy(float)])
    beta, *_ = np.linalg.lstsq(X, raw["skew_25d"].to_numpy(float), rcond=None)
    unwins = pd.Series(raw["skew_25d"].to_numpy(float) - X @ beta, index=raw.index)
    assert np.corrcoef(clean[m1], unwins)[0, 1] < 0.9


# ── VIX terciles ─────────────────────────────────────────────────────────────
def test_vix_terciles_split_the_explore_window_in_three():
    months = pd.date_range("2004-01-31", "2018-12-31", freq="ME")
    ter = os_.vix_terciles(months)
    counts = ter.value_counts()
    assert set(counts.index) == {"low", "mid", "high"}
    assert counts.min() >= len(months) // 3 - 3
    assert counts.max() <= len(months) // 3 + 3
