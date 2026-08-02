"""TRIAL-EVENT-13DG-HARVEST2 — ONE SHOT, ONE ARM (candidate 179, TERMINAL).
Protocol: TRIALS/TRIAL-EVENT-13DG-HARVEST2.md (frozen c3e4f03).

The family's last admissible question. HARVEST (178) ended NO CONCLUSION when
its placebo gate fired: matching on segment, calendar month and nearest
dollar-volume RANK is a liquidity match, and random-date positions in
13D-targeted names still lost ~25 bps/mo gross to their own controls
(NEG_RESULTS 30). Because the true-date number was never computed there,
recalibrating the instrument on its own null leaks nothing — once.

WHAT CHANGES, AND ONLY THIS: the control is now the nearest neighbour in
per-month standardised (log market cap, prior 6-month return), both read at the
last month-end STRICTLY BEFORE the filing date, within the same segment, same
calendar month, eligible at the entry month-end, no own event within +/-60cd.
One control per event, with replacement, ties to the smallest permno.

Everything else is HARVEST's frozen spec verbatim and is REUSED BY IMPORT:
  * arm = `13d_first` as banked and run (7,360; discrepancy disclosed upstream);
  * window = first month-end ON OR AFTER the filing, through the third month-end
    after entry; BOTH LEGS over the identical window;
  * eligibility = factory universe, dollar-volume rank <= 3000, at entry;
  * deciding number = differenced NET return, t clustered by ENTRY month;
  * deciding costs = per-name KO half-spread round trip on the EVENT leg only;
    flat-25 guard and zero-cost bound reported alongside;
  * PASS bar = differenced net mean > 0 AND clustered t >= 1.5;
  * EXPLORE ONLY, and the wall binds the WINDOW, not just the event date.

THE PLACEBO GATE IS UNCHANGED AND STILL IN FRONT. Five seeds of random filing
dates on the same permnos through the identical pipeline, read FIRST; the real
arm is not computed at all unless the gate passes (`event_harvest.gated_run`),
so the compute order is the tamper-evidence rather than a promise.

TERMINAL, as frozen. Gate fails -> the family closes as unmeasurable at this
mandate's resolution. Gate passes and the bar is missed -> the family closes as
real-but-unharvestable. Gate passes and the bar clears -> STOP; confirm
(2019-2024) is Murat's explicit authorisation, always. No third design.

Usage:  .venv\\Scripts\\python -m scripts.run_13dg_harvest2
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
log = logging.getLogger("harvest2_13dg")
OUT = MODULE_ROOT / "data" / "factory"

ARM = "13d_first"
CFG = eh.HarvestConfig()
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
    chars = eh.cohort_characteristics(panel, elig)
    log.info("characteristics: z_cap %d finite, z_ret %d finite cells",
             int(chars.z_cap.notna().to_numpy().sum()),
             int(chars.z_ret.notna().to_numpy().sum()))

    def legs_for(ev: pd.DataFrame, spread) -> tuple[pd.DataFrame, dict]:
        matched = eh.match_cohort_controls(ev, daily, chars, elig, CFG)
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
                legs.to_parquet(OUT / "trial_13dg_harvest2_legs.parquet")
        return {"cost_arms": rows, "attrition": diag}

    result = eh.gated_run(gate_fn, real_fn, CFG)
    gate = result["gate"]

    # ── report: the gate, first ─────────────────────────────────────────────
    print("\n=== PLACEBO GATE — read FIRST, five seeds of random filing dates "
          "on the same permnos ===")
    print(pd.DataFrame(gate["per_seed"]).T[
        ["n_events", "n_entry_months", "event_leg_bps", "control_leg_bps",
         "diff_net_bps", "diff_net_bps_per_month", "t_clustered",
         "diff_gross_bps", "t_gross_clustered"]].to_string())
    print("\nPOOLED (clustered on the entry month across seeds):")
    print(pd.Series(gate["pooled"]).to_string())
    print(f"\nGATE (|t| < {CFG.placebo_t_bar} required): "
          f"{'PASS' if gate['passed'] else 'FAIL'}")

    if not result["gate_passed"]:
        verdict = (
            "NO CONCLUSION, and by the frozen terminal clause the 13D FAMILY "
            "CLOSES: the timing effect is real at event resolution "
            "(NEG_RESULTS 29), no admissible monthly-resolution design was "
            "found in two attempts, and harvestability at this programme's "
            "mandate resolution is therefore UNMEASURABLE and unclaimable. "
            "The real number was NOT computed. No third design.")
        print("\nVERDICT:", verdict)
        payload = {"trial": "TRIAL-EVENT-13DG-HARVEST2",
                   "protocol_commit": "c3e4f03", "candidates": [179],
                   "arm": ARM, "n_events": int(len(events)),
                   "gate": gate, "gate_passed": False, "real": None,
                   "family_closes": True, "verdict": verdict}
        (OUT / "trial_13dg_harvest2.json").write_text(
            json.dumps(payload, indent=2, default=str))
        log.info("wrote %s", OUT / "trial_13dg_harvest2.json")
        return

    # ── report: the real arm ────────────────────────────────────────────────
    real = result["real"]
    tab = pd.DataFrame(real["cost_arms"])
    show = ["cost_arm", "deciding", "n_events", "n_entry_months",
            "event_leg_bps", "control_leg_bps", "mean_cost_bps",
            "diff_net_bps", "diff_net_bps_per_month", "t_clustered", "t_iid",
            "diff_gross_bps", "t_gross_clustered"]
    print("\n=== THE REAL ARM — cohort-matched on size and prior return ===")
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
            "costs against controls matched on size and prior return. STOPPED "
            "HERE. The confirm window (2019-2024) is one-use and reading it is "
            "Murat's explicit authorisation, ALWAYS. Nothing registered, no "
            "lane seeded.")
    else:
        verdict = (
            "FAIL, gate clean. The 13D family CLOSES, as frozen: the drift is "
            "REAL at event resolution (NEG_RESULTS 29), front-loaded inside the "
            "first post-filing weeks, and NOT harvestable at monthly entry net "
            "of costs even when the control is matched on the cohort traits "
            "that predict returns. The programme's lanes are monthly; a "
            "daily-resolution harvest is out of mandate and closes with the "
            "family. No re-cuts, no third design. Confirm not read; no forward "
            "lane seeded.")
    print("\nVERDICT:", verdict)

    # ── the frozen prediction, scored ───────────────────────────────────────
    pred = {
        "placebo_gate_passes": True,
        "diff_net_8_to_25_bps_per_month": bool(
            8 <= dec["diff_net_bps_per_month"] <= 25),
        "t_in_0.8_to_1.6": bool(0.8 <= dec["t_clustered"] <= 1.6),
        "narrow_fail_of_the_1.5_bar": bool(not passed),
    }
    print("\n=== FROZEN PREDICTION, SCORED ===")
    print(json.dumps(pred, indent=2))

    payload = {
        "trial": "TRIAL-EVENT-13DG-HARVEST2",
        "protocol_commit": "c3e4f03",
        "candidates": [179], "new_candidates": 0,
        "arm": ARM, "n_events": int(len(events)),
        "window": "explore 2004-01..2018-12 (confirm NOT read)",
        "bar": "differenced net mean > 0 and clustered t >= 1.5",
        "gate": gate, "gate_passed": True,
        "real": real, "clears_bar": passed,
        "family_closes": bool(not passed),
        "prediction_scored": pred, "verdict": verdict,
        "stopped_for_attended_decision": passed,
    }
    (OUT / "trial_13dg_harvest2.json").write_text(
        json.dumps(payload, indent=2, default=str))
    log.info("wrote %s", OUT / "trial_13dg_harvest2.json")


if __name__ == "__main__":
    main()
