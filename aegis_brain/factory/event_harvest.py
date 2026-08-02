"""Cohort-controlled monthly harvest test — TRIAL-EVENT-13DG-HARVEST, and its
one authorised successor TRIAL-EVENT-13DG-HARVEST2 (see the section at the
bottom of this file; the successor changes the control-matching rule and
NOTHING else, reusing every accounting function above it by import).

Spec frozen 2026-08-02 (TRIALS/TRIAL-EVENT-13DG-HARVEST.md, module commit
0951193, BEFORE this file existed). Candidate 178, one arm, one shot.

WHAT THIS EXISTS TO FIX. The book stage (NEG_RESULTS 29, book extension) asked
whether a monthly account could harvest the 13D drift and answered "no" —
but its own placebo showed it had measured the wrong thing: random filing
dates on the same permnos reproduced the whole negative excess, because the
registered benchmark was the EW eligible universe and activists target
laggards. An event book benchmarked against an unmatched universe measures
COHORT SELECTION, not event information.

The correction is structural, not verbal. Two things:

  1. THE BENCHMARK IS THE PARENT TRIAL'S MATCHED CONTROL, REUSED VERBATIM.
     `match_controls` in `factory/daily_events.py` is CALLED, not
     reimplemented — same segment, same calendar month, nearest dollar-volume
     rank, no event within +/-60 calendar days, matched at the ORIGINAL FILING
     DATE. Copying that rule into this module would let it drift; a test pins
     the identity anyway.
  2. THE PLACEBO IS A GATE, NOT A DIAGNOSTIC. See `gated_run` below. The real
     number is not computed until the gate has passed, and compute-order is
     the tamper-evidence: a design that cannot pass its own placebo does not
     get to produce a tradability verdict.

THE WINDOW. Event and control are measured over the IDENTICAL window: from the
first month-end on or after the filing date (the entry), through the third
month-end after entry. Under `factory/explore.py`'s convention a holding fixed
at formation month-end M earns month M+1's return, so a 3-month hold entered at
month index i0 earns the returns of months i0+1, i0+2, i0+3 — the book never
touches a return from the month in which it entered. This forfeits the
announcement pop and part of +1..+20 BY DESIGN; the harvestable remainder is
the thing under test.

MECHANICAL PLUMBING (the freeze is silent, precedent followed, disclosed):

  * Holding-period returns COMPOUND (prod(1+r)-1). That is what an account
    earns over three months; the daily CAR harness sums because it differences
    daily legs, which is a different object. Declared here, before the run.
  * A missing monthly return inside a window contributes 0 (the name delisted,
    the position is in cash). The fill fraction is measured and reported, as
    in `daily_events.compute_cars`.
  * COSTS HIT THE EVENT LEG ONLY, per the freeze: a KO half-spread charged at
    the entry month-end and again at the exit month-end (a round trip), per
    name, size-aware, with the flat guard as the fallback for a name missing
    from the spread frame. The control is a paper benchmark and pays nothing —
    conservative against us.
  * THE EXPLORE WALL BINDS THE WINDOW, NOT ONLY THE EVENT. An event whose
    third month-end after entry falls after 2018-12-31 produces NO measurement
    and is counted. The parent CAR trial let a +60-trading-day window spill
    past the boundary; this stage does not, because its window is 3 months
    wide and the wall is the one rule the programme never trades against.
    Attrition is reported rather than assumed immaterial.
  * Eligibility (factory universe, dollar-volume rank <= 3000) is checked on
    the EVENT name at its entry month-end, exactly as in the book stage. The
    control is NOT separately re-screened: it is whatever the parent's rule
    assigns, and re-screening it would be a deviation from "verbatim".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from aegis_brain.factory import daily_events as de
from aegis_brain.factory.event_book import entry_index

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HarvestConfig:
    """Frozen in TRIAL-EVENT-13DG-HARVEST — do not tune."""

    hold_months: int = 3
    max_rank: int = 3000                 # the factory's small-segment ceiling
    flat_cost_bps_one_way: float = 25.0  # guard arm + fallback for missing KO
    explore_start: str = "2004-01-01"
    explore_end: str = "2018-12-31"      # explore/confirm wall; never crossed
    exclusion_days: int = de.CONTROL_EXCLUSION_DAYS   # the parent's +/-60cd
    placebo_seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    placebo_t_bar: float = 2.0           # pooled |t| >= this -> NO CONCLUSION
    bar_t: float = 1.5                   # PASS bar on the real arm


# ── the control rule: the parent's, called rather than copied ────────────────
def match_parent_controls(events: pd.DataFrame, daily_panel: de.DailyEventPanel,
                          cfg: HarvestConfig | None = None) -> pd.DataFrame:
    """TRIAL-EVENT-13DG's control rule, VERBATIM, at the ORIGINAL filing date.

    This is a one-line delegation on purpose: the matching fields (segment,
    calendar month, nearest dollar-volume rank) and the +/-60 calendar-day
    contamination exclusion must be the same objects the parent trial used, or
    this stage is not measuring against the controls that established the
    effect.
    """
    cfg = cfg or HarvestConfig()
    return de.match_controls(events, daily_panel, cfg.exclusion_days)


# ── the two legs over one identical window ───────────────────────────────────
def compute_legs(matched: pd.DataFrame, panel, eligible: pd.DataFrame,
                 spread: pd.DataFrame | None,
                 cfg: HarvestConfig | None = None) -> tuple[pd.DataFrame, dict]:
    """Per-event holding-period returns for both legs, plus the differenced net.

    `spread`: [month x sym] ONE-WAY cost in bps (the KO half-spread frame).
    None means the flat guard everywhere; pass a zero frame for the zero-cost
    bound. Costs are charged to the EVENT leg only, at entry and at exit.

    Returns (per-event frame, attrition diagnostics).
    """
    cfg = cfg or HarvestConfig()
    m = matched.dropna(subset=["control_permno"]).copy()
    months = panel.monthly_ret.index
    cols = {c: i for i, c in enumerate(panel.monthly_ret.columns)}
    R = panel.monthly_ret.to_numpy(dtype=float)
    E = eligible.to_numpy(dtype=bool)
    S = None if spread is None else spread.to_numpy(dtype=float)
    hold = cfg.hold_months
    wall = pd.Timestamp(cfg.explore_end)

    diag = {"events_in": int(len(matched)), "no_control": int(
        len(matched) - len(m)), "not_in_panel": 0, "control_not_in_panel": 0,
        "no_entry_month": 0, "window_past_panel": 0, "window_past_explore": 0,
        "ineligible_at_entry": 0, "measured": 0}
    ev_missing = ct_missing = ev_cells = 0

    rows = []
    for permno, ctrl, dt in zip(m["permno"].to_numpy(),
                                m["control_permno"].to_numpy(),
                                pd.to_datetime(m["event_date"]).to_numpy()):
        j = cols.get(str(int(permno)))
        if j is None:
            diag["not_in_panel"] += 1
            continue
        jc = cols.get(str(int(ctrl)))
        if jc is None:
            diag["control_not_in_panel"] += 1
            continue
        i0 = entry_index(pd.Timestamp(dt), months)
        if i0 is None:
            diag["no_entry_month"] += 1
            continue
        if i0 + hold >= len(months):
            diag["window_past_panel"] += 1
            continue
        if months[i0 + hold] > wall:
            diag["window_past_explore"] += 1          # the wall binds the window
            continue
        if not bool(E[i0, j]):
            diag["ineligible_at_entry"] += 1
            continue

        sl = slice(i0 + 1, i0 + 1 + hold)             # identical for both legs
        ev_r, ct_r = R[sl, j], R[sl, jc]
        ev_cells += hold
        ev_missing += int(np.isnan(ev_r).sum())
        ct_missing += int(np.isnan(ct_r).sum())
        ev_r, ct_r = np.nan_to_num(ev_r), np.nan_to_num(ct_r)

        if S is None:
            entry_bps = exit_bps = cfg.flat_cost_bps_one_way
        else:
            entry_bps = S[i0, j]
            exit_bps = S[i0 + hold, j]
            if not np.isfinite(entry_bps):
                entry_bps = cfg.flat_cost_bps_one_way
            if not np.isfinite(exit_bps):
                exit_bps = cfg.flat_cost_bps_one_way
        cost = (float(entry_bps) + float(exit_bps)) / 1e4

        ev_gross = float(np.prod(1.0 + ev_r) - 1.0)
        ct_gross = float(np.prod(1.0 + ct_r) - 1.0)
        rows.append({
            "permno": int(permno), "control_permno": int(ctrl),
            "event_date": pd.Timestamp(dt),
            "entry_month": months[i0].to_period("M"),
            "exit_month": months[i0 + hold].to_period("M"),
            "event_gross": ev_gross, "control_gross": ct_gross,
            "cost": cost, "event_net": ev_gross - cost,
            "diff_gross": ev_gross - ct_gross,
            "diff_net": ev_gross - cost - ct_gross,
        })
        diag["measured"] += 1

    out = pd.DataFrame(rows)
    diag["event_return_cells_missing_frac"] = (
        round(ev_missing / ev_cells, 4) if ev_cells else float("nan"))
    diag["control_return_cells_missing_frac"] = (
        round(ct_missing / ev_cells, 4) if ev_cells else float("nan"))
    logger.info("harvest legs: %s", diag)
    return out, diag


def summarise_legs(legs: pd.DataFrame,
                   cfg: HarvestConfig | None = None) -> dict:
    """The deciding number: mean differenced NET return, t clustered by ENTRY
    month. `de.clustered_t` is reused so the inference is the parent's."""
    cfg = cfg or HarvestConfig()
    if legs.empty:
        raise ValueError("no event produced a measurement")
    net = de.clustered_t(legs["diff_net"], legs["entry_month"].astype(str))
    gross = de.clustered_t(legs["diff_gross"], legs["entry_month"].astype(str))
    return {
        "n_events": net["n"], "n_entry_months": net["n_clusters"],
        "event_leg_bps": round(float(legs["event_gross"].mean()) * 1e4, 1),
        "control_leg_bps": round(float(legs["control_gross"].mean()) * 1e4, 1),
        "mean_cost_bps": round(float(legs["cost"].mean()) * 1e4, 1),
        "diff_net_bps": round(net["mean"] * 1e4, 1),
        "diff_net_bps_per_month": round(
            net["mean"] * 1e4 / cfg.hold_months, 1),
        "t_clustered": round(net["t_clustered"], 2),
        "t_iid": round(net["t_iid"], 2),
        "diff_gross_bps": round(gross["mean"] * 1e4, 1),
        "t_gross_clustered": round(gross["t_clustered"], 2),
    }


