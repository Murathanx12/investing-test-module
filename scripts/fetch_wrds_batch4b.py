"""comp_pit follow-up: corrected table names from the saved catalog
(pitnamesus = US id/name map; pitqtrdataus = as-first-reported quarterly).
One Duo push. Usage: .venv\Scripts\python -m scripts.fetch_wrds_batch4b
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.wrds_conn import get_connection

RAW = MODULE_ROOT / "data" / "wrds_raw"


def main() -> None:
    manifest = {"fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    db = get_connection()
    try:
        for name, sql in [
            ("pit_names_us", "select * from comp_pit.pitnamesus"),
            ("pit_qtr_sample", "select * from comp_pit.pitqtrdataus limit 200000"),
        ]:
            t = time.time()
            try:
                df = db.raw_sql(sql)
                df.to_parquet(RAW / f"{name}.parquet")
                manifest[name] = {"rows": len(df), "cols": list(df.columns),
                                  "seconds": round(time.time() - t, 1)}
                print(f"[{name}] OK {len(df):,} rows", flush=True)
            except Exception as e:
                manifest[name] = {"error": str(e)[:300]}
                print(f"[{name}] FAILED: {e}", flush=True)
    finally:
        db.close()
        (RAW / "manifest_batch4b.json").write_text(json.dumps(manifest, indent=1, default=str))
        print(json.dumps({k: (v if isinstance(v, dict) and 'error' in v else
                              {kk: v[kk] for kk in ('rows', 'seconds')} if isinstance(v, dict) else v)
                          for k, v in manifest.items()}, indent=1, default=str))


if __name__ == "__main__":
    main()
