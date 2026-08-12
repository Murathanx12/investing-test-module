"""ABLATION-1 supplement — A3 risk matching on the DECISIVE placebo arm.

    python -m scripts.ablation_placebo_matched --calls <snapshot> --perm 200

`run_ablation_1` reports the shuffled-LLM placebo (Amendment A4 arm 1) on the
RAW pass only. Amendment A3 says every comparison in chunks 7 and 9 reports raw
AND matched, and chunk 5 is the reason: its one detectable arm was mostly beta
(0.787 vs 0.656) and dissolved on matching. The placebo is the arm that decides
chunk 9, so leaving it raw-only leaves the decisive comparison on the one
dimension the campaign has repeatedly been wrong about.

This runs the identical permutation (same seed, same pool, same code path) under
beta-matching and volatility-matching, and reports the observed `full` arm under
the same matchings so the difference is like-for-like.

It is a SUPPLEMENT, not a re-run: it does not overwrite `ablation_*.json`, and
the pre-registered primary remains the raw pass.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from scripts.arena_core import cagr, ruler
from scripts.run_ablation_1 import (ARMS, AUX, CALLS, LLM_CELLS, MARKET, PANEL,
                                    PERM_SEED, legs, per_spec_frame, simulate,
                                    summarise, swarm_score)
from scripts.run_portfolio_arena_1 import load_lc

FACTORY = MODULE_ROOT / "data" / "factory"
OUT = FACTORY / "ablation_placebo_matched.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", default=str(CALLS))
    ap.add_argument("--perm", type=int, default=200)
    ap.add_argument("--K", type=int, default=10)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    t0 = time.time()

    calls = pd.read_json(a.calls, lines=True)
    ps = per_spec_frame(calls)
    print(f"{len(calls)} calls ({Path(a.calls).name})", flush=True)

    panel = pd.read_parquet(PANEL)
    cells = pd.read_parquet(LLM_CELLS)[["date_ix", "permno"]]
    panel = panel.merge(cells, on=["date_ix", "permno"], how="inner")
    panel["log_mcap"] = np.log(panel["mcap"].clip(lower=1.0))
    panel["log_adv"] = np.log(panel["adv"].clip(lower=1.0))
    by_date = {int(k): g.set_index("permno") for k, g in panel.groupby("date_ix")}
    mkt = pd.read_parquet(MARKET).set_index("date_ix")
    dates_k = sorted(by_date)
    LC, dec_ix, mkt_log = load_lc()
    dec_dates = pd.DatetimeIndex(
        np.load(AUX, allow_pickle=False)["dec_dates"].astype("datetime64[ns]"))

    regime = {k: ("risk_on" if (float(mkt.loc[k, "mkt_ret_252"]) > 0
                                and float(mkt.loc[k, "mkt_dd_252"]) > -0.10)
                  else "risk_off") for k in dates_k}

    def arm_scores(llm_by: dict) -> dict:
        out = {}
        for k in dates_k:
            d = by_date[k]
            L = legs(d, regime[k], llm_by.get(k))
            out[k] = sum(L.values()) / len(L)
        return out

    g = swarm_score(ps, "swarm", None)
    base = {int(k): v.set_index("permno")["score"]
            for k, v in g.groupby("date_ix")}
    sco_obs = arm_scores(base)

    # turnover budget: the observed arm's own median, so the turnover match is
    # not defined by the placebos it is being compared against.
    fr_raw = simulate(sco_obs, by_date, mkt, dates_k, LC, dec_ix, mkt_log, a.K)
    tb = float(fr_raw["turnover_1way"].median())

    observed = {"raw": summarise(fr_raw, mkt, dec_dates)}
    for m in ("beta", "vol", "turnover"):
        fr = simulate(sco_obs, by_date, mkt, dates_k, LC, dec_ix, mkt_log, a.K,
                      matching=m, turnover_budget=tb)
        observed[m] = summarise(fr, mkt, dec_dates)
        print(f"observed {m}: {observed[m]['excess_cagr_pct']:+.3f}%/yr, "
              f"gross {observed[m]['gross_exposure_mean']:.3f}", flush=True)

    pool_keys = [(k, p) for k in base for p in base[k].index]
    pool_vals = np.array([float(base[k].loc[p]) for k, p in pool_keys])
    rng = np.random.default_rng(PERM_SEED)   # same seed as the primary

    acc = {m: {"excess": [], "gross": [], "vol": [], "turn": []}
           for m in ("raw", "beta", "vol", "turnover")}
    for i in range(a.perm):
        v = rng.permutation(pool_vals)
        sh: dict[int, dict] = {}
        for (k, p), val in zip(pool_keys, v):
            sh.setdefault(k, {})[p] = val
        shp = {k: pd.Series(d) for k, d in sh.items()}
        sco = arm_scores(shp)
        for m in ("raw", "beta", "vol", "turnover"):
            fr = simulate(sco, by_date, mkt, dates_k, LC, dec_ix, mkt_log, a.K,
                          matching=m, turnover_budget=tb)
            kk = fr["date_ix"].to_numpy()
            mm = mkt.loc[kk, "mkt_fwd_1m"].to_numpy()
            acc[m]["excess"].append((cagr(fr["net"].to_numpy())
                                     - cagr(mm)) * 100)
            acc[m]["gross"].append(float(fr["gross_exposure"].mean()))
            acc[m]["vol"].append(float(np.std(fr["net"].to_numpy(), ddof=1)
                                       * np.sqrt(12) * 100))
            acc[m]["turn"].append(float(fr["turnover_1way"].mean()))
        if (i + 1) % 25 == 0:
            print(f"  perm {i+1}/{a.perm} ({time.time()-t0:.0f}s)", flush=True)

    out = {
        "label": "ARCHITECTURE_RESULT_ONLY / A3 SUPPLEMENT",
        "calls_file": Path(a.calls).name, "n_calls": int(len(calls)),
        "n_permutations": a.perm, "perm_seed": PERM_SEED, "K": a.K,
        "n_dates": len(dates_k), "turnover_budget": round(tb, 4),
        "observed": observed, "placebo": {},
    }
    for m, d in acc.items():
        pe = np.array(d["excess"], dtype=float)
        obs = observed[m]["excess_cagr_pct"]
        out["placebo"][m] = {
            "observed_excess_cagr_pct": obs,
            "shuffled_mean_pct": round(float(pe.mean()), 3),
            "shuffled_sd_pct": round(float(pe.std(ddof=1)), 3),
            "shuffled_p05_pct": round(float(np.percentile(pe, 5)), 3),
            "shuffled_p95_pct": round(float(np.percentile(pe, 95)), 3),
            "permutation_p_value_one_sided": round(float((pe >= obs).mean()), 4),
            "observed_minus_shuffled_mean_pct": round(float(obs - pe.mean()), 3),
            "observed_gross": observed[m]["gross_exposure_mean"],
            "shuffled_gross_mean": round(float(np.mean(d["gross"])), 4),
            "observed_vol_ann_pct": observed[m]["vol_ann_pct"],
            "shuffled_vol_ann_pct_mean": round(float(np.mean(d["vol"])), 2),
            "observed_turnover": observed[m]["turnover_1way_mean"],
            "shuffled_turnover_mean": round(float(np.mean(d["turn"])), 4),
        }
    out["wall_seconds"] = round(time.time() - t0, 1)
    Path(a.out).write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {a.out} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
