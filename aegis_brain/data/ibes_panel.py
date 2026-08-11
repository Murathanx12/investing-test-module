"""IBES consensus panels, gridded to (month x permno) point-in-time.

Registered by TRIALS/PREREG_ANALYST_IBES_1.md. Read that first — it explains
which questions this data is allowed to answer and which were already killed.

THREE DEFECTS THIS MODULE EXISTS TO AVOID, all of them previously real here:

1. **The adjusted-file look-ahead.** `ibes.ptgdet` carries values restated to
   the DOWNLOAD-date share basis. Ratioed against nominal CRSP `prc` it
   produced a long book at tgt/price ~= 0.02 and a t of 7.12, and both runs
   were voided (`VOID-TGT-UPSIDE-B3B-B3C`, 2026-07-22). This module reads the
   UNADJUSTED summary files (`ptgsumu`, `statsumu_epsus`) only.

2. **The split-as-revision artefact.** Unadjusted targets are stated on the
   share basis of their own statpers. Differencing across a 10:1 split prints
   a -90% "revision" that is pure arithmetic. CRSP `month_end_price` in this
   panel is RAW, so the split factor is recoverable exactly:

       f_t = price_{t-1} * (1 + ret_t) / price_t

   ~1 in a normal month, ~k on a k:1 split. The cumulative product converts
   every past target onto the current share basis BEFORE any difference is
   taken. Levels need no such correction — target and price are both raw and
   same-dated, which is the whole reason to prefer the unadjusted file.

3. **The link that silently matches nothing.** `ibcrsphist` carries sdate/edate
   validity windows and a link `score`. A merge that ignores them, or one that
   drops 90% of rows without saying so, produces a thin panel that still looks
   like a panel. Coverage is measured and returned, and a build that matches
   too little raises rather than returning a sparse frame.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT

logger = logging.getLogger(__name__)

IBES_RAW = MODULE_ROOT / "data" / "wrds_raw" / "ibes"

#: Below this the panel is too thin to build a book on, and saying so is the
#: point — a silently sparse signal frame is the house failure mode.
MIN_LINK_MATCH_RATE = 0.60
MIN_NAMES_PER_MONTH = 50

#: A month whose implied factor sits outside this band is treated as a share
#: -basis change rather than a price move. Ordinary dividends push the factor a
#: few percent above 1; nothing short of a split reaches 1.3.
SPLIT_LO, SPLIT_HI = 1.0 / 1.3, 1.3


class IbesDataError(RuntimeError):
    """The IBES layer cannot produce a trustworthy panel. Never degrade quietly."""


@dataclass
class Coverage:
    table: str
    rows_in: int
    rows_linked: int
    match_rate: float
    months: int
    mean_names_per_month: float

    def as_dict(self) -> dict:
        return {
            "table": self.table, "rows_in": self.rows_in,
            "rows_linked": self.rows_linked,
            "match_rate": round(self.match_rate, 4),
            "months": self.months,
            "mean_names_per_month": round(self.mean_names_per_month, 1),
        }


def _require(name: str) -> pd.DataFrame:
    p = IBES_RAW / f"{name}.parquet"
    if not p.exists():
        raise IbesDataError(
            f"{p} is missing — run `python -m scripts.fetch_wrds_ibes` on the "
            f"WRDS-routable network. This is an absent input, NOT an empty one.")
    return pd.read_parquet(p)


@lru_cache(maxsize=1)
def _link() -> pd.DataFrame:
    """IBES ticker -> CRSP permno, with the validity window kept."""
    lk = _require("ibcrsphist").copy()
    lk["sdate"] = pd.to_datetime(lk["sdate"])
    lk["edate"] = pd.to_datetime(lk["edate"])
    # A link row with no permno is a link to nothing. Drop it explicitly and
    # count it, rather than letting a NA propagate into a column label.
    n_all = len(lk)
    lk = lk[lk["permno"].notna()]
    if len(lk) < n_all:
        logger.info("ibes link: dropped %d row(s) with no permno", n_all - len(lk))
    lk["permno"] = lk["permno"].astype("int64")
    # `score` is WRDS's link quality, 1 = best. 1-3 are the accepted grades in
    # the WRDS research guide; 4+ are CUSIP-only guesses.
    before = len(lk)
    lk = lk[lk["score"].astype(float) <= 3]
    logger.info("ibes link: kept %d of %d rows at score <= 3", len(lk), before)
    return lk[["ticker", "permno", "sdate", "edate"]]


def _attach_permno(df: pd.DataFrame, date_col: str) -> tuple[pd.DataFrame, float]:
    """Join on ticker, then keep only rows inside the link's validity window."""
    lk = _link()
    n_in = len(df)
    out = df.merge(lk, on="ticker", how="inner")
    out = out[(out[date_col] >= out["sdate"]) & (out[date_col] <= out["edate"])]
    # A ticker can map to two permnos in overlapping windows; keep the first
    # deterministically rather than silently duplicating the observation.
    out = out.sort_values([date_col, "ticker", "permno"])
    out = out.drop_duplicates(subset=[date_col, "ticker"], keep="first")
    rate = (len(out) / n_in) if n_in else 0.0
    return out.drop(columns=["sdate", "edate"]), rate


