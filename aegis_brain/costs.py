"""Kyle-Obizhaeva invariance spread model (INSTR-COST-MODEL).

Quoted spread from KO (Econometrica 2016), eq. (33) + Table 6 calibration:

    s_i / P_i = exp(-3.07) * sigma_i * (W_i / W*) ** (-1/3)

where sigma_i = daily return volatility, W_i = sigma_i * (daily dollar
volume) is trading activity, and W* = 0.02 * 40 * 1e6 = 800,000 is the
benchmark stock (sigma 2%/day, $40, 1M shares/day -> ~9 bps quoted spread,
matching KO Table 1 volume-group medians).

One-way trading cost = s/2 (half-spread, primary) or s (stress arm).
Inputs are the month's own realized daily stats (dsf_monthly_agg) — known
at the month-end trade time.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel

logger = logging.getLogger(__name__)
RAW = MODULE_ROOT / "data" / "wrds_raw"

W_STAR = 0.02 * 40.0 * 1e6
LN_SBAR = -3.07
FLOOR_BPS, CAP_BPS = 1.0, 500.0


def build_spread_frame(panel: Panel) -> pd.DataFrame:
    """[month x sym] ONE-WAY half-spread cost in bps (KO quoted spread / 2)."""
    d = pd.read_parquet(RAW / "dsf_monthly_agg.parquet",
                        columns=["permno", "month", "n_days", "vol_d",
                                 "dollar_vol"])
    d = d.dropna(subset=["vol_d", "dollar_vol", "n_days"])
    d = d[(d["vol_d"] > 0) & (d["dollar_vol"] > 0) & (d["n_days"] > 0)]
    d["sym"] = d["permno"].astype(int).astype(str)
    d["m"] = (pd.to_datetime(d["month"], utc=True).dt.tz_localize(None)
              .dt.to_period("M").dt.to_timestamp("M"))
    daily_dvol = d["dollar_vol"] / d["n_days"]
    w = d["vol_d"] * daily_dvol
    spread_frac = np.exp(LN_SBAR) * d["vol_d"] * (w / W_STAR) ** (-1.0 / 3.0)
    d["half_spread_bps"] = (spread_frac * 1e4 / 2.0).clip(FLOOR_BPS, CAP_BPS)
    wide = (d.pivot_table(index="m", columns="sym", values="half_spread_bps",
                          aggfunc="last")
            .reindex(index=panel.monthly_ret.index,
                     columns=panel.monthly_ret.columns))
    cov = wide.notna().sum(axis=1)
    logger.info("spread frame: mean monthly coverage %.0f names", cov.mean())
    return wide
