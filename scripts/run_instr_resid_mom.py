"""INSTR-RESID-MOM — one shot. Protocol: TRIALS/INSTR-RESID-MOM.md (frozen c95a97b).

Explore 2004-2018, both segments, bars declared at registration:
  largemid @ flat 25 bps   -> t_net >= 1.5 AND t_ic >= 2.0
  small    @ KO half-spread -> t_net >= 1.5 AND t_ic >= 2.0
Graduates get ONE confirm run (2019-2024, same segment, same cost arm).

mom_12_1 is re-run on identical windows and cost arms as the paired control —
reported, never deciding.

Usage:  python -m scripts.run_instr_resid_mom
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.batch1_price import BATCH1
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.resid_mom import compute_resid_mom
from aegis_brain.factory.signals import FactorySignal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("resid_mom")
OUT = MODULE_ROOT / "data" / "factory"

EXPLORE = ScanConfig()
CONFIRM = ScanConfig(first_test_month="2019-01-31", last_test_month="2024-12-31")


def bar(s: dict) -> bool:
    return bool(s["t_excess_net"] >= 1.5 and s["t_ic"] >= 2.0)


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    spreads = build_spread_frame(panel)

    scores = compute_resid_mom(panel)
    resid = FactorySignal(
        "resid_mom",
        "Residual momentum (Blitz-Huij-Martens 2011): FF3 residual 12-1, "
        "standardised by residual sd over the same window.",
        lambda p, f=scores: f, +1)
    mom = next(s for s in BATCH1 if s.name == "mom_12_1")   # paired control

    # (segment, cost arm label, cost_frame) — the deciding arms are declared
    # in the registration: largemid flat25, small KO-half.
    arms = [
        ("largemid", "flat25", None, True),
        ("small", "ko_half", spreads, True),
        ("small", "flat25_bridge", None, False),
        ("largemid", "ko_half_reported", spreads, False),
    ]

    rows = []
    for sig in (resid, mom):
        for seg, arm, frame, deciding in arms:
            r = scan_signal(panel, sig, seg, EXPLORE, cost_frame=frame)
            s = r["summary"]
            s.update({"window": "explore", "cost_arm": arm, "deciding": deciding})
            rows.append(s)

    ex = pd.DataFrame(rows)
    show = ["signal", "segment", "cost_arm", "deciding", "months",
            "mean_excess_net_bps", "t_excess_net", "t_excess_gross", "t_ic",
            "turnover_1way", "max_dd", "cagr_net"]
    print("\n=== EXPLORE 2004-2018 ===")
    print(ex[show].to_string(index=False))

    grads = []
    for seg, arm, frame, deciding in arms:
        if not deciding:
            continue
        row = ex[(ex["signal"] == "resid_mom") & (ex["segment"] == seg)
                 & (ex["cost_arm"] == arm)]
        if len(row) and bar(row.iloc[0].to_dict()):
            grads.append((seg, arm, frame))
    print("\nGRADUATES:", [(s, a) for s, a, _ in grads] or "NONE")

    confirms = []
    for seg, arm, frame in grads:
        s = scan_signal(panel, resid, seg, CONFIRM, cost_frame=frame)["summary"]
        s.update({"window": "confirm", "cost_arm": arm})
        s["confirm_pass"] = bool(s["mean_excess_net_bps"] > 0
                                 and s["t_excess_net"] >= 0.8
                                 and s["t_ic"] >= 1.5)
        confirms.append(s)
        print(f"CONFIRM {seg}/{arm}: net {s['mean_excess_net_bps']:+.1f} "
              f"t {s['t_excess_net']:+.2f} ic_t {s['t_ic']:+.2f} -> "
              f"{'PASS' if s['confirm_pass'] else 'REJECT'}")

    verdict = ("NO EXPLORE GRADUATE — residual-momentum family CLOSED"
               if not grads else
               ("CONFIRM PASS" if any(c["confirm_pass"] for c in confirms)
                else "GRADUATED THEN REJECTED AT CONFIRM"))
    print("\nVERDICT:", verdict)

    (OUT / "instr_resid_mom.json").write_text(json.dumps(
        {"explore": rows, "graduates": [(s, a) for s, a, _ in grads],
         "confirm": confirms, "verdict": verdict}, indent=2, default=str))


if __name__ == "__main__":
    main()
