"""TRIAL-EVENT-13DG-HARVEST2 spec tests — written BEFORE the one shot.

The predecessor's 28 tests still pin the accounting (windows, costs, the wall,
the gate, the redraw) because HARVEST2 reuses those functions by import rather
than reimplementing them; a test here asserts that reuse is real. What is NEW
is the control-matching rule, and it has exactly four ways to run green while
answering the wrong question:

  * MEASURING THE CHARACTERISTICS TOO LATE. If the match reads the cap or the
    prior return of the month the filing lands in, it absorbs the announcement
    into the matching variable and matches away the effect. The characteristic
    month must be the last month-end STRICTLY BEFORE the filing.
  * STANDARDISING POOLED RATHER THAN PER MONTH. A pooled z-score lets the
    market's own size and momentum drift decide which dimension dominates the
    distance, so the metric silently changes meaning across the sample.
  * A NON-DETERMINISTIC TIE-BREAK. Two candidates at identical distance must
    resolve the same way on every run, or the placebo and the real arm are not
    running the same pipeline.
  * A POOL THAT IS NOT THE FROZEN POOL — wrong segment, wrong month, ineligible
    names, the event as its own control, or a control carrying its own event
    inside +/-60 calendar days.

And the gate: if the real number can be computed behind a failed gate, the gate
is decoration. Pinned with a `real_fn` that raises.
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


def _daily_panel(n_syms: int = 40, seed: int = 3) -> de.DailyEventPanel:
    """Daily panel spanning the monthly fixture, all names in one segment."""
    rng = np.random.default_rng(seed)
    cal = pd.DatetimeIndex(pd.bdate_range("2004-01-01", "2007-12-31"))
    rows = []
    for i in range(n_syms):
        rows.append(pd.DataFrame({
            "permno": 10000 + i, "date": cal,
            "ret": rng.normal(0, 0.02, len(cal)),
            "dollar_vol": 1e9 - i * 1e6}))
    return de.DailyEventPanel.build(pd.concat(rows, ignore_index=True), cal)


def _eligible(panel: Panel) -> pd.DataFrame:
    return eb.eligible_universe(panel, eb.BookConfig(max_rank=3000))


def _chars(panel: Panel, eligible: pd.DataFrame,
           cap: pd.DataFrame | None = None) -> eh.CohortChars:
    """Characteristics from an explicit market-cap frame (no CRSP shrout read)."""
    if cap is None:
        cap = pd.DataFrame(
            np.tile(np.linspace(1e10, 1e8, panel.monthly_ret.shape[1]),
                    (panel.monthly_ret.shape[0], 1)),
            index=panel.monthly_ret.index, columns=panel.monthly_ret.columns)
    return eh.cohort_characteristics(panel, eligible, mktcap=cap)


def _events(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["permno", "event_date"])
    df["event_date"] = pd.to_datetime(df["event_date"])
    return df


def _match(events, panel=None, daily=None, eligible=None, chars=None, cap=None):
    panel = panel or _panel()
    daily = daily or _daily_panel()
    eligible = _eligible(panel) if eligible is None else eligible
    chars = _chars(panel, eligible, cap) if chars is None else chars
    return eh.match_cohort_controls(events, daily, chars, eligible)


# ── the successor changes the RULE and nothing else ──────────────────────────
def test_the_accounting_functions_are_the_predecessors_by_import_not_by_copy():
    """HARVEST2 inherits the window, the legs, the gate, the redraw and the bar
    as the SAME objects. If any were reimplemented, this file would be pinning
    a different pipeline than the 28 tests that already validated them."""
    for name in ("compute_legs", "summarise_legs", "placebo_gate", "gated_run",
                 "redraw_filing_dates", "clears_bar", "HarvestConfig"):
        assert hasattr(eh, name)
    cfg = eh.HarvestConfig()
    assert (cfg.hold_months, cfg.max_rank, cfg.exclusion_days) == (3, 3000, 60)
    assert cfg.placebo_seeds == (0, 1, 2, 3, 4) and cfg.placebo_t_bar == 2.0
    assert cfg.bar_t == 1.5 and cfg.explore_end == "2018-12-31"
    assert eh.CHAR_LOOKBACK_MONTHS == 6


def test_the_successor_output_is_a_drop_in_for_compute_legs():
    panel, daily = _panel(), _daily_panel()
    elig = _eligible(panel)
    ev = _events([(10005, "2005-03-14"), (10012, "2005-07-08")])
    m = _match(ev, panel, daily, elig)
    legs, diag = eh.compute_legs(m, panel, elig, None)
    assert diag["measured"] == 2 and len(legs) == 2


# ── the characteristics are PRE-filing ───────────────────────────────────────
def test_the_characteristic_month_is_strictly_before_the_filing():
    months = _panel().monthly_ret.index
    rng = np.random.default_rng(5)
    for _ in range(300):
        d = pd.Timestamp("2004-01-01") + pd.Timedelta(int(rng.integers(0, 1400)), "D")
        ic = eh.characteristic_index(d, months)
        if ic is None:
            continue
        assert months[ic] < d, "the match may never read the filing month"
        assert eh.characteristic_index(d, months) == \
            eb.entry_index(d, months) - 1


def test_a_month_end_filing_is_matched_on_the_PREVIOUS_month_end():
    months = _panel().monthly_ret.index
    d = months[10]                                   # a filing ON a month-end
    assert eb.entry_index(d, months) == 10, "entry is that same month-end"
    assert eh.characteristic_index(d, months) == 9, \
        "a filing on the month-end may not see that month-end's own cap/return"


def test_a_filing_in_the_panels_first_month_has_no_characteristic_month():
    panel = _panel()
    months = panel.monthly_ret.index
    assert eh.characteristic_index(months[0] - pd.Timedelta(3, "D"),
                                   months) is None
    m = _match(_events([(10005, months[0] - pd.Timedelta(3, "D"))]), panel)
    assert m["control_permno"].isna().all(), "no characteristics -> no control"


def test_the_match_cannot_see_the_filing_months_own_return():
    """The decisive lookahead test: blowing up the return of the month a filing
    lands in must not change which control it is matched to."""
    panel = _panel()
    elig = _eligible(panel)
    ev = _events([(10005, "2005-06-14"), (10021, "2005-06-20")])
    before = _match(ev, panel, eligible=elig)["control_permno"].to_numpy()

    tainted = _panel()
    tainted.monthly_ret.loc["2005-06-30"] *= 10.0    # the filing month itself
    after = _match(ev, tainted, eligible=_eligible(tainted)
                   )["control_permno"].to_numpy()
    np.testing.assert_array_equal(before, after)


def test_the_match_DOES_see_the_month_before_the_filing():
    """The mirror of the lookahead test — if perturbing the last PRE-filing
    month changed nothing either, the return dimension would be inert."""
    panel = _panel()
    ev = _events([(10005, "2005-06-14")])
    before = _match(ev, panel)["control_permno"].to_numpy()
    moved = _panel()
    moved.monthly_ret.loc["2005-05-31", "10005"] = 3.0
    after = _match(ev, moved)["control_permno"].to_numpy()
    assert not np.array_equal(before, after)


def test_the_prior_return_compounds_over_exactly_six_months():
    panel = _panel(n_months=12, n_syms=3)
    panel.monthly_ret.iloc[:, :] = 0.0
    panel.monthly_ret.iloc[3:9, 0] = 0.10           # months 3..8 inclusive
    pr = eh.prior_return_frame(panel)
    assert pr.iloc[8, 0] == pytest.approx(1.10 ** 6 - 1.0)
    assert pr.iloc[9, 0] == pytest.approx(1.10 ** 5 - 1.0), \
        "the window ends AT the month, so month 9's zero drops the earliest 0.10"
    assert np.isnan(pr.iloc[4, 1]), "five observations is not six"
    assert not np.isnan(pr.iloc[5, 1]), "the sixth month is the first value"


def test_the_prior_return_needs_all_six_months_present():
    panel = _panel(n_months=12, n_syms=3)
    panel.monthly_ret.iloc[:, :] = 0.01
    panel.monthly_ret.iloc[4, 0] = np.nan
    pr = eh.prior_return_frame(panel)
    assert np.isnan(pr.iloc[9, 0]), "a hole inside the window kills it"
    assert not np.isnan(pr.iloc[9, 1])
    assert np.isnan(pr.iloc[4, 2]), "fewer than six observations -> no value"


# ── standardisation is PER MONTH ─────────────────────────────────────────────
def test_standardisation_is_per_month_not_pooled():
    """Identical raw values in two months with different cross-sections must
    produce different z-scores — that is what "per-month" means."""
    panel = _panel(n_months=12, n_syms=6)
    elig = _eligible(panel)
    raw = pd.DataFrame(1.0, index=panel.monthly_ret.index,
                       columns=panel.monthly_ret.columns)
    raw.iloc[0] = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    raw.iloc[1] = [1.0, 2.0, 3.0, 40.0, 50.0, 60.0]
    z = eh._per_month_z(raw, elig)
    assert z.iloc[0].mean() == pytest.approx(0.0, abs=1e-12)
    assert z.iloc[0].std(ddof=0) == pytest.approx(1.0)
    assert z.iloc[1].std(ddof=0) == pytest.approx(1.0)
    assert z.iloc[0, 0] != pytest.approx(z.iloc[1, 0]), \
        "the same raw value must score differently against a different month"


def test_standardisation_moments_come_from_the_eligible_universe_only():
    panel = _panel(n_months=6, n_syms=6)
    elig = _eligible(panel)
    elig.iloc[:, 3:] = False                        # three ineligible names
    raw = pd.DataFrame(np.tile([1.0, 2.0, 3.0, 100.0, 200.0, 300.0], (6, 1)),
                       index=panel.monthly_ret.index,
                       columns=panel.monthly_ret.columns)
    z = eh._per_month_z(raw, elig)
    assert z.iloc[0, 1] == pytest.approx(0.0), \
        "2.0 is the mean of the ELIGIBLE cross-section {1,2,3}"
    assert z.iloc[0, 3] > 50, "an ineligible outlier is scored, not consulted"


def test_the_two_dimensions_are_both_live_in_the_distance():
    """A candidate nearer in cap but far in prior return must lose to the
    jointly nearest one — otherwise the metric is one-dimensional."""
    panel = _panel(n_months=24, n_syms=5)
    panel.monthly_ret.iloc[:, :] = 0.0
    panel.monthly_ret.iloc[:, 1] = 0.20             # 10001 is a big winner
    panel.monthly_ret.iloc[:, 2] = 0.0              # 10002 flat, like the event
    elig = _eligible(panel)
    cap = pd.DataFrame(np.tile([1e10, 1.01e10, 3e10, 9e10, 9.5e10], (24, 1)),
                       index=panel.monthly_ret.index,
                       columns=panel.monthly_ret.columns)
    m = _match(_events([(10000, "2005-06-14")]), panel, eligible=elig,
               chars=_chars(panel, elig, cap))
    assert int(m["control_permno"].iloc[0]) == 10002, \
        "nearest in cap alone would have picked 10001"


# ── the pool ─────────────────────────────────────────────────────────────────
def test_the_control_is_never_the_event_itself():
    m = _match(_events([(10005, "2005-03-14"), (10030, "2006-02-09")]))
    ok = m.dropna(subset=["control_permno"])
    assert len(ok) == 2
    assert (ok["control_permno"].to_numpy() != ok["permno"].to_numpy()).all()


def test_the_control_shares_the_events_segment_and_calendar_month():
    panel, daily = _panel(), _daily_panel()
    m = _match(_events([(10005, "2005-03-14"), (10032, "2005-09-08")]),
               panel, daily).dropna(subset=["control_permno"])
    assert len(m) == 2
    for _, r in m.iterrows():
        pool = daily.ranks[(daily.ranks["ym"] == r["ym"])
                           & (daily.ranks["segment"] == r["segment"])]
        assert int(r["control_permno"]) in set(pool["permno"])


def test_a_candidate_ineligible_at_the_ENTRY_month_end_is_not_a_control():
    panel = _panel()
    elig = _eligible(panel)
    ev = _events([(10005, "2005-06-14")])
    picked = int(_match(ev, panel, eligible=elig)["control_permno"].iloc[0])
    entry = eb.entry_index(pd.Timestamp("2005-06-14"), panel.monthly_ret.index)
    elig2 = elig.copy()
    elig2.iloc[entry, elig2.columns.get_loc(str(picked))] = False
    again = _match(ev, panel, eligible=elig2, chars=_chars(panel, elig2))
    assert int(again["control_permno"].iloc[0]) != picked


def test_a_contaminated_candidate_is_rejected_within_60_calendar_days():
    """The +/-60cd rule, inherited: a candidate with its own event inside the
    window is not a non-event name."""
    panel = _panel()
    ev = _events([(10005, "2005-06-14")])
    solo = int(_match(ev, panel)["control_permno"].iloc[0])
    both = _match(_events([(10005, "2005-06-14"), (solo, "2005-07-20")]), panel)
    assert int(both["control_permno"].iloc[0]) != solo
    far = _match(_events([(10005, "2005-06-14"), (solo, "2005-11-20")]), panel)
    assert int(far["control_permno"].iloc[0]) == solo, \
        "outside +/-60cd the same name is admissible again"


def test_one_control_per_event_and_matching_is_WITH_replacement():
    panel = _panel()
    ev = _events([(10005, "2005-06-14"), (10006, "2005-06-15")])
    m = _match(ev, panel)
    assert len(m) == 2 and m["control_permno"].notna().all()
    # the two events are within 60cd of each other, so neither can control the
    # other; a shared third name is allowed and must not be consumed by the first
    ev2 = _events([(10005, "2005-06-14"), (10005, "2005-06-15")])
    m2 = _match(ev2, panel)
    assert m2["control_permno"].nunique() == 1, "with replacement"


def test_the_tie_break_is_the_smallest_permno_and_is_deterministic():
    """Two candidates at exactly equal distance, one above and one below the
    event in cap with identical prior returns. The rule is the smaller permno,
    on every run — a matcher that resolved this by frame order would put the
    placebo and the real arm on subtly different pipelines."""
    panel = _panel(n_months=24, n_syms=5)
    panel.monthly_ret.iloc[:, :] = 0.0
    panel.monthly_ret.iloc[:, 0] = 0.02             # variance so the z is defined
    elig = _eligible(panel)
    cap = pd.DataFrame(np.tile([1e9, 2e9, 4e9, 8e9, 16e9], (24, 1)),
                       index=panel.monthly_ret.index,
                       columns=panel.monthly_ret.columns)   # equal log spacing
    chars = _chars(panel, elig, cap)
    ev = _events([(10002, "2005-06-14")])
    picks = {int(_match(ev, panel, eligible=elig, chars=chars)
                 ["control_permno"].iloc[0]) for _ in range(5)}
    assert picks == {10001}, \
        "10001 and 10003 tie exactly -> the smaller permno, always"


def test_an_event_with_no_admissible_candidate_is_counted_not_crashed():
    panel = _panel()
    ev = _events([(10005, "2005-06-14")])
    elig = _eligible(panel)
    elig.iloc[:, :] = False
    m = _match(ev, panel, eligible=elig, chars=_chars(panel, elig))
    assert len(m) == 1 and m["control_permno"].isna().all()
    legs, diag = eh.compute_legs(m, panel, _eligible(panel), None)
    assert diag["no_control"] == 1 and diag["measured"] == 0


def test_an_event_outside_the_daily_panels_ranks_keeps_a_row_with_no_control():
    """Unlike the parent matcher, a segment-less event does not vanish — the
    attrition has to add up to the arm."""
    panel = _panel()
    m = _match(_events([(10005, "2005-03-14"), (999999, "2005-03-14")]), panel)
    assert len(m) == 2
    assert m["control_permno"].isna().sum() == 1


# ── the pipeline end to end, with the gate in front ──────────────────────────
def _pipeline(panel, daily, elig, chars, spread=None):
    def run(ev: pd.DataFrame) -> pd.DataFrame:
        m = eh.match_cohort_controls(ev, daily, chars, elig)
        return eh.compute_legs(m, panel, elig, spread)[0]
    return run


def test_the_gate_runs_the_identical_pipeline_on_five_redraws():
    panel, daily = _panel(), _daily_panel()
    elig = _eligible(panel)
    chars = _chars(panel, elig)
    ev = _events([(10000 + i, "2005-06-14") for i in range(20)])
    cfg = eh.HarvestConfig(explore_start="2004-02-01", explore_end="2007-06-30")
    out = eh.placebo_gate(_pipeline(panel, daily, elig, chars), ev, cfg)
    assert set(out["per_seed"]) == {0, 1, 2, 3, 4}
    assert out["pooled"]["n_events"] > 0
    assert isinstance(out["passed"], bool)


def test_the_real_number_is_not_computed_behind_a_failed_gate():
    def real_fn():
        raise AssertionError("the real arm ran behind a failed gate")

    out = eh.gated_run(lambda: {"passed": False,
                                "pooled": {"t_clustered": -3.17}}, real_fn)
    assert out["gate_passed"] is False and out["real"] is None
    assert out["verdict"] == "NO CONCLUSION"


def test_entry_still_never_precedes_the_filing_under_the_new_matcher():
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _events([(10005, "2005-06-14"), (10006, "2005-06-30")])
    m = _match(ev, panel)
    legs, _ = eh.compute_legs(m, panel, _eligible(panel), None)
    for _, r in legs.iterrows():
        assert r["entry_month"].to_timestamp("M") >= \
            pd.Timestamp(r["event_date"]).to_period("M").to_timestamp("M") \
            or r["entry_month"].to_timestamp("M") >= r["event_date"]


def test_costs_still_hit_the_event_leg_only_under_the_new_matcher():
    panel = _panel()
    elig = _eligible(panel)
    m = _match(_events([(10005, "2005-06-14")]), panel, eligible=elig)
    free, _ = eh.compute_legs(m, panel, elig, None,
                              eh.HarvestConfig(flat_cost_bps_one_way=0.0))
    paid, _ = eh.compute_legs(m, panel, elig, None,
                              eh.HarvestConfig(flat_cost_bps_one_way=25.0))
    assert free["control_gross"].iloc[0] == pytest.approx(
        paid["control_gross"].iloc[0]), "the control is a paper benchmark"
    assert paid["diff_net"].iloc[0] == pytest.approx(
        free["diff_net"].iloc[0] - 0.005)
