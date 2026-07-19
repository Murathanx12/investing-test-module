"""Build the full monthly panel from the EODHD archive and cache it as parquet.

Data plumbing ONLY: assembles the panel and reports coverage statistics.
No strategy return is computed here — running a strategy is a registered trial.

Usage:
    .venv\\Scripts\\python -m scripts.build_panel_cache
Output:
    data/panel_2017/{monthly_ret,month_end_price,monthly_dollar_vol}.parquet
    data/panel_2017/stats.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT, PANEL_START
from aegis_brain.data.eodhd_panel import build_panel, list_symbols

OUT = MODULE_ROOT / "data" / "panel_2017"


def main() -> None:
    t0 = time.time()
    syms = list_symbols("all")
    print(f"symbols discovered: {len(syms)}", flush=True)

    panel = build_panel(syms, start=PANEL_START, min_months=13, progress=True)

    OUT.mkdir(parents=True, exist_ok=True)
    panel.monthly_ret.to_parquet(OUT / "monthly_ret.parquet")
    panel.month_end_price.to_parquet(OUT / "month_end_price.parquet")
    panel.monthly_dollar_vol.to_parquet(OUT / "monthly_dollar_vol.parquet")

    elig = panel.eligible()
    n_dead_in_window = sum(
        1 for last in panel.delist_month.values() if last < panel.monthly_ret.index.max()
    )
    stats = {
        "built_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "panel_start": PANEL_START,
        "months": len(panel.monthly_ret.index),
        "first_month": str(panel.monthly_ret.index.min().date()),
        "last_month": str(panel.monthly_ret.index.max().date()),
        "symbols_discovered": len(syms),
        "symbols_in_panel": len(panel.symbols),
        "symbols_dying_inside_window": n_dead_in_window,
        "mean_eligible_names_per_month": round(float(elig.sum(axis=1).mean()), 1),
        "median_eligible_names_per_month": float(elig.sum(axis=1).median()),
        "build_seconds": round(time.time() - t0, 1),
    }
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2), flush=True)


if __name__ == "__main__":
    main()
