"""INTERNET-INVESTIGATOR-FWD-1 — the read gate's boundaries, pinned.

WHY THESE TESTS AND NOT OTHERS
==============================
The gate's whole job is REFUSAL, and a refusal is the easiest thing in a
codebase to break without noticing: loosen an inequality by one and nothing
fails, no output changes, and the trial silently gains an unbounded number of
looks. There is no downstream number that goes wrong. So the boundaries are the
test.

Nine of these are the referee's enumerated boundary cases (39/40/41, 79/80/81,
119/120/121). The rest exist because a gate that refuses at the right n but
emits the wrong verdict AT a licensed n has only moved the failure.

Offline and deterministic. The one file read is the committed boundaries
receipt, and the point of reading it is that the config's constants are NOT
allowed to be a retyped memory of it.
"""

from __future__ import annotations

import pytest

from scripts import iif1_config as C
from scripts import iif1_read_gate as RG


# ── the nine boundaries ─────────────────────────────────────────────────────
# 41 is the case that matters most. Before this gate existed the only check was
# `n < 40`, so 41 passed -- and a trial that may read at 41 may read at 42, 43
# and every night after, which is not a schedule at all.

@pytest.mark.parametrize("n,expected", [
    (39,  RG.REFUSE),
    (40,  RG.READ),
    (41,  RG.REFUSE),
    (79,  RG.REFUSE),
    (80,  RG.READ),
    (81,  RG.REFUSE),
    (119, RG.REFUSE),
    (120, RG.READ),
    (121, RG.NEW_PREREG_REQUIRED),
])
def test_the_nine_boundaries(n, expected):
    assert RG.check_read(n).disposition == expected


@pytest.mark.parametrize("n", [39, 41, 79, 81, 119, 121])
def test_an_unlicensed_look_raises_rather_than_returning_a_weaker_answer(n):
    """`require_read` is what every verdict path calls. It must RAISE.

    A gate that returned "unlicensed" as a value would depend on every caller
    remembering to check it -- which is the shape of every silent-fragility bug
    this repo has already paid for.
    """
    with pytest.raises(RG.ReadRefused):
        RG.require_read(n)


@pytest.mark.parametrize("n", [40, 80, 120])
def test_a_licensed_look_does_not_raise_and_carries_its_own_bar(n):
    d = RG.require_read(n)
    assert d.licensed
    assert d.mde_z is not None and d.mde_z > 0


def test_121_is_refused_as_a_new_prereg_not_as_a_near_miss():
    """Past the final look the refusal has a DIFFERENT remedy.

    39 means "wait". 121 means "this pre-registration is over; accruing further
    and reading again is optional stopping relocated to the end." Collapsing
    the two would let a null at 120 quietly become "keep going until it isn't".
    """
    d = RG.check_read(121)
    assert d.disposition == RG.NEW_PREREG_REQUIRED
    assert "new prospective pre-registration" in d.reason
    assert RG.check_read(39).disposition == RG.REFUSE


def test_far_past_the_end_is_still_new_prereg_not_licensed():
    for n in (200, 400, 10_000):
        assert RG.check_read(n).disposition == RG.NEW_PREREG_REQUIRED


def test_zero_and_negative_nights_are_refused():
    """n=0 is the state on the night the runner is first switched on."""
    for n in (0, -1):
        with pytest.raises(RG.ReadRefused):
            RG.require_read(n)


# ── the bars widen early and are near-nominal at the end ────────────────────

def test_the_bar_is_strictly_hardest_at_the_earliest_look():
    """O'Brien-Fleming shape. If this ever inverts, the early peek has become
    the CHEAPEST place to stop, which is precisely backwards."""
    z = [d.mde_z for d in map(RG.check_read, RG.licensed_looks())]
    assert z[0] > z[1] > z[2]


def test_the_final_look_pays_almost_nothing_for_the_two_peeks():
    assert abs(RG.check_read(120).mde_z - C.MDE_Z) < 0.10


def test_the_config_constants_are_not_a_retyped_memory_of_the_receipt():
    """`READ_SCHEDULE` restates numbers `iif1_boundaries.py` simulated. A bar
    retyped 5% loose is a false-positive rate nobody notices."""
    chk = RG.verify_schedule_matches_receipt()
    assert chk["looks"] == list(RG.licensed_looks())
    assert abs(chk["familywise_alpha"] - 0.05) < 0.005


