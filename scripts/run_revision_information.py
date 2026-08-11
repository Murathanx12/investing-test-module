"""ANALYST-REVISION information, measured on the cross-section instead of a book.

WHAT IS BEING ASKED, AND WHAT IS NOT
====================================

ANALYST-IBES-1 reported that analyst target REVISIONS earn +1.5 to +6.1 %/yr
gross and die on 10x turnover, while analyst target LEVELS are perverse (-8 to
-18 %/yr). The revision arms were then re-audited and every one of them sat
below its own detection threshold: the best, `tgt_rev_breadth` small at
+6.05 %/yr, was measured by a design that resolves 7.60 %/yr under IID and
8.36 %/yr under HAC. So the honest state of the revision question is UNRESOLVED,
and it is the single most promising corpse in the graveyard.

This script does NOT re-run that trial. It asks the prior question the trial
skipped:

    does the cross-section carry the information at all,
    and for how long after the revision?

That is a Layer-1 question (`aegis_brain/pf/information.py`). It cannot and does
not conclude that money can be made — the spread it measures is dollar-neutral
and unconstrained, and Round 16 found 88 to 99.9% of a comparable spread living
in the short leg. A positive result here licenses a Layer-2 decision-boundary
test. It licenses no position and no capital.

THE SECOND QUESTION: IS THE NEW INSTRUMENT ACTUALLY BETTER?
===========================================================

The case for measuring on the cross-section is that a top-50 book throws away
breadth and leaves incidental factor exposure in its own standard error. In
synthetic worlds that argument is worth a factor of only 1.29 to 1.52 — see
`tests/test_information.py`, where a first attempt to assert a factor above 2
failed at 1.31 and the failure was kept. Whether the gain is larger on the real
panel is an empirical question about how much of a REAL book's variance is
incidental, and this script answers it by running both instruments over the same
signal and the same months.

If the gain turns out to be small, that is the finding, and the graveyard rescue
queue does not get its powered instrument from this direction. The script is
written to report that outcome as readily as the other one.

PRE-REGISTRATION
----------------
Registered before compute, in `TRIALS/PREREG_REVINFO_1.md`. Horizons 1/3/6/12
months, both segments, the frozen 2002-2022 window, holdout untouched. The
control arm is the corpse: `tgt_upside`, graded PERVERSE/CLOSED, which must come
back negative or the pipeline is wrong.

    python -m scripts.run_revision_information

Writes runs/REVINFO/revision_information.json.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.information import (cross_sectional_information,
                                        instrument_comparison)
from aegis_brain.pf.run import Factory

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "REVINFO"

FIRST, LAST = "2002-01-31", "2022-12-31"
HORIZONS = (1, 3, 6, 12)
SEGMENTS = ("small", "largemid")

#: The signal under test, plus the corpse that must reproduce its own kill.
#: A new mechanism carries the corpse it is not, as a control arm (ARENA-1).
ARMS = {
    "ibes:tgt_rev_breadth": "UNRESOLVED — the promising revision construction",
    "ibes:tgt_rev_3m": "UNRESOLVED — the second revision construction",
    "ibes:eps_rev_breadth": "UNTESTED at Layer 1 — EPS rather than target revisions",
    "ibes:tgt_upside": "CONTROL: PERVERSE/CLOSED, must come back negative",
}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    fac = Factory(FIRST, LAST, out_dir=OUT)
    frames = fac.lib._ibes()
    ret = fac.spine.panel.monthly_ret
    bench = fac.spine.mkt

    rows, comparisons = [], []
    for key, note in ARMS.items():
        if key not in frames:
            logger.warning("%s not in the IBES panel — skipped", key)
            continue
        frame = frames[key]
        for seg in SEGMENTS:
            elig = fac.eligible(seg)
            for h in HORIZONS:
                res = cross_sectional_information(
                    frame, ret, eligible=elig, horizon=h,
                    name=f"{key}|{seg}|h{h}")
                d = res.to_dict()
                d.update({"arm_note": note, "segment": seg, "signal_key": key})
                rows.append(d)
                logger.info(
                    "%-24s %-8s h%-2d: spread %+6.2f%%/yr  MDE %5.2f  t %s  -> %s",
                    key, seg, h, 100 * res.long_short_spread_ann,
                    100 * res.long_short_spread_mde_ann,
                    f"{res.long_short_spread_t:+.2f}"
                    if res.long_short_spread_t is not None else "  n/a",
                    res.verdict)

            # the instrument comparison only makes sense at the horizon the
            # incumbent actually used
            comp = instrument_comparison(frame, ret, bench, eligible=elig,
                                         name=f"{key}|{seg}", horizon=1)
            comparisons.append(comp)
            logger.info("   instrument gain %-8s %s: %.2fx  (incumbent MDE "
                        "%.2f%%/yr vs cross-sectional %.2f%%/yr)", key, seg,
                        comp["mde_ratio_incumbent_over_cross_sectional"],
                        100 * comp["incumbent_top_n_long_only"]["mde_ann"],
                        100 * comp["cross_sectional"]["mde_ann"])

    gains = [c["mde_ratio_incumbent_over_cross_sectional"] for c in comparisons
             if np.isfinite(c["mde_ratio_incumbent_over_cross_sectional"])]
    control = [r for r in rows if r["signal_key"] == "ibes:tgt_upside"]
    control_ok = all(r["long_short_spread_ann"] <= 0 for r in control
                     if r["horizon_months"] == 1)

    payload = {
        "trial": "REVINFO-1",
        "prereg": "TRIALS/PREREG_REVINFO_1.md",
        "layer": ("LAYER 1 — does the information exist. Licenses a Layer-2 "
                  "decision-boundary test and NOTHING else. No money claim, no "
                  "position, no capital."),
        "window": [FIRST, LAST],
        "horizons_months": list(HORIZONS),
        "segments": list(SEGMENTS),
        "arms": ARMS,
        "control_reproduced_its_kill": bool(control_ok),
        "rows": rows,
        "instrument_comparison": comparisons,
        "instrument_gain": {
            "measured_on": "the real panel, same signal and months as the incumbent",
            "min": round(min(gains), 3) if gains else None,
            "median": round(float(np.median(gains)), 3) if gains else None,
            "max": round(max(gains), 3) if gains else None,
            "synthetic_expectation": "1.29 to 1.52 (tests/test_information.py)",
        },
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "revision_information.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8")

    logger.info("=" * 72)
    logger.info("control (tgt_upside) reproduced its kill: %s", control_ok)
    if gains:
        logger.info("instrument gain on REAL data: %.2fx to %.2fx (median %.2f)",
                    min(gains), max(gains), float(np.median(gains)))
    for v in ("INFORMATION_PRESENT", "UNRESOLVED", "NO_INFORMATION"):
        logger.info("%-20s %d of %d", v,
                    sum(1 for r in rows if r["verdict"] == v), len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
