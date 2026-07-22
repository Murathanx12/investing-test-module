"""Run Strategy Factory batch 3b — customer momentum (TRIAL-THEME-SUPPLY's
cross-sectional arm), 13F best ideas, price-target upside.

Protocol: docs/STRATEGY_FACTORY.md batch-3b section, committed BEFORE running.

Usage:  .venv\\Scripts\\python -m scripts.run_factory_batch3b
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.altstores2 import (
    load_best_ideas,
    load_customer_momentum,
    load_target_upside,
)
from aegis_brain.factory.explore import run_batch
from aegis_brain.factory.signals import FactorySignal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

OUT = MODULE_ROOT / "data" / "factory"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")

    cm = load_customer_momentum(panel)
    bi = load_best_ideas(panel)
    tu = load_target_upside(panel)

    sigs = [
        FactorySignal("cust_mom", "Cohen-Frazzini 2008 customer momentum: investors "
                      "underreact to economically-linked customer news; suppliers "
                      "drift. Murat's suppliers-thesis, cross-sectional arm.",
                      lambda p: cm, +1),
        FactorySignal("best_ideas", "Cohen-Polk-Silli 2010: managers' top-3 "
                      "positions (their best ideas) outperform; count of managers "
                      "backing the name.", lambda p: bi, +1),
        FactorySignal("tgt_upside", "Brav-Lehavy 2003: high implied upside to "
                      "consensus 12m target predicts returns (optimism-bias "
                      "caveat in small caps).", lambda p: tu, +1),
    ]
    table = run_batch(panel, sigs)
    table.to_csv(OUT / "batch3b_summary.csv", index=False)
    print(table.to_string(index=False))
    print(f"\n{len(table)} scans -> {OUT / 'batch3b_summary.csv'}")


if __name__ == "__main__":
    main()
