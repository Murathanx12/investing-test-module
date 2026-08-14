"""GRAPH-COVARIANCE-1 primitives — contract, known-answer and leakage tests.

THE THREE KINDS OF TEST HERE, AND WHY EACH EXISTS
=================================================
1. CONTRACT — shapes, invariants, and the failures that must be loud. A capped
   simplex projection that quietly returns something not summing to one would
   make every realised variance downstream wrong in a way that looks like a
   result, so it raises instead.

2. KNOWN-ANSWER — a signal is PLANTED in a synthetic world and the pipeline is
   required to recover it. If a machine cannot find an effect that is definitely
   there, its null on real data means nothing. This is the same instrument as
   the trial's own `oracle_on_edges` power gate, one level down: measure the
   ceiling before trusting the floor.

3. LEAKAGE — the labels are shuffled and the recovered effect must collapse to
   chance. A pipeline that still "finds" something after the answer key is
   destroyed is measuring its own machinery.

Everything here is offline and deterministic. No network, no files.
"""

from __future__ import annotations

import numpy as np
import pytest

from scripts.gc1_cov import (
    corr_to_cov,
    effective_bets,
    gmv_long_only,
    gmv_weights,
    ledoit_wolf_corr,
    predicted_vol,
    project_capped_simplex,
    realised_max_drawdown,
    realised_vol,
    repair_correlation,
    rmt_denoise_corr,
)


# ── helpers ─────────────────────────────────────────────────────────────────

def _block_corr(n: int, k: int, rho: float) -> np.ndarray:
    """`n` names in `n//k` equal blocks; within-block correlation `rho`."""
    P = np.eye(n)
    lab = np.arange(n) // k
    same = lab[:, None] == lab[None, :]
    P[same] = rho
    np.fill_diagonal(P, 1.0)
    return P


def _draw(P: np.ndarray, T: int, seed: int, vol: np.ndarray | None = None
          ) -> np.ndarray:
    """`T` draws from N(0, D P D) using the project's RNG convention."""
    rng = np.random.default_rng(seed)
    n = P.shape[0]
    L = np.linalg.cholesky(P + 1e-10 * np.eye(n))
    X = rng.standard_normal((T, n)) @ L.T
    return X if vol is None else X * vol


# ── 1. CONTRACT ─────────────────────────────────────────────────────────────

def test_repair_returns_psd_unit_diagonal_from_an_indefinite_input():
    rng = np.random.default_rng(0)
    A = rng.standard_normal((40, 40))
    A = 0.5 * (A + A.T)                       # symmetric, wildly indefinite
    np.fill_diagonal(A, 1.0)
    P, diag = repair_correlation(A)
    assert diag["min_eig_raw"] < 0, "the test input was supposed to be indefinite"
    assert np.allclose(np.diag(P), 1.0)
    assert np.allclose(P, P.T)
    assert np.linalg.eigvalsh(P).min() >= -1e-10
    assert diag["n_eigs_clipped"] > 0


def test_repair_leaves_a_valid_correlation_matrix_essentially_alone():
    P = _block_corr(30, 10, 0.4)
    R, diag = repair_correlation(P)
    assert diag["min_eig_raw"] > 0
    assert diag["n_eigs_clipped"] == 0
    np.testing.assert_allclose(R, P, atol=1e-12)


def test_repair_clips_entries_no_correlation_matrix_may_contain():
    # The ridge that predicts these entries is unconstrained and was measured
    # returning 1.0119 on the real panel. A correlation above one is not a
    # rounding issue, it is an invalid matrix.
    P = np.eye(6)
    P[0, 1] = P[1, 0] = 1.4
    P[2, 3] = P[3, 2] = -1.2
    R, diag = repair_correlation(P, corr_clip=0.99)
    assert diag["n_entries_out_of_range"] == 4
    assert np.abs(R).max() <= 1.0 + 1e-12