# ── the terminal rule ───────────────────────────────────────────────────────

def test_an_underpowered_interim_produces_neither_a_positive_nor_a_negative():
    """The referee's extra condition: a licensed look that does not meet its
    MDE can produce NO substantive verdict in either direction.

    Both signs are checked, because the failure mode is asymmetric in practice
    -- an underpowered null reads as a kill to everyone who wasn't there.
    """
    # All strictly inside the SMALLER of the two interim bars (look 2, 3.295),
    # so each value is genuinely underpowered at both looks it is checked at.
    for t in (+2.0, -2.0, +0.1, -3.2, +3.2):
        for n in (40, 80):
            out = RG.classify(n, t)
            assert out["verdict"] == RG.INTERIM_UNDERPOWERED
            assert out["substantive"] is False
            assert out["terminal"] is False
            assert out["verdict"] not in (RG.H1_SUPPORTED,
                                          RG.H1_DIRECTION_REJECTED,
                                          RG.NOT_DETECTABLE)


def test_an_interim_that_clears_its_own_widened_bar_is_substantive():
    out = RG.classify(40, 4.5)          # look-1 bar is 4.312
    assert out["verdict"] == RG.H1_SUPPORTED
    assert out["terminal"] and out["substantive"]


def test_a_value_that_would_clear_the_house_bar_does_not_clear_look_one():
    """t = 3.0 clears the flat 2.80 and is nowhere near the look-1 bar. This is
    the multiplicity correction doing the only job it has."""
    assert 3.0 > C.MDE_Z
    assert RG.classify(40, 3.0)["verdict"] == RG.INTERIM_UNDERPOWERED
    assert RG.classify(120, 3.0)["verdict"] == RG.H1_SUPPORTED


def test_a_detectable_effect_in_the_wrong_direction_rejects_rather_than_wins():
    out = RG.classify(120, -3.5)
    assert out["verdict"] == RG.H1_DIRECTION_REJECTED
    assert out["substantive"] is True


def test_the_final_look_below_its_bar_terminates_the_prereg():
    out = RG.classify(120, 1.0)
    assert out["verdict"] == RG.NOT_DETECTABLE
    assert out["terminal"] is True
    assert "TERMINATES" in out["line"]
    assert "new prospective pre-registration" in out["line"]


def test_a_missing_statistic_is_never_a_substantive_verdict():
    for n in (40, 80, 120):
        out = RG.classify(n, None)
        assert out["substantive"] is False
        assert out["verdict"] == RG.INTERIM_UNDERPOWERED


def test_classify_refuses_at_an_unlicensed_n_before_looking_at_the_statistic():
    """The statistic must not be able to buy a look. Even an enormous t."""
    with pytest.raises(RG.ReadRefused):
        RG.classify(41, 99.0)


# ── the bound claim language ────────────────────────────────────────────────

def test_the_permitted_claim_is_about_calibration_not_picking():
    assert "calibration" in RG.CLAIM_LANGUAGE
    RG.assert_claim_language_permitted(RG.CLAIM_LANGUAGE)


@pytest.mark.parametrize("line", [
    "H1 supported: the investigator picks stocks better than the snapshot",
    "investigation produces alpha over the engineered snapshot",
    "the tools arm delivers a higher Sharpe",
    "this is tradable",
    "demonstrates forecasting skill",
])
def test_a_verdict_line_claiming_more_than_the_trial_can_support_is_refused(line):
    with pytest.raises(RG.ReadRefused):
        RG.assert_claim_language_permitted(line)


def test_the_gate_does_not_round_its_way_to_a_licensed_look():
    """`int(40.9)` is 40. A truncating coercion would hand a licensed look to a
    value that is not one, which is the same class of bug as a floor pretending
    to be a schedule."""
    for bad in (40.9, 39.5, 120.5, True):
        with pytest.raises(RG.ReadRefused):
            RG.check_read(bad)
    assert RG.check_read(40.0).disposition == RG.READ   # exactly 40 is fine
