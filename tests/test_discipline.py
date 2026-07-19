import numpy as np

from aegis_brain.discipline import (
    deflated_sharpe_from_returns,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    probability_of_backtest_overfitting,
)


def test_psr_strong_signal_high():
    rng = np.random.default_rng(0)
    r = rng.normal(0.01, 0.02, 240)  # per-obs SR ~0.5
    sr = r.mean() / r.std(ddof=1)
    assert probabilistic_sharpe_ratio(sr, len(r)) > 0.99


def test_dsr_deflates_with_trial_count():
    rng = np.random.default_rng(1)
    r = rng.normal(0.003, 0.02, 120)
    few = deflated_sharpe_from_returns(r, n_trials=2, sr_variance=0.01)
    many = deflated_sharpe_from_returns(r, n_trials=500, sr_variance=0.01)
    assert many["dsr"] < few["dsr"]


def test_expected_max_sharpe_grows_with_trials():
    assert expected_max_sharpe(100, 0.01) > expected_max_sharpe(10, 0.01) > 0


def test_pbo_detects_noise_selection():
    rng = np.random.default_rng(2)
    noise = rng.normal(0, 0.02, size=(240, 50))  # 50 configs of pure noise
    report = probability_of_backtest_overfitting(noise)
    # selecting the best of noise must NOT look robust (pbo ~0.5 in theory)
    assert report["pbo"] >= 0.3


def test_pbo_recognizes_dominant_config():
    rng = np.random.default_rng(3)
    perf = rng.normal(0, 0.02, size=(240, 10))
    perf[:, 0] += 0.02  # config 0 genuinely dominates
    report = probability_of_backtest_overfitting(perf)
    assert report["pbo"] <= 0.2
