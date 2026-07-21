"""Forward calibration ledger v0 — register the FIRST real pre-registered calls.

Each call is a probabilistic forecast on a GENUINELY UPCOMING FDA decision (PDUFA date
in the future as of 2026-07-21), so registered_at < event_date holds and the call is
falsifiable — it will be Brier-scored forward via yfinance at maturity. The LLM reads an
entity-neutered situation and proposes P(stock beats market over 21 trading days); a
human-auditable rationale + kill condition are stored. The LLM never sizes a position.

Committing this file's output (ledger/forward_calls.jsonl) right after the run makes the
git timestamp the tamper-evidence that every call predates its event.

Upcoming PDUFA dates sourced 2026-07-21 from public biotech catalyst calendars
(marketbeat.com/fda-calendar). Provisional; each call records its own event date.

Usage:  .venv\\Scripts\\python -m scripts.ledger_register_v0
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.events.ledger import EventCall, EventLedger
from aegis_brain.llm.event_call import propose_call

LEDGER_PATH = MODULE_ROOT / "ledger" / "forward_calls.jsonl"
HORIZON = 21  # trading days
BASE_RATE = 0.50  # neutral prior: beating the market over 21d absent info ~ coin flip

# (event_id, ticker, event_date, neutered situation built ONLY from known facts)
EVENTS = [
    ("PDUFA-SCPH-2026-07-26", "SCPH", "2026-07-26",
     "A small commercial-stage drug company awaits an FDA decision on a supplemental "
     "label expansion for an already-marketed product. Label expansions are incremental "
     "and often already partly priced in."),
    ("PDUFA-REPL-2026-08-02", "REPL", "2026-08-02",
     "A single-asset clinical-stage biotech awaits an FDA decision (biologic) on its lead "
     "oncolytic immunotherapy for an advanced solid tumor. A first approval would be "
     "company-defining; a rejection would be severe given the single-asset concentration."),
    ("PDUFA-LNTH-2026-08-13", "LNTH", "2026-08-13",
     "A mid-cap diagnostics/imaging company awaits an FDA decision on a new imaging agent. "
     "The company is diversified with existing revenue, so one product is only moderately "
     "material to the whole."),
    ("PDUFA-SVRA-2026-08-22", "SVRA", "2026-08-22",
     "A small single-asset biotech awaits an FDA decision (biologic) on its first product, "
     "a treatment for a rare autoimmune lung disease. Approval would create the company's "
     "first revenue; rejection would be existential."),
    ("PDUFA-NUVL-2026-09-18", "NUVL", "2026-09-18",
     "A clinical-stage oncology biotech nearing its first-ever approval awaits an FDA "
     "decision on a selective kinase inhibitor for a genetically-defined lung cancer "
     "subset. Strong prior trial data; first-approval transition risk remains."),
    ("PDUFA-RARE-2026-09-19", "RARE", "2026-09-19",
     "An established rare-disease biotech with multiple programs awaits an FDA decision "
     "(biologic/gene therapy) for an ultra-rare pediatric disorder. The company is "
     "diversified, so the single decision is materially but not existentially important."),
    ("PDUFA-IONS-2026-09-22", "IONS", "2026-09-22",
     "A larger diversified RNA-therapeutics company with several marketed and pipeline "
     "products awaits an FDA decision for an ultra-rare neurological disease. Given the "
     "broad pipeline, this one product is not very material to the whole."),
]


def main() -> None:
    led = EventLedger(LEDGER_PATH)
    now = datetime.now(timezone.utc).isoformat()
    for event_id, ticker, event_date, situation in EVENTS:
        try:
            call = propose_call(situation, base_rate=BASE_RATE, horizon_days=HORIZON)
        except Exception as e:
            print(f"[{event_id}] LLM call FAILED: {type(e).__name__}: {e}", flush=True)
            continue
        ec = EventCall(
            event_id=event_id, ticker=ticker, event_type="PDUFA",
            event_date=event_date, prob_up=call["prob_up"], horizon_days=HORIZON,
            rationale=f'{call["rationale"]} [model={call["model"]}, base={call["base_rate"]}]',
            kill_condition=call["kill_condition"], registered_at=now,
        )
        try:
            led.register_call(ec)
            print(f"[{event_id}] {ticker} P(up,{HORIZON}d)={call['prob_up']:.2f} "
                  f"event={event_date} :: {call['rationale']}", flush=True)
        except ValueError as e:
            print(f"[{event_id}] rejected: {e}", flush=True)
    print(f"\nledger now holds {len(led.calls())} calls -> {LEDGER_PATH}", flush=True)


if __name__ == "__main__":
    main()
