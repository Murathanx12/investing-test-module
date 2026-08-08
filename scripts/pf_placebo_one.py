"""One PF-1 placebo band, in its own process — Phase B, parallelized.

Identical computation to the campaign's Phase B (same spec, same 100 draws,
same seeds, same rho search); only the scheduling changes, so nothing in the
pre-registration moves. Phase A cards are read from disk, so nothing is
recomputed.

    python scripts/pf_placebo_one.py PF-ENGINE-ALPHA
"""
from __future__ import annotations

import glob
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import controls as ctrl
from aegis_brain.pf.panel63 import eligibility, load_spine
from aegis_brain.pf.run import Factory
from scripts.pf_run_batch1 import BASES, FIRST, LAST, PLACEBO_DRAWS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("placebo")


def base_card(name: str) -> dict:
    hits = [p for p in glob.glob(str(MODULE_ROOT / "runs" / "PF" / f"{name}__*.json"))
            if Path(p).stem.count("__") == 1]
    if not hits:
        raise SystemExit(f"no Phase A card for {name}")
    return json.loads(Path(hits[0]).read_text(encoding="utf-8"))


def main() -> int:
    name = sys.argv[1]
    spec = next(b for b in BASES if b.name == name)
    out_path = MODULE_ROOT / "runs" / "PF" / f"PLACEBO_{name}.json"
    if out_path.exists():
        log.info("%s exists — write-once", out_path.name)
        return 0

    card = base_card(name)
    turnover = card["implementation"]["turnover_1way_annual"]
    excess = card["headline"]["excess_cagr_net"]

    spine = load_spine(FIRST, LAST)
    elig = eligibility(spine, spec.segment)
    cost_frame = None
    if spec.cost_model == "ko":
        cost_frame = Factory(FIRST, LAST).cost_frame()

    band = ctrl.placebo_band(spine.panel, elig, spec, spine.rf, cost_frame,
                             spine.mkt, turnover, n_draws=PLACEBO_DRAWS)
    verdict = ctrl.placebo_verdict(excess, band)
    out = {"strategy": name, "spec_hash": card["spec_hash"],
           "band": band, "verdict": verdict}
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    log.info("%s: strategy %+.2f%% vs placebo p95 %+.2f%% max %+.2f%% -> %s",
             name, 100 * excess, 100 * band["excess_cagr"]["p95"],
             100 * band["excess_cagr"]["max"],
             "PASS" if verdict["PASS"] else "FAIL")
    print(json.dumps(out["verdict"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
