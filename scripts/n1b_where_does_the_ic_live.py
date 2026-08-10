"""N1B — where does the learned ranker's IC live?

TRIAL-N1B-WHERE-DOES-THE-IC-LIVE-1, prereg
`TRIALS/PREREG_N1B_WHERE_DOES_THE_IC_LIVE.md` + AMENDMENT 1 (NIGHT-9).

The parent measured three learned rankers ordering the cross-section better than
the hand-written composite (ΔIC +0.034/+0.068/+0.056 at t 4.18/4.09/3.46) while
every one of them earned LESS money. Turnover was ruled out by measurement. This
is the diagnosis, and it fits no model: it decomposes the parent's own frozen
predictions along six axes.

Step 0 is a re-fit, because the parent never persisted its score frames — and
that re-fit is admissible only if it reproduces the parent's published numbers.
A factory that cannot reproduce its own receipt by re-running its own script has
a worse problem than the one this trial was written to answer.

Reported, never deciding. No model is fitted here. No arm is added.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))
sys.path.insert(0, str(HERE))
logging.basicConfig(level=logging.ERROR)

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf import decomp as D
from aegis_brain.pf.engine import run_book
from aegis_brain.pf.run import Factory
from aegis_brain.pf.signals import composite_score
from aegis_brain.pf.spec import StrategySpec

import n1_ranker_vs_composite as N1        # the parent, imported not copied

OUT = MODULE_ROOT / "runs" / "NIGHT9"
FROZEN = OUT / "frozen_scores"
PARENT = MODULE_ROOT / "runs" / "NIGHT8" / "N1_RANKER_VS_COMPOSITE.json"

#: The prereg's reproduction gate. Looser on t than on the mean because a
#: Newey-West t is a ratio of two estimates and rounds harder.
TOL = {"mean_ic": 1e-4, "dic_mean": 1e-3, "t": 0.05, "money_mean": 1e-4,
       "turnover": 1e-3}
TOPK = (25, 50, 100, 150, 300)
BOUNDARY = (100, 250)
#: Coverage limit, declared: the phase axis runs the control and the largest-ΔIC
#: arm only. Twelve phases x four arms is 48 books; twelve x two is 24.
PHASE_ARMS = ("R0_composite", "R2_gbm_wide")


# ─────────────────────────────── step 0: freeze ────────────────────────────

def build_world():
    """Exactly the parent's setup, in the parent's order."""
    banked = json.loads(N1.BANKED.read_text(encoding="utf-8"))
    d = dict(banked["spec"])
    d["signals"] = tuple(tuple(s) for s in d["signals"])
    d["tags"] = ()
    f = Factory()
    elig = f.eligible(d["segment"])
    era = D.era_cost_frame(f.spine.panel, 25.0, f.cost_frame())
    ret = f.spine.panel.monthly_ret

    logret = np.log1p(ret.clip(lower=-0.99))
    fwd = logret.rolling(N1.LABEL_MONTHS).sum().shift(-N1.LABEL_MONTHS)
    fwd = fwd.where(elig)
    label = fwd.sub(fwd.mean(axis=1), axis=0)
    return f, d, elig, era, ret, label


def freeze(f, d, elig, ret, label) -> dict[str, pd.DataFrame]:
    """Re-run the parent's three fits with its seed and persist the frames."""
    FROZEN.mkdir(parents=True, exist_ok=True)
    names = ["R0_composite", "R1_gbm_narrow", "R2_gbm_wide", "R3_mlp_wide"]
    paths = {n: FROZEN / f"{n}.parquet" for n in names}
    if all(p.exists() for p in paths.values()):
        print("  frozen frames already on disk", flush=True)
        return {n: pd.read_parquet(p) for n, p in paths.items()}

    rng = np.random.default_rng(N1.SEED)
    narrow = tuple(k for k, _ in d["signals"])
    months = ret.index
    feats_narrow = N1.rank_frames(f.lib, narrow, elig)
    feats_wide = {**feats_narrow, **N1.rank_frames(f.lib, N1.WIDE, elig)}

    lo = pd.Timestamp(d["first_month"])
    usable = [m for m in months if m >= lo]
    fit_months = [m for i, m in enumerate(usable)
                  if i % 12 == 0 and i >= N1.MIN_TRAIN_MONTHS]
    tmpl = ret.loc[usable]
    e = elig.reindex(index=usable, columns=ret.columns).fillna(False)
    print(f"  refits {len(fit_months)}; building tables...", flush=True)
    tab_narrow = N1.Table(feats_narrow, usable, e, label)
    tab_wide = N1.Table(feats_wide, usable, e, label)

    scores = {"R0_composite": composite_score(f.lib, d["signals"], elig)[0]}
    scores["R1_gbm_narrow"] = N1.fit_predict("gbm", tab_narrow, fit_months,
                                             rng, tmpl)
    scores["R2_gbm_wide"] = N1.fit_predict("gbm", tab_wide, fit_months, rng,
                                           tmpl)
    scores["R3_mlp_wide"] = N1.fit_predict("mlp", tab_wide, fit_months, rng,
                                           tmpl)
    for n, s in scores.items():
        s.astype(np.float32).to_parquet(paths[n])
    return scores


