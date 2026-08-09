"""TRIAL-COHERENCE-BATTERY-1 — run the policy-coherence battery.

Runs BEFORE any economics, per the design: a reasoner that cannot keep its own
directions straight fails here, cheaply. Passing is a gate, never evidence.

    python scripts/night3_coherence.py [--scenarios 60] [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.night3 import coherence as coh
from aegis_brain.night3.llmcache import LLMCache, SpendGuard, parse_json

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("coherence")

RUN_DIR = MODULE_ROOT / "runs" / "NIGHT3"
MODEL = "deepseek-chat"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", type=int, default=60)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--cap-usd", type=float, default=25.0)
    args = ap.parse_args()

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    guard = SpendGuard(args.cap_usd)
    cache = LLMCache(RUN_DIR / "cache", MODEL, guard)

    bases = coh.build_scenarios(args.scenarios)
    jobs = [(s, dim, side) for s in bases for dim in coh.DIRECTIONS
            for side in ("low", "high")]
    log.info("%d scenarios x %d directions x 2 sides = %d calls "
             "(cached ones are free)", len(bases), len(coh.DIRECTIONS), len(jobs))

    def run(job):
        s, dim, side = job
        p = coh.perturb(s, dim, side)
        system, user = coh.prompt(p)
        rec = cache.call(system, user, temperature=0.0, max_tokens=200,
                         tag=f"coh|{s.scenario_id}|{dim}|{side}")
        val = None
        if rec.get("ok"):
            try:
                d = parse_json(rec["raw"])
                val = float(d["expected_excess_return"])
            except (ValueError, KeyError, TypeError) as exc:
                log.warning("unparseable %s %s %s: %s", s.scenario_id, dim, side, exc)
        return {"scenario_id": s.scenario_id, "dimension": dim, "side": side,
                "value": val, "ok": val is not None}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        recs = list(pool.map(run, jobs))

    # assemble pairs — a pair is usable only if BOTH sides parsed
    byk = {(r["scenario_id"], r["dimension"], r["side"]): r for r in recs}
    pairs = []
    for s in bases:
        for dim in coh.DIRECTIONS:
            lo = byk.get((s.scenario_id, dim, "low"))
            hi = byk.get((s.scenario_id, dim, "high"))
            ok = bool(lo and hi and lo["ok"] and hi["ok"])
            pairs.append({"scenario_id": s.scenario_id, "dimension": dim,
                          "low": lo["value"] if lo else None,
                          "high": hi["value"] if hi else None, "ok": ok})

    result = {
        "trial": "TRIAL-COHERENCE-BATTERY-1",
        "prereg": "TRIALS/PREREG_NIGHT3_DECISION_REPLAY.md §5 (N3)",
        "model_id": MODEL, "temperature": 0.0,
        "n_scenarios": len(bases), "n_calls": len(jobs),
        "n_pairs": len(pairs), "n_pairs_usable": sum(p["ok"] for p in pairs),
        "grades": coh.grade(pairs),
        "cache": cache.stats(), "spend": guard.as_dict(),
    }
    (RUN_DIR / "COHERENCE_BATTERY.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8")
    (RUN_DIR / "coherence_pairs.json").write_text(
        json.dumps(pairs, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"grades": result["grades"], "spend": result["spend"],
                      "cache": result["cache"]}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