def _to_month_end(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s) + pd.offsets.MonthEnd(0)


def _grid(df: pd.DataFrame, value_col: str, panel_index: pd.DatetimeIndex,
          panel_columns: pd.Index) -> pd.DataFrame:
    """Latest observation per (month, permno), forward-filled within 3 months.

    IBES publishes monthly, but a name can miss a statpers. Carrying the last
    observation for up to three months is a stated modelling choice: beyond
    that the consensus is stale enough that treating it as current would be
    inventing coverage.
    """
    g = (df.groupby(["month", "permno"])[value_col].last().unstack("permno"))
    g.index = pd.to_datetime(g.index)
    g.columns = [str(int(c)) for c in g.columns]
    out = g.reindex(index=panel_index).ffill(limit=3)
    return out.reindex(columns=panel_columns)


@lru_cache(maxsize=1)
def _split_factors_cached(panel_key: str) -> pd.DataFrame:  # pragma: no cover
    raise RuntimeError("use split_factors(panel)")


def split_factors(panel) -> pd.DataFrame:
    """Cumulative share-basis factor, so past targets can be restated.

    `f_t = price_{t-1}(1+ret_t)/price_t` is ~1 in an ordinary month and ~k on a
    k:1 split. `cum_t = prod(f_s for s > t)` converts a target quoted at month
    t onto the CURRENT basis, which is what makes a difference meaningful.
    """
    prc = panel.month_end_price.astype(float)
    ret = panel.monthly_ret.astype(float)
    f = (prc.shift(1) * (1.0 + ret)) / prc
    # Only genuine basis changes; everything else is a price move.
    f = f.where((f > SPLIT_HI) | (f < SPLIT_LO), 1.0)
    f = f.replace([np.inf, -np.inf], np.nan).fillna(1.0)
    # Reverse cumulative product of FUTURE factors, exclusive of month t.
    rev = f.iloc[::-1].cumprod().iloc[::-1]
    cum = rev.shift(-1)
    cum.iloc[-1] = 1.0
    return cum.fillna(1.0)


