"""TRIAL-TGT-REBUILD — nominal target-price signals (frozen spec in TRIALS/).

Builds two [month x permno] wide frames from ibes_ptgdet nominal targets:
  tgt_upside  median(latest per-analyst 12m target, 90d window) / price - 1
  tgt_ld      tgt_upside masked to at-or-below-median target dispersion
Split guard: targets straddling an ibes_adj spdates event are DROPPED
(no adjustment arithmetic — the original family died of exactly that).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.batch5 import _cusip_sym
from aegis_brain.factory.signals import FactorySignal

logger = logging.getLogger(__name__)
RAW = MODULE_ROOT / "data" / "wrds_raw"

WINDOW_DAYS = 90
MIN_ANALYSTS = 3


def _nominal_price(panel: Panel) -> pd.DataFrame:
    msf = pd.read_parquet(RAW / "crsp_msf.parquet",
                          columns=["permno", "date", "prc"])
    msf["sym"] = msf["permno"].astype(int).astype(str)
    msf["m"] = pd.to_datetime(msf["date"]).dt.to_period("M").dt.to_timestamp("M")
    wide = (msf.pivot_table(index="m", columns="sym", values="prc",
                            aggfunc="last").abs())
    return wide.reindex(index=panel.monthly_ret.index,
                        columns=panel.monthly_ret.columns)


def build_tgt_frames(panel: Panel) -> dict[str, pd.DataFrame]:
    pt = pd.read_parquet(RAW / "ibes_ptgdet.parquet",
                         columns=["ticker", "cusip", "amaskcd", "anndats",
                                  "horizon", "value", "estcur"])
    pt = pt.dropna(subset=["cusip", "amaskcd", "anndats", "value"])
    pt = pt[(pt["horizon"].astype(str).str.strip() == "12") & (pt["value"] > 0)]
    pt = pt[pt["estcur"].isna() | (pt["estcur"] == "USD")].copy()
    pt["anndats"] = pd.to_datetime(pt["anndats"])
    pt["c8"] = pt["cusip"].astype(str).str.upper().str[:8]
    pt = pt.merge(_cusip_sym(panel), on="c8")
    pt = pt[pt["sym"].isin(panel.monthly_ret.columns)]

    adj = pd.read_parquet(RAW / "ibes_adj.parquet")
    adj["spdates"] = pd.to_datetime(adj["spdates"])
    splits = adj.dropna(subset=["spdates"]).groupby("ticker")["spdates"].apply(
        lambda s: np.sort(s.unique()))

    price = _nominal_price(panel)
    months = [m for m in panel.monthly_ret.index
              if m >= pd.Timestamp("2003-06-30")]
    up_rows, ld_rows = {}, {}
    for m in months:
        w = pt[(pt["anndats"] > m - pd.Timedelta(days=WINDOW_DAYS))
               & (pt["anndats"] <= m)]
        if w.empty:
            continue
        # split guard: drop targets with a split event in (anndats, m]
        def _clean(g: pd.DataFrame) -> pd.DataFrame:
            sp = splits.get(g.name)
            if sp is None:
                return g
            sp = sp[(sp <= np.datetime64(m))]
            if len(sp) == 0:
                return g
            last_split = sp.max()
            return g[g["anndats"].values >= last_split]
        w = w.groupby("ticker", group_keys=False).apply(_clean)
        if w.empty:
            continue
        latest = (w.sort_values("anndats")
                   .drop_duplicates(["sym", "amaskcd"], keep="last"))
        g = latest.groupby("sym")["value"]
        med, sd, n = g.median(), g.std(ddof=1), g.size()
        px = price.loc[m]
        ok = (n >= MIN_ANALYSTS) & px.reindex(med.index).notna() \
            & (px.reindex(med.index) > 0)
        med, sd = med[ok], sd[ok]
        px = px.reindex(med.index)
        upside = med / px - 1.0
        disp = sd / px
        low = disp <= disp.median()
        up_rows[m] = upside
        ld_rows[m] = upside.where(low)
    up = pd.DataFrame(up_rows).T.reindex(index=panel.monthly_ret.index,
                                         columns=panel.monthly_ret.columns)
    ld = pd.DataFrame(ld_rows).T.reindex_like(up)
    logger.info("tgt frames: %d months, mean coverage upside=%.0f ld=%.0f",
                len(up_rows), up.notna().sum(axis=1).mean(),
                ld.notna().sum(axis=1).mean())
    return {"tgt_upside": up, "tgt_ld": ld}


def build_signals(panel: Panel) -> list[FactorySignal]:
    frames = build_tgt_frames(panel)
    return [
        FactorySignal("tgt_upside",
                      "raw median 12m target implied upside (nominal, "
                      "split-guarded); prior flat-to-negative",
                      (lambda p, f=frames["tgt_upside"]: f), +1),
        FactorySignal("tgt_ld",
                      "implied upside conditioned on low target dispersion "
                      "(PSZ 2025); prior positive IC",
                      (lambda p, f=frames["tgt_ld"]: f), +1),
    ]
