"""Does the PF-4 engine patch reproduce every banked PF-2 scorecard exactly?

The patch added two things (`delist_stub`, `holdings_out`) that are supposed to
be inert at their defaults. "Supposed to be" is not evidence. This script is the
evidence: it re-runs the banked specs through the patched engine and compares
every headline field. Any difference at all is a defect, not a rounding issue —
the engine is deterministic.
"""
from __future__ import annotations
import json, logging, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.WARNING)
from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.run import Factory
from aegis_brain.pf.spec import StrategySpec

TARGETS = [
    ("runs/PF2/PF-PROF-COMPOSITE-150__a1265dc617fb.json", "a1265dc617fb"),
    ("runs/PF2/PF-PROF-COMPOSITE-150__N100__8d232bc997b8.json", "8d232bc997b8"),
    ("runs/PF2/PF-ENGINE-ALPHA-2__9f837511b1c0.json", "9f837511b1c0"),
]

def spec_of(card: dict) -> StrategySpec:
    d = dict(card["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = tuple(d.get("tags", ()))
    return StrategySpec(**d)

def main() -> int:
    f = Factory()
    out, all_ok = [], True
    for rel, want_hash in TARGETS:
        banked = json.loads((MODULE_ROOT / rel).read_text(encoding="utf-8"))
        spec = spec_of(banked)
        got_hash = spec.spec_hash()
        t0 = time.time()
        card = f.run(spec, write=False)
        diffs = {k: [card["headline"][k], v]
                 for k, v in banked["headline"].items()
                 if card["headline"][k] != v}
        diffs.update({f"impl.{k}": [card["implementation"].get(k), banked["implementation"].get(k)]
                      for k in ("forced_liquidations", "turnover_1way_annual",
                                "cost_drag_annual_bps", "months")
                      if card["implementation"].get(k) != banked["implementation"].get(k)})
        ok = (got_hash == want_hash) and not diffs
        all_ok &= ok
        out.append({"artifact": rel, "spec_hash_ok": got_hash == want_hash,
                    "spec_hash": got_hash, "headline_identical": not diffs,
                    "diffs": diffs, "secs": round(time.time() - t0, 1)})
        print(f"{'OK  ' if ok else 'FAIL'} {rel} ({out[-1]['secs']}s)", flush=True)
        if diffs:
            print("   ", json.dumps(diffs), flush=True)
    res = {"trial": "TRIAL-PF4-DECOMPOSITION-1", "check": "engine-patch-inert",
           "all_reproduce": bool(all_ok), "targets": out}
    (MODULE_ROOT / "runs" / "PF4" / "REGRESSION.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({"all_reproduce": all_ok}, indent=2))
    return 0 if all_ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
