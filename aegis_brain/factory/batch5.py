"""Factory batch 5 — winner-picking interactions, streaks, and exits-side
inputs (frozen list in docs/STRATEGY_FACTORY.md BEFORE any scan runs).

Theme: second-generation candidates — interactions of information sources that
individually showed real IC but failed alone, plus quality-trend and
persistence signals the batch-2 level sorts didn't cover. All computable from
data on disk; PIT rules: annual FundStore (datadate+6m), QuarterlyStore (rdq),
insider/SI/revisions at filing/report month-end.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.fundamentals import FundStore
from aegis_brain.factory.quarterly import QuarterlyStore
from aegis_brain.factory.signals import FactorySignal

RAW = MODULE_ROOT / "data" / "wrds_raw"
DATA = MODULE_ROOT / "data"


def _mom_12_1(panel: Panel) -> pd.DataFrame:
    ret = panel.monthly_ret
    return np.expm1(np.log1p(ret).shift(2).rolling(11, min_periods=8).sum())


def _z(df: pd.DataFrame) -> pd.DataFrame:
    return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1), axis=0)


def _monthly_event_frame(panel: Panel, df: pd.DataFrame, date_col: str,
                         val_col: str, window_months: int) -> pd.DataFrame:
    """Sum of val_col per permno over a trailing window of months (event data
    stamped to the month-end of date_col; PIT — uses filing/report dates)."""
    d = df.copy()
    d["m"] = pd.to_datetime(d[date_col]).dt.to_period("M").dt.to_timestamp("M")
    d["sym"] = d["permno"].astype("Int64").astype(str)
    wide = (d.pivot_table(index="m", columns="sym", values=val_col, aggfunc="sum")
            .reindex(panel.monthly_ret.index).fillna(0.0)
            .reindex(columns=panel.monthly_ret.columns).fillna(0.0))
    return wide.rolling(window_months, min_periods=1).sum()


def _insider_cluster(panel: Panel) -> pd.DataFrame:
    """# DISTINCT opportunistic insider buyers, trailing 3 months. 0 -> NaN
    (signal is defined only where somebody bought — the cross-section is
    buyers ranked by breadth, not everyone)."""
    ip = pd.read_parquet(DATA / "insider_panel.parquet",
                         columns=["permno", "filing_date", "rptowner_cik",
                                  "is_opportunistic", "value"])
    ip = ip[(ip["is_opportunistic"] == True) & ip["permno"].notna()  # noqa: E712
            & (ip["value"] > 0)].copy()
    ip["m"] = pd.to_datetime(ip["filing_date"]).dt.to_period("M").dt.to_timestamp("M")
    ip["sym"] = ip["permno"].astype("Int64").astype(str)
    per = (ip.groupby(["m", "sym"])["rptowner_cik"].nunique().rename("n").reset_index())
    wide = (per.pivot_table(index="m", columns="sym", values="n", aggfunc="last")
            .reindex(panel.monthly_ret.index).fillna(0.0)
            .reindex(columns=panel.monthly_ret.columns).fillna(0.0))
    cnt = wide.rolling(3, min_periods=1).sum()
    return cnt.where(cnt > 0)


def _si_ratio(panel: Panel, store: FundStore) -> pd.DataFrame:
    """Short interest / shares outstanding, PIT (SI datadate month + 1)."""
    si = pd.read_parquet(RAW / "short_interest.parquet")
    link = pd.read_parquet(RAW / "ccm_link.parquet").dropna(subset=["permno", "gvkey"])
    link["gvkey"] = link["gvkey"].astype(str).str.strip()
    link["sym"] = link["permno"].astype("Int64").astype(str)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"]).fillna(pd.Timestamp("2262-01-01"))
    si["gvkey"] = si["gvkey"].astype(str).str.strip()
    si["datadate"] = pd.to_datetime(si["datadate"])
    m = si.merge(link, on="gvkey")
    m = m[(m["datadate"] >= m["linkdt"]) & (m["datadate"] <= m["linkenddt"])]
    m["avail"] = (m["datadate"] + pd.DateOffset(months=1)).dt.to_period("M").dt.to_timestamp("M")
    wide = (m.pivot_table(index="avail", columns="sym", values="shortintadj", aggfunc="last")
            .reindex(panel.monthly_ret.index).ffill(limit=2)
            .reindex(columns=panel.monthly_ret.columns))
    csho = pd.read_parquet(RAW / "comp_funda.parquet", columns=["gvkey", "datadate", "csho"])
    csho["gvkey"] = csho["gvkey"].astype(str).str.strip()
    csho["datadate"] = pd.to_datetime(csho["datadate"])
    cm = csho.merge(link, on="gvkey")
    cm = cm[(cm["datadate"] >= cm["linkdt"]) & (cm["datadate"] <= cm["linkenddt"])]
    cm["avail"] = (cm["datadate"] + pd.DateOffset(months=6)).dt.to_period("M").dt.to_timestamp("M")
    sh = (cm.pivot_table(index="avail", columns="sym", values="csho", aggfunc="last")
          .reindex(panel.monthly_ret.index).ffill(limit=18)
          .reindex(columns=panel.monthly_ret.columns))
    return wide / (sh * 1e3).where(sh > 0)  # shortint shares / (csho millions -> thousands)


def _sue_streak(panel: Panel) -> pd.DataFrame:
    """# consecutive positive analyst-SUE quarters ending at the latest report."""
    su = pd.read_parquet(DATA / "sue_events.parquet",
                         columns=["permno", "rdq", "sue_analyst"])
    su = su.dropna(subset=["permno", "rdq", "sue_analyst"]).copy()
    su = su.sort_values(["permno", "rdq"])
    pos = su["sue_analyst"] > 0
    grp = (~pos).groupby(su["permno"]).cumsum()
    su["streak"] = pos.groupby([su["permno"], grp]).cumsum()
    su["m"] = pd.to_datetime(su["rdq"]).dt.to_period("M").dt.to_timestamp("M")
    su["sym"] = su["permno"].astype("Int64").astype(str)
    wide = (su.pivot_table(index="m", columns="sym", values="streak", aggfunc="last")
            .reindex(panel.monthly_ret.index).ffill(limit=4)
            .reindex(columns=panel.monthly_ret.columns))
    return wide


