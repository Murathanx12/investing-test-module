"""TRIAL-PF5-RANK-SHAPE-1 — does marginal alpha inside the top-150 have shape?

Registered in TRIALS/PREREG_PF5_RANK_SHAPE.md, committed ec06dc6 before this
file existed. Section 0 of that document discloses that we have already seen
ranks 11-20 win once; this script is scored against the four registered shapes,
not against that memory.

TWO IMPLEMENTATION DECISIONS ARE RECORDED HERE, both taken before any output was
read, and both of which TIGHTEN the registered rule rather than loosen it:

1. COMMON MONTH SET. NIGHT-4's boundary run skipped 233 of 481 months for deep
   rank windows because the small segment does not contain 300 eligible names in
   the early panel — the never-indexed $200k dollar-volume floor again. If each
   bucket were measured on the months it happens to survive, shallow buckets
   would carry the 1960s-70s and deep buckets would not, and the "shape" would
   be an era effect wearing a rank costume. Every bucket alpha here is computed
   on the INTERSECTION of months available to all buckets.

2. BOTH CLOCKS MUST AGREE. The prereg said bucket books rebalance "on the same
   clock as the parent book". That was ambiguous after NIGHT-4, because the
   parent's registered clock is monthly and its shippable clock is annual. Both
   are run. A shape counts only if it survives BOTH. Reporting the friendlier
   one would be exactly the substitution the prereg forbids.
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
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

OUT = MODULE_ROOT / "runs" / "PF5"
BANKED = MODULE_ROOT / "runs" / "PF2" / "PF-PROF-COMPOSITE-150__a1265dc617fb.json"

TOP = 150
SPLIT = "2001-01-01"
FAMILY_BONFERRONI_T = 2.50        # 4 shape tests, frozen in the prereg


# ── bucket books ────────────────────────────────────────────────────────────
def bucket_returns(f, base_d, score, elig, era, lo, hi, reb, tag) -> pd.Series:
    # min_names is checked against the SCORED row, and rank_window_score leaves
    # exactly (hi-lo+1) names scored. Setting it to `hi` silently skipped every
    # bucket but the first. The universe-depth requirement is enforced instead
    # by `deep_enough` on the eligibility frame, where it belongs.
    spec = StrategySpec(**{**base_d, "top_n": hi - lo + 1,
                           "min_names": hi - lo + 1,
                           "hold_band_mult": 1.0, "rebalance_months": reb,
                           "cost_model": "ko",
                           "name": f"PF5RANK__{tag}_{lo}_{hi}_reb{reb}"})
    sc = D.rank_window_score(score, elig, lo, hi)
    out = run_book(f.spine.panel, sc, elig, spec, f.spine.rf, era)
    return out["monthly"]["net"].dropna()


def curve(f, base_d, score, elig, era, width, reb, tag) -> dict:
    """One rank curve: bucket returns on a COMMON month set."""
    edges = [(lo, lo + width - 1) for lo in range(1, TOP + 1, width)]
    series = {}
    for lo, hi in edges:
        try:
            series[(lo, hi)] = bucket_returns(f, base_d, score, elig, era,
                                              lo, hi, reb, tag)
        except RuntimeError as exc:
            print(f"    bucket {lo}-{hi} unrunnable: {str(exc)[:70]}", flush=True)
    if not series:
        return {"error": "no runnable buckets"}
    common = None
    for s in series.values():
        common = s.index if common is None else common.intersection(s.index)
    return {"edges": [list(e) for e in series], "common_months": len(common),
            "first": str(common.min())[:10], "last": str(common.max())[:10],
            "series": {f"{lo}-{hi}": s.reindex(common)
                       for (lo, hi), s in series.items()}}


def alphas(cv, f, months=None) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Annualized FF5+UMD alpha and its SE per bucket, on a fixed month set."""
    a, se, labs = [], [], []
    for lab, s in cv["series"].items():
        x = s if months is None else s.reindex(months).dropna()
        if len(x) < 36:
            continue
        r = D.alpha_report(x, f.factors, D.FF6, rf=f.spine.rf)
        if r.get("t_alpha") in (None, 0) and r.get("ann_alpha") is None:
            continue
        t = r["t_alpha"]
        a.append(r["ann_alpha"])
        se.append(abs(r["ann_alpha"] / t) if t else np.nan)
        labs.append(lab)
    return np.array(a, float), np.array(se, float), labs


# ── the four registered shapes ──────────────────────────────────────────────
def _wls(X, y, w):
    W = np.diag(w)
    beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
    resid = y - X @ beta
    chi2 = float(resid @ W @ resid)
    cov = np.linalg.inv(X.T @ W @ X)
    return beta, chi2, np.sqrt(np.diag(cov))


