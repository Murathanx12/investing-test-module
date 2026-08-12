"""REGIME-ARENA-1 — GRAND-ARENA-1 chunk 5. The runner.

Pre-registered `TRIALS/PREREG_REGIME_ARENA_1.md` at commit 9e5dd09, BEFORE any
runner file existed.

THE QUESTION, AND THE ONE THING THAT MAKES IT ANSWERABLE
========================================================
Chunk 6 tested a regime rule as an EXPOSURE dial and refused it. This runner
never varies exposure: gross is 1.00 in every scored arm and stage `sim`
verifies it per arm rather than asserting it. What varies is whether a
CROSS-SECTIONAL decision — which names (D1), which signal weights (D2), which
risk model (D3) — is made from the whole realised past or only from the part of
the past that carried the current state label.

Every conditioned arm therefore has an exact twin: the identical machinery with
the state label deleted (`S_NONE`). That twin is the control, always. "Regime-
conditioned X beats regime-conditioned nothing" is never computed here.

    python -m scripts.run_regime_arena_1 --stage all

Stages, each writing its own artifact to data/factory/regime_arena_1_*.json:
    states  — bed, option sets, fourteen label sequences
    proof   — the no-lookahead perturbation proof AND the two tripwire arms
    sim     — every simulated path (primary grid, costs, placebo seeds, matched)
    score   — D_cond vs the unconditional twin, with each arm's own MDE
    summary — search denominator, §20 self-check, CSCV/PBO, family DSR
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

from scripts import arena_core as A                            # noqa: E402
from scripts import regime_arena_core as R                     # noqa: E402
from scripts.pf7_deflated_sharpe import (deflated_sharpe,      # noqa: E402
                                         expected_max_sr)

OUT = Path(__file__).resolve().parents[1] / "data" / "factory"
PREREG = "TRIALS/PREREG_REGIME_ARENA_1.md @ 9e5dd09"
LOG = OUT / "regime_arena_1.log"

FAMILIES = ("D1_SELECTION", "D2_WEIGHTING", "D3_RISKMODEL")
PROBES = (100, 144, 200)
CSCV_S = 8
N_LADDER = (1, 5, 10, 25, 42, 100, 333, 1000)


def _log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _write(name: str, payload: dict) -> dict:
    p = OUT / f"regime_arena_1_{name}.json"
    p.write_text(json.dumps(payload, indent=1, default=_json_default),
                 encoding="utf-8")
    _log(f"wrote {p.name} ({p.stat().st_size/1024:.0f} KB)")
    return payload


def _read(name: str) -> dict | None:
    p = OUT / f"regime_arena_1_{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


# ══════════════════════════════════════════════════════════════════════════
# STAGE 1 — the bed, the option sets, the states
# ══════════════════════════════════════════════════════════════════════════
_CACHE: dict = {}


def build_world(force: bool = False) -> dict:
    if _CACHE and not force:
        return _CACHE
    t0 = time.time()
    panel, mkt, yc = R.load_frames()
    bed = R.load_bed(panel, mkt)
    feats = R.state_features(bed)
    opts = R.precompute_options(bed)
    states = R.build_states(bed, feats, opts, yc_raw=yc)
    _CACHE.update({"bed": bed, "feats": feats, "opts": opts, "states": states,
                   "yc": yc})
    _log(f"world built in {time.time()-t0:.0f}s "
         f"({len(bed['dates_k'])} dates, {len(states)} states)")
    return _CACHE


def stage_states() -> dict:
    _log("=== STAGE 1: states ===")
    w = build_world()
    bed, states = w["bed"], w["states"]
    years = bed["dates"].year.to_numpy()
    ev = np.arange(len(bed["dates_k"])) >= R.BURN_IN
    rows = {}
    for sid, lab in states.items():
        counts = np.bincount(lab).tolist()
        # persistence: P(label unchanged month to month) over the eval window
        chg = float(np.mean(lab[R.BURN_IN:] != lab[R.BURN_IN - 1:-1]))
        rows[sid] = {
            "class": R.STATE_CLASS[sid],
            "n_states": int(lab.max() + 1),
            "counts_full": counts,
            "counts_eval": np.bincount(lab[ev],
                                       minlength=len(counts)).tolist(),
            "switch_rate_eval": round(chg, 4),
            "min_state_share_eval": round(float(
                np.bincount(lab[ev], minlength=len(counts)).min()
                / int(ev.sum())), 4),
        }
    payload = {"trial": "REGIME-ARENA-1", "prereg": PREREG,
               "n_dates": len(bed["dates_k"]),
               "eval_dates": int(ev.sum()),
               "eval_span": [str(bed["dates"][R.BURN_IN].date()),
                             str(bed["dates"][-1].date())],
               "span": [str(bed["dates"][0].date()),
                        str(bed["dates"][-1].date())],
               "years": years.tolist(),
               "states": rows}
    return _write("states", payload)


# ══════════════════════════════════════════════════════════════════════════
# the simulator — ONE path builder for every arm
# ══════════════════════════════════════════════════════════════════════════
def frozen_default(w: dict, k: int, K: int):
    """The pre-rotation portfolio: EW on the equal-weight composite top-K."""
    sel = w["opts"]["comp_idx"][K][k]
    return sel, R._ew(len(sel))


def choose(family: str, w: dict, labels: np.ndarray, k: int, K: int):
    """(selection indices, weights, option-id, how) at one decision date."""
    opts = w["opts"]
    if family == "D1_SELECTION":
        j, how = R.conditioned_choice(labels, opts["sel_ret"][K], k)
        if j is None:
            sel, wt = frozen_default(w, k, K)
            return sel, wt, "DEFAULT", how
        sel = opts["sel_idx"][K][(k, j)]
        return sel, R._ew(len(sel)), R.SIG_IDS[j], how
    if family == "D2_WEIGHTING":
        bw, how = R.conditioned_blend(labels, opts["ic"], k)
        if bw is None:
            sel, wt = frozen_default(w, k, K)
            return sel, wt, "DEFAULT", how
        comp = w["bed"]["Z"][k] @ bw
        sel = R._pick(comp, K)
        return sel, R._ew(len(sel)), "|".join(f"{v:.3f}" for v in bw), how
    if family == "D3_RISKMODEL":
        j, how = R.conditioned_choice(labels, opts["risk_ret"][K], k)
        sel = opts["comp_idx"][K][k]
        if j is None:
            return sel, R._ew(len(sel)), "DEFAULT", how
        return sel, opts["risk_w"][K][(k, j)], R.RISK_IDS[j], how
    raise ValueError(family)


def simulate(w: dict, family: str, labels: np.ndarray, K: int = R.K_PRIMARY,
             cost_mult: float = 1.0, scale_path: np.ndarray | None = None,
             turnover_budget: float | None = None) -> dict:
    """One arm's wealth path plus the diagnostics every verdict needs.

    `scale_path` is the §A3 cash blend used ONLY by the matched variants; it is
    None for every primary arm, which is how gross stays pinned at 1.00.
    """
    bed = w["bed"]
    book = A.Book(cost_mult=cost_mult)
    mktf = bed["mkt"]
    choices, hows, beta_p, vol_p = [], [], [], []
    for i, k in enumerate(bed["dates_k"]):
        d = bed["by_date"][k]
        sel, wt, oid, how = choose(family, w, labels, k, K)
        idx = d.index[sel]
        target = pd.Series(np.asarray(wt, dtype=float), index=idx)
        target = target[target > 0]
        if turnover_budget is not None:
            target = A.partial_rebalance(target, book.w, turnover_budget)
        b = pd.to_numeric(d["beta_252"], errors="coerce").reindex(
            target.index).fillna(1.0).to_numpy(float)
        iv = pd.to_numeric(d["ivol_252"], errors="coerce").reindex(
            target.index).to_numpy(float)
        iv = np.where(np.isfinite(iv), iv, np.nanmedian(iv) if
                      np.isfinite(iv).any() else 0.3)
        tw = target.to_numpy(float)
        mv = float(mktf.loc[k, "mkt_vol_252"]) ** 2
        bp = float(tw @ b)
        vp = float(np.sqrt(max(bp ** 2 * mv + float((tw ** 2) @ (iv ** 2)),
                               0.0)))
        s = 1.0 if scale_path is None else float(scale_path[i])
        book.step(k, target, s,
                  ret=pd.to_numeric(d["fwd_ret_1m"], errors="coerce"),
                  hs_bps=pd.to_numeric(d["hs_bps"], errors="coerce"),
                  sig_d=pd.to_numeric(d["vol_252"], errors="coerce")
                  / np.sqrt(252.0),
                  adv=pd.to_numeric(d["adv"], errors="coerce"),
                  price=pd.to_numeric(d["price"], errors="coerce"),
                  r_cash=float(mktf.loc[k, "cash_fwd_1m"]))
        choices.append(oid)
        hows.append(how)
        beta_p.append(bp * s)
        vol_p.append(vp * s)
    f = book.frame()
    f["choice"] = choices
    f["how"] = hows
    f["beta_exante"] = beta_p
    f["vol_exante"] = vol_p
    return {"frame": f, "book": book}


def eval_slice(f: pd.DataFrame) -> pd.DataFrame:
    return f[f["date_ix"] >= R.BURN_IN].reset_index(drop=True)


def arm_metrics(f: pd.DataFrame) -> dict:
    e = eval_slice(f)
    n = e["net"].to_numpy(float)
    return {
        "n_months": len(e),
        "net_cagr_pp": round(A.cagr(n) * 100, 4),
        "net_mean_ann_pp": round(float(np.nanmean(n)) * 12 * 100, 4),
        "vol_ann_pct": round(float(np.nanstd(n, ddof=1)) * np.sqrt(12) * 100, 3),
        "max_drawdown": round(A.max_drawdown(n), 4),
        "gross_exposure_mean": round(float(e["gross_exposure"].mean()), 6),
        "gross_exposure_min": round(float(e["gross_exposure"].min()), 6),
        "gross_exposure_max": round(float(e["gross_exposure"].max()), 6),
        "eff_n_mean": round(float(e["eff_n"].mean()), 3),
        "turnover_oneway_yr": round(float(e["turnover_1way"].mean()) * 12, 4),
        "costs_bps_yr": round(float(e["cost"].mean()) * 12 * 1e4, 2),
        "beta_exante_mean": round(float(e["beta_exante"].mean()), 4),
        "vol_exante_mean": round(float(e["vol_exante"].mean()), 4),
        "conditioned_rate": round(float((e["how"] == "conditioned").mean()), 4),
        "fallback_uncond_rate": round(
            float((e["how"] == "fallback_uncond").mean()), 4),
        "fallback_default_rate": round(
            float((e["how"] == "fallback_default").mean()), 4),
        "n_distinct_choices": int(e["choice"].nunique()),
        "choice_switch_rate": round(
            float((e["choice"].to_numpy()[1:]
                   != e["choice"].to_numpy()[:-1]).mean()), 4),
    }


# ══════════════════════════════════════════════════════════════════════════
# STAGE 2 — the no-lookahead proof, and the two arms it MUST catch
# ══════════════════════════════════════════════════════════════════════════
def _sgn(rng, n: int, mode: int, scale: float = 1.0) -> np.ndarray:
    """Corruption draw. mode +1 forces positive, -1 negative, 0 is free.

    Forward returns need BOTH signs across the draw family. With a free draw
    only, `S_ORACLE2` — a label that is literally the sign of next month's
    market return — survived corruption at 8 of 9 probe/draw cells, because
    N(0.5,1) is positive 69% of the time and the true label was already 1. A
    tripwire whose firing depends on the corruption happening to land on the
    other side is not a tripwire; the draw family was rebuilt to span the sign.
    """
    v = rng.normal(0.5, 1.0, n) * scale
    if mode > 0:
        return np.abs(v) + scale
    if mode < 0:
        return -np.abs(v) - scale
    return v


def _corrupt(panel: pd.DataFrame, mkt: pd.DataFrame, yc: pd.Series,
             probe: int, dates: pd.DatetimeIndex, rng, mode: int = 0) -> tuple:
    """Garbage into every cell OBSERVED strictly after the probe date.

    `fwd_ret_1m` and `mkt_fwd_1m` AT the probe are included: month k's forward
    return is realised at k+1, so it is a future observation at k. A decision
    made at the probe that moves when they move is reading the future.
    """
    p, m = panel.copy(), mkt.copy()
    feat_cols = [c for c in p.columns if c not in ("date_ix", "permno", "col",
                                                   "ff12", "h_days")]
    after = p["date_ix"].to_numpy() > probe
    at_or_after = p["date_ix"].to_numpy() >= probe
    for c in feat_cols:
        mask = at_or_after if c == "fwd_ret_1m" else after
        vals = (_sgn(rng, int(mask.sum()), mode) if c == "fwd_ret_1m"
                else rng.normal(0.5, 1.0, int(mask.sum())))
        if c in ("price", "mcap", "adv"):
            vals = np.abs(vals) * 1e6 + 1e6
        if c == "hs_bps":
            vals = np.abs(vals) * 1e3
        p.loc[mask, c] = vals
    mk_after = m["date_ix"].to_numpy() > probe
    mk_at = m["date_ix"].to_numpy() >= probe
    # market state features are corrupted by THREE ORDERS OF MAGNITUDE, not by
    # N(0.5,1). The first harness used the small draw and S_LEAKY3's own LABEL
    # came back identical at 3/3 probes — a full-sample tercile breakpoint can
    # absorb a same-scale perturbation. A tripwire that a leaky arm can survive
    # is not a tripwire, so the corruption was rebuilt rather than the arm
    # dropped (prereg §6.2).
    for c in ("mkt_vol_252", "mkt_vol_63", "mkt_ret_63", "mkt_ret_252",
              "mkt_dd_252", "cash_fwd_1m"):
        m.loc[mk_after, c] = rng.normal(0.5, 1.0, int(mk_after.sum())) * 1e3
    for c in ("mkt_fwd_1m", "spy_fwd_1m", "qqq_fwd_1m"):
        m.loc[mk_at, c] = _sgn(rng, int(mk_at.sum()), mode)
    y = yc.copy()
    y.loc[y.index > dates[probe]] = rng.normal(0.5, 1.0, int(
        (y.index > dates[probe]).sum()))
    return p, m, y


def stage_proof() -> dict:
    _log("=== STAGE 2: no-lookahead proof + tripwire ===")
    w = build_world()
    base_states = w["states"]
    dates = w["bed"]["dates"]
    results = {}
    n_draws = 3
    for probe in PROBES:
        for draw in range(n_draws):
            t0 = time.time()
            rng = np.random.default_rng(R.SEED + 7919 * draw + probe)
            p2, m2, y2 = _corrupt(w["bed"]["panel"],
                                  pd.read_parquet(R.MARKET),
                                  w["yc"], probe, dates, rng,
                                  mode=(1, -1, 0)[draw])
            bed2 = R.load_bed(p2, m2)
            feats2 = R.state_features(bed2)
            opts2 = R.precompute_options(bed2)
            st2 = R.build_states(bed2, feats2, opts2, yc_raw=y2)
            w2 = {"bed": bed2, "opts": opts2, "states": st2}
            cell = {}
            for sid, lab in base_states.items():
                same_label = bool(int(lab[probe]) == int(st2[sid][probe]))
                dec = {}
                for fam in FAMILIES:
                    a = choose(fam, w, lab, probe, R.K_PRIMARY)
                    b = choose(fam, w2, st2[sid], probe, R.K_PRIMARY)
                    dec[fam] = bool(a[2] == b[2]
                                    and np.array_equal(a[0], b[0])
                                    and np.allclose(a[1], b[1], atol=0,
                                                    rtol=0, equal_nan=True))
                cell[sid] = {"class": R.STATE_CLASS[sid],
                             "label_identical": same_label,
                             "label_before": int(lab[probe]),
                             "label_after": int(st2[sid][probe]),
                             "decision_identical": dec}
            results[f"{probe}/{draw}"] = {"date": str(dates[probe].date()),
                                          "probe": probe, "draw": draw,
                                          "cells": cell,
                                          "secs": round(time.time() - t0, 1)}
            _log(f"  probe {probe} ({dates[probe].date()}) draw {draw} "
                 f"in {time.time()-t0:.0f}s")

    # ── the verdicts, computed mechanically ─────────────────────────────────
    # S_SHUFFLE3 is EXCLUDED from the PIT requirement and the exclusion is
    # declared, not silent: a block permutation of the WHOLE label sequence is
    # non-causal by construction — the placebo at month k carries some other
    # month's tercile, including a future one. That is what makes it a placebo
    # (a random partition of the trailing window) and it is never promotable.
    NON_PIT_BY_CONSTRUCTION = ("S_SHUFFLE3",)
    real_fail = []
    trip = {s: {"fired": 0, "cells": 0} for s in R.LEAKY_STATES}
    for pk, pv in results.items():
        for sid, c in pv["cells"].items():
            if sid in R.LEAKY_STATES:
                moved = (not c["label_identical"]) or not all(
                    c["decision_identical"].values())
                trip[sid]["fired"] += int(moved)
                trip[sid]["cells"] += 1
            elif sid in NON_PIT_BY_CONSTRUCTION:
                continue
            else:
                if not c["label_identical"]:
                    real_fail.append(f"{sid}@{pk}:label")
                for fam, ok in c["decision_identical"].items():
                    if not ok:
                        real_fail.append(f"{sid}@{pk}:{fam}")
    per_probe = {s: {str(p): sum(
        1 for k, v in results.items() if v["probe"] == p
        and ((not v["cells"][s]["label_identical"])
             or not all(v["cells"][s]["decision_identical"].values())))
        for p in PROBES} for s in R.LEAKY_STATES}
    payload = {"trial": "REGIME-ARENA-1", "prereg": PREREG,
               "probes": list(PROBES), "draws_per_probe": n_draws,
               "results": results,
               "real_state_violations": real_fail,
               "real_states_clean": not real_fail,
               "non_pit_by_construction_excluded": list(
                   NON_PIT_BY_CONSTRUCTION),
               "tripwire_fired": trip,
               "tripwire_fired_per_probe": per_probe,
               "tripwire_has_teeth": all(
                   all(v >= 1 for v in per_probe[s].values())
                   for s in R.LEAKY_STATES),
               "note": ("a real state must be bit-identical in LABEL and in "
                        "the CHOSEN OPTION under corruption of every cell "
                        "observed after the probe; S_ORACLE2 and S_LEAKY3 are "
                        "REQUIRED to move at every probe or the harness is "
                        "rebuilt, not the arm dropped (prereg §6.2)")}
    return _write("proof", payload)


# ══════════════════════════════════════════════════════════════════════════
# STAGE 3 — simulate everything
# ══════════════════════════════════════════════════════════════════════════
def stage_sim() -> dict:
    _log("=== STAGE 3: simulate ===")
    w = build_world()
    states = w["states"]
    paths: dict[str, pd.DataFrame] = {}
    denom = {"primary_grid": 0, "cost_cells": 0, "placebo_seeds": 0,
             "matched": 0}
    t0 = time.time()

    for fam in FAMILIES:
        for K in R.K_GRID:
            for sid, lab in states.items():
                key = f"{fam}|{sid}|K{K}|c1"
                paths[key] = simulate(w, fam, lab, K)["frame"]
                denom["primary_grid"] += 1
        _log(f"  {fam}: primary grid done ({time.time()-t0:.0f}s)")

    for fam in FAMILIES:
        for sid, lab in states.items():
            for cm in (0.0, 2.0):
                key = f"{fam}|{sid}|K20|c{cm:g}"
                paths[key] = simulate(w, fam, lab, R.K_PRIMARY,
                                      cost_mult=cm)["frame"]
                denom["cost_cells"] += 1
    _log(f"  cost cells done ({time.time()-t0:.0f}s)")

    for fam in FAMILIES:
        for s in range(R.N_SHUFFLE_SEEDS):
            lab = R.shuffled_state(states["S_VOL3"], seed=s)
            key = f"{fam}|SHUF{s}|K20|c1"
            paths[key] = simulate(w, fam, lab, R.K_PRIMARY)["frame"]
            denom["placebo_seeds"] += 1
    _log(f"  placebo seeds done ({time.time()-t0:.0f}s)")

    # ── §A3 matched variants, primary configuration only ───────────────────
    for fam in FAMILIES:
        ctl = paths[f"{fam}|S_NONE|K20|c1"]
        for sid, lab in states.items():
            if sid == "S_NONE":
                continue
            arm = paths[f"{fam}|{sid}|K20|c1"]
            for what in ("beta", "vol"):
                col = f"{what}_exante"
                sp = np.clip(ctl[col].to_numpy(float)
                             / np.where(arm[col].to_numpy(float) > 1e-9,
                                        arm[col].to_numpy(float), np.nan),
                             *A.SCALE_CLIP)
                sp = np.where(np.isfinite(sp), sp, 1.0)
                paths[f"{fam}|{sid}|K20|c1|m{what}"] = simulate(
                    w, fam, lab, R.K_PRIMARY, scale_path=sp)["frame"]
                denom["matched"] += 1
            # turnover matching: both sides capped at the SAME one-way budget
            bud = float(min(eval_slice(arm)["turnover_1way"].mean(),
                            eval_slice(ctl)["turnover_1way"].mean()))
            paths[f"{fam}|{sid}|K20|c1|mturn"] = simulate(
                w, fam, lab, R.K_PRIMARY, turnover_budget=bud)["frame"]
            paths[f"{fam}|{sid}|K20|c1|mturnCTL"] = simulate(
                w, fam, states["S_NONE"], R.K_PRIMARY,
                turnover_budget=bud)["frame"]
            denom["matched"] += 2
    _log(f"  matched variants done ({time.time()-t0:.0f}s)")

    store = OUT / "regime_arena_1_paths.parquet"
    big = pd.concat([f.assign(arm=k) for k, f in paths.items()],
                    ignore_index=True)
    big.to_parquet(store)
    payload = {"trial": "REGIME-ARENA-1", "prereg": PREREG,
               "n_paths": len(paths), "search_denominator_sims": denom,
               "total_sims": int(sum(denom.values())),
               "paths_file": store.name,
               "secs": round(time.time() - t0, 1)}
    return _write("sim", payload)


def load_paths() -> dict[str, pd.DataFrame]:
    big = pd.read_parquet(OUT / "regime_arena_1_paths.parquet")
    return {k: g.drop(columns=["arm"]).reset_index(drop=True)
            for k, g in big.groupby("arm")}


# ══════════════════════════════════════════════════════════════════════════
# STAGE 4 — score: D_cond against the unconditional twin
# ══════════════════════════════════════════════════════════════════════════
def paired(arm: np.ndarray, ctl: np.ndarray, years: np.ndarray) -> dict:
    d = np.log1p(arm) - np.log1p(ctl)
    r = A.ruler(d, years)
    return {"delta_pp_yr": r["mean_ann_pct"], "mde80_pp_yr": r["mde_ann_pct"],
            "t": r["t"], "detectable": r["detectable"],
            "blocks": r.get("blocks"), "blocks_agree_n": r.get("blocks_agree_n"),
            "blocks_n": r.get("blocks_n"), "halves_agree": r.get("halves_agree"),
            "n": r["n"], "ruler_verdict": r["verdict"]}


def _verdict(dc: dict, vs_placebo: dict, gross_ok: bool) -> str:
    if not gross_ok:
        return "VOID_GROSS_EXPOSURE"
    if dc["delta_pp_yr"] is None or not dc["detectable"]:
        return "NOT_DETECTABLE"
    cov = (dc["blocks_agree_n"] or 0) >= 5 and bool(dc["halves_agree"])
    if dc["delta_pp_yr"] < 0:
        return "CONDITIONING_HARMFUL" if cov else "UNRESOLVED_UNSTABLE"
    if not cov:
        return "UNRESOLVED_UNSTABLE"
    if not vs_placebo["detectable"] or (vs_placebo["delta_pp_yr"] or 0) <= 0:
        return "PLACEBO_EQUIVALENT"
    return "CONDITIONING_DETECTED"


def stage_score() -> dict:
    _log("=== STAGE 4: score ===")
    w = build_world()
    states = w["states"]
    paths = load_paths()
    years_all = w["bed"]["dates"].year.to_numpy()
    years = years_all[R.BURN_IN:]
    rows, dseries = [], {}

    for fam in FAMILIES:
        ctl20 = eval_slice(paths[f"{fam}|S_NONE|K20|c1"])["net"].to_numpy(float)
        # the placebo reference: seed 0 is the pre-registered S_SHUFFLE3 twin
        shuf = {s: eval_slice(paths[f"{fam}|SHUF{s}|K20|c1"]
                              )["net"].to_numpy(float)
                for s in range(R.N_SHUFFLE_SEEDS)}
        shuf_D = np.array([float(np.mean(np.log1p(v) - np.log1p(ctl20))) * 12
                           * 100 for v in shuf.values()])
        for K in R.K_GRID:
            ctl = eval_slice(paths[f"{fam}|S_NONE|K{K}|c1"]
                             )["net"].to_numpy(float)
            for sid in states:
                if sid == "S_NONE":
                    continue
                f = paths[f"{fam}|{sid}|K{K}|c1"]
                e = eval_slice(f)
                arm = e["net"].to_numpy(float)
                m = arm_metrics(f)
                # THE STATISTIC THAT DECIDES WHETHER AN ARM IS EVIDENCE AT ALL.
                # The fallback rate says the arm HAD an in-state history; it
                # does not say the state changed the answer. This does: the
                # share of evaluated months where the conditioned choice
                # differs from the unconditional twin's choice on the same
                # date. At 0.004 an arm is not a test of conditioning.
                ec = eval_slice(paths[f"{fam}|S_NONE|K{K}|c1"])
                m["decision_divergence_rate"] = round(float(
                    (e["choice"].to_numpy() != ec["choice"].to_numpy()).mean()
                ), 4)
                gross_ok = abs(m["gross_exposure_mean"] - 1.0) < 1e-6
                dc = paired(arm, ctl, years)
                vsp = paired(arm, shuf[0], years)
                row = {"id": f"{fam}|{sid}|K{K}",
                       "family": fam, "state": sid,
                       "class": R.STATE_CLASS[sid], "K": K,
                       "primary": K == R.K_PRIMARY,
                       "metrics": m,
                       "control_metrics": arm_metrics(
                           paths[f"{fam}|S_NONE|K{K}|c1"]),
                       "D_cond": dc,
                       "D_vs_placebo_seed0": vsp,
                       "gross_verified_1p00": gross_ok}
                row["verdict"] = _verdict(dc, vsp, gross_ok)
                if R.STATE_CLASS[sid] in ("IMPOSSIBLE", "TRIPWIRE_LOOKAHEAD"):
                    row["verdict"] = "DIAGNOSTIC — " + row["verdict"]
                if K == R.K_PRIMARY:
                    row["placebo_distribution"] = {
                        "n_seeds": int(len(shuf_D)),
                        "mean_pp_yr": round(float(shuf_D.mean()), 4),
                        "sd_pp_yr": round(float(shuf_D.std(ddof=1)), 4),
                        "p95_pp_yr": round(float(np.percentile(shuf_D, 95)), 4),
                        "arm_percentile_vs_placebo": round(float(
                            (shuf_D < (dc["delta_pp_yr"] or 0)).mean()), 3),
                    }
                    cs = {}
                    for cm in (0.0, 1.0, 2.0):
                        tag = f"c{cm:g}" if cm != 1.0 else "c1"
                        a2 = eval_slice(paths[f"{fam}|{sid}|K20|{tag}"]
                                        )["net"].to_numpy(float)
                        c2 = eval_slice(paths[f"{fam}|S_NONE|K20|{tag}"]
                                        )["net"].to_numpy(float)
                        cs[f"{cm:g}x"] = paired(a2, c2, years)["delta_pp_yr"]
                    row["cost_sensitivity_D_cond_pp_yr"] = cs
                    mt = {}
                    for what in ("beta", "vol"):
                        a2 = eval_slice(
                            paths[f"{fam}|{sid}|K20|c1|m{what}"]
                        )["net"].to_numpy(float)
                        mt[what] = paired(a2, ctl20, years)
                    a2 = eval_slice(paths[f"{fam}|{sid}|K20|c1|mturn"]
                                    )["net"].to_numpy(float)
                    c2 = eval_slice(paths[f"{fam}|{sid}|K20|c1|mturnCTL"]
                                    )["net"].to_numpy(float)
                    mt["turnover"] = paired(a2, c2, years)
                    row["matched_A3"] = mt
                    row["survives_matching"] = bool(
                        dc["detectable"]
                        and all(v["detectable"]
                                and np.sign(v["delta_pp_yr"])
                                == np.sign(dc["delta_pp_yr"])
                                for v in mt.values()))
                    # SYMMETRY. The first version applied this downgrade only
                    # to CONDITIONING_DETECTED, which would have held positive
                    # results to §A3 and let a negative one through unmatched —
                    # exactly the bias the amendment exists to remove. A harm
                    # that is really a beta effect is a beta effect.
                    if row["verdict"] in ("CONDITIONING_DETECTED",
                                          "CONDITIONING_HARMFUL") \
                            and not row["survives_matching"]:
                        row["verdict"] = "UNRESOLVED_MATCHING"
                    dseries[row["id"]] = np.log1p(arm) - np.log1p(ctl)
                rows.append(row)
    rows.sort(key=lambda r: -(r["D_cond"]["delta_pp_yr"] or -1e9))
    payload = {"trial": "REGIME-ARENA-1", "prereg": PREREG,
               "n_arms": len(rows), "arms": rows,
               "batch_selfcheck": _batch_selfcheck(dseries)}
    _write("score", payload)
    np.savez(OUT / "regime_arena_1_dseries.npz",
             **{k: v for k, v in dseries.items()})
    det = [r["id"] for r in rows if r["verdict"] == "CONDITIONING_DETECTED"]
    _log(f"  CONDITIONING_DETECTED: {det if det else 'NONE'}")
    return payload


def _batch_selfcheck(dseries: dict) -> dict:
    """§20 — how many of these configurations are actually distinct?"""
    keys = [k for k in dseries
            if not any(t in k for t in ("S_ORACLE2", "S_LEAKY3"))]
    if len(keys) < 2:
        return {"n_arms": len(keys)}
    M = np.vstack([dseries[k] for k in keys])
    Cm = np.corrcoef(M)
    off = Cm[~np.eye(len(keys), dtype=bool)]
    mean_abs = float(np.nanmean(np.abs(off)))
    eff = float(len(keys) / (1 + (len(keys) - 1) * mean_abs))
    per_fam = {}
    for fam in FAMILIES:
        kk = [k for k in keys if k.startswith(fam)]
        if len(kk) > 1:
            c = np.corrcoef(np.vstack([dseries[k] for k in kk]))
            o = c[~np.eye(len(kk), dtype=bool)]
            ma = float(np.nanmean(np.abs(o)))
            per_fam[fam] = {"n": len(kk),
                            "mean_abs_corr": round(ma, 4),
                            "effective_arms": round(
                                len(kk) / (1 + (len(kk) - 1) * ma), 2)}
    return {"n_arms": len(keys),
            "mean_abs_pairwise_corr_of_monthly_D_cond": round(mean_abs, 4),
            "effective_distinct_arms": round(eff, 2),
            "per_family": per_fam,
            "note": "correlation of the MONTHLY arm-minus-unconditional log "
                    "return difference, primary K=20 arms, diagnostics "
                    "excluded"}


# ══════════════════════════════════════════════════════════════════════════
# STAGE 5 — summary: denominator, CSCV/PBO, family DSR
# ══════════════════════════════════════════════════════════════════════════
def cscv_pbo(M: np.ndarray, S: int = CSCV_S) -> dict:
    """Bailey-Borwein-Lopez de Prado-Zhu CSCV on the D_cond matrix."""
    n_cfg, T = M.shape
    if n_cfg < 2 or T < 2 * S:
        return {"pbo": None, "note": "too few configurations or months"}
    blocks = np.array_split(np.arange(T), S)
    logits, oos_of_best = [], []
    for comb in combinations(range(S), S // 2):
        i_is = np.concatenate([blocks[i] for i in comb])
        i_oos = np.concatenate([blocks[i] for i in range(S) if i not in comb])
        p_is, p_oos = M[:, i_is].mean(1), M[:, i_oos].mean(1)
        star = int(np.argmax(p_is))
        rank = float((p_oos.argsort().argsort()[star] + 1) / (n_cfg + 1))
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        logits.append(np.log(rank / (1 - rank)))
        oos_of_best.append(float(p_oos[star]))
    lg = np.array(logits)
    return {"pbo": round(float((lg <= 0).mean()), 4),
            "n_combinations": len(lg),
            "n_configurations": n_cfg,
            "median_logit": round(float(np.median(lg)), 4),
            "mean_oos_D_cond_of_IS_best_pp_yr": round(
                float(np.mean(oos_of_best)) * 12 * 100, 4),
            "share_oos_negative": round(float(
                (np.array(oos_of_best) <= 0).mean()), 4)}


def family_dsr(M: np.ndarray, names: list[str]) -> dict:
    """DSR on the FAMILY (§A8), with V[SR] taken from the family's own spread."""
    sr = M.mean(1) / np.where(M.std(1, ddof=1) > 0, M.std(1, ddof=1), np.nan)
    sr = sr[np.isfinite(sr)]
    if len(sr) < 3:
        return {"note": "too few arms"}
    var_sr = float(np.var(sr, ddof=1))
    best_i = int(np.nanargmax(M.mean(1) / M.std(1, ddof=1)))
    x = M[best_i]
    n_obs = len(x)
    sr_best = float(x.mean() / x.std(ddof=1))
    from scipy import stats as st
    sk, ku = float(st.skew(x)), float(st.kurtosis(x, fisher=False))
    ladder, breakeven = {}, None
    for N in N_LADDER:
        sr0 = expected_max_sr(N, var_sr)
        d = deflated_sharpe(sr_best, sr0, n_obs, sk, ku)
        ladder[str(N)] = round(float(d), 4)
        if breakeven is None and d < 0.95:
            breakeven = N
    return {"family_var_SR_monthly": round(var_sr, 6),
            "best_arm": names[best_i],
            "best_arm_SR_monthly": round(sr_best, 4),
            "n_obs_months": n_obs,
            "skew": round(sk, 3), "kurtosis": round(ku, 3),
            "DSR_by_assumed_independent_trials": ladder,
            "breakeven_N_at_0.95": breakeven,
            "note": "the tested series is D_cond (conditioned minus its own "
                    "unconditional twin), which is the claim; V[SR] is the "
                    "spread ACROSS this family's arms, not an assumption"}


