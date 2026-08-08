"""INSTR-ERA-BACKTEST-1 — the long-window era instrument.

Pre-registered: TRIALS/PREREG_ERA_BACKTEST_1.md (commit 92950d9, before
this file existed). INSTRUMENT: no adoption/kill power. One shot.

Guard: reproduce osap_GP small t_ic 7.24 on the MODERN panel (identical
code path) before touching the era panel.

Run:  python scripts/run_era_backtest_1.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import Panel, load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal
from aegis_brain.factory.osap import ScoreGridder, load_doc, meta_table
from aegis_brain.factory.signals import FactorySignal

OSAP_SIGNALS = {"GP": +1, "OperProfRD": +1, "CBOperProf": +1, "OperProf": +1,
                "cfp": +1, "roaq": +1, "RoE": +1, "MaxRet": -1,
                "IdioVol3F": -1}
WINDOWS = {
    "W-A": {"first": "1985-01-31", "last": "2001-12-31",
            "segments": ("largemid", "small")},
    "W-B": {"first": "1972-01-31", "last": "1984-12-31",
            "segments": ("largemid",)},
    "W-A1": {"first": "1985-01-31", "last": "1993-12-31",
             "segments": ("largemid", "small")},
    "W-A2": {"first": "1994-01-31", "last": "2001-12-31",
             "segments": ("largemid", "small")},
}
GUARD = {"t_ic": 7.24}
OUT = MODULE_ROOT / "runs" / "ERA" / "instr_era_backtest_1.json"


def native_signals(panel: Panel) -> list[FactorySignal]:
    ret, prc = panel.monthly_ret, panel.month_end_price
    return [
        FactorySignal("price_level", "era", lambda p, _f=np.log(
            prc.where(prc > 0)): _f, +1),
        FactorySignal("vol_12m_low", "era", lambda p, _f=ret.rolling(
            12, min_periods=9).std(): _f, -1),
        FactorySignal("max_ret_low", "era", lambda p, _f=ret.rolling(
            12, min_periods=9).max(): _f, -1),
    ]


def osap_frames(panel: Panel) -> dict[str, pd.DataFrame]:
    d = pd.read_parquet(MODULE_ROOT / "data" / "osap" / "firm_char.parquet",
                        columns=["permno", "yyyymm"] + list(OSAP_SIGNALS))
    g = ScoreGridder(d, panel)
    return {a: g.grid(d[a]) for a in OSAP_SIGNALS}


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} exists — one shot; rerun is a new trial ID.")
    docsigns = {m.acronym: m.sign for m in meta_table(load_doc())}
    for a, s in OSAP_SIGNALS.items():
        if docsigns.get(a) != s:
            raise SystemExit(f"sign mismatch {a}: frozen {s} vs doc "
                             f"{docsigns.get(a)} — refusing")

    # ---------------- GUARD on the modern panel -----------------------------
    modern = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    mf = osap_frames(modern)
    gp = FactorySignal("osap_GP", "guard", lambda p, _f=mf["GP"]: _f, +1)
    g = scan_signal(modern, gp, "small", ScanConfig())["summary"]
    print(f"GUARD osap_GP/small modern t_ic {g['t_ic']} vs {GUARD['t_ic']} "
          f"{'PASS' if round(g['t_ic'], 2) == GUARD['t_ic'] else 'FAIL'}")
    if round(g["t_ic"], 2) != GUARD["t_ic"]:
        raise SystemExit("GUARD FAILED — VOID, no era statistic reported.")
    del modern, mf

    # ---------------- era panel ---------------------------------------------
    era = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_1962_2001")
    ef = osap_frames(era)
    sigs = [FactorySignal(f"osap_{a}", "era", lambda p, _f=ef[a]: _f, s)
            for a, s in OSAP_SIGNALS.items()] + native_signals(era)

    rows = []
    for wname, w in WINDOWS.items():
        cfg = ScanConfig(first_test_month=w["first"], last_test_month=w["last"])
        for sig in sigs:
            for seg in w["segments"]:
                t0 = time.time()
                try:
                    s = scan_signal(era, sig, seg, cfg)["summary"]
                except ValueError as e:
                    rows.append({"window": wname, "signal": sig.name,
                                 "segment": seg, "months": 0,
                                 "error": str(e)[:80]})
                    continue
                rows.append({"window": wname, "signal": sig.name,
                             "segment": seg, "months": s["months"],
                             "t_ic": s["t_ic"], "ic_mean": s["ic_mean"],
                             "t_gross": s["t_excess_gross"],
                             "t_net_flat25_REF_ONLY": s["t_excess_net"],
                             "mean_excess_gross_bps": round(
                                 s["mean_excess_net_bps"]
                                 + (s["t_excess_gross"] - s["t_excess_net"])
                                 * 0, 1),
                             "turnover": s["turnover_1way"],
                             "secs": round(time.time() - t0, 1)})
                print(json.dumps(rows[-1]))

    df = pd.DataFrame(rows)
    ok = df[df.months > 0]

    def val(sig, seg, win, col):
        r = ok[(ok.signal == sig) & (ok.segment == seg) & (ok.window == win)]
        return float(r[col].iloc[0]) if len(r) else float("nan")

    preds = {
        "P1_gp_class_gross_ge2_small_WA": {
            s: val(f"osap_{s}", "small", "W-A", "t_gross")
            for s in ("GP", "CBOperProf", "OperProfRD")},
        "P2_family_ic_ge3_both_splits_small": {
            s: [val(f"osap_{s}", "small", "W-A1", "t_ic"),
                val(f"osap_{s}", "small", "W-A2", "t_ic")]
            for s in ("GP", "CBOperProf", "OperProfRD", "OperProf", "cfp",
                      "roaq", "RoE")},
        "P4_sigma_ic_ge3_small_WA": {
            s: val(s if not s.startswith(("Max", "Idio")) else f"osap_{s}",
                   "small", "W-A", "t_ic")
            for s in ("MaxRet", "IdioVol3F", "vol_12m_low", "price_level")},
    }
    preds["P1_hit"] = all(v >= 2.0 for v in
                          preds["P1_gp_class_gross_ge2_small_WA"].values())
    preds["P2_hit"] = all(min(v) >= 3.0 for v in
                          preds["P2_family_ic_ge3_both_splits_small"].values())
    preds["P4_hit"] = all(v >= 3.0 for v in
                          preds["P4_sigma_ic_ge3_small_WA"].values())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "instrument": "INSTR-ERA-BACKTEST-1", "prereg_commit": "92950d9",
        "guard": g["t_ic"], "rows": rows, "prediction_scoring": preds},
        indent=2), encoding="utf-8")
    print(json.dumps(preds, indent=2, default=str))
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
