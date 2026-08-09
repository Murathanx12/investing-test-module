"""Walk-forward regime labels — computed from information available at t only.

EXECUTION_STANDARD §5.4: regime *reporting* blocks may be defined ex-post;
regime *trading inputs* may not. A full-sample HMM or a "bear market" defined
by where the market later bottomed is look-ahead wearing a lab coat.

The label here is deliberately primitive and unfittable: the sign of the
market's trailing 12-month total return at the formation month, with a
trailing-vol brake. Both use closed months only. No parameter is chosen by
looking at strategy performance.
"""

from __future__ import annotations

import pandas as pd


def trailing_12m_risk_on(mkt: pd.Series, *, vol_window: int = 36,
                         vol_multiple: float = 1.5) -> pd.Series:
    """True when the trailing year was positive AND vol is not extreme.

    Indexed by formation month; a strategy consuming it at formation month m
    sees only returns realized through m.
    """
    mkt = mkt.astype(float).sort_index()
    trail = (1.0 + mkt).rolling(12, min_periods=12).apply(
        lambda x: x.prod(), raw=True) - 1.0
    vol = mkt.rolling(12, min_periods=12).std()
    vol_ref = vol.rolling(vol_window, min_periods=24).median()
    calm = (vol <= vol_multiple * vol_ref) | vol_ref.isna()
    out = (trail > 0) & calm
    # before enough history exists, default risk-on (no look-ahead either way)
    out[trail.isna()] = True
    return out.rename("risk_on")