def test_regression_a_near_zero_eigenvalue_floor_breaks_minimum_variance():
    """THE DEFECT THIS TRIAL SHIPPED AND THEN CAUGHT — pinned so it cannot
    return.

    Flooring the eigenvalues of an indefinite predicted matrix at ~0 does not
    repair it. It creates directions of almost-zero variance, and a minimum-
    variance solve is exactly the machine that finds them and levers into them.
    Measured on the real panel at a 1e-8 floor: the matrix forecast 0.13%
    annualised volatility for a portfolio that realised 2.7% — a calibration
    ratio of 4,519 — while every PSD check passed.

    The test asserts the failure mode under the old floor and its absence under
    the relative one, so the assertion is about the FIX, not about a constant.
    """
    rng = np.random.default_rng(99)
    n = 120
    # A predicted-style matrix: mostly small entries, genuinely indefinite.
    A = np.eye(n)
    off = rng.normal(0.0, 0.06, size=(n, n))
    A = A + np.triu(off, 1) + np.triu(off, 1).T
    np.fill_diagonal(A, 1.0)
    assert np.linalg.eigvalsh(A).min() < 0, "input must be indefinite"

    vol = np.full(n, 0.02)
    P_bad, d_bad = repair_correlation(A, eig_floor_rel=1e-8)
    P_ok, d_ok = repair_correlation(A, eig_floor_rel=0.10)

    w_bad = gmv_weights(corr_to_cov(P_bad, vol))
    w_ok = gmv_weights(corr_to_cov(P_ok, vol))

    # The pathology, stated three ways.
    assert d_bad["cond"] > 1e6 > d_ok["cond"]
    assert predicted_vol(corr_to_cov(P_bad, vol), w_bad) < 0.1 * \
        predicted_vol(corr_to_cov(P_ok, vol), w_ok)
    # Leverage blows up too. The factor here is ~2.1x; on the real panel, whose
    # matrices were far more indefinite (minimum eigenvalue -0.34 against this
    # synthetic's much milder one), gross exposure went 2.74 -> 5.97 on the
    # oracle arm. The direction is the assertion; the magnitude is data.
    assert np.abs(w_bad).sum() > 2.0 * np.abs(w_ok).sum(), (
        "the near-zero floor must produce the leverage blow-up it produced on "
        "the real panel")


def test_repair_rejects_a_non_square_input_loudly():
    with pytest.raises(ValueError):
        repair_correlation(np.zeros((3, 4)))


def test_corr_to_cov_rejects_a_mismatched_volatility_block():
    with pytest.raises(ValueError):
        corr_to_cov(np.eye(5), np.ones(4))


def test_gmv_weights_are_fully_invested_and_beat_equal_weight_in_sample():
    P = _block_corr(60, 10, 0.6)
    vol = np.linspace(0.01, 0.03, 60)
    S = corr_to_cov(P, vol)
    w = gmv_weights(S)
    assert np.isclose(w.sum(), 1.0)
    ew = np.full(60, 1.0 / 60)
    assert w @ S @ w < ew @ S @ ew


def test_capped_simplex_projection_sums_to_one_and_respects_the_box():
    rng = np.random.default_rng(3)
    v = rng.standard_normal(200)
    w = project_capped_simplex(v, cap=0.10)
    assert np.isclose(w.sum(), 1.0, atol=1e-9)
    assert w.min() >= -1e-12
    assert w.max() <= 0.10 + 1e-12


def test_capped_simplex_refuses_an_infeasible_box_instead_of_returning_garbage():
    # 5 names capped at 10% each cannot sum to 1. Silence here would corrupt
    # every realised variance downstream, so it must raise.
    with pytest.raises(ValueError):
        project_capped_simplex(np.zeros(5), cap=0.10)


def test_long_only_solution_is_feasible_and_no_worse_than_its_start():
    P = _block_corr(50, 5, 0.5)
    vol = np.linspace(0.01, 0.04, 50)
    S = corr_to_cov(P, vol)
    w = gmv_long_only(S, cap=0.10, max_iters=5000, tol=1e-12)
    assert np.isclose(w.sum(), 1.0, atol=1e-8)
    assert w.min() >= -1e-10
    assert w.max() <= 0.10 + 1e-10
    ew = np.full(50, 1.0 / 50)
    assert w @ S @ w <= ew @ S @ ew + 1e-12


