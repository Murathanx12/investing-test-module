"""Exit rules — the layer the 179-candidate search never tested.

Every strategy the factory has ever run decided *what to buy* and then let the
rebalance clock decide, implicitly, what to sell: a name leaves the book when it
falls out of the incumbency band at a rebalance, and at no other time. That is
one exit rule out of many, and it was never registered as a choice.

This module makes the exit an explicit, swappable object so it can be swept with
the entry held fixed. Two hooks, both optional:

    interim(ctx) -> Index      names to sell THIS month, outside any rebalance
    retain(ctx)  -> Index      incumbents to keep at a rebalance regardless of rank

`interim` sales are replaced immediately by the best-scoring eligible non-held
name, so the book stays fully invested at `top_n`. That is deliberate: it removes
cash drag as a confound, leaving only the question the sweep asks — does it matter
WHICH names you hold, given you hold 150 of them?

Nothing here fits anything. Every threshold is a registered constant read from
the prereg (TRIALS/PREREG_PF7_EXIT_SWEEP.md), not chosen at run time.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Registered constants — frozen in the prereg, never tuned here.
STOP_DRAWDOWN = -0.20        # A1: trailing stop from since-entry peak
BREAK_PCTILE = 0.50          # A3: composite percentile below which the thesis broke
REVIEW_MONTHS = (2, 5, 8, 11)  # A4: earnings-season calendar proxy (Feb/May/Aug/Nov)


@dataclass
class ExitContext:
    """Everything an exit rule may look at. Strictly point-in-time.

    `score_row` and `mom_row` are FORMATION-month values (month m-1 for a
    decision realised in month m), identical to the convention the engine uses
    for selection. An exit rule that read the test month would be trading on
    information it could not have had.
    """

    formation_m: pd.Timestamp
    test_m: pd.Timestamp
    held: pd.Index                  # names currently in the book
    score_row: pd.Series            # composite score, eligible names only
    mom_row: pd.Series              # 12-1 momentum, all names
    peak_dd: pd.Series              # drawdown from since-entry peak, held names
    is_rebalance: bool


class ExitRule:
    """Base class: the banked behaviour — sell only at the rebalance, on rank."""

    name = "annual_rank"
    label = "A0 BASELINE — annual rank rebalance, incumbency band, nothing else"

    def interim(self, ctx: ExitContext) -> pd.Index:
        return pd.Index([])

    def retain(self, ctx: ExitContext) -> pd.Index:
        return pd.Index([])


class TrailingStop(ExitRule):
    """A1 — sell any name down >= 20% from its since-entry peak, and replace it.

    The Bessembinder prediction lives here: a stop truncates the left tail of
    every position, but the right tail of the CROSS-SECTION is where all the
    wealth is, and a name on its way to 10x routinely draws down 20% first.
    """

    name = "trailing_stop_20"
    label = f"A1 TRAILING-STOP — sell at {STOP_DRAWDOWN:.0%} from since-entry peak"

    def interim(self, ctx: ExitContext) -> pd.Index:
        dd = ctx.peak_dd.reindex(ctx.held).dropna()
        return dd.index[dd <= STOP_DRAWDOWN]


class MomentumHold(ExitRule):
    """A2 — let winners run: an incumbent with positive 12-1 momentum is kept.

    Retention DISPLACES a fresh pick rather than expanding the book, so the name
    count is unchanged; the arm trades less than the baseline by construction.
    """

    name = "momentum_hold"
    label = "A2 MOMENTUM-HOLD — force-retain incumbents with positive 12-1 momentum"

    def retain(self, ctx: ExitContext) -> pd.Index:
        m = ctx.mom_row.reindex(ctx.held).dropna()
        return m.index[m > 0]


class FundamentalBreak(ExitRule):
    """A3 — exit if and only if the selecting signal breaks.

    'Broke' = the name's composite score falls below the eligible-universe
    median. Checked every month (a thesis does not break on an anniversary).
    Rank alone never sells: at the annual clock every unbroken incumbent is
    force-retained, so the rebalance only refills slots the breaks emptied.
    """

    name = "fundamental_break"
    label = (f"A3 FUNDAMENTAL-BREAK — sell only when composite percentile "
             f"< {BREAK_PCTILE:.2f}; rank never sells")

    def _broken(self, ctx: ExitContext) -> pd.Index:
        s = ctx.score_row.dropna()
        if s.empty:
            return pd.Index([])
        pct = s.rank(pct=True)
        held_pct = pct.reindex(ctx.held)
        # A held name that has left the eligible universe has no percentile.
        # It is NOT broken — absence of evidence is not a sell signal, and
        # treating NaN as a break would silently turn A3 into a churn rule.
        held_pct = held_pct.dropna()
        return held_pct.index[held_pct < BREAK_PCTILE]

    def interim(self, ctx: ExitContext) -> pd.Index:
        return self._broken(ctx)

    def retain(self, ctx: ExitContext) -> pd.Index:
        broken = set(self._broken(ctx))
        return pd.Index([s for s in ctx.held if s not in broken])


class EarningsAnchored(ExitRule):
    """A4 — selling decisions happen only at scheduled reviews.

    The Selling Fast mechanism is attention: PMs sell badly because selling is
    an afterthought, and they sell WELL in earnings season when the firm is in
    front of them. This arm gives every name four scheduled appointments a year
    and forbids selling in between.

    DISCLOSED PROXY: the CRSP spine has no per-firm report dates, so this is a
    calendar (Feb/May/Aug/Nov), correct for December-fiscal-year firms and wrong
    for the rest. It tests scheduled staggered review, not per-firm attention.
    """

    name = "earnings_anchored"
    label = ("A4 EARNINGS-ANCHORED — review only in Feb/May/Aug/Nov "
             "(calendar proxy); out-of-band names sold at review")

    def __init__(self, hold_band_mult: float = 3.0, top_n: int = 150) -> None:
        self.band_n = max(int(hold_band_mult * top_n), top_n)

    def interim(self, ctx: ExitContext) -> pd.Index:
        if ctx.formation_m.month not in REVIEW_MONTHS:
            return pd.Index([])
        s = ctx.score_row.dropna()
        if s.empty:
            return pd.Index([])
        band = set(s.nlargest(min(self.band_n, len(s))).index)
        # Only names that are IN the scored universe and out of the band are
        # sold. A name with no score this month is not reviewable.
        scored = [x for x in ctx.held if x in s.index]
        return pd.Index([x for x in scored if x not in band])

    def retain(self, ctx: ExitContext) -> pd.Index:
        # The annual clock must not sell anything in this arm: selling happens
        # ONLY at a review. Retaining every incumbent turns the clock into a
        # pure refill of slots that delistings and reviews emptied, which is
        # what keeps the book at 150 names over 59 years without smuggling a
        # second, unregistered selling rule into the arm.
        return pd.Index(ctx.held)


ARMS: dict[str, ExitRule] = {}


def build_arms(top_n: int, hold_band_mult: float) -> dict[str, ExitRule]:
    """The five registered arms, in prereg order."""
    return {
        "A0_baseline": ExitRule(),
        "A1_trailing_stop": TrailingStop(),
        "A2_momentum_hold": MomentumHold(),
        "A3_fundamental_break": FundamentalBreak(),
        "A4_earnings_anchored": EarningsAnchored(hold_band_mult, top_n),
    }


# ── peak tracking ───────────────────────────────────────────────────────────
class PeakTracker:
    """Cumulative return since entry, and drawdown from its running peak.

    Reset on entry, dropped on exit. Kept out of the engine so the engine's
    banked path stays byte-identical when no exit rule is passed.
    """

    def __init__(self) -> None:
        self._cum: dict[str, float] = {}
        self._peak: dict[str, float] = {}

    def enter(self, names) -> None:
        for s in names:
            self._cum[s] = 1.0
            self._peak[s] = 1.0

    def leave(self, names) -> None:
        for s in names:
            self._cum.pop(s, None)
            self._peak.pop(s, None)

    def update(self, rets: pd.Series) -> None:
        for s, r in rets.items():
            if s in self._cum and np.isfinite(r):
                self._cum[s] *= (1.0 + float(r))
                if self._cum[s] > self._peak[s]:
                    self._peak[s] = self._cum[s]

    def drawdown(self) -> pd.Series:
        if not self._cum:
            return pd.Series(dtype=float)
        return pd.Series({s: self._cum[s] / self._peak[s] - 1.0
                          for s in self._cum}, dtype=float)