# ── the placebo gate ─────────────────────────────────────────────────────────
def redraw_filing_dates(events: pd.DataFrame, seed: int,
                        cfg: HarvestConfig | None = None) -> pd.DataFrame:
    """Same permnos, same per-permno event count, filing dates redrawn
    uniformly at random across the explore window.

    The book stage's diagnostic, promoted to a gate. Each row keeps its permno
    and gets a new date, so every permno's event count is preserved by
    construction — the cohort is identical and only the timing is destroyed.
    """
    cfg = cfg or HarvestConfig()
    rng = np.random.default_rng(seed)
    lo = pd.Timestamp(cfg.explore_start)
    span = (pd.Timestamp(cfg.explore_end) - lo).days
    out = events.copy()
    out["event_date"] = lo + pd.to_timedelta(
        rng.integers(0, span + 1, size=len(out)), unit="D")
    return out.sort_values(["permno", "event_date"], ignore_index=True)


def placebo_gate(pipeline, events: pd.DataFrame,
                 cfg: HarvestConfig | None = None) -> dict:
    """Run the identical pipeline on five random-date redraws and read it FIRST.

    `pipeline(events) -> per-event legs frame` is the same callable the real
    arm uses. The pooled statistic clusters on the entry month ACROSS seeds,
    because five draws landing in the same month share that month's shock.
    """
    cfg = cfg or HarvestConfig()
    per_seed, pooled = {}, []
    for seed in cfg.placebo_seeds:
        legs = pipeline(redraw_filing_dates(events, seed, cfg))
        per_seed[seed] = summarise_legs(legs, cfg)
        pooled.append(legs.assign(seed=seed))
    allrows = pd.concat(pooled, ignore_index=True)
    stat = de.clustered_t(allrows["diff_net"], allrows["entry_month"].astype(str))
    return {
        "per_seed": per_seed,
        "pooled": {
            "n_events": stat["n"], "n_entry_months": stat["n_clusters"],
            "diff_net_bps": round(stat["mean"] * 1e4, 1),
            "diff_net_bps_per_month": round(
                stat["mean"] * 1e4 / cfg.hold_months, 1),
            "t_clustered": round(stat["t_clustered"], 2),
            "t_iid": round(stat["t_iid"], 2),
        },
        "t_bar": cfg.placebo_t_bar,
        "passed": bool(abs(stat["t_clustered"]) < cfg.placebo_t_bar),
    }


