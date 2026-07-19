import numpy as np
import pandas as pd
import pytest

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.gate.adoption import evaluate_candidate
from aegis_brain.gate.registry import cumulative_trial_count, register_trial
from aegis_brain.harness.runner import WalkForwardConfig, build_design, run_walk_forward
from aegis_brain.signals.base import Signal


def _panel_with_planted_alpha(n_months=60, n_syms=120, seed=0, alpha=0.02):
    """Symbols 0..9 get persistent extra drift; the quality feature knows who."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2017-01-31", periods=n_months, freq="ME")
    cols = [f"S{i}" for i in range(n_syms)]
    ret = pd.DataFrame(rng.normal(0.003, 0.06, (n_months, n_syms)), index=idx, columns=cols)
    ret.iloc[:, :10] += alpha
    price = pd.DataFrame(20.0, index=idx, columns=cols)
    dv = pd.DataFrame(1e6, index=idx, columns=cols)
    quality = pd.DataFrame(0.0, index=idx, columns=cols)
    quality.iloc[:, :10] = 1.0
    panel = Panel(monthly_ret=ret, month_end_price=price, monthly_dollar_vol=dv)
    sig = Signal("quality", "planted alpha marker (test only)", lambda p: quality)
    return panel, sig


def test_design_has_no_same_month_leak():
    panel, sig = _panel_with_planted_alpha()
    design = build_design(panel, [sig])
    m = design.index.get_level_values("month")[0]
    sym = design.xs(m, level="month").index[0]
    # fwd_ret at (m, sym) must equal the NEXT month's realized return
    nxt = panel.monthly_ret.index[panel.monthly_ret.index.get_loc(m) + 1]
    assert design.loc[(m, sym), "fwd_ret"] == pytest.approx(panel.monthly_ret.loc[nxt, sym])


def test_walk_forward_finds_planted_alpha():
    panel, sig = _panel_with_planted_alpha()
    cfg = WalkForwardConfig(min_train_months=18, refit_every=6, top_frac=0.10,
                            min_names_per_month=30, cost_bps_one_way=25.0)
    out = run_walk_forward(panel, [sig], cfg)
    assert out["summary"]["months"] >= 24
    # top decile should capture the planted names → positive excess vs EW universe
    assert out["summary"]["mean_excess_vs_universe_ew"] > 0.005


def test_walk_forward_noise_has_no_edge():
    rng = np.random.default_rng(42)
    idx = pd.date_range("2017-01-31", periods=60, freq="ME")
    cols = [f"S{i}" for i in range(120)]
    ret = pd.DataFrame(rng.normal(0.003, 0.06, (60, 120)), index=idx, columns=cols)
    panel = Panel(
        monthly_ret=ret,
        month_end_price=pd.DataFrame(20.0, index=idx, columns=cols),
        monthly_dollar_vol=pd.DataFrame(1e6, index=idx, columns=cols),
    )
    noise_sig = Signal(
        "noise", "pure noise control (test only)",
        lambda p: pd.DataFrame(rng.normal(size=p.monthly_ret.shape),
                               index=p.monthly_ret.index, columns=p.monthly_ret.columns),
    )
    cfg = WalkForwardConfig(min_train_months=18, refit_every=6, min_names_per_month=30)
    out = run_walk_forward(panel, [noise_sig], cfg)
    assert abs(out["summary"]["t_stat_excess"]) < 3.0


def test_registry_idempotent_and_counts(tmp_path):
    path = tmp_path / "registry.jsonl"
    base = cumulative_trial_count(registry_path=path)
    register_trial("T-X", "h", "e", "k", registry_path=path)
    register_trial("T-X", "h", "e", "k", registry_path=path)  # no double count
    assert cumulative_trial_count(registry_path=path) == base + 1


def test_gate_rejects_without_pbo_matrix():
    rng = np.random.default_rng(5)
    good = rng.normal(0.02, 0.02, 120)
    report = evaluate_candidate(good, n_trials=15)
    assert report["verdict"] == "REJECT"  # no perf_matrix → cannot ship
    assert any("PBO" in r for r in report["reasons"])


def test_gate_adopts_genuine_dominant_candidate():
    rng = np.random.default_rng(6)
    good = rng.normal(0.02, 0.02, 120)
    batch = rng.normal(0.0, 0.02, size=(120, 10))
    batch[:, 0] = good
    report = evaluate_candidate(good, perf_matrix=batch, n_trials=15)
    assert report["dsr"]["dsr"] > 0.95
    assert report["verdict"] == "ADOPT-CANDIDATE"
