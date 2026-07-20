import numpy as np
import pandas as pd

from aegis_brain.data.wrds_conn import _parse_pgpass_line
from aegis_brain.harness.runner import WalkForwardConfig, run_walk_forward

from tests.test_runner_and_gate import _panel_with_planted_alpha


def test_pgpass_parser_handles_escapes():
    line = r"wrds-pgdata.wharton.upenn.edu:9737:wrds:alice:p\:a\\ss:word"
    # NB: pgpass escapes ':' as '\:' and '\' as '\\' — password field is 5th
    f = _parse_pgpass_line(line)
    assert f[3] == "alice"
    assert f[4] == "p:a\\ss"


def test_pgpass_parser_plain():
    f = _parse_pgpass_line("host:9737:wrds:bob:plainpw")
    assert f == ["host", "9737", "wrds", "bob", "plainpw"]


def test_hold_band_cuts_turnover_on_churning_signal():
    """A noisy signal churns the top decile every month — the band must damp it."""
    from aegis_brain.data.eodhd_panel import Panel
    from aegis_brain.signals.base import Signal

    rng = np.random.default_rng(7)
    idx = pd.date_range("2017-01-31", periods=60, freq="ME")
    cols = [f"S{i}" for i in range(120)]
    panel = Panel(
        monthly_ret=pd.DataFrame(rng.normal(0.003, 0.06, (60, 120)), index=idx, columns=cols),
        month_end_price=pd.DataFrame(20.0, index=idx, columns=cols),
        monthly_dollar_vol=pd.DataFrame(1e6, index=idx, columns=cols),
    )
    churn_sig = Signal(
        "churn", "iid noise — maximally unstable ranks (test only)",
        lambda p: pd.DataFrame(rng.normal(size=p.monthly_ret.shape),
                               index=p.monthly_ret.index, columns=p.monthly_ret.columns),
    )
    base = WalkForwardConfig(min_train_months=18, refit_every=6, top_frac=0.10,
                             min_names_per_month=30)
    banded = WalkForwardConfig(min_train_months=18, refit_every=6, top_frac=0.10,
                               min_names_per_month=30, hold_band_frac=0.35)
    out_base = run_walk_forward(panel, [churn_sig], base)
    out_band = run_walk_forward(panel, [churn_sig], banded)
    assert (out_band["summary"]["mean_monthly_traded"]
            < 0.8 * out_base["summary"]["mean_monthly_traded"])


def test_hold_band_still_captures_planted_alpha():
    panel, sig = _panel_with_planted_alpha()
    banded = WalkForwardConfig(min_train_months=18, refit_every=6, top_frac=0.10,
                               min_names_per_month=30, hold_band_frac=0.35)
    out_band = run_walk_forward(panel, [sig], banded)
    assert out_band["summary"]["mean_excess_vs_universe_ew"] > 0.005


def test_hold_band_book_size_constant():
    panel, sig = _panel_with_planted_alpha()
    cfg = WalkForwardConfig(min_train_months=18, refit_every=6, top_frac=0.10,
                            min_names_per_month=30, hold_band_frac=0.5)
    out = run_walk_forward(panel, [sig], cfg)
    assert (out["monthly"]["n_long"] == out["monthly"]["n_long"].iloc[0]).all()