def shape_power(se: np.ndarray, power: float = 0.80) -> dict:
    """What size of shape COULD this curve see? — the retraction's lesson.

    NIGHT-4 retracted a headline for writing "unmeasured" as "zero". A flat
    curve is only informative next to the swing it would have taken to look
    non-flat, so that number is computed here and printed whatever the verdict.

    For a linear ramp of total top-to-bottom swing S, the Cochran Q statistic
    is non-central chi-square with non-centrality lambda(S); the detectable S
    is the one whose lambda reaches `power` against the 5% critical value.
    """
    n = len(se)
    w = 1.0 / se ** 2
    x = np.arange(n, dtype=float)
    dev = (x - x.mean()) / (n - 1)              # unit-swing deviations
    lam_per_unit = float(np.sum(w * dev ** 2))  # lambda = S^2 * this
    crit = stats.chi2.ppf(0.95, n - 1)

    lo, hi = 0.0, 5.0
    for _ in range(60):                         # bisect on S
        mid = (lo + hi) / 2
        p = 1 - stats.ncx2.cdf(crit, n - 1, (mid ** 2) * lam_per_unit)
        if p < power:
            lo = mid
        else:
            hi = mid
    swing = (lo + hi) / 2

    # slope MDE straight from the WLS standard error
    X = np.column_stack([np.ones(n), x - x.mean()])
    _, _, sd = _wls(X, np.zeros(n), w)
    return {
        "detectable_total_swing_annualized": round(float(swing), 4),
        "detectable_swing_reading": (
            f"a monotone ramp smaller than {swing:.1%}/yr from best to worst "
            f"bucket would NOT reject flatness at 80% power. A flat result "
            f"therefore means 'no shape larger than {swing:.1%}/yr', never "
            f"'no shape'."),
        "mde_slope_per_bucket": round(float(2 * sd[1]), 4),
        "mde_median_bucket_alpha": round(float(2 * np.median(se)), 4),
    }


