"""T0.1 — restate NIGHT-3's ordering claim with the interval it always had.

NIGHT-3 said "the edge is MEMBERSHIP, not ORDERING" and cancelled an LLM
re-ranking campaign on it. The evidence was +1.46 %/yr at t = 0.43 for the
engine's own top-20-minus-bottom-20 inside its own 40-name slate. A t of 0.43 is
not a demonstration that ordering is worthless; it is a demonstration that this
test could not see it. The house rule (EXECUTION_STANDARD 4.5) is that a null
reads "smaller than X", never "zero" — and the house broke its own rule on its
own headline.

This recomputes the interval from the monthly series rather than back-solving it
from a rounded t, prints the ORACLE bracket beside it, and tests the one
alternative NIGHT-3 never tested: that ordering is NON-MONOTONE inside the slate,
which a top-minus-bottom spread cannot see at all.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.WARNING)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.night3.slate import PROF_SIGNALS, build_slates
from aegis_brain.pf.panel63 import annualize, eligibility, load_spine
from aegis_brain.pf.signals import SignalLibrary, composite_score

OUT = MODULE_ROOT / "runs" / "PF4"


def nw(x, lags: int = 12):
    r = newey_west_tstat(pd.Series(x).dropna(), lags=lags)
    return None if r.get("t") is None else float(r["t"])


def main() -> int:
    spine = load_spine("2003-01-31", "2022-12-31")
    lib = SignalLibrary(spine.panel)
    lib.preload(["native:mom_12_1", "native:vol_12m_low", "osap:GP", "osap:BM",
                 "osap:OperProfRD", "osap:CBOperProf"])
    elig = eligibility(spine, "small")
    score, _ = composite_score(lib, PROF_SIGNALS, elig)
    slates = build_slates(spine, lib, score, elig, first="2005-01-31",
                          last="2021-12-31", slate_n=40)
    rows = []
    for s in slates:
        # candidates sorted by the ENGINE's own composite rank — the order the
        # slate renderer deliberately hides from the LLM
        cs = sorted(s.candidates, key=lambda c: c.engine_rank)
        r = [c.fwd_ret for c in cs]
        q = [float(np.mean(r[i:i + 10])) for i in range(0, 40, 10)]
        rows.append({"ts": s.realized_month, "bench": s.benchmark_fwd,
                     "top20": float(np.mean(r[:20])),
                     "bot20": float(np.mean(r[20:])),
                     "q1": q[0], "q2": q[1], "q3": q[2], "q4": q[3],
                     "oracle20": float(np.mean(sorted(r, reverse=True)[:20])),
                     "anti20": float(np.mean(sorted(r)[:20])),
                     "all40": float(np.mean(r))})
    df = pd.DataFrame(rows).set_index("ts")
    df.index = pd.to_datetime(df.index)
    n = len(df)
    d = df["top20"] - df["bot20"]

    # Interval on the ANNUALIZED ARITHMETIC mean of the monthly spread, with a
    # Newey-West(12) standard error — the same estimator every t-stat in the
    # campaign uses, so the interval is consistent with the number it qualifies.
    t_nw = nw(d)
    mean_ann = float(d.mean()) * 12
    se_ann = abs(mean_ann / t_nw) if t_nw else float("nan")
    geo = annualize(df["top20"]) - annualize(df["bot20"])

    quart = {f"q{i}": {
        "excess_cagr": round(annualize(df[f"q{i}"]) - annualize(df["bench"]), 4),
        "mean_monthly": round(float(df[f"q{i}"].mean()), 5),
        "t_vs_bench": round(nw(df[f"q{i}"] - df["bench"]), 2)}
        for i in range(1, 5)}
    mono = [quart[f"q{i}"]["mean_monthly"] for i in range(1, 5)]

    res = {
        "correction": "RETRACTION-NIGHT3-5.2",
        "supersedes": ("NIGHT3_VERDICT_2026-08-09.md 'membership not ordering' "
                       "and the same claim in EXTERNAL_REVIEW_DOSSIER 5.2"),
        "n_months": n,
        "withdrawn_claim": ("the edge is MEMBERSHIP, not ORDERING — selection is "
                            "answered"),
        "corrected_claim": None,
        "engine_ordering_inside_own_slate": {
            "top20_minus_bottom20_geometric_annual": round(geo, 4),
            "annualized_arithmetic_mean": round(mean_ann, 4),
            "t_newey_west_12": round(t_nw, 2) if t_nw else None,
            "se_annualized": round(se_ann, 4),
            "ci95_annualized": [round(mean_ann - 1.96 * se_ann, 4),
                                round(mean_ann + 1.96 * se_ann, 4)],
            "mde_at_t2_annualized": round(2 * se_ann, 4)},
        "oracle_bracket": {
            "note": ("gross of costs and unattainable by construction — this is "
                     "the WIDTH of the achievable band, not a return"),
            "perfect_foresight_top20_excess_cagr": round(
                annualize(df["oracle20"]) - annualize(df["bench"]), 4),
            "anti_oracle_bottom20_excess_cagr": round(
                annualize(df["anti20"]) - annualize(df["bench"]), 4),
            "equal_weight_all40_excess_cagr": round(
                annualize(df["all40"]) - annualize(df["bench"]), 4),
            "reading": ("ordering information EXISTS in this environment in "
                        "abundance. What is unmeasured is how much of it the "
                        "composite captures — not whether any is there.")},
        "non_monotone_test": {
            "why": ("a top-minus-bottom spread is blind to a structure where the "
                    "very top names are crowded and the middle is best; that "
                    "structure reads as a null while ordering still carries "
                    "exploitable information"),
            "quartiles_of_engine_rank_within_slate": quart,
            "monotone_decreasing": bool(all(mono[i] >= mono[i + 1]
                                            for i in range(3))),
            "best_quartile": max(quart, key=lambda k: quart[k]["mean_monthly"])},
        "conditioning_caveat": (
            "both of NIGHT-3's derivations — the within-slate spread and the "
            "10-to-150 concentration grid — are computed INSIDE a set already "
            "selected on the composite. Range restriction attenuates any "
            "within-set relationship mechanically. They are one restriction "
            "sampled at two depths, not two independent confirmations, and the "
            "verdict should not have called them independent."),
        "process_miss": {
            "what": ("a campaign decision (the stratified re-ranking follow-up) "
                     "was cancelled on a null read as zero"),
            "rule_broken": ("EXECUTION_STANDARD 4.5 — a null reads 'smaller than "
                            "X', never 'zero'"),
            "self_inflicted": ("runs/NIGHT3/POWER_CHECK.json already carried the "
                               "correct reading in its own interpretation field: "
                               "'a null M1 means the TEST cannot separate "
                               "deciders ... and the verdict must be UNRESOLVED, "
                               "not REJECT'. The house wrote that sentence and "
                               "then did not follow it."),
            "scored_as": "process miss, recorded against the house"},
    }
    lo, hi = res["engine_ordering_inside_own_slate"]["ci95_annualized"]
    res["corrected_claim"] = (
        f"Within-slate ordering by the profitability composite is UNMEASURED at "
        f"this sample size: point estimate {mean_ann:+.2%}/yr, 95% CI "
        f"[{lo:+.2%}, {hi:+.2%}], t = {t_nw:.2f} over {n} months. The honest "
        f"statement is 'smaller than {2 * se_ann:.1%}/yr', not 'zero'. Membership "
        f"is the larger and better-measured effect; it is not the only one.")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RETRACTION_NIGHT3_5_2.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    df.to_csv(OUT / "slate_rank_quartiles.csv")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
