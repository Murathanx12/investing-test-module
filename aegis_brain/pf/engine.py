"""The portfolio backtest loop — one spec in, a monthly book out.

What this is NOT: a decile-spread scan. `factory/explore.scan_signal` answers
"does this signal carry information" with a top-decile long book vs the
equal-weight universe. This answers the money question the execution standard
asks: a REAL portfolio of N names, weights drifting between rebalances,
delisted names liquidated, costs charged on traded value, cash earning the
bill rate, measured against the market a buy-and-hold investor could have held.

Timing convention (identical to the rest of the module, and structural):
    formation month m-1 → decisions → realized return of month m.

Delisting: the CRSP panels carry real delisting returns as a name's final
observation. A held name whose return goes NaN is force-liquidated to cash at
that month's open at its last value (return 0 for the stub, cost charged), and
the count is reported. Dropping such names silently would re-import
survivorship bias through the back door.

CAVEAT, and the reason `delist_stub` exists (PF-4, external review 2026-08-09):
assigning 0 % to that stub is itself a mild upward bias. CRSP's DLRET is missing
for roughly a third of delisting events, and it is missing disproportionately
for the performance-related ones (Shumway 1997), which is exactly the population
whose true return is large and negative. Pass `delist_stub` — a month × permno
frame of stub returns — to charge those names something other than zero. The
default stays 0.0 so every banked scorecard reproduces to the decimal.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.pf.spec import StrategySpec

logger = logging.getLogger(__name__)

FLAT_BPS = {"flat25": 25.0, "flat0": 0.0}


def _target_weights(score_row: pd.Series, held: pd.Index, spec: StrategySpec
                    ) -> pd.Series:
    """Top-N selection with incumbency band, then weighting and the cap."""
    n = min(spec.top_n, len(score_row))
    band_n = max(int(spec.hold_band_mult * n), n)
    band = set(score_row.nlargest(band_n).index)
    kept = [s for s in held if s in band]
    kept = (score_row.reindex(kept).dropna().sort_values(ascending=False)
            .index[:n].tolist())
    fresh = [s for s in score_row.sort_values(ascending=False).index
             if s not in kept][: n - len(kept)]
    picks = pd.Index(kept + fresh)

    if spec.weighting == "ew":
        w = pd.Series(1.0 / len(picks), index=picks)
    else:  # score weighting on within-selection rank (never on raw score units)
        r = score_row.reindex(picks).rank()
        w = r / r.sum()
    if spec.max_weight < 1.0:
        w = w.clip(upper=spec.max_weight)
        w = w / w.sum()
    return w


def run_book(
    panel,
    score: pd.DataFrame,
    eligible: pd.DataFrame,
    spec: StrategySpec,
    rf: pd.Series,
    cost_frame: pd.DataFrame | None = None,
    regime_on: pd.Series | None = None,
    delist_stub: pd.DataFrame | None = None,
    holdings_out: list | None = None,
) -> dict:
    """Run one strategy. Returns {'monthly': DataFrame, 'diag': dict}.

    regime_on: optional boolean Series indexed by FORMATION month. False months
    hold cash instead of the book (walk-forward labels only — see regimes.py).

    delist_stub: optional month × permno frame of returns to charge a held name
    in the month its return goes missing, instead of 0. See the module docstring.

    holdings_out: optional list; if given, one dict per test month recording the
    invested weights AFTER rebalancing. Costs nothing when omitted, and lets the
    characteristic-matched placebo and the event-time membership profile replay
    the book's actual positions without re-deriving the incumbency-band logic.
    """
    ret = panel.monthly_ret
    months = ret.index
    lo, hi = pd.Timestamp(spec.first_month), pd.Timestamp(spec.last_month)
    test_months = [m for m in months if lo <= m <= hi]
    if not test_months:
        raise RuntimeError(f"{spec.name}: no test months in "
                           f"{spec.first_month}..{spec.last_month}")

    flat_bps = FLAT_BPS.get(spec.cost_model)
    if spec.cost_model == "ko" and cost_frame is None:
        raise RuntimeError(f"{spec.name}: cost_model='ko' but no cost frame "
                           "was supplied — refusing to silently charge flat 25")

    w = pd.Series(dtype=float)      # invested weights entering the month
    cash = 1.0
    records: list[dict] = []
    n_rebal = 0
    n_delist_liq = 0
    n_skipped = 0
    since_rebal = 10 ** 6           # force a rebalance on the first tradable month

    for test_m in test_months:
        pos = months.get_loc(test_m)
        if pos == 0:
            continue
        formation_m = months[pos - 1]
        realized = ret.loc[test_m]

        # ── forced liquidation of names with no return this month ───────────
        traded = 0.0
        cost = 0.0
        stub_pnl = 0.0
        if len(w):
            dead = w.index[realized.reindex(w.index).isna()]
            if len(dead):
                stub = pd.Series(0.0, index=dead)
                if delist_stub is not None and test_m in delist_stub.index:
                    stub = (delist_stub.loc[test_m].reindex(dead)
                            .fillna(0.0).astype(float))
                stub_pnl = float((w.loc[dead] * stub).sum())
                dead_w = float(w.loc[dead].sum()) + stub_pnl
                traded += float(w.loc[dead].sum())
                cost += _cost_of(w.loc[dead], formation_m, spec, flat_bps,
                                 cost_frame)
                cash += dead_w
                w = w.drop(dead)
                n_delist_liq += len(dead)

        # ── rebalance decision ──────────────────────────────────────────────
        since_rebal += 1
        want_rebal = since_rebal >= spec.rebalance_months
        risk_on = True if regime_on is None else bool(
            regime_on.get(formation_m, True))

        if want_rebal:
            elig_row = eligible.loc[formation_m]
            s = score.loc[formation_m]
            s = s[elig_row.reindex(s.index).fillna(False).to_numpy()].dropna()
            if len(s) < spec.min_names:
                n_skipped += 1
            else:
                target = (_target_weights(s, w.index, spec) if risk_on
                          else pd.Series(dtype=float))
                allw = w.index.union(target.index)
                delta = (target.reindex(allw, fill_value=0.0)
                         - w.reindex(allw, fill_value=0.0))
                traded += float(delta.abs().sum())
                cost += _cost_of(delta.abs(), formation_m, spec, flat_bps,
                                 cost_frame)
                cash = 1.0 - float(target.sum()) if len(target) else 1.0
                w = target
                since_rebal = 0
                n_rebal += 1

        # ── realize the month ───────────────────────────────────────────────
        held_in = w.copy()          # weights entering the month, pre-drift
        r = realized.reindex(w.index).fillna(0.0) if len(w) else pd.Series(dtype=float)
        equity_ret = float((w * r).sum())
        rf_m = float(rf.get(test_m, 0.0))
        gross = equity_ret + cash * rf_m + stub_pnl
        net = gross - cost

        # ── drift weights into next month ───────────────────────────────────
        if len(w):
            w = w * (1.0 + r)
        cash = cash * (1.0 + rf_m)
        total = float(w.sum()) + cash
        if total <= 0:
            raise RuntimeError(f"{spec.name}: portfolio value hit zero at {test_m}")
        w, cash = w / total, cash / total

        # Pre-inception months (universe too thin to establish the book yet)
        # are NOT performance: a small-cap strategy sitting in cash in 1965
        # because the segment does not exist would otherwise book 17 years of
        # bill returns against a compounding equity benchmark. The scorecard's
        # window therefore starts at the book's inception, and says so.
        if n_rebal == 0 and not len(w):
            continue

        records.append({
            "month": test_m, "gross": gross, "net": net, "cost": cost,
            "traded": traded, "n_held": int(len(w)), "cash_w": cash,
            "risk_on": risk_on,
        })
        if holdings_out is not None:
            holdings_out.append({"formation": formation_m, "test": test_m,
                                 "weights": held_in})

    if not records:
        raise RuntimeError(
            f"{spec.name}: the book was never established — no month in "
            f"{spec.first_month}..{spec.last_month} had {spec.min_names}+ "
            "eligible names. Fail loud rather than report an all-cash 'strategy'.")
    monthly = pd.DataFrame(records).set_index("month")
    diag = {
        "months": len(monthly), "rebalances": n_rebal,
        "months_skipped_thin_universe": n_skipped,
        "forced_liquidations": n_delist_liq,
        "mean_n_held": round(float(monthly["n_held"].mean()), 1),
        "mean_cash_weight": round(float(monthly["cash_w"].mean()), 4),
        "turnover_1way_annual": round(
            float(monthly["traded"].sum()) / 2 / (len(monthly) / 12), 3),
        "cost_drag_annual_bps": round(
            float(monthly["cost"].sum()) / (len(monthly) / 12) * 1e4, 1),
    }
    if n_skipped > 0.25 * len(monthly):
        logger.warning("%s: %d/%d months skipped for thin universe",
                       spec.name, n_skipped, len(monthly))
    return {"monthly": monthly, "diag": diag}


def _cost_of(traded_by_name: pd.Series, formation_m, spec: StrategySpec,
             flat_bps: float | None, cost_frame: pd.DataFrame | None) -> float:
    if not len(traded_by_name):
        return 0.0
    if flat_bps is not None:
        return float(traded_by_name.abs().sum()) * flat_bps / 1e4
    row = cost_frame.loc[formation_m].reindex(traded_by_name.index)
    row = row.fillna(25.0)   # KO frame gaps fall back to the punitive flat rate
    return float((traded_by_name.abs() * row).sum()) / 1e4


def buy_and_hold_universe(panel, eligible: pd.DataFrame, spec: StrategySpec,
                          rf: pd.Series) -> pd.Series:
    """Equal-weight, monthly-rebalanced return of the eligible universe.

    The 'could a monkey have done this' control: same universe, same
    eligibility, no selection. Costs are NOT charged (it is a reference index,
    and charging it turnover would flatter the strategy)."""
    ret = panel.monthly_ret
    months = ret.index
    lo, hi = pd.Timestamp(spec.first_month), pd.Timestamp(spec.last_month)
    out = {}
    for m in months:
        if not (lo <= m <= hi):
            continue
        pos = months.get_loc(m)
        if pos == 0:
            continue
        elig_row = eligible.loc[months[pos - 1]]
        names = elig_row[elig_row].index
        r = ret.loc[m].reindex(names).dropna()
        if len(r) >= spec.min_names:
            out[m] = float(r.mean())
    return pd.Series(out, name="ew_universe")
