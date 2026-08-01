"""Monthly long-only event book — the harvest test that stands between an event
CAR and a claim. Spec frozen 2026-08-02 (TRIALS/TRIAL-EVENT-13DG.md "BOOK
STAGE", module commit 6fcc381, BEFORE this file existed).

A differenced CAR says an effect exists at event resolution. It does NOT say a
monthly long-only account could have earned it, and the gap between those two
statements is where most published event anomalies live. This module builds the
account: month-end entry only, a fixed hold, equal weights, the standard factory
universe, and per-name costs on the turnover actually incurred.

WHAT THE CONSTRUCTION DELIBERATELY GIVES UP (frozen, not a defect):

  * **The announcement pop and part of the +1..+20 window.** A name enters at
    the first month-end ON OR AFTER its filing date, so a filing on the 3rd of
    the month sits unheld for most of the month in which its drift is
    strongest. A monthly book cannot trade the filing day; pretending otherwise
    is the lookahead this programme exists to refuse. What is measured here is
    the harvestable REMAINDER.
  * **The micro third.** Eligibility is the factory universe with dollar-volume
    rank <= 3000 at the entry month-end. NEG_RESULTS 29 measured 31% of matched
    13D events sitting outside that universe; excluding them is the question
    this stage exists to answer, not a filter chosen after the fact.

MECHANICAL PLUMBING (spec silent, precedent followed, disclosed):

  * The month/return convention is `factory/explore.py`'s, unchanged: holdings
    are fixed at a FORMATION month-end and earn the FOLLOWING month's return.
    "Entry at month-end M" therefore means the first return earned is month
    M+1's — the book never touches a return from the month in which it entered.
  * A hold of H months means membership at formation month-ends M, M+1, ...,
    M+H-1, and exit AT M+H. The name earns H monthly returns.
  * Membership is a SET of (name, formation month) pairs built as the union of
    each event's hold interval. That gives "a re-filing resets the clock" and
    "no doubled positions" from one mechanism rather than two rules that could
    disagree.
  * An event whose entry month-end fails eligibility creates NO position at all
    — it is dropped, not deferred to the next eligible month. Deferring would
    invent an entry rule the freeze does not contain. Eligibility is checked at
    ENTRY only, as written; how often a held name later falls out is measured
    and reported rather than assumed harmless.
  * A formation month with no active name is not scored (there is no book to
    hold); the count is reported.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from aegis_brain.data.eodhd_panel import Panel
from aegis_brain.factory.explore import segment_mask

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BookConfig:
    """Frozen in the BOOK STAGE registration — do not tune per book."""

    hold_months: int = 3
    max_rank: int = 3000                  # the factory's small-segment ceiling
    cost_bps_one_way: float = 25.0        # flat guard / fallback for missing KO
    first_test_month: str = "2004-01-31"
    last_test_month: str = "2018-12-31"   # explore/confirm boundary (inclusive)


def eligible_universe(panel: Panel, cfg: BookConfig | None = None) -> pd.DataFrame:
    """The factory universe, rank <= max_rank. Identical by construction to
    `panel.eligible() & (largemid | small)` — pinned by a test, because a book
    scored against a different universe than the factory's is not comparable to
    anything else in the ledger."""
    cfg = cfg or BookConfig()
    rank = panel.monthly_dollar_vol.rank(axis=1, ascending=False)
    return panel.eligible() & (rank <= cfg.max_rank)


def entry_index(filing_date: pd.Timestamp, months: pd.DatetimeIndex) -> int | None:
    """Position of the first month-end ON OR AFTER the filing date.

    A filing on the 15th enters at THAT month's end; a filing on the month-end
    itself enters that day. Entry can never precede the filing.
    """
    pos = int(months.searchsorted(pd.Timestamp(filing_date), side="left"))
    return pos if pos < len(months) else None


def membership_frame(events: pd.DataFrame, panel: Panel,
                     cfg: BookConfig | None = None,
                     eligible: pd.DataFrame | None = None
                     ) -> tuple[pd.DataFrame, dict]:
    """[month x sym] boolean: is this name in the book at this formation month?

    `events` needs `permno` and `event_date`. Returns the mask plus entry
    diagnostics (how many events created a position and why the rest did not).
    """
    cfg = cfg or BookConfig()
    months = panel.monthly_ret.index
    elig = eligible_universe(panel, cfg) if eligible is None else eligible

    cols = {c: i for i, c in enumerate(panel.monthly_ret.columns)}
    mask = np.zeros((len(months), len(cols)), dtype=bool)

    diag = {"events_in": int(len(events)), "no_month": 0, "not_in_panel": 0,
            "ineligible_at_entry": 0, "entered": 0}
    for permno, dt in zip(events["permno"], events["event_date"]):
        sym = str(int(permno))
        j = cols.get(sym)
        if j is None:
            diag["not_in_panel"] += 1
            continue
        i0 = entry_index(dt, months)
        if i0 is None:
            diag["no_month"] += 1
            continue
        if not bool(elig.iat[i0, j]):
            diag["ineligible_at_entry"] += 1
            continue
        mask[i0:i0 + cfg.hold_months, j] = True     # union => reset, no doubling
        diag["entered"] += 1

    out = pd.DataFrame(mask, index=months, columns=panel.monthly_ret.columns)
    logger.info("membership: %s", diag)
    return out, diag


def run_book(panel: Panel, events: pd.DataFrame,
             cfg: BookConfig | None = None,
             cost_frame: pd.DataFrame | None = None,
             restrict: pd.DataFrame | None = None,
             membership: pd.DataFrame | None = None
             ) -> dict:
    """One monthly book. Returns {'summary': dict, 'monthly': DataFrame}.

    cost_frame: [month x sym] ONE-WAY cost in bps (the KO half-spread frame).
    Names missing from it fall back to cfg.cost_bps_one_way; None means the flat
    cost everywhere, byte-identical to the flat-cost convention in
    `factory/explore.py`. Pass a zero frame for the zero-cost bound.

    restrict: optional [month x sym] mask (e.g. a segment) applied to BOTH the
    book and its benchmark, so a segment slice is scored against its own
    segment's universe. Reported only, never deciding.
    """
    cfg = cfg or BookConfig()
    elig = eligible_universe(panel, cfg)
    held = membership_frame(events, panel, cfg, elig)[0] if membership is None \
        else membership
    if restrict is not None:
        elig = elig & restrict
        held = held & restrict

    months = panel.monthly_ret.index
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    test_months = [m for m in months if lo <= m <= hi]

    prev_w = pd.Series(dtype=float)
    records: list[dict] = []
    n_empty = 0
    for test_m in test_months:
        pos = months.get_loc(test_m)
        if pos == 0:
            continue
        formation_m = months[pos - 1]

        universe = elig.loc[formation_m]
        universe = universe[universe].index
        names = held.loc[formation_m]
        names = names[names].index
        if len(names) == 0:
            n_empty += 1
            continue

        realized = panel.monthly_ret.loc[test_m]
        w = pd.Series(1.0 / len(names), index=names)

        gross = float((w * realized.reindex(w.index)).sum())
        bench = float(realized.reindex(universe).mean())

        idx = w.index.union(prev_w.index)
        traded_by_name = (w.reindex(idx, fill_value=0.0)
                          - prev_w.reindex(idx, fill_value=0.0)).abs()
        traded = float(traded_by_name.sum())
        if cost_frame is not None:
            c = (cost_frame.loc[formation_m].reindex(traded_by_name.index)
                 .fillna(cfg.cost_bps_one_way))
            charge = float((traded_by_name * c).sum()) / 1e4
        else:
            charge = traded * cfg.cost_bps_one_way / 1e4
        net = gross - charge

        records.append({
            "month": test_m, "n_held": len(names), "n_universe": len(universe),
            "gross": gross, "net": net, "benchmark_ew": bench,
            "excess_gross": gross - bench, "excess_net": net - bench,
            "traded": traded, "cost_bps": charge * 1e4,
        })
        prev_w = w

    monthly = pd.DataFrame(records)
    if monthly.empty:
        raise ValueError("book produced no scored month")
    monthly = monthly.set_index("month")

    def _t(x: pd.Series) -> float:
        x = x.dropna()
        sd = x.std(ddof=1)
        return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else 0.0

    cum = (1 + monthly["net"]).cumprod()
    summary = {
        "months": len(monthly), "months_empty": n_empty,
        "mean_n_held": round(float(monthly["n_held"].mean()), 1),
        "mean_excess_net_bps": round(float(monthly["excess_net"].mean()) * 1e4, 1),
        "t_excess_net": round(_t(monthly["excess_net"]), 2),
        "mean_excess_gross_bps": round(
            float(monthly["excess_gross"].mean()) * 1e4, 1),
        "t_excess_gross": round(_t(monthly["excess_gross"]), 2),
        "mean_cost_bps": round(float(monthly["cost_bps"].mean()), 1),
        "turnover_1way": round(float(monthly["traded"].mean()) / 2, 3),
        "cagr_net": round(float(cum.iloc[-1] ** (12 / len(monthly)) - 1), 4),
        "max_dd": round(float((cum / cum.cummax() - 1).min()), 3),
    }
    return {"summary": summary, "monthly": monthly}


def eligibility_decay(held: pd.DataFrame, elig: pd.DataFrame,
                      cfg: BookConfig | None = None) -> dict:
    """How often a name held under an entry-time eligibility rule is no longer
    eligible later in its hold. Measured rather than assumed harmless — the
    entry-only rule is the frozen text, so the exposure it creates is reported.
    """
    cfg = cfg or BookConfig()
    w = held.loc[cfg.first_test_month:cfg.last_test_month]
    e = elig.loc[cfg.first_test_month:cfg.last_test_month]
    total = int(w.to_numpy().sum())
    stale = int((w & ~e).to_numpy().sum())
    return {"held_name_months": total, "held_while_ineligible": stale,
            "frac": round(stale / total, 4) if total else float("nan")}
