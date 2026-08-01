"""TRIAL-ABIO-KIRK — abnormal institutional ownership. Spec frozen 2026-08-01
(TRIALS/TRIAL-ABIO-KIRK.md, module commit 66add9e, BEFORE this file existed).

Three arms, each a counted candidate (164-166):

  io_level  io = inst_shares / (shrout * 1000)                       direction +1
  io_chg    io_q - io_{q-1}, same cusip                              direction +1
  io_abn    residual of a per-quarter cross-sectional OLS of io on
            five frozen characteristics                              direction +1

Nothing here is tunable. The lag, the winsorisation, the characteristic set and
the link rule are all frozen in the registration; this module is the mechanical
implementation of that text and nothing else.

DISCLOSED REPAIRS (found before the run, no result seen at the time, recorded in
the trial doc):

  REPAIR 1 — table split by era. The registration names
  `tr13f_ownership_ext` and quotes its row count (662,688, "1980+"). That table
  in fact holds 1980-03-31..2001-12-31 ONLY; the 2002-2025 continuation of the
  identical WRDS s34 series lives in `tr13f_ownership` (1,169,903 rows). The
  explore window 2004-2018 has ZERO rows in the named table, so the frozen spec
  as literally written cannot produce a single scored month. We therefore read
  the UNION of the two files. They are the same series: identical dtypes,
  disjoint fdate ranges, no duplicate (fdate, cusip), 8-char cusips in both, and
  a continuous 2001Q4->2002Q1 boundary (11,374 -> 11,221 cusips, median
  inst_shares 858,827 -> 862,849, median n_inst 8 -> 9). No spec, lag,
  winsorisation, characteristic or bar is changed by this repair; in practice
  the explore window is served entirely by `tr13f_ownership`.

  REPAIR 2 — month-end matching. The spec says shrout is taken "at the month-end
  equal to fdate". CRSP month-end dates are TRADING-day month ends (2002-03-28)
  while 13F fdate is a CALENDAR quarter end (2002-03-31), so exact date equality
  matches almost nothing. We match on calendar year-month, which is what "the
  month-end equal to fdate" means. Same convention aligns fdate to the panel's
  (calendar) month-end index.

MECHANICAL PLUMBING (spec silent, precedent followed, disclosed):

  * A (fdate, permno) pair reachable from two different cusips is dropped on the
    same no-discretion principle the spec states for the cusip->permno
    direction. Measured, not assumed: see `link_diagnostics`.
  * Characteristics for the io_abn regression are read at the fdate month-end —
    the information contemporaneous with the holdings snapshot. The 60-day
    availability lag is applied to the RESIDUAL afterwards, so the score used at
    formation month m rests only on data at least 60 days old.
  * "Months since first CRSP obs" is min(namedt) per permno from
    crsp_stocknames, i.e. the security's first CRSP name record — the full CRSP
    history, not the 2002+ panel window (which would truncate every incumbent to
    the same age and destroy the regressor).
  * The availability rule is implemented as a forward-fill from each quarter's
    first eligible formation month, with NO staleness cap, because the frozen
    text says "the LATEST fdate with fdate + 60 calendar days <= m" and states
    no cap. Staleness is measured and reported rather than assumed harmless
    (`staleness_diagnostics`).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.signals.price_signals import momentum_12_1

logger = logging.getLogger(__name__)
RAW = MODULE_ROOT / "data" / "wrds_raw"

# ── FROZEN CONSTANTS (registration text; a change here is a new trial) ────────
LAG_DAYS = 60                      # fdate + 60 calendar days <= formation m
WINSOR_LO, WINSOR_HI = 0.01, 0.99  # per-quarter, 1%/99%
CHARS = ["log_mktcap", "mom_12_1", "log_dvol3m", "inv_price", "log_age"]
ARMS = ("io_level", "io_chg", "io_abn")
_FAR_FUTURE = pd.Timestamp("2262-01-01")


# ── ownership history ────────────────────────────────────────────────────────
def load_ownership() -> pd.DataFrame:
    """The 13F ownership series, both era files (REPAIR 1). Long: fdate, cusip,
    n_inst, inst_shares."""
    parts = []
    for f in ("tr13f_ownership_ext", "tr13f_ownership"):
        p = RAW / f"{f}.parquet"
        if not p.exists():                       # fail loud, never silently short
            raise FileNotFoundError(f"ownership file missing: {p}")
        parts.append(pd.read_parquet(p))
    own = pd.concat(parts, ignore_index=True)
    own["fdate"] = pd.to_datetime(own["fdate"])
    own["cusip"] = own["cusip"].astype(str).str.upper().str[:8]
    own = own.dropna(subset=["inst_shares"])
    own = own[own["inst_shares"] > 0]
    logger.info("ownership: %d rows, fdate %s..%s", len(own),
                own["fdate"].min().date(), own["fdate"].max().date())
    return own


def _stocknames() -> pd.DataFrame:
    nm = pd.read_parquet(RAW / "crsp_stocknames.parquet",
                         columns=["permno", "ncusip", "namedt", "nameenddt"])
    nm = nm[nm["ncusip"].notna()].copy()
    nm["cusip"] = nm["ncusip"].astype(str).str.upper().str[:8]
    nm["sym"] = nm["permno"].astype("Int64").astype(str)
    nm["namedt"] = pd.to_datetime(nm["namedt"])
    nm["nameenddt"] = pd.to_datetime(nm["nameenddt"]).fillna(_FAR_FUTURE)
    return nm[["sym", "cusip", "namedt", "nameenddt"]]


def link_ownership(own: pd.DataFrame,
                   names: pd.DataFrame | None = None) -> pd.DataFrame:
    """cusip -> permno on date-valid CRSP name records. AMBIGUOUS LINKS ARE
    DROPPED, never resolved (frozen: "no discretion") — in BOTH directions."""
    nm = _stocknames() if names is None else names
    m = own.merge(nm, on="cusip", how="inner")
    m = m[(m["fdate"] >= m["namedt"]) & (m["fdate"] <= m["nameenddt"])]

    # one cusip-quarter reaching >1 permno: drop the name-month (frozen rule)
    n_per = m.groupby(["fdate", "cusip"])["sym"].transform("nunique")
    m = m[n_per == 1]
    # the mirror case (two cusips -> one permno in the same quarter): same
    # principle, disclosed as plumbing
    n_rev = m.groupby(["fdate", "sym"])["cusip"].transform("nunique")
    m = m[n_rev == 1]
    return m[["fdate", "cusip", "sym", "n_inst", "inst_shares"]]


def link_diagnostics(own: pd.DataFrame) -> dict:
    """Counts for the write-up: how much the no-discretion rule actually drops."""
    nm = _stocknames()
    m = own.merge(nm, on="cusip", how="inner")
    m = m[(m["fdate"] >= m["namedt"]) & (m["fdate"] <= m["nameenddt"])]
    n_per = m.groupby(["fdate", "cusip"])["sym"].transform("nunique")
    amb_fwd = int((n_per > 1).sum())
    k = m[n_per == 1]
    n_rev = k.groupby(["fdate", "sym"])["cusip"].transform("nunique")
    return {
        "rows_in": int(len(own)),
        "rows_date_valid_linked": int(len(m)),
        "rows_dropped_ambiguous_cusip_to_permno": amb_fwd,
        "rows_dropped_ambiguous_permno_to_cusip": int((n_rev > 1).sum()),
        "rows_out": int((n_rev == 1).sum()),
    }


# ── shares outstanding and io ────────────────────────────────────────────────
def _shrout_by_month() -> pd.DataFrame:
    """Long: sym, ym (Period[M]), shrout (thousands of shares). REPAIR 2."""
    sh = pd.read_parquet(RAW / "crsp_msf_shrout.parquet")
    sh = sh.dropna(subset=["shrout"])
    sh = sh[sh["shrout"] > 0].copy()
    sh["sym"] = sh["permno"].astype("Int64").astype(str)
    sh["ym"] = pd.to_datetime(sh["date"]).dt.to_period("M")
    sh = sh.sort_values("date").drop_duplicates(["sym", "ym"], keep="last")
    return sh[["sym", "ym", "shrout"]]


def winsorise_by(s: pd.Series, groups: pd.Series) -> pd.Series:
    """Clip to the [1%, 99%] quantiles computed WITHIN each group (per quarter)."""
    lo = groups.map(s.groupby(groups).quantile(WINSOR_LO))
    hi = groups.map(s.groupby(groups).quantile(WINSOR_HI))
    return s.clip(lower=lo, upper=hi)


def build_io(own_linked: pd.DataFrame,
             shrout: pd.DataFrame | None = None) -> pd.DataFrame:
    """Long frame: fdate, sym, io (per-quarter winsorised), io_chg.

    io = inst_shares / (shrout * 1000); winsorised per quarter at 1/99 BEFORE
    any further step, so io_chg is a difference of winsorised levels (frozen
    ordering: "winsorised ... before any further step").
    """
    sh = _shrout_by_month() if shrout is None else shrout
    d = own_linked.copy()
    d["ym"] = d["fdate"].dt.to_period("M")
    d = d.merge(sh, on=["sym", "ym"], how="inner")
    d["io"] = d["inst_shares"] / (d["shrout"] * 1000.0)
    d = d[np.isfinite(d["io"])]
    d["io"] = winsorise_by(d["io"], d["fdate"])

    d = d.sort_values(["sym", "fdate"])
    d["io_chg"] = d.groupby("sym", sort=False)["io"].diff()
    return d[["fdate", "sym", "io", "io_chg"]]


# ── characteristics for the residual arm ─────────────────────────────────────
def build_characteristics(panel: Panel,
                          shrout: pd.DataFrame | None = None) -> pd.DataFrame:
    """Long frame: month (panel month-end), sym, + the five frozen regressors."""
    sh = _shrout_by_month() if shrout is None else shrout
    idx, cols = panel.monthly_ret.index, panel.monthly_ret.columns

    price = panel.month_end_price.abs()
    dvol3 = panel.monthly_dollar_vol.rolling(3, min_periods=3).mean()
    mom = momentum_12_1(panel)

    shr_wide = (sh.assign(m=sh["ym"].dt.to_timestamp("M"))
                .pivot_table(index="m", columns="sym", values="shrout",
                             aggfunc="last")
                .reindex(index=idx, columns=cols))
    mktcap = price * shr_wide * 1000.0

    nm = pd.read_parquet(RAW / "crsp_stocknames.parquet",
                         columns=["permno", "namedt"])
    nm["sym"] = nm["permno"].astype("Int64").astype(str)
    first = pd.to_datetime(nm.groupby("sym")["namedt"].min())
    first_ord = first.reindex(cols)
    age_months = pd.DataFrame(
        {c: (idx.year - first_ord[c].year) * 12 + (idx.month - first_ord[c].month)
         if pd.notna(first_ord.get(c)) else np.nan for c in cols}, index=idx)

    frames = {
        "log_mktcap": np.log(mktcap.where(mktcap > 0)),
        "mom_12_1": mom,
        "log_dvol3m": np.log(dvol3.where(dvol3 > 0)),
        "inv_price": 1.0 / price.where(price > 0),
        "log_age": np.log(age_months.where(age_months > 0)),
    }
    out = None
    for name, f in frames.items():
        s = f.stack().rename(name)
        s.index.names = ["month", "sym"]
        out = s.to_frame() if out is None else out.join(s, how="outer")
    return out.reset_index()


def residualise_per_quarter(df: pd.DataFrame) -> pd.Series:
    """Per-quarter cross-sectional OLS of io on the five (per-quarter
    winsorised) characteristics; returns the residual.

    Refit each quarter, with an intercept. Names with ANY missing regressor are
    dropped (frozen). Quarters are independent by construction — no pooling, no
    time-series information crosses a quarter boundary.
    """
    d = df.dropna(subset=["io", *CHARS]).copy()
    for c in CHARS:
        d[c] = winsorise_by(d[c], d["fdate"])

    resid = pd.Series(np.nan, index=d.index, dtype=float)
    for fdate, g in d.groupby("fdate", sort=True):
        if len(g) <= len(CHARS) + 1:
            continue
        X = np.column_stack([np.ones(len(g)), g[CHARS].to_numpy(float)])
        y = g["io"].to_numpy(float)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid.loc[g.index] = y - X @ beta
    return resid


# ── availability lag and panel alignment ─────────────────────────────────────
def first_available_month(fdate: pd.Timestamp,
                          months: pd.DatetimeIndex) -> pd.Timestamp | None:
    """Earliest formation month-end m in `months` with fdate + 60 days <= m.

    The frozen rule. A quarter filed 59 days before a month-end is NOT usable at
    that month-end; 60 days exactly IS.
    """
    ready = fdate + pd.Timedelta(days=LAG_DAYS)
    later = months[months >= ready]
    return later[0] if len(later) else None


def to_panel_frame(long: pd.DataFrame, value: str, panel: Panel) -> pd.DataFrame:
    """[month x sym] frame: value carried from the latest fdate whose 60-day lag
    has elapsed by the formation month-end."""
    idx, cols = panel.monthly_ret.index, panel.monthly_ret.columns
    d = long.dropna(subset=[value]).copy()
    avail = {f: first_available_month(f, idx) for f in d["fdate"].unique()}
    d["avail"] = d["fdate"].map(avail)
    d = d.dropna(subset=["avail"])
    wide = d.pivot_table(index="avail", columns="sym", values=value,
                         aggfunc="last")
    return (wide.reindex(idx.union(wide.index).sort_values())
            .ffill()                       # "the LATEST fdate" — no cap (frozen)
            .reindex(index=idx, columns=cols))


def staleness_diagnostics(long: pd.DataFrame, panel: Panel) -> dict:
    """How old is the quarter actually being used at each formation month?

    Reported so the uncapped forward-fill is MEASURED, not assumed harmless.
    Reported twice: over every panel column, and over the population the scan
    actually ranks (eligible AND inside the segment). The second is the one that
    bears on the result — a name that has dropped out of 13F entirely is
    normally also out of the liquid universe, so it is never ranked.
    """
    from aegis_brain.factory.explore import segment_mask

    idx = panel.monthly_ret.index
    d = long.dropna(subset=["io"]).copy()
    age = to_panel_frame(
        d.assign(fdate_ord=d["fdate"].map(lambda x: x.toordinal())),
        "fdate_ord", panel)
    month_ord = pd.Series([m.toordinal() for m in idx], index=idx)
    gap = (age.rsub(month_ord, axis=0)) / 30.44
    gap = gap.loc["2004-01-31":"2018-12-31"]

    def stats(g: pd.DataFrame) -> dict:
        s = g.stack().dropna()
        return {
            "n": int(len(s)),
            "median_months": round(float(s.median()), 2),
            "p95_months": round(float(s.quantile(0.95)), 2),
            "frac_older_than_6m": round(float((s > 6).mean()), 4),
            "frac_older_than_12m": round(float((s > 12).mean()), 4),
        }

    out = {"all_panel_columns": stats(gap)}
    elig = panel.eligible().loc[gap.index]
    for seg in ("largemid", "small"):
        mask = elig & segment_mask(panel, seg).loc[gap.index]
        out[f"ranked_{seg}"] = stats(gap.where(mask))
    return out


# ── the three arms ───────────────────────────────────────────────────────────
def build_abio_frames(panel: Panel) -> tuple[dict[str, pd.DataFrame], dict]:
    """{arm -> [month x sym] score frame}, plus a diagnostics dict."""
    own = load_ownership()
    diag = {"link": link_diagnostics(own)}
    linked = link_ownership(own)
    io = build_io(linked)

    chars = build_characteristics(panel)
    chars["fdate"] = chars["month"]
    merged = io.merge(chars.drop(columns=["month"]), on=["fdate", "sym"],
                      how="left")
    merged["io_abn"] = residualise_per_quarter(merged)

    diag["n_quarters"] = int(merged["fdate"].nunique())
    diag["n_rows_io"] = int(len(merged))
    diag["n_rows_io_abn"] = int(merged["io_abn"].notna().sum())
    diag["staleness"] = staleness_diagnostics(merged, panel)

    frames = {a: to_panel_frame(merged, "io" if a == "io_level" else a, panel)
              for a in ARMS}
    for a, f in frames.items():
        cov = f.loc["2004-01-31":"2018-12-31"].notna().sum(axis=1)
        diag[f"coverage_{a}"] = round(float(cov.mean()), 1)
        logger.info("%s: mean explore-window coverage %.0f names", a, cov.mean())
    return frames, diag
