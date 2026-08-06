"""RECAL-1 Stage 3'' — ladder selection against the FDR budget, then freeze.

The simulator is a calibration instrument: ground truth is known, so fitting
gate thresholds against it is calibration, not data snooping. What keeps it
honest is that the fitting is (a) pre-registered here before any bank exists,
(b) confined to ONE half of the reps, and (c) reported on the other half.

Pre-registered protocol (spec docs/RECAL1_SPEC_2026-08-06.md §4):
  - SELECTION half = even rep numbers. HELD-OUT half = odd. CRN pairs live
    inside a rep, so a rep is the atomic unit and the split cannot leak.
  - FEASIBLE := point FDR <= 0.05 AND Wilson-95 upper bound <= 0.08, where
    FDR = P(adopt | alpha = 0) in the a0.0/base cell.
  - OBJECTIVE := maximize P(adopt | alpha = 0.4, I1) — I1 is the only design
    whose injected edge still EXISTS in the 2019-24 confirm window (I2 decays
    to 9.2% of explore-window strength by construction), so it is the only
    design on which end-to-end adoption power is a meaningful target.
  - Tie-breaks, in order: P(adopt | 0.2, I1) desc; FDR asc; then STRICTEST
    surviving ladder (pbo_threshold asc, dsr_threshold desc, explore_t_ic
    desc, confirm_t_ic desc, largemid-only before both-segments, prod book
    before engineered) — ties resolve toward conceding as little as possible.
  - The winner is written to runs/GATE-M1/brain009_frozen.json. That file IS
    the freeze record; everything downstream reads it with @path.

Run:  python -m aegis_brain.calibration.select --tag r1
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from itertools import product

from aegis_brain.calibration.bank import load_bank, tables
from aegis_brain.calibration.config import RUNS_DIR, assert_production_constants
from aegis_brain.calibration.ruleset import BRAIN_008, Ruleset, evaluate
from aegis_brain.calibration.run_grid import wilson

FDR_CELL = "a0.0/base"
POWER_CELL = "a0.4/I1"
SECOND_CELL = "a0.2/I1"

FDR_MAX = 0.05
FDR_WILSON_MAX = 0.08

# ---- the pre-registered family (frozen before the bank existed) ----------
F_EXPLORE_T_IC = (1.25, 1.5, 1.75, 2.0, 2.25)
F_EXPLORE_SEGMENTS = (("largemid",), ("largemid", "small"))
F_CONFIRM_T_IC = (0.5, 0.75, 1.0, 1.25, 1.5)
F_BOOK = ("prod", "eng")
F_DSR_THRESHOLD = (0.0, 0.10, 0.25, 0.50, 0.75, 0.95)
# Spec delta 2026-08-06 (§10): PBO is computed on the CELL's 42 explore books,
# 41 of which are null, so it measures the batch's selection noise rather than
# the candidate's robustness — measured 0.51/0.59 on the two rep-0 control
# cells. Left fixed at 0.5 it would reject roughly half of everything by coin
# flip. It becomes a calibrated slot; 1.0 = reported, not gating.
F_PBO_THRESHOLD = (0.5, 0.6, 1.0)


def family() -> list[Ruleset]:
    out = []
    for e, segs, c, book, d, p in product(
            F_EXPLORE_T_IC, F_EXPLORE_SEGMENTS, F_CONFIRM_T_IC, F_BOOK,
            F_DSR_THRESHOLD, F_PBO_THRESHOLD):
        segtag = "lm" if len(segs) == 1 else "lm+sm"
        out.append(Ruleset(
            name=f"B009[e{e}/{segtag}|c{c}|{book}|d{d}|p{p}]",
            explore_t_ic=e, explore_t_net=None, explore_rank_by="t_ic",
            explore_segments=segs, explore_top_n=5,
            confirm_t_ic=c, confirm_t_net=None,
            confirm_sign_ic=True, confirm_sign_net=False, confirm_book=book,
            dsr_book=book, dsr_n_trials=179, dsr_threshold=d,
            pbo_threshold=p))
    return out


def rate(reps: list[dict], rs: Ruleset, cell: str) -> tuple[float, int, int]:
    rows = [evaluate(r["cells"][cell], rs) for r in reps if cell in r["cells"]]
    if not rows:
        raise KeyError(f"cell {cell} absent from the bank — grid incomplete")
    k = sum(1 for x in rows if x["terminal"] == "adopt")
    return k / len(rows), k, len(rows)


def score(reps: list[dict], rs: Ruleset) -> dict:
    fdr, kf, nf = rate(reps, rs, FDR_CELL)
    pw, kp, np_ = rate(reps, rs, POWER_CELL)
    try:
        p2 = rate(reps, rs, SECOND_CELL)[0]
    except KeyError:
        p2 = float("nan")
    lo, hi = (float(x) for x in wilson(kf, nf))
    # numpy scalars must not escape into the report — json refuses them, and
    # a chain that dies at the freeze write has burned the whole grid.
    return {"ruleset": rs, "fdr": float(fdr), "fdr_wilson": [lo, hi],
            "power_a04_I1": float(pw), "power_a02_I1": float(p2),
            "n_fdr": int(nf), "n_power": int(np_),
            "feasible": bool(fdr <= FDR_MAX and hi <= FDR_WILSON_MAX)}


def strictness(rs: Ruleset) -> tuple:
    """Higher = concedes less. Used only as a deterministic tie-break."""
    return (-rs.pbo_threshold, rs.dsr_threshold, rs.explore_t_ic,
            rs.confirm_t_ic,
            1 if rs.explore_segments == ("largemid",) else 0,
            1 if rs.dsr_book == "prod" else 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="r1")
    ap.add_argument("--out", default="brain009_frozen.json",
                    help="freeze record filename under runs/GATE-M1 "
                         "(smoke runs MUST override so they cannot write the "
                         "real freeze record)")
    args = ap.parse_args()
    assert_production_constants()

    sel = load_bank(args.tag, "even")
    hold = load_bank(args.tag, "odd")
    print(f"selection half: {len(sel)} reps | held-out half: {len(hold)} reps")

    scored = [score(sel, rs) for rs in family()]
    feasible = [s for s in scored if s["feasible"]]
    print(f"family: {len(scored)} ladders, {len(feasible)} feasible "
          f"(FDR <= {FDR_MAX}, Wilson upper <= {FDR_WILSON_MAX})")
    if not feasible:
        raise SystemExit(
            "NO FEASIBLE LADDER in the pre-registered family. This is a "
            "reportable outcome, not an error — widen the family only with a "
            "committed spec delta.")

    best = max(feasible, key=lambda s: (round(s["power_a04_I1"], 6),
                                        round(s["power_a02_I1"], 6),
                                        -round(s["fdr"], 6),
                                        strictness(s["ruleset"])))
    rs = best["ruleset"]
    frozen = Ruleset(**{**asdict(rs), "name": "BRAIN-009"})

    # held-out read of the frozen ladder, and the control arm alongside
    ho = score(hold, frozen)
    ctl_sel, ctl_ho = score(sel, BRAIN_008), score(hold, BRAIN_008)

    report = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tag": args.tag,
        "protocol": ("selection on even reps, held-out on odd; objective "
                     f"P(adopt|{POWER_CELL}) s.t. FDR<={FDR_MAX} and Wilson "
                     f"upper<={FDR_WILSON_MAX} on {FDR_CELL}"),
        "family_size": len(scored), "n_feasible": len(feasible),
        "ruleset": asdict(frozen),
        "selection_half": {k: best[k] for k in
                           ("fdr", "fdr_wilson", "power_a04_I1",
                            "power_a02_I1", "n_fdr", "n_power")},
        "held_out_half": {k: ho[k] for k in
                          ("fdr", "fdr_wilson", "power_a04_I1",
                           "power_a02_I1", "n_fdr", "n_power")},
        "control_BRAIN_008": {"selection": {k: ctl_sel[k] for k in
                                            ("fdr", "power_a04_I1")},
                              "held_out": {k: ctl_ho[k] for k in
                                           ("fdr", "power_a04_I1")}},
        "frontier": sorted(
            [{"key": s["ruleset"].key(), "fdr": round(s["fdr"], 4),
              "power_a04_I1": round(s["power_a04_I1"], 4),
              "power_a02_I1": round(s["power_a02_I1"], 4),
              "feasible": s["feasible"]} for s in scored],
            key=lambda d: -d["power_a04_I1"])[:60],
        "held_out_tables": tables(hold, frozen),
    }
    out = RUNS_DIR / args.out
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("ruleset", "selection_half", "held_out_half",
                       "control_BRAIN_008")}, indent=2))
    print(f"FROZEN -> {out}")


if __name__ == "__main__":
    main()
