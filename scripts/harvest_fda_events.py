"""Harvest FDA original-approval events 2002+ into a parquet event table.

Data plumbing only. Respects openFDA unauthenticated limits (1,000 req/day);
a full 2002-2026 harvest is ~a few hundred requests.

Usage:
    .venv\\Scripts\\python -m scripts.harvest_fda_events [start_year] [end_year]
Output:
    data/events/fda_approvals.parquet + stats.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.events.fda import events_to_records, fetch_fda_approvals

OUT = MODULE_ROOT / "data" / "events"


def main() -> None:
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 2002
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    t0 = time.time()
    frames = []
    for year in range(start, end + 1):
        events = fetch_fda_approvals(year)
        print(f"{year}: {len(events)} approvals", flush=True)
        frames.append(pd.DataFrame(events_to_records(events)))
    df = pd.concat(frames, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    existing = OUT / "fda_approvals.parquet"
    if existing.exists():  # merge chunked harvests, newest fetch wins
        df = (
            pd.concat([pd.read_parquet(existing), df], ignore_index=True)
            .drop_duplicates("application_number", keep="last")
            .sort_values("approval_date", ignore_index=True)
        )
    df.to_parquet(existing)
    stats = {
        "built_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "years": f"{start}-{end}",
        "events": len(df),
        "priority_share": round(float((df["review_priority"] == "PRIORITY").mean()), 3),
        "unique_sponsors": int(df["sponsor_name"].nunique()),
        "build_seconds": round(time.time() - t0, 1),
    }
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
