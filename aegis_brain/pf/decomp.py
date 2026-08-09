"""PF-4 — take a book apart and find out what is actually paying for it.

`PF-PROF-COMPOSITE-150` prints +4.67 %/yr net excess over 40.2 years. Three
independent external reviews made the same charge: a monthly-rebalanced,
equal-weight, small-cap book harvests several premia that have nothing to do
with the profitability signal it is named after, and nobody had ever separated
them. This module is the separation.

The instruments, and what each one removes:

  ew_universe                 everything shared with a no-information draw from
                              the identical eligible universe — the equal-weight
                              rebalancing premium (Plyakha-Uppal-Vilkov), the
                              universe's size and illiquidity premia, and its
                              calendar effects. The primary metric regresses the
                              SELF-FINANCING series (book − this) on FF5+UMD.

  smallcap_prof_factor        a properly constructed small-cap profitability
                              factor. RMW is value-weighted and dominated by the
                              largest names, so a low RMW loading on an
                              equal-weight microcap book is mechanically
                              expected and is NOT evidence of non-spanning. This
                              is the benchmark that can actually kill the alpha.

  char_matched_placebo        random books matched cell-by-cell on dollar
                              volume, momentum and book-to-market, with ONLY the
                              profitability dimension randomized, and with
                              turnover matched BY CONSTRUCTION rather than by
                              fitting an AR(1) rho. The turnover-matched placebo
                              already in `controls.py` is matched on the wrong
                              dimension: a random 150 names differ from a
                              profitability-selected 150 in size and liquidity,
                              so it is not exchangeable with the book and never
                              was a fair gate.

  era_cost_frame              a mechanical tick-size floor on the half-spread.
                              A flat 25 bps on a $4 stock in 1985, when the
                              minimum tick was $1/8, is not a cost model; it is
                              a wish. NOTE this frame is a LOWER bound: the
                              spine carries no daily high/low, so Corwin-Schultz
                              and Abdi-Ranaldo are not computable here, and any
                              excess left standing after this arm is an upper
                              bound on the truth.

  marginal_rank_window        books built from ranks 1-10, 11-20, … 141-150 held
                              separately. If ordering inside the selected set
                              carries nothing, their ALPHAS are flat. Raw excess
                              is not the test, because names 100-150 are smaller
                              and less liquid and therefore carry more size and
                              illiquidity premium — a genuine decline in signal
                              quality offset by rising premia produces exactly
                              the flat raw curve we already banked.

Nothing here adjudicates. `TRIALS/PREREG_PF4_DECOMPOSITION.md` holds the
decision rule, and it was committed before the first line of this file ran.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis_brain.harness.benchmark import factor_alpha, newey_west_tstat
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.spec import StrategySpec

logger = logging.getLogger(__name__)

FF6 = ["mktrf", "smb", "hml", "rmw", "cma", "umd"]

# US minimum tick regimes. Half-tick is the smallest possible half-spread, so
# these are hard mechanical floors, not estimates.
TICK_REGIMES: tuple[tuple[str, float], ...] = (
    ("1997-06-30", 0.125),      # eighths, through the June 1997 move to sixteenths
    ("2001-03-31", 0.0625),     # sixteenths, through decimalization
    ("2100-01-01", 0.01),       # decimals
)


# ── factor machinery ────────────────────────────────────────────────────────
def alpha_report(series: pd.Series, factors: pd.DataFrame, cols: list[str],
                 *, rf: pd.Series | None = None, lags: int = 12) -> dict:
    """Annualized alpha + NW t + betas for a return series.

    `rf` is subtracted only when the series is a GROSS holding return. A
    self-financing (long minus long) series is already an excess return and must
    NOT have the bill rate taken off it again — doing so is the classic way to
    manufacture negative alpha out of nothing.
    """
    s = series.dropna()
    if rf is not None:
        s = (s - rf.reindex(s.index)).dropna()
    f = factors.reindex(s.index)
    use = [c for c in cols if c in f.columns]
    keep = f[use].notna().all(axis=1)
    s, f = s[keep], f.loc[keep, use]
    if len(s) < 24:
        return {"n": len(s), "note": "fewer than 24 usable months"}
    a = factor_alpha(s, f, use, lags=lags)
    return {
        "n": len(s),
        "ann_alpha": (round(a["ann_alpha"], 4)
                      if a.get("ann_alpha") is not None else None),
        "t_alpha": round(a["t_alpha"], 2) if a.get("t_alpha") is not None else None,
        "betas": {k: round(v, 3) for k, v in a.get("betas", {}).items()},
    }


def nw_t(x: pd.Series, lags: int = 12) -> float | None:
    r = newey_west_tstat(pd.Series(x).dropna(), lags=lags)
    return None if r.get("t") is None else round(float(r["t"]), 2)


def mde_annualized(x: pd.Series, t_bar: float = 2.0) -> float:
    """Minimum effect this series could have detected at t = t_bar, annualized.

    Printed next to every null. A null that does not carry this number is a
    claim of zero, which the standard forbids.
    """
    s = pd.Series(x).dropna()
    return round(float(t_bar * s.std(ddof=1) / np.sqrt(len(s)) * 12), 4)


# ── costs ───────────────────────────────────────────────────────────────────
def tick_floor_bps(panel) -> pd.DataFrame:
    """Month × permno half-spread FLOOR in bps, from the minimum tick.

    half-spread >= (tick / 2) / price. Nothing about a real market can be
    cheaper than this, so it is a bound rather than a model.
    """
    prc = panel.month_end_price.where(panel.month_end_price > 0)
    tick = pd.Series(index=prc.index, dtype=float)
    prev = pd.Timestamp("1900-01-01")
    for end, size in TICK_REGIMES:
        end_ts = pd.Timestamp(end)
        tick.loc[(tick.index > prev) & (tick.index <= end_ts)] = size
        prev = end_ts
    floor = (tick.to_numpy()[:, None] / 2.0) / prc.to_numpy() * 1e4
    return pd.DataFrame(floor, index=prc.index, columns=prc.columns)


def era_cost_frame(panel, base_bps: float = 25.0,
                   ko_frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """The cost frame PF-4 charges: max(base or KO, mechanical tick floor)."""
    floor = tick_floor_bps(panel)
    base = pd.DataFrame(base_bps, index=floor.index, columns=floor.columns)
    if ko_frame is not None:
        base = ko_frame.reindex_like(floor).fillna(base_bps)
    out = np.fmax(base.to_numpy(), floor.to_numpy())
    return pd.DataFrame(out, index=floor.index, columns=floor.columns)


# ── universe-level constructions ────────────────────────────────────────────
def amihud(panel, window: int = 12) -> pd.DataFrame:
    """Amihud illiquidity: rolling mean of |return| / dollar volume."""
    dv = panel.monthly_dollar_vol.where(panel.monthly_dollar_vol > 0)
    raw = panel.monthly_ret.abs() / dv
    return raw.rolling(window, min_periods=max(window // 2, 3)).mean()


def long_short_factor(score: pd.DataFrame, eligible: pd.DataFrame,
                      ret: pd.DataFrame, *, frac: float = 0.3,
                      min_names: int = 30) -> pd.Series:
    """Equal-weight top-frac minus bottom-frac of `score`, inside `eligible`.

    Formation month m → realized month m+1, the same convention as every book in
    this module. Returned as a self-financing monthly series.
    """
    months = ret.index
    out: dict[pd.Timestamp, float] = {}
    for i in range(1, len(months)):
        fm, tm = months[i - 1], months[i]
        if fm not in score.index or fm not in eligible.index:
            continue
        s = score.loc[fm]
        s = s[eligible.loc[fm].reindex(s.index).fillna(False).to_numpy()].dropna()
        k = int(len(s) * frac)
        if k < min_names:
            continue
        srt = s.sort_values(ascending=False)
        r = ret.loc[tm]
        hi = r.reindex(srt.index[:k]).dropna()
        lo = r.reindex(srt.index[-k:]).dropna()
        if len(hi) < min_names or len(lo) < min_names:
            continue
        out[tm] = float(hi.mean() - lo.mean())
    return pd.Series(out, name="smallprof").sort_index()


def indexed_eligibility(panel, base_dollar_vol: float, anchor: str,
                        min_price: float = 1.0) -> pd.DataFrame:
    """Eligibility with the dollar-volume floor indexed to market liquidity.

    The production floor is a NOMINAL $200k/month that was never inflation- or
    market-indexed. In 1963 only ~215 names in the entire CRSP universe clear
    it, all of them large caps, so the small segment is empty by construction
    and every small-segment strategy silently loses 19 years of the panel.

    Here the floor is scaled by the panel's own aggregate dollar volume relative
    to `anchor`. That deflator uses a future-dated anchor month and is therefore
    NOT point-in-time — which is why anything computed on it is reported and can
    never decide.
    """
    dv = panel.monthly_dollar_vol
    total = dv.sum(axis=1)
    a = float(total.loc[:pd.Timestamp(anchor)].iloc[-1])
    scale = (total / a).clip(lower=1e-6)
    floor = scale * base_dollar_vol
    ok_dv = dv.ge(floor, axis=0)
    return (ok_dv & (panel.month_end_price >= min_price)).fillna(False).astype(bool)


# ── the characteristic-matched placebo ──────────────────────────────────────
def _decile(frame: pd.DataFrame, elig: pd.DataFrame, q: int = 10) -> pd.DataFrame:
    """Cross-sectional decile rank (1..q) inside the eligible set, per month."""
    masked = frame.where(elig)
    r = masked.rank(axis=1, pct=True)
    return np.ceil(r * q).clip(1, q)


def build_cells(panel, lib, eligible: pd.DataFrame, *, q: int = 10
                ) -> tuple[pd.DataFrame, dict]:
    """Characteristic cell id per name per month: dvol × momentum × B/M decile.

    The cell is what the placebo holds FIXED. Randomizing within it means the
    control book has the same size, momentum and value profile as the real book
    and differs only in profitability — which is the one dimension the strategy
    claims to use.
    """
    dv = _decile(panel.monthly_dollar_vol, eligible, q)
    mom = _decile(lib.get("native:mom_12_1"), eligible, q)
    bm = _decile(lib.get("osap:BM"), eligible, q)
    # a name missing momentum or B/M still has a size decile; collapse the
    # missing dimension to 0 rather than dropping the name, so the placebo can
    # always find it a partner and the match degrades visibly instead of the
    # sample silently shrinking
    cell = (dv.fillna(0) * 100 + mom.fillna(0) * 10 + bm.fillna(0))
    cell = cell.where(eligible)
    diag = {"q": q,
            "mean_cells_occupied": round(float(
                cell.apply(lambda r: r.dropna().nunique(), axis=1).mean()), 1),
            "frac_names_full_match": round(float(
                (dv.notna() & mom.notna() & bm.notna()).where(eligible).sum().sum()
                / max(eligible.sum().sum(), 1)), 4)}
    return cell, diag


def char_matched_scores(holdings: list[dict], cell: pd.DataFrame,
                        eligible: pd.DataFrame, *, seed: int) -> pd.DataFrame:
    """A score frame whose top-N is a characteristic-matched shadow of the book.

    For every name the real book holds, a partner is drawn from the same
    characteristic cell and KEPT for exactly as long as the real name is held.
    Turnover therefore matches by construction rather than by fitting a rho —
    the substitution is one-for-one, so the control trades when and only when
    the book trades.
    """
    rng = np.random.default_rng(seed)
    months = cell.index
    score = pd.DataFrame(np.nan, index=months, columns=cell.columns,
                         dtype=np.float32)
    mapping: dict[str, str] = {}
    n_fallback = 0
    n_assigned = 0

    # per-month cell -> members, built lazily and only for the months used
    for h in holdings:
        fm = h["formation"]
        held = list(h["weights"].index)
        row_cell = cell.loc[fm]
        row_elig = eligible.loc[fm]
        pool = row_cell[row_elig.reindex(row_cell.index).fillna(False).to_numpy()].dropna()
        by_cell: dict[float, np.ndarray] = {
            c: g.index.to_numpy() for c, g in pool.groupby(pool)}
        all_names = pool.index.to_numpy()

        mapping = {k: v for k, v in mapping.items() if k in set(held)}
        used = set(mapping.values())
        for name in held:
            if name in mapping:
                continue
            c = row_cell.get(name, np.nan)
            cands = by_cell.get(c, all_names) if c == c else all_names
            free = [x for x in cands if x not in used]
            if not free:
                free = [x for x in all_names if x not in used]
                n_fallback += 1
            if not free:                       # universe exhausted — impossible
                continue                       # at N=150 in a 2000-name segment
            pick = str(free[rng.integers(0, len(free))])
            mapping[name] = pick
            used.add(pick)
            n_assigned += 1
        subs = list(mapping.values())
        if subs:
            score.loc[fm, subs] = np.arange(len(subs), 0, -1, dtype=np.float32)
    logger.info("char-matched draw seed=%d: %d assignments, %d cell fallbacks",
                seed, n_assigned, n_fallback)
    score.attrs["fallback_frac"] = round(n_fallback / max(n_assigned, 1), 4)
    return score


def char_matched_placebo(panel, eligible, spec: StrategySpec, rf, cost_frame,
                         bench: pd.Series, holdings: list[dict],
                         cell: pd.DataFrame, *, n_draws: int,
                         seed: int) -> dict:
    """Distribution of net excess CAGR for characteristic-matched random books."""
    rows = []
    for i in range(n_draws):
        sc = char_matched_scores(holdings, cell, eligible, seed=seed + i)
        out = run_book(panel, sc, eligible, spec, rf, cost_frame)
        m = out["monthly"]
        b = bench.reindex(m.index)
        rows.append({"draw": i,
                     "excess_cagr_net": annualize(m["net"]) - annualize(b),
                     "excess_cagr_gross": annualize(m["gross"]) - annualize(b),
                     "turnover": out["diag"]["turnover_1way_annual"],
                     "months": len(m),
                     "fallback_frac": sc.attrs.get("fallback_frac", 0.0)})
        if (i + 1) % 10 == 0:
            logger.info("  char placebo %d/%d", i + 1, n_draws)
    df = pd.DataFrame(rows)
    return {
        "n_draws": n_draws, "seed": seed,
        "matched_on": "dollar-volume decile x 12-1 momentum decile x B/M decile",
        "substitution": "one-for-one, held as long as the real name is held",
        "placebo_turnover_mean": round(float(df["turnover"].mean()), 3),
        "mean_cell_fallback_frac": round(float(df["fallback_frac"].mean()), 4),
        "turnover_caveat": (
            "the substitution is one-for-one, but a substitute that loses "
            "eligibility must be replaced, so the control's realized turnover "
            "runs HOT relative to the book. Charging it more costs than the "
            "strategy would flatter the strategy - the exact error class found "
            "in the NIGHT-3 placebo. The GROSS band is therefore the primary "
            "statistic here and the net band is reported beside it."),
        "excess_cagr_gross": _band(df["excess_cagr_gross"]),
        "excess_cagr_net": _band(df["excess_cagr_net"]),
        "draws_gross": [round(float(v), 5) for v in df["excess_cagr_gross"]],
        "draws_net": [round(float(v), 5) for v in df["excess_cagr_net"]],
    }


def _band(ex: pd.Series) -> dict:
    return {"mean": round(float(ex.mean()), 4),
            "sd": round(float(ex.std(ddof=1)), 4),
            "p50": round(float(ex.quantile(0.5)), 4),
            "p95": round(float(ex.quantile(0.95)), 4),
            "max": round(float(ex.max()), 4)}


# ── decompositions on a finished book ───────────────────────────────────────
def calendar_split(net: pd.Series, bench: pd.Series) -> dict:
    """January vs the rest. For an EW small-cap book this is not a formality."""
    out = {}
    for label, mask in (("january", net.index.month == 1),
                        ("non_january", net.index.month != 1)):
        s, b = net[mask], bench[mask]
        # annualize over the ELAPSED calendar span, not the count of kept months
        yrs = len(net) / 12.0
        out[label] = {
            "months": int(mask.sum()),
            "contribution_to_terminal_wealth_x": round(
                float((1 + s).prod()), 3),
            "benchmark_contribution_x": round(float((1 + b).prod()), 3),
            "excess_log_growth_annual": round(float(
                (np.log1p(s).sum() - np.log1p(b).sum()) / yrs), 4),
            "mean_monthly_excess": round(float((s - b).mean()), 5),
            "t_excess": nw_t(s - b),
        }
    tot = sum(v["excess_log_growth_annual"] for v in out.values())
    for k in out:
        out[k]["share_of_excess"] = (round(out[k]["excess_log_growth_annual"]
                                           / tot, 3) if tot else None)
    out["_note"] = ("excess_log_growth_annual splits ADDITIVELY into the full "
                    "book's log excess growth, which is why the shares sum to 1; "
                    "the two rows are not each other's counterfactual")
    return out


def event_time_profile(holdings: list[dict], ret: pd.DataFrame,
                       bench: pd.Series) -> dict:
    """Excess return by months-of-continuous-membership bucket, plus exit hazard.

    If the premium accrues late, monthly rebalancing is destroying it and an
    annual-hold version is both better and far cheaper.
    """
    buckets = ((1, 6), (7, 12), (13, 24), (25, 10 ** 6))
    labels = ["m1_6", "m7_12", "m13_24", "m25_plus"]
    tenure: dict[str, int] = {}
    rows: dict[str, dict[pd.Timestamp, float]] = {k: {} for k in labels}
    at_risk = {k: 0 for k in labels}
    exited = {k: 0 for k in labels}

    def bucket_of(t: int) -> str:
        for (lo, hi), lab in zip(buckets, labels):
            if lo <= t <= hi:
                return lab
        return labels[-1]

    for i, h in enumerate(holdings):
        held = set(h["weights"].index)
        for name in list(tenure):
            if name not in held:
                tenure.pop(name)
        for name in held:
            tenure[name] = tenure.get(name, 0) + 1
        by_bucket: dict[str, list[str]] = {k: [] for k in labels}
        for name in held:
            by_bucket[bucket_of(tenure[name])].append(name)

        r = ret.loc[h["test"]]
        nxt = set(holdings[i + 1]["weights"].index) if i + 1 < len(holdings) else None
        for lab, names in by_bucket.items():
            if len(names) >= 5:
                v = r.reindex(names).dropna()
                if len(v) >= 5:
                    rows[lab][h["test"]] = float(v.mean())
            if nxt is not None:
                at_risk[lab] += len(names)
                exited[lab] += sum(1 for n in names if n not in nxt)

    out = {}
    for lab in labels:
        s = pd.Series(rows[lab]).sort_index()
        entry = {"months": len(s),
                 "monthly_exit_hazard": (round(exited[lab] / at_risk[lab], 4)
                                         if at_risk[lab] else None),
                 "name_months": at_risk[lab]}
        if len(s) >= 24:
            b = bench.reindex(s.index)
            entry.update({"cagr": round(annualize(s), 4),
                          "excess_cagr": round(annualize(s) - annualize(b), 4),
                          "t_excess": nw_t(s - b),
                          "mde_at_t2": mde_annualized(s - b)})
        else:
            entry["note"] = "fewer than 24 months — reported, not interpreted"
        out[lab] = entry
    out["_note"] = ("gross of costs: these are sub-book holding returns, not "
                    "tradable portfolios. The comparison across buckets is the "
                    "point; their levels are not net numbers.")
    return out


def rank_window_score(score: pd.DataFrame, eligible: pd.DataFrame,
                      lo: int, hi: int) -> pd.DataFrame:
    """Score frame whose only non-NaN entries are ranks [lo, hi] of the original.

    Used for the marginal-decile books. Ranks are 1-based and inclusive.
    """
    masked = score.where(eligible.reindex_like(score).fillna(False))
    r = masked.rank(axis=1, ascending=False, method="first")
    keep = (r >= lo) & (r <= hi)
    return masked.where(keep)
