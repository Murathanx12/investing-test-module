"""GRAND-ARENA-1 PHASE 1 — can our learners rediscover a rule we planted?

    python scripts/run_known_world_1.py                 # full sweep, resumable
    python scripts/run_known_world_1.py --worlds I L J  # negative controls only
    python scripts/run_known_world_1.py --fresh         # ignore the checkpoint

WHY THIS PHASE EXISTS. Before any learner is trusted to DISCOVER an exit rule, a
regime, or a specialist's reliability in a real market, it must first prove it
can REDISCOVER a rule planted by hand. A learner that cannot recover a known
answer has not earned the right to be believed when it reports an unknown one.
**This phase can fail, and a failure here invalidates the interpretation of
every other phase.** That is what it is for.

THE VERDICT RULES BELOW ARE PRE-REGISTERED. They were committed before the first
cell was scored (see `TRIALS/PREREG_GRAND_ARENA_KNOWN_WORLDS_1.md` and the git
history of this file). Nothing about a world is tuned to make a learner look
good; the worlds are verified against their own declared plant by
`known_worlds.verify()` and the run aborts on a world that is not what it claims.

CHECKPOINTING. One JSONL row per finished (world, learner) cell plus one .npy of
its out-of-sample scores. A crash three hours in resumes from the last finished
cell; it never restarts.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.arena import known_learners as KL           # noqa: E402
from aegis_brain.arena.known_worlds import (                 # noqa: E402
    FEATURES, WORLD_IDS, make_world, verify)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("known_world_1")

MODULE_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = MODULE_ROOT / "runs" / "known_world_1"
OUT_JSON = MODULE_ROOT / "data" / "factory" / "known_world_1_results.json"
CELLS = RUN_DIR / "cells.jsonl"
SEED = 20260812

# ═══════════════════════════════════════════════════════════════════════════
# PRE-REGISTERED DECISION RULES — fixed before any cell was scored
# ═══════════════════════════════════════════════════════════════════════════
#: A learner "uses" a feature when its out-of-sample score correlates with that
#: feature by at least this much, cross-sectionally, on average.
USE_THRESHOLD = 0.10
#: A conditional mechanism (interaction / threshold / sector) counts as
#: recovered when the model's reliance on the signal differs between the two
#: sides of the condition by at least this much in Spearman units.
CONDITIONAL_GAP = 0.15
#: A learner claims skill for a decoy specialist when its reliance on that
#: decoy exceeds this anywhere.
DECOY_BOUND = 0.10
#: Bandit: share of pulls given to the true arm inside the skilled sector minus
#: the share given to it elsewhere.
BANDIT_GAP = 0.25
#: Bandit: an arm share above this in a sector where the arm has no skill is a
#: claim of skill (uniform over 4 arms is 0.25).
BANDIT_DECOY_BOUND = 0.45
#: World K: replacement share when the staleness state fires minus when it does
#: not, and the ceiling on the share of actions that reach for cash.
K_REPLACE_GAP = 0.25
K_CASH_CEILING = 0.10

VERDICTS = ("RECOVERED", "PARTIAL", "MISSED", "FALSE-POSITIVE", "CORRECT-NULL")

#: Worlds whose correct answer is "nothing here". A learner that clears its MDE
#: in ANY direction on the primary metric of one of these has failed, and that
#: failure matters more than any success elsewhere.
NULL_WORLDS = {"I", "L"}
#: World J is a null on its NET metric and a signal on its GROSS metric.

XS_WORLDS = ["A", "B", "C", "E", "F", "G", "H", "I", "J"]
EXPOSURE_WORLDS = ["D", "L"]
ACTION_WORLDS = ["K"]
BANDIT_WORLDS = ["A", "B", "G", "H", "I"]

SPLIT = dict(n_folds=8, min_train=96, embargo=3, horizon=1)


# ═══════════════════════════════════════════════════════════════════════════
def _mask(p: pd.DataFrame, expr) -> np.ndarray:
    return expr.to_numpy() if isinstance(expr, pd.Series) else expr


def _corr_in(score, panel, col, mask) -> float:
    d = panel[mask]
    s = pd.Series(score[mask], index=d.index)
    v = d.groupby("t").apply(
        lambda g: pd.Series(s.loc[g.index]).corr(g[col], method="spearman"),
        include_groups=False)
    return float(v.mean())


def mechanism_check(world, panel: pd.DataFrame, score: np.ndarray) -> dict:
    """World-specific recovery probe. Model-agnostic: it reads only the score."""
    w = world.world_id
    fc = KL.score_feature_corr(score, panel)
    top = max(fc, key=lambda k: abs(fc[k]))
    out = {"feature_corr": fc, "top_feature": top,
           "top_feature_corr": fc[top], "ok": False, "why": ""}

    if w == "A":
        out["ok"] = top == "f_mom" and fc["f_mom"] > USE_THRESHOLD
        out["why"] = "top feature must be f_mom with a POSITIVE loading"
    elif w == "B":
        out["ok"] = top == "f_mom" and fc["f_mom"] < -USE_THRESHOLD
        out["why"] = "top feature must be f_mom with a NEGATIVE loading"
    elif w == "C":
        s0, s1 = panel["true_state"] == 0, panel["true_state"] == 1
        gm = _corr_in(score, panel, "f_mom", s0) - _corr_in(score, panel, "f_mom", s1)
        gv = _corr_in(score, panel, "f_val", s1) - _corr_in(score, panel, "f_val", s0)
        out.update({"mom_gap_state0_minus_state1": round(gm, 4),
                    "val_gap_state1_minus_state0": round(gv, 4)})
        out["ok"] = gm > CONDITIONAL_GAP and gv > CONDITIONAL_GAP
        out["why"] = ("must lean on f_mom in state 0 and f_val in state 1, "
                      f"each by > {CONDITIONAL_GAP}")
    elif w == "E":
        on = _corr_in(score, panel, "f_mom", panel["f_rev"] > 0)
        off = _corr_in(score, panel, "f_mom", panel["f_rev"] <= 0)
        out.update({"mom_corr_rev_on": round(on, 4), "mom_corr_rev_off": round(off, 4),
                    "gap": round(on - off, 4)})
        out["ok"] = (on - off) > CONDITIONAL_GAP
        out["why"] = f"momentum reliance must be > {CONDITIONAL_GAP} higher when f_rev > 0"
    elif w == "F":
        lo = _corr_in(score, panel, "f_mom", panel["f_val"] < 0.8)
        hi = _corr_in(score, panel, "f_mom", panel["f_val"] >= 0.8)
        out.update({"mom_corr_cheap": round(lo, 4), "mom_corr_expensive": round(hi, 4),
                    "gap": round(lo - hi, 4)})
        out["ok"] = (lo - hi) > CONDITIONAL_GAP
        out["why"] = f"momentum reliance must flip across f_val = 0.8 by > {CONDITIONAL_GAP}"
    elif w in ("G", "H"):
        col = world.truth["specialist"]
        dec = world.truth["decoy_specialist"]
        sec = world.truth["skilled_sector"]
        a = _corr_in(score, panel, col, panel["sector_id"] == sec)
        b = _corr_in(score, panel, col, panel["sector_id"] != sec)
        dmax = max(abs(_corr_in(score, panel, dec, panel["sector_id"] == s))
                   for s in sorted(panel["sector_id"].unique()))
        out.update({f"{col}_in_sector": round(a, 4), f"{col}_elsewhere": round(b, 4),
                    "gap": round(a - b, 4), f"max_{dec}_reliance": round(dmax, 4)})
        out["ok"] = (a - b) > CONDITIONAL_GAP and dmax < DECOY_BOUND
        out["why"] = (f"must follow {col} in {world.truth['skilled_sector_name']} "
                      f"and not claim {dec} anywhere")
    elif w == "J":
        out["ok"] = top == "f_rev" and fc["f_rev"] > USE_THRESHOLD
        out["why"] = "top feature must be the fast signal f_rev, positively"
    elif w == "I":
        out["ok"] = None
        out["why"] = "no mechanism exists — the null verdict is the whole test"
    return out


def verdict_xs(world, ic: dict, mech: dict, net: dict | None) -> tuple[str, str]:
    w = world.world_id
    if w in NULL_WORLDS:
        if ic["detected"]:
            return "FALSE-POSITIVE", (
                f"found an out-of-sample IC of {ic['mean']:+.4f} against an MDE "
                f"of {ic['mde']:.4f} in a world where nothing predicts anything")
        return "CORRECT-NULL", (
            f"IC {ic['mean']:+.4f} is inside its MDE of {ic['mde']:.4f} — the "
            "correct answer, which is nothing")
    if ic["detected"] and ic["mean"] < 0:
        return "FALSE-POSITIVE", (
            f"systematically ANTI-predictive out of sample: IC {ic['mean']:+.4f} "
            f"vs MDE {ic['mde']:.4f}")
    if w == "J":
        if not ic["detected"]:
            return "MISSED", (f"gross IC {ic['mean']:+.4f} below its MDE "
                              f"{ic['mde']:.4f}")
        if net and net["detected"] and net["mean"] > 0:
            return "FALSE-POSITIVE", (
                f"declared a NET edge of {net['mean']:+.4f}/yr against an MDE of "
                f"{net['mde']:.4f} — the costs were supposed to kill it")
        if not mech["ok"]:
            return "PARTIAL", "gross edge detected but the wrong feature carries it"
        return "RECOVERED", (
            f"gross IC {ic['mean']:+.4f} > MDE {ic['mde']:.4f}, and the net "
            f"spread {net['mean']:+.4f}/yr does not clear its MDE "
            f"{net['mde']:.4f} — correctly not tradeable")
    if not ic["detected"]:
        return "MISSED", f"IC {ic['mean']:+.4f} below its MDE {ic['mde']:.4f}"
    if mech["ok"]:
        return "RECOVERED", (f"IC {ic['mean']:+.4f} > MDE {ic['mde']:.4f} and the "
                             f"mechanism probe passed ({mech['why']})")
    return "PARTIAL", (f"IC {ic['mean']:+.4f} > MDE {ic['mde']:.4f} but the "
                       f"mechanism was not recovered ({mech['why']})")


# ═══════════════════════════════════════════════════════════════════════════
def run_xs_cell(world, learner: str) -> dict:
    p = world.panel.sort_values(["t", "name"]).reset_index(drop=True)
    folds = KL.purged_walk_forward(int(p["t"].max()), **SPLIT)
    fn = KL.XS_LEARNERS[learner]
    scores = np.full(len(p), np.nan)
    t = p["t"].to_numpy()
    hmm_states = {}
    for f in folds:
        tr = p[np.isin(t, f.train_t)]
        te_mask = np.isin(t, f.test_t)
        te = p[te_mask]
        s = fn(tr, te, SEED + f.k)
        scores[te_mask] = s
        if learner == "hmm_regime" and hasattr(KL.learn_hmm_regime, "last_states"):
            hmm_states.update(KL.learn_hmm_regime.last_states[1])
    ok = ~np.isnan(scores)
    pe, sc = p[ok].reset_index(drop=True), scores[ok]

    ic_s = KL.monthly_ic(sc, pe["y"].to_numpy(), pe["t"].to_numpy())
    ic = KL.effect_block(ic_s, label="oos_monthly_ic", unit="spearman ic")
    cost = world.meta.get("cost_bps_one_way", 0.0)
    g_s, n_s, turn = KL.decile_spread(sc, pe["y"].to_numpy(), pe["t"].to_numpy(),
                                      cost_bps=cost)
    gross = KL.effect_block(g_s, label="oos_quintile_spread_gross",
                            unit="return", annualize=True)
    net = KL.effect_block(n_s, label="oos_quintile_spread_net",
                          unit="return", annualize=True) if cost else None
    mech = mechanism_check(world, pe, sc)
    v, why = verdict_xs(world, ic, mech, net)
    extra = {}
    if learner == "hmm_regime" and hmm_states and world.world_id == "C":
        st = pe["t"].map(hmm_states)
        true = pe["true_state"]
        keep = st.notna()
        acc = float((st[keep] == true[keep]).mean())
        extra["hmm_state_accuracy"] = round(max(acc, 1 - acc), 4)
        extra["hmm_state_accuracy_mde"] = round(
            2.0 * np.sqrt(0.25 / pe["t"].nunique()), 4)
    return {"world": world.world_id, "learner": learner, "kind": "xs",
            "verdict": v, "why": why, "primary": ic, "spread_gross": gross,
            "spread_net": net, "turnover_1way": round(turn, 3),
            "mechanism": mech, "extra": extra,
            "_scores": sc, "_rows": int(len(pe))}


def run_exposure_cell(world, learner: str) -> dict:
    m = KL._mkt_frame(world)
    folds = KL.purged_walk_forward(int(m["t"].max()), **SPLIT)
    fn = KL.EXPOSURE_LEARNERS[learner]
    w = np.full(len(m), np.nan)
    for f in folds:
        tr = m[m["t"].isin(f.train_t)]
        te_mask = m["t"].isin(f.test_t).to_numpy()
        te = m[te_mask]
        if len(te) == 0:
            continue
        w[te_mask] = fn(tr, te, SEED + f.k)
    ok = ~np.isnan(w)
    me, we = m[ok].reset_index(drop=True), w[ok]
    y = me["y_mkt"].to_numpy()

    w_bar = float(we.mean())                     # MATCHED average exposure
    d = pd.Series((we - w_bar) * y, index=me["t"])
    imp = KL.effect_block(d, label="timing_gain_vs_matched_static",
                          unit="return", annualize=True)
    # did the de-risking actually land on the bad months?
    derisk = pd.Series(w_bar - we)
    shock = me["y_shock"].to_numpy() if "y_shock" in me else np.zeros(len(me))
    auc = float("nan")
    if shock.sum() > 5:
        from aegis_brain.arena.known_worlds import _auc
        auc = _auc(derisk.to_numpy(), shock)
    # AUC's own MDE, from the normal approximation to the Mann-Whitney SE
    n1 = int(shock.sum())
    n0 = int(len(shock) - n1)
    auc_mde = (2.0 * np.sqrt((n0 + n1 + 1) / (12.0 * max(n0 * n1, 1)))
               if n1 and n0 else None)
    port = pd.Series(we * y)
    stat = pd.Series(w_bar * y)
    diag = {
        "mean_exposure": round(w_bar, 4),
        "exposure_sd": round(float(np.std(we, ddof=1)), 4),
        "frac_months_zero_exposure": round(float((we <= 0.02).mean()), 4),
        "frac_months_full_exposure": round(float((we >= 0.98).mean()), 4),
        "sharpe_policy_ann": round(float(port.mean() / port.std(ddof=1) * np.sqrt(12)), 3),
        "sharpe_static_ann": round(float(stat.mean() / stat.std(ddof=1) * np.sqrt(12)), 3),
        "derisk_vs_shock_auc": None if not np.isfinite(auc) else round(auc, 4),
        "derisk_auc_mde": None if auc_mde is None else round(auc_mde, 4),
        "n_shock_months_in_test": n1,
    }
    if world.world_id == "L":
        v = ("FALSE-POSITIVE" if imp["detected"] else "CORRECT-NULL")
        why = (f"timing gain {imp['mean']:+.4f}/yr vs MDE {imp['mde']:.4f} at "
               "matched average exposure — " +
               ("an edge that is not there" if imp["detected"]
                else "correctly nothing"))
        mech = {"ok": None, "why": "no timing edge exists in this world"}
    else:
        timing_ok = (auc_mde is not None and np.isfinite(auc)
                     and (auc - 0.5) > auc_mde)
        mech = {"ok": bool(timing_ok),
                "why": "de-risking must land on the shock months (AUC above its MDE)",
                "auc": diag["derisk_vs_shock_auc"], "auc_mde": diag["derisk_auc_mde"]}
        if imp["detected"] and imp["mean"] < 0:
            v, why = "FALSE-POSITIVE", (
                f"timing SUBTRACTED {imp['mean']:+.4f}/yr against an MDE of "
                f"{imp['mde']:.4f} — worse than doing nothing, detectably")
        elif not imp["detected"]:
            v, why = "MISSED", (f"timing gain {imp['mean']:+.4f}/yr is inside its "
                                f"MDE of {imp['mde']:.4f}")
        elif timing_ok:
            v, why = "RECOVERED", (
                f"gain {imp['mean']:+.4f}/yr > MDE {imp['mde']:.4f} and the "
                f"de-risking landed on the shocks (AUC {auc:.3f} > 0.5 + "
                f"{auc_mde:.3f})")
        else:
            v, why = "PARTIAL", (f"gain {imp['mean']:+.4f}/yr > MDE "
                                 f"{imp['mde']:.4f} but the de-risking did not "
                                 f"land on the shock months")
    return {"world": world.world_id, "learner": learner, "kind": "exposure",
            "verdict": v, "why": why, "primary": imp, "mechanism": mech,
            "diagnostics": diag, "_scores": we, "_rows": int(len(me))}


def run_action_cell(world, learner: str) -> dict:
    logs = KL.build_k_logs(world, seed=SEED)
    folds = KL.purged_walk_forward(int(logs["t"].max()), **SPLIT)
    fn = KL.ACTION_LEARNERS[learner]
    act = np.array([None] * len(logs), dtype=object)
    for f in folds:
        tr = logs[logs["t"].isin(f.train_t)]
        te_mask = logs["t"].isin(f.test_t).to_numpy()
        if te_mask.sum() == 0 or len(tr) < 500:
            continue
        act[te_mask] = fn(tr, logs[te_mask], SEED + f.k)
    ok = act != None                                            # noqa: E711
    d = logs[ok].reset_index(drop=True)
    a = act[ok]
    R = d[["r_hold", "r_cash", "r_replace"]].to_numpy()
    ai = np.array([{"hold": 0, "cash": 1, "replace": 2}[x] for x in a])
    r_pol = R[np.arange(len(R)), ai]
    by_t = pd.DataFrame({"t": d["t"], "pol": r_pol, "hold": R[:, 0],
                         "cash": R[:, 1], "rep": R[:, 2],
                         "oracle": R.max(axis=1)}).groupby("t").mean()
    imp = KL.effect_block(by_t["pol"] - by_t["hold"],
                          label="policy_gain_vs_always_hold", unit="return",
                          annualize=True)
    vs_cash = KL.effect_block(by_t["pol"] - by_t["cash"],
                              label="policy_gain_vs_always_cash", unit="return",
                              annualize=True)
    vs_rep = KL.effect_block(by_t["pol"] - by_t["rep"],
                             label="policy_gain_vs_always_replace",
                             unit="return", annualize=True)
    stale = (d["f_qual"] < world.truth["stale_threshold"]).to_numpy()
    shares = {f"share_{x}": round(float((a == x).mean()), 4) for x in KL.ACTIONS}
    rep_gap = float((a[stale] == "replace").mean() - (a[~stale] == "replace").mean())
    diag = {**shares, "replace_share_when_stale": round(
        float((a[stale] == "replace").mean()), 4),
        "replace_share_when_fresh": round(
            float((a[~stale] == "replace").mean()), 4),
        "replace_gap": round(rep_gap, 4),
        "oracle_gain_vs_hold_ann": round(
            float((by_t["oracle"] - by_t["hold"]).mean() * 12), 4),
        "always_replace_gain_vs_hold_ann": round(
            float((by_t["rep"] - by_t["hold"]).mean() * 12), 4),
        "always_cash_gain_vs_hold_ann": round(
            float((by_t["cash"] - by_t["hold"]).mean() * 12), 4)}
    mech_ok = rep_gap > K_REPLACE_GAP and shares["share_cash"] <= K_CASH_CEILING
    mech = {"ok": bool(mech_ok), "replace_gap": round(rep_gap, 4),
            "cash_share": shares["share_cash"],
            "why": (f"replacement must be chosen at least {K_REPLACE_GAP} more "
                    f"often when the name is stale, and cash must stay under "
                    f"{K_CASH_CEILING} of all actions")}
    if imp["detected"] and imp["mean"] < 0:
        v, why = "FALSE-POSITIVE", (f"policy LOST {imp['mean']:+.4f}/yr vs simply "
                                    f"holding, against an MDE of {imp['mde']:.4f}")
    elif not imp["detected"]:
        v, why = "MISSED", (f"gain over always-hold {imp['mean']:+.4f}/yr is "
                            f"inside its MDE of {imp['mde']:.4f}")
    elif mech_ok:
        v, why = "RECOVERED", (
            f"gain {imp['mean']:+.4f}/yr > MDE {imp['mde']:.4f}, replacement "
            f"chosen {rep_gap:+.2f} more often on stale names, cash share "
            f"{shares['share_cash']:.2f}")
    else:
        v, why = "PARTIAL", (f"gain {imp['mean']:+.4f}/yr > MDE {imp['mde']:.4f} "
                             f"but the conditional replacement rule was not "
                             f"recovered (gap {rep_gap:+.2f}, cash share "
                             f"{shares['share_cash']:.2f})")
    return {"world": world.world_id, "learner": learner, "kind": "action",
            "verdict": v, "why": why, "primary": imp,
            "secondary": {"vs_always_cash": vs_cash, "vs_always_replace": vs_rep},
            "mechanism": mech, "diagnostics": diag,
            "_scores": ai.astype(float), "_rows": int(len(d))}


def run_bandit_cell(world) -> dict:
    folds = KL.purged_walk_forward(int(world.panel["t"].max()), **SPLIT)
    test_t = np.concatenate([f.test_t for f in folds])
    res = KL.run_linucb(world, seed=SEED, test_t=test_t)
    d = res["picks"]
    by_t = d.groupby("t")[["reward", "uniform_reward"]].mean()
    imp = KL.effect_block(by_t["reward"] - by_t["uniform_reward"],
                          label="bandit_gain_vs_uniform_arm", unit="return",
                          annualize=True)
    shares = (d.groupby(["sector_id", "arm"]).size()
              / d.groupby("sector_id").size()).unstack(fill_value=0.0)
    share_tab = {int(s): {a: round(float(shares.loc[s].get(a, 0.0)), 3)
                          for a in KL.BANDIT_ARMS} for s in shares.index}
    w = world.world_id
    mech = {"shares_by_sector": share_tab}
    if w in ("G", "H"):
        col, sec = world.truth["specialist"], world.truth["skilled_sector"]
        dec = world.truth["decoy_specialist"]
        in_s = share_tab[sec][col]
        out_s = float(np.mean([share_tab[s][col] for s in share_tab if s != sec]))
        dmax = max(share_tab[s][dec] for s in share_tab)
        mech.update({"true_arm_share_in_sector": in_s,
                     "true_arm_share_elsewhere": round(out_s, 3),
                     "gap": round(in_s - out_s, 3),
                     f"max_{dec}_share": dmax})
        mech["ok"] = (in_s - out_s) > BANDIT_GAP and dmax < BANDIT_DECOY_BOUND
        mech["why"] = (f"must concentrate {col} pulls in "
                       f"{world.truth['skilled_sector_name']} and not "
                       f"over-allocate to {dec} anywhere")
    elif w == "A":
        sh = float(np.mean([share_tab[s]["f_mom"] for s in share_tab]))
        mech.update({"f_mom_share": round(sh, 3), "ok": sh > 0.40,
                     "why": "momentum genuinely pays everywhere — follow it"})
    elif w == "B":
        sh = float(np.mean([share_tab[s]["f_mom"] for s in share_tab]))
        mech.update({"f_mom_share": round(sh, 3), "ok": sh < 0.30,
                     "why": ("momentum is anti-predictive and the arms are "
                             "long-only tilts — the correct behaviour is to "
                             "stop pulling it")})
    else:
        mech.update({"ok": None, "why": "null world — no arm has skill"})

    if w in NULL_WORLDS:
        v = "FALSE-POSITIVE" if imp["detected"] else "CORRECT-NULL"
        why = (f"bandit gain {imp['mean']:+.4f}/yr vs the uniform-arm control, "
               f"MDE {imp['mde']:.4f}")
    elif imp["detected"] and imp["mean"] < 0:
        v, why = "FALSE-POSITIVE", (f"bandit did detectably WORSE than pulling "
                                    f"arms at random ({imp['mean']:+.4f}/yr)")
    elif not imp["detected"]:
        v, why = "MISSED", (f"gain {imp['mean']:+.4f}/yr inside its MDE "
                            f"{imp['mde']:.4f}")
    elif mech.get("ok"):
        v, why = "RECOVERED", (f"gain {imp['mean']:+.4f}/yr > MDE {imp['mde']:.4f} "
                               f"with the right allocation ({mech['why']})")
    else:
        v, why = "PARTIAL", (f"gain {imp['mean']:+.4f}/yr > MDE {imp['mde']:.4f} "
                             f"but the allocation is wrong ({mech['why']})")
    return {"world": w, "learner": "contextual_bandit", "kind": "bandit",
            "verdict": v, "why": why, "primary": imp, "mechanism": mech,
            "_scores": by_t["reward"].to_numpy(), "_rows": int(len(d))}


# ═══════════════════════════════════════════════════════════════════════════
def planned_cells() -> list[tuple[str, str, str]]:
    cells = []
    for w in XS_WORLDS:
        for ln in KL.XS_LEARNERS:
            cells.append((w, ln, "xs"))
    for w in EXPOSURE_WORLDS:
        for ln in KL.EXPOSURE_LEARNERS:
            cells.append((w, ln, "exposure"))
    for w in ACTION_WORLDS:
        for ln in KL.ACTION_LEARNERS:
            cells.append((w, ln, "action"))
    for w in BANDIT_WORLDS:
        cells.append((w, "contextual_bandit", "bandit"))
    return cells


def load_done() -> dict:
    done = {}
    if CELLS.exists():
        for line in CELLS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r["world"], r["learner"])] = r
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worlds", nargs="*", default=None)
    ap.add_argument("--learners", nargs="*", default=None)
    ap.add_argument("--fresh", action="store_true")
    a = ap.parse_args()

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    if a.fresh and CELLS.exists():
        CELLS.unlink()

    # ── worlds first, and they must be what they claim ──────────────────────
    worlds, ver = {}, {}
    for wid in WORLD_IDS:
        if a.worlds and wid not in a.worlds:
            continue
        worlds[wid] = make_world(wid)
        ver[wid] = verify(worlds[wid])
        state = "verified" if ver[wid]["ok"] else "*** WORLD FAILED ITS OWN CHECK ***"
        log.info("world %s %s  %s", wid, state, json.dumps(ver[wid]["checks"]))
    bad = [k for k, v in ver.items() if not v["ok"]]
    if bad:
        log.error("refusing to score learners on unverified worlds: %s", bad)
        return 2
    (RUN_DIR / "world_verification.json").write_text(
        json.dumps(ver, indent=2), encoding="utf-8")

    done = load_done()
    todo = [c for c in planned_cells()
            if (not a.worlds or c[0] in a.worlds)
            and (not a.learners or c[1] in a.learners)
            and (c[0], c[1]) not in done]
    log.info("%d cells planned, %d already finished, %d to run",
             len(planned_cells()), len(done), len(todo))

    for i, (wid, ln, kind) in enumerate(todo, 1):
        t0 = time.time()
        try:
            if kind == "xs":
                r = run_xs_cell(worlds[wid], ln)
            elif kind == "exposure":
                r = run_exposure_cell(worlds[wid], ln)
            elif kind == "action":
                r = run_action_cell(worlds[wid], ln)
            else:
                r = run_bandit_cell(worlds[wid])
        except Exception as exc:                      # a crash is a finding too
            log.exception("cell %s/%s FAILED", wid, ln)
            r = {"world": wid, "learner": ln, "kind": kind, "verdict": "ERROR",
                 "why": f"{type(exc).__name__}: {exc}", "_scores": np.array([]),
                 "_rows": 0}
        sc = r.pop("_scores")
        np.save(RUN_DIR / f"scores_{wid}_{ln}.npy", np.asarray(sc, dtype=np.float64))
        r["seconds"] = round(time.time() - t0, 1)
        with CELLS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(r, default=float) + "\n")
        log.info("[%d/%d] %s / %-18s -> %-14s %5.1fs  %s", i, len(todo), wid, ln,
                 r["verdict"], r["seconds"], r["why"][:110])

    aggregate(worlds, ver)
    return 0


# ═══════════════════════════════════════════════════════════════════════════
def batch_self_check(cells: list[dict]) -> dict:
    """CANON §20 — the batch is checked against itself.

    Two questions. How many cells cleared their MDE in a world where nothing was
    planted, against how many a nominal 5% rule would produce by chance? And how
    many of these learners are actually DISTINCT — seven learners whose
    out-of-sample scores correlate at 0.9 are not seven independent chances to
    find something, and treating them as such is how a batch manufactures a
    discovery.
    """
    null_cells = [c for c in cells if c["world"] in NULL_WORLDS
                  or (c["world"] == "J" and c.get("spread_net"))]
    fp = [c for c in cells if c["verdict"] == "FALSE-POSITIVE"]
    nulls = [c for c in cells if c["world"] in NULL_WORLDS]
    # effective distinct learners per world, from the OOS score correlations
    eff = {}
    for wid in sorted({c["world"] for c in cells if c["kind"] == "xs"}):
        vecs = {}
        for c in cells:
            if c["world"] != wid or c["kind"] != "xs":
                continue
            f = RUN_DIR / f"scores_{wid}_{c['learner']}.npy"
            if f.exists():
                v = np.load(f)
                if v.size:
                    vecs[c["learner"]] = v
        if len(vecs) < 2:
            continue
        keys = sorted(vecs)
        n = min(len(vecs[k]) for k in keys)
        M = np.column_stack([vecs[k][:n] for k in keys])
        C = np.corrcoef(M, rowvar=False)
        off = C[np.triu_indices(len(keys), 1)]
        rho = float(np.nanmean(np.abs(off)))
        eff[wid] = {"n_learners": len(keys), "mean_abs_pairwise_corr": round(rho, 3),
                    "effective_distinct": round(len(keys) / (1 + (len(keys) - 1) * rho), 2)}
    med = float(np.median([v["effective_distinct"] for v in eff.values()])) if eff else None
    return {
        "n_cells": len(cells),
        "n_null_world_cells": len(nulls),
        "n_false_positive_cells": len(fp),
        "false_positive_cells": [f"{c['world']}/{c['learner']}" for c in fp],
        "expected_false_positives_at_nominal_5pct":
            round(0.0455 * len(nulls), 2),
        "effective_distinct_learners_by_world": eff,
        "median_effective_distinct_learners": med,
        "note": ("the nominal expectation assumes independent cells. The "
                 "effective-distinct count says they are not, so the honest "
                 "expected count is lower than the nominal one and a single "
                 "false positive is worth more than it looks."),
    }


def aggregate(worlds: dict, ver: dict) -> None:
    cells = list(load_done().values())
    matrix: dict[str, dict[str, str]] = {}
    for c in cells:
        matrix.setdefault(c["world"], {})[c["learner"]] = c["verdict"]
    counts: dict[str, int] = {}
    for c in cells:
        counts[c["verdict"]] = counts.get(c["verdict"], 0) + 1

    # which learners are trustworthy: no false positive anywhere, and recovery
    # in the worlds where recovery was possible
    per_learner = {}
    for ln in sorted({c["learner"] for c in cells}):
        mine = [c for c in cells if c["learner"] == ln]
        fp = [c["world"] for c in mine if c["verdict"] == "FALSE-POSITIVE"]
        rec = [c["world"] for c in mine if c["verdict"] == "RECOVERED"]
        par = [c["world"] for c in mine if c["verdict"] == "PARTIAL"]
        mis = [c["world"] for c in mine if c["verdict"] == "MISSED"]
        cn = [c["world"] for c in mine if c["verdict"] == "CORRECT-NULL"]
        per_learner[ln] = {
            "cells": len(mine), "recovered": rec, "partial": par, "missed": mis,
            "correct_null": cn, "false_positive": fp,
            "clean_on_negative_controls": len(fp) == 0,
        }
    out = {
        "phase": "GRAND-ARENA-1 PHASE 1 — known-answer worlds",
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "seed": SEED,
        "split": {**SPLIT, "scheme": "expanding-window purged+embargoed walk-forward"},
        "preregistered_thresholds": {
            "t_bar": KL.T_BAR, "use_threshold": USE_THRESHOLD,
            "conditional_gap": CONDITIONAL_GAP, "decoy_bound": DECOY_BOUND,
            "bandit_gap": BANDIT_GAP, "bandit_decoy_bound": BANDIT_DECOY_BOUND,
            "k_replace_gap": K_REPLACE_GAP, "k_cash_ceiling": K_CASH_CEILING,
            "mde_rule": "MDE = t_bar x max(HAC, IID) standard error (CANON §19)",
        },
        "worlds": {w: {**worlds[w].as_dict(), "verification": ver[w]}
                   for w in worlds} if worlds else {},
        "recovery_matrix": matrix,
        "verdict_counts": counts,
        "negative_controls": {
            "worlds": sorted(NULL_WORLDS) + ["J (net leg)"],
            "cells": [{k: c[k] for k in ("world", "learner", "verdict", "why")}
                      for c in cells
                      if c["world"] in NULL_WORLDS or c["world"] == "J"],
        },
        "per_learner": per_learner,
        "batch_self_check_canon_20": batch_self_check(cells),
        "cells": cells,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    log.info("wrote %s (%d cells)", OUT_JSON, len(cells))
    for w in sorted(matrix):
        log.info("  %s: %s", w, json.dumps(matrix[w]))


if __name__ == "__main__":
    raise SystemExit(main())
