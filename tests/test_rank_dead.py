"""INSTR-RANK-DEAD spec tests — written BEFORE the one shot.

This instrument's whole claim rests on two properties that are easy to break
silently:

  1. The two signals really are the FROZEN builders, unchanged. The guard for
     that is reproduction of the banked explore IC t (11.29 / 8.34) to within
     rounding. The guard itself is tested here; it fires for real against the
     real builders inside the run script, before any ladder number is scored.
  2. The ladder rungs really are comparable to the banked book. L2's top leg
     must be the banked book's gross leg EXACTLY — not a re-implementation that
     happens to look similar — or the leg split compares two different books
     and the whole decomposition is meaningless.

Precedent: tests/test_resid_mom.py caught an off-by-one that would have voided
a trial. A one-shot instrument gets its tests first.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory import rank_dead as rd
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.signals import FactorySignal


# ── fixtures ─────────────────────────────────────────────────────────────────
def _panel(n_months: int = 48, n_syms: int = 200, seed: int = 11) -> Panel:
    """A panel big enough to clear ScanConfig.min_names_per_month = 100 inside
    the small segment (dollar-volume rank 1001..3000), so the real scan path is
    exercised rather than short-circuited."""
    rng = np.random.default_rng(seed)
    months = pd.date_range("2004-01-31", periods=n_months, freq="ME")
    syms = [str(20000 + i) for i in range(n_syms)]
    # dollar volumes chosen so every name lands in the small segment: ranks
    # 1..200 would be largemid, so we pad the frame with 1000 huge names.
    pad = [str(90000 + i) for i in range(1000)]
    all_syms = pad + syms
    dv = pd.DataFrame(
        np.concatenate([np.full((n_months, len(pad)), 1e12),
                        np.tile(np.linspace(9e8, 1e8, n_syms), (n_months, 1))],
                       axis=1),
        index=months, columns=all_syms)
    ret = pd.DataFrame(rng.normal(0.004, 0.05, (n_months, len(all_syms))),
                       index=months, columns=all_syms)
    price = pd.DataFrame(50.0, index=months, columns=all_syms)
    return Panel(monthly_ret=ret, month_end_price=price, monthly_dollar_vol=dv,
                 delist_month={s: months[-1] for s in all_syms})


def _signal(frame: pd.DataFrame, direction: int = 1,
            name: str = "toy") -> FactorySignal:
    return FactorySignal(name, "toy", lambda p, f=frame: f, direction)


def _score_frame(panel: Panel, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(size=panel.monthly_ret.shape),
                        index=panel.monthly_ret.index,
                        columns=panel.monthly_ret.columns)


def _flat_mktcap(panel: Panel) -> pd.DataFrame:
    return pd.DataFrame(1.0, index=panel.monthly_ret.index,
                        columns=panel.monthly_ret.columns)


# ── frozen constants ─────────────────────────────────────────────────────────
def test_frozen_banked_numbers_and_thresholds():
    """The banked receipts and the four pre-declared thresholds. A change here
    is a different instrument, not a tweak."""
    assert rd.BANKED_IC_T == {"io_level": 11.29, "skew_25d": 8.34}
    assert rd.BANKED_GROSS_T == {"io_level": 0.02, "skew_25d": 1.01}
    assert (rd.R1_SPREAD_T, rd.R1_BOOK_T_MAX) == (3.0, 0.5)
    assert (rd.R2_RATIO, rd.R2_BOTTOM_T, rd.R2_TOP_T) == (2.0, 2.0, 1.0)
    assert rd.R3_RATIO == 2.0
    assert rd.R4_SPREAD_T == 1.5
    assert rd.DECILE_FRAC == 0.10


def test_instrument_never_reaches_the_confirm_window():
    """Explore only. The confirm window is not this instrument's to spend."""
    cfg = ScanConfig()
    assert cfg.first_test_month == "2004-01-31"
    assert cfg.last_test_month == "2018-12-31"


# ── THE GUARD: rebuilt signals must reproduce their banked IC t ──────────────
def test_reproduction_guard_accepts_an_exact_rebuild():
    assert rd.reproduction_ok(11.29, 11.29)
    assert rd.reproduction_ok(8.34, 8.34)
    # "within rounding": a value that rounds to the banked 2-dp figure passes
    assert rd.reproduction_ok(11.2949, 11.29)
    assert rd.reproduction_ok(8.3351, 8.34)


def test_reproduction_guard_rejects_a_changed_builder():
    """The failure this exists to catch: a builder that drifted. Even a small
    drift changes the 2-dp t and must void the run rather than be waved past."""
    assert not rd.reproduction_ok(11.24, 11.29)
    assert not rd.reproduction_ok(8.30, 8.34)
    assert not rd.reproduction_ok(0.0, 11.29)


