"""TRIAL-TGT-REBUILD — one shot. Protocol: TRIALS/TRIAL-TGT-REBUILD.md.

Usage:  .venv\\Scripts\\python -m scripts.run_trial_tgt
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.tgt_rebuild import build_signals

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("trial_tgt")
OUT = MODULE_ROOT / "data" / "factory"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    sigs = build_signals(panel)

    results: dict = {"explore": [], "confirm": []}
    for sig in sigs:
        for seg in ("largemid", "small"):
            results["explore"].append(scan_signal(panel, sig, seg)["summary"])

    # frozen graduation rule — confirm opens per-arm, largemid only
    confirm_cfg = ScanConfig(first_test_month="2019-01-31",
                             last_test_month="2024-12-31")
    for sig in sigs:
        e = next(r for r in results["explore"]
                 if r["signal"] == sig.name and r["segment"] == "largemid")
        graduates = e["t_excess_net"] >= 1.5 and e["t_ic"] >= 2.0
        log.info("GATE %s: t_net %.2f t_ic %.2f -> graduates=%s",
                 sig.name, e["t_excess_net"], e["t_ic"], graduates)
        if graduates:
            c = scan_signal(panel, sig, "largemid", confirm_cfg)["summary"]
            c["window"] = "confirm"
            results["confirm"].append(c)

    with open(OUT / "trial_tgt_rebuild.json", "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
