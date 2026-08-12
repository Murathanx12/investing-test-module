"""ABLATION-1 supplement — CANON §20 and Amendment A8 for the ARM FAMILY.

    python -m scripts.ablation_family_check --calls <snapshot>

`run_ablation_1` prints thirteen arms and twenty-two paired contrasts. Neither
count is a count of independent chances:

* §20 — thirteen arms built from the same four legs on the same 119 months are
  not thirteen distinct configurations. Chunk 6 got 2.02-2.40 effective from 47;
  chunk 5 got 5.60 from 36. This computes the same statistic (arms / (1 + (n-1)
  * mean |pairwise corr|)) on the monthly excess series, so chunk 9's number is
  comparable to theirs.
* §A8 — the deflated Sharpe ratio is computed for the FAMILY, with the search
  denominator set to the EFFECTIVE arm count and, separately, to the raw count,
  because the two bracket the honest answer and picking one silently would be a
  choice made after seeing which flatters.

It also prints the exact duplicate detection: two ARMS entries with identical
drop-sets and sources are ONE arm wearing two names, and the ladder must not be
allowed to count it twice.

No permutations, no LLM calls. ~1 minute.
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
from scripts.pf7_deflated_sharpe import deflated_sharpe, expected_max_sr
from scripts.run_ablation_1 import (ARMS, AUX, CALLS, LLM_CELLS, MARKET, PANEL,
                                    legs, per_spec_frame, simulate,
                                    swarm_score)
from scripts.run_portfolio_arena_1 import load_lc

FACTORY = MODULE_ROOT / "data" / "factory"
OUT = FACTORY / "ablation_family_check.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", default=str(CALLS))
    ap.add_argument("--K", type=int, default=10)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    t0 = time.time()

    calls = pd.read_json(a.calls, lines=True)
    ps = per_spec_frame(calls)

    panel = pd.read_parquet(PANEL)
    cells = pd.read_parquet(LLM_CELLS)[["date_ix", "permno"]]
    panel = panel.merge(cells, on=["date_ix", "permno"], how="inner")
    panel["log_mcap"] = np.log(panel["mcap"].clip(lower=1.0))
    panel["log_adv"] = np.log(panel["adv"].clip(lower=1.0))
    by_date = {int(k): g.set_index("permno") for k, g in panel.groupby("date_ix")}
    mkt = pd.read_parquet(MARKET).set_index("date_ix")
    dates_k = sorted(by_date)
    LC, dec_ix, mkt_log = load_lc()

    regime = {k: ("risk_on" if (float(mkt.loc[k, "mkt_ret_252"]) > 0
                                and float(mkt.loc[k, "mkt_dd_252"]) > -0.10)
                  else "risk_off") for k in dates_k}

    # ── duplicate detection, before anything is counted ─────────────────────
    sig: dict[tuple, list] = {}
    for n, s in ARMS.items():
        key = (tuple(sorted(s["drop"])), tuple(sorted(s.get("roles") or ())),
               s["src"], bool(s.get("conf")))
        sig.setdefault(key, []).append(n)
    dupes = {"|".join(v): len(v) for v in sig.values() if len(v) > 1}

    def arm_scores(spec: dict) -> dict:
        g = swarm_score(ps, spec["src"], spec.get("roles"),
                        conf_weighted=bool(spec.get("conf")))
        llm_by = {int(k): v.set_index("permno")["score"]
                  for k, v in g.groupby("date_ix")}
        out = {}
        for k in dates_k:
            d = by_date[k]
            L = legs(d, regime[k], llm_by.get(k))
            use = {n: v for n, v in L.items() if n not in spec["drop"]}
            if not use:
                continue
            out[k] = sum(use.values()) / len(use)
        return out

    ex: dict[str, pd.Series] = {}
    for n, spec in ARMS.items():
        fr = simulate(arm_scores(spec), by_date, mkt, dates_k, LC, dec_ix,
                      mkt_log, a.K)
        if len(fr) == 0:
            continue
        kk = fr["date_ix"].to_numpy()
        ex[n] = pd.Series(fr["net"].to_numpy()
                          - mkt.loc[kk, "mkt_fwd_1m"].to_numpy(), index=kk)
        print(f"  {n}: {len(fr)} months ({time.time()-t0:.0f}s)", flush=True)

    keys = sorted(ex)
    idx = ex[keys[0]].index
    for k in keys:
        idx = idx.intersection(ex[k].index)
    M = np.vstack([ex[k].loc[idx].to_numpy() for k in keys])
    C = np.corrcoef(M)
    off = C[~np.eye(len(keys), dtype=bool)]
    mean_abs = float(np.nanmean(np.abs(off)))
    eff = float(len(keys) / (1.0 + (len(keys) - 1) * mean_abs))

    # the ladder's six A4 arms, separately — the count that A4 actually cares
    # about. shuffled and time-shifted are transformations of `full`, so they
    # are named here but their series live in the primary artifact.
    ladder = ["full", "llm_only_swarm", "llm_only_generic", "randtext"]
    lk = [k for k in ladder if k in ex]
    Ml = np.vstack([ex[k].loc[idx].to_numpy() for k in lk])
    Cl = np.corrcoef(Ml)
    offl = Cl[~np.eye(len(lk), dtype=bool)]
    mal = float(np.nanmean(np.abs(offl)))
    effl = float(len(lk) / (1.0 + (len(lk) - 1) * mal))

    # ── A8: DSR for the family, at BOTH denominators ────────────────────────
    from scipy import stats as _st
    dsr_rows = {}
    n_obs = int(len(idx))
    srs = {k: float(ex[k].loc[idx].mean() / ex[k].loc[idx].std(ddof=1))
           for k in keys}
    var_sr = float(np.var(list(srs.values()), ddof=1))
    best = max(srs, key=lambda k: srs[k])
    for label, ntr in (("raw_arm_count", len(keys)),
                       ("effective_arm_count", max(1, round(eff))),
                       ("campaign_denominator_323_plus_13", 336)):
        sr0 = expected_max_sr(ntr, var_sr)
        x = ex[best].loc[idx]
        dsr_rows[label] = {
            "n_trials": ntr,
            "sr0_monthly": round(sr0, 4),
            "best_arm": best,
            "best_sr_monthly": round(srs[best], 4),
            "DSR": round(deflated_sharpe(srs[best], sr0, n_obs,
                                         float(_st.skew(x)),
                                         float(_st.kurtosis(x, fisher=False))),
                         4),
        }

    out = {
        "label": "ARCHITECTURE_RESULT_ONLY / §20 + A8 SUPPLEMENT",
        "calls_file": Path(a.calls).name, "n_calls": int(len(calls)),
        "n_months": n_obs,
        "duplicate_arms": dupes,
        "all_arms": {
            "n_arms": len(keys),
            "mean_abs_pairwise_corr_monthly_excess": round(mean_abs, 4),
            "effective_distinct_arms": round(eff, 2),
        },
        "a4_ladder_only": {
            "arms": lk,
            "mean_abs_pairwise_corr_monthly_excess": round(mal, 4),
            "effective_distinct_arms": round(effl, 2),
        },
        "sharpe_by_arm_monthly": {k: round(v, 4) for k, v in srs.items()},
        "cross_arm_var_sr": round(var_sr, 6),
        "deflated_sharpe_family": dsr_rows,
        "n_arms_positive_excess_sharpe": int(sum(v > 0 for v in srs.values())),
        "note": ("The DSR is computed on the BEST arm, which bounds the whole "
                 "family from above: if the best arm does not clear 0.95 "
                 "against the search denominator, no arm in the family does. "
                 "The three denominators are printed together because "
                 "choosing one after seeing which flatters is the failure "
                 "A8 exists to prevent."),
        "wall_seconds": round(time.time() - t0, 1),
    }
    Path(a.out).write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {a.out} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
