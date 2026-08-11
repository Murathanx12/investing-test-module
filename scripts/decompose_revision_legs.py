"""REVINFO-1, decomposed into the leg a long-only book can hold and the one it
cannot.

WHY THIS RUNS BEFORE ANYTHING IS BUILT ON REVISIONS
====================================================

REVINFO-1 found analyst-revision information in small caps out to about six
months: `tgt_rev_breadth` small at +9.36 %/yr against its own MDE of 5.76. Every
one of those numbers is a **dollar-neutral, unconstrained** spread. Round 16
measured 88 to 99.9% of a comparable spread living in the short leg — the leg a
long-only product cannot hold. If that is true here too, the Layer-1 pass is
real and the product is still dead, and it is far cheaper to learn that now than
after an exposure controller, a belief state and a lane have been built on it.

WHAT THIS IS AND IS NOT
-----------------------
It is a DECOMPOSITION of an already-registered result, not a new hypothesis. It
re-partitions the exact series REVINFO-1 already estimated, using the same
weights, over the same months, with the same estimator. It can only ever
subtract from what REVINFO-1 claimed — there is no outcome here that promotes
anything. So it **does not accrue to the search denominator**, on the same
footing as `scripts/audit_power_hac.py`.

The registered decision rule, stated before the numbers were seen:

* the long leg clears its OWN MDE  -> LONG_LEG_SURVIVES. The revision family
  remains a candidate for a long-only product, still gross of costs, still
  Layer 1, and still owing a Layer-2 decision-boundary test.
* the long leg does NOT clear it   -> LONG_LEG_UNRESOLVED. This is absence of
  evidence and NOT a kill (CANON §19) — but it is also not permission. Nothing
  long-only may be built on the family until an adequately powered long-leg
  test exists.

The share of the spread sitting in the short leg is DESCRIPTIVE and carries no
standard error. The claim that one leg carries more than the other is a claim
about their DIFFERENCE and is read off the paired difference series with its own
SE (CANON §18) — never off the share.

    python -m scripts.decompose_revision_legs

Writes runs/REVINFO/leg_decomposition.json.
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
from aegis_brain.pf.information import cross_sectional_information
from aegis_brain.pf.run import Factory
from scripts.run_revision_information import (ARMS, FIRST, HORIZONS, LAST,
                                              SEGMENTS)

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "REVINFO"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    fac = Factory(FIRST, LAST, out_dir=OUT)
    frames = fac.lib._ibes()
    ret = fac.spine.panel.monthly_ret

    rows = []
    for key, note in ARMS.items():
        if key not in frames:
            logger.warning("%s not in the IBES panel — skipped", key)
            continue
        for seg in SEGMENTS:
            elig = fac.eligible(seg)
            for h in HORIZONS:
                res = cross_sectional_information(
                    frames[key], ret, eligible=elig, horizon=h,
                    name=f"{key}|{seg}|h{h}")
                legs = res.diagnostics.get("long_only_decomposition")
                if legs is None:
                    continue
                if not legs["legs_sum_to_spread"]:
                    raise RuntimeError(
                        f"{key}|{seg}|h{h}: the legs do not sum to the spread "
                        f"they decompose — the partition is wrong and every "
                        f"share below would be wrong by an unknown amount")
                rows.append({
                    "signal_key": key, "segment": seg, "horizon_months": h,
                    "arm_note": note,
                    "spread_ann": res.long_short_spread_ann,
                    "spread_t": res.long_short_spread_t,
                    "spread_mde_ann": res.long_short_spread_mde_ann,
                    "spread_verdict": res.verdict,
                    **legs,
                })
                logger.info(
                    "%-24s %-8s h%-2d: spread %+6.2f  long %+6.2f (MDE %5.2f, "
                    "t %s)  short %+6.2f  -> %s",
                    key, seg, h, 100 * res.long_short_spread_ann,
                    100 * legs["long_leg_ann"], 100 * legs["long_leg_mde_ann"],
                    f"{legs['long_leg_t']:+.2f}"
                    if legs["long_leg_t"] is not None else " n/a",
                    100 * legs["short_leg_ann"], legs["verdict"])

    # The headline is taken on the arms REVINFO-1 actually licensed. An arm that
    # was UNRESOLVED at Layer 1 has nothing to decompose.
    licensed = [r for r in rows if r["spread_verdict"] == "INFORMATION_PRESENT"]
    survived = [r for r in licensed if r["verdict"] == "LONG_LEG_SURVIVES"]
    shares = [r["short_leg_share_of_spread"] for r in licensed
              if r["short_leg_share_of_spread"] is not None]
    diffs = [r for r in licensed if r["difference_is_detectable"]]

    payload = {
        "trial": "REVINFO-1 leg decomposition",
        "parent": "TRIALS/PREREG_REVINFO_1.md",
        "accrues_to_denominator": 0,
        "why_zero": ("a re-partition of an already-registered result, using the "
                     "same weights over the same months; no outcome here can "
                     "promote anything, only subtract"),
        "window": [FIRST, LAST],
        "horizons_months": list(HORIZONS),
        "segments": list(SEGMENTS),
        "n_licensed_arms": len(licensed),
        "n_licensed_arms_whose_long_leg_survives": len(survived),
        "short_leg_share_across_licensed_arms": {
            "min": round(min(shares), 4) if shares else None,
            "median": round(float(np.median(shares)), 4) if shares else None,
            "max": round(max(shares), 4) if shares else None,
            "round_16_comparison": "0.88 to 0.999 for a comparable spread",
            "note": "descriptive only, no SE — see difference_* for the claim",
        },
        "n_licensed_arms_with_a_detectable_leg_difference": len(diffs),
        "rows": rows,
        "licenses": (
            "Still LAYER 1 and still gross of all costs. A surviving long leg "
            "licenses a Layer-2 decision-boundary test for a long-only book. It "
            "licenses no money claim, no position and no capital."),
        "runtime_secs": round(time.time() - t0, 1),
    }
    (OUT / "leg_decomposition.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8")

    logger.info("=" * 72)
    logger.info("licensed arms: %d   long leg survives in: %d",
                len(licensed), len(survived))
    if shares:
        logger.info("short-leg share across licensed arms: %.1f%% to %.1f%% "
                    "(median %.1f%%)  [Round 16: 88-99.9%%]",
                    100 * min(shares), 100 * max(shares),
                    100 * float(np.median(shares)))
    logger.info("leg difference detectable in %d of %d licensed arms",
                len(diffs), len(licensed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
