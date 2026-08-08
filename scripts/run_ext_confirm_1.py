"""TRIAL-EXT-CONFIRM-1 — the one-shot confirm for osap_GP + osap_OperProfRD.

Pre-registered: TRIALS/PREREG_EXT_CONFIRM_1.md (commit a6b85d9, BEFORE this
file existed). One confirm read per candidate, then spent forever.

Run:  python scripts/run_ext_confirm_1.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.calibration.replay2_eval import empirical_p
from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal, segment_mask
from aegis_brain.factory.osap import ScoreGridder, load_doc, meta_table
from aegis_brain.factory.signals import FactorySignal

CANDS = ["GP", "OperProfRD"]
SEG = "small"
PLACEBO_SEEDS = (11, 12, 13, 14, 15)
PHI = 0.99
EXPLORE_CFG = ScanConfig()
CONFIRM_CFG = ScanConfig(first_test_month="2019-01-31",
                         last_test_month="2024-12-31")
OUT = MODULE_ROOT / "runs" / "EXT-BANK-1" / "trial_ext_confirm_1.json"


def leg_decomposition(score, direction, panel, cfg):
    sc = score * float(direction)
    elig = panel.eligible() & segment_mask(panel, SEG)
    months = panel.monthly_ret.index
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    spread, long_leg = [], []
    for m in months:
        if not (lo <= m <= hi) or months.get_loc(m) == 0:
            continue
        f = months[months.get_loc(m) - 1]
        e = elig.loc[f]
        s = sc.loc[f].reindex(e[e].index).dropna()
        if len(s) < 100:
            continue
        r = panel.monthly_ret.loc[m].reindex(s.index)
        ok = r.notna()
        s, r = s[ok], r[ok]
        if len(s) < 100:
            continue
        dec = pd.qcut(s.rank(method="first"), 10, labels=False)
        spread.append(float(r[dec == 9].mean()) - float(r[dec == 0].mean()))
        long_leg.append(float(r[dec == 9].mean()) - float(r.mean()))
    sp, ll = float(np.mean(spread)), float(np.mean(long_leg))
    return {"months": len(spread), "mean_spread_bps": round(sp * 1e4, 1),
            "mean_long_leg_bps": round(ll * 1e4, 1),
            "long_leg_share": round(ll / sp, 3) if sp != 0 else None}


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} exists — one shot; rerun is a new trial ID.")
    banked = json.loads((MODULE_ROOT / "runs" / "EXT-BANK-1" /
                         "trial_ext_prof_small_1.json").read_text("utf-8"))
    banked_rows = {r["signal"]: r for r in banked["rows"]}

    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    doc = {m.acronym: m for m in meta_table(load_doc())}
    long_df = pd.read_parquet(MODULE_ROOT / "data" / "osap" /
                              "firm_char.parquet",
                              columns=["permno", "yyyymm"] + CANDS)
    gridder = ScoreGridder(long_df, panel)
    frames = {a: gridder.grid(long_df[a]) for a in CANDS}
    ko = build_spread_frame(panel)

    with np.load(MODULE_ROOT / "runs" / "REPLAY-2" /
                 "real_null_2_small.npz") as z:
        cf_null = np.sort(z["pooled_t_confirm"])

    # ---------------- GUARD: reproduce banked explore lines -----------------
    sigs = {}
    for a in CANDS:
        sig = FactorySignal(f"osap_{a}", "confirm-1",
                            lambda p, _f=frames[a]: _f, doc[a].sign)
        rep = scan_signal(panel, sig, SEG, EXPLORE_CFG)["summary"]
        want = banked_rows[a]
        ok = (round(rep["t_ic"], 2) == round(want["t_ic"], 2)
              and round(rep["t_excess_net"], 2)
              == round(want["t_net_flat25"], 2))
        print(f"GUARD {a}: t_ic {rep['t_ic']} vs {want['t_ic']}, "
              f"t_net {rep['t_excess_net']} vs {want['t_net_flat25']} "
              f"{'PASS' if ok else 'FAIL'}")
        if not ok:
            raise SystemExit("GUARD FAILED — VOID, no confirm read.")
        sigs[a] = sig

    # ---------------- placebo confirm books (before real reads, cheap) ------
    T, N = panel.monthly_ret.shape
    sd_eps = np.sqrt(1 - PHI ** 2)
    placebos = []
    for seed in PLACEBO_SEEDS:
        rng = np.random.default_rng(seed)
        eps = rng.standard_normal((T, N))
        x = np.empty((T, N))
        x[0] = eps[0]
        for t in range(1, T):
            x[t] = PHI * x[t - 1] + sd_eps * eps[t]
        psig = FactorySignal(f"pl{seed}", "placebo",
                             lambda p, _f=pd.DataFrame(
                                 x, index=panel.monthly_ret.index,
                                 columns=panel.monthly_ret.columns): _f, +1)
        s = scan_signal(panel, psig, SEG, CONFIRM_CFG)["summary"]
        placebos.append({"seed": seed, "t_net": s["t_excess_net"],
                         "t_ic": s["t_ic"]})
        print("placebo", seed, json.dumps(placebos[-1]))
    max_placebo_net = max(p["t_net"] for p in placebos)

    # ---------------- THE confirm reads -------------------------------------
    results = {"trial": "TRIAL-EXT-CONFIRM-1", "prereg_commit": "a6b85d9",
               "placebos": placebos, "candidates": {}}
    for a in CANDS:
        t0 = time.time()
        flat = scan_signal(panel, sigs[a], SEG, CONFIRM_CFG)["summary"]
        koh = scan_signal(panel, sigs[a], SEG, CONFIRM_CFG,
                          cost_frame=ko)["summary"]
        legs = leg_decomposition(frames[a], doc[a].sign, panel, CONFIRM_CFG)
        info_pass = flat["ic_mean"] > 0 and flat["t_ic"] >= 0.5
        money = "FAIL"
        if (flat["t_excess_net"] >= 1.5 and koh["t_excess_net"] >= 0.8
                and flat["t_excess_net"] > max_placebo_net):
            money = "TRADABLE-PASS"
        elif (0.8 <= flat["t_excess_net"] < 1.5
              and flat["t_excess_net"] > max_placebo_net):
            money = "WEAK (attended)"
        results["candidates"][a] = {
            "confirm_t_ic": flat["t_ic"],
            "p_t_ic_vs_null": round(empirical_p(flat["t_ic"], cf_null), 5),
            "confirm_ic_mean": flat["ic_mean"],
            "confirm_t_net_flat25": flat["t_excess_net"],
            "confirm_t_net_ko_half": koh["t_excess_net"],
            "confirm_t_gross": flat["t_excess_gross"],
            "mean_excess_net_bps": flat["mean_excess_net_bps"],
            "turnover_1way": flat["turnover_1way"],
            "months": flat["months"], "legs": legs,
            "information": "PASS" if info_pass else "FAIL",
            "money": money, "secs": round(time.time() - t0, 1)}
        print(a, json.dumps(results["candidates"][a]))

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
