"""Write the committable half of a night: hashes, receipts, claim coverage.

    python scripts/make_night_manifest.py NIGHT7 --doc docs/NIGHT7_VERDICT_2026-08-10.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.discipline.manifest import (build, calibrate, claim_coverage,
                                             walk_scalars)

OUT = MODULE_ROOT / "docs" / "manifests"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("night")
    ap.add_argument("--doc", action="append", default=[],
                    help="verdict document(s) to claim-check against the receipts")
    ap.add_argument("--also", action="append", default=[],
                    help="earlier run dirs whose receipts may legitimately be "
                         "quoted (e.g. --also NIGHT6 --also G7)")
    a = ap.parse_args()

    man = build(MODULE_ROOT / "runs" / a.night, MODULE_ROOT, a.night)
    scalars = {f"{n}:{p}": v for n, b in man["receipts"].items()
               for p, v in walk_scalars(b)}

    prior: dict[str, float] = {}
    for other in a.also:
        try:
            om = build(MODULE_ROOT / "runs" / other, MODULE_ROOT, other)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"  (skipping --also {other}: {e})")
            continue
        prior.update({f"{other}/{n}:{p}": v for n, b in om["receipts"].items()
                      for p, v in walk_scalars(b)})
    man["prior_nights_consulted"] = a.also
    man["prior_scalar_count"] = len(prior)

    if a.doc:
        # the instrument's own error rate, computed on THIS pool, every time
        man["claim_check_calibration"] = calibrate(scalars, prior)
        man["claim_check"] = {}
        for rel in a.doc:
            p = MODULE_ROOT / rel
            if not p.exists():
                man["claim_check"][rel] = {"error": "not found"}
                continue
            man["claim_check"][rel] = claim_coverage(
                p.read_text(encoding="utf-8"), scalars, prior=prior)

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"{a.night}_MANIFEST.json"
    dest.write_text(json.dumps(man, indent=2), encoding="utf-8")

    print(f"{a.night}: {man['artifact_count']} artifacts, "
          f"{man['scalar_count']} scalars, code {man['code_sha'][:12]}")
    for rel, cc in man.get("claim_check", {}).items():
        if "error" in cc:
            print(f"  {rel}: {cc['error']}")
            continue
        print(f"  {rel}: {cc['claims_found']} numbers — "
              f"{cc['informatively_backed']} informatively backed, "
              f"{cc['matched_but_uninformative']} matched-but-uninformative, "
              f"{cc['unbacked_anywhere']} UNBACKED")
        for u in cc["unbacked"]:
            print(f"      line {u['line']:4d}  {u['raw']}   (unbacked)")
    print(f"-> {dest.relative_to(MODULE_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
