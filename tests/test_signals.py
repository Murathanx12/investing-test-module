import numpy as np
import pandas as pd

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.signals.price_signals import momentum_12_1, short_term_reversal


def _toy_panel(n_months=30, n_syms=4, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2017-01-31", periods=n_months, freq="ME")
    cols = [f"S{i}" for i in range(n_syms)]
    ret = pd.DataFrame(rng.normal(0.005, 0.05, (n_months, n_syms)), index=idx, columns=cols)
    price = pd.DataFrame(20.0, index=idx, columns=cols)
    dv = pd.DataFrame(1e6, index=idx, columns=cols)
    return Panel(monthly_ret=ret, month_end_price=price, monthly_dollar_vol=dv)


def test_momentum_12_1_excludes_current_month():
    panel = _toy_panel()
    mom = momentum_12_1(panel)
    t = panel.monthly_ret.index[15]
    # hand-compute: product of (1+r) over months t-11..t-1, exclusive of month t
    window = panel.monthly_ret["S0"].iloc[4:15]  # rows 4..14 = t-11..t-1
    expected = float(np.expm1(np.log1p(window).sum()))
    np.testing.assert_allclose(mom.loc[t, "S0"], expected, rtol=1e-10)
    # changing month-t return must NOT change the month-t momentum value
    panel2 = _toy_panel()
    panel2.monthly_ret.loc[t, "S0"] = 5.0
    mom2 = momentum_12_1(panel2)
    np.testing.assert_allclose(mom2.loc[t, "S0"], mom.loc[t, "S0"], rtol=1e-12)


def test_reversal_is_current_month_return():
    panel = _toy_panel()
    rev = short_term_reversal(panel)
    pd.testing.assert_frame_equal(rev, panel.monthly_ret)