def gated_run(gate_fn, real_fn, cfg: HarvestConfig | None = None) -> dict:
    """THE COMPUTE-ORDER IS THE TAMPER-EVIDENCE.

    `real_fn` is not called — the real number does not exist in this process —
    unless the placebo gate has already passed. A failed gate returns
    NO CONCLUSION with `real` still None, and nothing downstream is readable.
    """
    cfg = cfg or HarvestConfig()
    gate = gate_fn()
    if not gate["passed"]:
        return {"gate": gate, "gate_passed": False, "real": None,
                "verdict": "NO CONCLUSION"}
    return {"gate": gate, "gate_passed": True, "real": real_fn(),
            "verdict": None}


def clears_bar(summary: dict, cfg: HarvestConfig | None = None) -> bool:
    """The frozen PASS bar: differenced net mean > 0 AND clustered t >= 1.5."""
    cfg = cfg or HarvestConfig()
    return bool(summary["diff_net_bps"] > 0
                and summary["t_clustered"] >= cfg.bar_t)


# ═════════════════════════════════════════════════════════════════════════════
# TRIAL-EVENT-13DG-HARVEST2 — candidate 179, TERMINAL for the 13D family.
# Spec frozen 2026-08-02 (TRIALS/TRIAL-EVENT-13DG-HARVEST2.md, module commit
# c3e4f03, BEFORE this section existed).
#
# THE ONLY THING THAT CHANGES IS THE CONTROL-MATCHING RULE. Everything above —
# the window, the legs, the compounding, the event-leg-only cost convention,
# the explore wall binding the window, the redraw, the GATE and the bar — is
# reused as-is by import, not re-derived. That is deliberate: HARVEST's 28 spec
# tests keep pinning the accounting while this section is swapped underneath it.
#
# WHY. HARVEST's gate fired (NEG_RESULTS 30): random-date positions in
# 13D-targeted names lose ~25 bps/mo GROSS to their own liquidity-rank-matched
# controls. Dollar-volume rank is a LIQUIDITY match; within a segment and month
# activist targets are still the size/laggard tail, and the parent's rule never
# touched that. The successor matches on the two traits the null decomposition
# says were missed, and nothing else:
#
#   nearest neighbour in per-month standardised (log market cap, prior 6-month
#   return), BOTH read at the last month-end STRICTLY BEFORE the filing date.
#
# PRE-FILING IS LOAD-BEARING. The cohort trait under control is PRE-filing
# laggardness. A filing on the 15th must not be matched on the cap or the
# 6-month return that includes the month of its own announcement — that would
# absorb the event into the matching variable and match away the thing being
# measured. The characteristic month is therefore i0 - 1, never i0.
#
# MECHANICAL PLUMBING (the freeze is silent; declared here, before the run):
#
#   * PER-MONTH STANDARDISATION POPULATION = the eligible universe in the
#     characteristic month (the factory universe, rank <= max_rank — the pool
#     controls are drawn from). Standardising over ALL names would let micro
#     junk inflate the return dimension's SD and quietly re-weight the metric
#     back toward size, which is the failure being corrected. Moments are taken
#     over eligible names; the transform is applied to every name, so an event
#     that is itself ineligible still has a defined position in the metric.
#   * PRIOR 6-MONTH RETURN COMPOUNDS and requires all six monthly returns
#     present; a name short of six observations has no characteristic and is
#     neither an event nor a candidate that month. No winsorisation is applied
#     (the freeze does not authorise one, and a nearest-neighbour metric is not
#     a regression: an extreme event simply matches the nearest extreme name).
#   * THE +/-60cd CONTAMINATION EXCLUSION IS APPLIED AGAINST THE ARM'S OWN
#     EVENT FRAME, exactly as `daily_events.match_controls` does. The freeze
#     says "no 13D/13G event within +/-60 calendar days" under a heading that
#     reads "What changes, and ONLY this" — the metric. Widening the exclusion
#     to the full banked 13D+13G universe would be a second, stricter change
#     the freeze does not authorise, and it would also break the placebo's
#     symmetry (redrawn arm dates against a fixed real exclusion set).
#   * ONE CONTROL PER EVENT, WITH REPLACEMENT; ties broken by SMALLEST PERMNO,
#     implemented by sorting the candidate pool ascending and taking the first
#     argmin, so the run is reproducible to the row.
#   * An event with no characteristic month (a filing in the panel's first
#     month), no segment that month, or no surviving candidate gets NO control
#     and is counted by `compute_legs` as `no_control` — never silently
#     dropped. Unlike the parent's matcher, events whose segment is missing are
#     RETAINED with a null control rather than vanishing from the frame, so the
#     attrition adds up to the arm.
# ═════════════════════════════════════════════════════════════════════════════

