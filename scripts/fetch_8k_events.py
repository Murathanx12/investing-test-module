"""TRIAL-EVENT-8K-FILTER step 1 — walk EDGAR DAILY indexes 2004-2024 for 8-K rows.

Daily indexes ONLY (frozen spec: full/quarterly indexes are retroactively rebuilt
and BANNED as the event source). Every fetch goes through the single paced,
identified choke-point in aegis_brain.events.edgar_sec.

Usage: .venv\\Scripts\\python -m scripts.fetch_8k_events
Output: data/events/edgar_8k_daily_index.parquet
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.events.edgar_8k import harvest_daily_8k
from aegis_brain.events.edgar_sec import STATS

START_YEAR, END_YEAR = 2004, 2024


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        stream=sys.stdout)
    t0 = time.time()
    out_dir = MODULE_ROOT / "data" / "events"
    out_dir.mkdir(parents=True, exist_ok=True)

    cache = out_dir / "_8k_year_cache"
    cache.mkdir(exist_ok=True)
    df, audit = harvest_daily_8k(START_YEAR, END_YEAR, cache_dir=cache)
    path = out_dir / "edgar_8k_daily_index.parquet"
    df.to_parquet(path, index=False)

    meta = {
        "window": f"{START_YEAR}-{END_YEAR}",
        "walk_audit": audit,
        "n_rows": int(len(df)),
        "n_originals": int((~df["is_amendment"]).sum()),
        "n_amendments": int(df["is_amendment"].sum()),
        "n_distinct_cik": int(df["cik"].nunique()),
        "first_date": str(df["date_filed"].min().date()),
        "last_date": str(df["date_filed"].max().date()),
        "fetch_stats": dict(STATS),
        "elapsed_s": round(time.time() - t0, 1),
    }
    (out_dir / "edgar_8k_daily_index_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == "__main__":
    main()
