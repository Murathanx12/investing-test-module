"""REAL-NULL-2 — real-data null CDFs for the one-shot replay's flat floor.

Pre-registered in TRIALS/PREREG_REAL_NULL_2.md BEFORE any statistic existed.
Harness = REAL-NULL-1 (verified: reproduces banked batch-1 numbers exactly),
extended to both segments, with RAW SAMPLES saved for the replay's empirical
p-values.

Run:  python scripts/real_null_2.py --segment largemid
      python scripts/real_null_2.py --segment small
(each ~1-2 h at K=5000 x 4 phis; resumable per segment — output is per-segment)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

MOD = Path(__file__).resolve().parents[1]
PANEL = MOD / "data" / "crsp_panel_2002"
OUT = MOD / "runs" / "REPLAY-2"

MIN_PRICE = 1.0
MIN_DV = 200_000.0
MIN_NAMES = 100
MIN_OK = 30
EXPLORE = ("2004-01-31", "2018-12-31")
CONFIRM = ("2019-01-31", "2024-12-31")
PHIS = (0.97, 0.99, 0.995, 0.999)     # frozen in the prereg
SEED = 20260808                        # frozen in the prereg
GUARD_BANKED = {"vol_12m_low": 1.89, "price_level": 2.12}
REPLICATION_BAND = (0.06, 0.11)        # largemid pooled P(t>=1.5) VOID band


def t_stat(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--segment", choices=("largemid", "small"), required=True)
    ap.add_argument("--K", type=int, default=5000)
    args = ap.parse_args()

    ret = pd.read_parquet(PANEL / "monthly_ret.parquet")
    prc = pd.read_parquet(PANEL / "month_end_price.parquet")
    dv = pd.read_parquet(PANEL / "monthly_dollar_vol.parquet")
    months = ret.index
    R = ret.to_numpy(dtype="float64")
    print(f"panel: {ret.shape[0]} months x {ret.shape[1]} permnos | "
          f"segment {args.segment} | K={args.K} x phis {PHIS}")

    elig = (prc >= MIN_PRICE) & (dv >= MIN_DV)
    rank_dv = dv.rank(axis=1, ascending=False)

    def seg_mask(segment: str) -> np.ndarray:
        if segment == "largemid":
            return (elig & (rank_dv <= 1000)).to_numpy()
        return (elig & (rank_dv > 1000) & (rank_dv <= 3000)).to_numpy()

    def month_slots(window, es: np.ndarray):
        lo, hi = pd.Timestamp(window[0]), pd.Timestamp(window[1])
        slots = []
        for pos, m in enumerate(months):
            if not (lo <= m <= hi) or pos == 0:
                continue
            e = np.flatnonzero(es[pos - 1])
            if e.size < MIN_NAMES:
                continue
            slots.append((pos - 1, pos, e))
        return slots

    def prep(slots):
        out = []
        for f, t, e in slots:
            fwd = R[t, e]
            ok = ~np.isnan(fwd)
            if ok.sum() < MIN_OK:
                continue
            out.append((f, e[ok], rankdata(fwd[ok]), e))
        return out

    def ic_path(score_mat: np.ndarray, pre) -> np.ndarray:
        ics = np.empty(len(pre))
        for k, (f, cols, fwd_r, e) in enumerate(pre):
            s = score_mat[f, e]
            good = ~np.isnan(s)
            if good.sum() < MIN_NAMES:
                ics[k] = np.nan
                continue
            keep = np.isin(e[good], cols, assume_unique=False)
            sc = s[good][keep]
            fr = fwd_r[np.isin(cols, e[good])]
            if sc.size < MIN_OK:
                ics[k] = np.nan
                continue
            ics[k] = np.corrcoef(rankdata(sc), rankdata(fr))[0, 1]
        return ics

    # ---------------- GUARD (always on largemid — see prereg limitation) ----
    lm = seg_mask("largemid")
    ex_lm = prep(month_slots(EXPLORE, lm))
    vol12 = (-ret.rolling(12, min_periods=9).std()).to_numpy(dtype="float64")
    plevel = np.log(prc.where(prc > 0)).to_numpy(dtype="float64")
    guard = {}
    for name, mat in (("vol_12m_low", vol12), ("price_level", plevel)):
        tv = round(t_stat(ic_path(mat, ex_lm)), 2)
        guard[name] = {"measured": tv, "banked": GUARD_BANKED[name],
                       "match": tv == GUARD_BANKED[name]}
        print(f"GUARD {name:14s} {tv:5.2f} vs banked "
              f"{GUARD_BANKED[name]:5.2f} "
              f"{'PASS' if guard[name]['match'] else 'FAIL'}")
    OUT.mkdir(parents=True, exist_ok=True)
    if not all(g["match"] for g in guard.values()):
        json.dump({"guard": guard, "status": "VOID"},
                  open(OUT / f"real_null_2_{args.segment}_meta.json", "w"),
                  indent=2)
        sys.exit("GUARD FAILED — VOID, no null statistic reported.")
    print("GUARD PASSED\n")

    # ---------------- NULL RUN --------------------------------------------
    es = seg_mask(args.segment)
    ex_pre = prep(month_slots(EXPLORE, es))
    cf_pre = prep(month_slots(CONFIRM, es))
    print(f"scored months: explore {len(ex_pre)} | confirm {len(cf_pre)}")

    T, N = R.shape
    rng = np.random.default_rng(SEED if args.segment == "largemid"
                                 else SEED + 1)
    samples: dict[str, dict[str, list[float]]] = {}
    for phi in PHIS:
        t0 = time.time()
        tex, tcf = [], []
        sd_eps = np.sqrt(1 - phi ** 2)
        for k in range(args.K):
            eps = rng.standard_normal((T, N))
            x = np.empty((T, N))
            x[0] = eps[0]
            for t in range(1, T):
                x[t] = phi * x[t - 1] + sd_eps * eps[t]
            tex.append(t_stat(ic_path(x, ex_pre)))
            tcf.append(t_stat(ic_path(x, cf_pre)))
            if (k + 1) % 500 == 0:
                print(f"  phi={phi} {k+1}/{args.K} "
                      f"({time.time()-t0:.0f}s)", flush=True)
        samples[str(phi)] = {"t_explore": tex, "t_confirm": tcf}
        te = np.array(tex)
        print(f"phi={phi}: P(t>=1.5)={float((te >= 1.5).mean()):.4f} "
              f"p95={float(np.percentile(te, 95)):.3f} "
              f"({time.time()-t0:.0f}s)")

    pooled_ex = np.concatenate([np.array(v["t_explore"])
                                for v in samples.values()])
    pooled_cf = np.concatenate([np.array(v["t_confirm"])
                                for v in samples.values()])
    grad = pooled_ex >= 1.5
    p_ge = float(grad.mean())
    adopt = grad & (pooled_cf >= 0.5)
    meta = {
        "guard": guard, "status": "OK", "segment": args.segment,
        "K_per_phi": args.K, "phis": list(PHIS), "seed": SEED,
        "n_pooled": int(pooled_ex.size),
        "pooled_p_ge_1.5": round(p_ge, 4),
        "pooled_p95": round(float(np.percentile(pooled_ex, 95)), 3),
        "pooled_p99": round(float(np.percentile(pooled_ex, 99)), 3),
        "p_confirm_given_grad": (round(float(adopt.sum() / grad.sum()), 4)
                                 if grad.sum() else None),
        "explore_months": len(ex_pre), "confirm_months": len(cf_pre),
    }
    if args.segment == "largemid" and not (
            REPLICATION_BAND[0] <= p_ge <= REPLICATION_BAND[1]):
        meta["status"] = "VOID-REPLICATION"
        print(f"REPLICATION BAND VIOLATED: {p_ge} outside {REPLICATION_BAND} "
              "— VOID pending diagnosis (prereg kill condition).")

    np.savez_compressed(
        OUT / f"real_null_2_{args.segment}.npz",
        **{f"{k}_{leg}": np.array(v[leg]) for k, v in samples.items()
           for leg in ("t_explore", "t_confirm")},
        pooled_t_explore=pooled_ex, pooled_t_confirm=pooled_cf)
    json.dump(meta, open(OUT / f"real_null_2_{args.segment}_meta.json", "w"),
              indent=2)
    print(json.dumps(meta, indent=2))
    print(f"written -> real_null_2_{args.segment}.npz + meta")


if __name__ == "__main__":
    main()
