"""Honest exhibits from the committed replay records.

Chart 1: held-out confirm rank-IC of the 10 adoptions vs the measured null.
Chart 2: adopted-book confirm NAV vs the US market — WITH the caveats
printed ON the chart (t 1.07, placebo 1.32: not a beat-the-market claim).

Recomputes the frozen book construction for the NAV path only (same spent
window, same frozen inputs — no new information is read). Output PNGs to
aegis-finance/docs/exhibits/.

Run:  python scripts/build_exhibits.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.calibration.replay_stage_b import resolve_signal
from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.signals import FactorySignal
from aegis_brain.harness.benchmark import load_ff_factors
from scripts.run_replay_book_1 import ew_rank_composite

OUT = Path(r"C:\Users\mrthn\aegis-finance\docs\exhibits")
CONFIRM_CFG = ScanConfig(first_test_month="2019-01-31",
                         last_test_month="2024-12-31")


def chart1() -> None:
    d = json.loads((MODULE_ROOT / "runs" / "REPLAY-2" / "stageB_confirm.json")
                   .read_text("utf-8"))
    names = [r["signal"] for r in d["results"]]
    t_ic = [r["confirm"]["t_ic"] for r in d["results"]]
    meta = json.loads((MODULE_ROOT / "runs" / "REPLAY-2" /
                       "real_null_2_small_meta.json").read_text("utf-8"))
    p99 = meta["pooled_p99"]

    fig, ax = plt.subplots(figsize=(9, 5))
    order = np.argsort(t_ic)[::-1]
    ax.bar([names[i] for i in order], [t_ic[i] for i in order],
           color="#2b6cb0")
    ax.axhline(p99, color="#c53030", ls="--", lw=1.5,
               label=f"99th percentile of 20,000 information-free nulls "
                     f"(t = {p99})")
    ax.set_ylabel("held-out confirm rank-IC t-stat (2019–2024)")
    ax.set_title("The 10 replay adoptions: held-out information vs the "
                 "measured null")
    ax.legend(loc="upper right")
    ax.tick_params(axis="x", rotation=35)
    fig.text(0.01, 0.005,
             "Information evidence only — tradability after costs is "
             "separately tested and NOT established (see chart 2).",
             fontsize=8, color="#555")
    fig.tight_layout()
    fig.savefig(OUT / "01_adoptions_heldout_ic.png", dpi=150)
    print("chart 1 written")


def chart2() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    stage_a = json.loads((MODULE_ROOT / "runs" / "REPLAY-2" /
                          "stageA_selection.json").read_text("utf-8"))
    frames = []
    for g in stage_a["graduates"]:
        sig, _ = resolve_signal(g["signal"], panel)
        frames.append((sig.compute(panel), sig.direction))
    comp = ew_rank_composite(frames)
    sig = FactorySignal("book", "exhibit", lambda p, _f=comp: _f, +1)
    monthly = scan_signal(panel, sig, "small", CONFIRM_CFG)["monthly"]

    ff = load_ff_factors(MODULE_ROOT / "data")
    mkt = (ff["mktrf"] + ff["rf"]).reindex(monthly.index)
    nav_book = (1 + monthly["net"]).cumprod()
    nav_mkt = (1 + mkt).cumprod()

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(nav_book.index, nav_book, label="Adopted 10-signal small book "
            "(net of 25bps costs)", color="#2b6cb0", lw=2)
    ax.plot(nav_mkt.index, nav_mkt, label="US total market (Fama-French)",
            color="#718096", lw=2)
    ax.set_title("Held-out window 2019–2024: adopted book vs the market")
    ax.set_ylabel("growth of $1")
    ax.legend(loc="upper left")
    caveat = ("HONESTY BOX — this is NOT a beat-the-market claim:\n"
              "book net t = 1.07 over 72 months (an information-free placebo "
              "book printed 1.32);\n72 months cannot statistically "
              "distinguish edges of this size (the S&P itself prints "
              "t≈1.1);\nthe claim lives on the forward paper lanes, "
              "24-month clock.")
    fig.text(0.01, 0.005, caveat, fontsize=7.5, color="#742a2a")
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(OUT / "02_book_vs_market_heldout.png", dpi=150)
    print("chart 2 written; book CAGR "
          f"{float(nav_book.iloc[-1] ** (12 / len(monthly)) - 1):.3f} vs "
          f"mkt {float(nav_mkt.iloc[-1] ** (12 / len(monthly)) - 1):.3f}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    chart1()
    chart2()


if __name__ == "__main__":
    main()
