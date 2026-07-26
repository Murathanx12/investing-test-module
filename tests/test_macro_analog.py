"""INSTR-REGIME-ANALOG engine tests — synthetic data, no disk/network."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aegis_brain.macro.macro_analog import (EPISODE_GAP_TD, NMS_TD,
                                            SELF_EXCLUSION_TD, cluster_episodes,
                                            retrieve_analogs, robust_z)


def _z(n_days: int = 2000, n_feat: int = 15, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2005-01-03", periods=n_days)
    d = pd.DataFrame(rng.normal(size=(n_days, n_feat)),
                     index=idx, columns=[f"f{i}" for i in range(n_feat)])
    return robust_z(d)


def test_retrieval_deterministic():
    z = _z()
    q = z.index[-1]
    a1 = retrieve_analogs(z, q, n=20)
    a2 = retrieve_analogs(z, q, n=20)
    assert list(a1.index) == list(a2.index)
    assert (a1["distance"] == a2["distance"]).all()


def test_self_exclusion_and_count():
    z = _z()
    q = z.index[-1]
    a = retrieve_analogs(z, q, n=30)
    assert len(a) == 30
    qpos = z.index.get_loc(q)
    for d in a.index:
        assert qpos - z.index.get_loc(d) >= SELF_EXCLUSION_TD


def test_nms_spacing():
    z = _z()
    a = retrieve_analogs(z, z.index[-1], n=40)
    pos = sorted(z.index.get_loc(d) for d in a.index)
    assert min(np.diff(pos)) >= NMS_TD


def test_nearest_is_planted_twin():
    z = _z()
    q = z.index[-1]
    twin = z.index[500]
    z.loc[twin] = z.loc[q]                       # exact twin far in the past
    a = retrieve_analogs(z, q, n=10)
    assert a.index[0] == twin
    assert a["distance"].iloc[0] == pytest.approx(0.0)


def test_episode_clustering_merges_adjacent():
    z = _z()
    q = z.index[-1]
    picked = [z.index[300], z.index[300 + EPISODE_GAP_TD // 2],  # same episode
              z.index[1200]]                                     # separate
    analogs = pd.DataFrame({"distance": [0.5, 0.7, 0.9],
                            "dist_percentile": [0.01, 0.02, 0.03]},
                           index=pd.Index(picked))
    eps = cluster_episodes(analogs, z)
    assert len(eps) == 2
    assert sorted(e["n_analogs"] for e in eps) == [1, 2]


def test_incomplete_query_vector_raises():
    z = _z()
    q = z.index[-1]
    z.loc[q, "f0"] = np.nan
    with pytest.raises(KeyError):
        retrieve_analogs(z, q)


def test_robust_z_centering():
    d = pd.DataFrame({"a": np.arange(100.0)})
    zz = robust_z(d)
    assert zz["a"].median() == pytest.approx(0.0)
