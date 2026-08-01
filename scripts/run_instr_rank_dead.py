"""INSTR-RANK-DEAD — ONE SHOT. Protocol: TRIALS/INSTR-RANK-DEAD.md (frozen 98c99e2).

The replication bridge. Two signals with the starkest rank-real/book-dead
pattern, rebuilt from their frozen trial builders UNCHANGED, decomposed down a
three-rung ladder, and scored against four readings that were pre-declared
before any run code existed:

    io_level  (small)            TRIAL-ABIO-KIRK  builder, direction +1
    skew_25d  (optionable small) TRIAL-OPT-COHORT builder, direction -1

  L1  D10 - D1 decile spread, EW and VW, gross  -- the published conditions
  L2  top-minus-universe vs universe-minus-bottom, EW, gross -- the leg split
  L3  rank-IC in the upper vs lower dollar-volume half -- the tradability split

EXPLORE 2004-01..2018-12 ONLY. Everything is GROSS: no cost model is loaded,
so no cost dispute can touch the result. This instrument cannot revive,
graduate or seed anything under any outcome.

THE GUARD RUNS FIRST. Before a single ladder number is computed, each rebuilt
signal must reproduce its banked explore IC t to within rounding (io_level
11.29, skew_25d 8.34). If it does not, the builders are not the frozen
builders, the instrument is measuring something else, and the run aborts.

If R4 fires (L1 dead in both weightings) the frozen doc commits the program to
a harness audit -- a NEW ATTENDED DECISION. This script writes its results and
stops; it does not improvise the audit and takes no further cuts.

Usage:  .venv\\Scripts\\python -m scripts.run_instr_rank_dead
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory import rank_dead as rd
from aegis_brain.factory.abio import build_abio_frames
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.optsurf import DIRECTIONS as OPT_DIRECTIONS
from aegis_brain.factory.optsurf import build_opt_frames
from aegis_brain.factory.signals import FactorySignal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rank_dead")
OUT = MODULE_ROOT / "data" / "factory"

EXPLORE = ScanConfig()          # 2004-01..2018-12, frozen; costs never used here
SEGMENT = "small"               # both receipts are small-segment findings


def build_signals(panel) -> tuple[list[FactorySignal], dict]:
    """The two frozen builders, called UNCHANGED. No parameter is passed in and
    nothing is post-processed — the only thing this instrument is allowed to do
    to these signals is measure them differently."""
    abio_frames, abio_diag = build_abio_frames(panel)
    opt_frames, opt_diag = build_opt_frames(panel)

    sigs = [
        FactorySignal(
            "io_level",
            "Institutional ownership fraction (TRIAL-ABIO-KIRK builder, "
            "rebuilt unchanged).",
            lambda p, f=abio_frames["io_level"]: f, +1),
        FactorySignal(
            "skew_25d",
            "25-delta put IV minus 25-delta call IV, 30-day (TRIAL-OPT-COHORT "
            "builder, rebuilt unchanged).",
            lambda p, f=opt_frames["skew_25d"]: f, OPT_DIRECTIONS["skew_25d"]),
    ]
    diag = {"abio_coverage_io_level": abio_diag.get("coverage_io_level"),
            "opt_coverage_skew_25d": opt_diag.get("coverage_skew_25d")}
    return sigs, diag


def guard(panel, sigs: list[FactorySignal]) -> dict:
    """Reproduce the banked explore IC t before any ladder number exists.

    IC and gross excess are both cost-independent, so a flat-cost scan
    reproduces the banked `t_ic` and `t_excess_gross` exactly as NEG_RESULTS
    26/27 report them. Fails LOUD: a builder that has drifted voids the run.
    """
    report = {}
    for sig in sigs:
        s = scan_signal(panel, sig, SEGMENT, EXPLORE)["summary"]
        banked_ic = rd.BANKED_IC_T[sig.name]
        banked_gross = rd.BANKED_GROSS_T[sig.name]
        ok = rd.reproduction_ok(s["t_ic"], banked_ic)
        report[sig.name] = {
            "months": s["months"], "ic_mean": s["ic_mean"],
            "t_ic_measured": s["t_ic"], "t_ic_banked": banked_ic,
            "t_gross_measured": s["t_excess_gross"],
            "t_gross_banked": banked_gross,
            "reproduces_banked_ic_t": ok,
        }
        log.info("GUARD %s: t_ic %.2f vs banked %.2f | gross t %.2f vs banked "
                 "%.2f", sig.name, s["t_ic"], banked_ic, s["t_excess_gross"],
                 banked_gross)
        if not ok:
            raise SystemExit(
                f"GUARD FAILED for {sig.name}: rebuilt explore IC t "
                f"{s['t_ic']} does not reproduce the banked {banked_ic}. The "
                f"builder is not the frozen builder; the run is VOID.")
    return report


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    sigs, coverage = build_signals(panel)

    print("\n=== GUARD — rebuilt signals must reproduce their banked IC t ===")
    guard_report = guard(panel, sigs)
    print(pd.DataFrame(guard_report).T.to_string())

    mktcap = rd.market_cap_frame(panel)

    results, ladders = {}, {}
    for sig in sigs:
        l1 = rd.ladder_l1(panel, sig, SEGMENT, EXPLORE, mktcap=mktcap)
        l2 = rd.ladder_l2(panel, sig, SEGMENT, EXPLORE)
        l3 = rd.ladder_l3(panel, sig, SEGMENT, EXPLORE)
        readings = rd.score_readings(l1, l2, l3)
        readings["months"] = int(len(l1))
        readings["mean_ew_spread_bps"] = round(float(l1["ew_spread"].mean()) * 1e4, 1)
        readings["mean_vw_spread_bps"] = round(float(l1["vw_spread"].mean()) * 1e4, 1)
        readings["mean_top_bps"] = round(
            float(l2["top_minus_universe"].mean()) * 1e4, 1)
        readings["mean_bottom_bps"] = round(
            float(l2["universe_minus_bottom"].mean()) * 1e4, 1)
        readings["ic_mean_upper"] = round(float(l3["ic_upper"].mean()), 4)
        readings["ic_mean_lower"] = round(float(l3["ic_lower"].mean()), 4)
        results[sig.name] = readings
        ladders[sig.name] = {"l1": l1, "l2": l2, "l3": l3}

    tab = pd.DataFrame(results).T
    print("\n=== INSTR-RANK-DEAD — EXPLORE 2004-2018, ALL GROSS (one shot) ===")
    print(tab[["months", "mean_ew_spread_bps", "t_spread_ew",
               "mean_vw_spread_bps", "t_spread_vw",
               "mean_top_bps", "t_top_minus_universe",
               "mean_bottom_bps", "t_universe_minus_bottom",
               "ic_mean_upper", "t_ic_upper_half",
               "ic_mean_lower", "t_ic_lower_half"]].to_string())

    print("\n=== PRE-DECLARED READINGS (frozen before any number existed) ===")
    keys = ["R1_conditions_not_code", "R2_information_is_short_side",
            "R3_below_tradability", "R4_the_puzzle_stands"]
    print(tab[keys].to_string())

    fired = {k: [n for n in results if results[n][k]] for k in keys}
    for k in keys:
        print(f"  {k:34s} FIRED ON: {fired[k] or 'NONE'}")

    r4_any = bool(fired["R4_the_puzzle_stands"])
    if r4_any:
        verdict = (
            "R4 FIRED on " + ", ".join(fired["R4_the_puzzle_stands"]) +
            " — L1 is dead gross in BOTH weightings, so the rank-real/"
            "book-dead pattern is UNEXPLAINED at this resolution. Per the "
            "frozen doc: no further re-cuts here; the harness audit is a NEW "
            "ATTENDED DECISION. STOPPED.")
    else:
        verdict = ("R4 did not fire — L1 carries the published effect. See the "
                   "per-signal readings for which of R1-R3 explain the gap.")
    print("\nVERDICT:", verdict)

    payload = {
        "instrument": "INSTR-RANK-DEAD",
        "protocol_commit": "98c99e2",
        "candidate": 174,
        "window": "explore 2004-01..2018-12 (confirm NOT read)",
        "segment": SEGMENT,
        "all_gross": True,
        "coverage": coverage,
        "guard": guard_report,
        "readings": results,
        "fired": fired,
        "verdict": verdict,
        "stopped_for_attended_decision": r4_any,
    }
    (OUT / "instr_rank_dead.json").write_text(
        json.dumps(payload, indent=2, default=str))
    for name, L in ladders.items():
        for rung, frame in L.items():
            frame.to_parquet(OUT / f"instr_rank_dead_{name}_{rung}.parquet")
    log.info("wrote %s", OUT / "instr_rank_dead.json")


if __name__ == "__main__":
    main()
