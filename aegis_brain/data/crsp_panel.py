"""CRSP monthly panel — the paper-grade L0 data spine (WRDS unlock, 2026-07-20).

Replaces the EODHD direction-check panel for backtests:
  - survivorship-free by construction (CRSP keeps dead names)
  - REAL delisting returns from crsp.msedelist, compounded into the final month
    (the EODHD panel had to guess with a flat Shumway -30%)
  - universe defined the CRSP-canonical way: share codes 10/11 (common stock),
    exchange codes 1/2/3 (NYSE/AMEX/NASDAQ)
  - identity key is PERMNO (stable through ticker changes), stringified to fit
    the Panel column convention.

Missing delisting returns are filled with the Shumway (1997) / Shumway-Warther
(1999) convention: -30% for performance-related delistings (dlstcd 500 or
520-584) on NYSE/AMEX, -55% on NASDAQ; 0 otherwise. Fill counts are reported.

CRSP monthly `vol` is in units of 100 shares; we approximate a median DAILY
dollar volume as abs(prc)*vol*100/21 so the Panel.eligible() floors keep the
same meaning they had on the EODHD panel.

Note: the annual-cut crsp.msf ends the previous December (currently 2024-12).
That is fine — historical trials run on CRSP; the live/forward window stays on
the forward paper clocks, which are the only scorecard anyway.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.data.eodhd_panel import RET_CAP, RET_FLOOR, Panel

logger = logging.getLogger(__name__)

PERFORMANCE_DLSTCDS = "(dlstcd = 500 or (dlstcd between 520 and 584))"


def fetch_crsp_monthly(db, start: str = "2002-01-01", end: str | None = None) -> pd.DataFrame:
    """Pull the filtered monthly file with names + delisting info server-side.

    Args:
        db: an open wrds.Connection.
    """
    end_clause = f"and a.date <= '{end}'" if end else ""
    q = f"""
        select a.permno, a.date, a.ret, a.prc, a.vol,
               b.exchcd,
               c.dlret, c.dlstcd, c.dlstdt
        from crsp.msf a
        join crsp.msenames b
          on a.permno = b.permno
         and a.date between b.namedt and coalesce(b.nameendt, current_date)
        left join crsp.msedelist c
          on a.permno = c.permno
         and date_trunc('month', a.date) = date_trunc('month', c.dlstdt)
        where a.date >= '{start}' {end_clause}
          and b.shrcd in (10, 11)
          and b.exchcd in (1, 2, 3)
    """
    df = db.raw_sql(q, date_cols=["date", "dlstdt"])
    logger.info("fetched %d monthly rows from crsp.msf", len(df))
    return df


def build_crsp_panel(df: pd.DataFrame) -> Panel:
    """Assemble a Panel (dates x permno-strings) from the fetched frame."""
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp("M")

    # Total return incl. delisting: (1+ret)(1+dlret)-1; dlret alone if ret NaN.
    dlret = df["dlret"]
    missing_dl = df["dlstcd"].notna() & dlret.isna()
    if missing_dl.any():
        # .fillna(False): dlstcd/exchcd arrive as nullable dtypes, so the masks
        # carry pd.NA on non-delist rows — np.where can't evaluate NA (raises
        # "boolean value of NA is ambiguous"). The fill is only *applied* where
        # missing_dl is True anyway, so forcing the mask to False elsewhere is safe.
        perf = (df["dlstcd"].eq(500) | df["dlstcd"].between(520, 584)).fillna(False)
        nasdaq = df["exchcd"].eq(3).fillna(False)
        fill = np.where(perf & nasdaq, -0.55, np.where(perf, -0.30, 0.0))
        dlret = dlret.where(~missing_dl, fill)
        logger.warning(
            "filled %d missing delisting returns (Shumway convention: "
            "-55%% NASDAQ perf, -30%% NYSE/AMEX perf, 0 otherwise)",
            int(missing_dl.sum()),
        )
    # Hygiene (audit H1): CRSP encodes some missingness as sentinel numerics and can
    # carry a stray impossible return; the paper-grade panel must guard like the EODHD
    # one does. Coerce ret/dlret < -100% to NaN BEFORE compounding, then null any final
    # total outside [RET_FLOOR, RET_CAP]. Counts are surfaced by the build script.
    ret = df["ret"].where(df["ret"] >= RET_FLOOR)
    dlret = dlret.where(dlret >= RET_FLOOR)
    total = (1 + ret.fillna(0.0)) * (1 + dlret.fillna(0.0)) - 1
    total = total.where(~(ret.isna() & dlret.isna()))
    n_impossible = int(((total < RET_FLOOR) | (total > RET_CAP)).sum())
    if n_impossible:
        logger.warning("nulled %d impossible CRSP total returns (outside [%s, %s])",
                       n_impossible, RET_FLOOR, RET_CAP)
    total = total.where((total >= RET_FLOOR) & (total <= RET_CAP))
    df["total_ret"] = total

    df["price"] = df["prc"].abs()  # negative prc = bid/ask midpoint flag
    df["daily_dollar_vol"] = df["price"] * df["vol"].fillna(0.0) * 100.0 / 21.0
    df["sym"] = df["permno"].astype(int).astype(str)

    # A permno can hit duplicate (month, permno) rows via msenames overlaps —
    # keep the last observation.
    df = df.sort_values("date").drop_duplicates(["month", "sym"], keep="last")

    monthly_ret = df.pivot(index="month", columns="sym", values="total_ret").sort_index()
    month_end_price = df.pivot(index="month", columns="sym", values="price").reindex(
        monthly_ret.index
    )
    monthly_dollar_vol = df.pivot(
        index="month", columns="sym", values="daily_dollar_vol"
    ).reindex(monthly_ret.index)

    delist_month = {
        sym: monthly_ret[sym].last_valid_index() for sym in monthly_ret.columns
    }
    return Panel(
        monthly_ret=monthly_ret,
        month_end_price=month_end_price,
        monthly_dollar_vol=monthly_dollar_vol,
        delist_month=delist_month,
    )
