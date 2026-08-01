"""TRIAL-EVENT-13DG spec tests — written BEFORE the one shot.

The arms have no model to leak through; what has to be right is the SPEC and
the plumbing under it. Four things would each answer a different question than
the one registered, silently:

  * an amendment slipping into any arm (ruling 1),
  * the 24-month gap rule reading the wrong history or the wrong direction,
  * the -1..0 announcement window being computed with an off-by-one, which
    would turn the trial's own pipeline sanity check into a lie,
  * the 13D-minus-13G contrast being computed arm-by-arm instead of on the
    pooled event month, which would double-count each month's market shock.

The announcement-window arithmetic gets the same treatment `test_daily_events`
gives the forward windows: a synthetic panel where the true CAR is known.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.factory import daily_events as de
from aegis_brain.factory import event_13dg as eg


# ── fixtures ─────────────────────────────────────────────────────────────────
def _events(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["permno", "event_date", "form_type"])
    df["event_date"] = pd.to_datetime(df["event_date"])
    df["accession"] = [f"acc-{i}" for i in range(len(df))]
    return df


def _calendar(n: int = 400) -> pd.DatetimeIndex:
    return pd.bdate_range("2010-01-04", periods=n)


def _daily(calendar, permnos, base_ret=0.0):
    return pd.concat(
        [pd.DataFrame({"permno": p, "date": calendar, "ret": base_ret,
                       "dollar_vol": 1e9 - i * 1e6})
         for i, p in enumerate(permnos)], ignore_index=True)


# ── frozen constants ─────────────────────────────────────────────────────────
def test_frozen_constants():
    assert eg.ARMS == ("13d_all", "13g_all", "13d_first")
    assert eg.FIRST_GAP_MONTHS == 24
    assert eg.DECIDING_WINDOWS == ((1, 5), (1, 20), (1, 60))
    assert eg.ANNOUNCEMENT_WINDOW == (-1, 0)
    assert eg.CONTRAST_T_BAR == 2.0
    assert (eg.EXPLORE_START, eg.EXPLORE_END) == ("2004-01-01", "2018-12-31")
    assert eg.ERA_SPLIT == "2011-01-01"


def test_explore_window_never_reaches_confirm():
    df = _events([(1, "2018-12-31", "SC 13D"), (1, "2019-01-02", "SC 13D")])
    out = eg.in_explore(df)
    assert len(out) == 1 and out["event_date"].iloc[0].year == 2018


# ── ruling 1: amendments are excluded from ALL arms ──────────────────────────
def test_amendments_are_excluded_from_every_arm():
    df = _events([
        (1, "2006-03-01", "SC 13D"), (1, "2006-04-01", "SC 13D/A"),
        (2, "2006-03-01", "SC 13G"), (2, "2006-04-01", "SC 13G/A"),
    ])
    arms = eg.build_arms(df)
    assert len(arms["13d_all"]) == 1
    assert len(arms["13g_all"]) == 1
    assert len(arms["13d_first"]) == 1
    for a in arms.values():
        assert set(a.columns) == {"permno", "event_date"}


def test_13g_arm_holds_no_13d_and_vice_versa():
    df = _events([(1, "2006-03-01", "SC 13D"), (2, "2006-03-01", "SC 13G")])
    arms = eg.build_arms(df)
    assert arms["13d_all"]["permno"].tolist() == [1]
    assert arms["13g_all"]["permno"].tolist() == [2]


# ── the 24-month gap rule ────────────────────────────────────────────────────
def test_24m_rule_drops_a_repeat_inside_the_window():
    df = _events([(1, "2006-01-10", "SC 13D"), (1, "2007-06-10", "SC 13D")])
    first = eg.first_in_24m(df)
    assert first["event_date"].dt.strftime("%Y-%m-%d").tolist() == ["2006-01-10"]


def test_24m_rule_keeps_a_repeat_outside_the_window():
    df = _events([(1, "2006-01-10", "SC 13D"), (1, "2008-01-11", "SC 13D")])
    first = eg.first_in_24m(df)
    assert len(first) == 2, "a 24-month-plus-one-day gap is a new campaign"


def test_24m_rule_boundary_is_inclusive_of_exactly_24_months():
    """Exactly 24 months earlier still counts as a prior filing — the gap must
    be strictly greater than 24 months to qualify as 'first'."""
    df = _events([(1, "2006-01-10", "SC 13D"), (1, "2008-01-10", "SC 13D")])
    first = eg.first_in_24m(df)
    assert first["event_date"].dt.strftime("%Y-%m-%d").tolist() == ["2006-01-10"]


def test_24m_lookback_reads_history_before_the_explore_window():
    """A 2004 filing preceded by a 2003 filing is NOT a first filing. Reading
    only the explore window would silently promote every early event."""
    df = _events([(1, "2003-06-01", "SC 13D"), (1, "2004-02-01", "SC 13D")])
    assert len(eg.first_in_24m(df)) == 0


def test_24m_rule_is_per_name():
    df = _events([(1, "2006-01-10", "SC 13D"), (2, "2006-02-10", "SC 13D")])
    assert len(eg.first_in_24m(df)) == 2


def test_same_day_sibling_is_not_a_prior_filing():
    df = _events([(1, "2006-01-10", "SC 13D"), (1, "2006-01-10", "SC 13D")])
    assert len(eg.first_in_24m(df)) == 2


def test_amendments_do_not_disqualify_a_first_filing():
    """Ruling 1 excludes amendments from all arms, so a 13D/A is not a 'prior
    13D' for the gap rule either — otherwise the arm would be defined by rows
    the trial has declared to be non-events."""
    df = _events([(1, "2006-01-10", "SC 13D/A"), (1, "2006-06-10", "SC 13D")])
    assert len(eg.first_in_24m(df)) == 1


def test_13d_first_is_a_subset_of_13d_all():
    rng = np.random.default_rng(2)
    rows = [(int(p), d, "SC 13D") for p, d in
            zip(rng.integers(1, 20, 200),
                pd.to_datetime("2004-01-01") + pd.to_timedelta(
                    rng.integers(0, 5000, 200), unit="D"))]
    arms = eg.build_arms(_events(rows))
    a, b = arms["13d_all"], arms["13d_first"]
    assert len(b) <= len(a)
    merged = b.merge(a, on=["permno", "event_date"], how="left", indicator=True)
    assert (merged["_merge"] == "both").all()


# ── the -1..0 announcement window ────────────────────────────────────────────
def test_announcement_window_recovers_a_known_two_day_car():
    """A +30 bps move on day -1 and +70 bps on day 0 must sum to exactly 100
    bps in the -1..0 window, and must NOT leak into any forward window."""
    cal = _calendar()
    permnos = list(range(1, 21))
    daily = _daily(cal, permnos)
    t0 = 100
    for p in permnos[:10]:
        daily.loc[(daily["permno"] == p) & (daily["date"] == cal[t0 - 1]),
                  "ret"] = 0.0030
        daily.loc[(daily["permno"] == p) & (daily["date"] == cal[t0]),
                  "ret"] = 0.0070

    panel = de.DailyEventPanel.build(daily, cal)
    events = pd.DataFrame({"permno": permnos[:10], "event_date": cal[t0]})
    windows = (eg.ANNOUNCEMENT_WINDOW, *eg.DECIDING_WINDOWS)
    summary, _ = de.run_event_study(events, panel, windows=windows)
    s = summary.set_index("window")
    assert s.loc["-1..0", "car_diff_bps"] == pytest.approx(100.0, abs=1e-6)
    assert s.loc["+1..+5", "car_diff_bps"] == pytest.approx(0.0, abs=1e-6)
    assert s.loc["+1..+60", "car_diff_bps"] == pytest.approx(0.0, abs=1e-6)


def test_announcement_window_is_flagged_non_tradable():
    """The window is reported; the harness marks it as what it is so no reader
    or downstream table can mistake it for a return an account could earn."""
    cal = _calendar()
    permnos = list(range(1, 21))
    panel = de.DailyEventPanel.build(_daily(cal, permnos), cal)
    events = pd.DataFrame({"permno": permnos[:10], "event_date": cal[100]})
    summary, _ = de.run_event_study(
        events, panel, windows=(eg.ANNOUNCEMENT_WINDOW, *eg.DECIDING_WINDOWS))
    s = summary.set_index("window")["tradable"]
    assert s["-1..0"] is np.False_ or s["-1..0"] is False or not s["-1..0"]
    assert all(bool(s[w]) for w in ("+1..+5", "+1..+20", "+1..+60"))


def test_adding_the_announcement_window_does_not_move_forward_windows():
    """The forward CARs must be byte-identical with and without the diagnostic
    window in the list — the slicing change must not disturb the banked path."""
    cal = _calendar()
    permnos = list(range(1, 21))
    daily = _daily(cal, permnos)
    rng = np.random.default_rng(9)
    daily["ret"] = rng.normal(0, 0.01, len(daily))
    panel = de.DailyEventPanel.build(daily, cal)
    events = pd.DataFrame({"permno": permnos[:10], "event_date": cal[100]})

    a, _ = de.run_event_study(events, panel)
    b, _ = de.run_event_study(
        events, panel, windows=(eg.ANNOUNCEMENT_WINDOW, *eg.DECIDING_WINDOWS))
    for w in ("+1..+5", "+1..+20", "+1..+60"):
        assert (a.set_index("window").loc[w, "car_diff_bps"]
                == b.set_index("window").loc[w, "car_diff_bps"])


# ── the contrast ─────────────────────────────────────────────────────────────
def test_clustered_ols_reproduces_the_harness_clustered_t_on_a_constant():
    """The contrast must use the SAME inference the rest of the harness uses.
    On a constant-only design the sandwich has to collapse onto the existing
    `clustered_t`, or the two numbers in the write-up are not comparable."""
    rng = np.random.default_rng(5)
    y = rng.normal(0.01, 0.05, 300)
    g = np.array([f"m{i % 20}" for i in range(300)])
    beta, se = eg.clustered_ols(y, np.ones((300, 1)), g)
    ref = de.clustered_t(pd.Series(y), pd.Series(g))
    assert beta[0] == pytest.approx(ref["mean"], rel=1e-10)
    assert beta[0] / se[0] == pytest.approx(ref["t_clustered"], rel=1e-8)


def test_contrast_recovers_a_known_difference():
    idx = pd.period_range("2004-01", periods=60, freq="M").astype(str)
    d = pd.Series(np.tile([0.03], 60))
    g = pd.Series(np.tile([0.01], 60))
    out = eg.contrast(d, pd.Series(idx), g, pd.Series(idx))
    assert out["contrast_bps"] == pytest.approx(200.0, abs=1e-6)
    assert out["car_13g_bps"] == pytest.approx(100.0, abs=1e-6)
    assert out["n_13d"] == 60 and out["n_13g"] == 60


def test_contrast_clusters_on_the_pooled_event_month():
    """Both arms file into the same calendar, so a month's market shock hits
    both. Pooling first means that shock cancels inside the contrast; the
    contrast is then far better identified than either arm on its own. If the
    two arms were summarised separately and differenced afterwards, the shared
    shock would enter both standard errors and the contrast would look noisy.
    """
    months = pd.Series(np.repeat([f"2004-{m:02d}" for m in range(1, 25)], 20))
    rng = np.random.default_rng(6)
    shock = {m: rng.normal(0, 0.05) for m in months.unique()}
    base = months.map(shock).to_numpy()
    d = pd.Series(base + 0.001 + rng.normal(0, 0.0005, len(months)))
    g = pd.Series(base + rng.normal(0, 0.0005, len(months)))

    out = eg.contrast(d, months, g, months)
    assert out["n_clusters"] == 24
    assert out["contrast_bps"] == pytest.approx(10.0, abs=1.0)

    arm_only = de.clustered_t(d, months)          # the 13D arm on its own
    assert abs(out["t_clustered"]) > 10 * abs(arm_only["t_clustered"]), \
        "the shared monthly shock must cancel inside the pooled contrast"


def test_contrast_reports_month_level_noise_as_noise():
    """The mirror case: when the 13D-minus-13G gap is itself month-level noise
    rather than a constant effect, the clustered contrast t must stay modest."""
    months = pd.Series(np.repeat([f"2004-{m:02d}" for m in range(1, 25)], 20))
    rng = np.random.default_rng(11)
    base = months.map({m: rng.normal(0, 0.05)
                       for m in months.unique()}).to_numpy()
    gap = months.map({m: rng.normal(0, 0.02) for m in months.unique()}).to_numpy()
    out = eg.contrast(pd.Series(base + gap), months, pd.Series(base), months)
    assert abs(out["t_clustered"]) < 3.0