def _dtc(panel: Panel, store: FundStore) -> pd.DataFrame:
    """Days-to-cover: shortint / avg daily share volume (msf vol / 21)."""
    msf = pd.read_parquet(RAW / "crsp_msf.parquet", columns=["permno", "date", "vol"])
    msf["m"] = pd.to_datetime(msf["date"]).dt.to_period("M").dt.to_timestamp("M")
    msf["sym"] = msf["permno"].astype("Int64").astype(str)
    vol = (msf.pivot_table(index="m", columns="sym", values="vol", aggfunc="last")
           .reindex(panel.monthly_ret.index)
           .reindex(columns=panel.monthly_ret.columns))
    adv = (vol * 100 / 21).rolling(3, min_periods=1).mean()  # msf vol in 100s
    si = _si_ratio_raw_shares(panel)
    return si / adv.where(adv > 0)


_SI_CACHE: dict = {}


def _si_ratio_raw_shares(panel: Panel) -> pd.DataFrame:
    if "raw" in _SI_CACHE:
        return _SI_CACHE["raw"]
    si = pd.read_parquet(RAW / "short_interest.parquet")
    link = pd.read_parquet(RAW / "ccm_link.parquet").dropna(subset=["permno", "gvkey"])
    link["gvkey"] = link["gvkey"].astype(str).str.strip()
    link["sym"] = link["permno"].astype("Int64").astype(str)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"]).fillna(pd.Timestamp("2262-01-01"))
    si["gvkey"] = si["gvkey"].astype(str).str.strip()
    si["datadate"] = pd.to_datetime(si["datadate"])
    m = si.merge(link, on="gvkey")
    m = m[(m["datadate"] >= m["linkdt"]) & (m["datadate"] <= m["linkenddt"])]
    m["avail"] = (m["datadate"] + pd.DateOffset(months=1)).dt.to_period("M").dt.to_timestamp("M")
    out = (m.pivot_table(index="avail", columns="sym", values="shortintadj", aggfunc="last")
           .reindex(panel.monthly_ret.index).ffill(limit=2)
           .reindex(columns=panel.monthly_ret.columns))
    _SI_CACHE["raw"] = out
    return out


