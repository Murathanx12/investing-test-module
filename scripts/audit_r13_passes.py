"""Re-score every pre-registration that R13 has ever seen, under R13b + R13c.

    python -m scripts.audit_r13_passes            # table
    python -m scripts.audit_r13_passes --json out.json

WHY
===
R13 passed N20 at a claimed 0.46pp floor when the honest bootstrap MDE was
0.895-1.306pp, because `n_available = freq x years` took "independent
episodes" on the author's word. That is SS41 (`n_effective = n`) inside the
gate built to prevent SS41 — and **inverted**. A false KILL looks conservative
and attracts scrutiny; every one of the five was caught. A false PASS lets
unresolvable work proceed, and nobody goes looking, because the work produces
a result that looks fine.

So "every prior pass is suspect" is not a sentence to put in a report. It is a
sweep, and this is the sweep.

WHAT IT REFUSES TO DO
=====================
It does **not** flip a verdict on every document whose numbers moved. A design
with 200x headroom is not made unsound by a 3x correction, and re-opening it
would be manufacturing a retrospective crisis out of arithmetic that never
mattered. The report separates:

  CHANGED_VERDICT   the gate's answer is different now — these need re-reading
  MATERIAL          same answer, but headroom fell below 20x — the count was
                    load-bearing and the design deserves a second look
  IMMATERIAL        the correction moved nothing that could have decided it
  UNCHECKABLE       the document never declared power fields at all, so R13
                    never scored it and there is nothing to re-score

The distinction is the finding. "Which passes were actually at risk" is a
smaller and far more useful set than "which passes existed".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aegis_brain.discipline import prereg_power as PP

ROOTS = [
    Path(__file__).resolve().parents[1] / "TRIALS",
    Path(__file__).resolve().parents[2] / "aegis-finance" / "docs" / "TRIALS",
]

#: Below this, the supplied observation count was load-bearing: a dependence
#: the author did not declare could have flipped the gate on its own.
MATERIAL_HEADROOM = PP.DEPENDENCE_DECLARATION_HEADROOM


def _legacy_verdict(text: str) -> dict:
    """What R13 said BEFORE R13b/R13c — freq x years, taken on trust.

    Reimplemented here rather than kept as a flag in the live gate, because a
    gate that can still be asked for its old answer is a gate with its old
    answer still in it.
    """
    f = PP.parse_power_fields(text)
    if f["missing"]:
        return {"verdict": "MISSING_POWER_FIELDS", "n_available": None,
                "floor": None}
    n_avail = float(f["event_frequency_per_year"]) * float(f["corpus_years"])
    need = PP.n_required(f["declared_effect_size_pp"], f["outcome_dispersion_pp"])
    floor = PP.resolvable_effect(n_avail, f["outcome_dispersion_pp"])
    if need is None:
        return {"verdict": "MISSING_POWER_FIELDS", "n_available": n_avail,
                "floor": floor}
    return {
        "verdict": ("UNPOWERED_AT_REGISTRATION" if need > n_avail
                    else "RESOLVABLE"),
        "n_available": n_avail, "n_required": need, "floor": floor,
    }


def audit(paths: list[Path]) -> list[dict]:
    rows = []
    for p in sorted(paths):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        old = _legacy_verdict(text)
        new = PP.check_resolvability(text)

        if old["verdict"] == "MISSING_POWER_FIELDS" and \
                new["verdict"] == "MISSING_POWER_FIELDS":
            klass = "UNCHECKABLE"
        elif old["verdict"] != new["verdict"]:
            klass = "CHANGED_VERDICT"
        else:
            need = new.get("n_required")
            avail = new.get("n_available")
            headroom = (avail / need) if (need and avail and need > 0) else None
            klass = ("MATERIAL" if headroom is not None
                     and headroom < MATERIAL_HEADROOM else "IMMATERIAL")

        need = new.get("n_required")
        avail = new.get("n_available")
        rows.append({
            "path": str(p),
            "name": p.name,
            "class": klass,
            "old_verdict": old["verdict"],
            "new_verdict": new["verdict"],
            "old_n_available": old.get("n_available"),
            "new_n_available": avail,
            "n_required": need,
            "old_floor_pp": old.get("floor"),
            "new_floor_pp": new.get("smallest_resolvable_effect_pp"),
            "headroom": ((avail / need) if (need and avail and need > 0)
                         else None),
            "overlap_factor": new.get("overlap_factor"),
            "dependence_unit": new.get("dependence_unit"),
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                        # noqa: BLE001
            pass

    paths: list[Path] = []
    for root in ROOTS:
        if root.exists():
            paths.extend(root.glob("*.md"))
    print(f"scanning {len(paths)} pre-registration documents in "
          f"{len([r for r in ROOTS if r.exists()])} roots\n")

    rows = audit(paths)
    order = {"CHANGED_VERDICT": 0, "MATERIAL": 1, "IMMATERIAL": 2,
             "UNCHECKABLE": 3}
    rows.sort(key=lambda r: (order[r["class"]], r["name"]))

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["class"]] = counts.get(r["class"], 0) + 1

    scored = [r for r in rows if r["class"] != "UNCHECKABLE"]
    print(f"{len(scored)} documents declared power fields and were scored by "
          f"R13; {counts.get('UNCHECKABLE', 0)} never were.\n")

    for klass in ("CHANGED_VERDICT", "MATERIAL", "IMMATERIAL"):
        sel = [r for r in rows if r["class"] == klass]
        if not sel:
            continue
        print(f"── {klass}  ({len(sel)}) " + "─" * (52 - len(klass)))
        for r in sel:
            head = (f"{r['headroom']:.1f}x" if r["headroom"] else "  n/a")
            print(f"  {r['name'][:56]:<56s} {head:>7s}")
            if klass != "IMMATERIAL":
                print(f"      {r['old_verdict']} -> {r['new_verdict']}   "
                      f"n_avail {r['old_n_available'] or 0:.0f} -> "
                      f"{r['new_n_available'] or 0:.0f}"
                      + (f"   floor {r['old_floor_pp']:.3g} -> "
                         f"{r['new_floor_pp']:.3g}pp"
                         if r["old_floor_pp"] and r["new_floor_pp"] else ""))
                if r["overlap_factor"]:
                    print(f"      overlap {r['overlap_factor']:.1f}x at the "
                          f"declared horizon")
                if not r["dependence_unit"]:
                    print("      no dependence unit declared")
        print()

    print("READ THIS AS: CHANGED_VERDICT needs re-reading before its result is "
          "cited.\nMATERIAL kept its verdict but its margin was thin enough "
          "that the supplied\ncount was load-bearing. IMMATERIAL had enough "
          "headroom that no plausible\ndependence correction could have "
          "decided it, and re-opening those would be\nmanufacturing a crisis "
          "out of arithmetic that never mattered.")

    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