def test_long_only_reaches_the_unconstrained_optimum_when_it_is_feasible():
    # A matrix whose unconstrained GMV is interior to the box: the constrained
    # solve must find the same thing, which is what makes it trustworthy on the
    # matrices where the constraint DOES bind.
    P = _block_corr(20, 4, 0.3)
    S = corr_to_cov(P, np.full(20, 0.02))
    w_free = gmv_weights(S)
    assert w_free.min() > 0 and w_free.max() < 0.20
    w_box = gmv_long_only(S, cap=0.20, max_iters=20000, tol=1e-14)
    assert abs(w_box @ S @ w_box - w_free @ S @ w_free) < 1e-12


def test_realised_vol_and_drawdown_survive_missing_rows():
    R = np.full((100, 4), 0.001)
    R[10, 2] = np.nan
    w = np.full(4, 0.25)
    assert np.isfinite(realised_vol(R, w))
    assert realised_max_drawdown(R, w) <= 0.0


def test_effective_bets_counts_what_it_should():
    assert np.isclose(effective_bets(np.full(25, 1.0 / 25)), 25.0)
    assert np.isclose(effective_bets(np.array([1.0, 0.0, 0.0])), 1.0)


# ── 2. KNOWN-ANSWER — plant a correlation, recover it ───────────────────────

def test_known_answer_the_true_matrix_beats_a_wrong_one_out_of_sample():
    """The instrument's floor: if the TRUE covariance does not produce a lower
    realised variance than a deliberately wrong one, the metric cannot detect
    anything and every null measured with it is uninterpretable.

    This is the same logic as the trial's `oracle_on_edges` gate, at unit scale.
    """
    n, T_fwd = 60, 126
    P_true = _block_corr(n, 10, 0.7)
    vol = np.full(n, 0.02)
    S_true = corr_to_cov(P_true, vol)
    S_wrong = corr_to_cov(np.eye(n), vol)      # "everything is independent"

    w_true = gmv_weights(S_true)
    w_wrong = gmv_weights(S_wrong)

    wins = 0
    for seed in range(40):
        R = _draw(P_true, T_fwd, seed, vol)
        wins += realised_vol(R, w_true) < realised_vol(R, w_wrong)
    # Knowing the block structure must win the large majority of forward windows
    assert wins >= 36, f"true matrix only won {wins}/40 forward windows"


def test_known_answer_correcting_only_a_few_entries_still_helps():
    """The trial's actual situation: the graph touches ~0.58% of pairs. This
    plants a correlation in a SMALL number of off-diagonal entries that the
    baseline believes are zero, and requires the corrected matrix to win.

    If a sparse correction could never move a minimum-variance portfolio, the
    trial would be unpowered by construction and this test would fail — which is
    exactly the thing the `oracle_on_edges` gate is there to measure on the real
    panel rather than assume.
    """
    rng = np.random.default_rng(11)
    n, T_fwd, n_edges = 80, 126, 60
    P_true = np.eye(n)
    iu, ju = np.triu_indices(n, k=1)
    pick = rng.choice(len(iu), size=n_edges, replace=False)
    for a, b in zip(iu[pick], ju[pick]):
        P_true[a, b] = P_true[b, a] = 0.75
    P_true, _ = repair_correlation(P_true)

    vol = np.full(n, 0.02)
    w_corrected = gmv_weights(corr_to_cov(P_true, vol))
    w_blind = gmv_weights(corr_to_cov(np.eye(n), vol))

    wins = sum(realised_vol(_draw(P_true, T_fwd, s, vol), w_corrected)
               < realised_vol(_draw(P_true, T_fwd, s, vol), w_blind)
               for s in range(40))
    assert wins >= 34, f"sparse correction only won {wins}/40"


def test_known_answer_ledoit_wolf_shrinks_more_when_there_is_less_data():
    # The INTENSITY is the estimator's behaviour. The resulting off-diagonal
    # LEVEL is not: a 60-row sample has noisier raw correlations (mean |off|
    # 0.176 against 0.103 at T=2000) and stays above the long sample even after
    # being shrunk five times harder. Asserting on the level fails for a reason
    # that is not a bug, which is why this asserts on delta.
    P = _block_corr(40, 8, 0.5)
    _, d_near = ledoit_wolf_corr(_draw(P, 60, 5), return_intensity=True)
    _, d_far = ledoit_wolf_corr(_draw(P, 2000, 5), return_intensity=True)
    assert 0.0 < d_far < d_near <= 1.0, (d_near, d_far)
    assert d_near > 5 * d_far


