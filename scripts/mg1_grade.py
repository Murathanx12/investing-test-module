"""MARKET-GRAPH-1 stage 5 — H1, H2, and the five controls.

WHAT IS BEING MEASURED
======================
H1: does adding semantic edges to a model that ALREADY CONTAINS the trailing
correlation improve out-of-sample prediction of forward pairwise co-movement?

The primary number is one thing:

    d_t = mean_pairs(e_baseline^2) - mean_pairs(e_semantic^2)   at each cut date
    statistic = mean_t d_t,  reported also as a share of Var(rho_fwd) = dR^2

and its SE. Overlapping pair-windows are dependent in two ways at once: within
a cut date every pair shares the same 126 trading days, and consecutive cut
dates are one quarter apart while the window is two quarters long, so each
window overlaps its neighbour by half. The first dependence is removed by
collapsing to ONE number per cut date before any SE is taken; the second is
handled by a Newey-West SE with two lags over those date-level numbers. n for
the SE is therefore the number of GRADED CUT DATES, not the number of pairs,
and both are printed (§19). MDE = 2.80 x max(HAC, IID) SE, per NIGHT-11's rule
that the ruler is the wider of the two.

H2 is tested as a DIFFERENCE with its own SE (§18): the rate at which
`semantic YES / numeric NO` pairs enter the top co-movement decile in
(t, t+h], minus the same rate among matched `semantic NO / numeric NO` pairs,
differenced WITHIN each cut date before the SE is taken. It is never two
separate significance claims.

THE FIVE CONTROLS, ALL OF THEM
------------------------------
1. shuffled-semantic placebo — the identical edge multiset, re-attached by a
   random permutation of NODE LABELS within each cut date. Relabelling nodes
   preserves the degree sequence exactly and carries each edge's confidence and
   type with it, which is what the prereg asks for and what a naive
   "shuffle the pair column" would destroy.
2. same-sector exclusion — the whole pipeline re-run on cross-sector pairs only.
3. random edges at matched density — the same COUNT of edges per cut date drawn
   uniformly from that date's pairs, confidences resampled from the real
   confidence distribution.
4. trailing-correlation-only baseline — the thing every delta is measured
   against; it is the reference in every arm, so it cannot fail to run.
5. reversed-direction control — the only one that can distinguish transmission
   from co-movement. Correlation is symmetric, so a directed claim needs a
   directed statistic: for each directed edge (supplier/customer) we take the
   LEAD-LAG cross-correlation of forward residuals at lags 1..5 in the upstream
   ->downstream orientation, minus the same quantity downstream->upstream. If
   the difference is indistinguishable from zero, the graph found co-movement,
   not causation, and H2 fails regardless of its headline number.

    python -m scripts.mg1_grade
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT                       # noqa: E402
from scripts import mg1_config as C                              # noqa: E402
from scripts.mg1_panel import residuals                          # noqa: E402

OUT = MODULE_ROOT / "runs" / "MARKET-GRAPH-1"
PANELF = MODULE_ROOT / "data" / "factory" / "wg1_panel.npz"
DSI = MODULE_ROOT / "data" / "wrds_raw" / "crsp_dsi.parquet"

BASE_FEATS = ["rho_trail", "rho_trail2", "same_sector"]
SEM_FEATS = ["has_edge", "log_n_edges", "max_conf"]

#: Lags for the reversed-direction control. One week of trading days: long
#: enough for an operational shock to propagate along a supply chain, short
#: enough that it is still the same news.
XLAGS = (1, 2, 3, 4, 5)


# ── inference helpers ───────────────────────────────────────────────────────

def newey_west_se(x: np.ndarray, lags: int = 2) -> float:
    """SE of the mean of a serially dependent series."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    e = x - x.mean()
    g0 = float(e @ e) / n
    var = g0
    for L in range(1, min(lags, n - 1) + 1):
        gl = float(e[L:] @ e[:-L]) / n
        var += 2.0 * (1.0 - L / (lags + 1.0)) * gl
    var = max(var, 1e-30)
    return float(np.sqrt(var / n))


