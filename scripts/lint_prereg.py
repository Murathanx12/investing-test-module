"""Run the corpse check on a preregistration before it accrues on data.

    python scripts/lint_prereg.py TRIALS/PREREG_N1_RANKER_VS_COMPOSITE.md

Exit code 1 on BLOCKED so a hook or CI can stop on it; 0 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from aegis_brain.discipline.prereg_lint import lint, load_corpus


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="+")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    worst = 0
    for rel in a.path:
        p = Path(rel)
        if not p.is_absolute():
            p = MODULE_ROOT / rel
        corpus = load_corpus(exclude=p)          # never match a file to itself
        res = lint(p.read_text(encoding="utf-8"), corpus=corpus)
        if a.json:
            print(json.dumps({"file": rel, **res}, indent=2))
        else:
            print(f"\n{p.name}: {res['verdict']}  "
                  f"(vs {res['corpus_size']} prior experiments)")
            print(f"  {res['why']}")
            for m in res["matches"]:
                mark = ("DUPLICATE" if m in res["duplicates"]
                        else "BLOCK" if m in res["blocking"]
                        else "RESURRECT" if m in res["resurrections"]
                        else "near")
                print(f"   [{mark:9s}] {m['similarity']:.3f}  "
                      f"{m['source']:9s} {m['verdict']:22s} {m['id']}")
                if m.get("declared_new_instrument"):
                    print(f"               declared new instrument: "
                          f"{m['declared_new_instrument']}")
                why = (m.get("detail") or {}).get("why") \
                    or (m.get("detail") or {}).get("hypothesis")
                if why:
                    print(f"               {str(why)[:150]}")
        worst = max(worst, 1 if res["verdict"] == "BLOCKED" else 0)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
