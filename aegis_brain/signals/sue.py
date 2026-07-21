"""Earnings-surprise (PEAD / SUE) event signal — Phase 2 / L2 event feed.

Post-earnings-announcement drift (Ball & Brown 1968; Bernard & Thomas 1989,
*Journal of Accounting and Economics* 13(4): 305-340) is the most durable
accounting anomaly: firms that beat expectations keep drifting up for weeks
after the report. The tradeable primitive is the **standardized unexpected
earnings** (SUE) measured *at the announcement date* ``rdq``, which is the only
date the downstream backtest is allowed to key on.

We compute two flavours, both strictly point-in-time (they use ONLY data
observable at ``rdq``):

1. **Time-series SUE (Foster 1977), primary and self-contained in Compustat.**
   Per firm (``gvkey``) form the seasonal difference of basic EPS excluding
   extraordinary items::

       dEPS(t) = epspxq(t) - epspxq(t-4 quarters)      # same fiscal quarter, prior year

   and scale it by the rolling standard deviation of the trailing eight
   quarters of that difference (min six observations)::

       SUE_ts(t) = dEPS(t) / std_8q( dEPS )

   Each value is anchored to its quarter's ``rdq``. This needs nothing but
   Compustat ``comp_fundq`` and so is available for essentially every reported
   quarter.

2. **Analyst-based SUE (best-effort), from IBES.** Using the *pre-announcement*
   consensus::

       SUE_an = (actual - meanest) / |price|

   where ``actual`` is the realized quarterly EPS IBES records for the fiscal
   period, ``meanest`` is the consensus mean estimate from the LATEST IBES
   monthly snapshot (``statpers``) dated STRICTLY BEFORE ``rdq`` (no
   look-ahead), and ``price`` is the Compustat quarter-close ``prccq``. Where
   there is no clean IBES match, ``sue_analyst`` is ``NaN`` — never fabricated.

PIT / correctness rules honoured here
-------------------------------------
  * Never use a ``statpers`` snapshot dated ``>= rdq`` for the consensus.
  * ``rdq`` is the sole event/observability date the backtest keys on; rows with
    a missing/NaT ``rdq`` are dropped.
  * Restatement look-ahead caveat: we use the Compustat ``fundq`` row as-is,
    i.e. the (possibly later-restated) first-vintage value. A true first-report
    vintage would require the Compustat point-in-time ("preliminary") file. This
    is an accepted limitation of a first version and is documented, not hidden.

The IBES period match is by 8-digit CUSIP stem AND fiscal-period-end alignment
(both ``datadate`` and ``fpedats`` normalised to month-end absorbs the few-day
slack the task allows). CRSP ``permno`` is attached PIT via
``attach_permno_by_cusip`` (Compustat carries the 9-digit CUSIP; its 8-digit
stem is the join key).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.events.crsp_link import attach_permno_by_cusip

logger = logging.getLogger(__name__)

RAW = MODULE_ROOT / "data" / "wrds_raw"
OUT_PATH = MODULE_ROOT / "data" / "sue_events.parquet"

# IBES summary forecast-period-indicator codes for QUARTERLY periods.
_QUARTERLY_FPI = ("6", "7")

# Foster time-series SUE parameters.
_SEASONAL_LAG_Q = 4   # same fiscal quarter, one year prior
_VOL_WINDOW_Q = 8     # trailing quarters of dEPS for the scaling volatility
_VOL_MIN_Q = 6        # minimum non-NaN dEPS observations to form the volatility

# Final event-frame schema.
_COLUMNS = ["permno", "rdq", "sue_ts", "sue_analyst", "price", "numest"]


# --------------------------------------------------------------------------- #
# 1. Time-series SUE (Foster) — self-contained in Compustat                    #
# --------------------------------------------------------------------------- #
def time_series_sue(fundq: pd.DataFrame) -> pd.DataFrame:
    """Compute Foster (1977) time-series SUE per ``gvkey``.

    Expects a Compustat ``comp_fundq``-shaped frame with columns
    ``gvkey, datadate, fyearq, fqtr, epspxq`` (plus whatever else is carried
    through). Returns a copy of the input with two added columns:

      * ``deps``    — seasonal difference ``epspxq(t) - epspxq(t-4q)`` (prior-year
                      SAME fiscal quarter, matched on ``(gvkey, fyearq, fqtr)`` so
                      it is robust to missing/irregular quarters);
      * ``sue_ts``  — ``deps`` divided by the rolling std (ddof=1) of the trailing
                      eight quarters of ``deps`` within the firm (min six obs).

    Point-in-time by construction: the seasonal lag and the trailing volatility
    only ever reference the current and prior quarters, all observable by ``rdq``.
    """
    df = fundq.copy()
    for col in ("gvkey", "datadate", "fyearq", "fqtr", "epspxq"):
        if col not in df.columns:
            raise KeyError(f"time_series_sue: missing required column {col!r}")

    # Prior-year SAME-quarter EPS via a self-merge on the fiscal key. Shifting the
    # prior year's key forward by one year makes it join to the current row.
    prior = (
        df[["gvkey", "fyearq", "fqtr", "epspxq"]]
        .dropna(subset=["gvkey", "fyearq", "fqtr"])
        .drop_duplicates(["gvkey", "fyearq", "fqtr"], keep="last")
        .copy()
    )
    prior["fyearq"] = prior["fyearq"] + 1
    prior = prior.rename(columns={"epspxq": "_epspxq_ly"})
    df = df.merge(prior, on=["gvkey", "fyearq", "fqtr"], how="left")

    df["deps"] = df["epspxq"] - df["_epspxq_ly"]

    # Trailing-8-quarter volatility of dEPS, per firm, ordered by report period.
    df = df.sort_values(["gvkey", "datadate"], kind="mergesort")
    vol = df.groupby("gvkey")["deps"].transform(
        lambda s: s.rolling(_VOL_WINDOW_Q, min_periods=_VOL_MIN_Q).std()
    )
    # Zero (or absent) volatility cannot standardize -> leave SUE undefined.
    vol = vol.where(vol > 0)
    df["sue_ts"] = df["deps"] / vol
    return df.drop(columns=["_epspxq_ly"])


# --------------------------------------------------------------------------- #
# 2. Analyst-based SUE (best-effort) — IBES consensus strictly before rdq      #
# --------------------------------------------------------------------------- #
def analyst_sue(fundq: pd.DataFrame, ibes: pd.DataFrame) -> pd.DataFrame:
    """Best-effort analyst SUE per announcement, PIT-correct against IBES.

    For each Compustat announcement ``(gvkey, datadate, rdq, cusip, price)`` we
    find IBES *quarterly* rows (``fpi`` in {'6','7'}) whose 8-digit CUSIP stem
    matches and whose target period ``fpedats`` aligns with ``datadate`` (both
    normalised to month-end to absorb the few-day slack), keep only snapshots
    with ``statpers < rdq`` (strict — no look-ahead), take the consensus
    ``meanest`` / ``numest`` from the LATEST such ``statpers``, and form::

        sue_analyst = (actual - meanest) / |price|

    ``actual`` is IBES's realized EPS for that fiscal period (constant across a
    period's snapshots). Announcements with no clean match are simply absent from
    the result (the caller fills ``sue_analyst = NaN``).

    Returns a frame keyed by ``(gvkey, datadate)`` with columns
    ``[gvkey, datadate, sue_analyst, numest, meanest_used, actual]``.
    """
    out_cols = ["gvkey", "datadate", "sue_analyst", "numest", "meanest_used", "actual"]

    # --- Announcement side ---
    ann = fundq[["gvkey", "datadate", "rdq", "cusip", "prccq"]].copy()
    ann = ann.dropna(subset=["datadate", "rdq", "cusip"])
    ann["cusip8"] = ann["cusip"].astype(str).str.strip().str.upper().str[:8]
    ann["price"] = pd.to_numeric(ann["prccq"], errors="coerce")
    ann["pkey"] = pd.to_datetime(ann["datadate"]) + pd.offsets.MonthEnd(0)
    ann["_aid"] = np.arange(len(ann))

    # --- IBES quarterly side ---
    q = ibes[ibes["fpi"].astype(str).isin(_QUARTERLY_FPI)].copy()
    q = q.dropna(subset=["cusip", "fpedats", "statpers"])
    q["cusip8"] = q["cusip"].astype(str).str.strip().str.upper().str[:8]
    q["pkey"] = pd.to_datetime(q["fpedats"]) + pd.offsets.MonthEnd(0)
    q = q[["cusip8", "pkey", "statpers", "meanest", "numest", "actual"]]

    if ann.empty or q.empty:
        return pd.DataFrame(columns=out_cols)

    # Candidate snapshots for each announcement (same firm-period).
    m = ann[["_aid", "cusip8", "pkey", "rdq", "price"]].merge(
        q, on=["cusip8", "pkey"], how="inner"
    )
    # Strict PIT: consensus must be knowable strictly before the report date.
    m = m[m["statpers"] < m["rdq"]]
    if m.empty:
        return pd.DataFrame(columns=out_cols)

    # Latest pre-announcement snapshot per announcement.
    m = m.sort_values(["_aid", "statpers"], kind="mergesort")
    best = m.drop_duplicates("_aid", keep="last").copy()

    price_abs = best["price"].abs()
    best["sue_analyst"] = (best["actual"] - best["meanest"]) / price_abs.where(price_abs > 0)
    best = best.rename(columns={"meanest": "meanest_used"})

    res = best.merge(ann[["_aid", "gvkey", "datadate"]], on="_aid", how="left")
    return res[out_cols].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 3. Assemble the event frame                                                  #
# --------------------------------------------------------------------------- #
def build_sue_events(
    fundq: pd.DataFrame | None = None,
    ibes: pd.DataFrame | None = None,
    *,
    write: bool = True,
) -> pd.DataFrame:
    """Build the one-row-per-earnings-announcement SUE event frame.

    Reads ``comp_fundq`` and ``ibes_epsus`` from ``data/wrds_raw/`` (or accepts
    them directly for testing), computes both SUE flavours, attaches CRSP
    ``permno`` PIT by 8-digit CUSIP at ``rdq``, and returns a frame with columns::

        permno, rdq, sue_ts, sue_analyst, price, numest

    One row per Compustat announcement. Rows with a missing/NaT ``rdq`` are
    dropped (``rdq`` is the event date). When ``write`` is true the result is
    written to ``data/sue_events.parquet`` (git-ignored).
    """
    if fundq is None:
        fundq = pd.read_parquet(RAW / "comp_fundq.parquet")
    if ibes is None:
        ibes = pd.read_parquet(RAW / "ibes_epsus.parquet")

    base = fundq.copy()
    base["rdq"] = pd.to_datetime(base["rdq"], errors="coerce")
    base = base[base["rdq"].notna()].copy()  # rdq is the observability date

    ts = time_series_sue(base)
    an = analyst_sue(base, ibes)

    df = ts.merge(an[["gvkey", "datadate", "sue_analyst", "numest"]],
                  on="gvkey datadate".split(), how="left")

    df["price"] = pd.to_numeric(df["prccq"], errors="coerce")

    # Attach CRSP permno PIT at the announcement date (Compustat CUSIP is 9-digit;
    # the mapper uses the 8-digit stem).
    df, link_diag = attach_permno_by_cusip(df, cusip_col="cusip", date_col="rdq")
    logger.info("permno link: %s", link_diag)
    df.attrs["permno_link"] = link_diag

    out = df[_COLUMNS].reset_index(drop=True)

    if write:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(OUT_PATH, index=False)
        logger.info("wrote %d SUE events -> %s", len(out), OUT_PATH)

    return out
