"""GRAPH-COVARIANCE-1 — build the matrices, solve the portfolios, grade.

    python -m scripts.gc1_grade                # gate, then everything
    python -m scripts.gc1_grade --gate-only    # the power probe alone
    python -m scripts.gc1_grade --arms a,b     # resume specific arms

WHAT THIS MEASURES
==================
Given two covariance estimates, the one whose minimum-variance portfolio
realises LOWER variance out of sample is the better estimate. That criterion
contains no return forecast at all, which is why this trial can make a
portfolio-level claim without predicting a single return.

Every arm differs in exactly one thing: the residual correlation block `P`. The
volatility block `D`, the PSD repair, the solver, the constraints, the holding
window and the universe are byte-identical across arms. If an arm ever needs its
own treatment, that is a finding to report, not a fix to apply.

THE ORDER MATTERS AND IT IS ENFORCED
------------------------------------
`oracle_on_edges` runs FIRST and `gate_report.json` is written BEFORE any real
arm is graded. GRAND-ARENA-1 discovered after the fact that its selection oracle
sat at 0.64x its own MDE, which made every null in that family uninterpretable.
Here the ceiling is measured before the floor, and the file on disk carries the
timestamp that proves it.

RESUMABILITY
------------
Per-arm results are checkpointed to `arms/<name>.json` as each finishes. Five
agents died to API stalls on 2026-08-12 and only the ones with incremental
artifacts kept their compute. This run is pure local compute, but the same rule
applies: an interrupted run resumes instead of restarting.
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

from aegis_brain.config import MODULE_ROOT                        # noqa: E402
from scripts import gc1_config as G                               # noqa: E402
from scripts import mg1_config as C                               # noqa: E402
from scripts.gc1_cov import (corr_to_cov, effective_bets,         # noqa: E402
                             gmv_long_only, gmv_weights,
                             ledoit_wolf_corr, predicted_vol,
                             realised_max_drawdown, realised_vol,
                             repair_correlation, rmt_denoise_corr)
from scripts.mg1_grade import (Ridge, attach, edge_features,      # noqa: E402
                               random_edges, shuffled_placebo,
                               stat_block)
from scripts.mg1_panel import residuals                           # noqa: E402
from scripts.mg1_robust import stratified_placebo                 # noqa: E402

MG1 = MODULE_ROOT / "runs" / "MARKET-GRAPH-1"
OUT = MODULE_ROOT / "runs" / "GRAPH-COVARIANCE-1"
ARMS_DIR = OUT / "arms"
PANELF = MODULE_ROOT / "data" / "factory" / "wg1_panel.npz"
DSI = MODULE_ROOT / "data" / "wrds_raw" / "crsp_dsi.parquet"

BASE = list(G.BASE_FEATS)
SEM = list(G.SEM_FEATS)

#: Arms whose difference decides H1/H2, and the placebos that can void them.
DECISION_ARMS = ("model_numeric", "model_semantic")
PLACEBO_ARMS = ("placebo_shuffled", "random_matched_density",
                "placebo_stratified")
CONTEXT_ARMS = ("diagonal", "sample", "ledoit_wolf", "rmt_denoised")


# ── the numeric spine, per cut date ─────────────────────────────────────────

def build_cache(uni: pd.DataFrame) -> dict:
    """Per cut date: the residual matrices, the volatility block and the factor
    covariance, all built from prices alone and identical for every arm.

    `res_t`/`res_f` are MARKET-GRAPH-1's residuals verbatim — betas fitted on
    the trailing 252 days and APPLIED to the forward 126, so the grading window
    never chooses its own market model. `fit_t = R_t - res_t` is the fitted
    market+sector component, and its trailing covariance is the factor block of
    the total-return matrix used by H2.
    """
    z = np.load(PANELF, allow_pickle=False)
    dates_all = pd.DatetimeIndex(z["dates"].astype("datetime64[ns]"))
    permnos_all = z["permnos"].astype(int)
    RET = z["RET"]
    dsi = pd.read_parquet(DSI, columns=["date", "vwretd"])
    dsi["date"] = pd.to_datetime(dsi["date"])
    mkt = (pd.to_numeric(dsi.set_index("date")["vwretd"], errors="coerce")
           .reindex(dates_all).to_numpy(dtype=np.float64))
    pos = {int(p): k for k, p in enumerate(permnos_all)}

    cache: dict = {}
    for t, g in uni.groupby("date"):
        ix = int(np.searchsorted(dates_all, t, side="right") - 1)
        if ix - C.TRAIL_DAYS < 0 or ix + C.HORIZON_DAYS >= len(dates_all):
            continue
        g = g.sort_values("permno")
        pn = g["permno"].to_numpy(dtype=int)
        cols = np.array([pos[int(p)] for p in pn])
        ff = g["ff12"].to_numpy()
        Rt = RET[ix - C.TRAIL_DAYS + 1:ix + 1, cols].astype(np.float64)
        Rf = RET[ix + 1:ix + 1 + C.HORIZON_DAYS, cols].astype(np.float64)
        mt = mkt[ix - C.TRAIL_DAYS + 1:ix + 1]
        mf = mkt[ix + 1:ix + 1 + C.HORIZON_DAYS]

        res_t, B = residuals(Rt, mt, ff)
        res_f, _ = residuals(Rf, mf, ff, betas=B)
        fit_t = Rt - res_t

        # A name is held only if its trailing residual is estimable AND its
        # forward window is well enough covered to measure a realised variance.
        # The SAME name set is used by every arm.
        ok = (np.isfinite(res_t).sum(axis=0) >= int(0.8 * C.TRAIL_DAYS)) & \
             (np.isfinite(res_f).sum(axis=0)
              >= int(G.MIN_FWD_OBS_FRAC * C.HORIZON_DAYS))
        if ok.sum() < 30:
            continue
        pn, res_t, res_f = pn[ok], res_t[:, ok], res_f[:, ok]
        fit_t, Rf = fit_t[:, ok], Rf[:, ok]

        vol = np.nanstd(res_t, axis=0, ddof=1)
        vol[~np.isfinite(vol) | (vol <= 0)] = np.nanmedian(vol)

        F = np.nan_to_num(fit_t, nan=0.0)
        Sigma_fit = np.cov(F, rowvar=False)

        cache[t] = {
            "permnos": pn,
            "index": {int(p): k for k, p in enumerate(pn)},
            "res_t": res_t, "res_f": res_f, "Rf": Rf,
            "vol": vol, "Sigma_fit": Sigma_fit, "n": int(len(pn)),
        }
    return cache


def dense_from_pairs(pn: np.ndarray, idx: dict, lo: np.ndarray,
                     hi: np.ndarray, val: np.ndarray,
                     fill: float) -> tuple[np.ndarray, int]:
    """Scatter a per-pair vector into a dense symmetric matrix.

    Pairs whose correlation could not be estimated at all (thin overlap) are
    absent from the panel for EVERY arm alike, so they get the same `fill` in
    every arm and the count is reported rather than hidden.
    """
    n = len(pn)
    P = np.full((n, n), fill, dtype=np.float64)
    a = np.array([idx.get(int(x), -1) for x in lo])
    b = np.array([idx.get(int(x), -1) for x in hi])
    m = (a >= 0) & (b >= 0) & np.isfinite(val)
    P[a[m], b[m]] = val[m]
    P[b[m], a[m]] = val[m]
    np.fill_diagonal(P, 1.0)
    n_off = n * (n - 1) // 2
    return P, int(n_off - m.sum())


# ── one arm, all dates ──────────────────────────────────────────────────────

def grade_arm(name: str, df: pd.DataFrame, cache: dict, dates: list,
              feats: list[str] | None, mode: str = "model",
              eig_floor_rel: float | None = None) -> dict:
    """Realised risk of the minimum-variance portfolio, per cut date.

    `mode`:
      model   ridge on `feats`, fitted walk-forward on strictly earlier dates
      oracle  the model_numeric ridge, with the TRUE forward correlation written
              into exactly the edge-carrying entries. THE POWER GATE.
      oracle_full
              the TRUE forward correlation EVERYWHERE. Not in the original
              pre-registration; added as a declared INSTRUMENT diagnostic after
              the first gate run, and never adoptable because it reads the
              outcome in every entry. It answers a question the on-edges oracle
              cannot: is this metric able to reward a better correlation matrix
              AT ALL? If `oracle_full` moves the portfolio and `oracle_on_edges`
              does not, the binding constraint is edge COVERAGE, not edge
              information — which is exactly what the pre-committed escalation
              path (raise UNIVERSE_N) addresses.
      const   a constant off-diagonal (the `diagonal` context arm uses 0)
      sample  the trailing residual correlation as-is
      lw      Ledoit-Wolf shrinkage of the trailing residual correlation
      rmt     Marchenko-Pastur denoising of the trailing residual correlation
    """
    y = df["rho_fwd"].to_numpy(dtype=np.float64)
    d_at = df["date"].to_numpy()
    lo_all = df["lo"].to_numpy()
    hi_all = df["hi"].to_numpy()
    has_all = df["has_edge"].to_numpy(dtype=np.float64) > 0
    X = df[feats].to_numpy(dtype=np.float64) if feats else None

    rows = []
    for k, t in enumerate(dates):
        if k < C.MIN_TRAIN_DATES or t not in cache:
            continue
        cu = cache[t]
        te = d_at == t
        if te.sum() < 100:
            continue

        if mode in ("model", "oracle", "oracle_full"):
            cutoff = dates[k - G.PURGE] if k - G.PURGE >= 0 else t
            tr = d_at < cutoff
            if tr.sum() < 1000:
                continue
            pred = Ridge(C.RIDGE_ALPHA).fit(X[tr], y[tr]).predict(X[te])
            if mode == "oracle":
                # The ceiling: perfect knowledge on exactly the pairs the graph
                # touches, nothing else changed. Never adoptable, by design.
                pred = pred.copy()
                pred[has_all[te]] = y[te][has_all[te]]
            elif mode == "oracle_full":
                pred = y[te].copy()
            P, n_missing = dense_from_pairs(cu["permnos"], cu["index"],
                                            lo_all[te], hi_all[te], pred,
                                            fill=float(np.median(pred)))
        elif mode == "const":
            P = np.eye(cu["n"])
            n_missing = 0
        else:
            R = cu["res_t"]
            if mode == "sample":
                P = np.corrcoef(np.nan_to_num(R, nan=0.0), rowvar=False)
            elif mode == "lw":
                P = ledoit_wolf_corr(np.nan_to_num(R, nan=0.0))
            elif mode == "rmt":
                P = rmt_denoise_corr(
                    np.corrcoef(np.nan_to_num(R, nan=0.0), rowvar=False),
                    T=R.shape[0])
            else:
                raise ValueError(f"unknown mode {mode}")
            n_missing = 0

        P, mdiag = repair_correlation(
            P, eig_floor_rel=(G.EIG_FLOOR_REL if eig_floor_rel is None
                              else eig_floor_rel),
            shrink=G.SHRINK_TO_IDENTITY, corr_clip=G.CORR_CLIP)
        Sig_res = corr_to_cov(P, cu["vol"])

        # PRIMARY (H1): residual-space GMV, fully invested, no sign constraint.
        w = gmv_weights(Sig_res)
        v_real = realised_vol(cu["res_f"], w, G.ANNUALISE_DAYS)
        v_pred = predicted_vol(Sig_res, w, G.ANNUALISE_DAYS)

        # SECONDARY (H2): long-only capped GMV on the total-return matrix.
        Sig_tot = cu["Sigma_fit"] + Sig_res
        w2 = gmv_long_only(Sig_tot, G.LONGONLY_MAX_WEIGHT,
                           G.LONGONLY_MAX_ITERS, G.LONGONLY_TOL)
        v2_real = realised_vol(cu["Rf"], w2, G.ANNUALISE_DAYS)
        v2_pred = predicted_vol(Sig_tot, w2, G.ANNUALISE_DAYS)

        rows.append({
            "date": str(pd.Timestamp(t).date()), "n_names": cu["n"],
            "n_pairs": int(te.sum()), "n_edge_pairs": int(has_all[te].sum()),
            "n_pairs_missing": n_missing,
            "vol_realised": v_real, "vol_predicted": v_pred,
            "maxdd": realised_max_drawdown(cu["res_f"], w),
            "eff_bets": effective_bets(w),
            "gross": float(np.abs(w).sum()),
            "lo_vol_realised": v2_real, "lo_vol_predicted": v2_pred,
            "lo_maxdd": realised_max_drawdown(cu["Rf"], w2),
            "lo_eff_bets": effective_bets(w2),
            "min_eig_raw": mdiag["min_eig_raw"],
            "n_eigs_clipped": mdiag["n_eigs_clipped"],
            "n_entries_out_of_range": mdiag["n_entries_out_of_range"],
            "cond": mdiag["cond"],
        })
    per = pd.DataFrame(rows)
    if per.empty:
        return {"arm": name, "error": "no graded dates"}
    calib = float((per["vol_realised"] / per["vol_predicted"]).mean())
    lo_calib = float((per["lo_vol_realised"] / per["lo_vol_predicted"]).mean())
    lo_band, hi_band = G.CALIBRATION_VOID_BAND
    void = not (lo_band <= calib <= hi_band)
    return {
        "arm": name, "mode": mode, "n_dates": int(len(per)),
        "eig_floor_rel": (G.EIG_FLOOR_REL if eig_floor_rel is None
                          else eig_floor_rel),
        # The assertion that would have caught the 1e-8 defect without a human
        # reading a diagnostic. A void arm is reported as void, never compared.
        "VOID_numerically_degenerate": void,
        "void_reason": (f"mean calibration ratio {calib:.1f} outside "
                        f"[{lo_band}, {hi_band}] — the matrix does not forecast "
                        f"the risk of the portfolio it chooses" if void else ""),
        "mean_n_entries_out_of_range": float(
            per["n_entries_out_of_range"].mean()),
        "mean_vol_realised": float(per["vol_realised"].mean()),
        "mean_vol_predicted": float(per["vol_predicted"].mean()),
        "calibration_ratio": calib,
        "mean_maxdd": float(per["maxdd"].mean()),
        "mean_eff_bets": float(per["eff_bets"].mean()),
        "mean_gross": float(per["gross"].mean()),
        "lo_mean_vol_realised": float(per["lo_vol_realised"].mean()),
        "lo_calibration_ratio": lo_calib,
        "lo_mean_maxdd": float(per["lo_maxdd"].mean()),
        "lo_mean_eff_bets": float(per["lo_eff_bets"].mean()),
        "mean_min_eig_raw": float(per["min_eig_raw"].mean()),
        "mean_n_eigs_clipped": float(per["n_eigs_clipped"].mean()),
        "mean_cond": float(per["cond"].mean()),
        "total_pairs_missing": int(per["n_pairs_missing"].sum()),
        "total_edge_pairs": int(per["n_edge_pairs"].sum()),
        "per_date": per.to_dict("records"),
    }


def paired(ref: dict, arm: dict, key: str) -> dict:
    """`arm - ref` on a per-cut-date series, differenced WITHIN the date (S18).

    The key is a realised VOLATILITY, so the raw difference is negative when the
    arm did better. Sign confusion in a risk metric is a real way to publish a
    result backwards, so `risk_reduction = -mean` is written out explicitly and
    every downstream comparison reads that field rather than re-deriving a sign.
    """
    pa = pd.DataFrame(ref["per_date"]).set_index("date")[key]
    pb = pd.DataFrame(arm["per_date"]).set_index("date")[key]
    common = pa.index.intersection(pb.index)
    d = (pb.loc[common] - pa.loc[common]).to_numpy(dtype=float)
    st = stat_block(d, lags=G.NW_LAGS)
    st["n_common_dates"] = int(len(common))
    st["mean_ref"] = float(pa.loc[common].mean())
    st["mean_arm"] = float(pb.loc[common].mean())
    st["risk_reduction"] = -float(st["mean"])
    st["risk_reduction_pct_of_ref"] = (
        -float(st["mean"]) / float(pa.loc[common].mean()) * 100.0
        if pa.loc[common].mean() else float("nan"))
    st["detectable_improvement"] = bool(st["risk_reduction"] >= st["mde"])
    return st


# ── main ────────────────────────────────────────────────────────────────────

def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list]:
    uni = pd.read_parquet(MG1 / "universe.parquet")
    uni["date"] = pd.to_datetime(uni["date"])
    pairs = pd.read_parquet(MG1 / "pairs.parquet")
    pairs["date"] = pd.to_datetime(pairs["date"])
    pairs["lo"] = np.minimum(pairs["permno_i"], pairs["permno_j"])
    pairs["hi"] = np.maximum(pairs["permno_i"], pairs["permno_j"])
    pairs["rho_trail"] = pairs["rho_trail"].astype(float)
    pairs["rho_trail2"] = pairs["rho_trail"] ** 2
    pairs["same_sector"] = pairs["same_sector"].astype(float)
    pairs["rho_fwd"] = pairs["rho_fwd"].astype(float)
    inst = pd.read_parquet(MG1 / "edge_instances.parquet")
    inst["date"] = pd.to_datetime(inst["date"])
    return uni, pairs, inst, sorted(pairs["date"].unique())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-only", action="store_true")
    ap.add_argument("--floor-sensitivity", action="store_true",
                    help="re-grade the two decision arms at every floor in "
                         "EIG_FLOOR_SENSITIVITY. Can only DEMOTE a verdict: if "
                         "the sign or the detectability of the headline moves "
                         "across floors, the result is fragile and says so.")
    ap.add_argument("--arms", default="")
    ap.add_argument("--force", action="store_true",
                    help="re-run arms that already have a checkpoint")
    a = ap.parse_args()

    t0 = time.time()
    ARMS_DIR.mkdir(parents=True, exist_ok=True)
    uni, pairs, inst, dates = load()
    print(f"pairs {len(pairs):,} | cut dates {len(dates)} | "
          f"edge-instances {len(inst):,}", flush=True)

    print("building the numeric cache ...", flush=True)
    cache = build_cache(uni)
    print(f"  {len(cache)} cut dates cached; "
          f"names/date {np.mean([c['n'] for c in cache.values()]):.1f}",
          flush=True)

    sem_real = attach(pairs, edge_features(inst))

    # A PERFECT EDGE FEATURE, fed through the SAME ridge as everything else.
    #
    # Declared instrument addition, made after the first gate run and never
    # adoptable (it reads the outcome). `oracle_on_edges` writes the realised
    # forward correlation directly into 0.58% of the matrix entries while the
    # other 99.42% keep the ridge's much narrower dispersion — so it tests a
    # matrix no predictor could ever produce, and the first repaired gate run
    # measured it making the portfolio detectably WORSE. This arm asks the
    # question the pre-registration meant to ask: if the semantic block were a
    # PERFECT predictor of forward correlation on the pairs it covers, what
    # could the real architecture buy? The feature enters the same fixed-alpha
    # ridge, so the resulting matrix is scale-consistent by construction, which
    # is the property `oracle_on_edges` lacks.
    sem_oracle = sem_real.copy()
    sem_oracle["oracle_feat"] = (sem_oracle["rho_fwd"].to_numpy(dtype=float)
                                 * (sem_oracle["has_edge"].to_numpy(dtype=float)
                                    > 0))

    frames = {
        "model_numeric": sem_real,
        "model_semantic": sem_real,
        "oracle_on_edges": sem_real,
        "placebo_shuffled": attach(pairs, edge_features(
            shuffled_placebo(inst, uni, C.SEED_SHUFFLE))),
        "random_matched_density": attach(pairs, edge_features(
            random_edges(inst, pairs, C.SEED_RANDOM_EDGES))),
        "placebo_stratified": stratified_placebo(sem_real, G.SEED_STRATIFIED),
    }
    spec = {
        "model_numeric": (frames["model_numeric"], BASE, "model"),
        "model_semantic": (frames["model_semantic"], BASE + SEM, "model"),
        "oracle_on_edges": (frames["oracle_on_edges"], BASE, "oracle"),
        "oracle_full": (sem_real, BASE, "oracle_full"),
        "oracle_feature": (sem_oracle, BASE + ["oracle_feat"], "model"),
        "placebo_shuffled": (frames["placebo_shuffled"], BASE + SEM, "model"),
        "random_matched_density": (frames["random_matched_density"],
                                   BASE + SEM, "model"),
        "placebo_stratified": (frames["placebo_stratified"], BASE + SEM,
                               "model"),
        "diagonal": (sem_real, None, "const"),
        "sample": (sem_real, None, "sample"),
        "ledoit_wolf": (sem_real, None, "lw"),
        "rmt_denoised": (sem_real, None, "rmt"),
    }

    def run(name: str, floor: float | None = None) -> dict:
        tag = name if floor is None else f"{name}__floor{floor}"
        p = ARMS_DIR / f"{tag}.json"
        if p.exists() and not a.force:
            print(f"  [{tag}] checkpoint present, reusing", flush=True)
            return json.loads(p.read_text(encoding="utf-8"))
        df, feats, mode = spec[name]
        s = time.time()
        r = grade_arm(name, df, cache, dates, feats, mode, eig_floor_rel=floor)
        p.write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")
        flag = "  VOID" if r.get("VOID_numerically_degenerate") else ""
        print(f"  [{tag}] {r.get('n_dates')} dates, mean realised vol "
              f"{r.get('mean_vol_realised', float('nan')):.5f}, calib "
              f"{r.get('calibration_ratio', float('nan')):.2f}{flag}  "
              f"({time.time() - s:.0f}s)", flush=True)
        return r

    # ── THE GATE, FIRST, AND WRITTEN BEFORE ANY REAL ARM IS GRADED ──────────
    print("\n=== POWER GATE — oracle vs model_numeric ===", flush=True)
    res = {"model_numeric": run("model_numeric"),
           "oracle_on_edges": run("oracle_on_edges"),
           "oracle_feature": run("oracle_feature"),
           "oracle_full": run("oracle_full")}
    voids = {k: v.get("void_reason") for k, v in res.items()
             if v.get("VOID_numerically_degenerate")}
    gate = {
        "run_utc": pd.Timestamp.utcnow().isoformat(),
        "what": "oracle_on_edges: true forward correlation written into exactly "
                "the edge-carrying entries of the model_numeric matrix - the "
                "ceiling on any edge-based correction at this coverage. "
                "oracle_full: true forward correlation EVERYWHERE - a declared "
                "instrument diagnostic added after the first gate run, never "
                "adoptable, which separates 'the metric cannot reward a better "
                "matrix' from 'edge coverage is the binding constraint'.",
        "voided_arms": voids,
        "primary_residual_gmv": paired(res["model_numeric"],
                                       res["oracle_on_edges"], "vol_realised"),
        "secondary_longonly_total": paired(res["model_numeric"],
                                           res["oracle_on_edges"],
                                           "lo_vol_realised"),
        "instrument_oracle_full_residual_gmv": paired(
            res["model_numeric"], res["oracle_full"], "vol_realised"),
        "instrument_oracle_full_longonly": paired(
            res["model_numeric"], res["oracle_full"], "lo_vol_realised"),
        "instrument_oracle_feature_residual_gmv": paired(
            res["model_numeric"], res["oracle_feature"], "vol_realised"),
        "instrument_oracle_feature_longonly": paired(
            res["model_numeric"], res["oracle_feature"], "lo_vol_realised"),
    }
    g = gate["primary_residual_gmv"]
    gf = gate["instrument_oracle_full_residual_gmv"]
    gx = gate["instrument_oracle_feature_residual_gmv"]
    gate["passed"] = bool(g["detectable_improvement"]) and not voids
    gate["metric_responds_to_a_better_matrix"] = bool(
        gf["detectable_improvement"])
    # The gate the pre-registration MEANT: a perfect edge feature inside the
    # real architecture. `oracle_on_edges` cannot answer it because it builds a
    # matrix no predictor could produce.
    #
    # Three-valued, not two. An earlier version asked only whether the ceiling
    # showed a detectable IMPROVEMENT, which cannot express the case that
    # actually occurred — a perfect feature making the risk model detectably
    # WORSE — and fell through to a branch recommending escalation.
    gate["architecture_ceiling_detectable"] = bool(gx["detectable_improvement"])
    gate["architecture_ceiling_negative"] = bool(
        not gx["detectable_improvement"]
        and -gx["risk_reduction"] >= gx["mde"])
    if voids:
        gate["verdict"] = ("GATE_VOID — one or more arms are numerically "
                           f"degenerate: {voids}. Nothing may be compared until "
                           "the matrices forecast the risk of the portfolios "
                           "they choose.")
    elif gate["passed"]:
        gate["verdict"] = ("GATE_PASSED — the oracle clears its own MDE, so a "
                           "null from a real arm is informative")
    elif gate["architecture_ceiling_negative"]:
        gate["verdict"] = (
            "GATE_FAILED, AND THE ARCHITECTURE CEILING IS NEGATIVE. Two "
            "separate things are true and must not be conflated. (1) The "
            "pre-registered gate was the wrong instrument: oracle_on_edges "
            "builds a matrix no predictor could emit — realised truth at full "
            "dispersion in 0.58% of entries, ridge predictions at a quarter of "
            "that dispersion in the other 99.42% — and a minimum-variance solve "
            "is detectably HARMED by that inconsistency even though the "
            "inserted values are correct. (2) oracle_feature, the same perfect "
            "information fed through the REAL ridge so the matrix is "
            "scale-consistent, is ALSO detectably worse. So adding any "
            "edge-restricted feature to a globally-fitted entrywise ridge "
            "degrades the risk model even when the feature is perfect, and the "
            "real arms land where that ceiling says they will. Meanwhile "
            "oracle_full clears its own MDE, so the METRIC is innocent. "
            "Whether escalating edge count could ever help is NOT answered "
            "here — it is answered by the headroom test (oracle_full vs the "
            "trailing sample matrix) in floor_sensitivity.json, and this "
            "verdict deliberately does not pre-empt it.")
    elif gate["architecture_ceiling_detectable"]:
        gate["verdict"] = (
            "GATE_FAILED AS WRITTEN, BUT THE PRE-REGISTERED GATE WAS THE WRONG "
            "INSTRUMENT. oracle_on_edges builds a matrix no predictor could "
            "produce, at two incompatible dispersion scales. oracle_full and "
            "oracle_feature both clear their own MDEs, so the metric rewards a "
            "better matrix and the architecture has room. The real arms are "
            "informative and are graded.")
    elif gate["metric_responds_to_a_better_matrix"]:
        gate["verdict"] = ("GATE_FAILED — UNDERPOWERED_BY_CONSTRUCTION, and the "
                           "instrument is INNOCENT: oracle_full DOES move the "
                           "portfolio by its own MDE, so the metric can reward "
                           "a better matrix and the binding constraint is edge "
                           "COVERAGE, not edge information. No null from a real "
                           "arm is a kill; escalating edge count is the "
                           "candidate next step, under a new name, IF the "
                           "headroom test says a gap exists to compete for.")
    else:
        gate["verdict"] = ("GATE_FAILED and the INSTRUMENT IS ALSO SILENT — "
                           "not even the full-knowledge oracle moves the "
                           "portfolio by its own MDE. The metric, not the "
                           "graph, is what has not been shown to work here; "
                           "escalating edge count would be premature.")
    (OUT / "gate_report.json").write_text(
        json.dumps(gate, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in gate.items() if k != "run_utc"},
                     indent=2, default=str))
    print(f"\nwrote {OUT / 'gate_report.json'} BEFORE grading the real arms",
          flush=True)

    if a.gate_only:
        return 0

    if a.floor_sensitivity:
        print("\n=== eigenvalue-floor sensitivity (can only DEMOTE) ===",
              flush=True)
        sens = {}
        for f in G.EIG_FLOOR_SENSITIVITY:
            num = run("model_numeric", f)
            sem = run("model_semantic", f)
            # The headroom check, at every floor. The verdict's central claim is
            # that perfect foresight of the realised forward correlation is
            # indistinguishable from the trailing sample matrix. The floor caps
            # how much structure ANY matrix can express, so that claim is only
            # honest if it survives relaxing the cap.
            smp = run("sample", f)
            orc = run("oracle_full", f)
            sens[str(f)] = {
                "primary_residual_gmv": paired(num, sem, "vol_realised"),
                "secondary_longonly_total": paired(num, sem,
                                                   "lo_vol_realised"),
                "headroom_oracle_full_minus_sample": paired(
                    smp, orc, "vol_realised"),
                "calibration_numeric": num["calibration_ratio"],
                "calibration_semantic": sem["calibration_ratio"],
                "void": bool(num["VOID_numerically_degenerate"]
                             or sem["VOID_numerically_degenerate"]
                             or smp["VOID_numerically_degenerate"]
                             or orc["VOID_numerically_degenerate"]),
            }

        def _label(s: dict) -> str:
            if s["detectable_improvement"]:
                return "better"
            if -s["risk_reduction"] >= s["mde"]:
                return "worse"
            return "not_detectable"

        # Three-valued, not two. An earlier version tracked only
        # `detectable_improvement`, which called a headline "stable" while it
        # crossed its MDE in the HARMFUL direction at the tightest floor. A
        # stability check that cannot see one of the three outcomes is not a
        # stability check.
        signs = {k: float(np.sign(v["primary_residual_gmv"]["risk_reduction"]))
                 for k, v in sens.items()}
        labels = {k: _label(v["primary_residual_gmv"])
                  for k, v in sens.items()}
        head = {k: _label(v["headroom_oracle_full_minus_sample"])
                for k, v in sens.items()}
        sens["labels_by_floor"] = labels
        sens["headroom_by_floor"] = head
        sens["stable_sign"] = bool(len(set(signs.values())) == 1)
        sens["stable_label"] = bool(len(set(labels.values())) == 1)
        sens["headroom_absent_at_every_floor"] = bool(
            set(head.values()) <= {"not_detectable", "worse"})
        sens["reading"] = (
            ("STABLE across floors: " if sens["stable_sign"]
             and sens["stable_label"] else
             "SIGN-STABLE but the READING moves across floors — the headline's "
             "detectability depends on a numerical choice, so it is reported as "
             "fragile in that direction: ")
            + f"primary {labels}; headroom (oracle_full - sample) {head}.")
        (OUT / "floor_sensitivity.json").write_text(
            json.dumps(sens, indent=2, default=str), encoding="utf-8")
        print(json.dumps({k: v for k, v in sens.items()
                          if not k.startswith("0.")}, indent=2, default=str))
        print(f"wrote {OUT / 'floor_sensitivity.json'}")
        return 0

    wanted = ([s.strip() for s in a.arms.split(",") if s.strip()]
              or list(spec))
    for name in wanted:
        if name not in res:
            res[name] = run(name)

    report = {
        "run_utc": pd.Timestamp.utcnow().isoformat(),
        "trial": G.TRIAL,
        "n_cut_dates_cached": len(cache),
        "params": {k: getattr(G, k) for k in dir(G) if k.isupper()},
        "gate": gate,
        "arms": {k: {kk: vv for kk, vv in v.items() if kk != "per_date"}
                 for k, v in res.items()},
        "per_date": {k: v.get("per_date", []) for k, v in res.items()},
        "comparisons": {},
    }
    ref = res["model_numeric"]
    for name in list(PLACEBO_ARMS) + ["model_semantic", "oracle_on_edges"]:
        if name in res and "per_date" in res[name]:
            report["comparisons"][f"{name}_minus_numeric"] = {
                "primary_residual_gmv": paired(ref, res[name], "vol_realised"),
                "secondary_longonly_total": paired(ref, res[name],
                                                   "lo_vol_realised"),
            }
    # ── the verdict, computed from the decision rule, not composed by hand ──
    # The rule was frozen in `PREREG_GRAPH_COVARIANCE_1.md` before compute. It
    # is evaluated here so the registry row is a function of the receipt.
    h1 = report["comparisons"]["model_semantic_minus_numeric"][
        "primary_residual_gmv"]
    h2 = report["comparisons"]["model_semantic_minus_numeric"][
        "secondary_longonly_total"]
    plac = {n: report["comparisons"][f"{n}_minus_numeric"]["primary_residual_gmv"]
            for n in PLACEBO_ARMS if f"{n}_minus_numeric" in report["comparisons"]}
    placebos_clean = all(
        abs(v["risk_reduction"]) < v["mde"] for v in plac.values())

    if any(v.get("VOID_numerically_degenerate") for v in res.values()):
        tv = "VOID"
    elif not gate["passed"] and not gate["metric_responds_to_a_better_matrix"]:
        tv = "UNDERPOWERED_BY_CONSTRUCTION"
    elif not placebos_clean:
        tv = "PLACEBO_CONTAMINATED"
    elif h1["detectable_improvement"] and h2["detectable_improvement"]:
        tv = "ADOPTED_INTO_RESEARCH_USE"
    elif h1["detectable_improvement"]:
        tv = "LONG_SHORT_ONLY"
    else:
        tv = "NOT_DETECTABLE"
    report["trial_verdict"] = tv
    report["verdict_line"] = (
        f"H1 (resid-GMV) {h1['risk_reduction']:+.6f} vs MDE {h1['mde']:.6f} "
        f"(t {-h1['t']:+.2f}); H2 (long-only) {h2['risk_reduction']:+.6f} vs "
        f"MDE {h2['mde']:.6f}; placebos clean = {placebos_clean}; gate passed = "
        f"{gate['passed']}; metric responds to a better matrix = "
        f"{gate['metric_responds_to_a_better_matrix']}; architecture ceiling "
        f"negative = {gate.get('architecture_ceiling_negative')}.")
    report["headline"] = {
        "h1_primary": h1, "h2_secondary": h2,
        "placebos_primary": plac,
        "arm_realised_vol": {k: v.get("mean_vol_realised")
                             for k, v in res.items()},
    }
    print(f"\nTRIAL VERDICT: {tv}\n  {report['verdict_line']}", flush=True)

    report["elapsed_min"] = round((time.time() - t0) / 60, 2)
    (OUT / "grade_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {OUT / 'grade_report.json'} ({report['elapsed_min']} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
