"""Score matured forward calls and print the calibration record.

Run this periodically (e.g. weekly cron). It scores any call whose horizon has fully
elapsed AND for which yfinance has data, appends to the scored file, and prints the
running Brier score + calibration table. Calls not yet matured stay pending (never a
faux-0). This is the forward clock — the only thing that earns conviction.

Usage:  .venv\\Scripts\\python -m scripts.ledger_score
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.events.ledger import EventLedger
from aegis_brain.events.realized import realized_fn

LEDGER_PATH = MODULE_ROOT / "ledger" / "forward_calls.jsonl"


def main() -> None:
    led = EventLedger(LEDGER_PATH)
    calls = led.calls()
    today = date.today().isoformat()
    print(f"ledger: {len(calls)} registered calls; scoring as of {today}", flush=True)

    newly = led.score_matured(realized_fn, as_of=today)
    print(f"newly scored this run: {len(newly)}", flush=True)
    for s in newly:
        print(f"  {s.event_id}: p={s.prob_up:.2f} realized={s.realized_return:+.3f} "
              f"outcome={s.outcome} brier={s.brier:.3f}", flush=True)

    scored = led.scored()
    if scored:
        summ = led.calibration_summary()
        print("\n=== calibration record ===", flush=True)
        print(json.dumps(summ, indent=2, default=str), flush=True)
    else:
        pending = len(calls)
        print(f"\nNo matured calls yet — {pending} pending. Earliest matures ~21 trading "
              f"days after its event date. The record builds forward; check back after "
              f"the first PDUFA window closes.", flush=True)


if __name__ == "__main__":
    main()