def stage_summary() -> dict:
    _log("=== STAGE 5: summary ===")
    sc, sm, pr, stt = _read("score"), _read("sim"), _read("proof"), \
        _read("states")
    if sc is None:
        raise SystemExit("REFUSAL: no scored artifact")
    z = np.load(OUT / "regime_arena_1_dseries.npz")
    keys = [k for k in z.files
            if not any(t in k for t in ("S_ORACLE2", "S_LEAKY3"))]
    M = np.vstack([z[k] for k in keys])
    real = [k for k in keys if "S_SHUFFLE3" not in k]

    arms = sc["arms"]
    prim = [a for a in arms if a["primary"]]
    diag = [a for a in prim if a["class"] in ("IMPOSSIBLE",
                                              "TRIPWIRE_LOOKAHEAD")]
    real_arms = [a for a in prim if a["class"] not in
                 ("IMPOSSIBLE", "TRIPWIRE_LOOKAHEAD")]
    det = [a["id"] for a in real_arms if a["verdict"] == "CONDITIONING_DETECTED"]
    harm = [a["id"] for a in real_arms if a["verdict"] == "CONDITIONING_HARMFUL"]
    unm = [a["id"] for a in real_arms if a["verdict"] == "UNRESOLVED_MATCHING"]
    above = [a["id"] for a in real_arms if a["D_cond"]["detectable"]]

    # §A11(4): the SAME state clearing in >= 2 of the 3 families independently
    by_state: dict[str, list[str]] = {}
    for a in real_arms:
        if a["verdict"] == "CONDITIONING_DETECTED":
            by_state.setdefault(a["state"], []).append(a["family"])
    replicated = {s: f for s, f in by_state.items() if len(set(f)) >= 2}

    oracle = {a["id"]: a["D_cond"]["delta_pp_yr"] for a in prim
              if a["state"] == "S_ORACLE2"}
    best_obs = max((a["D_cond"]["delta_pp_yr"] or -1e9) for a in real_arms
                   if a["state"] not in ("S_SHUFFLE3",))
    orc = max(oracle.values()) if oracle else None

    out = {
        "trial": "REGIME-ARENA-1", "prereg": PREREG,
        "search_denominator": {
            **sm["search_denominator_sims"],
            "total_simulations": sm["total_sims"],
            "scored_arms": sc["n_arms"],
            "primary_arms": len(prim),
            "real_primary_arms": len(real_arms),
            "diagnostic_arms": len(diag),
            "states": len(stt["states"]),
            "families": len(FAMILIES),
            "K_grid": list(R.K_GRID),
            "cost_multipliers": list(R.COST_MULTS),
            "placebo_seeds": R.N_SHUFFLE_SEEDS,
            "declared_non_run": "no exposure arm exists in this trial by "
                                "construction (chunk 6 owns that question)",
        },
        "lookahead": {
            "real_states_clean": pr["real_states_clean"],
            "violations": pr["real_state_violations"],
            "tripwire_fired": pr["tripwire_fired"],
            "tripwire_fired_per_probe": pr["tripwire_fired_per_probe"],
            "non_pit_by_construction_excluded":
                pr["non_pit_by_construction_excluded"],
            "tripwire_has_teeth": pr["tripwire_has_teeth"],
        },
        "headline": {
            "any_state_beat_its_unconditional_twin": bool(det),
            "which": det,
            "CONDITIONING_HARMFUL": harm,
            "UNRESOLVED_MATCHING": unm,
            "n_real_arms_above_own_MDE": len(above),
            "which_above_own_MDE": above,
            "n_real_primary_arms": len(real_arms),
            "A11_4_replication_eligible": bool(replicated),
            "replicating_states": replicated,
            "breakthrough_eligible": bool(replicated),
        },
        "oracle_bound": {
            "oracle_D_cond_pp_yr": oracle,
            "best_observable_D_cond_pp_yr": round(best_obs, 4),
            "share_of_oracle_captured": (round(best_obs / orc, 4)
                                         if orc and orc > 0 else None),
        },
        "batch_selfcheck": sc["batch_selfcheck"],
        "PBO_cscv_all_real_and_placebo": cscv_pbo(M),
        "PBO_cscv_real_states_only": cscv_pbo(
            np.vstack([z[k] for k in real])),
        "DSR_family": family_dsr(M, keys),
        "gross_exposure_verification": {
            "arms_at_1p00": int(sum(a["gross_verified_1p00"] for a in arms)),
            "arms_total": len(arms),
            "voided": [a["id"] for a in arms if not a["gross_verified_1p00"]],
        },
    }
    return _write("summary", out)


# ══════════════════════════════════════════════════════════════════════════
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all")
    a = ap.parse_args()
    order = ["states", "proof", "sim", "score", "summary"]
    todo = order if a.stage == "all" else [a.stage]
    for s in todo:
        globals()[f"stage_{s}"]()
    _log("DONE")


if __name__ == "__main__":
    main()