def build(panel, *, report: dict | None = None) -> dict[str, pd.DataFrame]:
    """Every IBES-derived score frame, aligned to `panel`.

    Returns a dict of (month x permno) frames, each already SIGNED so that
    higher = higher predicted return under its own hypothesis. Nothing here
    decides whether that hypothesis is true.
    """
    idx = panel.monthly_ret.index
    cols = panel.monthly_ret.columns
    rep = report if report is not None else {}
    out: dict[str, pd.DataFrame] = {}

    # ── consensus price targets ────────────────────────────────────────────
    ptg = _require("ptgsumu")
    ptg = ptg[["ticker", "statpers", "meanptg", "medptg", "stdev", "numest",
               "numup1m", "numdown1m"]].copy()
    ptg["statpers"] = pd.to_datetime(ptg["statpers"])
    ptg, rate = _attach_permno(ptg, "statpers")
    if rate < MIN_LINK_MATCH_RATE:
        raise IbesDataError(
            f"ptgsumu link matched only {rate:.1%} of rows (floor "
            f"{MIN_LINK_MATCH_RATE:.0%}). A thin panel that still looks like a "
            f"panel is worse than no panel — refusing to build.")
    ptg["month"] = _to_month_end(ptg["statpers"])
    for c in ("meanptg", "stdev", "numest", "numup1m", "numdown1m"):
        ptg[c] = pd.to_numeric(ptg[c], errors="coerce")

    mean_tgt = _grid(ptg, "meanptg", idx, cols)
    numest = _grid(ptg, "numest", idx, cols)
    nup = _grid(ptg, "numup1m", idx, cols)
    ndn = _grid(ptg, "numdown1m", idx, cols)
    stdev = _grid(ptg, "stdev", idx, cols)

    prc = panel.month_end_price.astype(float).reindex(index=idx, columns=cols)

    # A1 — the LEVEL. No adjustment: both sides are raw and same-dated.
    out["ibes:tgt_upside"] = (mean_tgt / prc.where(prc > 0)) - 1.0

    # A2 — target-revision BREADTH. Counts, so split-immune by construction.
    denom = numest.where(numest > 0)
    out["ibes:tgt_rev_breadth"] = (nup - ndn) / denom

    # A3 — target-revision MAGNITUDE. This is the one that needs the correction.
    cum = split_factors(panel).reindex(index=idx, columns=cols)
    tgt_adj = mean_tgt * cum            # every past target on today's basis
    out["ibes:tgt_rev_3m"] = (tgt_adj / tgt_adj.shift(3)) - 1.0

    # A5 — dispersion, as a FILTER only (its picker version is adjudicated).
    out["ibes:tgt_disp_low"] = -(stdev / mean_tgt.where(mean_tgt > 0))

    # ── ANALYST-IDENT-1 diagnostics (TRIALS/PREREG_ANALYST_IDENT_1.md) ─────
    #
    # A2 and A3 disagreed in SIGN in the small segment, so under the parent's
    # registered rule the object is not identified. The successor hypothesis
    # the parent wrote down: `numup1m`/`numdown1m` count analyst ACTIONS, while
    # a change in `meanptg` mixes actions with COVERAGE CHURN — an analyst
    # initiating coverage at a high target moves the mean with nobody having
    # revised anything, and the contamination scales as 1/numest, so it bites
    # hardest exactly where coverage is thin. That is small caps.
    #
    # These frames split A3 on whether the analyst COUNT held still across the
    # same 3-month window the signal differences over. They are diagnostics,
    # never production signals: no `allowed_in_pm` entry references them.
    churn_free = (numest == numest.shift(3)) & numest.notna() & numest.shift(3).notna()
    out["ibes:tgt_rev_3m_nochurn"] = out["ibes:tgt_rev_3m"].where(churn_free)
    out["ibes:tgt_rev_3m_churn"] = out["ibes:tgt_rev_3m"].where(
        ~churn_free & numest.notna() & numest.shift(3).notna())
    # P4 placebo: A2 is blind to churn BY CONSTRUCTION (it counts actions), so
    # the same purge must leave it materially unchanged. If it does not, the
    # purge is selecting on something other than churn and the design is void.
    out["ibes:tgt_rev_breadth_nochurn"] = out["ibes:tgt_rev_breadth"].where(churn_free)
    rep["ident1_churn"] = {
        "churn_free_share": round(float(
            churn_free.sum().sum()
            / max(1, int((numest.notna() & numest.shift(3).notna()).sum().sum()))), 4),
        "note": ("share of name-months where the analyst COUNT is unchanged "
                 "over the 3m window A3 differences over"),
    }

    rep["ptgsumu"] = Coverage(
        "ptgsumu", len(ptg), len(ptg), rate, int(mean_tgt.notna().any(axis=1).sum()),
        float(mean_tgt.notna().sum(axis=1).mean())).as_dict()

    # ── EPS consensus (the replication arm) ────────────────────────────────
    eps = _require("statsumu_epsus")
    eps = eps[eps["fpi"].astype(str) == "1"]
    eps = eps[["ticker", "statpers", "numest", "numup", "numdown", "meanest"]].copy()
    eps["statpers"] = pd.to_datetime(eps["statpers"])
    eps, erate = _attach_permno(eps, "statpers")
    eps["month"] = _to_month_end(eps["statpers"])
    for c in ("numest", "numup", "numdown", "meanest"):
        eps[c] = pd.to_numeric(eps[c], errors="coerce")

    e_num = _grid(eps, "numest", idx, cols)
    e_up = _grid(eps, "numup", idx, cols)
    e_dn = _grid(eps, "numdown", idx, cols)
    out["ibes:eps_rev_breadth"] = (e_up - e_dn) / e_num.where(e_num > 0)

    rep["statsumu_epsus"] = Coverage(
        "statsumu_epsus", len(eps), len(eps), erate,
        int(e_num.notna().any(axis=1).sum()),
        float(e_num.notna().sum(axis=1).mean())).as_dict()

    # ── the loud check ─────────────────────────────────────────────────────
    for key, frame in out.items():
        cov = float(frame.notna().sum(axis=1).mean())
        rep.setdefault("signal_coverage", {})[key] = round(cov, 1)
        # ANALYST-IDENT-1's frames are deliberate SUBSAMPLES, so thin coverage
        # is the measurement, not a fault — a purge that removes most of the
        # panel is a POWER_FAILED verdict for that trial, adjudicated in its own
        # runner against its registered retention floor. Exempting them here
        # keeps the production floor exactly as strict as it was.
        if key.endswith(("_nochurn", "_churn")):
            rep.setdefault("diagnostic_coverage", {})[key] = round(cov, 1)
            out[key] = frame.replace([np.inf, -np.inf], np.nan).astype(np.float32)
            continue
        if cov < MIN_NAMES_PER_MONTH:
            raise IbesDataError(
                f"{key}: {cov:.0f} names/month, floor {MIN_NAMES_PER_MONTH}. "
                f"Refusing to hand back a degenerate signal frame.")
        out[key] = frame.replace([np.inf, -np.inf], np.nan).astype(np.float32)

    return out


def coverage_report(panel) -> dict:
    rep: dict = {}
    build(panel, report=rep)
    return rep
