"""Pre-registered KILL diagnostics D1/D2 for INSTR-REGIME-ANALOG (macro_analog).

READ-ONLY: imports the frozen engine, mutates nothing (no ledger writes, no
engine edits, no git). Emits numbers to stdout + a JSON blob for the report.

D1  ANALOG AGE DISTRIBUTION
    kill line: >40% of accepted analogs within 12 months of the query
    => the engine measures local smoothness of its own state path
       (autocorrelation), not historical precedent.

D2  EFFECTIVE DIMENSION
    kill line: if the number of principal components explaining 90% of
    variance D_A >= 5, the 15-D retrieval is under-supported by ~24 years of
    library and the 2-3 PC version is the honest engine.

Usage (from module root):
  python scripts/diag_d1_d2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT  # noqa: E402
from aegis_brain.macro.macro_analog import (  # noqa: E402
    BELIEF_LEDGER, N_ANALOGS, NMS_TD, SELF_EXCLUSION_TD, build_descriptors,
    compute_belief, forward_outcomes, retrieve_analogs, robust_z)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXCL_CF = 504          # counterfactual +/-24 month self-exclusion (trading days)
AGE_BINS = {"3m": 91, "6m": 182, "12m": 365, "24m": 730}   # calendar days
OUT_JSON = MODULE_ROOT / "runs" / "diag_d1_d2_2026-07-29.json"


# --------------------------------------------------------------- retrieval
def retrieve_pos(X: np.ndarray, pos: int, excl: int, n: int = N_ANALOGS,
                 nms: int = NMS_TD) -> tuple[list[int], np.ndarray]:
    """Byte-faithful re-implementation of macro_analog.retrieve_analogs on
    positions of a complete-vector matrix X, parameterized by exclusion
    window and feature space. Returns (accepted positions, distances)."""
    cut = max(pos - excl + 1, 0)
    if cut < n:
        raise ValueError(f"only {cut} candidate days before self-exclusion")
    q = X[pos]
    dist = np.sqrt(((X[:cut] - q) ** 2).sum(axis=1))
    order = np.argsort(dist, kind="mergesort")    # stable == engine mergesort
    accepted: list[int] = []
    for p in order:
        if all(abs(int(p) - ap) >= nms for ap in accepted):
            accepted.append(int(p))
            if len(accepted) == n:
                break
    return accepted, dist[accepted]


def state_probs_from(fwd: pd.DataFrame) -> dict:
    """compute_belief's state_probs block, verbatim."""
    f6 = fwd["fwd_6m"].dropna()
    f12 = fwd["fwd_12m"].dropna()
    dd = fwd["fwd_12m_maxdd"].dropna()
    return {
        "fwd6m_positive": round(float((f6 > 0).mean()), 3) if len(f6) else None,
        "fwd12m_positive": round(float((f12 > 0).mean()), 3) if len(f12) else None,
        "crash12m_dd15": round(float((dd <= -0.15).mean()), 3) if len(dd) else None,
        "crash12m_dd20": round(float((dd <= -0.20).mean()), 3) if len(dd) else None,
    }


def jaccard(a: set, b: set) -> float:
    u = a | b
    return len(a & b) / len(u) if u else np.nan


