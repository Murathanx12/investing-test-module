"""Prove the holdout was not read — by checking artifacts, not by asserting it.

Two independent checks, because a single one can be satisfied by accident:

1. **Every experience** carries both a decision timestamp and a resolution
   timestamp. Both must fall strictly before 2023-01-01. A resolution inside the
   holdout would mean an outcome from the locked window reached the store even
   if the decision did not.
2. **Every cached prompt** is scanned for a real post-2022 date string. The
   synthetic scenarios deliberately use fabricated 2100+ dates, so the pattern
   is restricted to plausible ones.

Exit code is non-zero on any violation, so this can gate a commit.

    python scripts/night3_verify_holdout.py
"""
from __future__ import annotations

import glob
import json
import pathlib
import re
import sys

HOLDOUT_FIRST = "2023-01-01"
RUN_DIR = pathlib.Path(__file__).resolve().parents[1] / "runs" / "NIGHT3"
REAL_FUTURE_DATE = re.compile(r"\b20(2[3-9]|[3-9]\d)-\d\d")


def main() -> int:
    violations: list[str] = []
    report: dict = {"holdout_first": HOLDOUT_FIRST, "stores": {}, "prompts": {}}

    stores = sorted(glob.glob(str(RUN_DIR / "experiences_*.jsonl")))
    if not stores:
        print("no experience stores found — nothing to verify")
        return 1
    for f in stores:
        mx_ts = mx_res = ""
        n = 0
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                n += 1
                mx_ts = max(mx_ts, r["ts"])
                mx_res = max(mx_res, r["resolved_ts"])
        name = pathlib.Path(f).name
        report["stores"][name] = {"n": n, "max_decision": mx_ts,
                                  "max_resolution": mx_res}
        print(f"{name:<34} n={n:<6} max decision {mx_ts}  max resolution {mx_res}")
        if mx_ts >= HOLDOUT_FIRST or mx_res >= HOLDOUT_FIRST:
            violations.append(f"{name}: touches the holdout")

    hits: list[str] = []
    cached = glob.glob(str(RUN_DIR / "cache" / "*" / "*.json"))
    for f in cached:
        d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        blob = (d.get("user") or "") + (d.get("system") or "")
        if REAL_FUTURE_DATE.search(blob):
            hits.append(pathlib.Path(f).name)
    report["prompts"] = {"scanned": len(cached), "with_2023plus_date": len(hits),
                         "examples": hits[:5]}
    print(f"\ncached prompts scanned: {len(cached)}; containing a real 2023+ "
          f"date: {len(hits)}")
    if hits:
        violations.append(f"{len(hits)} cached prompts contain a 2023+ date")

    report["verdict"] = "HOLDOUT CLEAN" if not violations else "VIOLATIONS"
    report["violations"] = violations
    (RUN_DIR / "HOLDOUT_VERIFICATION.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print(report["verdict"])
    return 0 if not violations else 2


if __name__ == "__main__":
    sys.exit(main())
