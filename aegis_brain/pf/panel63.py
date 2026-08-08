"""The 63-year survivorship-free spine for the portfolio factory.

Two certified CRSP panels are stitched into one monthly panel:

    data/crsp_panel_1962_2001   480 months, 20,902 permnos, real dlrets
    data/crsp_panel_2002        276 months, 11,098 permnos, real dlrets

They share the join key (permno as string) and do not overlap in time, so the
stitch is a concat, not a merge. Every assumption in that sentence is CHECKED
at load time and raises — a silently mis-stitched panel would print plausible
numbers forever (the house failure mode).

BENCHMARK. "Beat SPY" over 63 years cannot be measured against SPY: SPY starts
1993. The benchmark is the CRSP value-weighted TOTAL market return, taken from
the pinned Ken French vintage as `mktrf + rf`. That is the same index SPY
tracks, survivorship-free, available from 1963-07. Where SPY exists the two
differ by fees and tracking only. Every scorecard says which benchmark it used.

REGIME BLOCKS are frozen here, before any strategy is run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel, load_cached_panel
from aegis_brain.harness.benchmark import load_ff_factors

logger = logging.getLogger(__name__)

ERA_DIR = MODULE_ROOT / "data" / "crsp_panel_1962_2001"
MODERN_DIR = MODULE_ROOT / "data" / "crsp_panel_2002"

# Benchmark availability (Ken French monthly series starts 1963-07).
PANEL63_FIRST = "1963-07-31"
# Holdout: the most recent 24 months of the panel. Nothing in a factory run
# reads past this boundary; firing the holdout is a separate attended step.
HOLDOUT_FIRST = "2023-01-31"
EVAL_LAST = "2022-12-31"

# ── Regime blocks (frozen 2026-08-08, before any PF-1 compute) ──────────────
# GATE blocks are the six named in EXECUTION_STANDARD §3 ("positive net excess
# in >= 4 of 6"). The finer FULL blocks are reported alongside because a 45-year
# "pre-2008" bucket hides more than it shows.
GATE_BLOCKS: tuple[tuple[str, str, str], ...] = (
    ("pre-2008", "1963-07-31", "2007-12-31"),
    ("GFC", "2008-01-31", "2009-06-30"),
    ("post-crisis-bull", "2009-07-31", "2020-01-31"),
    ("COVID", "2020-02-29", "2020-12-31"),
    ("bear-2022", "2022-01-31", "2022-12-31"),
    ("megacap-2023+", "2023-01-31", "2024-12-31"),  # HOLDOUT — not evaluated
)
HOLDOUT_BLOCK = "megacap-2023+"

FULL_BLOCKS: tuple[tuple[str, str, str], ...] = (
    ("1963-72-go-go", "1963-07-31", "1972-12-31"),
    ("1973-82-stagflation", "1973-01-31", "1982-12-31"),
    ("1983-94-disinflation", "1983-01-31", "1994-12-31"),
    ("1995-99-tech-boom", "1995-01-31", "1999-12-31"),
    ("2000-02-dotcom-bust", "2000-01-31", "2002-12-31"),
    ("2003-07-credit-boom", "2003-01-31", "2007-12-31"),
    ("2008-09H1-GFC", "2008-01-31", "2009-06-30"),
    ("2009H2-19-QE-bull", "2009-07-31", "2019-12-31"),
    ("2020-COVID", "2020-01-31", "2020-12-31"),
    ("2021-reflation", "2021-01-31", "2021-12-31"),
    ("2022-bear", "2022-01-31", "2022-12-31"),
)


@dataclass(frozen=True)
class Spine:
    """Panel + aligned benchmark series + the eligibility mask, built once."""

    panel: Panel
    mkt: pd.Series          # CRSP VW total return (mktrf + rf), monthly decimal
    rf: pd.Series           # 1-month T-bill, monthly decimal
    provenance: dict

    @property
    def months(self) -> pd.DatetimeIndex:
        return self.panel.monthly_ret.index


def _check_panel(p: Panel, name: str) -> None:
    r = p.monthly_ret
    if r.empty:
        raise RuntimeError(f"{name}: empty monthly_ret")
    if not r.index.is_monotonic_increasing:
        raise RuntimeError(f"{name}: month index not sorted")
    if not all(c.isdigit() for c in list(r.columns[:50])):
        raise RuntimeError(f"{name}: columns are not permno strings — "
                           "the two panels would not stitch on the same key")
    frac = float(r.notna().sum().sum()) / r.size
    if frac < 0.01:
        raise RuntimeError(f"{name}: only {frac:.4%} of cells populated")
    logger.info("%s: %d months %s..%s, %d permnos, %.1f%% cells",
                name, len(r), r.index.min().date(), r.index.max().date(),
                r.shape[1], 100 * frac)


def load_spine(first: str = PANEL63_FIRST, last: str = EVAL_LAST,
               *, allow_holdout: bool = False) -> Spine:
    """Stitched panel truncated to [first, last], with benchmark aligned.

    `allow_holdout=False` (the default) hard-refuses any window reaching into
    the registered holdout. Reading the holdout is an attended, one-shot act;
    it must never happen because a default was left loose.
    """
    last_ts = pd.Timestamp(last)
    if not allow_holdout and last_ts >= pd.Timestamp(HOLDOUT_FIRST):
        raise RuntimeError(
            f"last={last} reaches into the registered holdout "
            f"(>= {HOLDOUT_FIRST}). Pass allow_holdout=True only inside an "
            "attended one-shot holdout firing.")

    era = load_cached_panel(ERA_DIR)
    modern = load_cached_panel(MODERN_DIR)
    _check_panel(era, "crsp_panel_1962_2001")
    _check_panel(modern, "crsp_panel_2002")
    if era.monthly_ret.index.max() >= modern.monthly_ret.index.min():
        raise RuntimeError("era and modern panels overlap in time — stitch "
                           "would double-count months")

    def stitch(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
        cols = a.columns.union(b.columns)
        out = pd.concat([a.reindex(columns=cols), b.reindex(columns=cols)])
        return out.sort_index()

    ret = stitch(era.monthly_ret, modern.monthly_ret)
    prc = stitch(era.month_end_price, modern.month_end_price)
    dvol = stitch(era.monthly_dollar_vol, modern.monthly_dollar_vol)

    lo, hi = pd.Timestamp(first), last_ts
    # one extra leading month: formation at m-1 for the first test month m
    lead = ret.index[ret.index < lo]
    keep_lo = lead.max() if len(lead) else lo
    sel = (ret.index >= keep_lo) & (ret.index <= hi)
    ret, prc, dvol = ret.loc[sel], prc.loc[sel], dvol.loc[sel]

    # drop permnos with no data at all in the window (memory, not selection:
    # an all-NaN column can never be eligible, held, or ranked)
    live = ret.notna().any() | prc.notna().any()
    ret, prc, dvol = ret.loc[:, live], prc.loc[:, live], dvol.loc[:, live]

    panel = Panel(monthly_ret=ret, month_end_price=prc, monthly_dollar_vol=dvol,
                  delist_month={s: ret[s].last_valid_index() for s in ret.columns})

    ff = load_ff_factors(MODULE_ROOT / "data")
    mkt = (ff["mktrf"] + ff["rf"]).reindex(ret.index)
    rf = ff["rf"].reindex(ret.index)
    missing = int(mkt.isna().sum())
    if missing:
        raise RuntimeError(f"benchmark missing for {missing} panel months "
                           f"({ret.index[mkt.isna()].min()} ...) — refusing to "
                           "score excess return against a hole")

    prov = {
        "panels": [str(ERA_DIR.name), str(MODERN_DIR.name)],
        "months": len(ret), "permnos": int(ret.shape[1]),
        "first": str(ret.index.min().date()), "last": str(ret.index.max().date()),
        "benchmark": "CRSP value-weighted total return (Ken French mktrf+rf, "
                     "pinned vintage) — the index SPY tracks; SPY itself only "
                     "exists from 1993",
        "holdout_first": HOLDOUT_FIRST, "holdout_read": bool(allow_holdout),
    }
    logger.info("spine: %s", prov)
    return Spine(panel=panel, mkt=mkt.astype(float), rf=rf.astype(float),
                 provenance=prov)


def segment_mask(panel: Panel, segment: str) -> pd.DataFrame:
    """Formation-month membership by dollar-volume rank (PIT: month m only).

    Matches factory/explore.segment_mask exactly, plus an 'all' segment
    (everything inside the liquid 3000) for portfolio-level runs.
    """
    rank = panel.monthly_dollar_vol.rank(axis=1, ascending=False)
    if segment == "largemid":
        return rank <= 1000
    if segment == "small":
        return (rank > 1000) & (rank <= 3000)
    if segment == "all":
        return rank <= 3000
    raise ValueError(f"unknown segment {segment!r}")


def eligibility(spine: Spine, segment: str) -> pd.DataFrame:
    """Production eligibility (price + dollar-volume floors) ∩ segment."""
    return spine.panel.eligible() & segment_mask(spine.panel, segment)


def block_slice(x: pd.Series, first: str, last: str) -> pd.Series:
    return x.loc[(x.index >= pd.Timestamp(first)) & (x.index <= pd.Timestamp(last))]


def annualize(monthly: pd.Series) -> float:
    """Geometric annualized return of a monthly decimal series."""
    m = monthly.dropna()
    if len(m) == 0:
        return float("nan")
    return float((1.0 + m).prod() ** (12.0 / len(m)) - 1.0)


def max_drawdown(monthly: pd.Series) -> float:
    cum = (1.0 + monthly.dropna()).cumprod()
    if cum.empty:
        return float("nan")
    return float((cum / cum.cummax() - 1.0).min())


def to_float32(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.astype(np.float32)
