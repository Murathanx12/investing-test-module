"""Score every pre-registration under R13e — the calendar axis.

    python -m scripts.audit_r13e_calendar            # table
    python -m scripts.audit_r13e_calendar --json out.json

WHY
===
N9's confirmation held out six securities and reused seventeen years, and the
number it produced (1.271, p=0.015) was the programme's only surviving
positive until the split that withdrew it. R13e refuses that design at
registration. The obvious next question is how many OTHER designs were built
the same way, and the honest way to answer it is a sweep, not a recollection.

WHAT IT CAN AND CANNOT SEE
==========================
R13e reads DECLARED windows. A document that never declared a selection window
cannot be scored — and that is the majority of them, because the field did not
exist until today. So the classes are:

  REFUSED_NOW     the document declares both windows and they overlap, or sit
                  inside each other's label reach. R13e would have stopped it.
  CLEAN           declared, disjoint, gap sufficient.
  UNDECLARED      makes a transfer claim and never says what it was selected
                  on. NOT a pass: it is the state N9 was in, and every one of
                  these needs its window written down before it is cited.
  LEGACY_TRANSFER_CLAIM
                  no `slice_purpose` at all (the field is younger than the
                  document) but the prose makes a transfer/holdout claim.
                  UNSCOREABLE. A reading list, not a verdict.
  NOT_APPLICABLE  claims no transfer (EXPLORE / REANALYSIS / PAIRED / silent).

The legacy bucket being the whole answer on 2026-08-16 — 41 of 124 documents,
REFUSED_NOW=0, CLEAN=0 — is the finding, not a defect in the sweep, and it is
the reason the count is printed with that caveat attached rather than as a
clean bill. The point of moving the axis to registration is that the bucket
empties going forward.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.discipline import prereg_power as PP

ROOTS = [
    Path(__file__).resolve().parents[1] / "TRIALS",
    Path(__file__).resolve().parents[2] / "aegis-finance" / "docs" / "TRIALS",
]

_CLASS = {
    "CALENDAR_OVERLAPPING_CONFIRMATION": "REFUSED_NOW",
    "CONFIRMATION_WINDOW_ABUTS_SELECTION": "REFUSED_NOW",
    "SELECTION_WINDOW_CONTRADICTS_PARENT": "REFUSED_NOW",
    "UNPARSEABLE_WINDOW": "REFUSED_NOW",
    "UNDECLARED_SELECTION_WINDOW": "UNDECLARED",
    "CALENDAR_DISJOINT": "CLEAN",
    "CALENDAR_DISJOINT_BY_CONSTRUCTION": "CLEAN",
    "CALENDAR_OVERLAPPING_FOREIGN_SLICE": "FOREIGN_OVERLAP",
    "NOT_APPLICABLE": "NOT_APPLICABLE",
}

#: The vocabulary is newer than the documents. Every pre-registration written
#: before 2026-08-16 predates `slice_purpose`, so R13e scores all of them
#: NOT_APPLICABLE — and a sweep that reports "0 refused" because it could not
#: read anything is the house failure mode with a report attached.
#:
#: So legacy documents are matched on the language of a transfer claim and
#: reported as UNSCOREABLE rather than clean. A keyword is not a purpose
#: declaration and is not treated as one: these are a READING LIST, not a
#: verdict.
_LEGACY_CLAIM_TERMS = (
    "confirmation slice", "confirm on", "confirmed on", "transfer",
    "held out", "holdout", "hold-out", "out-of-sample", "untouched securit",
    "unread securit", "foreign slice", "fresh securit", "in neither slice",
)


def audit(paths: list[Path]) -> list[dict]:
    rows = []
    for p in sorted(paths):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        r = PP.check_calendar_disjointness(text)
        sl = PP.check_slice_declaration(text)
        klass = _CLASS.get(r["verdict"], r["verdict"])
        hits = sorted({t for t in _LEGACY_CLAIM_TERMS if t in text.lower()})
        if klass == "NOT_APPLICABLE" and not r.get("slice_purpose") and hits:
            klass = "LEGACY_TRANSFER_CLAIM"
        rows.append({
            "path": str(p), "name": p.name,
            "class": klass, "legacy_terms": hits,
            "verdict": r["verdict"],
            "blocked": bool(r.get("blocked")),
            "slice_purpose": r.get("slice_purpose"),
            "slice_verdict": sl["verdict"],
            "selection_period": r.get("selection_period"),
            "slice_period": r.get("slice_period"),
            "overlap_days": r.get("overlap_days"),
            "gap_days": r.get("gap_days"),
            "required_gap_days": r.get("required_gap_days"),
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=None)
    ap.add_argument("--all", action="store_true",
                    help="print NOT_APPLICABLE rows too")
    a = ap.parse_args(argv)

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                        # noqa: BLE001
            pass

    paths = [p for root in ROOTS if root.exists()
             for p in root.glob("*.md")]
    rows = audit(paths)
    counts = Counter(r["class"] for r in rows)

    order = ["REFUSED_NOW", "UNDECLARED", "LEGACY_TRANSFER_CLAIM",
             "FOREIGN_OVERLAP", "CLEAN", "NOT_APPLICABLE"]
    for klass in order:
        sel = [r for r in rows if r["class"] == klass]
        if not sel or (klass == "NOT_APPLICABLE" and not a.all):
            continue
        print(f"\n=== {klass}  ({len(sel)}) ===")
        for r in sel:
            extra = ""
            if r["overlap_days"]:
                extra = f"  overlap {r['overlap_days']}d"
            elif r["gap_days"] is not None:
                extra = (f"  gap {r['gap_days']}d "
                         f"(need {r['required_gap_days']}d)")
            if klass == "LEGACY_TRANSFER_CLAIM":
                print(f"  {r['name']:<52s} "
                      f"{', '.join(r['legacy_terms'][:3])}")
            else:
                print(f"  {r['name']:<52s} {r['slice_purpose'] or '-':<10s} "
                      f"{r['verdict']}{extra}")

    print("\n" + "  ".join(f"{k}={counts.get(k, 0)}" for k in order))
    print(f"total documents scanned: {len(rows)}")
    print("\nLEGACY_TRANSFER_CLAIM = written before `slice_purpose` existed, "
          "so R13e cannot score it.\nThat is a reading list, not a clean bill: "
          "the gate reads declarations, and these have none.")
    print("UNDECLARED is not a pass either. It is the state N9's Amendment 1 "
          "was in\nwhen it produced 1.271: a transfer claim with no recorded "
          "selection window,\nwhich nothing could check.")

    if a.json:
        Path(a.json).write_text(
            json.dumps({"rows": rows, "counts": dict(counts)}, indent=2),
            encoding="utf-8")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
