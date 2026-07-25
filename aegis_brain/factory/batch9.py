"""Factory batch 9 — self-directed research round (frozen in
docs/STRATEGY_FACTORY.md BEFORE any scan; prior-check gate transcripts in
the freeze commit). Two decile signals; the announcement-premium flag trial
runs separately (TRIAL-BRAIN-012, binary signal -> flag harness).

industry_mom  — Moskowitz-Grinblatt 1999 industry momentum (2-digit SIC,
                date-valid via stocknames intervals). Prior-check: 0 hits.
                LOW prior declared (flat since ~2000 per Linnainmaa; kept
                as the subsumption baseline for conn_mom).
conn_mom      — Ali-Hirshleifer JFE 2020 shared-analyst connected momentum:
                coverage-weighted prior-month return of stocks sharing IBES
                analysts (pairs from ptgdet trailing 12m). Subsumes
                industry/customer momentum in the paper.
comp_issue_5y — Daniel-Titman 2006 composite share issuance: log ME growth
                minus cumulative log return over 60 months; long LOW
                issuers. Adjacent to shelf-class net_issuance (1y, b2) —
                provenance disclosed, distinct published construction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.batch5 import _cusip_sym
from aegis_brain.factory.batch7 import _annual_wide
from aegis_brain.factory.signals import FactorySignal

RAW = MODULE_ROOT / "data" / "wrds_raw"
MIN_IND_NAMES = 5


def _sic2_map(panel: Panel) -> pd.DataFrame:
    """[month x sym] 2-digit SIC, date-valid at each month (stocknames intervals)."""
    sn = pd.read_parquet(RAW / "crsp_stocknames.parquet",
                         columns=["permno", "namedt", "nameenddt", "siccd"])
    sn = sn.dropna(subset=["siccd"]).copy()
    sn["sym"] = sn["permno"].astype(int).astype(str)
    sn["namedt"] = pd.to_datetime(sn["namedt"])
    sn["nameenddt"] = pd.to_datetime(sn["nameenddt"]).fillna(pd.Timestamp("2262-01-01"))
    sn["sic2"] = (sn["siccd"].astype(int) // 100).astype(float)
    sn = sn[sn["sym"].isin(panel.monthly_ret.columns)]
    out = pd.DataFrame(np.nan, index=panel.monthly_ret.index,
                       columns=panel.monthly_ret.columns)
    for sym, g in sn.groupby("sym"):
        for r in g.itertuples():
            lo = out.index.searchsorted(r.namedt)
            hi = out.index.searchsorted(r.nameenddt, side="right")
            if hi > lo:
                out.iloc[lo:hi, out.columns.get_loc(sym)] = r.sic2
    return out


def _conn_mom(panel: Panel) -> pd.DataFrame:
    """[month x sym] shared-analyst connected prior-month return.
    Pairs: analyst (amaskcd) x stock, active if a target price was announced
    in the trailing 12 months (ptgdet detail; TP coverage as the proxy for
    coverage — disclosed). Weight_ij = # shared analysts; signal_i =
    sum_j w_ij * r_j(m-1) / sum_j w_ij, j != i."""
    pt = pd.read_parquet(RAW / "ibes_ptgdet.parquet",
                         columns=["cusip", "amaskcd", "anndats"])
    pt = pt.dropna(subset=["cusip", "amaskcd", "anndats"]).copy()
    pt["c8"] = pt["cusip"].astype(str).str.upper().str[:8]
    link = _cusip_sym(panel)
    pt = pt.merge(link, on="c8")
    pt = pt[pt["sym"].isin(panel.monthly_ret.columns)]
    pt["m"] = pd.to_datetime(pt["anndats"]).dt.to_period("M").dt.to_timestamp("M")
    pt["aid"] = pt["amaskcd"].astype("category").cat.codes
    months = panel.monthly_ret.index
    cols = panel.monthly_ret.columns
    col_ix = {s: i for i, s in enumerate(cols)}
    n_an = int(pt["aid"].max()) + 1
    pairs = pt[["m", "aid", "sym"]].drop_duplicates()

    r_prev = panel.monthly_ret.shift(1)
    out = pd.DataFrame(np.nan, index=months, columns=cols)
    for m in months:
        win = pairs[(pairs["m"] <= m) & (pairs["m"] > m - pd.DateOffset(months=12))]
        if len(win) < 500:
            continue
        w = win.drop_duplicates(["aid", "sym"])
        rows = w["aid"].to_numpy()
        cix = np.array([col_ix[s] for s in w["sym"]])
        A = sparse.csr_matrix((np.ones(len(w)), (rows, cix)),
                              shape=(n_an, len(cols)))
        S = (A.T @ A).tolil()
        S.setdiag(0)
        S = S.tocsr()
        rp = r_prev.loc[m].to_numpy(dtype=float)
        rp_f = np.nan_to_num(rp, nan=0.0)
        notna = (~np.isnan(rp)).astype(float)
        num = S @ rp_f
        den = S @ notna
        with np.errstate(invalid="ignore", divide="ignore"):
            sig = np.where(den > 0, num / den, np.nan)
        out.loc[m] = sig
    return out


def build_batch9(panel: Panel) -> list[FactorySignal]:
    r = panel.monthly_ret
    cum6 = (1 + r).rolling(6, min_periods=5).apply(np.prod, raw=True) - 1
    sic2 = _sic2_map(panel)

    ind_rows = []
    for m in r.index:
        s, c = sic2.loc[m], cum6.loc[m]
        df = pd.DataFrame({"sic": s, "c": c}).dropna()
        g = df.groupby("sic")["c"].agg(["mean", "count"])
        g = g[g["count"] >= MIN_IND_NAMES]
        ind_rows.append(df["sic"].map(g["mean"]).reindex(r.columns))
    ind_mom = pd.DataFrame(ind_rows, index=r.index)

    base = pd.read_parquet(RAW / "comp_funda.parquet",
                           columns=["gvkey", "datadate", "csho"])
    base["gvkey"] = base["gvkey"].astype(str).str.strip()
    base["datadate"] = pd.to_datetime(base["datadate"])
    base = base.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"])
    csho_w = _annual_wide(panel, base.dropna(subset=["csho"]), "csho")
    me = (csho_w * panel.month_end_price.abs()).where(csho_w > 0)
    logret = np.log1p(r)
    iota = (np.log(me / me.shift(60))
            - logret.rolling(60, min_periods=54).sum())

    conn = _conn_mom(panel)

    return [
        FactorySignal("industry_mom", "Industry momentum (Moskowitz-Grinblatt "
                      "1999): stock inherits its 2-digit-SIC industry's "
                      "trailing 6m EW return; horizon 1-6mo, turnover MED; "
                      "LOW prior (flat since ~2000) — subsumption baseline.",
                      lambda p: ind_mom, +1),
        FactorySignal("conn_mom", "Shared-analyst connected momentum "
                      "(Ali-Hirshleifer JFE 2020): coverage-weighted "
                      "prior-month return of analyst-connected stocks; "
                      "horizon 1-3mo, turnover HIGH (declared cost risk).",
                      lambda p: conn, +1),
        FactorySignal("comp_issue_5y", "Composite share issuance (Daniel-"
                      "Titman 2006): log ME growth minus 60m cumulative log "
                      "return; issuers underperform, long LOW; horizon "
                      "annual+, turnover LOW; live from ~2007 (60m ME "
                      "warmup, disclosed).", lambda p: iota, -1),
    ]
