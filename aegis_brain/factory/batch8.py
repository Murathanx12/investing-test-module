"""Factory batch 8 — panel-round-4 adoptions (frozen in docs/STRATEGY_FACTORY.md
BEFORE any scan). Horizon-first declarations in the freeze doc.

si_trend   — CHANGE in short interest (3m), long decreases (Zhu-Duan trend-in-
             short-selling class; distinct from the dead dtc/si LEVEL family).
rd_gp      — R&D / market equity gated to top-half gross profitability
             (Chan-Lakonishok-Sougiannis 2001 x Novy-Marx conditioning; the
             qual_mom interaction pattern).
pead_agree — PEAD only when analyst SUE and time-series SUE AGREE positive
             (Livnat-Mendenhall 2006: drift largest on agreement). Declared
             a priori: fast decay, very high turnover, likely IC-real/net-dead
             at our cost model; scanned for the combiner shelf regardless.
"""

from __future__ import annotations

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.batch5 import _si_ratio
from aegis_brain.factory.batch7 import _annual_wide
from aegis_brain.factory.fundamentals import FundStore
from aegis_brain.factory.signals import FactorySignal

RAW = MODULE_ROOT / "data" / "wrds_raw"
DATA = MODULE_ROOT / "data"


def build_batch8(panel: Panel, store: FundStore) -> list[FactorySignal]:
    sir = _si_ratio(panel, store)
    si_chg = sir.diff(3)  # 3m change in SI/shares; SI data live 2006-07 ->

    ext = pd.read_parquet(RAW / "comp_funda_ext_cols.parquet",
                          columns=["gvkey", "datadate", "xrd"])
    ext["gvkey"] = ext["gvkey"].astype(str).str.strip()
    ext["datadate"] = pd.to_datetime(ext["datadate"])
    base = pd.read_parquet(RAW / "comp_funda.parquet",
                           columns=["gvkey", "datadate", "csho"])
    base["gvkey"] = base["gvkey"].astype(str).str.strip()
    base["datadate"] = pd.to_datetime(base["datadate"])
    f = ext.merge(base, on=["gvkey", "datadate"], how="inner")
    f = f.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"])
    xrd_w = _annual_wide(panel, f[["gvkey", "datadate", "xrd"]].dropna(), "xrd")
    csho_w = _annual_wide(panel, f[["gvkey", "datadate", "csho"]].dropna(), "csho")
    px = panel.month_end_price.abs()
    me = (csho_w * px).where(csho_w > 0)
    gp = store.get("gross_prof")

    su = pd.read_parquet(DATA / "sue_events.parquet",
                         columns=["permno", "rdq", "sue_ts", "sue_analyst"])
    su = su.dropna(subset=["rdq", "sue_ts", "sue_analyst"])
    agree = su[(su["sue_ts"] > 0) & (su["sue_analyst"] > 0)].copy()
    agree["val"] = agree[["sue_ts", "sue_analyst"]].min(axis=1)
    agree["sym"] = agree["permno"].astype("Int64").astype(str)
    agree["avail"] = pd.to_datetime(agree["rdq"]).dt.to_period("M").dt.to_timestamp("M")
    pead_w = (agree.pivot_table(index="avail", columns="sym", values="val",
                                aggfunc="last")
              .reindex(panel.monthly_ret.index).ffill(limit=2)
              .reindex(columns=panel.monthly_ret.columns))

    def si_trend(p: Panel) -> pd.DataFrame:
        return si_chg

    def rd_gp(p: Panel) -> pd.DataFrame:
        top_half = gp.ge(gp.median(axis=1), axis=0)
        r = xrd_w / me.where(me > 0)
        return r.where(top_half)

    def pead_agree(p: Panel) -> pd.DataFrame:
        return pead_w

    return [
        FactorySignal("si_trend", "3m CHANGE in short interest / shares — "
                      "rising shorting predicts losses beyond the level "
                      "(trend-in-short-selling class); long decreases; "
                      "horizon 1-6mo, turnover HIGH (declared risk).",
                      si_trend, -1),
        FactorySignal("rd_gp", "R&D / market equity within top-half gross "
                      "profitability — priced-out intangible investment "
                      "where quality confirms it is productive (CLS 2001 x "
                      "GP conditioning); horizon annual, turnover LOW.",
                      rd_gp, +1),
        FactorySignal("pead_agree", "PEAD gated on analyst+time-series SUE "
                      "agreement (Livnat-Mendenhall 2006), magnitude = min "
                      "z; horizon 1-3mo FAST decay, turnover VERY HIGH — "
                      "declared a priori likely net-dead at 25bps; scanned "
                      "for the combiner shelf.", pead_agree, +1),
    ]
