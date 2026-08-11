"""ARENA null bar — what does best-of-384 look like when NOTHING predicts anything?

NIGHT-10 found that the published "+4.87 %/yr false-discovery bar" does not
trace to the receipt it describes. `synthetic_results.json → null_calibration`
says **+2.73 %/yr**, and that is ONE seed; the three-seed power curve gives
+2.73 / +4.16 / +7.43. The published +4.87 is numerically the REAL-DATA
equal-weight control — which is also the separately-published "4th of 384" — so
two of the four headline numbers were one measurement counted twice.

A best-of-N maximum is a sample from an extreme-value distribution, and three
draws of it spanning 2.7-7.4 %/yr is not a bar. This script draws it properly.

    python -m scripts.arena_null_bar [--seeds 60]

Writes runs/ARENA1/null_bar.json. Scores nothing real, selects nothing, and
changes no verdict on its own: it replaces a point estimate with the
distribution that estimate was pretending to summarise.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

from aegis_brain.config import MODULE_ROOT
from scripts.arena_power_curve import (  # noqa: E402
    TRUTH_WORLD, _genomes_from, _replant, _score_world, load_manifest,
)

logger = logging.getLogger(__name__)
OUT = MODULE_ROOT / "runs" / "ARENA1" / "null_bar.json"

#: The bar a real result must clear. A genome that beats what pure noise
#: produces only 50% of the time has cleared nothing; the operating point is
#: the upper tail of the null maximum.
BAR_PERCENTILE = 95


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=60)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT.parent.mkdir(parents=True, exist_ok=True)

    genomes = _genomes_from(load_manifest())
    t0 = time.time()
    draws: list[dict] = []
    for i in range(a.seeds):
        seed = 20260811 + 1000 * i
        # effect 0.0 == the null world: the signal carries no information, and
        # the same generator, genome pool and scorer the real arena used.
        world = _replant(TRUTH_WORLD, seed=seed, effect=0.0)
        rows = _score_world(world, genomes)
        noise = [r["excess"] for r in rows if not r["is_truth"]]
        allx = [r["excess"] for r in rows]
        if not noise:
            continue
        draws.append({"seed": seed,
                      "best_of_pool": round(float(max(allx)), 5),
                      "best_noise": round(float(max(noise)), 5),
                      "median": round(float(np.median(allx)), 5)})
        if (i + 1) % 10 == 0:
            logger.info("%d/%d seeds, running best-of-pool mean %.4f",
                        i + 1, a.seeds,
                        float(np.mean([d["best_of_pool"] for d in draws])))

    best = np.array([d["best_of_pool"] for d in draws], dtype=float)
    pcts = {f"p{q}": round(float(np.percentile(best, q)), 5)
            for q in (5, 25, 50, 75, 90, 95, 99)}
    bar = float(np.percentile(best, BAR_PERCENTILE))

    payload = {
        "question": ("what does the MAXIMUM over the frozen 384-genome pool "
                     "look like when nothing predicts anything?"),
        "supersedes": ("the single-seed +2.73%/yr in synthetic_results.json "
                       "null_calibration, and the +4.87%/yr published as the "
                       "false-discovery bar, which was in fact the real-data "
                       "equal-weight control genome"),
        "n_seeds": len(draws),
        "n_genomes": len(genomes),
        "world": f"{TRUTH_WORLD} replanted at effect 0.0 (the null)",
        "runtime_secs": round(time.time() - t0, 1),
        "best_of_pool": {
            "mean": round(float(best.mean()), 5),
            "sd": round(float(best.std(ddof=1)), 5),
            "min": round(float(best.min()), 5),
            "max": round(float(best.max()), 5),
            **pcts,
        },
        "bar_percentile": BAR_PERCENTILE,
        "false_discovery_bar_ann": round(bar, 5),
        "reading": (
            f"Across {len(draws)} null worlds the best of 384 genomes averages "
            f"{100*best.mean():.2f} %/yr and ranges "
            f"{100*best.min():.2f} to {100*best.max():.2f}. The operating bar "
            f"at the {BAR_PERCENTILE}th percentile is {100*bar:.2f} %/yr: a "
            f"real best-of-384 below that is indistinguishable from what noise "
            f"produces. Quoting any single draw of this maximum as 'the bar' "
            f"understates it {100*(bar/best.mean()-1):.0f}% of the way to the "
            f"tail at the mean, and by more below it."),
        "caveat": (
            "This is the bar for a SELECTED MAXIMUM over this specific frozen "
            "pool of 384 genomes. A different pool size has a different bar, "
            "and it must be recomputed rather than carried over — the whole "
            "point of an extreme-value bar is that it scales with how many "
            "chances were taken."),
        "draws": draws,
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in
                      ("n_seeds", "best_of_pool", "false_discovery_bar_ann",
                       "reading")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