def reproduce(scores, f, d, elig, era, label) -> dict:
    """The gate. Recompute the parent's headline statistics from the frames."""
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    first = min(s.notna().any(axis=1).idxmax() for k, s in scores.items()
                if k != "R0_composite")
    window = {"first_month": str(first.date()),
              "last_month": d["last_month"]}
    monthly, ics, diags, holds = {}, {}, {}, {}
    for name, sc in scores.items():
        spec = StrategySpec(**{**d, **window, "rebalance_months": 12,
                               "cost_model": "ko", "name": f"N1__{name}"})
        h: list = []
        out = run_book(f.spine.panel, sc.astype(np.float32), elig, spec,
                       f.spine.rf, era, holdings_out=h)
        monthly[name] = out["monthly"]["net"]
        diags[name] = out["diag"]
        holds[name] = h
        ics[name] = N1.rank_ic(sc.loc[sc.index >= first], label, elig)

    checks, ok = [], True
    base, base_ic = monthly["R0_composite"], ics["R0_composite"]
    for name in scores:
        if name == "R0_composite":
            continue
        p_o, p_m = parent["ordering"][name], parent["money"][name]
        o = N1.paired(ics[name], base_ic, lags=N1.LABEL_MONTHS)
        m = N1.paired(monthly[name], base)
        for field, got, want, tol in (
                ("dic_mean", o["mean_monthly"], p_o["mean_monthly"],
                 TOL["dic_mean"]),
                ("dic_t", o["t_newey_west"], p_o["t_newey_west"], TOL["t"]),
                ("money_mean", m["mean_monthly"], p_m["mean_monthly"],
                 TOL["money_mean"]),
                ("money_t", m["t_newey_west"], p_m["t_newey_west"], TOL["t"]),
                ("turnover", diags[name]["turnover_1way_annual"],
                 parent["diagnostics"][name]["turnover_1way_annual"],
                 TOL["turnover"])):
            good = abs(float(got) - float(want)) <= tol
            ok &= good
            checks.append({"arm": name, "field": field, "reproduced": got,
                           "published": want, "pass": bool(good)})
    return {"window": window, "checks": checks, "pass": bool(ok),
            "monthly": monthly, "ics": ics, "diags": diags, "holds": holds,
            "first": first}


# ───────────────────────────── the decompositions ──────────────────────────

def _paired_ic(a: pd.Series, b: pd.Series, lags: int = 12) -> dict:
    """Paired ΔIC in IC UNITS. Never annualised — a correlation has no /yr."""
    dd = (a - b).dropna()
    if len(dd) < 12:
        return {"months": int(len(dd)), "insufficient": True}
    se = float(dd.std(ddof=1) / np.sqrt(len(dd)))
    return {"months": int(len(dd)),
            "dic_mean": round(float(dd.mean()), 5),
            "t_newey_west": D.nw_t(pd.Series(dd.to_numpy()), lags=lags),
            "mde_ic_units": round(2.0 * se, 5),
            "unit": "spearman correlation, monthly, NOT annualisable"}


