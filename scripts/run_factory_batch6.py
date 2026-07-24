"""Run Strategy Factory batch 6 — explore tier. Frozen in STRATEGY_FACTORY.md
BEFORE running. Usage: .venv\Scripts\python -m scripts.run_factory_batch6
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.batch6 import build_batch6
from aegis_brain.factory.explore import run_batch
from aegis_brain.factory.fundamentals import FundStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
OUT = MODULE_ROOT / "data" / "factory"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    store = FundStore(panel)
    table = run_batch(panel, build_batch6(panel, store))
    table.to_csv(OUT / "batch6_summary.csv", index=False)
    with open(OUT / "batch6_summary.txt", "w") as fh:
        fh.write(table.to_string(index=False))
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
