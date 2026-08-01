"""TRIAL-EVENT-13DG-HARVEST — ONE SHOT, ONE ARM (candidate 178).
Protocol: TRIALS/TRIAL-EVENT-13DG-HARVEST.md (frozen 0951193).

The only still-open question on this family: does NEG_RESULTS 29's timing
effect survive the monthly entry delay and costs, measured against the SAME
cohort-matched controls that established it? The book stage could not answer
that — its EW-universe benchmark measured cohort, not timing, and its own
random-date placebo proved it.

WHAT MAKES THIS RUN VALID, AND THE ORDER IT HAPPENS IN:

  1. THE PLACEBO GATE RUNS FIRST AND IS READ FIRST. Five seeds of random
     filing dates on the same permnos, through the identical pipeline. If the
     pooled differenced |t| >= 2.0 the design has failed to control cohort and
     the verdict is NO CONCLUSION — nothing downstream is readable. The real
     number is not computed at all in that branch (`event_harvest.gated_run`),
     so the compute order is the tamper-evidence, not a promise.
  2. THE CONTROL RULE IS THE PARENT TRIAL'S, CALLED NOT COPIED — same segment,
     same calendar month, nearest dollar-volume rank, no event within +/-60
     calendar days, matched at the ORIGINAL filing date.

Frozen and enforced below:
  * one arm, `13d_first`, exactly as banked and run (7,360; the rule-as-written
    set, discrepancy already disclosed in the parent trial);
  * window = first month-end ON OR AFTER the filing date, through the third
    month-end after entry; BOTH LEGS over the identical window;
  * eligibility = factory universe, dollar-volume rank <= 3000, at entry;
  * deciding number = differenced NET return, t clustered by ENTRY month;
  * deciding costs = per-name KO half-spread round trip on the EVENT leg only
    (the control is a paper benchmark and pays nothing — conservative against
    us); flat-25 guard and zero-cost bound reported alongside;
  * PASS bar = differenced net mean > 0 AND clustered t >= 1.5;
  * EXPLORE ONLY — and here the wall binds the WINDOW, not just the event: a
    filing whose third month-end lands in 2019 produces no measurement.

If it clears the bar this script STOPS. Confirm (2019-2024) is Murat's
authorisation, always.

Usage:  .venv\\Scripts\\python -m scripts.run_13dg_harvest
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory import daily_events as de
from aegis_brain.factory import event_13dg as eg
from aegis_brain.factory import event_book as eb
from aegis_brain.factory import event_harvest as eh

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("harvest_13dg")
OUT = MODULE_ROOT / "data" / "factory"

ARM = "13d_first"
CFG = eh.HarvestConfig()
# Filing dates (real and redrawn) live in 2004-01..2018-12; the control rule
# only ever reads dollar-volume ranks in the filing month, so these are the
# years that can affect a match. Loading more cannot change a rank.
PANEL_YEARS = range(2004, 2019)


def main() -> None:
    events = eg.build_arms()[ARM]
    log.info("arm %s: %d events, %d permnos", ARM, len(events),
             events["permno"].nunique())

    daily = de.DailyEventPanel.from_disk(PANEL_YEARS)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    spreads = build_spread_frame(panel)
    zero = spreads * 0.0
    elig = eb.eligible_universe(panel, eb.BookConfig(max_rank=CFG.max_rank))

    def legs_for(ev: pd.DataFrame, spread) -> tuple[pd.DataFrame, dict]:
        matched = eh.match_parent_controls(ev, daily, CFG)
        return eh.compute_legs(matched, panel, elig, spread, CFG)

    # ── 1. THE GATE (deciding cost arm, identical pipeline) ──────────────────
    def gate_fn() -> dict:
        log.info("PLACEBO GATE: 5 random-date seeds, read BEFORE the real arm")
        return eh.placebo_gate(lambda ev: legs_for(ev, spreads)[0], events, CFG)

    # ── 2. THE REAL ARM — only ever called behind a passed gate ──────────────
    def real_fn() -> dict:
        log.info("gate passed; computing the real arm")
        rows, diag = [], None
        for label, frame, deciding in (("ko_half", spreads, True),
                                       ("flat25_guard", None, False),
                                       ("zero_cost_bound", zero, False)):
            legs, d = legs_for(events, frame)
            s = eh.summarise_legs(legs, CFG)
            s.update({"cost_arm": label, "deciding": deciding})
            rows.append(s)
            if deciding:
                diag = d
                legs.to_parquet(OUT / "trial_13dg_harvest_legs.parquet")
        return {"cost_arms": rows, "attrition": diag}

    result = eh.gated_run(gate_fn, real_fn, CFG)
    gate = result["gate"]

    # ── report: the gate, first ──────────────────────────────────────────────
    print("\n=== PLACEBO GATE — read FIRST, five seeds of random filing dates "
          "on the same permnos ===")
    print(pd.DataFrame(gate["per_seed"]).T[
        ["n_events", "n_entry_months", "diff_net_bps",
         "diff_net_bps_per_month", "t_clustered"]].to_string())
    print("\nPOOLED (clustered on the entry month across seeds):")
    print(pd.Series(gate["pooled"]).to_string())
    print(f"\nGATE (|t| < {CFG.placebo_t_bar} required): "
          f"{'PASS' if gate['passed'] else 'FAIL'}")

    if not result["gate_passed"]:
        verdict = (
            "NO CONCLUSION. The placebo gate FAILED: random filing dates on the "
            "same permnos produce a differenced net return significant at "
            f"|t| >= {CFG.placebo_t_bar}, so this design does not control the "
            "cohort either and nothing downstream is readable. The real number "
            "was NOT computed. A design that cannot pass its own placebo does "
            "not get to produce a tradability verdict.")
        print("\nVERDICT:", verdict)
        payload = {"trial": "TRIAL-EVENT-13DG-HARVEST",
                   "protocol_commit": "0951193", "candidates": [178],
                   "arm": ARM, "n_events": int(len(events)),
                   "gate": gate, "gate_passed": False, "real": None,
                   "verdict": verdict}
        (OUT / "trial_13dg_harvest.json").write_text(
            json.dumps(payload, indent=2, default=str))
        log.info("wrote %s", OUT / "trial_13dg_harvest.json")
        return

    # ── report: the real arm ─────────────────────────────────────────────────
    real = result["real"]
    tab = pd.DataFrame(real["cost_arms"])
    show = ["cost_arm", "deciding", "n_events", "n_entry_months",
            "event_leg_bps", "control_leg_bps", "mean_cost_bps",
            "diff_net_bps", "diff_net_bps_per_month", "t_clustered", "t_iid",
            "diff_gross_bps", "t_gross_clustered"]
    print("\n=== THE REAL ARM — cohort-matched, monthly-implementable window ===")
    print(tab[show].to_string(index=False))

    print("\n=== ATTRITION (where the banked events went) ===")
    print(pd.Series(real["attrition"]).to_string())

    dec = next(r for r in real["cost_arms"] if r["deciding"])
    passed = eh.clears_bar(dec, CFG)
    print(f"\n=== FROZEN BAR: differenced net mean > 0 AND clustered t >= "
          f"{CFG.bar_t} === -> {'PASS' if passed else 'FAIL'}")

    if passed:
        verdict = (
            "PASS — the 13D timing effect survives the monthly entry delay and "
            "costs against cohort-matched controls. STOPPED HERE. The confirm "
            "window (2019-2024) is one-use and reading it is Murat's explicit "
            "authorisation, always. Nothing registered, no lane seeded.")
    else:
        verdict = (
            "FAIL, gate clean. Recorded finding, as frozen: 13D drift is REAL "
            "(NEG_RESULTS 29), front-loaded inside the first post-filing weeks, "
            "and NOT harvestable at monthly resolution net of costs even "
            "cohort-controlled. The 13D family CLOSES COMPLETELY for this "
            "programme. The programme's lanes are monthly; a daily-resolution "
            "harvest is out of mandate and closes with the family (paper-noted, "
            "not re-registered). No re-cuts by cap, era, campaign type or "
            "window. Confirm not read; no forward lane seeded.")
    print("\nVERDICT:", verdict)

    # ── the frozen prediction, scored ────────────────────────────────────────
    pred = {
        "diff_net_8_to_25_bps_per_month": bool(
            8 <= dec["diff_net_bps_per_month"] <= 25),
        "t_in_0.8_to_1.6": bool(0.8 <= dec["t_clustered"] <= 1.6),
        "narrow_fail_of_the_1.5_bar": bool(not passed),
        "placebo_gate_passes": True,
        "placebo_abs_t_below_1": bool(abs(gate["pooled"]["t_clustered"]) < 1.0),
    }
    print("\n=== FROZEN PREDICTION, SCORED ===")
    print(json.dumps(pred, indent=2))

    payload = {
        "trial": "TRIAL-EVENT-13DG-HARVEST",
        "protocol_commit": "0951193",
        "candidates": [178], "new_candidates": 0,
        "arm": ARM, "n_events": int(len(events)),
        "window": "explore 2004-01..2018-12 (confirm NOT read)",
        "bar": "differenced net mean > 0 and clustered t >= 1.5",
        "gate": gate, "gate_passed": True,
        "real": real, "clears_bar": passed,
        "prediction_scored": pred, "verdict": verdict,
        "stopped_for_attended_decision": passed,
    }
    (OUT / "trial_13dg_harvest.json").write_text(
        json.dumps(payload, indent=2, default=str))
    log.info("wrote %s", OUT / "trial_13dg_harvest.json")


if __name__ == "__main__":
    main()
