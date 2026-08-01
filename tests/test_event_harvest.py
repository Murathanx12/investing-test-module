"""TRIAL-EVENT-13DG-HARVEST spec tests — written BEFORE the one shot.

This stage exists because the book stage measured the wrong thing. Its whole
validity rests on two mechanisms, and each has a failure mode that would run
green while silently answering the predecessor's question again:

  * THE CONTROL. If the matching rule here is not byte-for-byte the parent
    trial's, the "cohort-matched" claim is decoration. Pinned by calling the
    parent's function and asserting the outputs are identical objects, plus
    the +/-60cd exclusion constant.
  * THE GATE. If the real number is computed before the placebo is read, the
    gate is a formality that could be rationalised away after the fact. Pinned
    by a `real_fn` that RAISES: if it is ever called on a failed gate, the test
    explodes rather than passing quietly.

Then the accounting, where four errors would each flatter us:

  * an entry that precedes the filing (lookahead),
  * legs measured over different windows (the control leg silently shifted),
  * the entry month's own return reaching the book (the pop we forfeit),
  * costs that are flat rather than per-name and size-aware, or that leak onto
    the control leg (which the freeze says pays nothing).

And one with no direction: the explore wall must bind the WINDOW, not just the
event date, or a 2018-11 filing reads confirm returns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory import daily_events as de
from aegis_brain.factory import event_book as eb
from aegis_brain.factory import event_harvest as eh


# ── fixtures ─────────────────────────────────────────────────────────────────
def _panel(n_months: int = 48, n_syms: int = 40, seed: int = 7) -> Panel:
    rng = np.random.default_rng(seed)
    months = pd.date_range("2004-01-31", periods=n_months, freq="ME")
    syms = [str(10000 + i) for i in range(n_syms)]
    return Panel(
        monthly_ret=pd.DataFrame(rng.normal(0.005, 0.04, (n_months, n_syms)),
                                 index=months, columns=syms),
        month_end_price=pd.DataFrame(50.0, index=months, columns=syms),
        monthly_dollar_vol=pd.DataFrame(
            np.tile(np.linspace(1e9, 1e8, n_syms), (n_months, 1)),
            index=months, columns=syms),
        delist_month={s: months[-1] for s in syms})


def _matched(rows) -> pd.DataFrame:
    """(permno, control_permno, event_date) — as `match_parent_controls` emits."""
    df = pd.DataFrame(rows, columns=["permno", "control_permno", "event_date"])
    df["event_date"] = pd.to_datetime(df["event_date"])
    return df


def _legs(panel, matched, spread=None, cfg=None):
    cfg = cfg or eh.HarvestConfig()
    elig = eb.eligible_universe(panel, eb.BookConfig(max_rank=cfg.max_rank))
    return eh.compute_legs(matched, panel, elig, spread, cfg)


def _daily_panel(seed: int = 3) -> de.DailyEventPanel:
    """Small synthetic daily panel for the control-matching identity test."""
    rng = np.random.default_rng(seed)
    cal = pd.DatetimeIndex(pd.bdate_range("2004-01-01", "2004-12-31"))
    permnos = np.arange(10000, 10030)
    rows = []
    for i, p in enumerate(permnos):
        rows.append(pd.DataFrame({
            "permno": p, "date": cal,
            "ret": rng.normal(0, 0.02, len(cal)),
            "dollar_vol": 1e9 - i * 1e7}))
    return de.DailyEventPanel.build(pd.concat(rows, ignore_index=True), cal)


# ── frozen constants ─────────────────────────────────────────────────────────
def test_frozen_harvest_constants():
    cfg = eh.HarvestConfig()
    assert cfg.hold_months == 3
    assert cfg.max_rank == 3000
    assert cfg.flat_cost_bps_one_way == 25.0
    assert cfg.explore_start == "2004-01-01"
    assert cfg.explore_end == "2018-12-31", "the harvest never reads confirm"
    assert cfg.exclusion_days == 60
    assert cfg.placebo_seeds == (0, 1, 2, 3, 4)
    assert cfg.placebo_t_bar == 2.0
    assert cfg.bar_t == 1.5


# ── the control rule IS the parent's ─────────────────────────────────────────
def test_control_matching_is_the_parent_trials_function_verbatim():
    """Not "equivalent to" — the same call, on the same fields, with the same
    exclusion. A reimplementation is free to drift; a delegation is not."""
    panel = _daily_panel()
    rng = np.random.default_rng(11)
    ev = pd.DataFrame({
        "permno": rng.choice(np.arange(10000, 10030), 40),
        "event_date": pd.to_datetime(
            rng.choice(pd.bdate_range("2004-02-02", "2004-11-30"), 40))})
    mine = eh.match_parent_controls(ev, panel)
    parent = de.match_controls(ev, panel, de.CONTROL_EXCLUSION_DAYS)
    pd.testing.assert_frame_equal(mine, parent)


def test_control_match_fields_are_segment_month_and_nearest_rank():
    """The parent's matching fields, asserted on the output rather than trusted:
    a control shares the event's calendar month and segment, is never the event
    name itself, and is the nearest available dollar-volume rank."""
    panel = _daily_panel()
    ev = pd.DataFrame({"permno": [10005, 10020],
                       "event_date": pd.to_datetime(["2004-05-14",
                                                     "2004-08-10"])})
    m = eh.match_parent_controls(ev, panel).dropna(subset=["control_permno"])
    assert len(m) == 2
    for _, r in m.iterrows():
        assert r["control_permno"] != r["permno"]
        pool = panel.ranks[(panel.ranks["ym"] == r["ym"])
                           & (panel.ranks["segment"] == r["segment"])]
        assert int(r["control_permno"]) in set(pool["permno"])
        crank = float(pool.loc[pool["permno"] == r["control_permno"],
                               "rank"].iloc[0])
        others = pool[pool["permno"] != r["permno"]]
        best = (others["rank"] - r["rank"]).abs().min()
        assert abs(crank - r["rank"]) == pytest.approx(best)


def test_a_contaminated_control_is_rejected_within_60_calendar_days():
    """The +/-60cd exclusion is what makes the control a NON-event name. If it
    were dropped, the control leg would quietly contain events of its own."""
    panel = _daily_panel()
    ev = pd.DataFrame({"permno": [10005, 10006],
                       "event_date": pd.to_datetime(["2004-05-14",
                                                     "2004-05-20"])})
    m = eh.match_parent_controls(ev, panel).dropna(subset=["control_permno"])
    for _, r in m.iterrows():
        assert r["control_permno"] not in (10005, 10006), \
            "a control with its own event inside +/-60cd is contaminated"


# ── entry timing ─────────────────────────────────────────────────────────────
def test_entry_never_precedes_the_filing_date():
    months = _panel().monthly_ret.index
    rng = np.random.default_rng(2)
    for _ in range(300):
        d = months[0] + pd.Timedelta(days=int(rng.integers(0, 1200)))
        i = eb.entry_index(d, months)
        if i is not None:
            assert months[i] >= d, "entry month-end precedes the filing"


def test_the_window_never_contains_the_entry_months_own_return():
    """The pop this design forfeits must actually be forfeited."""
    panel = _panel()
    months = panel.monthly_ret.index
    panel.monthly_ret.loc[:, :] = 0.0
    panel.monthly_ret.loc[months[5], "10000"] = 1.0      # the entry month itself
    legs, _ = _legs(panel, _matched([(10000, 10001, months[5])]))
    assert legs["event_gross"].iloc[0] == pytest.approx(0.0)


def test_the_window_is_exactly_three_monthly_returns_and_compounds():
    panel = _panel()
    months = panel.monthly_ret.index
    panel.monthly_ret.loc[:, :] = 0.0
    panel.monthly_ret.loc[:, "10000"] = 0.10
    legs, _ = _legs(panel, _matched([(10000, 10001, months[5])]))
    assert legs["event_gross"].iloc[0] == pytest.approx(1.10 ** 3 - 1)
    assert str(legs["entry_month"].iloc[0]) == "2004-06"
    assert str(legs["exit_month"].iloc[0]) == "2004-09"


def test_both_legs_share_the_identical_window():
    """The control must be measured over the SAME three months. A leg shifted
    by one month would be a different benchmark wearing the same name."""
    panel = _panel()
    months = panel.monthly_ret.index
    panel.monthly_ret.loc[:, :] = 0.0
    # only months 6,7,8 are inside the window for an entry at month 5
    panel.monthly_ret.loc[months[6:9], "10001"] = 0.10
    panel.monthly_ret.loc[months[5], "10001"] = 5.0      # before the window
    panel.monthly_ret.loc[months[9], "10001"] = 5.0      # after the window
    legs, _ = _legs(panel, _matched([(10000, 10001, months[5])]))
    assert legs["control_gross"].iloc[0] == pytest.approx(1.10 ** 3 - 1)


def test_both_legs_move_together_when_the_window_shifts():
    panel = _panel()
    months = panel.monthly_ret.index
    panel.monthly_ret.loc[:, :] = 0.0
    panel.monthly_ret.loc[months[10:13], ["10000", "10001"]] = 0.05
    early, _ = _legs(panel, _matched([(10000, 10001, months[5])]))
    late, _ = _legs(panel, _matched([(10000, 10001, months[9])]))
    assert early["diff_gross"].iloc[0] == pytest.approx(0.0)
    assert late["diff_gross"].iloc[0] == pytest.approx(0.0)
    assert late["event_gross"].iloc[0] == pytest.approx(1.05 ** 3 - 1)


# ── costs: event leg only, per name, size aware ──────────────────────────────
def test_costs_hit_the_event_leg_only():
    """The freeze: the control is a paper benchmark and pays nothing —
    conservative against us, so it must not quietly pay anything."""
    panel = _panel()
    months = panel.monthly_ret.index
    frame = pd.DataFrame(100.0, index=months, columns=panel.monthly_ret.columns)
    free, _ = _legs(panel, _matched([(10000, 10001, months[5])]),
                    spread=frame * 0.0)
    paid, _ = _legs(panel, _matched([(10000, 10001, months[5])]), spread=frame)
    assert paid["control_gross"].iloc[0] == pytest.approx(
        free["control_gross"].iloc[0]), "a cost leaked onto the control leg"
    assert paid["event_gross"].iloc[0] == pytest.approx(
        free["event_gross"].iloc[0]), "the event GROSS leg must be cost-free"
    assert paid["diff_net"].iloc[0] < free["diff_net"].iloc[0]


def test_the_cost_is_a_round_trip_at_entry_and_exit():
    panel = _panel()
    months = panel.monthly_ret.index
    frame = pd.DataFrame(0.0, index=months, columns=panel.monthly_ret.columns)
    frame.loc[months[5], "10000"] = 30.0        # entry month-end
    frame.loc[months[8], "10000"] = 70.0        # exit month-end
    frame.loc[months[6], "10000"] = 999.0       # mid-hold: not a trade
    legs, _ = _legs(panel, _matched([(10000, 10001, months[5])]), spread=frame)
    assert legs["cost"].iloc[0] == pytest.approx(100.0 / 1e4)


def test_the_cost_is_per_name_and_size_aware():
    panel = _panel()
    months = panel.monthly_ret.index
    frame = pd.DataFrame(5.0, index=months, columns=panel.monthly_ret.columns)
    frame.loc[:, "10002"] = 400.0
    legs, _ = _legs(panel, _matched([(10000, 10001, months[5]),
                                     (10002, 10003, months[5])]), spread=frame)
    cheap = legs.loc[legs["permno"] == 10000, "cost"].iloc[0]
    dear = legs.loc[legs["permno"] == 10002, "cost"].iloc[0]
    assert dear > cheap * 10, "a flat charge cannot be the deciding arm"


def test_a_name_missing_from_the_spread_frame_falls_back_to_the_flat_guard():
    panel = _panel()
    months = panel.monthly_ret.index
    frame = pd.DataFrame(np.nan, index=months, columns=panel.monthly_ret.columns)
    legs, _ = _legs(panel, _matched([(10000, 10001, months[5])]), spread=frame)
    assert legs["cost"].iloc[0] == pytest.approx(50.0 / 1e4)


def test_the_flat_guard_and_the_zero_cost_bound():
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _matched([(10000, 10001, months[5])])
    flat, _ = _legs(panel, ev, spread=None)
    zero, _ = _legs(panel, ev, spread=pd.DataFrame(
        0.0, index=months, columns=panel.monthly_ret.columns))
    assert flat["cost"].iloc[0] == pytest.approx(50.0 / 1e4)
    assert zero["cost"].iloc[0] == pytest.approx(0.0)
    assert zero["diff_net"].iloc[0] == pytest.approx(zero["diff_gross"].iloc[0])


def test_diff_net_is_event_net_minus_control_gross():
    panel = _panel()
    months = panel.monthly_ret.index
    legs, _ = _legs(panel, _matched([(10000 + 2 * i, 10001 + 2 * i, months[5])
                                     for i in range(5)]))
    np.testing.assert_allclose(
        legs["diff_net"], legs["event_gross"] - legs["cost"]
        - legs["control_gross"], atol=1e-12)


# ── eligibility and the explore wall ─────────────────────────────────────────
def test_a_name_ineligible_at_entry_produces_no_measurement():
    panel = _panel()
    months = panel.monthly_ret.index
    panel.month_end_price.loc[months[5], "10000"] = 0.10     # below the $1 floor
    legs, diag = _legs(panel, _matched([(10000, 10001, months[5]),
                                        (10002, 10003, months[5])]))
    assert diag["ineligible_at_entry"] == 1 and diag["measured"] == 1
    assert 10000 not in set(legs["permno"])


def test_the_explore_wall_binds_the_WINDOW_not_only_the_event():
    """A filing inside explore whose third month-end lands in 2019 must produce
    NO measurement. Its window would otherwise read confirm returns."""
    months = pd.date_range("2018-01-31", periods=18, freq="ME")   # into 2019
    syms = ["10000", "10001"]
    panel = Panel(
        monthly_ret=pd.DataFrame(0.01, index=months, columns=syms),
        month_end_price=pd.DataFrame(50.0, index=months, columns=syms),
        monthly_dollar_vol=pd.DataFrame(1e9, index=months, columns=syms),
        delist_month={s: months[-1] for s in syms})
    ok, diag_ok = _legs(panel, _matched([(10000, 10001, "2018-09-15")]))
    assert diag_ok["measured"] == 1
    assert str(ok["exit_month"].iloc[0]) == "2018-12"
    _, diag_bad = _legs(panel, _matched([(10000, 10001, "2018-10-15")]))
    assert diag_bad["measured"] == 0 and diag_bad["window_past_explore"] == 1, \
        "the panel HAS the 2019 returns; only the wall may stop this window"


def test_a_control_missing_from_the_panel_is_counted_not_crashed():
    panel = _panel()
    months = panel.monthly_ret.index
    _, diag = _legs(panel, _matched([(10000, 999999, months[5]),
                                     (10001, 10002, months[5])]))
    assert diag["control_not_in_panel"] == 1 and diag["measured"] == 1


def test_an_unmatched_event_never_reaches_a_measurement():
    panel = _panel()
    months = panel.monthly_ret.index
    m = _matched([(10000, 10001, months[5])])
    m.loc[1] = {"permno": 10002, "control_permno": np.nan,
                "event_date": months[5]}
    _, diag = _legs(panel, m)
    assert diag["no_control"] == 1 and diag["measured"] == 1


# ── the placebo redraw ───────────────────────────────────────────────────────
def test_the_redraw_preserves_each_permnos_event_count():
    ev = pd.DataFrame({"permno": [1, 1, 1, 2, 3, 3],
                       "event_date": pd.to_datetime(
                           ["2005-03-04"] * 3 + ["2009-07-01"]
                           + ["2012-02-02"] * 2)})
    for seed in range(5):
        out = eh.redraw_filing_dates(ev, seed)
        pd.testing.assert_series_equal(
            out["permno"].value_counts().sort_index(),
            ev["permno"].value_counts().sort_index())


def test_the_redraw_stays_inside_the_explore_window_and_moves_the_dates():
    cfg = eh.HarvestConfig()
    ev = pd.DataFrame({"permno": np.arange(500),
                       "event_date": pd.to_datetime(["2010-06-15"] * 500)})
    out = eh.redraw_filing_dates(ev, 0)
    assert out["event_date"].min() >= pd.Timestamp(cfg.explore_start)
    assert out["event_date"].max() <= pd.Timestamp(cfg.explore_end)
    assert out["event_date"].nunique() > 100, "the timing must be destroyed"


def test_the_redraw_is_seed_reproducible_and_seed_dependent():
    ev = pd.DataFrame({"permno": np.arange(200),
                       "event_date": pd.to_datetime(["2010-06-15"] * 200)})
    a = eh.redraw_filing_dates(ev, 0)
    b = eh.redraw_filing_dates(ev, 0)
    c = eh.redraw_filing_dates(ev, 1)
    pd.testing.assert_frame_equal(a, b)
    assert not a["event_date"].equals(c["event_date"])


# ── the gate ─────────────────────────────────────────────────────────────────
def test_the_gate_short_circuits_before_the_real_computation():
    """If a failed gate ever lets the real number be computed, this raises."""
    def real_fn():
        raise AssertionError("the real number was computed behind a failed gate")

    out = eh.gated_run(lambda: {"passed": False, "pooled": {"t_clustered": 9.9}},
                       real_fn)
    assert out["gate_passed"] is False
    assert out["real"] is None
    assert out["verdict"] == "NO CONCLUSION"


def test_a_passed_gate_lets_the_real_number_be_computed():
    out = eh.gated_run(lambda: {"passed": True, "pooled": {"t_clustered": 0.4}},
                       lambda: {"diff_net_bps": 12.0, "t_clustered": 1.7})
    assert out["gate_passed"] is True
    assert out["real"]["diff_net_bps"] == 12.0


def test_the_gate_threshold_is_two_and_is_two_sided():
    """|t| >= 2.0 fails: a strongly NEGATIVE placebo is as disqualifying as a
    positive one — it was a negative placebo that killed the book stage."""
    cfg = eh.HarvestConfig()

    def constant(value):
        n = 40
        return pd.DataFrame({
            "diff_net": [value] * n, "diff_gross": [value] * n,
            "event_gross": 0.0, "control_gross": 0.0, "cost": 0.0,
            "entry_month": [f"2004-{1 + i % 9:02d}" for i in range(n)]})

    ev = pd.DataFrame({"permno": [1], "event_date": pd.to_datetime(["2010-01-01"])})
    pos = eh.placebo_gate(lambda _: constant(0.01), ev, cfg)
    neg = eh.placebo_gate(lambda _: constant(-0.01), ev, cfg)
    assert pos["passed"] is False, "a constant placebo effect must fail the gate"
    assert neg["passed"] is False, "a NEGATIVE placebo is equally disqualifying"
    assert neg["pooled"]["t_clustered"] < -2.0
    assert pos["t_bar"] == 2.0


def test_the_placebo_pools_all_five_seeds():
    calls = []

    def pipeline(ev):
        calls.append(len(ev))
        rng = np.random.default_rng(len(calls))
        x = rng.normal(0, 0.05, 60)
        return pd.DataFrame({"diff_net": x, "diff_gross": x,
                             "event_gross": 0.0, "control_gross": 0.0,
                             "cost": 0.0,
                             "entry_month": [f"2004-{1 + i % 12:02d}"
                                             for i in range(60)]})

    ev = pd.DataFrame({"permno": np.arange(30),
                       "event_date": pd.to_datetime(["2010-06-15"] * 30)})
    out = eh.placebo_gate(pipeline, ev)
    assert len(calls) == 5, "five seeds, as frozen"
    assert set(out["per_seed"]) == {0, 1, 2, 3, 4}
    assert out["pooled"]["n_events"] == 300


# ── the bar ──────────────────────────────────────────────────────────────────
def test_the_frozen_bar_needs_both_a_positive_mean_and_t_at_least_1p5():
    assert eh.clears_bar({"diff_net_bps": 20.0, "t_clustered": 1.5})
    assert not eh.clears_bar({"diff_net_bps": 20.0, "t_clustered": 1.49})
    assert not eh.clears_bar({"diff_net_bps": -20.0, "t_clustered": 3.0})


def test_the_summary_clusters_on_the_entry_month():
    """Not the filing month, and not iid: entries pile into the same month-ends
    and share that month's shock."""
    legs = pd.DataFrame({
        "diff_net": [0.03] * 30 + [0.01] * 30,
        "diff_gross": [0.03] * 30 + [0.01] * 30,
        "event_gross": 0.0, "control_gross": 0.0, "cost": 0.0,
        "entry_month": ["2004-01"] * 30 + ["2004-02"] * 30})
    s = eh.summarise_legs(legs)
    assert s["n_entry_months"] == 2
    assert s["diff_net_bps"] == pytest.approx(200.0)
    assert s["diff_net_bps_per_month"] == pytest.approx(200.0 / 3, abs=0.1)
    assert abs(s["t_clustered"]) < abs(s["t_iid"]) / 5, \
        "two shocks dressed as 60 draws must not survive clustering"
