"""INSTR-REGIME-ANALOG runner — current belief state + month-end backfill.

Descriptive, never arms. Current run -> data/factory/regime_analog_current.json
(narration-ready) + one BeliefState row appended to ledger/belief_states.jsonl.
--backfill rebuilds the month-end belief trajectory (stamped backfill=true)
so belief evolution exists from day one; it refuses to run twice.

Usage:
  .venv\\Scripts\\python -m scripts.run_regime_analog             # latest day
  .venv\\Scripts\\python -m scripts.run_regime_analog --date 2020-03-20
  .venv\\Scripts\\python -m scripts.run_regime_analog --backfill
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.macro.macro_analog import (BELIEF_LEDGER, append_belief,
                                            build_descriptors, compute_belief,
                                            robust_z)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = MODULE_ROOT / "data" / "factory"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--backfill", action="store_true")
    args = ap.parse_args()

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    z = robust_z(build_descriptors())
    zc = z.dropna()
    print(f"complete descriptor vectors: {len(zc)} days "
          f"({zc.index.min().date()} -> {zc.index.max().date()})")

    if args.backfill:
        done = set()
        if BELIEF_LEDGER.exists():
            done = {json.loads(ln)["query_date"]
                    for ln in BELIEF_LEDGER.read_text(encoding="utf-8").splitlines()
                    if ln.strip()}
        month_ends = zc.groupby(zc.index.to_period("M")).tail(1).index
        # need >= N_ANALOGS candidates before self-exclusion: skip the first ~2y
        month_ends = [d for d in month_ends if zc.index.get_loc(d) >= 63 + 50 * 2]
        n_new = 0
        for d in month_ends:
            if str(d.date()) in done:
                continue
            belief, _ = compute_belief(z, d, now, backfill=True)
            append_belief(belief)
            n_new += 1
        print(f"backfill: {n_new} month-end belief states appended "
              f"({len(month_ends) - n_new} already present)")
        return

    qd = pd.Timestamp(args.date) if args.date else zc.index.max()
    belief, detail = compute_belief(z, qd, now, backfill=False)
    append_belief(belief)
    payload = {"belief_state": belief.__dict__, "detail": detail}
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "regime_analog_current.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(json.dumps(payload, indent=2, default=str))
    print(f"\n-> {out_path}\n-> appended to {BELIEF_LEDGER}")


if __name__ == "__main__":
    main()
