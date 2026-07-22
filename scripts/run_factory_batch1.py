"""Run Strategy Factory batch 1 (explore tier) on the CRSP panel.

Protocol: docs/STRATEGY_FACTORY.md (committed BEFORE this runs). Explore
window only (2004-01..2018-12); results are hypothesis ranking, never
evidence. Output: data/factory/batch1_summary.csv + per-scan monthlies.

Usage:  .venv\\Scripts\\python -m scripts.run_factory_batch1
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.batch1_price import BATCH1
from aegis_brain.factory.explore import run_batch

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

OUT = MODULE_ROOT / "data" / "factory"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    table = run_batch(panel, BATCH1)
    table.to_csv(OUT / "batch1_summary.csv", index=False)
    with open(OUT / "batch1_summary.txt", "w") as fh:
        fh.write(table.to_string(index=False))
    print(table.to_string(index=False))
    print(f"\n{len(table)} scans -> {OUT / 'batch1_summary.csv'}")


if __name__ == "__main__":
    main()
