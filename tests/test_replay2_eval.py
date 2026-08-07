"""REPLAY-2 evaluation machinery — unit tests for the pieces that can fail
silently: the empirical p-value, BH step-up, and the D1 evaluator's terminal
routing on a synthetic cell."""

import numpy as np
import pytest

from aegis_brain.calibration.replay2_eval import (
    bh_reject,
    build_null_cdfs,
    empirical_p,
    evaluate_d1,
)
from aegis_brain.calibration.ruleset import Ruleset

B10 = Ruleset(
    name="B10-test",
    explore_t_ic=1.5, explore_t_net=None, explore_rank_by="t_ic",
    explore_segments=("largemid", "small"), explore_top_n=10,
    confirm_t_ic=0.5, confirm_t_net=None,
    confirm_sign_ic=True, confirm_sign_net=False, confirm_book="prod",
    dsr_book="prod", dsr_n_trials=179, dsr_threshold=0.0, pbo_threshold=1.0,
)


def test_empirical_p_bounds_and_monotone():
    null = np.sort(np.array([0.0, 0.5, 1.0, 1.5, 2.0]))
    # far right tail: add-one smoothing keeps p > 0
    assert empirical_p(99.0, null) == pytest.approx(1 / 6)
    # far left: p == 1
    assert empirical_p(-99.0, null) == pytest.approx(1.0)
    # ties count as >= (side='left')
    assert empirical_p(1.5, null) == pytest.approx(3 / 6)
    assert empirical_p(1.5001, null) < empirical_p(1.4999, null)


def test_bh_reject_known_case():
    # classic: m=4, q=0.1 -> thresholds 0.025/0.05/0.075/0.1
    flags = bh_reject([0.01, 0.04, 0.30, 0.90], 0.10)
    assert flags == [True, True, False, False]
    # step-up property: a large p can drag smaller ones in
    flags = bh_reject([0.01, 0.02, 0.074], 0.10)
    assert flags == [True, True, True]
    assert bh_reject([0.9, 0.8], 0.10) == [False, False]


def _cell(inj_t_ic: float, null_t: float = 0.0, confirm_t_ic: float = 2.0,
          ic_mean: float = 0.01):
    ex = {seg: {"injected_edge": {"t_ic": inj_t_ic, "t_net": 0.0,
                                  "contaminated": False, "months": 180},
                "nullsig": {"t_ic": null_t, "t_net": 0.0,
                            "contaminated": False, "months": 180}}
          for seg in ("largemid", "small")}
    conf = {f"{seg}/prod": {"t_ic": confirm_t_ic, "t_net": 0.0,
                            "mean_excess_bps": 1.0, "ic_mean": ic_mean,
                            "months": 72}
            for seg in ("largemid", "small")}
    dsr = {f"{seg}/prod_179": 0.5 for seg in ("largemid", "small")}
    return {"explore": ex, "confirm": conf, "dsr": dsr, "pbo": 0.5}


def _cdfs():
    null = np.sort(np.random.default_rng(0).standard_normal(400))
    return {(n, s): null for n in ("injected_edge", "nullsig")
            for s in ("largemid", "small")}


def test_evaluate_d1_adopts_strong_and_rejects_null():
    cdfs = _cdfs()
    strong = evaluate_d1(_cell(inj_t_ic=5.0), B10, cdfs, q=0.10)
    assert strong["terminal"] == "adopt"
    weak = evaluate_d1(_cell(inj_t_ic=0.0), B10, cdfs, q=0.10)
    assert weak["terminal"] == "no_graduate"


def test_evaluate_d1_confirm_wall_still_kills():
    cdfs = _cdfs()
    row = evaluate_d1(_cell(inj_t_ic=5.0, ic_mean=-0.01), B10, cdfs, q=0.10)
    assert row["terminal"] == "confirm_fail"


def test_build_null_cdfs_shapes():
    reps = [{"cells": {"a0.0/base": _cell(inj_t_ic=float(i))}}
            for i in range(5)]
    cdfs = build_null_cdfs(reps)
    assert len(cdfs[("injected_edge", "largemid")]) == 5
    assert list(cdfs[("injected_edge", "small")]) == sorted(
        cdfs[("injected_edge", "small")])
