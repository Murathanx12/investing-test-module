"""TRIAL-EXT-PROF-SMALL-1 — the profitability cohort, small segment, one shot.

Pre-registered: TRIALS/PREREG_EXT_BANK_1.md (committed before M4 scoring).
Explore window ONLY. Confirm stays shut.

Guard: reproduce the banked osap_GP small explore line (t_ic 7.31, t_net
+2.42 from runs/EXT-NULL-1/scan_predictor.csv, verified session 2026-08-07)
before any new number is read.

Gates per registration:
  G1  BH within the EXT-BANK-1 denominator on empirical p vs the
      REAL-NULL-2 small pooled persistent CDF (raw samples, runs/REPLAY-2)
  G2  money leg: t_net >= 1.5 under BOTH flat-25 and KO-half arms
  G3  long-leg share of D10-D1 spread >= 50%
  Contrast: CBOperProf >= GP on t_net (Ball et al. 2016)
  Sigma-family check: |rho| vs vol_12m reported per member

Run:  python scripts/run_ext_prof_small_1.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.calibration.replay2_eval import bh_reject, empirical_p
from aegis_brain.config import MODULE_ROOT
from aegis_brain.costs import build_spread_frame
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, scan_signal, segment_mask
from aegis_brain.factory.osap import ScoreGridder, load_doc, meta_table
from aegis_brain.factory.signals import FactorySignal

COHORT = ["GP", "OperProf", "OperProfRD", "CBOperProf", "cfp", "roaq"]
GUARD = {"signal": "osap_GP", "segment": "small", "t_ic": 7.31,
         "t_net": 2.42}
Q = 0.10
# EXT-BANK-1 denominator at registration: 209 scanned predictors + the
# registered EXT designs (6 cohort members here + 7 issuance + 2 composites
# + 1 exclusion + 1 ML) — frozen conservative m
M_EXT_BANK = 209 + 17
SEG = "small"
OUT = MODULE_ROOT / "runs" / "EXT-BANK-1"


def t_stat(x: pd.Series) -> float:
    x = x.dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else 0.0


def leg_decomposition(score: pd.DataFrame, direction: int, panel,
                      cfg: ScanConfig) -> dict:
    """Monthly D10-D1 spread and long-leg (D10 - universe EW) among eligible
    small names; shares from mean monthly contributions (§28 methodology)."""
    sc = score * float(direction)
    elig = panel.eligible() & segment_mask(panel, SEG)
    months = panel.monthly_ret.index
    lo, hi = pd.Timestamp(cfg.first_test_month), pd.Timestamp(cfg.last_test_month)
    spread, long_leg = [], []
    for m in months:
        if not (lo <= m <= hi):
            continue
        pos = months.get_loc(m)
        if pos == 0:
            continue
        f = months[pos - 1]
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
        d10 = float(r[dec == 9].mean())
        d1 = float(r[dec == 0].mean())
        spread.append(d10 - d1)
        long_leg.append(d10 - float(r.mean()))
    sp, ll = float(np.mean(spread)), float(np.mean(long_leg))
    return {"months": len(spread),
            "mean_spread_bps": round(sp * 1e4, 1),
            "mean_long_leg_bps": round(ll * 1e4, 1),
            "long_leg_share": round(ll / sp, 3) if sp != 0 else None}


def main() -> None:
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    cfg = ScanConfig()

    # REAL-NULL-2 small floor (must be certified OK)
    meta = json.loads((MODULE_ROOT / "runs" / "REPLAY-2" /
                       "real_null_2_small_meta.json").read_text("utf-8"))
    if meta.get("status") != "OK":
        raise SystemExit(f"REAL-NULL-2 small status {meta.get('status')!r} — "
                         "floor not certified, trial cannot run.")
    with np.load(MODULE_ROOT / "runs" / "REPLAY-2" /
                 "real_null_2_small.npz") as z:
        floor = np.sort(z["pooled_t_explore"])

    doc = load_doc()
    metas = {m.acronym: m for m in meta_table(doc)
             if m.acronym in COHORT + ["GP"]}
    missing = sorted(set(COHORT) - set(metas))
    if missing:
        raise SystemExit(f"doc rows missing for {missing} — refusing to scan")

    long_df = pd.read_parquet(MODULE_ROOT / "data" / "osap" /
                              "firm_char.parquet",
                              columns=["permno", "yyyymm"] + COHORT)
    gridder = ScoreGridder(long_df, panel)
    frames = {a: gridder.grid(long_df[a]) for a in COHORT}

    # ---------------- GUARD: reproduce banked osap_GP small ----------------
    gp_sig = FactorySignal("osap_GP", "guard", lambda p: frames["GP"],
                           metas["GP"].sign)
    g = scan_signal(panel, gp_sig, SEG, cfg)["summary"]
    ok = (round(g["t_ic"], 2) == GUARD["t_ic"]
          and round(g["t_excess_net"], 2) == GUARD["t_net"])
    print(f"GUARD osap_GP/small t_ic {g['t_ic']} vs {GUARD['t_ic']}, "
          f"t_net {g['t_excess_net']} vs {GUARD['t_net']} "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        raise SystemExit("GUARD FAILED — VOID, no cohort number reported.")

    ko = build_spread_frame(panel)
    vol12 = -panel.monthly_ret.rolling(12, min_periods=9).std()

    rows = []
    for a in COHORT:
        m = metas[a]
        sig = FactorySignal(f"osap_{a}", "cohort", lambda p, _f=frames[a]: _f,
                            m.sign)
        t0 = time.time()
        flat = scan_signal(panel, sig, SEG, cfg)["summary"]
        koh = scan_signal(panel, sig, SEG, cfg, cost_frame=ko)["summary"]
        legs = leg_decomposition(frames[a], m.sign, panel, cfg)
        # sigma-family: mean |cross-sectional spearman| vs 12m vol
        elig = panel.eligible() & segment_mask(panel, SEG)
        rhos = []
        months = panel.monthly_ret.index
        for mm in months[(months >= pd.Timestamp(cfg.first_test_month))
                         & (months <= pd.Timestamp(cfg.last_test_month))]:
            f = months[months.get_loc(mm) - 1]
            e = elig.loc[f]
            s = frames[a].loc[f].reindex(e[e].index).dropna()
            v = vol12.loc[f].reindex(s.index).dropna()
            s = s.reindex(v.index)
            if len(s) >= 100:
                r = s.rank().corr(v.rank())
                if np.isfinite(r):
                    rhos.append(abs(float(r)))
        p_emp = empirical_p(flat["t_ic"], floor)
        rows.append({
            "signal": a, "sign": m.sign,
            "t_ic": flat["t_ic"], "p_vs_floor": round(p_emp, 5),
            "t_net_flat25": flat["t_excess_net"],
            "t_net_ko_half": koh["t_excess_net"],
            "turnover_1way": flat["turnover_1way"],
            "months": flat["months"],
            **legs, "abs_rho_vol12": round(float(np.mean(rhos)), 3),
            "secs": round(time.time() - t0, 1)})
        print(json.dumps(rows[-1]))

    df = pd.DataFrame(rows)
    # G1: BH within the frozen EXT-BANK-1 denominator — pad to m with p=1
    pvals = list(df.p_vs_floor) + [1.0] * (M_EXT_BANK - len(df))
    flags = bh_reject(pvals, Q)[: len(df)]
    df["bh_pass"] = flags
    df["g2_money"] = (df.t_net_flat25 >= 1.5) & (df.t_net_ko_half >= 1.5)
    df["g3_long_leg"] = df.long_leg_share >= 0.50
    df["clears_all"] = df.bh_pass & df.g2_money & df.g3_long_leg

    contrast = (float(df[df.signal == "CBOperProf"].t_net_flat25.iloc[0])
                >= float(df[df.signal == "GP"].t_net_flat25.iloc[0]))
    verdict = {
        "n_clear_all_gates": int(df.clears_all.sum()),
        "clears": df[df.clears_all].signal.tolist(),
        "contrast_CBOperProf_ge_GP": bool(contrast),
        "kill_a_no_member_clears_bh": bool(~df.bh_pass.any()),
        "kill_b_no_long_leg": bool((df.long_leg_share < 0.50).all()),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "trial_ext_prof_small_1.json"
    if out.exists():
        raise SystemExit(f"{out} exists — one shot; rerun is a new trial ID.")
    out.write_text(json.dumps({
        "trial": "TRIAL-EXT-PROF-SMALL-1", "guard": GUARD,
        "m_ext_bank": M_EXT_BANK, "q": Q,
        "floor_meta": meta, "rows": df.to_dict("records"),
        "verdict": verdict}, indent=2), encoding="utf-8")
    print(json.dumps(verdict, indent=2))
    print(f"written -> {out}")


if __name__ == "__main__":
    main()