def _cusip_sym(panel: Panel) -> pd.DataFrame:
    """8-digit CUSIP -> sym via CRSP stocknames (date-agnostic unique-ever)."""
    sn = pd.read_parquet(RAW / "crsp_stocknames.parquet", columns=["permno", "ncusip"])
    sn = sn.dropna().copy()
    sn["c8"] = sn["ncusip"].astype(str).str.upper().str[:8]
    sn["sym"] = sn["permno"].astype(int).astype(str)
    per = sn.groupby("c8")["sym"].nunique()
    return (sn[sn["c8"].isin(per[per == 1].index)]
            [["c8", "sym"]].drop_duplicates())


def _inst_flows(panel: Panel) -> pd.DataFrame:
    """[quarter-month x sym] net institutional share change from 13F aggregates."""
    own = pd.read_parquet(RAW / "tr13f_ownership.parquet")
    own["c8"] = own["cusip"].astype(str).str.upper().str[:8]
    link = _cusip_sym(panel)
    m = own.merge(link, on="c8")
    m["fdate"] = pd.to_datetime(m["fdate"])
    # 13F filings public within 45 days: available 2 months after quarter end
    m["avail"] = (m["fdate"] + pd.DateOffset(months=2)).dt.to_period("M").dt.to_timestamp("M")
    sh = (m.pivot_table(index="avail", columns="sym", values="inst_shares", aggfunc="last"))
    return sh.diff()


def _inst_persist(panel: Panel) -> pd.DataFrame:
    """# consecutive quarters of net institutional BUYING (Dasgupta-Prat-
    Verardo 2011: persistent buying underperforms long-horizon -> direction -1)."""
    d = _inst_flows(panel)
    pos = d > 0
    grp = (~pos).cumsum()
    streak = pos.astype(float).copy()
    for col in streak.columns:
        streak[col] = pos[col].groupby(grp[col]).cumsum()
    streak = streak.where(d.notna())
    return (streak.reindex(panel.monthly_ret.index).ffill(limit=3)
            .reindex(columns=panel.monthly_ret.columns))


def _own_dur_t10(panel: Panel) -> pd.DataFrame:
    """Top-10-holdings ownership-duration PROXY (Cremers-Pareek 2016 variant):
    mean # consecutive quarters each current top-10 manager has held the name
    in its top 10. Coarser than true duration (top-10 subset only) — declared
    as a proxy in the freeze doc."""
    t10 = pd.read_parquet(RAW / "tr13f_top10.parquet", columns=["fdate", "mgrno", "cusip"])
    t10["c8"] = t10["cusip"].astype(str).str.upper().str[:8]
    link = _cusip_sym(panel)
    t10 = t10.merge(link, on="c8")
    t10["fdate"] = pd.to_datetime(t10["fdate"])
    t10 = t10.sort_values("fdate")
    qs = {d: i for i, d in enumerate(sorted(t10["fdate"].unique()))}
    t10["qi"] = t10["fdate"].map(qs)
    # holding streak per (mgrno, sym): consecutive quarter-indices present
    t10 = t10.drop_duplicates(["mgrno", "sym", "qi"]).sort_values(["mgrno", "sym", "qi"])
    g = t10.groupby(["mgrno", "sym"])
    new_run = g["qi"].diff().ne(1)
    t10["run"] = new_run.groupby([t10["mgrno"], t10["sym"]]).cumsum()
    t10["streak"] = t10.groupby(["mgrno", "sym", "run"]).cumcount() + 1
    agg = t10.groupby(["fdate", "sym"])["streak"].mean().reset_index()
    agg["avail"] = (agg["fdate"] + pd.DateOffset(months=2)).dt.to_period("M").dt.to_timestamp("M")
    wide = agg.pivot_table(index="avail", columns="sym", values="streak", aggfunc="last")
    return (wide.reindex(panel.monthly_ret.index).ffill(limit=3)
            .reindex(columns=panel.monthly_ret.columns))


