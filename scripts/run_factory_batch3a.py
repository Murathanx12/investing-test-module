"""Run Strategy Factory batch 3a (alt-data) — explore tier.

Protocol: docs/STRATEGY_FACTORY.md batch-3a section (committed BEFORE this
runs). Six signals x 2 segments on the explore window; congress-dependent
signals run 2014-01..2018-12 (post-STOCK-Act coverage), stated a priori.

Usage:  .venv\\Scripts\\python -m scripts.run_factory_batch3a
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.altstores import (
    gemini_score,
    insider_flag_12m,
    load_breadth_chg,
    load_congress_buys,
    load_daily_agg,
    load_rec_momentum,
    load_short_interest_chg,
)
from aegis_brain.factory.explore import ScanConfig, run_batch
from aegis_brain.factory.signals import FactorySignal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

OUT = MODULE_ROOT / "data" / "factory"
CONGRESS_CFG = ScanConfig(first_test_month="2014-01-31", last_test_month="2018-12-31")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")

    daily = load_daily_agg(panel)
    si = load_short_interest_chg(panel)
    breadth = load_breadth_chg(panel)
    rec = load_rec_momentum(panel)
    congress = load_congress_buys(panel)
    insider = insider_flag_12m(panel)
    gem = gemini_score(panel, congress, insider)

    full = [
        FactorySignal("max_dret_low_D", "Real daily MAX: lottery demand overprices "
                      "spike names (Bali-Cakici-Whitelaw 2011) — daily-data upgrade "
                      "of batch-1's monthly proxy.", lambda p: daily["max_dret"], -1),
        FactorySignal("ivol_low_D", "Idiosyncratic/total daily vol: low-vol anomaly "
                      "at proper daily resolution (Ang et al. 2006).",
                      lambda p: daily["vol_d"], -1),
        FactorySignal("amihud_D", "Real daily Amihud illiquidity premium (2002) — "
                      "upgrade of the monthly proxy.", lambda p: daily["amihud_d"], +1),
        FactorySignal("si_chg_low", "Rising short interest predicts underperformance "
                      "(Boehmer et al.; Rapach et al. 2016) — long falling SI.",
                      lambda p: si, -1),
        FactorySignal("breadth_chg", "Rising breadth of institutional ownership is "
                      "bullish (Chen-Hong-Stein 2002), 45d filing lag.",
                      lambda p: breadth, +1),
        FactorySignal("rec_mom", "Recommendation upgrades minus downgrades (Jegadeesh "
                      "et al. 2004). NOTE: BRAIN-005 (EPS estimate revisions) "
                      "REJECTED — this is the distinct recommendations measure.",
                      lambda p: rec, +1),
    ]
    short_window = [
        FactorySignal("congress_buys", "INSTR-CONGRESS-HIST: senators' disclosed "
                      "purchases (45d PIT lag) predict returns — adjudicating the "
                      "'5-10%/yr' claim on data.", lambda p: congress, +1),
        FactorySignal("gemini_score", "INSTR-GEMINI-SCORE: Gemini's literal point "
                      "composite (dip>=40% +5, insider +10, congress +10; narrative "
                      "omitted - no PIT source).", lambda p: gem, +1),
    ]

    t_full = run_batch(panel, full)
    t_short = run_batch(panel, short_window, cfg=CONGRESS_CFG)
    table = pd.concat([t_full, t_short], ignore_index=True)
    table = table.sort_values("t_excess_net", ascending=False, na_position="last")
    table.to_csv(OUT / "batch3a_summary.csv", index=False)
    with open(OUT / "batch3a_summary.txt", "w") as fh:
        fh.write(table.to_string(index=False))
    print(table.to_string(index=False))
    print(f"\n{len(table)} scans -> {OUT / 'batch3a_summary.csv'}")


if __name__ == "__main__":
    main()