def masked_ic(score: pd.DataFrame, label: pd.DataFrame, mask: pd.DataFrame,
              months) -> pd.Series:
    """Monthly rank-IC restricted to a boolean mask (a decile, a band)."""
    out = {}
    for m in months:
        if m not in score.index or m not in label.index or m not in mask.index:
            continue
        keep = mask.loc[m]
        s = score.loc[m].where(keep).dropna()
        y = label.loc[m].reindex(s.index).dropna()
        s = s.reindex(y.index)
        if len(y) >= 30:
            out[m] = float(s.rank().corr(y.rank()))
    return pd.Series(out).dropna()


def decile_masks(score: pd.DataFrame, elig: pd.DataFrame, months, n=10):
    """Decile 1 = the names the score likes best."""
    r = score.where(elig.reindex_like(score)).loc[months].rank(
        axis=1, pct=True, ascending=False)
    return {i + 1: ((r > i / n) & (r <= (i + 1) / n)) for i in range(n)}


def band_mask(score: pd.DataFrame, elig: pd.DataFrame, months, lo, hi):
    r = score.where(elig.reindex_like(score)).loc[months].rank(
        axis=1, ascending=False)
    return (r > lo) & (r <= hi)


def topk_forward(score: pd.DataFrame, label: pd.DataFrame, elig, months, k):
    """Mean within-month-demeaned forward 12m log return of the top K."""
    out = {}
    for m in months:
        if m not in score.index or m not in label.index:
            continue
        s = score.loc[m].where(elig.loc[m]).dropna()
        if len(s) < k:
            continue
        top = s.nlargest(k).index
        y = label.loc[m].reindex(top).dropna()
        if len(y) >= max(10, k // 4):
            out[m] = float(y.mean())
    return pd.Series(out).dropna()


def replacement(base_h: list, arm_h: list, label: pd.DataFrame) -> dict:
    """On actual rebalance dates: what did the arm drop, what did it add?

    replacement loss = E[r(dropped)] - E[r(added)]. Positive means the arm's
    swaps made the book worse at exactly the point where selection happens.
    """
    bmap = {h["formation"]: h for h in base_h if h["rebalanced"]}
    amap = {h["formation"]: h for h in arm_h if h["rebalanced"]}
    rows = []
    for m in sorted(set(bmap) & set(amap)):
        if m not in label.index:
            continue
        A = pd.Index(bmap[m]["weights"].index)
        B = pd.Index(amap[m]["weights"].index)
        common, dropped, added = A.intersection(B), A.difference(B), B.difference(A)
        lab = label.loc[m]
        rd, ra = lab.reindex(dropped).dropna(), lab.reindex(added).dropna()
        if len(rd) < 5 or len(ra) < 5:
            continue
        rows.append({"month": m, "n_base": len(A), "n_arm": len(B),
                     "overlap": len(common) / max(len(A), 1),
                     "n_dropped": len(dropped), "n_added": len(added),
                     "r_dropped": float(rd.mean()), "r_added": float(ra.mean()),
                     "r_common": float(lab.reindex(common).dropna().mean()),
                     "loss": float(rd.mean() - ra.mean())})
    if not rows:
        return {"rebalances": 0, "insufficient": True}
    df = pd.DataFrame(rows).set_index("month")
    d = df["loss"]
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    return {"rebalances": int(len(df)),
            "mean_overlap": round(float(df["overlap"].mean()), 4),
            "mean_swapped_per_rebalance": round(float(df["n_dropped"].mean()), 1),
            "r_dropped": round(float(df["r_dropped"].mean()), 5),
            "r_added": round(float(df["r_added"].mean()), 5),
            "r_common": round(float(df["r_common"].mean()), 5),
            "replacement_loss": round(float(d.mean()), 5),
            "t_iid": round(float(d.mean() / se), 2) if se > 0 else None,
            "mde_at_t2": round(2.0 * se, 5),
            "unit": "forward 12m log return, demeaned within month"}


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    f, d, elig, era, ret, label = build_world()

    print("step 0: freezing the parent's predictions...", flush=True)
    scores = freeze(f, d, elig, ret, label)
    rep = reproduce(scores, f, d, elig, era, label)
    print(f"  reproduction gate: {'PASS' if rep['pass'] else 'FAIL'}", flush=True)
    for c in rep["checks"]:
        if not c["pass"]:
            print(f"    MISMATCH {c['arm']}.{c['field']}: "
                  f"{c['reproduced']} vs published {c['published']}", flush=True)

    res = {
        "trial": "TRIAL-N1B-WHERE-DOES-THE-IC-LIVE-1",
        "question": "the learned rankers order better and earn less — where "
                    "does the ordering advantage go?",
        "status": "REPORTED-NEVER-DECIDING",
        "prereg": "TRIALS/PREREG_N1B_WHERE_DOES_THE_IC_LIVE.md (+ AMENDMENT 1)",
        "data_grade": "crsp",
        "parent": "TRIAL-N1-RANKER-VS-COMPOSITE-1",
        "models_fitted_in_this_trial": 0,
        "reproduction_gate": {"pass": rep["pass"], "checks": rep["checks"],
                              "window": rep["window"]},
        "coverage_limits": [
            f"phase axis runs {PHASE_ARMS} only — the control and the "
            "largest-ΔIC arm; 12 phases x 4 arms was not run and is not "
            "claimed",
            "left-tail hit rate uses bottom-quintile forward return, not "
            "delistings: the delisting join is a separate build",
        ],
    }
    if not rep["pass"]:
        res["verdict"] = "DATA_FAILED — the parent's numbers did not reproduce"
        (OUT / "N1B_WHERE_DOES_THE_IC_LIVE.json").write_text(
            json.dumps(res, indent=2, default=str), encoding="utf-8")
        print("STOPPED: reproduction gate failed.", flush=True)
        return 1

    ics, holds = rep["ics"], rep["holds"]
    base_ic = ics["R0_composite"]
    arms = [k for k in scores if k != "R0_composite"]
    all_months = list(base_ic.index)
    reb_months = sorted({h["formation"] for h in holds["R0_composite"]
                         if h["rebalanced"] and h["formation"] in base_ic.index})
    off_months = [m for m in all_months if m not in set(reb_months)]
    print(f"\nclock: {len(reb_months)} rebalance months, {len(off_months)} off",
          flush=True)

    # ── axis 1: clock ──────────────────────────────────────────────────────
    res["clock"] = {"n_rebalance_months": len(reb_months),
                    "n_off_clock_months": len(off_months), "arms": {}}
    for a in arms:
        res["clock"]["arms"][a] = {
            "on_rebalance": _paired_ic(ics[a].reindex(reb_months).dropna(),
                                       base_ic.reindex(reb_months).dropna(),
                                       lags=1),
            "off_clock": _paired_ic(ics[a].reindex(off_months).dropna(),
                                    base_ic.reindex(off_months).dropna()),
            "all_months": _paired_ic(ics[a], base_ic),
        }
        c = res["clock"]["arms"][a]
        print(f"  {a:16s} on-clock dIC {c['on_rebalance'].get('dic_mean')} "
              f"(t {c['on_rebalance'].get('t_newey_west')}, MDE "
              f"{c['on_rebalance'].get('mde_ic_units')})   off-clock "
              f"{c['off_clock'].get('dic_mean')} "
              f"(t {c['off_clock'].get('t_newey_west')})", flush=True)

    # ── axis 2: rank deciles ───────────────────────────────────────────────
    print("\nrank deciles...", flush=True)
    res["rank"] = {"note": "own_decile is the registered test; base_decile "
                           "conditions both arms on identical name sets",
                   "arms": {}}
    base_dec = decile_masks(scores["R0_composite"], elig, all_months)
    for a in arms:
        own_dec = decile_masks(scores[a], elig, all_months)
        rows = {}
        for i in range(1, 11):
            b_own = masked_ic(scores["R0_composite"], label, own_dec[i],
                              all_months)
            a_own = masked_ic(scores[a], label, own_dec[i], all_months)
            b_bas = masked_ic(scores["R0_composite"], label, base_dec[i],
                              all_months)
            a_bas = masked_ic(scores[a], label, base_dec[i], all_months)
            rows[i] = {"own_decile": _paired_ic(a_own, b_own),
                       "base_decile": _paired_ic(a_bas, b_bas)}
        res["rank"]["arms"][a] = rows
        top = rows[1]["base_decile"].get("dic_mean")
        bot = rows[10]["base_decile"].get("dic_mean")
        print(f"  {a:16s} base-decile dIC  D1 {top}  D10 {bot}", flush=True)

    # ── axis 3: the selection boundary ─────────────────────────────────────
    print("\nboundary band (ranks 100-250)...", flush=True)
    res["boundary"] = {"band": BOUNDARY, "arms": {}}
    for a in arms:
        bm = band_mask(scores["R0_composite"], elig, all_months, *BOUNDARY)
        res["boundary"]["arms"][a] = _paired_ic(
            masked_ic(scores[a], label, bm, all_months),
            masked_ic(scores["R0_composite"], label, bm, all_months))
        print(f"  {a:16s} dIC in band "
              f"{res['boundary']['arms'][a].get('dic_mean')} "
              f"(t {res['boundary']['arms'][a].get('t_newey_west')})", flush=True)

    # ── axis 4: top-K on rebalance months ──────────────────────────────────
    print("\ntop-K forward return, rebalance months only...", flush=True)
    res["topk"] = {"months": "rebalance only", "arms": {}, "control": {}}
    for k in TOPK:
        b = topk_forward(scores["R0_composite"], label, elig, reb_months, k)
        res["topk"]["control"][k] = round(float(b.mean()), 5)
        for a in arms:
            s = topk_forward(scores[a], label, elig, reb_months, k)
            dd = (s - b).dropna()
            se = float(dd.std(ddof=1) / np.sqrt(len(dd))) if len(dd) > 2 else None
            res["topk"]["arms"].setdefault(a, {})[k] = {
                "arm_mean": round(float(s.mean()), 5),
                "delta": round(float(dd.mean()), 5) if len(dd) else None,
                "t_iid": round(float(dd.mean() / se), 2) if se else None,
                "mde_at_t2": round(2 * se, 5) if se else None,
                "n": int(len(dd))}
        print(f"  K={k:4d} control {res['topk']['control'][k]:+.4f}  " +
              "  ".join(f"{a.split('_')[0]} "
                        f"{res['topk']['arms'][a][k]['delta']:+.4f}"
                        for a in arms), flush=True)

    # ── axis 5: membership and replacement loss ────────────────────────────
    print("\nmembership / replacement loss...", flush=True)
    res["membership"] = {}
    for a in arms:
        res["membership"][a] = replacement(holds["R0_composite"], holds[a],
                                           label)
        r = res["membership"][a]
        print(f"  {a:16s} overlap {r.get('mean_overlap')}  swapped/reb "
              f"{r.get('mean_swapped_per_rebalance')}  dropped "
              f"{r.get('r_dropped')} vs added {r.get('r_added')}  loss "
              f"{r.get('replacement_loss')} (t {r.get('t_iid')}, MDE "
              f"{r.get('mde_at_t2')})", flush=True)

    # ── axis 6: phase ──────────────────────────────────────────────────────
    print("\nphase axis (declared coverage limit: "
          f"{PHASE_ARMS})...", flush=True)
    res["phase"] = {"arms_run": list(PHASE_ARMS), "results": {}}
    for a in PHASE_ARMS:
        per = {}
        for ph in range(12):
            spec = StrategySpec(**{**d, **rep["window"], "rebalance_months": 12,
                                   "cost_model": "ko",
                                   "name": f"N1B__{a}__ph{ph}"})
            h: list = []
            try:
                out = run_book(f.spine.panel, scores[a].astype(np.float32),
                               elig, spec, f.spine.rf, era, holdings_out=h,
                               phase=ph)
            except RuntimeError as e:
                per[ph] = {"error": str(e)[:120]}
                continue
            per[ph] = {"cagr_net": out["diag"].get("cagr_net"),
                       "excess_cagr": out["diag"].get("excess_cagr"),
                       "turnover": out["diag"].get("turnover_1way_annual"),
                       "rebalances": out["diag"].get("rebalances")}
        res["phase"]["results"][a] = per
        got = [v.get("excess_cagr") for v in per.values()
               if isinstance(v.get("excess_cagr"), (int, float))]
        if got:
            print(f"  {a:16s} excess CAGR across 12 phases: "
                  f"{min(got):+.4f} .. {max(got):+.4f}  "
                  f"range {max(got) - min(got):.4f}", flush=True)
            res["phase"].setdefault("range_excess_cagr", {})[a] = round(
                float(max(got) - min(got)), 5)

    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "N1B_WHERE_DOES_THE_IC_LIVE.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(f"\nwritten. {res['runtime_secs']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
