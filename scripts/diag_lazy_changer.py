"""Diagnostic on TRIAL-TEXT-LAZY's pre-declared CHANGER cohort.

Not a re-scan of the trial. The trial is decided (REJECT, results_explore.json).
This asks one question about the ONE quantity in that file that looked like a
pass: is the changer cohort's -3.06% / t=-15.03 the Lazy-Prices hypothesis, or
is it the plumbing?

Three checks, all pre-committed here before running:

  A. CONTROL. Run the identical cohort statistic on ctl_cos / ctl_jac — the same
     filings scored against a RANDOM DIFFERENT FIRM. Under the hypothesis the
     control cohort is noise. If the control reproduces the effect, the effect is
     "bottom decile of a document-similarity score", not "firms that changed
     their 10-K". This is the TRIAL-EVENT-8K-FILTER lesson (NEG_RESULTS s20)
     applied before, not after.

  B. OVERLAP. The reported t uses monthly observations of 3-month returns: each
     observation shares 2/3 of its window with its neighbours. Recompute on
     NON-OVERLAPPING quarters (every 3rd month) and with Newey-West(3).

  C. COMPOSITION. What is the bottom decile actually selecting? Report its median
     dollar-volume rank and month-over-month persistence vs the universe.
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
from aegis_brain.data.eodhd_panel import load_cached_panel
from aegis_brain.factory.explore import ScanConfig, segment_mask
from scripts.run_trial_lazy import build_frames

LO, HI = "2004-01-31", "2018-12-31"


def _t(x) -> float:
    x = pd.Series(x).dropna()
    if len(x) < 2:
        return float("nan")
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(len(x))) if sd > 0 else float("nan")


def _t_nw(x, lags: int = 3) -> float:
    """Newey-West t on the mean, the standard fix for overlapping windows."""
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    n = len(x)
    if n < 5:
        return float("nan")
    e = x - x.mean()
    g0 = float(e @ e) / n
    var = g0
    for L in range(1, min(lags, n - 1) + 1):
        gL = float(e[L:] @ e[:-L]) / n
        var += 2.0 * (1.0 - L / (lags + 1.0)) * gL
    if var <= 0:
        return float("nan")
    return float(x.mean() / np.sqrt(var / n))


def cohort(panel, frame, seg_name, mask, seg_ew, elig, months, stride: int = 1):
    vals, comp_rank, comp_persist = [], [], []
    prev = None
    for i, m in enumerate(months):
        if not (pd.Timestamp(LO) <= m <= pd.Timestamp(HI)) or i + 3 >= len(months):
            continue
        if (i % stride) != 0:
            prev = None
            continue
        s = frame.loc[m].dropna()
        s = s[s.index.isin(elig.loc[m][elig.loc[m]].index)]
        s = s[s.index.isin(mask.loc[m][mask.loc[m]].index)]
        if len(s) < 100:
            prev = None
            continue
        worst = s.nsmallest(max(int(len(s) * 0.10), 10)).index
        win = months[i + 1: i + 4]
        r = panel.monthly_ret.loc[win, list(worst)]
        cum = (1.0 + r.fillna(0.0)).prod(axis=0) - 1.0
        bench = float(np.prod(1.0 + seg_ew[seg_name].loc[win].fillna(0.0).values) - 1.0)
        vals.append(float(cum.mean()) - bench)

        # composition: where does the cohort sit in the segment's dv-rank?
        dv = panel.monthly_dollar_vol.loc[m].reindex(s.index).rank(pct=True)
        comp_rank.append(float(dv.reindex(worst).median()))
        if prev is not None:
            comp_persist.append(len(set(worst) & prev) / len(worst))
        prev = set(worst)

    return {
        "n_obs": len(vals),
        "mean_3m_excess_pct": round(float(np.mean(vals)) * 100, 2) if vals else None,
        "t_naive": round(_t(vals), 2) if vals else None,
        "t_newey_west3": round(_t_nw(vals), 2) if vals else None,
        "median_dv_pctile_in_segment": round(float(np.mean(comp_rank)), 3) if comp_rank else None,
        "cohort_persistence": round(float(np.mean(comp_persist)), 3) if comp_persist else None,
    }


def main() -> None:
    t0 = time.time()
    panel = load_cached_panel(MODULE_ROOT / "data" / "crsp_panel_2002")
    frames = build_frames(panel)
    ret = panel.monthly_ret
    months = ret.index
    lm, sm = segment_mask(panel, "largemid"), segment_mask(panel, "small")
    seg_ew = {"largemid": ret.where(lm).mean(axis=1), "small": ret.where(sm).mean(axis=1)}
    elig = panel.eligible() & (lm | sm)

    out = {"diagnostic": "TRIAL-TEXT-LAZY changer cohort",
           "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "note": "Diagnostic on a pre-declared reported quantity. Decides nothing "
                   "about the trial, which is REJECTED on its registered bar.",
           "results": {}}

    for name in ("text_cos", "text_jac", "ctl_cos", "ctl_jac"):
        for seg, mask in (("largemid", lm), ("small", sm)):
            key = f"{name}/{seg}"
            out["results"][key] = {
                "overlapping_monthly": cohort(panel, frames[name], seg, mask,
                                              seg_ew, elig, months, stride=1),
                "non_overlapping_quarterly": cohort(panel, frames[name], seg, mask,
                                                    seg_ew, elig, months, stride=3),
            }
            print(key, json.dumps(out["results"][key]["overlapping_monthly"]))

    out["elapsed_s"] = round(time.time() - t0, 1)
    p = MODULE_ROOT / "runs" / "TRIAL-TEXT-LAZY" / "diag_changer_cohort.json"
    p.write_text(json.dumps(out, indent=2))
    print("\nwrote", p)


if __name__ == "__main__":
    main()
