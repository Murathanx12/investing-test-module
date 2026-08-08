"""TRIAL-EXT-EXCLUDE-1 — lottery/distress exclusion overlay, small segment.

Pre-registered: TRIALS/PREREG_EXT_BANK_1.md (frozen pre-M4). Base book =
EW universe fallback (the PROF-SMALL-1 book was killed by its own clause).
Explore window ONLY. One shot.

Avoid-composite (construction-declared, avoid-space signs):
  MaxRet(+), IdioVol3F(+), OScore(+), zerotrade12M(+), ShareIss1Y(+),
  FirmAge(−, young = avoid). Worst quintile of the composite is excluded
  at formation each month; no mid-month ejections.

KILL: paired dt_net <= 0, or indistinguishable from 5-seed random
exclusion (pooled |t| < 1.5), or incremental turnover > 0.05/mo.

Run:  python scripts/run_ext_exclude_1.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, segment_mask
from aegis_brain.factory.osap import ScoreGridder

AVOID = {"MaxRet": +1, "IdioVol3F": +1, "OScore": +1, "zerotrade12M": +1,
         "ShareIss1Y": +1, "FirmAge": -1}
SEG = "small"
COST_BPS = 25.0
SEEDS = (1, 2, 3, 4, 5)
OUT = MODULE_ROOT / "runs" / "EXT-BANK-1" / "trial_ext_exclude_1.json"


def t_stat(x: pd.Series) -> float:
    x = x.dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else 0.0


def book_path(panel, months, elig, keep_fn) -> pd.DataFrame:
    """Monthly EW book of keep_fn(formation_month) names; costs on traded
    weight at COST_BPS one-way. Returns monthly frame [net, gross, n]."""
    prev_w = pd.Series(dtype=float)
    rows = []
    for m in months:
        pos = panel.monthly_ret.index.get_loc(m)
        if pos == 0:
            continue
        f = panel.monthly_ret.index[pos - 1]
        e = elig.loc[f]
        names = keep_fn(f, e[e].index)
        if names is None or len(names) < 100:
            continue
        w = pd.Series(1.0 / len(names), index=names)
        r = panel.monthly_ret.loc[m].reindex(names)
        gross = float((w * r).sum()) if r.notna().any() else np.nan
        aligned_prev = prev_w.reindex(w.index.union(prev_w.index), fill_value=0.0)
        aligned_new = w.reindex(aligned_prev.index, fill_value=0.0)
        traded = float((aligned_new - aligned_prev).abs().sum())
        net = gross - traded * COST_BPS / 1e4
        rows.append({"month": m, "gross": gross, "net": net,
                     "traded": traded, "n": len(names)})
        prev_w = w
    return pd.DataFrame(rows).set_index("month")


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT} exists — one shot; rerun is a new trial ID.")
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    cols = list(AVOID)
    long_df = pd.read_parquet(MODULE_ROOT / "data" / "osap" /
                              "firm_char.parquet",
                              columns=["permno", "yyyymm"] + cols)
    g = ScoreGridder(long_df, panel)
    ranks = {}
    for c in cols:
        r = g.grid(long_df[c]).rank(axis=1, pct=True)
        ranks[c] = r if AVOID[c] > 0 else (1.0 - r)
    acc = sum(rk.fillna(0.0) for rk in ranks.values())
    cnt = sum(rk.notna().astype("int16") for rk in ranks.values())
    avoid = acc / cnt.replace(0, np.nan)   # high = avoid

    cfg = ScanConfig()
    months_all = panel.monthly_ret.index
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    months = [m for m in months_all if lo <= m <= hi]
    elig = panel.eligible() & segment_mask(panel, SEG)

    def unscreened(f, names):
        return names

    def screened(f, names):
        s = avoid.loc[f].reindex(names).dropna()
        if len(s) < 100:
            return names          # no coverage -> no screen that month
        cut = s.quantile(0.80)
        drop = set(s[s >= cut].index)
        return pd.Index([x for x in names if x not in drop])

    base = book_path(panel, months, elig, unscreened)
    scr = book_path(panel, months, elig, screened)
    common = base.index.intersection(scr.index)
    diff = scr.loc[common, "net"] - base.loc[common, "net"]
    inc_turn = float((scr.loc[common, "traded"]
                      - base.loc[common, "traded"]).mean()) / 2

    rng_placebo = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)

        def rand_screen(f, names, _rng=rng):
            k = int(len(names) * 0.20)
            drop = set(_rng.choice(names, size=k, replace=False))
            return pd.Index([x for x in names if x not in drop])

        pb = book_path(panel, months, elig, rand_screen)
        pdiff = pb.loc[pb.index.intersection(common), "net"] \
            - base.loc[pb.index.intersection(common), "net"]
        rng_placebo.append({"seed": seed,
                            "dt_net": round(t_stat(pdiff), 3),
                            "mean_bps": round(float(pdiff.mean()) * 1e4, 2)})

    screen_vs_rand = []
    # pooled screen-minus-random comparison, per placebo, on common months
    for seed in SEEDS:
        rng = np.random.default_rng(seed)

        def rand_screen(f, names, _rng=rng):
            k = int(len(names) * 0.20)
            drop = set(_rng.choice(names, size=k, replace=False))
            return pd.Index([x for x in names if x not in drop])

        pb = book_path(panel, months, elig, rand_screen)
        idx = pb.index.intersection(common)
        screen_vs_rand.append(t_stat(scr.loc[idx, "net"] - pb.loc[idx, "net"]))
    pooled_vs_rand = float(np.mean(screen_vs_rand))

    dt_net = t_stat(diff)
    mean_bps = float(diff.mean()) * 1e4
    killed = (dt_net <= 0 or abs(pooled_vs_rand) < 1.5
              or inc_turn > 0.05)
    res = {
        "trial": "TRIAL-EXT-EXCLUDE-1", "base": "EW-universe (fallback)",
        "months": int(len(common)),
        "dt_net_screen_minus_base": round(dt_net, 3),
        "mean_improvement_bps_mo": round(mean_bps, 2),
        "incremental_turnover_1way": round(inc_turn, 4),
        "base_net_t": round(t_stat(base.loc[common, "net"]), 3),
        "screened_net_t": round(t_stat(scr.loc[common, "net"]), 3),
        "random_exclusion_placebos": rng_placebo,
        "screen_vs_random_t_by_seed": [round(x, 3) for x in screen_vs_rand],
        "screen_vs_random_pooled_t": round(pooled_vs_rand, 3),
        "verdict": "KILLED" if killed else "PASS",
        "kill_reasons": {
            "dt_net_le_0": bool(dt_net <= 0),
            "indistinguishable_from_random": bool(abs(pooled_vs_rand) < 1.5),
            "turnover_gt_005": bool(inc_turn > 0.05)},
    }
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