def test_known_answer_rmt_collapses_the_noise_bulk_and_keeps_the_real_factor():
    P = _block_corr(50, 25, 0.6)                 # one strong block structure
    C = np.corrcoef(_draw(P, 120, 7), rowvar=False)
    D = rmt_denoise_corr(C, T=120)
    assert np.allclose(np.diag(D), 1.0)
    w_raw = np.sort(np.linalg.eigvalsh(C))
    w_den = np.sort(np.linalg.eigvalsh(D))
    # The dominant eigenvalue — the real block structure — survives.
    assert w_den.max() > 0.8 * w_raw.max()
    # The bulk is collapsed. Note the eigenvalues do NOT come out identical:
    # collapsing them and then rescaling to a unit diagonal reintroduces some
    # spread. That is the standard recipe behaving as designed, so the test
    # asserts the DISPERSION falls rather than that the values coincide.
    assert w_den[:-2].std() < 0.25 * w_raw[:-2].std()


# ── 3. LEAKAGE — destroy the answer key, the effect must die ────────────────

def test_leakage_shuffling_the_planted_structure_collapses_the_advantage():
    """The negative control for the known-answer test above.

    The SAME correction, the same number of entries, the same magnitude — but
    attached to randomly chosen pairs instead of the true ones. If the corrected
    matrix still wins, the win came from the machinery (adding off-diagonal mass
    changes a minimum-variance solve) rather than from knowing which pairs are
    related. That is precisely the confound the trial's three placebos exist to
    catch, and it is checked here at unit scale first.
    """
    rng = np.random.default_rng(23)
    n, T_fwd, n_edges = 80, 126, 60
    iu, ju = np.triu_indices(n, k=1)

    P_true = np.eye(n)
    pick = rng.choice(len(iu), size=n_edges, replace=False)
    for a, b in zip(iu[pick], ju[pick]):
        P_true[a, b] = P_true[b, a] = 0.75
    P_true, _ = repair_correlation(P_true)

    # the placebo: identical multiset of corrections, WRONG pairs
    P_fake = np.eye(n)
    fake = rng.choice(np.setdiff1d(np.arange(len(iu)), pick),
                      size=n_edges, replace=False)
    for a, b in zip(iu[fake], ju[fake]):
        P_fake[a, b] = P_fake[b, a] = 0.75
    P_fake, _ = repair_correlation(P_fake)

    vol = np.full(n, 0.02)
    w_true = gmv_weights(corr_to_cov(P_true, vol))
    w_fake = gmv_weights(corr_to_cov(P_fake, vol))
    w_blind = gmv_weights(corr_to_cov(np.eye(n), vol))

    true_wins, fake_wins = 0, 0
    for s in range(60):
        R = _draw(P_true, T_fwd, s, vol)         # reality follows P_true
        base = realised_vol(R, w_blind)
        true_wins += realised_vol(R, w_true) < base
        fake_wins += realised_vol(R, w_fake) < base
    assert true_wins >= 50, f"the real correction only won {true_wins}/60"
    assert fake_wins <= 40, (
        f"the shuffled correction won {fake_wins}/60 — the metric is rewarding "
        f"off-diagonal mass rather than knowing which pairs are related")
    assert true_wins > fake_wins


def test_leakage_predicted_vol_is_honest_about_a_matrix_that_is_wrong():
    """Calibration: a matrix that believes everything is independent must
    UNDER-predict the risk of the portfolio it chooses, when reality is
    correlated. If it did not, the calibration diagnostic would be blind."""
    n = 60
    P_true = _block_corr(n, 10, 0.7)
    vol = np.full(n, 0.02)
    S_blind = corr_to_cov(np.eye(n), vol)
    w = gmv_weights(S_blind)
    said = predicted_vol(S_blind, w)
    got = float(np.mean([realised_vol(_draw(P_true, 252, s, vol), w)
                         for s in range(20)]))
    assert got > said * 1.2, f"predicted {said:.4f} vs realised {got:.4f}"