def stat_block(per_date: np.ndarray, lags: int = 2) -> dict:
    """One date-level series -> mean, SEs, t, and the 80%-power MDE."""
    x = np.asarray(per_date, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return {"n_dates": n, "mean": float("nan"), "se": float("nan"),
                "t": float("nan"), "mde": float("nan"), "detectable": False}
    se_hac = newey_west_se(x, lags)
    se_iid = float(x.std(ddof=1) / np.sqrt(n))
    se = max(se_hac, se_iid)            # NIGHT-11: the ruler is the wider one
    mde = C.MDE_Z * se
    return {"n_dates": int(n), "mean": float(x.mean()), "se_hac": se_hac,
            "se_iid": se_iid, "se": se, "t": float(x.mean() / se) if se else
            float("nan"), "mde": float(mde),
            "detectable": bool(abs(x.mean()) >= mde)}


def ridge_fit(X: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    """Standardised ridge with an unpenalised intercept. Returns (mu, sd, w, b)
    packed by the caller; here just the solved weights on standardised X."""
    p = X.shape[1]
    A = X.T @ X + alpha * np.eye(p)
    return np.linalg.solve(A, X.T @ y)


class Ridge:
    def __init__(self, alpha: float) -> None:
        self.alpha = alpha

    def fit(self, X: np.ndarray, y: np.ndarray) -> "Ridge":
        self.mu = X.mean(axis=0)
        self.sd = X.std(axis=0)
        self.sd[self.sd < 1e-12] = 1.0
        Z = (X - self.mu) / self.sd
        self.ybar = float(y.mean())
        self.w = ridge_fit(Z, y - self.ybar, self.alpha)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return ((X - self.mu) / self.sd) @ self.w + self.ybar


# ── the H1 engine ───────────────────────────────────────────────────────────

def walk_forward(df: pd.DataFrame, base: list[str], sem: list[str],
                 dates: list) -> dict:
    """Per-date squared-error improvement from adding `sem` to `base`.

    Fitted on cut dates strictly before the graded one. Nothing is graded
    until MIN_TRAIN_DATES prior dates exist.
    """
    y = df["rho_fwd"].to_numpy(dtype=np.float64)
    Xb = df[base].to_numpy(dtype=np.float64)
    Xs = df[base + sem].to_numpy(dtype=np.float64)
    d_at = df["date"].to_numpy()
    has = df["has_edge"].to_numpy(dtype=np.float64) > 0

    rows = []
    for k, t in enumerate(dates):
        if k < C.MIN_TRAIN_DATES:
            continue
        tr = d_at < t
        te = d_at == t
        if tr.sum() < 1000 or te.sum() < 100:
            continue
        pb = Ridge(C.RIDGE_ALPHA).fit(Xb[tr], y[tr]).predict(Xb[te])
        ps = Ridge(C.RIDGE_ALPHA).fit(Xs[tr], y[tr]).predict(Xs[te])
        yt = y[te]
        e2b = (yt - pb) ** 2
        e2s = (yt - ps) ** 2
        m = has[te]
        rows.append({"date": t, "n_pairs": int(te.sum()),
                     "n_edge_pairs": int(m.sum()),
                     "mse_base": float(e2b.mean()),
                     "mse_sem": float(e2s.mean()),
                     "d": float(e2b.mean() - e2s.mean()),
                     "d_on_edge": (float(e2b[m].mean() - e2s[m].mean())
                                   if m.sum() >= 20 else np.nan),
                     "mse_base_on_edge": (float(e2b[m].mean())
                                          if m.sum() >= 20 else np.nan),
                     "var_y": float(yt.var())})
    per = pd.DataFrame(rows)
    if per.empty:
        return {"error": "no graded dates"}
    st = stat_block(per["d"].to_numpy())
    var_y = float(per["var_y"].mean())
    st.update(
        n_pairs_graded=int(per["n_pairs"].sum()),
        mse_base=float(per["mse_base"].mean()),
        mse_sem=float(per["mse_sem"].mean()),
        r2_base_oos=float(1.0 - per["mse_base"].mean() / var_y),
        r2_sem_oos=float(1.0 - per["mse_sem"].mean() / var_y),
        delta_r2=float(st["mean"] / var_y),
        delta_r2_mde=float(st["mde"] / var_y),
    )
    # SECONDARY, and labelled as such: the same delta measured only over the
    # test pairs that actually carry an edge. The model is still FITTED on
    # every pair, so the semantic block still has to earn its place against the
    # whole panel; this only stops a 0.5%-coverage feature from being graded
    # mostly on the 99.5% of pairs where it is identically zero. It is a
    # conditional statistic and it is never the decision number.
    st["on_edge_pairs"] = stat_block(per["d_on_edge"].to_numpy())
    mb = float(per["mse_base_on_edge"].mean())
    st["on_edge_pairs"]["n_edge_pairs_graded"] = int(per["n_edge_pairs"].sum())
    st["on_edge_pairs"]["mse_base"] = mb
    # Reported as a fraction of the BASELINE's own error on those same pairs.
    # Dividing by the all-pair variance instead would print a large number that
    # means nothing: edge-carrying pairs are not a random slice, their errors
    # are bigger, and the ratio would be an artefact of the denominator.
    st["on_edge_pairs"]["mse_reduction_pct"] = float(
        st["on_edge_pairs"]["mean"] / mb) if mb else float("nan")
    st["on_edge_pairs"]["mse_reduction_mde_pct"] = float(
        st["on_edge_pairs"]["mde"] / mb) if mb else float("nan")
    return st


# ── edge -> pair features ───────────────────────────────────────────────────

def edge_features(inst: pd.DataFrame) -> pd.DataFrame:
    """(date, lo, hi) -> the three semantic features, and nothing else.

    Three features, not thirty. The arms differ only by which block is present,
    and a fat semantic block would let "the model got bigger" masquerade as
    "the relationships carried information" — the same reason the estimator is
    a fixed-alpha ridge and not a booster.
    """
    g = inst.groupby(["date", "lo", "hi"], as_index=False).agg(
        n_edges=("confidence", "size"), max_conf=("confidence", "max"))
    g["has_edge"] = 1.0
    g["log_n_edges"] = np.log1p(g["n_edges"].astype(float))
    return g[["date", "lo", "hi", "has_edge", "log_n_edges", "max_conf"]]


def attach(pairs: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    out = pairs.merge(feats, on=["date", "lo", "hi"], how="left")
    for c in SEM_FEATS:
        out[c] = out[c].fillna(0.0)
    return out


def shuffled_placebo(inst: pd.DataFrame, uni: pd.DataFrame,
                     seed: int) -> pd.DataFrame:
    """Node-label permutation within each cut date.

    Degree sequence preserved exactly; every edge keeps its own confidence and
    type; only WHICH companies the relationships are between is destroyed. That
    is the arm that separates "these relationships carry information" from
    "adding another dense graph changed the model".
    """
    rng = np.random.default_rng(seed)
    out = []
    for t, g in inst.groupby("date"):
        members = uni.loc[uni["date"] == t, "permno"].to_numpy()
        perm = rng.permutation(members)
        mp = dict(zip(members, perm))
        a = np.array([mp.get(p, p) for p in g["subject_permno"]])
        b = np.array([mp.get(p, p) for p in g["counterparty_permno"]])
        h = g.copy()
        h["lo"], h["hi"] = np.minimum(a, b), np.maximum(a, b)
        out.append(h[h["lo"] != h["hi"]])
    return pd.concat(out, ignore_index=True)


def random_edges(inst: pd.DataFrame, pairs: pd.DataFrame,
                 seed: int) -> pd.DataFrame:
    """The same NUMBER of distinct edge-pairs per date, drawn uniformly."""
    rng = np.random.default_rng(seed)
    conf_pool = inst["confidence"].to_numpy()
    out = []
    for t, g in inst.groupby("date"):
        k = g.groupby(["lo", "hi"]).ngroups
        cand = pairs.loc[pairs["date"] == t, ["lo", "hi"]].to_numpy()
        if len(cand) == 0 or k == 0:
            continue
        pick = cand[rng.choice(len(cand), size=min(k, len(cand)),
                               replace=False)]
        out.append(pd.DataFrame({
            "date": t, "lo": pick[:, 0], "hi": pick[:, 1],
            "confidence": rng.choice(conf_pool, size=len(pick))}))
    return pd.concat(out, ignore_index=True)


# ── H2 ──────────────────────────────────────────────────────────────────────

def h2(df: pd.DataFrame, seed: int) -> dict:
    """`semantic YES / numeric NO` vs matched `semantic NO / numeric NO`.

    Matched EXACTLY on (cut date, same-sector indicator, rho_trail decile),
    up to C.H2_CONTROLS_PER_CASE controls per case, without replacement.
    Differenced within the date, then one SE over the date-level differences.
    """
    rng = np.random.default_rng(seed)
    per_rate, per_rho, n_case_tot, n_ctrl_tot = [], [], 0, 0
    for t, g in df.groupby("date"):
        thr = g["rho_fwd"].quantile(C.NUMERIC_YES_Q)
        g = g.assign(fwd_yes=(g["rho_fwd"] >= thr).astype(float))
        pool = g[~g["numeric_yes"].astype(bool)]
        case = pool[pool["has_edge"] > 0]
        ctrl_pool = pool[pool["has_edge"] <= 0]
        if len(case) < 5 or ctrl_pool.empty:
            continue
        want = (case.groupby(["same_sector", "trail_decile"]).size()
                * C.H2_CONTROLS_PER_CASE)
        picks = []
        for keyv, n_want in want.items():
            sub = ctrl_pool[(ctrl_pool["same_sector"] == keyv[0])
                            & (ctrl_pool["trail_decile"] == keyv[1])]
            if sub.empty:
                continue
            take = int(min(n_want, len(sub)))
            picks.append(sub.iloc[rng.choice(len(sub), size=take,
                                             replace=False)])
        if not picks:
            continue
        ctrl = pd.concat(picks)
        per_rate.append(case["fwd_yes"].mean() - ctrl["fwd_yes"].mean())
        per_rho.append(case["rho_fwd"].mean() - ctrl["rho_fwd"].mean())
        n_case_tot += len(case)
        n_ctrl_tot += len(ctrl)
    if len(per_rate) < 3:
        return {"error": f"only {len(per_rate)} usable dates"}
    a = stat_block(np.array(per_rate))
    b = stat_block(np.array(per_rho))
    return {"n_cases": n_case_tot, "n_controls": n_ctrl_tot,
            "rate_diff": a, "rho_diff": b}


# ── the reversed-direction control ──────────────────────────────────────────

def forward_residual_cache(uni: pd.DataFrame) -> dict:
    """Forward-window residual matrix and permno->column map per cut date."""
    z = np.load(PANELF, allow_pickle=False)
    dates = pd.DatetimeIndex(z["dates"].astype("datetime64[ns]"))
    permnos = z["permnos"].astype(int)
    RET = z["RET"]
    dsi = pd.read_parquet(DSI, columns=["date", "vwretd"])
    dsi["date"] = pd.to_datetime(dsi["date"])
    mkt = (pd.to_numeric(dsi.set_index("date")["vwretd"], errors="coerce")
           .reindex(dates).to_numpy(dtype=np.float64))
    pos = {int(p): k for k, p in enumerate(permnos)}
    cache = {}
    for t, g in uni.groupby("date"):
        ix = int(np.searchsorted(dates, t, side="right") - 1)
        if ix - C.TRAIL_DAYS < 0 or ix + C.HORIZON_DAYS >= len(dates):
            continue
        cols = np.array([pos[int(p)] for p in g["permno"]])
        ff = g["ff12"].to_numpy()
        Rt = RET[ix - C.TRAIL_DAYS + 1:ix + 1, cols].astype(np.float64)
        Rf = RET[ix + 1:ix + 1 + C.HORIZON_DAYS, cols].astype(np.float64)
        _, B = residuals(Rt, mkt[ix - C.TRAIL_DAYS + 1:ix + 1], ff)
        res_f, _ = residuals(Rf, mkt[ix + 1:ix + 1 + C.HORIZON_DAYS], ff,
                             betas=B)
        cache[t] = (res_f, {int(p): k for k, p in enumerate(g["permno"])})
    return cache


def _xcorr(a: np.ndarray, b: np.ndarray, lag: int) -> float:
    """corr(a[:-lag], b[lag:]) — a LEADS b by `lag` days."""
    x, y = a[:-lag], b[lag:]
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 40:
        return float("nan")
    x, y = x[ok], y[ok]
    sx, sy = x.std(), y.std()
    if sx < 1e-12 or sy < 1e-12:
        return float("nan")
    return float(((x - x.mean()) @ (y - y.mean())) / (len(x) * sx * sy))


def reversed_direction(inst: pd.DataFrame, cache: dict, seed: int) -> dict:
    """Upstream->downstream lead-lag minus downstream->upstream, at lags 1..5.

    Orientation comes from the edge itself, never from the outcome:
      supplier + direction 'in'  -> counterparty supplies subject: counterparty
                                    is upstream.
      customer + direction 'out' -> counterparty buys from subject: subject is
                                    upstream.
    Edges whose type/direction pair does not fix an orientation are dropped and
    counted; guessing an orientation would make this control vacuous.
    """
    rng = np.random.default_rng(seed)
    d = inst[inst["type"].isin(C.DIRECTED_TYPES)].copy()
    up, dn, dropped = [], [], 0
    for r in d.itertuples():
        if r.type == "supplier" and r.direction == "in":
            u, v = r.counterparty_permno, r.subject_permno
        elif r.type == "supplier" and r.direction == "out":
            u, v = r.subject_permno, r.counterparty_permno
        elif r.type == "customer" and r.direction == "out":
            u, v = r.subject_permno, r.counterparty_permno
        elif r.type == "customer" and r.direction == "in":
            u, v = r.counterparty_permno, r.subject_permno
        else:
            dropped += 1
            up.append(np.nan)
            dn.append(np.nan)
            continue
        up.append(u)
        dn.append(v)
    d["up"], d["dn"] = up, dn
    d = d.dropna(subset=["up", "dn"])
    d = d.drop_duplicates(["date", "up", "dn"])

    per_date, per_date_plac, n_used = [], [], 0
    for t, g in d.groupby("date"):
        if t not in cache:
            continue
        res, colmap = cache[t]
        diffs, plac = [], []
        for u, v in zip(g["up"].astype(int), g["dn"].astype(int)):
            cu, cv = colmap.get(u), colmap.get(v)
            if cu is None or cv is None:
                continue
            a, b = res[:, cu], res[:, cv]
            f = np.nanmean([_xcorr(a, b, L) for L in XLAGS])
            r = np.nanmean([_xcorr(b, a, L) for L in XLAGS])
            if not np.isfinite(f) or not np.isfinite(r):
                continue
            diffs.append(f - r)
            plac.append((f - r) * (1.0 if rng.random() < 0.5 else -1.0))
        if len(diffs) >= 3:
            per_date.append(float(np.mean(diffs)))
            per_date_plac.append(float(np.mean(plac)))
            n_used += len(diffs)
    if len(per_date) < 3:
        return {"error": f"only {len(per_date)} usable dates",
                "n_directed_edges": int(len(d)), "n_unoriented": dropped}
    return {"n_directed_pairs_graded": n_used,
            "n_unoriented_dropped": int(dropped),
            "asymmetry": stat_block(np.array(per_date)),
            "coinflip_placebo": stat_block(np.array(per_date_plac))}


# ── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()
    uni = pd.read_parquet(OUT / "universe.parquet")
    uni["date"] = pd.to_datetime(uni["date"])
    pairs = pd.read_parquet(OUT / "pairs.parquet")
    pairs["date"] = pd.to_datetime(pairs["date"])
    pairs["lo"] = np.minimum(pairs["permno_i"], pairs["permno_j"])
    pairs["hi"] = np.maximum(pairs["permno_i"], pairs["permno_j"])
    pairs["rho_trail2"] = pairs["rho_trail"].astype(float) ** 2
    pairs["same_sector"] = pairs["same_sector"].astype(float)
    pairs["rho_fwd"] = pairs["rho_fwd"].astype(float)
    pairs["rho_trail"] = pairs["rho_trail"].astype(float)

    # A finer industry code than FF12. The prereg's own warning is that "a
    # semantic edge that only rediscovers GICS is a slow expensive sector
    # dummy"; FF12 has twelve buckets, so two semiconductor firms are the SAME
    # FF12 group and two firms one SIC apart can be different ones. Excluding
    # same-2-digit-SIC pairs as well as same-FF12 pairs is the sharper version
    # of the same question, and it is the one arm that can tell "relationship"
    # from "taxonomy the trailing correlation had not caught up with".
    u = uni[["date", "permno", "siccd"]].copy()
    u["sic2"] = (pd.to_numeric(u["siccd"], errors="coerce")
                 .fillna(-1).astype(int) // 100)
    for side in ("i", "j"):
        pairs = pairs.merge(
            u[["date", "permno", "sic2"]].rename(
                columns={"permno": f"permno_{side}", "sic2": f"sic2_{side}"}),
            on=["date", f"permno_{side}"], how="left")
    pairs["same_sic2"] = (pairs["sic2_i"] == pairs["sic2_j"]).astype(float)

    inst = pd.read_parquet(OUT / "edge_instances.parquet")
    inst["date"] = pd.to_datetime(inst["date"])
    dates = sorted(pairs["date"].unique())
    print(f"pairs {len(pairs):,} over {len(dates)} cut dates; "
          f"edge-instances {len(inst):,}", flush=True)

    graphs = {
        "semantic": edge_features(inst),
        "placebo_shuffled": edge_features(
            shuffled_placebo(inst, uni, C.SEED_SHUFFLE)),
        "random_matched_density": edge_features(
            random_edges(inst, pairs, C.SEED_RANDOM_EDGES)),
    }

    report: dict = {"run_utc": pd.Timestamp.utcnow().isoformat(),
                    "n_pairs": int(len(pairs)), "n_cut_dates": len(dates),
                    "n_edge_instances": int(len(inst)),
                    "n_distinct_edge_pairs": int(
                        inst.groupby(["date", "lo", "hi"]).ngroups),
                    "arms": {}}

    for name, feats in graphs.items():
        df = attach(pairs, feats)
        cov = float((df["has_edge"] > 0).mean())
        print(f"\n=== H1 arm: {name}  (edge coverage {cov:.4%}) ===",
              flush=True)
        r_all = walk_forward(df, BASE_FEATS, SEM_FEATS, dates)
        print("  all pairs      :", json.dumps(r_all, default=str))
        xs = df[df["same_sector"] <= 0]
        r_x = walk_forward(xs, ["rho_trail", "rho_trail2"], SEM_FEATS, dates)
        print("  cross-sector   :", json.dumps(r_x, default=str))
        xs2 = df[(df["same_sector"] <= 0) & (df["same_sic2"] <= 0)]
        r_x2 = walk_forward(xs2, ["rho_trail", "rho_trail2"], SEM_FEATS, dates)
        print("  cross-FF12+SIC2:", json.dumps(r_x2, default=str))
        h = h2(df, C.SEED_H2_MATCH)
        print("  H2             :", json.dumps(h, default=str))
        hx = h2(xs, C.SEED_H2_MATCH)
        hx2 = h2(xs2, C.SEED_H2_MATCH)
        report["arms"][name] = {
            "edge_coverage_of_pairs": cov,
            "h1_all_pairs": r_all,
            "h1_cross_sector_only": r_x,
            "h1_cross_sector_and_sic2": r_x2,
            "h2_all_pairs": h,
            "h2_cross_sector_only": hx,
            "h2_cross_sector_and_sic2": hx2,
        }

    print("\n=== reversed-direction control ===", flush=True)
    cache = forward_residual_cache(uni)
    report["reversed_direction"] = reversed_direction(inst, cache,
                                                      C.SEED_SHUFFLE)
    print(json.dumps(report["reversed_direction"], indent=2, default=str))

    report["elapsed_min"] = round((time.time() - t0) / 60, 2)
    (OUT / "grade_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {OUT / 'grade_report.json'}  "
          f"({report['elapsed_min']} min)")


if __name__ == "__main__":
    main()
