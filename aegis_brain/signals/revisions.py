"""Analyst EPS estimate-revision signal (IBES) as a monthly cross-sectional panel.

Estimate revisions are one of the most durable post-1990 anomalies: when the
sell-side consensus for a firm's forward EPS drifts up (down), returns drift the
same way over the following weeks (Stickel 1991; Chan-Jegadeesh-Lakonishok 1996;
the "revisions" leg of the GKX fundamentals block). Here it is a cross-sectional
FEATURE for the combiner, not a standalone lane.

POINT-IN-TIME.  IBES `statpers` is a monthly consensus SNAPSHOT date — the day the
summary file was cut. It IS the point-in-time anchor: a month-M signal may only use
snapshots dated on or before month-M's end. All operations here are strictly
backward-looking (shift / trailing rolling), so no future consensus ever leaks into
a past month.

FORMULA (documented exactly).  Filter to FY1 consensus (`fpi='1'`, `measure='EPS'`).
Per security (`cusip`), collapse to one snapshot per calendar month (keep the LAST
`statpers` in the month) and order by month. Let `m` be this month's FY1 mean estimate
and `m_prev` the prior monthly snapshot's mean estimate, but ONLY when both snapshots
target the SAME fiscal period (`fpedats` unchanged) — an FY1 target roll is not a
revision and is neutralised. With eps = 1e-6:

    raw     = (m - m_prev) / (|m_prev| + eps)          # scaled one-month revision
    raw_c   = clip(raw, -1, +1)                         # robust to split/error jumps
    netdir  = trailing-3-month mean of sign(raw)        # revision-momentum, in [-1, +1]
    revision_score = 0.5 * raw_c + 0.5 * netdir

`revision_score` is 0.0 where there is no comparable prior (first snapshot of a
security, or the month of an FY1 target roll). Values are UNADJUSTED as given by IBES.
`numest <= 1` is the thin-coverage flag (a one-analyst "revision" is unreliable); the
row is KEPT and `numest` carried through so the backtest can down-weight or drop it.

Mapping to CRSP permno uses the PIT 8-digit-CUSIP bridge in `events.crsp_link`;
unmatched rows are dropped. Output is written to data/revision_panel.parquet (gitignored).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.events.crsp_link import attach_permno_by_cusip

RAW = MODULE_ROOT / "data" / "wrds_raw"
OUT_PATH = MODULE_ROOT / "data" / "revision_panel.parquet"

_EPS = 1e-6


def _load_ibes() -> pd.DataFrame:
    """FY1 EPS consensus snapshots, the only slice this signal consumes."""
    df = pd.read_parquet(
        RAW / "ibes_epsus.parquet",
        columns=["cusip", "statpers", "fpi", "measure", "fpedats", "numest", "meanest"],
    )
    df = df[(df["measure"] == "EPS") & (df["fpi"] == "1")].copy()
    return df


def compute_revision_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Pure, offline core: raw FY1 IBES snapshots -> monthly revision panel.

    Input must carry columns: cusip, statpers, meanest, numest, fpedats (fpi/measure
    already filtered to FY1/EPS, or single-security synthetic fixtures). Returns one
    row per (cusip, month) with columns [cusip, month, revision_score, numest].
    """
    d = df[["cusip", "statpers", "meanest", "numest", "fpedats"]].copy()
    d["statpers"] = pd.to_datetime(d["statpers"])
    d["fpedats"] = pd.to_datetime(d["fpedats"])
    # PIT month anchor: statpers -> calendar month-end.
    d["month"] = d["statpers"].dt.to_period("M").dt.to_timestamp("M")

    # Collapse to one snapshot per (cusip, month): keep the LAST statpers in the month.
    d = d.sort_values(["cusip", "month", "statpers"])
    d = d.groupby(["cusip", "month"], as_index=False).last()
    d = d.sort_values(["cusip", "month"])

    g = d.groupby("cusip", sort=False)
    m_prev = g["meanest"].shift(1)
    fpe_prev = g["fpedats"].shift(1)
    same_target = d["fpedats"].eq(fpe_prev)

    raw = (d["meanest"] - m_prev) / (m_prev.abs() + _EPS)
    raw = raw.where(same_target)  # NaN at first obs and at FY1 target rolls
    raw_c = raw.clip(-1.0, 1.0)
    chg_sign = np.sign(raw)  # NaN where raw is NaN

    # Trailing-3-month mean of change-sign (revision momentum); skips NaNs, min 1 obs.
    netdir = (
        chg_sign.groupby(d["cusip"], sort=False)
        .rolling(3, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    score = 0.5 * raw_c + 0.5 * netdir
    d["revision_score"] = score.fillna(0.0)

    out = d[["cusip", "month", "revision_score", "numest"]].reset_index(drop=True)
    return out


def build_revision_panel(df: pd.DataFrame | None = None, write: bool = True) -> pd.DataFrame:
    """Build the monthly analyst-revision panel and (optionally) persist it.

    Loads FY1 EPS IBES snapshots (unless `df` is supplied), scores revisions PIT,
    maps cusip -> CRSP permno via the date-bounded 8-digit-CUSIP bridge, drops
    unmatched rows, and writes data/revision_panel.parquet. Returns the panel with
    columns [permno, month, revision_score, numest].
    """
    if df is None:
        df = _load_ibes()

    scored = compute_revision_scores(df)

    mapped, diag = attach_permno_by_cusip(scored, cusip_col="cusip", date_col="month")
    build_revision_panel.last_match_diag = diag  # surfaced for the run report

    mapped = mapped[mapped["permno"].notna()].copy()
    out = (
        mapped[["permno", "month", "revision_score", "numest"]]
        .sort_values(["month", "permno"])
        .reset_index(drop=True)
    )

    if write:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(OUT_PATH)
    return out
