"""T4 — trial-count accounting on the survivor. Publish the number either way.

The charge (external review, and Harvey-Liu-Zhu 2016 / Bailey & Lopez de Prado
2014, both verified in runs/NIGHT7/VERIFIED_CITATIONS.md): PF-PROF-COMPOSITE-150
was selected as the best of a large search and then judged against a t-bar
calibrated as though it were the first test on this data. The expected MAXIMUM
of N draws from a null is not zero, and it grows with N.

This computes the Deflated Sharpe Ratio of the survivor's EXCESS series - the
statistic the claim actually rests on ("it beats the market"), not the raw
Sharpe of its returns.

Two honesty devices:

  1. The cross-trial Sharpe variance V[SR] is ESTIMATED FROM OUR OWN GRAVEYARD
     (148 scored rows with t and month counts), not assumed. A DSR that plugs in
     a guessed V[SR] is theatre.

  2. There is no single defensible "effective number of independent trials" -
     the 179 candidates are correlated, so nominal N overstates and 1
     understates. Rather than pick one and hide the choice, this reports DSR
     across a LADDER of N and prints the BREAK-EVEN N: the number of independent
     trials at which the claim stops clearing 0.95. The reader can then decide
     whether the search was bigger or smaller than that.

Reported, never deciding.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.ERROR)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf import ledger as L
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.panel63 import annualize
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "NIGHT7"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"
GRAVEYARD = MODULE_ROOT / "runs" / "PF5" / "T4_graveyard_rows.csv"

EULER = 0.5772156649015329
N_LADDER = (1, 5, 10, 25, 50, 100, 148, 179, 300, 648, 821, 2000)


def expected_max_sr(n_trials: int, var_sr: float) -> float:
    """E[max SR] under the null across n independent trials (Bailey-LdP eq. 4).

    SR0 = sqrt(V[SR]) * [ (1-g)*Z(1 - 1/N) + g*Z(1 - 1/(N*e)) ]
    """
    if n_trials <= 1:
        return 0.0
    z1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(np.sqrt(var_sr) * ((1.0 - EULER) * z1 + EULER * z2))


def deflated_sharpe(sr: float, sr0: float, n_obs: int, skew: float,
                    kurt: float) -> float:
    """P(true SR > 0 | observed SR, n trials, non-normality). Bailey-LdP eq. 8.

    sr, sr0 and the moments are all PER-OBSERVATION (monthly here). kurt is the
    non-excess (Pearson) kurtosis: 3.0 for a normal.
    """
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2
    if denom <= 0:
        return float("nan")
    z = (sr - sr0) * np.sqrt(n_obs - 1.0) / np.sqrt(denom)
    return float(stats.norm.cdf(z))


def series_stats(excess: pd.Series) -> dict:
    x = excess.dropna()
    sr = float(x.mean() / x.std(ddof=1))
    return {"months": int(len(x)),
            "sr_monthly": round(sr, 4),
            "sr_annualized": round(sr * np.sqrt(12), 4),
            "skew": round(float(stats.skew(x)), 4),
            "kurtosis_pearson": round(float(stats.kurtosis(x, fisher=False)), 4),
            "t_iid": round(sr * np.sqrt(len(x)), 3),
            "t_newey_west_12": D.nw_t(x),
            "excess_cagr": round(annualize(x + 0.0) if False else float("nan"), 4)}


def var_sr_menu(n_obs: int) -> dict:
    """Three defensible V[SR] inputs, spanning the honest range.

    Bailey-LdP's V[SR] is the variance of the trial Sharpes the search selected
    the maximum FROM. There is no single right estimate here and pretending
    otherwise is where this statistic usually goes wrong, so all three are
    reported and the verdict is read across them.

    RAW is the naive plug-in and it OVER-deflates: our graveyard contains books
    with t as low as -8.4, which are cost-destroyed implementations, not draws
    the search was ever choosing between. Their spread is real but it is not
    search dispersion.

    ROBUST rescales a median-absolute-deviation to a Gaussian sigma, so the
    cost-destroyed tail cannot set the scale.

    NULL is the classical floor: if every trial were pure noise over the SAME
    n_obs months, observed Sharpes would have variance 1/n_obs. This is the
    most strategy-FAVOURABLE assumption that is still defensible, so a claim
    that fails here fails everywhere.
    """
    g = pd.read_csv(GRAVEYARD)
    g = g[g["months"] > 12].dropna(subset=["t_excess_net", "months"])
    sr = g["t_excess_net"].astype(float) / np.sqrt(g["months"].astype(float))
    mad = float(np.median(np.abs(sr - np.median(sr))))
    robust = (1.4826 * mad) ** 2
    # variance components: observed spread = true spread + estimation noise
    noise = float((1.0 / g["months"].astype(float)).mean())
    return {
        "n_rows_used": int(len(sr)),
        "source": "runs/PF5/T4_graveyard_rows.csv (t_excess_net / sqrt(months))",
        "graveyard_t_range": [round(float(g["t_excess_net"].min()), 2),
                              round(float(g["t_excess_net"].max()), 2)],
        "estimates": {
            "RAW_graveyard": {
                "var_sr_monthly": round(float(sr.var(ddof=1)), 6),
                "std_sr_annualized": round(float(sr.std(ddof=1)) * np.sqrt(12), 4),
                "note": "naive plug-in; OVER-deflates (see docstring)"},
            "ROBUST_mad": {
                "var_sr_monthly": round(robust, 6),
                "std_sr_annualized": round(np.sqrt(robust) * np.sqrt(12), 4),
                "note": "1.4826*MAD squared; tail-resistant central estimate"},
            "NULL_pure_noise": {
                "var_sr_monthly": round(1.0 / n_obs, 6),
                "std_sr_annualized": round(np.sqrt(1.0 / n_obs) * np.sqrt(12), 4),
                "note": ("1/T: every trial pure noise over the candidate's own "
                         "window. The MOST FAVOURABLE defensible choice - "
                         "failing here is unarguable")},
        },
        "variance_components": {
            "observed_var": round(float(sr.var(ddof=1)), 6),
            "mean_estimation_noise_var": round(noise, 6),
            "implied_true_dispersion_var": round(
                float(sr.var(ddof=1)) - noise, 6)},
        "caveat": ("the graveyard is the SURVIVING record of the search, not "
                   "every cell ever computed"),
    }


def run_config(f, base_d, name, **over) -> pd.Series:
    spec = StrategySpec(**{**base_d, "name": name, **over})
    era = (D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())
           if over.get("cost_model") == "ko" else None)
    elig = f.eligible(spec.segment)
    score, _ = composite_score(f.lib, spec.signals, elig)
    out = run_book(f.spine.panel, score, elig, spec, f.spine.rf, era)
    net = out["monthly"]["net"].dropna()
    return (net - f.spine.mkt.reindex(net.index)).dropna()


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()

    f = Factory()
    configs = {
        "as_banked_monthly_flat25": run_config(
            f, d, "DSR__banked", rebalance_months=1, cost_model="flat25"),
        "shippable_annual_era": run_config(
            f, d, "DSR__annual_era", rebalance_months=12, cost_model="ko"),
    }

    n_obs_ref = int(len(configs["shippable_annual_era"].dropna()))
    vs = var_sr_menu(n_obs_ref)
    res = {
        "task": "T4 trial-count accounting (Deflated Sharpe)",
        "trial": "TRIAL-PF7-DSR-1",
        "status": "REPORTED-NEVER-DECIDING",
        "statistic": ("DSR on the EXCESS series (strategy minus CRSP VW total "
                      "return) - the claim is 'it beats the market', so the "
                      "market-relative Sharpe is what must survive deflation"),
        "var_sr_estimate": vs,
        "ledger_denominator": L.testing_block(2.85, None),
        "configs": {},
    }

    for key, ex in configs.items():
        st = series_stats(ex)
        st["excess_cagr"] = round(annualize(ex), 4)
        grids, breakevens = {}, {}
        for vname, vinfo in vs["estimates"].items():
            v = vinfo["var_sr_monthly"]
            ladder = {}
            for n in N_LADDER:
                sr0 = expected_max_sr(n, v)
                dsr = deflated_sharpe(st["sr_monthly"], sr0, st["months"],
                                      st["skew"], st["kurtosis_pearson"])
                ladder[str(n)] = {
                    "expected_max_sr_annualized": round(sr0 * np.sqrt(12), 4),
                    "DSR": round(dsr, 4),
                    "clears_0.95": bool(dsr >= 0.95)}
            grids[vname] = ladder
            # break-even N: largest N still clearing DSR 0.95, by bisection
            def ok(n: int) -> bool:
                return deflated_sharpe(st["sr_monthly"], expected_max_sr(n, v),
                                       st["months"], st["skew"],
                                       st["kurtosis_pearson"]) >= 0.95
            if not ok(2):
                breakevens[vname] = 1
            else:
                lo, hi = 2, 10 ** 9
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if ok(mid):
                        lo = mid
                    else:
                        hi = mid - 1
                breakevens[vname] = lo
        res["configs"][key] = {
            "series": st, "dsr_grid_by_var_estimate": grids,
            "breakeven_independent_trials_at_DSR_0.95": breakevens,
            "reading": (
                f"survives deflation only if the programme's EFFECTIVE "
                f"independent trial count is below "
                f"{breakevens['NULL_pure_noise']:,} even under the MOST "
                f"favourable variance assumption (all trials pure noise). "
                f"Counts on record: 148 scored graveyard rows, 179 closed "
                f"candidates, "
                f"{res['ledger_denominator'].get('denominator', {}).get('total', '?')} "
                f"programme-wide."),
        }

    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "T4_DEFLATED_SHARPE.json").write_text(json.dumps(res, indent=2),
                                                 encoding="utf-8")
    for k, v in res["configs"].items():
        s = v["series"]
        print(f"\n{k}: excess CAGR {s['excess_cagr']:+.2%}, SR_ann "
              f"{s['sr_annualized']:.3f}, t_iid {s['t_iid']}, "
              f"NW {s['t_newey_west_12']}, months {s['months']}")
        for vname, be in v["breakeven_independent_trials_at_DSR_0.95"].items():
            print(f"  V[SR]={vname:18s} break-even N at DSR 0.95: {be:,}")
            for n in ("50", "148", "179", "821"):
                e = v["dsr_grid_by_var_estimate"][vname][n]
                print(f"     N={n:>4}: E[maxSR]ann "
                      f"{e['expected_max_sr_annualized']:.3f}  DSR {e['DSR']:.4f}"
                      f"  {'PASS' if e['clears_0.95'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