CHAR_LOOKBACK_MONTHS = 6            # prior-return window, frozen in HARVEST2


@dataclass(frozen=True)
class CohortChars:
    """Per-month standardised matching characteristics, [month x sym]."""

    z_cap: pd.DataFrame             # log market cap, z-scored within the month
    z_ret: pd.DataFrame             # prior 6-month return, z-scored likewise


def characteristic_index(filing_date: pd.Timestamp,
                         months: pd.DatetimeIndex) -> int | None:
    """Position of the last month-end STRICTLY BEFORE the filing date.

    The mirror of `event_book.entry_index`, one step back: entry is the first
    month-end on or after the filing, so the last month-end strictly before it
    is always entry - 1. A filing ON a month-end is matched on the PREVIOUS
    month-end's characteristics — it may not see the cap or the return of the
    month it lands in.
    """
    pos = int(months.searchsorted(pd.Timestamp(filing_date), side="left")) - 1
    return pos if pos >= 0 else None


def prior_return_frame(panel, lookback: int = CHAR_LOOKBACK_MONTHS
                       ) -> pd.DataFrame:
    """[month x sym] compounded return over the `lookback` months ENDING at
    that month-end (inclusive). All `lookback` returns must be present."""
    log1p = np.log1p(panel.monthly_ret.astype(float))
    return np.expm1(log1p.rolling(lookback, min_periods=lookback).sum())


