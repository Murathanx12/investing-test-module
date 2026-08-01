"""Cohort-controlled monthly harvest test — TRIAL-EVENT-13DG-HARVEST.

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