def _dnoa(panel: Panel) -> pd.DataFrame:
    """Change in net operating assets / assets (bloated NOA -> low returns;
    Hirshleifer et al. 2004 lineage, computable from existing BS items)."""
    f = pd.read_parquet(RAW / "comp_funda.parquet",
                        columns=["gvkey", "datadate", "at", "che", "lt",
                                 "dlc", "dltt"])
    f = f.dropna(subset=["gvkey", "datadate", "at"]).copy()
    f["gvkey"] = f["gvkey"].astype(str).str.strip()
    f["datadate"] = pd.to_datetime(f["datadate"])
    f = f.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"])
    noa = (f["at"] - f["che"].fillna(0)) - \
          (f["lt"].fillna(0) - f["dlc"].fillna(0) - f["dltt"].fillna(0))
    g = f.groupby("gvkey", sort=False)
    f["dnoa"] = (noa - noa.groupby(f["gvkey"]).shift(1)) / g["at"].shift(1)
    lo, hi = f["dnoa"].quantile([0.005, 0.995])
    f["dnoa"] = f["dnoa"].clip(lo, hi)
    link = pd.read_parquet(RAW / "ccm_link.parquet").dropna(subset=["permno", "gvkey"])
    link["gvkey"] = link["gvkey"].astype(str).str.strip()
    link["sym"] = link["permno"].astype("Int64").astype(str)
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"]).fillna(pd.Timestamp("2262-01-01"))
    m = f.merge(link, on="gvkey")
    m = m[(m["datadate"] >= m["linkdt"]) & (m["datadate"] <= m["linkenddt"])]
    m["avail"] = (m["datadate"] + pd.DateOffset(months=6)).dt.to_period("M").dt.to_timestamp("M")
    wide = m.pivot_table(index="avail", columns="sym", values="dnoa", aggfunc="last")
    return (wide.reindex(panel.monthly_ret.index).ffill(limit=18)
            .reindex(columns=panel.monthly_ret.columns))


