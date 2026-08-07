"""TRIAL-REPLAY-BOOK-1 — money-leg adjudication of the replay's 10 adoptions.

Pre-registered: TRIALS/PREREG_REPLAY_BOOK_1.md (committed 8340298 BEFORE
this file existed). One shot; output write-once.

Run:  python scripts/run_replay_book_1.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.calibration.replay_stage_b import resolve_signal
from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal, segment_mask
from aegis_brain.factory.signals import FactorySignal

SEG = "small"
PHI = 0.99
PLACEBO_SEEDS = (1, 2, 3, 4, 5)
EXPLORE_CFG = ScanConfig()
CONFIRM_CFG = ScanConfig(first_test_month="2019-01-31",
                         last_test_month="2024-12-31")
STRESS_CFG = {"explore": ScanConfig(cost_bps_one_way=50.0),
              "confirm": ScanConfig(cost_bps_one_way=50.0,
                                    first_test_month="2019-01-31",
                                    last_test_month="2024-12-31")}
OUT = MODULE_ROOT / "runs" / "REPLAY-2" / "trial_replay_book_1.json"


def ew_rank_composite(frames: list[tuple[pd.DataFrame, int]]) -> pd.DataFrame:
    """EW of per-month cross-sectional pct-ranks, direction applied."""
    acc, cnt = None, None
    for score, direction in frames:
        r = score.rank(axis=1, pct=True)
        if direction < 0:
            r = 1.0 - r
        good = r.notna()
        r0 = r.fillna(0.0)
        if acc is None:
            acc, cnt = r0, good.astype("int16")
        else:
            acc = acc + r0
            cnt = cnt + good.astype("int16")
    out = acc / cnt.replace(0, np.nan)
    return out


def leg_decomposition(comp: pd.DataFrame, panel, cfg: ScanConfig) -> dict:
    elig = panel.eligible() & segment_mask(panel, SEG)
    months = panel.monthly_ret.index
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    spread, long_leg = [], []
    for m in months:
        if not (lo <= m <= hi) or months.get_loc(m) == 0:
            continue
        f = months[months.get_loc(m) - 1]
        e = elig.loc[f]
        s = comp.loc[f].reindex(e[e].index).dropna()
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


def scan_book(name: str, comp: pd.DataFrame, panel, cfg: ScanConfig,
              cost_frame=None) -> dict:
    sig = FactorySignal(name, "book", lambda p, _f=comp: _f, +1)
    return scan_signal(panel, sig, SEG, cfg, cost_frame=cost_frame)["summary"]


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} exists — one shot; rerun is a new trial ID.")
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    stage_a = json.loads((MODULE_ROOT / "runs" / "REPLAY-2" /
                          "stageA_selection.json").read_text("utf-8"))
    adopted = [(g["signal"], g["segment"]) for g in stage_a["graduates"]]
    assert len(adopted) == 10 and all(s == SEG for _, s in adopted)

    frames = []
    for name, _seg in adopted:
        sig, prov = resolve_signal(name, panel)
        if sig is None:
            raise SystemExit(f"unresolvable graduate {name}: {prov}")
        frames.append((sig.compute(panel), sig.direction))
        print(f"resolved {name} ({prov})")
    comp = ew_rank_composite(frames)

    ko = build_spread_frame(panel)
    results: dict = {"trial": "TRIAL-REPLAY-BOOK-1",
                     "prereg_commit": "8340298", "book": {}}
    for window, cfg in (("explore", EXPLORE_CFG), ("confirm", CONFIRM_CFG)):
        flat = scan_book(f"book_{window}", comp, panel, cfg)
        koh = scan_book(f"book_{window}_ko", comp, panel, cfg, cost_frame=ko)
        stress = scan_book(f"book_{window}_s50", comp, panel,
                           STRESS_CFG[window])
        results["book"][window] = {
            "t_ic": flat["t_ic"], "ic_mean": flat["ic_mean"],
            "t_net_flat25": flat["t_excess_net"],
            "t_net_ko_half": koh["t_excess_net"],
            "t_net_stress50": stress["t_excess_net"],
            "t_gross": flat["t_excess_gross"],
            "mean_excess_net_bps": flat["mean_excess_net_bps"],
            "turnover_1way": flat["turnover_1way"],
            "months": flat["months"], "cagr_net": flat["cagr_net"],
            "max_dd": flat["max_dd"],
            "legs": leg_decomposition(comp, panel, cfg)}
        print(window, json.dumps(results["book"][window]))

    # ---- placebo books ----------------------------------------------------
    T, N = panel.monthly_ret.shape
    placebos = []
    sd_eps = np.sqrt(1 - PHI ** 2)
    for seed in PLACEBO_SEEDS:
        rng = np.random.default_rng(seed)
        pframes = []
        for _ in range(10):
            eps = rng.standard_normal((T, N))
            x = np.empty((T, N))
            x[0] = eps[0]
            for t in range(1, T):
                x[t] = PHI * x[t - 1] + sd_eps * eps[t]
            pframes.append((pd.DataFrame(x, index=panel.monthly_ret.index,
                                         columns=panel.monthly_ret.columns), 1))
        pcomp = ew_rank_composite(pframes)
        pc = scan_book(f"placebo{seed}", pcomp, panel, CONFIRM_CFG)
        placebos.append({"seed": seed, "confirm_t_net": pc["t_excess_net"],
                         "confirm_t_ic": pc["t_ic"]})
        print("placebo", seed, json.dumps(placebos[-1]))
    results["placebos"] = placebos

    # ---- frozen decision rule ---------------------------------------------
    c = results["book"]["confirm"]
    beats_all = all(c["t_net_flat25"] > p["confirm_t_net"] for p in placebos)
    legs_ok = (c["legs"]["long_leg_share"] or 0) >= 0.50
    if (c["t_net_flat25"] >= 1.5 and c["t_net_ko_half"] >= 1.5
            and beats_all and legs_ok):
        verdict = "PASS"
    elif (c["t_net_flat25"] >= 1.5 and 0.8 <= c["t_net_ko_half"] < 1.5
          and beats_all and legs_ok):
        verdict = "WEAK-PASS (cost-fragile; seeding decision attended)"
    else:
        verdict = "FAIL"
    results["verdict"] = {"verdict": verdict, "beats_all_placebos": beats_all,
                          "long_leg_ok": legs_ok}
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("VERDICT:", verdict)
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