def _per_month_z(frame: pd.DataFrame, eligible: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z within each month, moments taken over eligible names."""
    elig = eligible.reindex(index=frame.index, columns=frame.columns,
                            fill_value=False).fillna(False).astype(bool)
    f = frame.where(elig)
    mu = f.mean(axis=1)
    sd = f.std(axis=1, ddof=0).replace(0.0, np.nan)
    return frame.sub(mu, axis=0).div(sd, axis=0)


def cohort_characteristics(panel, eligible: pd.DataFrame,
                           mktcap: pd.DataFrame | None = None,
                           lookback: int = CHAR_LOOKBACK_MONTHS) -> CohortChars:
    """The two matching dimensions, per-month standardised.

    `mktcap` defaults to `rank_dead.market_cap_frame` — the same |month-end
    price| x shrout x 1000 construction `abio.py` and `optsurf.py` use for
    `log_mktcap`, so "market cap" means one thing across the ledger.
    """
    from aegis_brain.factory.rank_dead import market_cap_frame

    mc = market_cap_frame(panel) if mktcap is None else mktcap
    log_cap = np.log(mc.where(mc > 0))
    prior = prior_return_frame(panel, lookback)
    return CohortChars(z_cap=_per_month_z(log_cap, eligible),
                       z_ret=_per_month_z(prior, eligible))


def match_cohort_controls(events: pd.DataFrame, daily_panel: de.DailyEventPanel,
                          chars: CohortChars, eligible: pd.DataFrame,
                          cfg: HarvestConfig | None = None) -> pd.DataFrame:
    """HARVEST2's control rule. Same segment, same calendar month, eligible at
    the entry month-end, no own event within +/-`exclusion_days` calendar days;
    among those, the nearest neighbour in per-month standardised (log market
    cap, prior 6-month return) read at the last month-end BEFORE the filing.

    Returns `events` plus rank/segment/ym and a `control_permno` column, NaN
    where no admissible control exists.
    """
    cfg = cfg or HarvestConfig()
    ev = events.copy()
    ev["event_date"] = pd.to_datetime(ev["event_date"])
    ev["ym"] = ev["event_date"].dt.to_period("M")
    ev = ev.merge(daily_panel.ranks[["permno", "ym", "rank", "segment"]],
                  on=["permno", "ym"], how="left").reset_index(drop=True)

    months = eligible.index
    syms = list(eligible.columns)
    col = {s: i for i, s in enumerate(syms)}
    E = eligible.to_numpy(dtype=bool)
    ZC = chars.z_cap.reindex(index=months, columns=syms).to_numpy(dtype=float)
    ZR = chars.z_ret.reindex(index=months, columns=syms).to_numpy(dtype=float)

    # contamination universe: the arm's own events, as the parent rule does
    ex = events.assign(event_date=pd.to_datetime(events["event_date"])
                       ).sort_values("event_date")
    ex_dates = ex["event_date"].to_numpy("datetime64[ns]")
    ex_permno = ex["permno"].to_numpy(dtype="int64")
    excl = np.timedelta64(int(cfg.exclusion_days), "D")

    dates = ev["event_date"].to_numpy("datetime64[ns]")
    i0 = months.searchsorted(dates, side="left")
    ev["entry_i"], ev["char_i"] = i0, i0 - 1

    pools = {k: np.sort(g["permno"].to_numpy().astype("int64"))
             for k, g in daily_panel.ranks.groupby(["ym", "segment"],
                                                   sort=False)}

    ctrl = np.full(len(ev), np.nan)
    diag = {"events_in": int(len(ev)), "no_segment": 0, "no_char_month": 0,
            "window_past_panel": 0, "event_no_char": 0, "empty_pool": 0,
            "matched": 0}
    usable = (ev["entry_i"].to_numpy() < len(months)) \
        & (ev["char_i"].to_numpy() >= 0) & ev["segment"].notna().to_numpy()
    diag["no_segment"] = int((~ev["segment"].notna().to_numpy()).sum())
    diag["no_char_month"] = int((ev["char_i"].to_numpy() < 0).sum())
    diag["window_past_panel"] = int((ev["entry_i"].to_numpy()
                                     >= len(months)).sum())

    for (ym, seg, m0, mc), grp in ev[usable].groupby(
            ["ym", "segment", "entry_i", "char_i"], sort=False):
        p = pools.get((ym, seg))
        if p is None or len(p) == 0:
            diag["empty_pool"] += len(grp)
            continue
        j = np.array([col.get(str(int(x)), -1) for x in p], dtype="int64")
        keep = j >= 0
        p, j = p[keep], j[keep]
        if len(p):
            keep = (E[m0, j] & np.isfinite(ZC[mc, j]) & np.isfinite(ZR[mc, j]))
            p, j = p[keep], j[keep]
        if len(p) == 0:
            diag["empty_pool"] += len(grp)
            continue
        zc, zr = ZC[mc, j], ZR[mc, j]

        for idx, permno, d in zip(grp.index.to_numpy(),
                                  grp["permno"].to_numpy(),
                                  grp["event_date"].to_numpy()):
            je = col.get(str(int(permno)), -1)
            if je < 0 or not np.isfinite(ZC[mc, je]) or not np.isfinite(
                    ZR[mc, je]):
                diag["event_no_char"] += 1
                continue
            lo = int(np.searchsorted(ex_dates, d - excl, side="left"))
            hi = int(np.searchsorted(ex_dates, d + excl, side="right"))
            ok = ~np.isin(p, ex_permno[lo:hi]) & (p != int(permno))
            if not ok.any():
                diag["empty_pool"] += 1
                continue
            d2 = (zc[ok] - ZC[mc, je]) ** 2 + (zr[ok] - ZR[mc, je]) ** 2
            ctrl[idx] = p[ok][int(np.argmin(d2))]   # pool sorted -> tie = min permno
            diag["matched"] += 1

    ev["control_permno"] = ctrl
    logger.info("cohort controls matched for %d/%d events: %s",
                diag["matched"], len(ev), diag)
    return ev
