"""Decision rule v2 — the gate ladder that will judge PF-2.

Adjudication code that has never been tested is a way to lose a campaign to a
typo. Every branch of the taxonomy gets a case here.
"""
from __future__ import annotations

import pytest

from scripts.pf_run_batch2 import adjudicate_v2


def card(*, excess=0.05, alpha=0.03, t_alpha=3.0, blocks=5, ruin=0.05,
         ex_best=0.04, ex_top=0.01, years=59.5, tw=10.0) -> dict:
    return {
        "headline": {"excess_cagr_net": excess,
                     "terminal_wealth_multiple_vs_benchmark": tw},
        "robustness": {"excess_cagr_ex_best_year": ex_best,
                       "excess_cagr_ex_top_1pct_months": ex_top},
        "regimes_gate": {"_summary": {"blocks_positive_excess": blocks,
                                      "blocks_evaluated": 5}},
        "tail": {"p_maxdd_worse_than_60pct": ruin},
        "factor_alpha": {"ff5_umd": {"ann_alpha": alpha, "t_alpha": t_alpha}},
        "window": {"years": years},
    }


PASS_PLACEBO = {"PASS": True}
FAIL_PLACEBO = {"PASS": False}


def grid(c, n_pos=8):
    return [c] + [card(excess=(0.01 if i < n_pos - 1 else -0.01))
                  for i in range(7)]


def test_everything_passing_is_engine_skill():
    c = card()
    v = adjudicate_v2(c, grid(c), PASS_PLACEBO)
    assert v["verdict"] == "WINNER (ENGINE SKILL)"


def test_no_factor_alpha_but_beats_investable_alternatives_is_a_product():
    c = card(alpha=0.009, t_alpha=0.71)
    v = adjudicate_v2(c, grid(c), PASS_PLACEBO, product_pass=True)
    assert v["verdict"] == "WINNER (FACTOR-HARVEST PRODUCT)"
    assert "ENGINE" not in v["verdict"]


def test_no_factor_alpha_and_loses_to_alternatives_is_a_near_miss():
    c = card(alpha=0.009, t_alpha=0.71)
    v = adjudicate_v2(c, grid(c), PASS_PLACEBO, product_pass=False)
    assert v["verdict"] == "NEAR-MISS(G4a_factor_alpha)"


def test_alpha_big_but_insignificant_fails_the_factor_gate():
    """+5%/yr at t=1.1 is not evidence; the gate needs both."""
    c = card(alpha=0.05, t_alpha=1.1)
    v = adjudicate_v2(c, grid(c), PASS_PLACEBO, product_pass=True)
    assert v["checks"]["G4a_factor_alpha"] is False


def test_one_failed_gate_is_a_named_near_miss():
    c = card(blocks=3)
    v = adjudicate_v2(c, grid(c), PASS_PLACEBO)
    assert v["verdict"] == "NEAR-MISS(regime_blocks_ge_4_of_5)"


def test_placebo_failure_always_fails_however_good_the_returns():
    c = card(excess=0.20, alpha=0.10, t_alpha=9.0)
    v = adjudicate_v2(c, grid(c), FAIL_PLACEBO)
    assert v["verdict"] == "FAILED"
    assert v["reason_class"] == "placebo_gate"


def test_untested_placebo_cannot_graduate_anything():
    c = card()
    v = adjudicate_v2(c, grid(c), None)
    assert v["verdict"].startswith("PROVISIONAL[")
    assert "placebo_untested" in v["reason_class"]


def test_two_failed_gates_is_a_failure_not_a_near_miss():
    c = card(blocks=3, ruin=0.5)
    v = adjudicate_v2(c, grid(c), PASS_PLACEBO)
    assert v["verdict"] == "FAILED"
    assert set(v["failed_gates"]) == {"regime_blocks_ge_4_of_5", "G8_ruin_le_20pct"}


def test_negative_excess_is_failed_before_any_other_reading():
    c = card(excess=-0.02, alpha=0.05, t_alpha=5.0)
    v = adjudicate_v2(c, grid(c), PASS_PLACEBO)
    assert v["verdict"] == "FAILED"
    assert v["reason_class"] == "negative_excess"


def test_short_window_with_several_failures_is_unresolved():
    c = card(excess=0.01, alpha=0.0, t_alpha=0.1, blocks=2, years=10.0)
    v = adjudicate_v2(c, grid(c), PASS_PLACEBO)
    assert v["verdict"] == "UNRESOLVED"
    assert v["reason_class"] == "window_too_short"


def test_pf1_engine_alpha_would_now_read_as_a_two_gate_failure():
    """Sanity anchor on the real banked numbers: PF-1's ENGINE-ALPHA fails
    regime breadth (3/5) AND the new factor gate (alpha 0.89%, t 0.71)."""
    c = card(excess=0.0521, alpha=0.0089, t_alpha=0.71, blocks=3, ruin=0.005,
             ex_best=0.042, ex_top=0.038, tw=15.58)
    v = adjudicate_v2(c, grid(c), PASS_PLACEBO, product_pass=True)
    assert v["verdict"] == "FAILED"
    assert set(v["failed_gates"]) == {"regime_blocks_ge_4_of_5", "G4a_factor_alpha"}
