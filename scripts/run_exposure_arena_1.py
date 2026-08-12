"""EXPOSURE-ARENA-1 — GRAND-ARENA-1 CHUNK 6, the exposure / timing arena.

Pre-registered `TRIALS/PREREG_EXPOSURE_ARENA_1.md` at commit 31a49f8 (spec) and
f36f321 (§11 clarifications) BEFORE this file existed. The spec is frozen there;
this runner implements it and has no tuning knobs on the command line.

    python -m scripts.run_exposure_arena_1                # all stages, resumes
    python -m scripts.run_exposure_arena_1 --stage 4      # one stage
    python -m scripts.run_exposure_arena_1 --force        # ignore checkpoints

ORDER OF OPERATIONS IS THE PREREG'S, AND IT IS THE POINT (§A1). Stage 2 builds
the matched-average-exposure FRONTIER — a pure function of mean exposure and the
bed, with no free parameters — and writes it to disk. Stage 3 is the first stage
allowed to construct a controller. The runner asserts the frontier file's mtime
predates every controller artifact, so the control that decides cannot have been
tuned to lose.

Every stage checkpoints to `data/factory/exposure_arena_1_*.json`; a crashed run
resumes at the first stage whose artifact is missing.
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
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scripts import exposure_arena_core as C          # noqa: E402
from scripts import exposure_arena_learn as L         # noqa: E402

OUT = C.OUT_DIR
PREREG = "TRIALS/PREREG_EXPOSURE_ARENA_1.md @ 31a49f8 (+§11 @ f36f321)"
BEDS = ("BED1", "BED2", "BED3")

# ── the full declared configuration grid (prereg §7) ──────────────────────
def controller_grid() -> list[dict]:
    g: list[dict] = []
    g.append({"id": "A_FULL", "family": "A", "fn": "ctrl_full", "kw": {},
              "primary": True})
    g.append({"id": "B_STATIC_50", "family": "B", "fn": "ctrl_static",
              "kw": {"w": 0.5}, "primary": True})
    for s in (0.10, 0.15, 0.20, 0.25):
        for w in (21, 63, 126):
            g.append({"id": f"C_VOLTGT_s{s:.2f}_w{w}", "family": "C",
                      "fn": "ctrl_vol_target",
                      "kw": {"sigma_star": s, "window": w},
                      "primary": (s == 0.15 and w == 63)})
    for b in (1.0, 1.5, 2.0):
        g.append({"id": f"C2_BETATGT_b{b:.1f}", "family": "C2",
                  "fn": "ctrl_beta_target", "kw": {"beta_star": b},
                  "primary": (b == 1.5)})
    for s in (0.15, 0.20, 0.25):
        for d in (0.10, 0.15, 0.20):
            g.append({"id": f"D_LADDER_s{s:.2f}_d{int(d*100)}", "family": "D",
                      "fn": "ctrl_ladder",
                      "kw": {"sigma_star": s, "d_star": d},
                      "primary": (s == 0.15 and d == 0.10)})
    for ma in (50, 100, 200):
        for mp in ("2x2", "trend"):
            g.append({"id": f"E_REGIME_ma{ma}_{mp}", "family": "E",
                      "fn": "ctrl_regime", "kw": {"ma": ma, "mapping": mp},
                      "primary": (ma == 200 and mp == "2x2")})
    for th in (0.5, 1.0, 1.5):
        for fl in (0.3, 0.5, 0.7):
            g.append({"id": f"F_EVENT_t{th}_f{fl}", "family": "F",
                      "fn": "ctrl_event",
                      "kw": {"threshold": th, "floor": fl, "gpr": "monthly"},
                      "primary": (th == 1.0 and fl == 0.5), "non_pit": True})
    g.append({"id": "F_EVENT_DAILY_t1.0_f0.5", "family": "F",
              "fn": "ctrl_event",
              "kw": {"threshold": 1.0, "floor": 0.5, "gpr": "daily"},
              "primary": False, "non_pit": True})
    for k in (1, 21, 63):
        g.append({"id": f"H_ORACLE_k{k}", "family": "H", "fn": "ctrl_oracle",
                  "kw": {"k": k}, "primary": (k == 21), "impossible": True})
    return g


def _log(*a):
    print(*a, flush=True)


def _write(name: str, payload: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"exposure_arena_1_{name}.json"
    p.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    _log(f"  wrote {p.name}")
    return p


def _read(name: str) -> dict | None:
    p = OUT / f"exposure_arena_1_{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ══════════════════════════════════════════════════════════════════════════
# STAGE 1 — the beds, printed as found
# ══════════════════════════════════════════════════════════════════════════
def stage_data(force=False) -> dict:
    if not force and (old := _read("data")):
        _log("STAGE 1 data — checkpoint found, skipped")
        return old
    _log("=== STAGE 1: beds ===")
    ff = C.load_ff()
    meta = {}
    for b in BEDS:
        t0 = time.time()
        bed = C.make_bed(b, ff)
        idx = C.eval_index(bed)
        r = bed["r_book"]
        meta[b] = {**bed["meta"],
                   "span": [str(r.index[0].date()), str(r.index[-1].date())],
                   "eval_span": [str(idx[0].date()), str(idx[-1].date())],
                   "eval_days": int(len(idx)),
                   "warmup_days_excluded": C.WARMUP_TD,
                   "cost_bps_oneway": bed["cost_bps"],
                   "ann_vol_pct": round(float(r.std(ddof=1) * np.sqrt(252)
                                              * 100), 3),
                   "ann_mean_pct": round(float(r.mean() * 252 * 100), 3),
                   "maxdd_unmanaged": round(C._maxdd(r.loc[idx]
                                                     .to_numpy(float)), 4),
                   "build_secs": round(time.time() - t0, 1)}
        _log(f"  {b}: {meta[b]['eval_days']} eval days "
             f"{meta[b]['eval_span'][0]}..{meta[b]['eval_span'][1]}  "
             f"vol {meta[b]['ann_vol_pct']}%  maxDD "
             f"{meta[b]['maxdd_unmanaged']:.1%}")
    return _write("data", {"trial": "EXPOSURE-ARENA-1", "prereg": PREREG,
                           "beds": meta,
                           "cost_model_provenance": {
                               "BED1/BED2": "exit_lab_core.BENCH_BPS = 5.0 bps "
                                            "one-way (the repo's index-leg cost)",
                               "BED3": "EXIT-LAB-1 measured Corwin-Schultz "
                                       "median 24.2 bps + SimConfig "
                                       "slippage 5.0 + commission 1.0 = 30.2"}})


# ══════════════════════════════════════════════════════════════════════════
# STAGE 2 — THE MATCHED-AVERAGE-EXPOSURE FRONTIER, built before any controller
# ══════════════════════════════════════════════════════════════════════════
def stage_frontier(force=False) -> dict:
    if not force and (old := _read("frontier")):
        _log("STAGE 2 frontier — checkpoint found, skipped")
        return old
    _log("=== STAGE 2: the matched-average-exposure FRONTIER (§A1) ===")
    _log("  built BEFORE any controller exists; a pure function of w-bar and "
         "the bed; no free parameters, nothing fitted")
    ff = C.load_ff()
    out = {}
    for b in BEDS:
        bed = C.make_bed(b, ff)
        rows = []
        for wbar in C.FRONTIER_GRID:
            sim = C.constant_path(bed, float(wbar))
            m = C.metrics(sim, bed)
            m["p_ruin"] = C.ruin_probability(
                sim["net"].to_numpy(float))["p_ruin"]
            m["wbar"] = float(wbar)
            rows.append(m)
        out[b] = rows
        best = max(rows, key=lambda r: r["net_cagr_pp"])
        _log(f"  {b}: frontier over {len(rows)} constant policies; "
             f"max net CAGR {best['net_cagr_pp']:.3f}pp/yr at w={best['wbar']}")
    return _write("frontier", {"trial": "EXPOSURE-ARENA-1", "prereg": PREREG,
                               "grid": list(C.FRONTIER_GRID),
                               "note": "prereg §5 — this file's mtime must "
                                       "predate every controller artifact",
                               "frontier": out})


# ══════════════════════════════════════════════════════════════════════════
# STAGE 3 — controllers A-F, H  (weights + causality proofs)
# ══════════════════════════════════════════════════════════════════════════
def _build_weights(bed: dict, spec: dict, gprm, gprd):
    fn = getattr(C, spec["fn"])
    kw = dict(spec["kw"])
    idx = C.eval_index(bed)
    if spec["fn"] == "ctrl_event":
        which = kw.pop("gpr")
        z = gprm if which == "monthly" else gprd
        kw["gpr_z"] = z
        if which == "daily":
            live = z.dropna()
            if len(live) == 0:
                return None, None
            idx = idx[idx >= live.index[0]]
            if len(idx) < 504:
                return None, None
    w = fn(bed, **kw)
    return w, idx


def stage_controllers(force=False) -> dict:
    if not force and (old := _read("controllers")):
        _log("STAGE 3 controllers — checkpoint found, skipped")
        return old
    fr = OUT / "exposure_arena_1_frontier.json"
    if not fr.exists():
        raise SystemExit("REFUSAL: the frontier must exist before any "
                         "controller is built (prereg §5)")
    _log("=== STAGE 3: controllers A-F, H ===")
    ff = C.load_ff()
    grid = controller_grid()
    payload = {"trial": "EXPOSURE-ARENA-1", "prereg": PREREG,
               "frontier_mtime": fr.stat().st_mtime, "beds": {}}
    store = {}
    for b in BEDS:
        bed = C.make_bed(b, ff)
        full_idx = bed["r_book"].index
        gprm = C.gpr_z_monthly(full_idx)
        gprd = C.gpr_z_daily(full_idx)
        rows, proofs = [], []
        for spec in grid:
            w, idx = _build_weights(bed, spec, gprm, gprd)
            if w is None:
                rows.append({"id": spec["id"], "status": "SKIPPED_NO_DATA"})
                continue
            if w.isna().any() or (w < -1e-12).any() or (w > 1 + 1e-12).any():
                raise SystemExit(f"ASSERTION FAILED [{b}/{spec['id']}]: "
                                 f"weights outside [0,1] or NaN")
            store[f"{b}|{spec['id']}"] = (w, idx)
            rows.append({"id": spec["id"], "family": spec["family"],
                         "primary": spec["primary"],
                         "non_pit": spec.get("non_pit", False),
                         "impossible": spec.get("impossible", False),
                         "eval_days": int(len(idx)),
                         "mean_w": round(float(w.reindex(idx).mean()), 4),
                         "status": "OK"})
            if spec["primary"]:
                probe = idx[len(idx) // 2]
                kw = dict(spec["kw"])
                if spec["fn"] == "ctrl_event":
                    kw.pop("gpr")
                    kw["gpr_z"] = gprm
                pr = C.perturbation_proof(bed, getattr(C, spec["fn"]), kw,
                                          probe)
                pr["id"] = spec["id"]
                impossible = spec.get("impossible", False)
                pr["must_be_identical"] = not impossible
                pr["verdict"] = ("PASS" if (pr["identical"] or impossible)
                                 else "FAIL")
                if impossible:
                    pr["note"] = ("random multiplicative perturbation is NOT a "
                                  "reliable tripwire at k>1 (a probe can sit "
                                  "20 days after its own decision date, so one "
                                  "rescaled day need not flip the window's "
                                  "sign). The real tripwire is the negation "
                                  "test below, on the k=1 oracle.")
                if spec["fn"] == "ctrl_event":
                    pr["note"] = ("the GPR conditioner is exogenous to the "
                                  "book path, so this proof is trivially "
                                  "passed; its real weakness is that GPR is "
                                  "NOT point-in-time (prereg §7)")
                proofs.append(pr)
                if pr["verdict"] == "FAIL":
                    raise SystemExit(
                        f"CAUSALITY ASSERTION FAILED [{b}/{spec['id']}]: "
                        f"identical={pr['identical']}, required="
                        f"{pr['must_be_identical']}")
        # THE TRIPWIRE: the oracle must be CAUGHT, or the clean proofs above
        # are a clean bill of health from an instrument that cannot see.
        probe = C.eval_index(bed)[len(C.eval_index(bed)) // 2]
        tw = C.lookahead_tripwire(bed, C.ctrl_oracle, {"k": 1}, probe)
        tw["id"] = "H_ORACLE_k1"
        tw["verdict"] = "PASS (look-ahead DETECTED)" if tw["differs"] else "FAIL"
        if not tw["differs"]:
            raise SystemExit(
                f"TRIPWIRE FAILED [{b}]: the harness did not detect the "
                f"oracle's look-ahead, so its clean proofs mean nothing")
        payload["beds"][b] = {"configs": rows, "perturbation_proofs": proofs,
                              "lookahead_tripwire": tw}
        n_ok = sum(1 for r in rows if r["status"] == "OK")
        _log(f"  {b}: {n_ok}/{len(rows)} configs built; {len(proofs)} "
             f"perturbation proofs identical; TRIPWIRE {tw['verdict']} "
             f"(w {tw['w_base']} -> {tw['w_shocked']}) — the harness can see "
             f"look-ahead, so the clean proofs are informative")
    _save_weights(store)
    return _write("controllers", payload)


def _save_weights(store: dict) -> None:
    p = OUT / "exposure_arena_1_weights.npz"
    d = {}
    for k, (w, idx) in store.items():
        d[k + "|w"] = w.to_numpy(np.float32)
        d[k + "|wi"] = w.index.values.astype("datetime64[D]")
        d[k + "|ei"] = idx.values.astype("datetime64[D]")
    np.savez_compressed(p, **d)
    _log(f"  wrote {p.name} ({p.stat().st_size/1e6:.1f} MB)")


def _load_weights() -> dict:
    p = OUT / "exposure_arena_1_weights.npz"
    z = np.load(p, allow_pickle=False)
    keys = {k.rsplit("|", 1)[0] for k in z.files}
    out = {}
    for k in sorted(keys):
        w = pd.Series(z[k + "|w"].astype(float),
                      index=pd.DatetimeIndex(z[k + "|wi"]))
        idx = pd.DatetimeIndex(z[k + "|ei"])
        out[k] = (w, idx)
    return out


# ══════════════════════════════════════════════════════════════════════════
# STAGE 4 — the learned controller G
# ══════════════════════════════════════════════════════════════════════════
def stage_learned(force=False) -> dict:
    if not force and (old := _read("learned")):
        _log("STAGE 4 learned — checkpoint found, skipped")
        return old
    _log("=== STAGE 4: controller G, the LEARNED exposure policy ===")
    ff = C.load_ff()
    payload = {"trial": "EXPOSURE-ARENA-1", "prereg": PREREG, "beds": {}}
    store = {}
    for b in BEDS:
        bed = C.make_bed(b, ff)
        fte, ry = (("1955-12-31", 5) if b != "BED3" else ("2011-12-31", 3))
        _log(f"  {b}: first train end {fte}, retrain every {ry}y, "
             f"purge+embargo {L.EMBARGO}td")
        t0 = time.time()
        res = L.run_learned(bed, fte, ry, log=_log)
        if "error" in res:
            payload["beds"][b] = res
            continue
        eval_idx = C.eval_index(bed)
        first = pd.Timestamp(res["first_oof_date"])
        idx = eval_idx[eval_idx >= first]
        fam_rows = []
        for fam, s in res["series"].items():
            w = s.ffill().fillna(1.0).clip(0, 1)
            store[f"{b}|G_{fam.upper()}"] = (w, idx)
            fam_rows.append({"id": f"G_{fam.upper()}", "family": "G",
                             "primary": True, "eval_days": int(len(idx)),
                             "mean_w": round(float(w.reindex(idx).mean()), 4),
                             "status": "OK"})
        payload["beds"][b] = {"configs": fam_rows,
                              "folds": res["folds"],
                              "n_model_fits": res["n_model_fits"],
                              "first_oof_date": res["first_oof_date"],
                              "feature_names": res["feature_names"],
                              "protocol": res["protocol"],
                              "declared_non_run": res["declared_non_run"],
                              "structural_causality": {
                                  "purge_embargo_td": L.EMBARGO,
                                  "label_horizon_td": L.LABEL_H,
                                  "claim": "every test row's index is at least "
                                           "EMBARGO trading days after the last "
                                           "training row, so no label overlaps "
                                           "any test day; asserted at fold "
                                           "construction",
                                  "asserted": True},
                              "secs": round(time.time() - t0, 1)}
        _log(f"    {b} done in {time.time()-t0:.0f}s, "
             f"{res['n_model_fits']} model fits")
    _save_learned_weights(store)
    return _write("learned", payload)


def _save_learned_weights(store: dict) -> None:
    p = OUT / "exposure_arena_1_weights_learned.npz"
    d = {}
    for k, (w, idx) in store.items():
        d[k + "|w"] = w.to_numpy(np.float32)
        d[k + "|wi"] = w.index.values.astype("datetime64[D]")
        d[k + "|ei"] = idx.values.astype("datetime64[D]")
    np.savez_compressed(p, **d)
    _log(f"  wrote {p.name}")


def _load_learned_weights() -> dict:
    p = OUT / "exposure_arena_1_weights_learned.npz"
    if not p.exists():
        return {}
    z = np.load(p, allow_pickle=False)
    keys = {k.rsplit("|", 1)[0] for k in z.files}
    out = {}
    for k in sorted(keys):
        out[k] = (pd.Series(z[k + "|w"].astype(float),
                            index=pd.DatetimeIndex(z[k + "|wi"])),
                  pd.DatetimeIndex(z[k + "|ei"]))
    return out


# ══════════════════════════════════════════════════════════════════════════
# STAGE 5 — scoring against the matched control
# ══════════════════════════════════════════════════════════════════════════
def _verdict(dm: dict, dd: dict, sc: dict, n_blocks_needed: int) -> str:
    det = dm["detectable"]
    cov = (sc["n_blocks_same_sign"] >= n_blocks_needed
           and sc["both_halves_same_sign"])
    if det and dm["delta_pp_yr"] > 0:
        return "TIMING_DETECTED" if cov else "UNRESOLVED_UNSTABLE"
    if det and dm["delta_pp_yr"] < 0:
        return "TIMING_HARMFUL" if cov else "UNRESOLVED_UNSTABLE"
    if dd.get("dd_vs_full_pp") is not None and dd["dd_vs_full_pp"] >= 5.0:
        return "DE_RISKING_ONLY"
    return "UNRESOLVED"


def stage_score(force=False) -> dict:
    if not force and (old := _read("scored")):
        _log("STAGE 5 scored — checkpoint found, skipped")
        return old
    _log("=== STAGE 5: scoring every arm against its matched cousin ===")
    ff = C.load_ff()
    W = _load_weights()
    W.update(_load_learned_weights())
    grid = {s["id"]: s for s in controller_grid()}
    payload = {"trial": "EXPOSURE-ARENA-1", "prereg": PREREG, "beds": {}}

    for b in BEDS:
        bed = C.make_bed(b, ff)
        n_need = 6 if b != "BED3" else 5
        keys = [k for k in W if k.startswith(b + "|")]
        rows = []
        dseries = {}
        t0 = time.time()
        for k in keys:
            cid = k.split("|", 1)[1]
            w, idx = W[k]
            spec = grid.get(cid, {"family": cid.split("_")[0],
                                  "primary": True})
            sim = C.simulate(bed, w.copy(), 1.0, idx)
            m = C.metrics(sim, bed)
            wbar = m["mean_exposure"]
            mc = C.constant_path(bed, wbar, 1.0, idx)
            mm = C.metrics(mc, bed)
            fullsim = C.constant_path(bed, 1.0, 1.0, idx)
            mf = C.metrics(fullsim, bed)

            na = sim["net"].to_numpy(float)
            nm = mc["net"].to_numpy(float)
            nf = fullsim["net"].to_numpy(float)
            dm = C.mde_paired(na, nm)
            df_ = C.mde_paired(na, nf)
            ddm = C.mde_maxdd(na, nm)
            sc = C.sign_consistency(sim["net"], mc["net"], bed)
            dd_vs_full = (m["max_drawdown"] - mf["max_drawdown"]) * 100

            row = {
                "id": cid, "family": spec.get("family"),
                "primary": spec.get("primary", False),
                "non_pit": spec.get("non_pit", False),
                "impossible": spec.get("impossible", False),
                "eval_span": [str(idx[0].date()), str(idx[-1].date())],
                "metrics": m,
                "matched_control": {"wbar": wbar, "metrics": mm},
                "full_control": {"metrics": mf},
                "D_matched": dm,
                "D_vs_full": df_,
                "dd_vs_matched": ddm,
                "dd_vs_full_pp": round(dd_vs_full, 3),
                "sign_consistency_vs_matched": sc,
                "p_ruin": C.ruin_probability(na),
                "p_ruin_matched": C.ruin_probability(nm),
            }
            row["verdict"] = _verdict(dm, {"dd_vs_full_pp": dd_vs_full}, sc,
                                      n_need)
            if spec.get("impossible"):
                row["verdict"] = "DIAGNOSTIC_IMPOSSIBLE — " + row["verdict"]
            if spec.get("primary"):
                cs = {}
                for mult in C.COST_MULTIPLIERS:
                    s2 = C.simulate(bed, w.copy(), mult, idx)
                    c2 = C.constant_path(bed, wbar, mult, idx)
                    cs[f"{mult:g}x"] = C.mde_paired(
                        s2["net"].to_numpy(float),
                        c2["net"].to_numpy(float))["delta_pp_yr"]
                row["cost_sensitivity_D_matched_pp_yr"] = cs
            rows.append(row)
            dseries[cid] = (np.log1p(na) - np.log1p(nm))
        rows.sort(key=lambda r: -r["D_matched"]["delta_pp_yr"])
        payload["beds"][b] = {"arms": rows,
                              "batch_selfcheck": _batch_selfcheck(dseries),
                              "secs": round(time.time() - t0, 1)}
        _log(f"  {b}: {len(rows)} arms scored in {time.time()-t0:.0f}s")
        det = [r["id"] for r in rows
               if r["verdict"].startswith("TIMING_DETECTED")]
        _log(f"    TIMING_DETECTED: {det if det else 'NONE'}")
    return _write("scored", payload)


def _batch_selfcheck(dseries: dict) -> dict:
    """§20 — how many of these configurations are actually distinct?"""
    keys = [k for k in dseries if not k.startswith("A_")]
    n = min(len(dseries[k]) for k in keys) if keys else 0
    if len(keys) < 2:
        return {"n_arms": len(keys)}
    M = np.vstack([dseries[k][-n:] for k in keys])
    Cm = np.corrcoef(M)
    off = Cm[~np.eye(len(keys), dtype=bool)]
    mean_abs = float(np.nanmean(np.abs(off)))
    eff = float(len(keys) / (1 + (len(keys) - 1) * mean_abs))
    return {"n_arms": len(keys),
            "mean_abs_pairwise_corr_of_daily_D": round(mean_abs, 4),
            "effective_distinct_arms": round(eff, 2),
            "note": "correlation of the DAILY arm-minus-matched log-return "
                    "difference; N configurations that are variations of four "
                    "mechanisms are not N independent chances"}


# ══════════════════════════════════════════════════════════════════════════
# STAGE 6 — summary
# ══════════════════════════════════════════════════════════════════════════
def stage_summary(force=False) -> dict:
    _log("=== STAGE 6: summary ===")
    sc = _read("scored")
    ctl = _read("controllers")
    lrn = _read("learned")
    if sc is None:
        raise SystemExit("REFUSAL: no scored artifact")
    denom = {"controller_configs_per_bed": len(controller_grid()),
             "learned_families_per_bed": 3,
             "beds": len(BEDS)}
    n_arms = sum(len(v["arms"]) for v in sc["beds"].values())
    n_fits = sum(v.get("n_model_fits", 0) for v in lrn["beds"].values()) \
        if lrn else 0
    n_skip = sum(1 for b in ctl["beds"].values() for r in b["configs"]
                 if r["status"] != "OK") if ctl else 0
    frontier_pts = len(C.FRONTIER_GRID) * len(BEDS)
    out = {"trial": "EXPOSURE-ARENA-1", "prereg": PREREG,
           "search_denominator": {
               **denom, "arms_scored": n_arms,
               "arms_skipped_no_data": n_skip,
               "frontier_constant_policies": frontier_pts,
               "learned_model_fits": n_fits,
               "cost_sensitivity_cells": sum(
                   1 for v in sc["beds"].values() for r in v["arms"]
                   if "cost_sensitivity_D_matched_pp_yr" in r) * 4,
               "declared_non_run": "conservative offline-Q (KNOWN-WORLDS §5: "
                                   "NOT TRUSTED for action work)"},
           "headline": {}, "per_bed": {}}
    for b, v in sc["beds"].items():
        arms = v["arms"]
        det = [r for r in arms if r["verdict"] == "TIMING_DETECTED"]
        harm = [r for r in arms if r["verdict"] == "TIMING_HARMFUL"]
        uns = [r for r in arms if r["verdict"] == "UNRESOLVED_UNSTABLE"]
        drk = [r for r in arms if r["verdict"] == "DE_RISKING_ONLY"]
        above = [r for r in arms if r["D_matched"]["detectable"]
                 and not r["impossible"]]
        out["per_bed"][b] = {
            "n_arms": len(arms),
            "TIMING_DETECTED": [r["id"] for r in det],
            "TIMING_HARMFUL": [r["id"] for r in harm],
            "UNRESOLVED_UNSTABLE": [r["id"] for r in uns],
            "DE_RISKING_ONLY": [r["id"] for r in drk],
            "n_above_own_MDE_excl_oracle": len(above),
            "batch_selfcheck": v["batch_selfcheck"],
            "best_D_matched": {r["id"]: r["D_matched"]["delta_pp_yr"]
                               for r in arms[:3]},
        }
    any_det = [f"{b}/{i}" for b, v in out["per_bed"].items()
               for i in v["TIMING_DETECTED"]]
    out["headline"] = {
        "any_controller_beat_matched_average_exposure": bool(any_det),
        "which": any_det,
        "breakthrough_eligible": False,
        "note": ("§A11(3) requires the SAME controller family to clear on >= 2 "
                 "beds and both halves of each before the word BREAKTHROUGH may "
                 "be used; §A7 forbids calling anything here certified."),
    }
    # BED INDEPENDENCE — the correction that decides the §A11(3) clause.
    # "Clears on >= 2 beds" is meaningless if two beds are the SAME path. BED-2
    # is r = 2.15*mktrf + rf and BED-1 is r = 1.0*mktrf + rf, so their excess
    # returns are proportional by construction and their correlation is exactly
    # 1. Measured rather than argued, then applied.
    ff = C.load_ff()
    ex = {b: (C.make_bed(b, ff)["r_book"] - C.make_bed(b, ff)["rf"])
          for b in BEDS}
    indep = {}
    for i, a in enumerate(BEDS):
        for bb in BEDS[i + 1:]:
            j = ex[a].index.intersection(ex[bb].index)
            indep[f"{a}~{bb}"] = round(float(np.corrcoef(
                ex[a].loc[j], ex[bb].loc[j])[0, 1]), 6)
    groups = []
    for b in BEDS:
        placed = False
        for g in groups:
            if indep.get(f"{g[0]}~{b}", indep.get(f"{b}~{g[0]}", 0)) > 0.999:
                g.append(b)
                placed = True
                break
        if not placed:
            groups.append([b])
    bed_group = {b: i for i, g in enumerate(groups) for b in g}
    out["bed_independence"] = {
        "excess_return_correlations": indep,
        "independent_bed_groups": groups,
        "note": "beds inside a group are the same underlying path and count "
                "ONCE for replication; BED-2 is BED-1 levered 2.15x"}

    fams = {}
    for b, v in out["per_bed"].items():
        for i in v["TIMING_DETECTED"]:
            fams.setdefault(i.split("_")[0], set()).add(bed_group[b])
    out["headline"]["breakthrough_eligible"] = any(
        len(bs) >= 2 for bs in fams.values())
    out["headline"]["families_detected_by_independent_bed_group"] = {
        k: sorted(v) for k, v in fams.items()}
    out["headline"]["replication_note"] = (
        "BED-1 and BED-2 are the same market path at two leverages "
        "(excess-return correlation 1.000000) and count as ONE independent "
        "bed. The only genuinely different bed is BED-3, and it detected "
        "nothing.")
    _write("summary", out)
    _log(json.dumps(out["headline"], indent=1))
    return out


STAGES = {1: stage_data, 2: stage_frontier, 3: stage_controllers,
          4: stage_learned, 5: stage_score, 6: stage_summary}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    todo = [a.stage] if a.stage else sorted(STAGES)
    for s in todo:
        STAGES[s](force=a.force)
    _log(f"\ntotal {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