def main() -> None:
    res: dict = {}

    # ------------------------------------------------- STEP 0 determinism
    z = robust_z(build_descriptors())
    zc = z.dropna()
    X = zc.to_numpy()
    dates = zc.index
    pos_of = {d: i for i, d in enumerate(dates)}
    print(f"complete descriptor vectors: {len(zc)} "
          f"({dates.min().date()} -> {dates.max().date()})  dims={X.shape[1]}")

    ledger = [json.loads(ln) for ln in
              BELIEF_LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    print(f"ledger rows: {len(ledger)}  unique query_dates: "
          f"{len({e['query_date'] for e in ledger})}")

    det = []
    for i in (0, len(ledger) // 2, len(ledger) - 2):
        e = ledger[i]
        qd = pd.Timestamp(e["query_date"])
        b, _ = compute_belief(z, qd, "diag", backfill=True)
        det.append({
            "i": i, "query_date": e["query_date"],
            "state_probs_match": b.state_probs == e["state_probs"],
            "episodes_match": b.evidence["episodes"] == e["evidence"]["episodes"],
            "confidence_match": abs(b.confidence - e["confidence"]) < 1e-9,
        })
    res["step0_determinism"] = det
    for d in det:
        print("STEP0", d)
    if not all(d["state_probs_match"] and d["episodes_match"] for d in det):
        print("STEP0 FAILED -> recomputation path invalid"); sys.exit(1)
    print("STEP0 PASS -> full recomputation path (exact)\n")

    # verify the fast re-implementation reproduces the engine exactly
    qdates = [pd.Timestamp(e["query_date"]) for e in ledger]
    mism = 0
    for qd in qdates:
        eng = retrieve_analogs(z, qd)
        acc, dst = retrieve_pos(X, pos_of[qd], SELF_EXCLUSION_TD)
        if list(dates[acc]) != list(eng.index) or not np.allclose(
                np.sort(dst), np.sort(eng["distance"].to_numpy())):
            mism += 1
    res["reimpl_mismatches"] = mism
    print(f"fast-retrieval parity vs engine over {len(qdates)} query dates: "
          f"{mism} mismatches\n")
    if mism:
        sys.exit(1)

    # ---------------------------------- precomputed forward outcomes table
    FWD = forward_outcomes(dates)          # every complete-vector day, once
    # spot-check against a fresh engine call
    chk_idx = dates[[500, 3000, 5000]]
    assert np.allclose(FWD.loc[chk_idx, "fwd_6m"].astype(float).to_numpy(),
                       forward_outcomes(chk_idx)["fwd_6m"].astype(float).to_numpy(),
                       equal_nan=True)

    # ============================================================== D1
    print("=" * 70, "\nD1 ANALOG AGE DISTRIBUTION\n", "=" * 70, sep="")
    rows63, rows504 = [], []
    ages_all: list[float] = []
    ages_all_504: list[float] = []
    per_state = []
    for qd in qdates:
        p = pos_of[qd]
        acc, dst = retrieve_pos(X, p, SELF_EXCLUSION_TD)
        ad = dates[acc]
        age = np.array([(qd - a).days for a in ad], dtype=float)
        ages_all.extend(age.tolist())
        rec = {"query_date": str(qd.date()), "n_analogs": len(acc),
               "median_age_d": float(np.median(age)),
               "share_le_12m": float((age <= AGE_BINS["12m"]).mean()),
               "nearest_dist": float(dst.min()), "mean_dist": float(dst.mean())}
        rows63.append(rec)
        try:
            acc2, dst2 = retrieve_pos(X, p, EXCL_CF)
            ad2 = dates[acc2]
            age2 = np.array([(qd - a).days for a in ad2], dtype=float)
            ages_all_504.extend(age2.tolist())
            rows504.append({"query_date": str(qd.date()), "n_analogs": len(acc2),
                            "median_age_d": float(np.median(age2)),
                            "share_le_12m": float((age2 <= AGE_BINS["12m"]).mean()),
                            "nearest_dist": float(dst2.min()),
                            "mean_dist": float(dst2.mean())})
            per_state.append({"query_date": str(qd.date()),
                              "jaccard": jaccard(set(acc), set(acc2))})
        except ValueError:
            pass

    def shares(ages: list[float]) -> dict:
        a = np.array(ages)
        out = {k: round(float((a <= v).mean()), 4) for k, v in AGE_BINS.items()}
        out["median_age_years"] = round(float(np.median(a)) / 365.25, 3)
        out["mean_age_years"] = round(float(a.mean()) / 365.25, 3)
        out["n_analog_slots"] = int(len(a))
        return out

    d1 = {
        "pooled_63td": shares(ages_all),
        "pooled_504td": shares(ages_all_504),
        "n_states_63td": len(rows63),
        "n_states_504td": len(rows504),
        "median_of_state_medians_years_63td":
            round(float(np.median([r["median_age_d"] for r in rows63])) / 365.25, 3),
        "median_of_state_medians_years_504td":
            round(float(np.median([r["median_age_d"] for r in rows504])) / 365.25, 3),
        "share_states_majority_within_12m_63td":
            round(float(np.mean([r["share_le_12m"] > 0.5 for r in rows63])), 4),
        "share_states_majority_within_12m_504td":
            round(float(np.mean([r["share_le_12m"] > 0.5 for r in rows504])), 4),
        "nearest_dist_63td_mean": round(float(np.mean([r["nearest_dist"] for r in rows63])), 4),
        "nearest_dist_63td_median": round(float(np.median([r["nearest_dist"] for r in rows63])), 4),
        "nearest_dist_504td_mean": round(float(np.mean([r["nearest_dist"] for r in rows504])), 4),
        "nearest_dist_504td_median": round(float(np.median([r["nearest_dist"] for r in rows504])), 4),
        "mean_dist_63td": round(float(np.mean([r["mean_dist"] for r in rows63])), 4),
        "mean_dist_504td": round(float(np.mean([r["mean_dist"] for r in rows504])), 4),
        "mean_jaccard_63_vs_504": round(float(np.mean([r["jaccard"] for r in per_state])), 4),
        "median_jaccard_63_vs_504": round(float(np.median([r["jaccard"] for r in per_state])), 4),
        "n_analogs_lt50_states": int(sum(r["n_analogs"] < N_ANALOGS for r in rows63)),
    }
    # matched-subset nearest distance (same query dates in both arms)
    common = {r["query_date"] for r in rows504}
    n63m = [r["nearest_dist"] for r in rows63 if r["query_date"] in common]
    d1["nearest_dist_63td_mean_matched"] = round(float(np.mean(n63m)), 4)
    d1["nearest_dist_63td_median_matched"] = round(float(np.median(n63m)), 4)
    d1["nearest_ratio_mean_matched"] = round(
        d1["nearest_dist_504td_mean"] / d1["nearest_dist_63td_mean_matched"], 3)
    d1["nearest_ratio_median_matched"] = round(
        d1["nearest_dist_504td_median"] / d1["nearest_dist_63td_median_matched"], 3)
    d1["kill_fired"] = d1["pooled_63td"]["12m"] > 0.40
    res["D1"] = d1
    res["D1_per_state_63td"] = rows63
    for k, v in d1.items():
        print(f"  {k}: {v}")
    print(f"\n  D1 VERDICT: kill line (>40% within 12m) "
          f"{'FIRED' if d1['kill_fired'] else 'DID NOT FIRE'} "
          f"(actual {d1['pooled_63td']['12m']:.1%})\n")

    # ============================================================== D2
    print("=" * 70, "\nD2 EFFECTIVE DIMENSION\n", "=" * 70, sep="")
    Xc = X - X.mean(axis=0)
    cov = np.cov(Xc, rowvar=False)
    evals, evecs = np.linalg.eigh(cov)
    order = np.argsort(evals)[::-1]
    evals, evecs = evals[order], evecs[:, order]
    evr = evals / evals.sum()
    cum = np.cumsum(evr)
    d_a = {f"D_A_{int(t*100)}": int(np.searchsorted(cum, t) + 1)
           for t in (0.80, 0.90, 0.95)}
    d2 = {"eigenvalues": [round(float(v), 4) for v in evals],
          "explained_variance_ratio": [round(float(v), 4) for v in evr],
          "cumulative": [round(float(v), 4) for v in cum], **d_a}
    d2["kill_fired"] = d2["D_A_90"] >= 5
    scores = Xc @ evecs                                   # PC scores, all 15

    base_sets, base_probs = {}, {}
    for qd in qdates:
        acc, _ = retrieve_pos(X, pos_of[qd], SELF_EXCLUSION_TD)
        base_sets[qd] = set(acc)
        base_probs[qd] = state_probs_from(FWD.loc[dates[acc]])

    keys = ["fwd6m_positive", "fwd12m_positive", "crash12m_dd15", "crash12m_dd20"]
    for k in range(2, 4):
        S = np.ascontiguousarray(scores[:, :k])
        jac, diffs = [], {kk: [] for kk in keys}
        pairs = {kk: ([], []) for kk in keys}
        for qd in qdates:
            acc, _ = retrieve_pos(S, pos_of[qd], SELF_EXCLUSION_TD)
            jac.append(jaccard(set(acc), base_sets[qd]))
            pp = state_probs_from(FWD.loc[dates[acc]])
            for kk in keys:
                a, b = base_probs[qd][kk], pp[kk]
                if a is not None and b is not None:
                    diffs[kk].append(abs(a - b))
                    pairs[kk][0].append(a); pairs[kk][1].append(b)
        d2[f"pc{k}"] = {
            "mean_jaccard_vs_15d": round(float(np.mean(jac)), 4),
            "median_jaccard_vs_15d": round(float(np.median(jac)), 4),
            "share_states_zero_overlap": round(float(np.mean(np.array(jac) == 0)), 4),
            "mean_abs_diff": {kk: round(float(np.mean(diffs[kk])), 4) for kk in keys},
            "corr_across_states": {
                kk: round(float(np.corrcoef(pairs[kk][0], pairs[kk][1])[0, 1]), 4)
                for kk in keys},
            "mean_prob_15d": {kk: round(float(np.mean(pairs[kk][0])), 4) for kk in keys},
            "mean_prob_pc": {kk: round(float(np.mean(pairs[kk][1])), 4) for kk in keys},
        }
    res["D2"] = d2
    for k, v in d2.items():
        print(f"  {k}: {v}")
    print(f"\n  D2 VERDICT: D_A(90%) = {d2['D_A_90']}; kill line (D_A >= 5) "
          f"{'FIRED' if d2['kill_fired'] else 'DID NOT FIRE'}")

    # ====================================================== ADDENDUM (context)
    print("\n" + "=" * 70, "\nADDENDUM (not pre-registered; context for the verdicts)\n",
          "=" * 70, sep="")
    add: dict = {}

    # A1 short-analog states: NMS + a short early library cap acceptance < 50
    n_an = np.array([r["n_analogs"] for r in rows63])
    full = [r for r in rows63 if r["n_analogs"] == N_ANALOGS]
    short = [r for r in rows63 if r["n_analogs"] < N_ANALOGS]
    ages_full, ages_short = [], []
    for qd in qdates:
        acc, _ = retrieve_pos(X, pos_of[qd], SELF_EXCLUSION_TD)
        age = [(qd - a).days for a in dates[acc]]
        (ages_full if len(acc) == N_ANALOGS else ages_short).extend(age)
    add["n_analogs_min"] = int(n_an.min())
    add["n_analogs_p25_p50"] = [int(np.percentile(n_an, 25)), int(np.percentile(n_an, 50))]
    add["states_full50"] = len(full)
    add["states_short"] = len(short)
    add["short_states_date_range"] = [min(r["query_date"] for r in short),
                                      max(r["query_date"] for r in short)] if short else None
    add["pooled_share_le_12m_full50"] = round(float(
        (np.array(ages_full) <= AGE_BINS["12m"]).mean()), 4)
    add["pooled_share_le_12m_short"] = round(float(
        (np.array(ages_short) <= AGE_BINS["12m"]).mean()), 4) if ages_short else None
    ms = np.array([r["median_age_d"] for r in rows63]) / 365.25
    add["per_state_median_age_years_quantiles"] = {
        q: round(float(np.quantile(ms, q)), 3) for q in (0.05, 0.25, 0.5, 0.75, 0.95)}
    add["max_state_share_le_12m"] = round(float(max(r["share_le_12m"] for r in rows63)), 4)

    # A2 unconditional base rate: how much do the state_probs move at all?
    base = state_probs_from(FWD)
    add["unconditional_base_rate_all_library_days"] = base
    add["mean_abs_diff_15d_vs_base_rate"] = {
        kk: round(float(np.mean([abs(base_probs[qd][kk] - base[kk])
                                 for qd in qdates if base_probs[qd][kk] is not None])), 4)
        for kk in keys}
    add["sd_of_15d_state_probs"] = {
        kk: round(float(np.std([base_probs[qd][kk] for qd in qdates
                                if base_probs[qd][kk] is not None])), 4) for kk in keys}
    res["ADDENDUM"] = add
    for k, v in add.items():
        print(f"  {k}: {v}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"\n-> {OUT_JSON}")


if __name__ == "__main__":
    main()
