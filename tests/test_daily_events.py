"""Daily event-harness spec tests.

The harness decides nothing on its own, which is exactly why it has to be right
before any family is registered against it: a silent defect here would be
inherited by every event trial that follows. The properties pinned are the three
the module exists to guarantee — a known CAR is recovered exactly, the control
arm is genuinely uncontaminated, and delisting returns are not lost — plus the
no-look-ahead boundary at day 0.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.factory import daily_events as de


def _calendar(n: int = 400) -> pd.DatetimeIndex:
    """A synthetic trading calendar: weekdays only, so 'trading day' != 'day'."""
    return pd.bdate_range("2010-01-04", periods=n)


def _daily(calendar: pd.DatetimeIndex, permnos: list[int],
           base_ret: float = 0.0, dollar_vol=None) -> pd.DataFrame:
    rows = []
    for i, p in enumerate(permnos):
        rows.append(pd.DataFrame({
            "permno": p, "date": calendar, "ret": base_ret,
            "dollar_vol": (dollar_vol[i] if dollar_vol is not None
                           else 1e9 - i * 1e6),
        }))
    return pd.concat(rows, ignore_index=True)


# ── the known-CAR test ───────────────────────────────────────────────────────
def test_recovers_a_known_car_exactly():
    """Event names earn +10 bps/day on trading days +1..+5 and nothing after;
    controls earn zero. CAR(+1..+5) must be exactly 50 bps, and the longer
    windows must ALSO be 50 bps — the effect stops but the cumulation does not
    decay, which is the arithmetic the module claims.
    """
    cal = _calendar()
    permnos = list(range(1, 21))
    daily = _daily(cal, permnos)

    event_permnos = permnos[:10]
    event_date = cal[100]
    t0 = 100
    bump = 0.0010
    for p in event_permnos:
        m = (daily["permno"] == p) & daily["date"].isin(cal[t0 + 1:t0 + 6])
        daily.loc[m, "ret"] = bump

    panel = de.DailyEventPanel.build(daily, cal)
    events = pd.DataFrame({"permno": event_permnos, "event_date": event_date})
    summary, cars = de.run_event_study(events, panel)

    got = summary.set_index("window")["car_diff_bps"]
    assert got["+1..+5"] == pytest.approx(50.0, abs=1e-6)
    assert got["+1..+20"] == pytest.approx(50.0, abs=1e-6)
    assert got["+1..+60"] == pytest.approx(50.0, abs=1e-6)
    # the control leg is genuinely flat — the difference is not an artefact
    assert summary.set_index("window").loc["+1..+5", "car_control_bps"] == \
        pytest.approx(0.0, abs=1e-6)


def test_event_day_zero_is_excluded():
    """A one-day spike ON the event date must NOT enter any window. Windows open
    at +1 because information released on day 0 is not tradable at day-0 open.
    """
    cal = _calendar()
    permnos = list(range(1, 21))
    daily = _daily(cal, permnos)
    t0 = 100
    for p in permnos[:10]:
        daily.loc[(daily["permno"] == p) & (daily["date"] == cal[t0]),
                  "ret"] = 0.5           # +50% on the event day itself

    panel = de.DailyEventPanel.build(daily, cal)
    events = pd.DataFrame({"permno": permnos[:10], "event_date": cal[t0]})
    summary, _ = de.run_event_study(events, panel)
    assert summary["car_diff_bps"].abs().max() == pytest.approx(0.0, abs=1e-6)


def test_windows_are_trading_days_not_calendar_days():
    """+1..+5 spans five TRADING days, so a bump on the five business days after
    the event is fully captured even though they span a calendar week."""
    cal = _calendar()
    permnos = list(range(1, 21))
    daily = _daily(cal, permnos)
    t0 = 100
    assert (cal[t0 + 5] - cal[t0]).days == 7, "fixture must straddle a weekend"
    for p in permnos[:10]:
        m = (daily["permno"] == p) & daily["date"].isin(cal[t0 + 1:t0 + 6])
        daily.loc[m, "ret"] = 0.001

    panel = de.DailyEventPanel.build(daily, cal)
    events = pd.DataFrame({"permno": permnos[:10], "event_date": cal[t0]})
    summary, _ = de.run_event_study(events, panel)
    assert summary.set_index("window").loc["+1..+5", "car_diff_bps"] == \
        pytest.approx(50.0, abs=1e-6)


# ── the control arm ──────────────────────────────────────────────────────────
def test_control_has_no_event_within_the_exclusion_window():
    """THE property the §20 receipt demands. Every name is an event name at some
    point, but at staggered dates; each control returned must be event-free
    within +/-60 calendar days of the event it is matched to."""
    cal = _calendar()
    permnos = list(range(1, 41))
    daily = _daily(cal, permnos)
    panel = de.DailyEventPanel.build(daily, cal)

    rng = np.random.default_rng(7)
    events = pd.DataFrame({
        "permno": permnos,
        "event_date": [cal[i] for i in rng.integers(60, 340, len(permnos))],
    })
    matched = de.match_controls(events, panel)
    matched = matched.dropna(subset=["control_permno"])
    assert len(matched) > 0

    by_permno = events.groupby("permno")["event_date"].apply(list).to_dict()
    for _, r in matched.iterrows():
        for dt in by_permno.get(r["control_permno"], []):
            assert abs(dt - r["event_date"]).days > 60, \
                "a contaminated control was selected"
        assert r["control_permno"] != r["permno"]


def test_control_is_the_nearest_liquidity_rank():
    """Matching is on dollar-volume rank within segment+month, not arbitrary."""
    cal = _calendar()
    permnos = list(range(1, 11))
    dv = [1e9 - i * 1e7 for i in range(10)]        # strictly decreasing
    daily = _daily(cal, permnos, dollar_vol=dv)
    panel = de.DailyEventPanel.build(daily, cal)

    events = pd.DataFrame({"permno": [5], "event_date": [cal[100]]})
    matched = de.match_controls(events, panel)
    # permno 5 is rank 5; its neighbours are ranks 4 and 6 (permnos 4 and 6)
    assert matched["control_permno"].iloc[0] in (4, 6)


def test_selection_masquerading_as_drift_is_caught():
    """The §20 scenario, simulated end to end.

    Event names drift +10 bps/day for 20 days — but so does every other name in
    their liquidity segment, because it is a segment-wide move, not information.
    The raw event leg looks impressive; the control-differenced CAR must be zero.
    This is the test the 8-K trial did not have.
    """
    cal = _calendar()
    permnos = list(range(1, 21))
    daily = _daily(cal, permnos, base_ret=0.0)
    t0 = 100
    window = cal[t0 + 1:t0 + 21]
    daily.loc[daily["date"].isin(window), "ret"] = 0.0010   # EVERY name drifts

    panel = de.DailyEventPanel.build(daily, cal)
    events = pd.DataFrame({"permno": permnos[:10], "event_date": cal[t0]})
    summary, _ = de.run_event_study(events, panel)
    s = summary.set_index("window")
    assert s.loc["+1..+20", "car_event_bps"] == pytest.approx(200.0, abs=1e-6)
    assert s.loc["+1..+20", "car_diff_bps"] == pytest.approx(0.0, abs=1e-6)


# ── delisting ────────────────────────────────────────────────────────────────
def test_delisting_return_is_appended_after_the_last_quote():
    cal = _calendar(60)
    daily = _daily(cal[:30], [1])                  # name 1 stops after 30 days
    delist = pd.DataFrame({"permno": [1], "dlstdt": [cal[30]],
                           "dlstcd": [574], "dlret": [-0.7]})
    out = de.apply_delisting_returns(daily, delist, cal)
    tail = out[out["permno"] == 1].sort_values("date").iloc[-1]
    assert tail["date"] == cal[30]
    assert tail["ret"] == pytest.approx(-0.7)


def test_missing_dlret_is_not_silently_invented():
    cal = _calendar(60)
    daily = _daily(cal[:30], [1])
    delist = pd.DataFrame({"permno": [1], "dlstdt": [cal[30]],
                           "dlstcd": [574], "dlret": [np.nan]})
    out = de.apply_delisting_returns(daily, delist, cal)
    assert len(out) == len(daily), "a missing dlret must not become a number"

    opt = de.apply_delisting_returns(daily, delist, cal, missing_dlret="shumway")
    assert opt[opt["permno"] == 1]["ret"].iloc[-1] == pytest.approx(-0.30)


def test_delisting_return_reaches_the_car():
    """A name that delists at -70% inside the window must carry that loss into
    its CAR. Without the dsedelist join (dsf.ret does NOT contain it, verified
    on real data) this CAR would be ~0 and every distress study biased upward.
    """
    cal = _calendar()
    permnos = list(range(1, 21))
    t0 = 100
    daily = _daily(cal, permnos)
    daily = daily[~((daily["permno"] == 1) & (daily["date"] > cal[t0 + 2]))]
    delist = pd.DataFrame({"permno": [1], "dlstdt": [cal[t0 + 3]],
                           "dlstcd": [574], "dlret": [-0.7]})
    daily = de.apply_delisting_returns(daily, delist, cal)

    panel = de.DailyEventPanel.build(daily, cal)
    events = pd.DataFrame({"permno": [1], "event_date": [cal[t0]]})
    _, cars = de.run_event_study(events, panel)
    assert cars["car_1_5"].iloc[0] == pytest.approx(-0.7, abs=1e-9)


# ── inference ────────────────────────────────────────────────────────────────
def test_clustered_t_is_not_inflated_by_repeated_months():
    """Perfectly clustered data: 40 events in 4 months, identical within month.
    There are really only 4 independent observations. The iid t treats them as
    40 and inflates; the clustered t must be materially smaller.
    """
    vals, months = [], []
    for m, v in enumerate([0.01, 0.012, 0.008, 0.011]):
        vals += [v] * 10
        months += [f"2010-{m + 1:02d}"] * 10
    r = de.clustered_t(pd.Series(vals), pd.Series(months))
    assert r["n"] == 40 and r["n_clusters"] == 4
    assert abs(r["t_clustered"]) < abs(r["t_iid"]) / 2


def test_clustered_and_iid_agree_when_every_event_is_its_own_month():
    """With one event per cluster the correction is only G/(G-1) — the two t's
    must agree closely, proving the clustering is not a blanket haircut."""
    rng = np.random.default_rng(3)
    x = pd.Series(rng.normal(0.01, 0.02, 60))
    g = pd.Series([f"m{i}" for i in range(60)])
    r = de.clustered_t(x, g)
    assert r["t_clustered"] == pytest.approx(r["t_iid"], rel=0.05)
