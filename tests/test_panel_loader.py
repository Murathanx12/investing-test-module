from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aegis_brain.config import EODHD_ROOT
from aegis_brain.data.eodhd_panel import build_panel, list_symbols, load_history


def test_list_symbols_and_build(fake_archive):
    syms = list_symbols("all", root=fake_archive)
    assert len(syms) == 10
    panel = build_panel(syms, start="2017-01-01", min_months=6)
    assert "ACT0" in panel.symbols and "DEAD0" in panel.symbols
    # months are month-end stamped
    assert panel.monthly_ret.index.is_monotonic_increasing


def test_delisting_stamp(fake_archive):
    syms = list_symbols("all", root=fake_archive)
    panel = build_panel(syms, start="2017-01-01", min_months=6, delist_return=-0.30)
    dead = panel.monthly_ret["DEAD1"].dropna()
    # last observation for the dead name should be the -30% Shumway stamp
    assert dead.iloc[-1] == pytest.approx(-0.30)
    # and it must occur AFTER its final traded month (2018-03)
    assert dead.index[-1] > pd.Timestamp("2018-03-31")


def test_eligibility_mask_shape(fake_archive):
    syms = list_symbols("all", root=fake_archive)
    panel = build_panel(syms, start="2017-01-01", min_months=6)
    elig = panel.eligible(min_price=1.0, min_dollar_vol=1_000.0)
    assert elig.shape == panel.monthly_ret.shape
    assert elig.dtypes.unique().tolist() == [np.dtype("bool")]


@pytest.mark.skipif(not Path(EODHD_ROOT).exists(), reason="real archive not present")
def test_real_archive_smoke():
    syms = list_symbols("active")
    assert len(syms) > 15_000
    df = load_history(syms["AAPL"])
    assert not df.empty
    assert {"Close", "Adjusted_close", "Volume"} <= set(df.columns)
