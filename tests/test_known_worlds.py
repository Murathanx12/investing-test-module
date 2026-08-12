"""Guards for GRAND-ARENA-1 PHASE 1.

These are not tests of a result. They are tests of the two things that would
make every result in the phase meaningless without announcing themselves:

* the splitter leaking the label horizon back into training, and
* a world's identity leaking through the feature schema.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.arena.known_learners import (T_BAR, effect_block,
                                              purged_walk_forward)
from aegis_brain.arena.known_worlds import (FEATURES, WORLD_IDS, make_world,
                                            verify)


def test_splits_are_temporal_disjoint_and_purged():
    folds = purged_walk_forward(299, n_folds=8, min_train=96, embargo=3,
                                horizon=1)
    assert len(folds) == 8
    for f in folds:
        assert set(f.train_t).isdisjoint(set(f.test_t))
        # every training month's LABEL (t+horizon) must land before the test
        # window opens, with the embargo on top
        assert f.train_t.max() + 1 + 3 <= f.test_t.min()
        assert f.train_t.min() == 0                      # expanding window
    # test blocks tile forward and never overlap
    for a, b in zip(folds, folds[1:]):
        assert a.test_t.max() < b.test_t.min()


def test_split_refuses_an_impossible_request():
    with pytest.raises(ValueError):
        purged_walk_forward(100, n_folds=8, min_train=96, embargo=3, horizon=1)


@pytest.mark.parametrize("wid", WORLD_IDS)
def test_every_world_is_what_it_claims(wid):
    """The plant must be measurable before any learner is scored on it."""
    w = make_world(wid)
    v = verify(w)
    assert v["ok"], f"world {wid} failed its own check: {v['checks']}"


def test_feature_schema_is_identical_across_worlds():
    """A world whose identity leaks through its columns is a rigged test."""
    cols = None
    for wid in WORLD_IDS:
        w = make_world(wid, n_months=120)
        present = [c for c in FEATURES if c in w.panel.columns]
        assert present == FEATURES, f"{wid} is missing {set(FEATURES) - set(present)}"
        if cols is None:
            cols = set(w.panel.columns)
        else:
            assert set(w.panel.columns) == cols, f"{wid} has a different schema"


def test_truth_columns_are_not_features():
    for name in ("true_state", "shock_next", "idio", "y", "y_idio", "mkt"):
        assert name not in FEATURES


def test_worlds_are_reproducible():
    a = make_world("A", n_months=120)
    b = make_world("A", n_months=120)
    pd.testing.assert_frame_equal(a.panel, b.panel)


def test_mde_uses_the_larger_of_hac_and_iid():
    rng = np.random.default_rng(0)
    x = pd.Series(rng.normal(0.01, 0.05, 200))
    blk = effect_block(x, label="t", unit="return")
    assert blk["se"] == max(blk["se_hac"], blk["se_iid"])
    assert blk["mde"] == pytest.approx(T_BAR * blk["se"], rel=1e-9)
    assert blk["detected"] == (abs(blk["mean"]) > blk["mde"])


def test_effect_block_refuses_a_short_series():
    blk = effect_block(pd.Series([0.1] * 5), label="t", unit="return")
    assert blk["mean"] is None and blk["detected"] is None