# ── L2: the top leg IS the banked book's gross leg ───────────────────────────
def test_l2_top_leg_equals_the_banked_books_gross_leg():
    """Not 'close to' — identical, month by month. L2's whole job is to split a
    number the ledger already banked; if the top leg is a re-implementation the
    split is of some other book."""
    panel = _panel()
    sig = _signal(_score_frame(panel))
    banked = scan_signal(panel, sig, "small")["monthly"]["excess_gross"]
    l2 = rd.ladder_l2(panel, sig, "small")
    pd.testing.assert_series_equal(l2["top_minus_universe"], banked,
                                   check_names=False)


def test_l2_bottom_leg_is_the_mirror_not_a_second_top_leg():
    """universe-minus-bottom must be the negation of the flipped-direction
    book's excess_gross — the short leg's long-only mirror, on the same code
    path, so the two legs are comparable by construction."""
    panel = _panel()
    sig = _signal(_score_frame(panel), direction=+1)
    mirror = _signal(sig.compute(panel), direction=-1, name="toy__mirror")
    flipped = scan_signal(panel, mirror, "small")["monthly"]["excess_gross"]
    l2 = rd.ladder_l2(panel, sig, "small")
    pd.testing.assert_series_equal(l2["universe_minus_bottom"], -flipped,
                                   check_names=False)


def test_l2_legs_are_scored_on_the_same_months_as_the_book():
    panel = _panel()
    sig = _signal(_score_frame(panel))
    banked = scan_signal(panel, sig, "small")["monthly"]
    l2 = rd.ladder_l2(panel, sig, "small")
    assert list(l2.index) == list(banked.index)


# ── L1: value weights come from LAGGED market cap ────────────────────────────
def test_vw_weights_come_from_lagged_market_cap():
    """The weight applied to a return in month m must be built from the market
    cap at m-1. Constructed so the two answers differ by a mile: one name's cap
    explodes in the return month, and using the contemporaneous cap would drag
    the value-weighted top leg onto that name's return.
    """
    panel = _panel(n_months=24, n_syms=200)
    score = _score_frame(panel)
    sig = _signal(score)

    months = panel.monthly_ret.index
    cols = panel.monthly_ret.columns
    mc = pd.DataFrame(1.0, index=months, columns=cols)

    test_m, formation_m = months[5], months[4]
    s = (score.loc[formation_m].reindex(
        [c for c in cols if c.startswith("2")]).dropna())
    top = s.nlargest(max(int(len(s) * 0.10), 10)).index
    heavy, other = top[0], top[1]
    # heavy dominates at formation; other dominates in the return month
    mc.loc[formation_m, heavy] = 1e6
    mc.loc[test_m, other] = 1e9
    panel.monthly_ret.loc[test_m, heavy] = 1.0
    panel.monthly_ret.loc[test_m, other] = -1.0

    l1 = rd.ladder_l1(panel, sig, "small", mktcap=mc)
    got = l1.loc[test_m, "vw_top"]
    assert got > 0.9, "value weights must come from the formation month"


def test_vw_and_ew_differ_when_caps_differ_and_agree_when_flat():
    panel = _panel(n_months=24)
    sig = _signal(_score_frame(panel))
    flat = rd.ladder_l1(panel, sig, "small", mktcap=_flat_mktcap(panel))
    pd.testing.assert_series_equal(flat["ew_spread"], flat["vw_spread"],
                                   check_names=False, rtol=1e-9)

    rng = np.random.default_rng(1)
    caps = pd.DataFrame(rng.lognormal(10, 2, panel.monthly_ret.shape),
                        index=panel.monthly_ret.index,
                        columns=panel.monthly_ret.columns)
    tilted = rd.ladder_l1(panel, sig, "small", mktcap=caps)
    assert not np.allclose(tilted["ew_spread"], tilted["vw_spread"])


def test_l1_spread_is_top_decile_minus_bottom_decile():
    """A signal that perfectly predicts next month's return must produce a
    strongly positive spread; its exact negation must produce the negation."""
    panel = _panel(n_months=36)
    fwd = panel.monthly_ret.shift(-1)          # oracle: knows the answer
    sig = _signal(fwd, direction=+1)
    l1 = rd.ladder_l1(panel, sig, "small", mktcap=_flat_mktcap(panel))
    assert l1["ew_spread"].mean() > 0

    anti = _signal(-fwd, direction=+1)
    l1b = rd.ladder_l1(panel, anti, "small", mktcap=_flat_mktcap(panel))
    assert l1b["ew_spread"].mean() == pytest.approx(-l1["ew_spread"].mean(),
                                                    rel=1e-9)


def test_l1_decile_count_matches_the_books_top_decile_count():
    panel = _panel(n_months=18)
    sig = _signal(_score_frame(panel))
    l1 = rd.ladder_l1(panel, sig, "small", mktcap=_flat_mktcap(panel))
    n_uni = l1["n_universe"]
    expected = np.maximum((n_uni * rd.DECILE_FRAC).astype(int), 10)
    assert (l1["n_decile"] == expected).all()