def build_batch5(panel: Panel, store: FundStore, qstore: QuarterlyStore
                 ) -> list[FactorySignal]:
    mom = _mom_12_1(panel)
    gp = store.get("gross_prof")
    rev = pd.read_parquet(DATA / "revision_panel.parquet")
    rev["sym"] = rev["permno"].astype("Int64").astype(str)
    rev_w = (rev.pivot_table(index="month", columns="sym", values="revision_score",
                             aggfunc="last")
             .reindex(panel.monthly_ret.index).ffill(limit=2)
             .reindex(columns=panel.monthly_ret.columns))

    def qual_mom(p: Panel) -> pd.DataFrame:
        top_half = gp.ge(gp.median(axis=1), axis=0)
        return mom.where(top_half)

    def gp_mom(p: Panel) -> pd.DataFrame:
        return gp - gp.shift(12)

    def rev_conf(p: Panel) -> pd.DataFrame:
        zr, zm = _z(rev_w), _z(mom)
        both = (zr > 0) & (zm > 0)
        return (zr + zm).where(both)

    def insider_si(p: Panel) -> pd.DataFrame:
        cluster = _insider_cluster(p)
        sir = _si_ratio(p, store)
        high_si = sir.ge(sir.quantile(0.7, axis=1), axis=0)
        return cluster.where(high_si)

    def defensive(p: Panel) -> pd.DataFrame:
        da = pd.read_parquet(RAW / "dsf_monthly_agg.parquet")
        da["sym"] = da["permno"].astype("Int64").astype(str)
        def wide(col):
            return (da.pivot_table(index="month", columns="sym", values=col,
                                   aggfunc="last")
                    .reindex(p.monthly_ret.index)
                    .reindex(columns=p.monthly_ret.columns))
        mx, vd = wide("max_dret"), wide("vol_d")
        px = p.month_end_price.abs()
        return _z(-mx) + _z(-vd) + _z(np.log(px.where(px > 0)))

    return [
        FactorySignal("qual_mom", "Momentum restricted to high-profitability "
                      "names — quality screens out momentum crashes "
                      "(Novy-Marx quality-momentum interaction).", qual_mom, +1),
        FactorySignal("earn_stab", "Low 5y earnings volatility = durable "
                      "franchise; the stability leg of quality "
                      "(earnings-smoothness literature).",
                      lambda p: qstore.get("earn_stab"), +1),
        FactorySignal("gp_mom", "Year-over-year IMPROVEMENT in gross "
                      "profitability/assets — fundamental momentum "
                      "(Novy-Marx 2015).", gp_mom, +1),
        FactorySignal("roa_mom", "Quarterly ROA vs 4 quarters prior — the "
                      "faster fundamental-momentum clock (rdq-anchored PIT).",
                      lambda p: qstore.get("roa_mom"), +1),
        FactorySignal("sue_streak", "Consecutive positive analyst-surprise "
                      "quarters — earnings streaks command drift beyond "
                      "single-quarter SUE (Loh-Warachka 2012).", _sue_streak, +1),
        FactorySignal("insider_cluster", "# distinct opportunistic insider "
                      "buyers, 3mo — consensus among informed insiders beats "
                      "a lone buy (cluster-buy literature).",
                      _insider_cluster, +1),
        FactorySignal("insider_si", "Opportunistic insider clusters INSIDE "
                      "the top-30% short-interest names — informed "
                      "disagreement resolves toward insiders.", insider_si, +1),
        FactorySignal("rev_conf", "Analyst-revision z + momentum z where BOTH "
                      "positive — fundamental confirmation filters price-only "
                      "momentum.", rev_conf, +1),
        FactorySignal("dtc_low", "Days-to-cover (SI / ADV): crowded shorts "
                      "underperform; long the UNcrowded (Hong et al.).",
                      lambda p: _dtc(p, store), -1),
        FactorySignal("defensive", "Lottery-avoidance composite: low MAX + "
                      "low daily vol + high price (Bali-Cakici-Whitelaw "
                      "composite of batch-1/3a defensive directions).",
                      defensive, +1),
        FactorySignal("earn_accel", "CHANGE in yoy EPS growth (second "
                      "derivative), price-scaled — market extrapolates growth "
                      "levels, underreacts to growth changes "
                      "(He-Narayanamoorthy 2020).",
                      lambda p: qstore.get("earn_accel"), +1),
        FactorySignal("ea_shift", "Announcement-date advance vs same quarter "
                      "last year (rdq-only construction) — advancers carry "
                      "good news (Johnson-So 2018).",
                      lambda p: qstore.get("ea_shift"), +1),
        FactorySignal("inst_persist_low", "Consecutive quarters of net 13F "
                      "buying — persistent institutional herding reverses at "
                      "long horizons; long the persistently-SOLD "
                      "(Dasgupta-Prat-Verardo 2011).", _inst_persist, -1),
        FactorySignal("own_dur_t10", "Ownership-duration PROXY: mean streak "
                      "of quarters current top-10 managers have held the name "
                      "— patient money marks durable winners (Cremers-Pareek "
                      "2016, top-10 variant).", _own_dur_t10, +1),
        FactorySignal("dnoa_low", "Change in net operating assets / assets — "
                      "balance-sheet bloat predicts low returns (Hirshleifer "
                      "et al. 2004), distinct component from total accruals.",
                      _dnoa, -1),
    ]
