"""TRIAL-EVENT-13DG — ONE SHOT PER ARM. Protocol: TRIALS/TRIAL-EVENT-13DG.md
(frozen 98c99e2).

Three arms, each a counted candidate (175-177): 13d_all, 13g_all, 13d_first.
The 13G arm is the point — same 5% threshold, same filer population, same
salience, differing only in declared intent. If both drift, the effect is
disclosure/selection; if only 13D drifts, intent is doing work.

EXPLORE 2004-01-01..2018-12-31 ONLY. The confirm window is not read here under
any outcome.

Frozen and enforced below:
  * initial filings only (amendments excluded from all arms);
  * matched control arm MANDATORY — same segment, same calendar month, nearest
    dollar-volume rank, no event within +/-60 calendar days;
  * the DIFFERENCED CAR is the only deciding number;
  * t clustered by event month, iid t reported alongside;
  * era split 2004-2010 vs 2011-2018 reported (13D volume falls 2,756/yr ->
    1,024/yr, so a pooled result is early-weighted);
  * the -1..0 announcement window is REPORTED, NEVER DECIDING. It doubles as
    the live sanity check that the event dates are real: if 13D shows no
    announcement-window action at all, suspect the pipeline before believing
    the nulls.

KILL CONDITION (frozen): if the 13D-minus-13G contrast is not positive with
clustered t >= 2.0 in at least one window, the activist-intent mechanism is
recorded dead and the family closes.

If any arm passes its CAR gate this script STOPS and flags: building a passing
arm as a monthly portfolio and clearing it through `scan_signal` is a separate,
ATTENDED step, and confirm needs Murat's authorisation.

Usage:  .venv\\Scripts\\python -m scripts.run_trial_event_13dg
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.factory import daily_events as de
from aegis_brain.factory import event_13dg as eg

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("event_13dg")
OUT = MODULE_ROOT / "data" / "factory"

# 2003 for the -1 day of a 2004-01-02 event; 2019 for the +60 trading days of a
# 2018-12-31 event. Loading less would silently truncate a window.
PANEL_YEARS = range(2003, 2020)
WINDOWS = (eg.ANNOUNCEMENT_WINDOW, *eg.DECIDING_WINDOWS)
DECIDING_LABELS = [de.window_label(a, b) for a, b in eg.DECIDING_WINDOWS]
ANNOUNCE_LABEL = de.window_label(*eg.ANNOUNCEMENT_WINDOW)


def arm_gate(summary: pd.DataFrame) -> bool:
    """Positive differenced CAR with clustered t >= 2.0 in a TRADABLE window.

    The freeze names one numeric bar — clustered t >= 2.0 on the differenced
    CAR — for the contrast; the same bar is applied per arm, since the doc
    states no other. The announcement window is excluded by construction: it is
    declared non-deciding.
    """
    d = summary[summary["tradable"]]
    return bool(((d["car_diff_bps"] > 0) & (d["t_clustered"] >= 2.0)).any())


def main() -> None:
    events = eg.load_events()
    arms = eg.build_arms(events)
    counts = {k: {"n_events": int(len(v)),
                  "n_permnos": int(v["permno"].nunique())}
              for k, v in arms.items()}
    print("\n=== ARMS (explore 2004-2018, initial filings only) ===")
    print(pd.DataFrame(counts).T.to_string())

    panel = de.DailyEventPanel.from_disk(PANEL_YEARS)

    summaries, cars_by_arm, eras = {}, {}, {}
    for name, ev in arms.items():
        log.info("running arm %s (%d events)", name, len(ev))
        summary, cars = de.run_event_study(ev, panel, windows=WINDOWS)
        summaries[name] = summary
        cars_by_arm[name] = cars
        cars["era"] = eg.era(cars["event_date"])
        eras[name] = {e: de.summarise(g, WINDOWS)
                      for e, g in cars.groupby("era")}
        print(f"\n--- {name} — differenced CAR vs matched controls ---")
        print(summary.to_string(index=False))

    # ── the announcement-window sanity check (reported, never deciding) ──────
    print("\n=== SANITY CHECK — the -1..0 announcement window ===")
    sanity = {}
    for name, s in summaries.items():
        row = s[s["window"] == ANNOUNCE_LABEL].iloc[0]
        sanity[name] = {"car_diff_bps": float(row["car_diff_bps"]),
                        "t_clustered": float(row["t_clustered"]),
                        "n_events": int(row["n_events"])}
    print(pd.DataFrame(sanity).T.to_string())
    d13 = sanity["13d_all"]
    dates_look_real = bool(d13["car_diff_bps"] > 0 and d13["t_clustered"] >= 2.0)
    print("  13D announcement-window action present:", dates_look_real,
          "-> event dates behave like real filing dates" if dates_look_real
          else "-> SUSPECT THE PIPELINE BEFORE BELIEVING THE NULLS")

    # ── era split (declared before any number existed) ───────────────────────
    print("\n=== ERA SPLIT (2004-2010 vs 2011-2018) ===")
    era_rows = []
    for name, by_era in eras.items():
        for e, s in by_era.items():
            for _, r in s.iterrows():
                era_rows.append({"arm": name, "era": e, **r.to_dict()})
    era_tab = pd.DataFrame(era_rows)
    print(era_tab[era_tab["tradable"]].to_string(index=False))

    # ── the deciding number: the 13D-minus-13G contrast ──────────────────────
    print("\n=== 13D-MINUS-13G CONTRAST (clustered on the pooled event month) ===")
    contrasts = {}
    g_cars = cars_by_arm["13g_all"]
    for d_name in ("13d_all", "13d_first"):
        d_cars = cars_by_arm[d_name]
        for a, b in eg.DECIDING_WINDOWS:
            col = f"car_{a}_{b}"
            c = eg.contrast(d_cars[col], d_cars["event_month"],
                            g_cars[col], g_cars["event_month"])
            contrasts[f"{d_name} vs 13g_all {de.window_label(a, b)}"] = c
    ctab = pd.DataFrame(contrasts).T
    print(ctab.to_string())

    primary = {k: v for k, v in contrasts.items() if k.startswith("13d_all")}
    primary_pass = any(v["contrast_bps"] > 0 and v["t_clustered"] >= eg.CONTRAST_T_BAR
                       for v in primary.values())
    secondary = {k: v for k, v in contrasts.items() if k.startswith("13d_first")}
    secondary_pass = any(v["contrast_bps"] > 0
                         and v["t_clustered"] >= eg.CONTRAST_T_BAR
                         for v in secondary.values())

    gates = {name: arm_gate(s) for name, s in summaries.items()}
    print("\nPER-ARM CAR GATE (positive differenced CAR, clustered t >= 2.0, "
          "tradable window):", gates)
    print("CONTRAST GATE (13d_all vs 13g_all):", primary_pass,
          "| (13d_first vs 13g_all):", secondary_pass)

    if primary_pass or secondary_pass or any(gates.values()):
        verdict = (
            "AN ARM OR CONTRAST CLEARED ITS GATE — STOPPED BEFORE THE "
            "PORTFOLIO / scan_signal STEP. Building a passing arm as a monthly "
            "book and clearing it through the deciding cost arms is an "
            "ATTENDED step, and confirm needs Murat's authorisation.")
    else:
        both_drift = all(
            summaries[n][summaries[n]["tradable"]]["car_diff_bps"].abs().max() > 0
            for n in ("13d_all", "13g_all"))
        verdict = (
            "NO ARM AND NO CONTRAST CLEARS ITS GATE. The 13D-minus-13G "
            "contrast is not positive at clustered t >= 2.0 in any window, so "
            "under the frozen kill condition the activist-intent mechanism is "
            "recorded DEAD and the family CLOSES — no re-cuts by market cap, "
            "campaign type, filer identity or window. Confirm not read; no "
            "forward lane seeded.")
        del both_drift

    print("\nVERDICT:", verdict)

    payload = {
        "trial": "TRIAL-EVENT-13DG",
        "protocol_commit": "98c99e2",
        "candidates": [175, 176, 177],
        "window": "explore 2004-01-01..2018-12-31 (confirm NOT read)",
        "arm_counts": counts,
        "summaries": {k: v.to_dict("records") for k, v in summaries.items()},
        "era_split": era_tab.to_dict("records"),
        "announcement_window_sanity": sanity,
        "event_dates_behave_like_real_filings": dates_look_real,
        "contrasts": contrasts,
        "arm_gates": gates,
        "contrast_gate_primary": primary_pass,
        "contrast_gate_13d_first": secondary_pass,
        "verdict": verdict,
    }
    (OUT / "trial_event_13dg.json").write_text(
        json.dumps(payload, indent=2, default=str))
    for name, c in cars_by_arm.items():
        c.to_parquet(OUT / f"trial_event_13dg_cars_{name}.parquet")
    log.info("wrote %s", OUT / "trial_event_13dg.json")


if __name__ == "__main__":
    main()
