"""TRIAL-ABIO-KIRK — ONE SHOT. Protocol: TRIALS/TRIAL-ABIO-KIRK.md (frozen 66add9e).

Three arms, each a counted candidate (164-166): io_level, io_chg, io_abn.
Explore 2004-01..2018-12 ONLY. The confirm window is NOT read here under any
outcome — a graduating arm stops and is flagged for an attended authorisation,
because the confirm read is one-use and spending it is Murat's call.

Deciding cost arms (registration): largemid @ flat 25 bps, small @ KO half
spread. The zero-cost bound and the flat-25 regression guard are reported
alongside every deciding number (post-CS-SPREAD convention, NEG_RESULTS 25: a
single-model cost number is never quoted without the interval).

Graduation (explore, per segment, on the deciding arm):
    t_ic >= 2.0 AND t_excess_gross >= 1.5 AND t_excess_net >= 1.5

PRE-DECLARED DECISIVE COMPARISON, reported regardless of graduation:
    if t_ic(io_abn) <= t_ic(io_level) + 0.5 pooled, the finding is
    "residualisation added nothing over the raw level".

Usage:  .venv\\Scripts\\python -m scripts.run_trial_abio_kirk
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.abio import ARMS, build_abio_frames
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.signals import FactorySignal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("abio_kirk")
OUT = MODULE_ROOT / "data" / "factory"

EXPLORE = ScanConfig()                       # 2004-01..2018-12, frozen
ZERO = ScanConfig(cost_bps_one_way=0.0)

T_IC_MIN, T_GROSS_MIN, T_NET_MIN = 2.0, 1.5, 1.5
DECISIVE_MARGIN = 0.5                        # frozen in the registration

DESCRIPTIONS = {
    "io_level": "Institutional ownership fraction, inst_shares/(shrout*1000).",
    "io_chg": "Quarter-over-quarter change in institutional ownership fraction.",
    "io_abn": "Abnormal institutional ownership: residual of a per-quarter "
              "cross-sectional OLS of io on five frozen characteristics "
              "(Kirk-STYLE, our characteristic set, frozen at registration).",
}


def bar(s: dict) -> bool:
    return bool(s["t_ic"] >= T_IC_MIN
                and s["t_excess_gross"] >= T_GROSS_MIN
                and s["t_excess_net"] >= T_NET_MIN)


def _t(x: pd.Series) -> float:
    x = x.dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else 0.0


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    spreads = build_spread_frame(panel)

    frames, diag = build_abio_frames(panel)
    log.info("construction diagnostics: %s", json.dumps(diag, default=str))

    signals = [FactorySignal(a, DESCRIPTIONS[a], (lambda p, f=frames[a]: f), +1)
               for a in ARMS]

    # (segment, arm label, cfg, cost_frame, deciding)
    plan = [
        ("largemid", "flat25", EXPLORE, None, True),
        ("largemid", "zero_cost_bound", ZERO, None, False),
        ("largemid", "ko_half_reported", EXPLORE, spreads, False),
        ("small", "ko_half", EXPLORE, spreads, True),
        ("small", "zero_cost_bound", ZERO, None, False),
        ("small", "flat25_regression_guard", EXPLORE, None, False),
    ]

    rows, monthly_ic = [], {}
    for sig in signals:
        for seg, arm, cfg, frame, deciding in plan:
            r = scan_signal(panel, sig, seg, cfg, cost_frame=frame)
            s = r["summary"]
            s.update({"window": "explore", "cost_arm": arm, "deciding": deciding})
            rows.append(s)
            if arm in ("flat25", "ko_half"):      # IC is cost-independent
                monthly_ic[(sig.name, seg)] = r["monthly"]["ic"]

    ex = pd.DataFrame(rows)
    show = ["signal", "segment", "cost_arm", "deciding", "months",
            "mean_excess_net_bps", "t_excess_net", "t_excess_gross", "t_ic",
            "turnover_1way", "max_dd", "cagr_net"]
    print("\n=== TRIAL-ABIO-KIRK — EXPLORE 2004-2018 (one shot) ===")
    print(ex[show].to_string(index=False))

    # ── pre-declared decisive comparison (pooled across segments) ────────────
    pooled = {}
    for name in ARMS:
        ics = pd.concat([monthly_ic[(name, s)] for s in ("largemid", "small")])
        pooled[name] = round(_t(ics), 2)
    gap = pooled["io_abn"] - pooled["io_level"]
    residualisation_added_nothing = bool(gap <= DECISIVE_MARGIN)
    print("\n=== PRE-DECLARED DECISIVE COMPARISON (pooled IC t) ===")
    print(f"  t_ic(io_level) = {pooled['io_level']:+.2f}")
    print(f"  t_ic(io_abn)   = {pooled['io_abn']:+.2f}   (io_chg {pooled['io_chg']:+.2f})")
    print(f"  gap = {gap:+.2f}  vs frozen margin +{DECISIVE_MARGIN}")
    print("  ->", "RESIDUALISATION ADDED NOTHING OVER THE RAW LEVEL"
          if residualisation_added_nothing else
          "residualisation cleared the declared margin")

    # ── graduation on the deciding arms only ─────────────────────────────────
    grads = []
    for name in ARMS:
        for seg, arm in (("largemid", "flat25"), ("small", "ko_half")):
            row = ex[(ex["signal"] == name) & (ex["segment"] == seg)
                     & (ex["cost_arm"] == arm)]
            if len(row) and bar(row.iloc[0].to_dict()):
                grads.append({"signal": name, "segment": seg, "cost_arm": arm})
    print("\nGRADUATES (deciding arms):",
          [(g["signal"], g["segment"]) for g in grads] or "NONE")

    if grads:
        verdict = ("EXPLORE GRADUATE(S) — STOPPED BEFORE CONFIRM. The confirm "
                   "read is one-use; authorising it is Murat's call.")
    else:
        verdict = ("NO EXPLORE GRADUATE — all three arms rejected; the 13F "
                   "ownership family stays closed at level, flow AND residual "
                   "resolution.")
    print("\nVERDICT:", verdict)

    results = {
        "trial": "TRIAL-ABIO-KIRK",
        "protocol_commit": "66add9e",
        "candidates": [164, 165, 166],
        "window": "explore 2004-01..2018-12 (confirm NOT read)",
        "construction_diagnostics": diag,
        "explore_runs": rows,
        "pooled_ic_t": pooled,
        "decisive_gap": round(gap, 2),
        "residualisation_added_nothing": residualisation_added_nothing,
        "graduates": grads,
        "confirm_runs": [],
        "verdict": verdict,
    }
    (OUT / "trial_abio_kirk.json").write_text(
        json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
