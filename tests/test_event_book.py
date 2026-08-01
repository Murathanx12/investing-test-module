"""13DG BOOK STAGE spec tests — written BEFORE the one shot.

The book has no model in it, so what has to be right is the calendar and the
accounting. Five things would each silently answer a different question than the
one frozen, and four of them would answer it in our FAVOUR:

  * an entry that precedes the filing date (lookahead — the failure mode this
    whole programme exists to refuse),
  * a name filed mid-month entering at the PRIOR month-end (the same lookahead
    wearing a calendar disguise, and it would hand the book the announcement
    pop the freeze explicitly forfeits),
  * a hold that runs long (more of the drift than the frozen 3 months),
  * a re-filing that doubles a position instead of resetting the clock
    (concentration the freeze forbids),
  * a cost charge that is flat rather than per-name and size-aware (13D names
    are small; a flat charge understates what they cost to trade).

The fifth check has no direction: the eligible universe must be the factory's,
or the book is not comparable to anything else in the ledger.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory import event_book as eb
from aegis_brain.factory.explore import segment_mask


# ── fixtures ─────────────────────────────────────────────────────────────────
def _panel(n_months: int = 36, n_syms: int = 40, seed: int = 4) -> Panel:
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


def _events(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["permno", "event_date"])
    df["event_date"] = pd.to_datetime(df["event_date"])
    return df


# ── frozen constants ─────────────────────────────────────────────────────────
def test_frozen_book_constants():
    cfg = eb.BookConfig()
    assert cfg.hold_months == 3
    assert cfg.max_rank == 3000
    assert cfg.cost_bps_one_way == 25.0
    assert cfg.first_test_month == "2004-01-31"
    assert cfg.last_test_month == "2018-12-31", "the book never reads confirm"


# ── entry timing: the lookahead guards ───────────────────────────────────────
def test_entry_never_precedes_the_filing_date():
    panel = _panel()
    months = panel.monthly_ret.index
    rng = np.random.default_rng(1)
    for _ in range(200):
        d = months[0] + pd.Timedelta(days=int(rng.integers(0, 1000)))
        i = eb.entry_index(d, months)
        if i is not None:
            assert months[i] >= d, "entry month-end precedes the filing"


def test_a_mid_month_filing_enters_at_that_months_end():
    panel = _panel()
    months = panel.monthly_ret.index
    i = eb.entry_index(pd.Timestamp("2004-03-15"), months)
    assert months[i] == pd.Timestamp("2004-03-31")


def test_a_month_end_filing_enters_that_same_day():
    """'on or after' — a filing dated exactly on the month-end is tradable at
    that month-end close, not deferred a month."""
    panel = _panel()
    months = panel.monthly_ret.index
    i = eb.entry_index(pd.Timestamp("2004-03-31"), months)
    assert months[i] == pd.Timestamp("2004-03-31")


def test_a_first_of_month_filing_waits_for_the_month_end():
    """The costly half of the rule: a filing on the 1st is NOT held for the
    month in which its drift is strongest. This is the forfeit the freeze
    declares, and it must actually be paid."""
    panel = _panel()
    months = panel.monthly_ret.index
    i = eb.entry_index(pd.Timestamp("2004-04-01"), months)
    assert months[i] == pd.Timestamp("2004-04-30")


def test_the_book_earns_no_return_from_its_entry_month():
    """Formation-month convention: a name entering at month-end M first earns
    month M+1's return. If it earned M's, the book would be trading on a price
    it could not have traded at."""
    panel = _panel()
    months = panel.monthly_ret.index
    panel.monthly_ret.loc[:, :] = 0.0
    panel.monthly_ret.loc[months[5], "10000"] = 1.0     # the entry month itself
    ev = _events([(10000, months[5])])
    r = eb.run_book(panel, ev, cost_frame=None)
    scored = r["monthly"]
    assert months[5] not in scored.index, \
        "the entry month-end is a formation date, never a scored return month"
    assert scored["gross"].abs().sum() == pytest.approx(0.0), \
        "the entry month's own +100% must not reach the book"


# ── the hold ─────────────────────────────────────────────────────────────────
def test_hold_exits_at_the_third_month_end():
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _events([(10000, months[5])])
    held, _ = eb.membership_frame(ev, panel)
    active = held["10000"]
    assert active.loc[months[5]] and active.loc[months[6]] and active.loc[months[7]]
    assert not active.loc[months[8]], "the position must be gone at M+3"
    assert int(active.sum()) == 3


def test_hold_earns_exactly_three_monthly_returns():
    panel = _panel()
    months = panel.monthly_ret.index
    panel.monthly_ret.loc[:, :] = 0.0
    panel.monthly_ret.loc[:, "10000"] = 0.10
    ev = _events([(10000, months[5])])
    r = eb.run_book(panel, ev, cost_frame=None)
    earned = r["monthly"]["gross"]
    assert int((earned > 0).sum()) == 3
    assert list(earned[earned > 0].index) == [months[6], months[7], months[8]]


# ── re-filing resets, never doubles ──────────────────────────────────────────
def test_a_refiling_resets_the_clock_rather_than_doubling():
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _events([(10000, months[5]), (10000, months[6])])
    held, diag = eb.membership_frame(ev, panel)
    active = held["10000"]
    assert diag["entered"] == 2
    # the second filing extends the hold to M6..M8, so membership is M5..M8
    assert int(active.sum()) == 4
    assert active.loc[months[8]] and not active.loc[months[9]]


def test_a_refiling_does_not_double_the_weight():
    """Two live filings on one name must still be ONE equal-weighted position."""
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _events([(10000, months[5]), (10000, months[6]),
                  (10001, months[5]), (10002, months[5])])
    r = eb.run_book(panel, ev, cost_frame=None)
    n = r["monthly"].loc[months[7], "n_held"]
    assert n == 3, "the re-filed name must be counted once, not twice"


def test_a_second_filing_after_the_hold_reopens_the_position():
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _events([(10000, months[5]), (10000, months[20])])
    held, _ = eb.membership_frame(ev, panel)
    active = held["10000"]
    assert int(active.sum()) == 6
    assert not active.loc[months[8]] and active.loc[months[20]]


# ── costs: per-name and size-aware ───────────────────────────────────────────
def test_cost_charge_is_per_name_not_a_flat_rate():
    """Two names, wildly different spreads. A flat charge cannot distinguish
    them; the frozen deciding arm must."""
    panel = _panel(n_syms=4)
    months = panel.monthly_ret.index
    panel.monthly_ret.loc[:, :] = 0.0
    cheap = pd.DataFrame(1.0, index=months, columns=panel.monthly_ret.columns)
    dear = cheap.copy()
    dear.loc[:, "10000"] = 400.0

    ev = _events([(10000, months[5]), (10001, months[5])])
    a = eb.run_book(panel, ev, cost_frame=cheap)["monthly"]["cost_bps"]
    b = eb.run_book(panel, ev, cost_frame=dear)["monthly"]["cost_bps"]
    assert b.sum() > a.sum() * 10, "a per-name spread must reach the charge"


def test_cost_is_charged_on_actual_turnover_only():
    """A name held across a month with no weight change is not re-charged; the
    charge lands on the entry and the exit."""
    panel = _panel(n_syms=4)
    months = panel.monthly_ret.index
    panel.monthly_ret.loc[:, :] = 0.0
    frame = pd.DataFrame(100.0, index=months, columns=panel.monthly_ret.columns)
    ev = _events([(p, months[5]) for p in (10000, 10001, 10002, 10003)])
    m = eb.run_book(panel, ev, cost_frame=frame)["monthly"]
    # entry month charged, the two hold months not, the exit month charged
    assert m.loc[months[6], "cost_bps"] > 0
    assert m.loc[months[7], "cost_bps"] == pytest.approx(0.0)
    assert m.loc[months[8], "cost_bps"] == pytest.approx(0.0)


def test_zero_cost_frame_is_the_zero_cost_bound():
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _events([(10000 + i, months[5]) for i in range(5)])
    zero = pd.DataFrame(0.0, index=months, columns=panel.monthly_ret.columns)
    r = eb.run_book(panel, ev, cost_frame=zero)
    assert r["summary"]["mean_cost_bps"] == pytest.approx(0.0)
    pd.testing.assert_series_equal(r["monthly"]["net"], r["monthly"]["gross"],
                                   check_names=False)


def test_flat_guard_matches_the_factory_flat_convention():
    """cost_frame=None must reproduce `traded * 25 / 1e4`, the flat-cost
    arithmetic `factory/explore.py` uses."""
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _events([(10000 + i, months[5]) for i in range(5)])
    m = eb.run_book(panel, ev, cost_frame=None)["monthly"]
    expected = m["traded"] * 25.0 / 1e4
    np.testing.assert_allclose(m["gross"] - m["net"], expected, atol=1e-12)


# ── the universe ─────────────────────────────────────────────────────────────
def test_eligible_universe_matches_the_factory():
    """Identical to the factory's largemid + small, or the book's excess is
    measured against a benchmark nothing else in the ledger uses."""
    panel = _panel(n_syms=40)
    mine = eb.eligible_universe(panel)
    factory = panel.eligible() & (segment_mask(panel, "largemid")
                                  | segment_mask(panel, "small"))
    pd.testing.assert_frame_equal(mine, factory)


def test_a_name_ineligible_at_entry_creates_no_position():
    panel = _panel(n_syms=4)
    months = panel.monthly_ret.index
    panel.month_end_price.loc[months[5], "10000"] = 0.10    # below the $1 floor
    ev = _events([(10000, months[5]), (10001, months[5])])
    held, diag = eb.membership_frame(ev, panel)
    assert diag["ineligible_at_entry"] == 1 and diag["entered"] == 1
    assert not held.loc[months[5], "10000"]
    assert held.loc[months[5], "10001"]


def test_an_event_outside_the_panel_is_counted_not_crashed():
    panel = _panel(n_syms=4)
    months = panel.monthly_ret.index
    ev = _events([(999999, months[5]), (10001, months[5])])
    _, diag = eb.membership_frame(ev, panel)
    assert diag["not_in_panel"] == 1 and diag["entered"] == 1


def test_benchmark_is_the_equal_weighted_eligible_universe():
    panel = _panel(n_syms=6)
    months = panel.monthly_ret.index
    ev = _events([(10000, months[5])])
    m = eb.run_book(panel, ev, cost_frame=None)["monthly"]
    expected = panel.monthly_ret.loc[months[6]].mean()
    assert m.loc[months[6], "benchmark_ew"] == pytest.approx(expected)
    assert m.loc[months[6], "n_universe"] == 6


# ── the deciding number ──────────────────────────────────────────────────────
def test_excess_net_is_net_minus_benchmark():
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _events([(10000 + i, months[5]) for i in range(5)])
    m = eb.run_book(panel, ev, cost_frame=None)["monthly"]
    np.testing.assert_allclose(m["excess_net"], m["net"] - m["benchmark_ew"],
                               atol=1e-12)


def test_a_book_that_only_holds_the_universe_has_zero_excess():
    """Sanity floor: holding every eligible name equal-weighted must produce
    exactly the benchmark, so the excess is zero before costs."""
    panel = _panel(n_syms=8)
    months = panel.monthly_ret.index
    ev = _events([(10000 + i, months[5]) for i in range(8)])
    m = eb.run_book(panel, ev, cost_frame=None)["monthly"]
    assert m.loc[months[6], "excess_gross"] == pytest.approx(0.0, abs=1e-12)


def test_months_with_no_active_name_are_skipped_and_counted():
    panel = _panel()
    months = panel.monthly_ret.index
    ev = _events([(10000, months[5])])
    r = eb.run_book(panel, ev, cost_frame=None)
    assert r["summary"]["months_empty"] > 0
    assert len(r["monthly"]) == 3