# ── L3: the liquidity split ──────────────────────────────────────────────────
def test_l3_halves_partition_the_eligible_cross_section():
    panel = _panel(n_months=24)
    sig = _signal(_score_frame(panel))
    l3 = rd.ladder_l3(panel, sig, "small")
    l1 = rd.ladder_l1(panel, sig, "small", mktcap=_flat_mktcap(panel))
    common = l3.index.intersection(l1.index)
    assert len(common) == len(l3)
    assert ((l3.loc[common, "n_upper"] + l3.loc[common, "n_lower"])
            == l1.loc[common, "n_universe"]).all()
    # halves are within one name of each other (median split of a finite set)
    assert (l3["n_upper"] - l3["n_lower"]).abs().max() <= 1


def test_l3_isolates_information_that_lives_in_one_half():
    """A signal informative ONLY among the less liquid half must show IC in the
    lower half and nothing in the upper — the exact shape R3 is looking for."""
    panel = _panel(n_months=36)
    dv_rank = panel.monthly_dollar_vol.rank(axis=1, ascending=False)
    fwd = panel.monthly_ret.shift(-1)
    rng = np.random.default_rng(4)
    noise = pd.DataFrame(rng.normal(size=fwd.shape), index=fwd.index,
                         columns=fwd.columns)
    # ranks 1..1000 are the pad (largemid); the 200 small names occupy ranks
    # 1001..1200, so their median split sits at ~1100 and "informative below
    # 1100" means informative in the LESS liquid half only
    informative = dv_rank > 1100
    score = fwd.where(informative, noise)
    l3 = rd.ladder_l3(panel, _signal(score), "small")
    assert rd.t_stat(l3["ic_lower"]) > 3 * max(rd.t_stat(l3["ic_upper"]), 0.5)


# ── the readings ─────────────────────────────────────────────────────────────
def _ladders(ew, vw, top, bottom, upper, lower, n=180, seed=0):
    """Synthetic monthly series with prescribed t-stats (mean/sd chosen so the
    t of each column is what the caller asked for)."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2004-01-31", periods=n, freq="ME")

    def series(t):
        x = pd.Series(rng.normal(0, 1, n), index=idx)
        x = (x - x.mean()) / x.std(ddof=1)
        return x + t / np.sqrt(n)

    l1 = pd.DataFrame({"ew_spread": series(ew), "vw_spread": series(vw)})
    l2 = pd.DataFrame({"top_minus_universe": series(top),
                       "universe_minus_bottom": series(bottom)})
    l3 = pd.DataFrame({"ic_upper": series(upper), "ic_lower": series(lower)})
    return l1, l2, l3


def test_r1_fires_on_a_live_spread_with_a_dead_book():
    r = rd.score_readings(*_ladders(ew=4.0, vw=3.5, top=0.02, bottom=1.0,
                                    upper=1.0, lower=1.0))
    assert r["R1_conditions_not_code"]
    assert not r["R4_the_puzzle_stands"]


def test_r1_does_not_fire_when_the_long_only_book_is_alive():
    r = rd.score_readings(*_ladders(ew=4.0, vw=3.5, top=2.0, bottom=1.0,
                                    upper=1.0, lower=1.0))
    assert not r["R1_conditions_not_code"]


def test_r2_fires_on_a_short_side_effect():
    r = rd.score_readings(*_ladders(ew=1.0, vw=1.0, top=0.5, bottom=3.0,
                                    upper=1.0, lower=1.0))
    assert r["R2_information_is_short_side"]


def test_r3_fires_when_the_information_is_below_tradability():
    r = rd.score_readings(*_ladders(ew=1.0, vw=1.0, top=0.5, bottom=0.5,
                                    upper=1.0, lower=4.0))
    assert r["R3_below_tradability"]


def test_r4_fires_only_when_both_weightings_are_dead():
    dead = rd.score_readings(*_ladders(ew=1.0, vw=0.9, top=0.1, bottom=0.1,
                                       upper=0.1, lower=0.1))
    assert dead["R4_the_puzzle_stands"]

    half = rd.score_readings(*_ladders(ew=1.0, vw=2.5, top=0.1, bottom=0.1,
                                       upper=0.1, lower=0.1))
    assert not half["R4_the_puzzle_stands"], \
        "one live weighting is enough to keep R4 from firing"


def test_readings_are_scored_independently():
    """R1-R3 are not mutually exclusive; the frozen doc says each is scored on
    its own. All three must be able to fire at once."""
    r = rd.score_readings(*_ladders(ew=5.0, vw=4.0, top=0.1, bottom=4.0,
                                    upper=0.4, lower=4.0))
    assert r["R1_conditions_not_code"]
    assert r["R2_information_is_short_side"]
    assert r["R3_below_tradability"]
    assert not r["R4_the_puzzle_stands"]
