"""DIAG-D3 — regenerate the analog belief ledger CAUSALLY and score it.

Two jobs, in one pass:

(a) REGENERATE. The shipped ledger (`ledger/belief_states.jsonl`, 283 monthly
    states) was backfilled with FULL-SAMPLE robust z: a 2005 state was
    standardized with 2026 information. Retrieval was causal, standardization
    was not, so the ledger as it stands is NOT scoreable. This script rebuilds
    every state at the SAME query dates using
    `aegis_brain.macro.causal_standardize.causal_robust_z`, into
    `ledger/belief_states_causal.jsonl` (overwritten each run, never appended).
    The sacred original is read-only here and is never touched.

(b) SCORE. Against realized SPY outcomes, under four binding rules:

    R1  The deciding baseline is PERSISTENCE, never climatology.
    R2  The deciding metric is a paired Diebold-Mariano test on the per-state
        Brier DIFFERENCE series (engine - persistence), variance by BOTH
        Newey-West AND circular block bootstrap. BSS is DESCRIPTIVE ONLY.
    R3  Report the Brier decomposition REL - RES + UNC (10 bins) for engine
        and persistence separately. RESOLUTION is the payable part.
    R4  Report N_eff ~= n(1-r1)/(1+r1) (Santer et al. 2000) beside raw n.

Usage
-----
  python -m scripts.diag_d3_score                      # default 63-td exclusion
  python -m scripts.diag_d3_score --exclusion-td 504   # D1 rerun
  python -m scripts.diag_d3_score --d4                 # confidence channel (D4)

Honest expectation, stated up front: with ~250 overlapping monthly states the
effective sample is on the order of 20-30. This is very likely INCONCLUSIVE.
That is a legitimate result. Do not shop for a verdict.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.macro import macro_analog as MA
from aegis_brain.macro.causal_standardize import (CAUSAL_VERSION,
                                                  DEFAULT_MIN_HISTORY_TD,
                                                  burn_in_start,
                                                  causal_robust_z,
                                                  contamination_report)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CAUSAL_ENGINE_VERSION = "analog-p1-causal-2026-07-29"
ORIG_LEDGER = MODULE_ROOT / "ledger" / "belief_states.jsonl"
CAUSAL_LEDGER = MODULE_ROOT / "ledger" / "belief_states_causal.jsonl"
REPORT = MODULE_ROOT / "docs" / "DIAG_D3_2026-07-29.md"

# outcome -> (forward horizon in trading days, Newey-West lag in months)
OUTCOMES = {
    "fwd6m_positive": (126, 6),
    "fwd12m_positive": (252, 12),
    "crash12m_dd15": (252, 12),
    "crash12m_dd20": (252, 12),
}
DD_THRESH = {"crash12m_dd15": -0.15, "crash12m_dd20": -0.20}
N_BINS = 10
BLOCK_LEN = 12


# ============================================================ (a) REGENERATE
def load_query_dates(path: Path) -> tuple[list[str], int]:
    """Ledger query dates, de-duplicated, order preserved.

    The shipped ledger has 283 rows but 282 unique dates (2026-07-24 appears
    twice: month-end backfill + the live run). One state per date is written.
    """
    raw = [json.loads(ln)["query_date"]
           for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    seen, uniq = set(), []
    for q in raw:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq, len(raw)


def regenerate(exclusion_td: int, min_history_td: int) -> dict:
    """Rebuild every ledger state under causal standardization."""
    MA.SELF_EXCLUSION_TD = exclusion_td          # module attr, file untouched

    d = MA.build_descriptors()
    z = causal_robust_z(d, min_history_td=min_history_td)
    zc = z.dropna()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    qdates, n_raw = load_query_dates(ORIG_LEDGER)
    rows, skipped = [], []
    for qs in qdates:
        qd = pd.Timestamp(qs)
        if qd not in zc.index:
            skipped.append((qs, "burn-in: no complete causal vector"))
            continue
        try:
            belief, detail = MA.compute_belief(z, qd, now, backfill=True)
        except (KeyError, ValueError) as exc:
            skipped.append((qs, str(exc)))
            continue
        dists = [a["distance"] for a in detail["analogs"]]
        belief.engine_version = CAUSAL_ENGINE_VERSION
        belief.extras = {
            "standardization": CAUSAL_VERSION,
            "min_history_td": min_history_td,
            "exclusion_td": exclusion_td,
            "n_analogs_used": len(dists),
            "mean_analog_distance": round(float(np.mean(dists)), 4) if dists else None,
        }
        rows.append(asdict(belief))

    CAUSAL_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(CAUSAL_LEDGER, "w", encoding="utf-8") as fh:   # overwrite, never append
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    return {
        "n_ledger_rows": n_raw,
        "n_requested": len(qdates),
        "n_written": len(rows),
        "n_skipped": len(skipped),
        "skipped": skipped,
        "first_scoreable": rows[0]["query_date"] if rows else None,
        "last_scoreable": rows[-1]["query_date"] if rows else None,
        "orig_first": qdates[0],
        "library_rows_causal": int(len(zc)),
        "library_start_causal": str(zc.index.min().date()),
        "library_rows_full": int(MA.robust_z(d).dropna().shape[0]),
        "library_start_full": str(MA.robust_z(d).dropna().index.min().date()),
        "burn_in_start": str(burn_in_start(d, min_history_td).date()),
        "contamination_table": contamination_report(d, min_history_td),
    }


# ========================================================= outcomes/baselines
def load_spy() -> pd.Series:
    return pd.read_parquet(MA.ETF_SNAP).sort_index()["SPY"].dropna()


def realized_and_persistence(spy: pd.Series, dates: list[pd.Timestamp]) -> dict:
    """Realized binary outcomes + PERSISTENCE forecasts per query date.

    Realized (NaN when the horizon runs past the data right edge):
      fwd6m_positive   SPY[p+126]/SPY[p] - 1 > 0
      fwd12m_positive  SPY[p+252]/SPY[p] - 1 > 0
      crash12m_dd15/20 max drawdown over (p, p+252] <= -15% / -20%
    Persistence (binary, mirror-image of the outcome on trailing data):
      trailing 126td return > 0 / trailing 252td return > 0 /
      trailing 252td max drawdown <= -15% / -20%
    """
    pos = {d: spy.index.get_loc(d) for d in dates}
    y = {k: [] for k in OUTCOMES}
    f = {k: [] for k in OUTCOMES}
    n = len(spy)
    for d in dates:
        p = pos[d]
        # ---- realized
        y["fwd6m_positive"].append(
            float(spy.iloc[p + 126] / spy.iloc[p] - 1 > 0) if p + 126 < n else np.nan)
        y["fwd12m_positive"].append(
            float(spy.iloc[p + 252] / spy.iloc[p] - 1 > 0) if p + 252 < n else np.nan)
        if p + 252 < n:
            path = spy.iloc[p: p + 253]
            dd = float((path / path.cummax() - 1).min())
        else:
            dd = np.nan
        for k, thr in DD_THRESH.items():
            y[k].append(float(dd <= thr) if dd == dd else np.nan)
        # ---- persistence
        f["fwd6m_positive"].append(
            float(spy.iloc[p] / spy.iloc[p - 126] - 1 > 0) if p - 126 >= 0 else np.nan)
        r252 = (float(spy.iloc[p] / spy.iloc[p - 252] - 1 > 0)
                if p - 252 >= 0 else np.nan)
        f["fwd12m_positive"].append(r252)
        if p - 252 >= 0:
            tpath = spy.iloc[p - 252: p + 1]
            tdd = float((tpath / tpath.cummax() - 1).min())
        else:
            tdd = np.nan
        for k, thr in DD_THRESH.items():
            f[k].append(float(tdd <= thr) if tdd == tdd else np.nan)
    return {"y": pd.DataFrame(y, index=dates), "persistence": pd.DataFrame(f, index=dates)}


def causal_climatology(dates: list[pd.Timestamp], y: pd.DataFrame,
                       spy: pd.Series) -> pd.DataFrame:
    """Expanding-window climatology, causal: at state i the forecast is the
    mean realized outcome over states whose OWN horizon had already resolved
    by query_date_i. REPORTED ONLY -- never deciding (R1)."""
    out = {}
    posd = {d: spy.index.get_loc(d) for d in dates}
    for col, (h, _) in OUTCOMES.items():
        vals = []
        for i, d in enumerate(dates):
            usable = [y[col].iloc[j] for j, dj in enumerate(dates)
                      if posd[dj] + h <= posd[d] and y[col].iloc[j] == y[col].iloc[j]]
            vals.append(float(np.mean(usable)) if usable else 0.5)
        out[col] = vals
    return pd.DataFrame(out, index=dates)


# ================================================================ statistics
def brier_decomposition(p: np.ndarray, y: np.ndarray, n_bins: int = N_BINS) -> dict:
    """Murphy (1973) REL - RES + UNC, `n_bins` equal-width probability bins."""
    n = len(y)
    ybar = float(y.mean())
    b = np.clip((p * n_bins).astype(int), 0, n_bins - 1)
    rel = res = 0.0
    for k in range(n_bins):
        m = b == k
        nk = int(m.sum())
        if nk == 0:
            continue
        pk, yk = float(p[m].mean()), float(y[m].mean())
        rel += nk * (pk - yk) ** 2
        res += nk * (yk - ybar) ** 2
    rel /= n
    res /= n
    unc = ybar * (1 - ybar)
    return {"brier": float(np.mean((p - y) ** 2)), "REL": rel, "RES": res,
            "UNC": unc, "check": rel - res + unc, "n_bins_used": int(len(set(b)))}


def newey_west_var(dd: np.ndarray, lag: int) -> float:
    """HAC variance of the sample MEAN with Bartlett kernel."""
    n = len(dd)
    e = dd - dd.mean()
    g0 = float((e * e).sum() / n)
    v = g0
    for k in range(1, min(lag, n - 1) + 1):
        gk = float((e[k:] * e[:-k]).sum() / n)
        v += 2.0 * (1.0 - k / (lag + 1.0)) * gk
    if v <= 0:
        v = g0                                   # degenerate HAC -> iid fallback
    return v / n


def circular_block_bootstrap(dd: np.ndarray, block: int = BLOCK_LEN,
                             n_boot: int = 2000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    n = len(dd)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, nb))
    offs = np.arange(block)
    idx = (starts[:, :, None] + offs[None, None, :]) % n      # circular wrap
    means = dd[idx.reshape(n_boot, -1)[:, :n]].mean(axis=1)
    se = float(means.std(ddof=1))
    return {"se": se, "lo": float(np.percentile(means, 2.5)),
            "hi": float(np.percentile(means, 97.5)),
            "t": float(dd.mean() / se) if se > 0 else np.nan,
            "n_boot": int(n_boot), "block": int(block)}


def n_eff(dd: np.ndarray) -> tuple[float, float]:
    """Santer et al. (2000) effective sample size from lag-1 autocorrelation."""
    n = len(dd)
    if n < 3:
        return float(n), 0.0
    e = dd - dd.mean()
    denom = float((e * e).sum())
    r1 = float((e[1:] * e[:-1]).sum() / denom) if denom > 0 else 0.0
    r1 = float(np.clip(r1, -0.999, 0.999))
    return float(np.clip(n * (1 - r1) / (1 + r1), 1.0, n)), r1


def score_outcome(p: np.ndarray, y: np.ndarray, base: np.ndarray, clim: np.ndarray,
                  nw_lag: int, n_boot: int, seed: int) -> dict:
    b_eng = (p - y) ** 2
    b_bas = (base - y) ** 2
    b_cli = (clim - y) ** 2
    dd = b_eng - b_bas
    n = len(dd)
    nw_v = newey_west_var(dd, nw_lag)
    nw_se = float(np.sqrt(nw_v))
    t_nw = float(dd.mean() / nw_se) if nw_se > 0 else np.nan
    # Harvey-Leybourne-Newbold small-sample correction (n is small by design)
    hln = float(np.sqrt(max((n + 1 - 2 * nw_lag + nw_lag * (nw_lag - 1) / n) / n, 1e-9)))
    boot = circular_block_bootstrap(dd, BLOCK_LEN, n_boot, seed)
    ne, r1 = n_eff(dd)

    nw_lo, nw_hi = dd.mean() - 1.96 * nw_se, dd.mean() + 1.96 * nw_se
    if nw_hi < 0 and boot["hi"] < 0:
        verdict = "BEATS PERSISTENCE"
    elif nw_lo > 0 and boot["lo"] > 0:
        verdict = "LOSES TO PERSISTENCE"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "n": n, "n_eff": ne, "rho1": r1,
        "brier_engine": float(b_eng.mean()), "brier_persistence": float(b_bas.mean()),
        "brier_climatology": float(b_cli.mean()),
        "mean_diff": float(dd.mean()),
        "nw_lag": nw_lag, "nw_se": nw_se, "t_nw": t_nw,
        "t_hln": t_nw * hln, "nw_ci": (float(nw_lo), float(nw_hi)),
        "boot": boot,
        "bss_vs_persistence": float(1 - b_eng.mean() / b_bas.mean()) if b_bas.mean() > 0 else np.nan,
        "bss_vs_climatology": float(1 - b_eng.mean() / b_cli.mean()) if b_cli.mean() > 0 else np.nan,
        "decomp_engine": brier_decomposition(p, y),
        "decomp_persistence": brier_decomposition(base, y),
        "base_rate": float(y.mean()),
        "verdict": verdict,
    }


# ==================================================================== scoring
def read_ledger(path: Path) -> pd.DataFrame:
    recs = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]
    rows = []
    for r in recs:
        row = {"query_date": pd.Timestamp(r["query_date"]),
               "confidence": r.get("confidence"),
               "engine_version": r.get("engine_version")}
        row.update({k: r["state_probs"].get(k) for k in OUTCOMES})
        ex = r.get("extras") or {}
        md = ex.get("mean_analog_distance")
        if md is None:                                  # fall back to episodes
            eps = (r.get("evidence") or {}).get("episodes") or []
            tot = sum(e["n_analogs"] for e in eps)
            md = (sum(e["mean_distance"] * e["n_analogs"] for e in eps) / tot
                  if tot else None)
        row["mean_analog_distance"] = md
        row["n_analogs_used"] = ex.get("n_analogs_used")
        rows.append(row)
    return (pd.DataFrame(rows).drop_duplicates("query_date", keep="first")
            .sort_values("query_date").reset_index(drop=True))


def score_ledger(led: pd.DataFrame, spy: pd.Series, n_boot: int, seed: int,
                 label: str) -> dict:
    dates = [d for d in led["query_date"] if d in spy.index]
    led = led[led["query_date"].isin(dates)].reset_index(drop=True)
    rp = realized_and_persistence(spy, list(led["query_date"]))
    y_all, base_all = rp["y"], rp["persistence"]
    clim_all = causal_climatology(list(led["query_date"]), y_all, spy)

    res = {"label": label, "n_states": len(led),
           "span": (str(led["query_date"].min().date()), str(led["query_date"].max().date())),
           "outcomes": {}, "excluded": {}}
    for col, (h, lag) in OUTCOMES.items():
        p = led[col].astype(float).to_numpy()
        y = y_all[col].to_numpy()
        base = base_all[col].to_numpy()
        clim = clim_all[col].to_numpy()
        m = ~(np.isnan(p) | np.isnan(y) | np.isnan(base))
        res["excluded"][col] = {
            "right_edge": int(np.isnan(y).sum()),
            "no_engine_prob": int(np.isnan(p).sum()),
            "no_persistence": int(np.isnan(base).sum()),
            "scored": int(m.sum()),
        }
        if m.sum() < 10:
            res["outcomes"][col] = {"n": int(m.sum()), "verdict": "INSUFFICIENT DATA"}
            continue
        res["outcomes"][col] = score_outcome(p[m], y[m], base[m], clim[m],
                                             lag, n_boot, seed)
        res["outcomes"][col]["masked"] = m
    res["_frame"] = led
    res["_y"] = y_all
    return res


# ======================================================================== D4
def run_d4(res: dict) -> dict:
    """Confidence channel. Kill line: purged correlation < 0.15 => the
    confidence channel does not exist and abstention is decoration."""
    led, y_all = res["_frame"], res["_y"]
    out = {}
    for col in OUTCOMES:
        r = res["outcomes"].get(col, {})
        if "masked" not in r:
            continue
        m = r["masked"]
        p = led[col].astype(float).to_numpy()[m]
        y = y_all[col].to_numpy()[m]
        dist = led["mean_analog_distance"].astype(float).to_numpy()[m]
        conf = led["confidence"].astype(float).to_numpy()[m]
        err = np.abs(p - y)
        ok = ~(np.isnan(dist) | np.isnan(err))
        corr = float(np.corrcoef(dist[ok], err[ok])[0, 1]) if ok.sum() > 3 else np.nan
        # confidence terciles -> resolution within each bin
        qs = np.nanquantile(conf, [1 / 3, 2 / 3])
        tercile = np.digitize(conf, qs)
        bins = []
        for t in (0, 1, 2):
            s = tercile == t
            if s.sum() < 5:
                bins.append({"tercile": t, "n": int(s.sum())})
                continue
            dec = brier_decomposition(p[s], y[s])
            bins.append({"tercile": t, "n": int(s.sum()),
                         "conf_range": (float(conf[s].min()), float(conf[s].max())),
                         "RES": dec["RES"], "brier": dec["brier"],
                         "base_rate": float(y[s].mean())})
        out[col] = {"corr_dist_abserr": corr, "n": int(ok.sum()), "terciles": bins,
                    "kill": ("CHANNEL ABSENT (abstention is decoration)"
                             if not (abs(corr) >= 0.15) else "channel plausibly present")}
    return out


# ==================================================================== report
def _f(x, nd=4):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    return f"{x:.{nd}f}"


def write_report(regen: dict, causal: dict, contam: dict, contam_common: dict,
                 agree: dict, args, d4: dict | None) -> None:
    L = []
    A = L.append
    A("# DIAG-D3 — causal re-standardization and scoring of the analog belief engine")
    A("")
    A(f"Run: {datetime.datetime.now(datetime.timezone.utc).isoformat()} · "
      f"exclusion = **{args.exclusion_td} td** · burn-in = {args.min_history_td} td · "
      f"bootstrap = {args.bootstrap} resamples, block {BLOCK_LEN}")
    A("")
    A("## The four binding rules (quoted)")
    A("")
    A("> **R1.** The deciding baseline is PERSISTENCE, never climatology. "
      "An expanding-window (causal) climatology baseline is REPORTED ONLY, never deciding.")
    A("> ")
    A("> **R2.** The deciding metric is a paired Diebold-Mariano test on the per-state "
      "Brier DIFFERENCE series (engine − persistence), per outcome. Variance via BOTH "
      "Newey-West (lag = horizon in months) AND a circular block bootstrap "
      "(block length 12, ≥2000 resamples) — report both. "
      "BSS is reported as DESCRIPTIVE ONLY and must be labeled so.")
    A("> ")
    A("> **R3.** Report the Brier decomposition REL − RES + UNC (10 probability bins) "
      "separately for engine and persistence, per outcome. "
      "RESOLUTION is the payable part — say which forecaster has more of it.")
    A("> ")
    A("> **R4.** Report N_eff ≈ n(1−r₁)/(1+r₁) (Santer et al. 2000) computed on each "
      "Brier-difference series, alongside raw n.")
    A("")
    A("## Stated honest expectation (written before reading the numbers)")
    A("")
    A("> With N_eff ≈ 23 this will very likely be INCONCLUSIVE — that is a legitimate "
      "result, do not shop for a verdict.")
    A("")
    A("Monthly states over ~20 years with 6–12 month overlapping horizons carry roughly "
      "one independent observation per horizon. The test is underpowered **by "
      "construction**; a null result is information about the design, not about the world.")
    A("")
    A("## Headline (numbers first)")
    A("")
    A("| outcome | verdict (95%) | DM t (NW) | DM t (boot) | n | N_eff | engine RES / UNC |")
    A("|---|---|---:|---:|---:|---:|---:|")
    for col in OUTCOMES:
        r = causal["outcomes"][col]
        if "t_nw" not in r:
            A(f"| {col} | {r['verdict']} | — | — | {r['n']} | — | — |")
            continue
        de = r["decomp_engine"]
        A(f"| `{col}` | **{r['verdict']}** | {r['t_nw']:.2f} | {r['boot']['t']:.2f} | "
          f"{r['n']} | {r['n_eff']:.1f} | {_f(de['RES'] / de['UNC'] * 100, 1)}% |")
    A("")
    n_beats = sum(1 for c in OUTCOMES
                  if causal["outcomes"][c]["verdict"] == "BEATS PERSISTENCE")
    A(f"{n_beats} of {len(OUTCOMES)} outcomes clear the pre-registered bar at this "
      "exclusion, but §3 shows how much of each Brier margin is reliability (hedging "
      "against a 0/1 baseline) rather than resolution. No verdict was altered after "
      "seeing the numbers.")
    A("")
    A("## 0. The defect being repaired")
    A("")
    A("`macro_analog.robust_z` standardizes with a full-sample median/IQR over 2002–2026. "
      "Retrieval is causal (candidates strictly older than the query) but standardization "
      "is not — a 2005 state was expressed in units that include 2026. Both the query "
      "vector and every library vector are displaced by information that did not exist at "
      "their own timestamps, so the metric defining 'nearest analog' is contaminated. "
      "`causal_robust_z` replaces the two constants with expanding-window estimates using "
      "only rows ≤ t; the exact per-row expanding estimator is used (measured ~0.05 s on "
      "the 6179×15 panel), not the monthly step-function fallback.")
    A("")
    A("| | full-sample (shipped) | causal (this run) |")
    A("|---|---|---|")
    A(f"| library complete rows | {regen['library_rows_full']} | {regen['library_rows_causal']} |")
    A(f"| library starts | {regen['library_start_full']} | {regen['library_start_causal']} |")
    A(f"| states written | {regen['n_requested']} "
      f"({regen['n_ledger_rows']} ledger rows, 1 duplicate date collapsed) "
      f"| {regen['n_written']} |")
    A(f"| states skipped (burn-in / <50 candidates) | 0 | {regen['n_skipped']} |")
    A(f"| first scoreable state | {regen['orig_first']} | {regen['first_scoreable']} |")
    A("")
    A("Per-feature displacement caused by full-sample standardization "
      "(|causal z − full-sample z| over the overlapping rows):")
    A("")
    ct = regen["contamination_table"].round(3)
    A("| feature | n | mean abs diff | p95 | max |")
    A("|---|---:|---:|---:|---:|")
    for k, r in ct.iterrows():
        A(f"| {k} | {int(r['n_compared'])} | {r['mean_abs_diff']:.3f} | "
          f"{r['p95_abs_diff']:.3f} | {r['max_abs_diff']:.3f} |")
    A("")
    A("## 1. Scoring inputs")
    A("")
    A(f"Causal ledger: `ledger/belief_states_causal.jsonl`, {causal['n_states']} states, "
      f"{causal['span'][0]} → {causal['span'][1]}, engine_version `{CAUSAL_ENGINE_VERSION}`.")
    A("")
    A("Per-outcome exclusions (states whose horizon runs past the data right edge are "
      "dropped for that outcome only):")
    A("")
    A("| outcome | horizon (td) | scored n | dropped: right edge | dropped: no engine prob |")
    A("|---|---:|---:|---:|---:|")
    for col, (h, _) in OUTCOMES.items():
        e = causal["excluded"][col]
        A(f"| {col} | {h} | {e['scored']} | {e['right_edge']} | {e['no_engine_prob']} |")
    A("")
    A("## 2. R2 — Diebold-Mariano, engine vs PERSISTENCE (the deciding test)")
    A("")
    A("Difference series d = Brier(engine) − Brier(persistence). **Negative = engine "
      "better.** A verdict of BEATS/LOSES requires the 95% interval to exclude zero under "
      "**both** variance estimators; otherwise INCONCLUSIVE.")
    A("")
    A("| outcome | n | N_eff | r₁ | Brier eng | Brier pers | mean d | DM t (NW) | NW 95% CI | boot t | boot 95% CI | verdict |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|")
    for col in OUTCOMES:
        r = causal["outcomes"][col]
        if "t_nw" not in r:
            A(f"| {col} | {r['n']} | — | — | — | — | — | — | — | — | — | {r['verdict']} |")
            continue
        A(f"| {col} | {r['n']} | {r['n_eff']:.1f} | {r['rho1']:.2f} | "
          f"{_f(r['brier_engine'])} | {_f(r['brier_persistence'])} | {_f(r['mean_diff'])} | "
          f"{r['t_nw']:.2f} | [{_f(r['nw_ci'][0],3)}, {_f(r['nw_ci'][1],3)}] | "
          f"{r['boot']['t']:.2f} | [{_f(r['boot']['lo'],3)}, {_f(r['boot']['hi'],3)}] | "
          f"**{r['verdict']}** |")
    A("")
    A("Harvey-Leybourne-Newbold small-sample corrected t (same sign, shrunk toward zero): "
      + ", ".join(f"{c} {causal['outcomes'][c].get('t_hln', float('nan')):.2f}"
                  for c in OUTCOMES if "t_hln" in causal["outcomes"][c]))
    A("")
    A("### DESCRIPTIVE ONLY — Brier skill scores (not deciding, R2)")
    A("")
    A("| outcome | BSS vs persistence | BSS vs causal climatology | Brier climatology |")
    A("|---|---:|---:|---:|")
    for col in OUTCOMES:
        r = causal["outcomes"][col]
        if "bss_vs_persistence" not in r:
            continue
        A(f"| {col} | {_f(r['bss_vs_persistence'],3)} | {_f(r['bss_vs_climatology'],3)} | "
          f"{_f(r['brier_climatology'])} |")
    A("")
    A("## 3. R3 — Brier decomposition REL − RES + UNC (10 bins)")
    A("")
    A("RESOLUTION (RES) is the payable part: it is the only term that says the forecaster "
      "separates high-outcome from low-outcome states. Reliability (REL) is fixable by "
      "recalibration; uncertainty (UNC) belongs to the outcome, not the forecaster.")
    A("")
    A("| outcome | base rate | REL eng | RES eng | REL pers | RES pers | UNC | more RESOLUTION |")
    A("|---|---:|---:|---:|---:|---:|---:|---|")
    for col in OUTCOMES:
        r = causal["outcomes"][col]
        if "decomp_engine" not in r:
            continue
        de, dp = r["decomp_engine"], r["decomp_persistence"]
        who = ("engine" if de["RES"] > dp["RES"] else
               "persistence" if dp["RES"] > de["RES"] else "tie")
        A(f"| {col} | {_f(r['base_rate'],3)} | {_f(de['REL'])} | {_f(de['RES'])} | "
          f"{_f(dp['REL'])} | {_f(dp['RES'])} | {_f(de['UNC'])} | **{who}** |")
    A("")
    A("### Where the Brier win actually comes from (UNC cancels in the difference)")
    A("")
    A("Brier(eng) − Brier(pers) = (REL_eng − REL_pers) − (RES_eng − RES_pers). "
      "Reliability is a hedging term: persistence is forced to forecast 0 or 1, so it is "
      "maximally unreliable by construction, and any hedged probability collects that gap "
      "**without forecasting anything**. Only ΔRES is payable.")
    A("")
    A("| outcome | Brier gap | from reliability (ΔREL) | from resolution (ΔRES) | share of gap from hedging | engine RES / UNC |")
    A("|---|---:|---:|---:|---:|---:|")
    for col in OUTCOMES:
        r = causal["outcomes"][col]
        if "decomp_engine" not in r:
            continue
        de, dp = r["decomp_engine"], r["decomp_persistence"]
        d_rel = dp["REL"] - de["REL"]            # positive = engine gains from hedging
        d_res = de["RES"] - dp["RES"]            # positive = engine gains from skill
        tot = d_rel + d_res
        share = d_rel / tot if tot != 0 else np.nan
        A(f"| {col} | {_f(-r['mean_diff'])} | {_f(d_rel)} | {_f(d_res)} | "
          f"{_f(share * 100, 1)}% | {_f(de['RES'] / de['UNC'] * 100, 1)}% |")
    A("")
    A("**Read this before reading the verdicts.** Resolution is the fraction of the "
      "outcome's own uncertainty the forecaster actually resolves; the last column is that "
      "fraction. Wherever REL_eng > RES_eng in the table above, the engine's "
      "miscalibration exceeds its resolution and a CONSTANT forecast at the base rate "
      "would score a strictly better Brier than the engine. The verdicts in §2 are "
      "the pre-registered decision rule and are reported unaltered, but a Brier win built "
      "almost entirely from ΔREL against a 0/1 baseline is a win for *hedging*, not for "
      "*information*.")
    A("")
    A("## 4. R4 — effective sample size")
    A("")
    A("| outcome | raw n | lag-1 autocorr r₁ of d | N_eff |")
    A("|---|---:|---:|---:|")
    for col in OUTCOMES:
        r = causal["outcomes"][col]
        if "n_eff" not in r:
            continue
        A(f"| {col} | {r['n']} | {r['rho1']:.3f} | {r['n_eff']:.1f} |")
    A("")
    A("## 5. Contaminated ledger — for comparison only")
    A("")
    A("**Contaminated — for comparison only.** The shipped `belief_states.jsonl` scored "
      "identically. These numbers are NOT evidence about the engine's skill; they measure "
      "how much the look-ahead standardization moved the scoreboard.")
    A("")
    A("| outcome | Brier eng (contaminated, all states) | Brier eng (contaminated, common dates) | Brier eng (causal) | Δ causal − contaminated(common) | DM t (contaminated, common) | verdict (contaminated) |")
    A("|---|---:|---:|---:|---:|---:|---|")
    for col in OUTCOMES:
        rc = causal["outcomes"][col]
        ra = contam["outcomes"].get(col, {})
        rk = contam_common["outcomes"].get(col, {})
        if "brier_engine" not in rc or "brier_engine" not in rk:
            continue
        A(f"| {col} | {_f(ra.get('brier_engine'))} | {_f(rk['brier_engine'])} | "
          f"{_f(rc['brier_engine'])} | {_f(rc['brier_engine'] - rk['brier_engine'])} | "
          f"{rk.get('t_nw', float('nan')):.2f} | {rk.get('verdict','—')} |")
    A("")
    A("Per-state probability displacement on the common dates "
      "(|p_causal − p_contaminated|):")
    A("")
    A("| outcome | n common | mean abs Δp | p95 | max | sign flips vs 0.5 |")
    A("|---|---:|---:|---:|---:|---:|")
    for col in OUTCOMES:
        a = agree[col]
        A(f"| {col} | {a['n']} | {_f(a['mean'],3)} | {_f(a['p95'],3)} | {_f(a['max'],3)} | {a['flips']} |")
    A("")
    if d4 is not None:
        A("## 6. D4 — confidence channel")
        A("")
        A("Kill line: **purged correlation < 0.15 ⇒ the confidence channel does not exist "
          "and abstention is decoration.**")
        A("")
        A("| outcome | corr(mean analog distance, abs forecast error) | n | verdict |")
        A("|---|---:|---:|---|")
        for col, r in d4.items():
            A(f"| {col} | {_f(r['corr_dist_abserr'],3)} | {r['n']} | {r['kill']} |")
        A("")
        A("Resolution by stated-confidence tercile:")
        A("")
        A("| outcome | tercile | n | confidence range | RES | Brier | base rate |")
        A("|---|---:|---:|---|---:|---:|---:|")
        for col, r in d4.items():
            for b in r["terciles"]:
                if "RES" not in b:
                    A(f"| {col} | {b['tercile']} | {b['n']} | — | — | — | — |")
                    continue
                A(f"| {col} | {b['tercile']} | {b['n']} | "
                  f"{b['conf_range'][0]:.2f}–{b['conf_range'][1]:.2f} | "
                  f"{_f(b['RES'])} | {_f(b['brier'])} | {_f(b['base_rate'],3)} |")
        A("")
    else:
        A("## 6. D4 — confidence channel")
        A("")
        A("Not run (`--d4` off by default; invoked separately only if D1–D3 survive).")
        A("")
    A("## 7. Final verdict, per outcome (95%)")
    A("")
    for col in OUTCOMES:
        r = causal["outcomes"][col]
        if "t_nw" not in r:
            A(f"- **{col}: {r['verdict']}** (n = {r['n']})")
            continue
        A(f"- **{col}: {r['verdict']} at 95%** — DM t(NW, lag {r['nw_lag']}) = "
          f"{r['t_nw']:.2f}, bootstrap t = {r['boot']['t']:.2f}, "
          f"n = {r['n']}, N_eff = {r['n_eff']:.1f}, "
          f"Brier {_f(r['brier_engine'],4)} vs persistence {_f(r['brier_persistence'],4)}.")
    A("")
    A("## 8. Caveats that limit what any of the above can mean")
    A("")
    if args.exclusion_td < 504:
        A(f"1. **Analog forward windows overlap the query's own future.** With an exclusion of "
          f"{args.exclusion_td} td, an analog sitting just past the exclusion boundary still "
          f"has its 6m/12m/24m forward outcome measured up to {126 - args.exclusion_td} / "
          f"{252 - args.exclusion_td} / {504 - args.exclusion_td} trading days AFTER the query "
          "date. Standardization is now causal; the OUTCOME AGGREGATION is not, at this "
          "exclusion. Rerun with `--exclusion-td 504` to close it.")
    else:
        A(f"1. **Outcome-aggregation leak closed at this exclusion.** With {args.exclusion_td} td "
          "of self-exclusion, every analog's 6m/12m/24m forward window ends at or before the "
          "query date (the boundary analog's 24m window ends exactly at it). Standardization "
          "and outcome aggregation are both causal in this run.")
    A("2. **Overlapping monthly states.** Consecutive states share most of their forward "
      "window; N_eff above is the honest count.")
    A("3. **One market, one history.** All four outcomes are functions of the same SPY "
      "path; the four tests are not independent.")
    A("4. **The baseline is binary, the engine is probabilistic.** Persistence as "
      "specified emits 0/1, so its Brier score is its error RATE and it is maximally "
      "penalized for being wrong. A hedged probabilistic forecaster wins that comparison "
      "on reliability alone. This asymmetry is baked into the pre-registered rule (R1) and "
      "the verdicts respect it, but §3's ΔRES column — not the DM t — is what says whether "
      "the engine knows anything.")
    A("5. Causal standardization costs the first ~2 years of the library "
      f"({regen['n_skipped']} states unscoreable, first scoreable "
      f"{regen['first_scoreable']}).")
    A("")
    A("Artifacts: `ledger/belief_states_causal.jsonl` (regenerated, overwritten each run) · "
      "`aegis_brain/macro/causal_standardize.py` · `tests/test_causal_standardize.py` · "
      "`scripts/diag_d3_score.py`. The sacred `ledger/belief_states.jsonl` is read-only "
      "throughout and was not modified.")
    A("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L), encoding="utf-8")


# ====================================================================== main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclusion-td", type=int, default=63)
    ap.add_argument("--min-history-td", type=int, default=DEFAULT_MIN_HISTORY_TD)
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--d4", action="store_true",
                    help="run the D4 confidence-channel diagnostic (off by default)")
    args = ap.parse_args()

    print(f"[regen] exclusion={args.exclusion_td}td min_history={args.min_history_td}td")
    regen = regenerate(args.exclusion_td, args.min_history_td)
    print(f"[regen] wrote {regen['n_written']} states "
          f"({regen['n_skipped']} skipped), first scoreable {regen['first_scoreable']}")
    for qs, why in regen["skipped"][:3]:
        print(f"         skip {qs}: {why}")

    spy = load_spy()
    causal_led = read_ledger(CAUSAL_LEDGER)
    orig_led = read_ledger(ORIG_LEDGER)
    common = set(causal_led["query_date"]) & set(orig_led["query_date"])

    causal = score_ledger(causal_led, spy, args.bootstrap, args.seed, "causal")
    contam = score_ledger(orig_led, spy, args.bootstrap, args.seed,
                          "contaminated (all states)")
    contam_common = score_ledger(
        orig_led[orig_led["query_date"].isin(common)].reset_index(drop=True),
        spy, args.bootstrap, args.seed, "contaminated (common dates)")

    a = causal_led.set_index("query_date")
    b = orig_led.set_index("query_date")
    idx = sorted(common)
    agree = {}
    for col in OUTCOMES:
        dv = (a.loc[idx, col].astype(float) - b.loc[idx, col].astype(float)).abs().dropna()
        flips = int(((a.loc[idx, col].astype(float) > 0.5) !=
                     (b.loc[idx, col].astype(float) > 0.5)).sum())
        agree[col] = {"n": int(len(dv)), "mean": float(dv.mean()),
                      "p95": float(dv.quantile(0.95)), "max": float(dv.max()),
                      "flips": flips}

    d4 = run_d4(causal) if args.d4 else None

    write_report(regen, causal, contam, contam_common, agree, args, d4)

    print(f"\n{'outcome':<18}{'n':>5}{'N_eff':>8}{'B_eng':>9}{'B_pers':>9}"
          f"{'t_NW':>8}{'t_boot':>8}  verdict")
    for col in OUTCOMES:
        r = causal["outcomes"][col]
        if "t_nw" not in r:
            print(f"{col:<18}{r['n']:>5}   {r['verdict']}")
            continue
        print(f"{col:<18}{r['n']:>5}{r['n_eff']:>8.1f}{r['brier_engine']:>9.4f}"
              f"{r['brier_persistence']:>9.4f}{r['t_nw']:>8.2f}{r['boot']['t']:>8.2f}"
              f"  {r['verdict']}")
    if d4:
        print("\n[D4]", {k: round(v["corr_dist_abserr"], 3) for k, v in d4.items()})
    print(f"\n-> {REPORT}\n-> {CAUSAL_LEDGER}")


if __name__ == "__main__":
    main()