def fit_shapes(a: np.ndarray, se: np.ndarray) -> dict:
    """AIC over S1-S4 with KNOWN measurement variances (chi2 + 2k)."""
    n = len(a)
    w = 1.0 / se ** 2
    x = np.arange(1, n + 1, dtype=float)
    xc = x - x.mean()
    res = {}

    # S4 flat
    X = np.ones((n, 1))
    b, chi2, sd = _wls(X, a, w)
    res["S4_flat"] = {"k": 1, "chi2": round(chi2, 2), "aic": round(chi2 + 2, 2),
                      "level": round(float(b[0]), 4)}

    # S1 linear
    X = np.column_stack([np.ones(n), xc])
    b, chi2, sd = _wls(X, a, w)
    t_beta = float(b[1] / sd[1])
    res["S1_linear"] = {"k": 2, "chi2": round(chi2, 2), "aic": round(chi2 + 4, 2),
                        "slope_per_bucket": round(float(b[1]), 4),
                        "t_slope": round(t_beta, 2),
                        "monotone_decreasing": bool(b[1] < 0
                                                    and abs(t_beta)
                                                    > FAMILY_BONFERRONI_T)}

    # S2 quadratic
    X = np.column_stack([np.ones(n), xc, xc ** 2])
    b, chi2, sd = _wls(X, a, w)
    t_g = float(b[2] / sd[2])
    vertex = float(-b[1] / (2 * b[2])) + x.mean() if b[2] != 0 else np.nan
    interior = bool(1 < vertex < n) if np.isfinite(vertex) else False
    res["S2_quadratic"] = {
        "k": 3, "chi2": round(chi2, 2), "aic": round(chi2 + 6, 2),
        "gamma": round(float(b[2]), 5), "t_gamma": round(t_g, 2),
        "vertex_bucket": round(vertex, 2) if np.isfinite(vertex) else None,
        "vertex_interior": interior,
        "inverted_u": bool(b[2] < 0 and abs(t_g) > FAMILY_BONFERRONI_T
                           and interior)}

    # S3 flat-then-linear, best breakpoint
    best = None
    for bp in range(2, n):
        z = np.maximum(x - bp, 0.0)
        X = np.column_stack([np.ones(n), z])
        bb, c2, sd3 = _wls(X, a, w)
        if best is None or c2 < best[1]:
            best = (bp, c2, bb, sd3)
    bp, c2, bb, sd3 = best
    res["S3_plateau_then_decay"] = {
        "k": 3, "chi2": round(c2, 2), "aic": round(c2 + 6, 2),
        "breakpoint_bucket": bp, "post_slope": round(float(bb[1]), 4),
        "t_post_slope": round(float(bb[1] / sd3[1]), 2)}

    # Cochran Q for S4
    abar = float(np.sum(w * a) / np.sum(w))
    Q = float(np.sum(w * (a - abar) ** 2))
    res["cochran_q"] = {"Q": round(Q, 2), "df": n - 1,
                        "p": round(float(1 - stats.chi2.cdf(Q, n - 1)), 4),
                        "rejects_flatness": bool(
                            1 - stats.chi2.cdf(Q, n - 1) < 0.05)}
    rho, prho = stats.spearmanr(np.arange(n), a)
    res["spearman_rank_vs_alpha"] = {"rho": round(float(rho), 3),
                                     "p": round(float(prho), 4)}
    res["mde_per_bucket_annualized"] = round(float(2 * np.median(se)), 4)
    res["power"] = shape_power(se)

    order = sorted(["S4_flat", "S1_linear", "S2_quadratic",
                    "S3_plateau_then_decay"], key=lambda k: res[k]["aic"])
    gap = res[order[1]]["aic"] - res[order[0]]["aic"]
    res["aic_winner"] = order[0]
    res["aic_runner_up"] = order[1]
    res["aic_gap"] = round(float(gap), 2)
    res["aic_reading"] = ("gap < 2 => UNRESOLVED between the top two shapes"
                          if gap < 2 else f"{order[0]} wins by {gap:.2f} AIC")
    return res


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    banked = json.loads(BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()

    f = Factory()
    elig_raw = f.eligible(d["segment"])
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())

    # Structural common month set: every bucket must face the SAME months, so
    # months whose eligible universe is shallower than the deepest bucket are
    # switched off for ALL buckets rather than for some. On this panel the
    # restriction is free — 482 of 483 months already carry 300+ eligible names,
    # the same window every other PF number uses — because the never-indexed
    # $200k floor has already deleted everything before 1982-11.
    depth = elig_raw.sum(axis=1)
    deep_enough = depth >= TOP
    elig = elig_raw.copy()
    elig.loc[~deep_enough] = False
    print(f"[universe] {int(deep_enough.sum())} of {len(depth)} months carry "
          f"{TOP}+ eligible names; window "
          f"{depth[deep_enough].index.min().date()} .. "
          f"{depth[deep_enough].index.max().date()}", flush=True)

    score, _ = composite_score(f.lib, d["signals"], elig)

    res = {"trial": "TRIAL-PF5-RANK-SHAPE-1",
           "prereg": "TRIALS/PREREG_PF5_RANK_SHAPE.md",
           "prereg_commit": "ec06dc6",
           "design_decisions_recorded_before_reading_output": [
               "bucket alphas computed on the INTERSECTION of months available "
               "to every bucket, because the never-indexed $200k floor makes "
               "deep windows unrunnable in the early panel",
               "both clocks (monthly and annual) run; a shape counts only if "
               "it survives BOTH — a tightening of the registered rule"],
           "curves": {}}

    # ── primary: 10-name buckets, both clocks ──────────────────────────────
    for reb, tag in ((1, "monthly"), (12, "annual")):
        print(f"[primary {tag}] 10-name buckets", flush=True)
        cv = curve(f, d, score, elig, era, 10, reb, f"comp{reb}")
        a, se, labs = alphas(cv, f)
        blk = {"width": 10, "clock": tag, "buckets": labs,
               "common_months": cv["common_months"],
               "window": [cv["first"], cv["last"]],
               "alpha_by_bucket": [round(float(v), 4) for v in a],
               "se_by_bucket": [round(float(v), 4) for v in se],
               "shapes": fit_shapes(a, se)}

        # A2 era split on the same buckets
        idx = next(iter(cv["series"].values())).index
        for half, m in (("pre_2001", idx[idx < SPLIT]),
                        ("post_2001", idx[idx >= SPLIT])):
            aa, ss, ll = alphas(cv, f, months=m)
            blk[f"era_{half}"] = {"months": int(len(m)), "buckets": ll,
                                  "alpha_by_bucket": [round(float(v), 4)
                                                      for v in aa],
                                  "shapes": fit_shapes(aa, ss)} if len(aa) > 4 \
                else {"months": int(len(m)), "error": "too few buckets"}

        # A1 — the NIGHT-4 observation, as ONE pre-declared contrast
        s = cv["series"]
        if "1-10" in s and "11-20" in s:
            dd = (s["11-20"] - s["1-10"]).dropna()
            blk["A1_ranks_11_20_minus_1_10"] = {
                "ann_diff": round(float(D.alpha_report(dd, f.factors,
                                                       D.FF6)["ann_alpha"]), 4),
                "t": D.alpha_report(dd, f.factors, D.FF6)["t_alpha"],
                "caveat": ("not independent of the observation that motivated "
                           "it; cannot confirm itself")}
        res["curves"][f"primary_10name_{tag}"] = blk
        print(f"    Q p={blk['shapes']['cochran_q']['p']}  "
              f"AIC winner {blk['shapes']['aic_winner']} "
              f"gap {blk['shapes']['aic_gap']}", flush=True)

    # ── secondary: 5-name buckets, monthly only (cannot overturn primary) ──
    print("[secondary] 5-name buckets, monthly", flush=True)
    cv5 = curve(f, d, score, elig, era, 5, 1, "comp5")
    a5, se5, l5 = alphas(cv5, f)
    res["curves"]["secondary_5name_monthly"] = {
        "width": 5, "clock": "monthly", "buckets": l5,
        "common_months": cv5["common_months"],
        "alpha_by_bucket": [round(float(v), 4) for v in a5],
        "se_by_bucket": [round(float(v), 4) for v in se5],
        "shapes": fit_shapes(a5, se5),
        "status": "SECONDARY — registered as unable to overturn the primary"}

    # ── A3 cross-signal replication ────────────────────────────────────────
    res["A3_constituent_signals"] = {}
    for sig, _w in d["signals"]:
        print(f"[A3] {sig}", flush=True)
        sc1, _ = composite_score(f.lib, ((sig, 1.0),), elig)
        c = curve(f, d, sc1, elig, era, 10, 1, f"sig{sig.split(':')[-1]}")
        if "error" in c:
            res["A3_constituent_signals"][sig] = c
            continue
        aa, ss, ll = alphas(c, f)
        sh = fit_shapes(aa, ss)
        res["A3_constituent_signals"][sig] = {
            "buckets": ll, "common_months": c["common_months"],
            "alpha_by_bucket": [round(float(v), 4) for v in aa],
            "shapes": sh}
        print(f"    Q p={sh['cochran_q']['p']}  winner {sh['aic_winner']}",
              flush=True)

    # ── the frozen decision rule ───────────────────────────────────────────
    pm = res["curves"]["primary_10name_monthly"]["shapes"]
    pa = res["curves"]["primary_10name_annual"]["shapes"]
    eras = [res["curves"]["primary_10name_monthly"].get(f"era_{h}", {})
            for h in ("pre_2001", "post_2001")]
    era_winners = [e.get("shapes", {}).get("aic_winner") for e in eras]
    const_winners = [v.get("shapes", {}).get("aic_winner")
                     for v in res["A3_constituent_signals"].values()]

    q_rej = pm["cochran_q"]["rejects_flatness"]
    gap_ok = pm["aic_gap"] >= 2
    clocks_agree = pm["aic_winner"] == pa["aic_winner"]
    eras_agree = len(set(era_winners)) == 1 and era_winners[0] == pm["aic_winner"]
    const_ok = pm["aic_winner"] in const_winners

    if q_rej and gap_ok and clocks_agree and eras_agree and const_ok:
        verdict, why = "SHAPE ESTABLISHED", (
            f"{pm['aic_winner']} survives every registered requirement")
    elif not q_rej:
        verdict, why = "NO MEASURABLE SHAPE", (
            f"Cochran Q p={pm['cochran_q']['p']} does not reject flatness. "
            f"The curve could not have seen a monotone ramp smaller than "
            f"{pm['power']['detectable_total_swing_annualized']:.1%}/yr from "
            f"best to worst bucket at 80% power (per-bucket MDE "
            f"{pm['mde_per_bucket_annualized']:.2%}/yr). Per the prereg and "
            "the NIGHT-4 retraction this reads UNMEASURED, NOT ZERO, and the "
            "re-ranking campaign is not built on this data.")
    else:
        verdict, why = "UNRESOLVED", (
            f"Q rejects but the shape does not hold up: aic_gap>=2 {gap_ok}, "
            f"clocks agree {clocks_agree}, eras agree {eras_agree} "
            f"({era_winners}), constituent replication {const_ok} "
            f"({const_winners})")

    n_books = sum(len(c.get("buckets", [])) for c in res["curves"].values()) \
        + sum(len(v.get("buckets", []))
              for v in res["A3_constituent_signals"].values())
    res["VERDICT"] = {"verdict": verdict, "reading": why,
                      "requirements": {
                          "cochran_q_rejects": q_rej,
                          "aic_gap_ge_2": gap_ok,
                          "both_clocks_agree": clocks_agree,
                          "era_halves_agree": eras_agree,
                          "constituent_replication": const_ok}}
    res["multiple_testing"] = L.testing_block(None, None)
    res["decision_branches_this_family"] = n_books
    res["books_fitted"] = n_books
    res["runtime_secs"] = round(time.time() - t0, 1)

    (OUT / "T3_RANK_SHAPE.json").write_text(json.dumps(res, indent=2,
                                                       default=str),
                                            encoding="utf-8")
    print(json.dumps(res["VERDICT"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
