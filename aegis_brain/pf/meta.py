"""PF-META-1 — the "11th account that copies whatever worked".

Murat's idea, stated plainly: run several strategies, watch which ones have
been winning, and put the money there. This module implements it as a
backtestable object so the idea gets a receipt instead of an opinion.

The construction: treat each base strategy's monthly NET return series as an
asset. Every `review_months`, rank the assets by trailing `lookback_months`
return and hold the top `hold_top`, equal-weighted, until the next review.
Switching between strategies costs `switch_bps` on the traded fraction — a
real cost that a paper "just follow the winner" rule always forgets.

Two controls, both frozen before the run:
  * EQUAL-WEIGHT — hold all the strategies all the time, rebalanced monthly.
    This is the boring alternative the winner-chaser must beat.
  * BEST-SINGLE — the single strategy with the highest full-sample return,
    held throughout. This is deliberately UNFAIR to the meta rule (it uses
    hindsight to pick the asset) and exists only as an upper reference; it is
    reported, never a gate.

The house prediction, registered before compute: selection-by-trailing-
performance does NOT beat equal-weighting. It is market timing applied to
strategies instead of stocks, and timing has failed every test this project
has run. Being wrong here is the point of writing it down.

Sequencing is strictly walk-forward: the rank at review month m uses returns
through m only, and is applied to month m+1 onward.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _tw(returns: pd.Series) -> float:
    return float((1.0 + returns.dropna()).prod())


def meta_book(strategy_rets: pd.DataFrame, *, lookback_months: int = 12,
              hold_top: int = 1, review_months: int = 1,
              switch_bps: float = 25.0) -> pd.DataFrame:
    """Trailing-winner selection over strategies. Returns a monthly frame.

    Args:
        strategy_rets: month x strategy NET monthly returns. A strategy is
            eligible in month m only if it has a complete `lookback_months`
            history ending at m-1 (books with later inception simply join
            when they exist — no back-filling, no survivorship).
    """
    if hold_top < 1:
        raise ValueError("hold_top must be >= 1")
    rets = strategy_rets.sort_index()
    months = rets.index
    held: list[str] = []
    records = []

    for i, m in enumerate(months):
        if i == 0:
            continue
        # ── formation uses months strictly before m ─────────────────────────
        hist = rets.iloc[:i]
        if len(hist) < lookback_months:
            continue
        win = hist.iloc[-lookback_months:]
        ok = win.notna().all(axis=0)
        cand = win.loc[:, ok]
        if cand.shape[1] == 0:
            continue

        is_review = (len(records) == 0) or (len(records) % review_months == 0)
        if is_review or not held:
            trailing = (1.0 + cand).prod(axis=0) - 1.0
            new = list(trailing.nlargest(min(hold_top, len(trailing))).index)
        else:
            new = [s for s in held if s in cand.columns] or held

        # ── switching cost on the changed fraction ──────────────────────────
        old_w = pd.Series(1.0 / len(held), index=held) if held else pd.Series(dtype=float)
        new_w = pd.Series(1.0 / len(new), index=new)
        traded = float(old_w.subtract(new_w, fill_value=0.0).abs().sum())
        cost = traded * (switch_bps / 1e4)

        row = rets.loc[m, new]
        if row.isna().any():                    # a held strategy died this month
            row = row.dropna()
            if row.empty:
                continue
        gross = float(row.mean())
        records.append({"month": m, "gross": gross, "net": gross - cost,
                        "cost": cost, "traded": traded, "n_held": len(new),
                        "cash_w": 0.0, "risk_on": True,
                        "holding": "+".join(sorted(new))})
        held = new

    if not records:
        raise RuntimeError("meta book never established — no month had a "
                           "complete lookback window for any strategy")
    return pd.DataFrame(records).set_index("month")


def equal_weight_book(strategy_rets: pd.DataFrame,
                      switch_bps: float = 25.0) -> pd.DataFrame:
    """The control: hold every available strategy, equal-weighted, monthly."""
    rets = strategy_rets.sort_index()
    records = []
    prev: list[str] = []
    for m, row in rets.iterrows():
        avail = list(row.dropna().index)
        if not avail:
            continue
        # only the churn from strategies entering/leaving costs anything
        old_w = pd.Series(1.0 / len(prev), index=prev) if prev else pd.Series(dtype=float)
        new_w = pd.Series(1.0 / len(avail), index=avail)
        traded = float(old_w.subtract(new_w, fill_value=0.0).abs().sum())
        cost = traded * (switch_bps / 1e4)
        gross = float(row[avail].mean())
        records.append({"month": m, "gross": gross, "net": gross - cost,
                        "cost": cost, "traded": traded, "n_held": len(avail),
                        "cash_w": 0.0, "risk_on": True,
                        "holding": "EW:" + "+".join(sorted(avail))})
        prev = avail
    if not records:
        raise RuntimeError("equal-weight control never established")
    return pd.DataFrame(records).set_index("month")


def single_book(strategy_rets: pd.DataFrame, name: str) -> pd.DataFrame:
    """Hold one named strategy throughout (no switching, no extra cost)."""
    s = strategy_rets[name].dropna()
    return pd.DataFrame({
        "month": s.index, "gross": s.values, "net": s.values,
        "cost": 0.0, "traded": 0.0, "n_held": 1, "cash_w": 0.0,
        "risk_on": True, "holding": name}).set_index("month")


def meta_diag(book: pd.DataFrame) -> dict:
    n_years = max(len(book) / 12.0, 1e-9)
    switches = int((book["holding"] != book["holding"].shift()).sum()) - 1
    return {
        "months": len(book), "rebalances": switches + 1,
        "months_skipped_thin_universe": 0, "forced_liquidations": 0,
        "mean_n_held": round(float(book["n_held"].mean()), 2),
        "mean_cash_weight": 0.0,
        "turnover_1way_annual": round(float(book["traded"].sum()) / 2 / n_years, 3),
        "cost_drag_annual_bps": round(float(book["cost"].sum()) / n_years * 1e4, 1),
        "strategy_switches": switches,
        "holding_share": {k: round(v, 3) for k, v in
                          book["holding"].value_counts(normalize=True)
                          .head(8).items()},
    }
