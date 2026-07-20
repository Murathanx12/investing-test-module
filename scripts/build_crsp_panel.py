"""Fetch CRSP monthly 2002+ and cache the paper-grade panel as parquet.

Data plumbing only — no strategy return computed.

Usage:
    .venv\\Scripts\\python -m scripts.build_crsp_panel
Output:
    data/crsp_panel_2002/{monthly_ret,month_end_price,monthly_dollar_vol}.parquet
    data/crsp_panel_2002/stats.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.crsp_panel import build_crsp_panel, fetch_crsp_monthly
from aegis_brain.data.wrds_conn import get_connection

OUT = MODULE_ROOT / "data" / "crsp_panel_2002"
START = "2002-01-01"


def main() -> None:
    t0 = time.time()
    db = get_connection()
    df = fetch_crsp_monthly(db, start=START)
    db.close()
    print(f"rows fetched: {len(df):,}", flush=True)

    panel = build_crsp_panel(df)
    OUT.mkdir(parents=True, exist_ok=True)
    panel.monthly_ret.to_parquet(OUT / "monthly_ret.parquet")
    panel.month_end_price.to_parquet(OUT / "month_end_price.parquet")
    panel.monthly_dollar_vol.to_parquet(OUT / "monthly_dollar_vol.parquet")

    elig = panel.eligible()
    n_dead = sum(
        1 for last in panel.delist_month.values()
        if last is not None and last < panel.monthly_ret.index.max()
    )
    n_dlret = int(df["dlret"].notna().sum())
    stats = {
        "built_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "crsp.msf + msenames (shrcd 10/11, exchcd 1/2/3) + msedelist",
        "start": START,
        "months": len(panel.monthly_ret.index),
        "first_month": str(panel.monthly_ret.index.min().date()),
        "last_month": str(panel.monthly_ret.index.max().date()),
        "permnos": len(panel.symbols),
        "permnos_dying_inside_window": n_dead,
        "rows_with_real_delisting_return": n_dlret,
        "mean_eligible_names_per_month": round(float(elig.sum(axis=1).mean()), 1),
        "build_seconds": round(time.time() - t0, 1),
    }
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2), flush=True)


if __name__ == "__main__":
    main()
