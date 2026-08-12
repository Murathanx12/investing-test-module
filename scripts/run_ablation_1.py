"""ABLATION-1 — the six-arm placebo ladder and the component ablation.

    python -m scripts.run_ablation_1

THE SYSTEM BEING ABLATED, DEFINED ONCE
======================================
`Full` is the mean of five z-scored legs, each of which is a thing a component
supplies:

    L1 quant_base   z(the shipping per-stock signal stack, arena_systems.P5)
    L2 event        z(SUE within 21 trading days of the announcement)
    L3 revisions    z(the NIGHT-11 analyst-revision score)
    L4 regime       a regime-conditional tilt: momentum in risk-on,
                    low-volatility in risk-off
    L5 llm          z(the five-role swarm's directional score)

An ablation removes exactly one leg — and, where the leg has a matching
specialist, that role is dropped from L5 too, because "no revisions" that
leaves an analyst-revisions specialist talking is not an ablation.

THE LADDER
----------
Arms 1 and 2 (shuffled, time-shifted) are permutations of the swarm's own
output and cost nothing. **Arm 1 is decisive**: it holds the exact multiset of
scores and confidences fixed and permutes only WHICH security and date each one
belongs to. If Full ≈ shuffled, the content is doing nothing and the noise is
doing everything.

EVERY NUMBER HERE IS `ARCHITECTURE_RESULT_ONLY` (Amendment A6).
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
_AF = Path("C:/Users/mrthn/aegis-finance")
if str(_AF) not in sys.path:
    sys.path.insert(0, str(_AF))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from scripts import arena_systems as S
from scripts.arena_core import (MDE_Z, SCALE_CLIP, Book, cagr, max_drawdown,
                                partial_rebalance, ruler)
from scripts.arena_llm_score import score_frame
from scripts.run_portfolio_arena_1 import exante, load_lc, pick

FACTORY = MODULE_ROOT / "data" / "factory"
CALLS = FACTORY / "arena_llm_calls.jsonl"
PANEL = FACTORY / "arena_panel.parquet"
MARKET = FACTORY / "arena_market.parquet"
LLM_CELLS = FACTORY / "arena_llm_cells.parquet"
AUX = FACTORY / "exit_lab_1_aux.npz"
OUT = FACTORY / "ablation_1.json"

K_PRIMARY = 10          # on a 40-name eligible set, 20 names is half the universe
K_SECOND = 20
WMAX = 0.20
N_PERM = 200
PERM_SEED = 20260812
SWARM_ROLES = ("company_fundamental", "analyst_revisions",
               "execution_momentum", "geopolitical", "skeptic")


# ── the legs ────────────────────────────────────────────────────────────────

def legs(d: pd.DataFrame, regime: str, llm: pd.Series | None) -> dict:
    age = pd.to_numeric(d["days_since_rdq"], errors="coerce")
    sue = pd.to_numeric(d["sue"], errors="coerce")
    out = {
        "quant_base": S.z(S.aegis_deterministic(d)),
        "event": S.z(sue.where(age <= 21, 0.0).fillna(0.0)),
        "revisions": S.z(d["rev_score"]),
        "regime": (S.z(d["mom_12_1"]) if regime == "risk_on"
                   else S.z(-pd.to_numeric(d["vol_252"], errors="coerce"))),
    }
    if llm is not None:
        out["llm"] = S.z(llm.reindex(d.index))
    return out


ARMS: dict[str, dict] = {
    # name                      legs dropped            roles dropped   llm source
    "full":                    dict(drop=(), roles=None, src="swarm"),
    "no_llm":                  dict(drop=("llm",), roles=None, src="swarm"),
    "no_news":                 dict(drop=("event",), roles=None, src="swarm"),
    "no_geopolitical":         dict(drop=(), roles=("geopolitical",),
                                    src="swarm"),
    "no_revisions":            dict(drop=("revisions",),
                                    roles=("analyst_revisions",), src="swarm"),
    "no_regime":               dict(drop=("regime",), roles=None, src="swarm"),
    "no_quant":                dict(drop=("quant_base", "event", "revisions",
                                          "regime"), roles=None, src="swarm"),
    "generic_instead_of_swarm": dict(drop=(), roles=None, src="generic"),
    "llm_only_swarm":          dict(drop=("quant_base", "event", "revisions",
                                          "regime"), roles=None, src="swarm"),
    "llm_only_generic":        dict(drop=("quant_base", "event", "revisions",
                                          "regime"), roles=None, src="generic"),
    "randtext":                dict(drop=("quant_base", "event", "revisions",
                                          "regime"), roles=None,
                                    src="randtext"),
    # P8 in the arena's numbering: reliability-weighted LLM + Aegis. Under A5
    # the specialist weights are NEUTRAL, so the only thing separating it from
    # P7 (`full`) is the model's own stated confidence.
    "p8_confidence_weighted":  dict(drop=(), roles=None, src="swarm",
                                    conf=True),
    "full_randtext":           dict(drop=(), roles=None, src="randtext"),
}

DECLARED_NON_RUN = {
    "no_options": ("There is no point-in-time options-implied panel joined to "
                   "this spine. OptionMetrics files exist in data/wrds_raw but "
                   "are not linked to the arena cache, and the production "
                   "signal stack's `options_iv` weight (0.12) is one of the "
                   "five branches recorded unavailable in arena_systems. "
                   "Inventing the panel is not permitted."),
    "no_why_moved_experience": ("The WHY-MOVED experience memory is a 2026 "
                                "forward artefact. There is no 2015-2024 "
                                "memory to remove, so the arm cannot be run "
                                "and is not simulated."),
}


def swarm_score(sc: pd.DataFrame, src: str, drop_roles,
                conf_weighted: bool = False) -> pd.DataFrame:
    """(date_ix, permno) -> one score, from the requested source."""
    if src == "swarm":
        arm = "swarm"
    elif src == "generic":
        arm = "generic"
    else:
        arm = "randtext"
    v = sc[sc["arm"] == arm]
    if drop_roles and arm == "swarm":
        v = v[~v["specialist"].isin(drop_roles)]
    if conf_weighted:
        # P8. Amendment A5 forbids weighting a SPECIALIST from the unresolved
        # ledger; the model's own stated confidence is an OUTPUT of the call,
        # not an earned reliability, so it is the only non-neutral weight
        # available today. P8 - P7 therefore measures exactly one thing.
        v = v.copy()
        v["cw"] = v["conf"].fillna(v["conf"].mean())
        v["num"] = v["dir_mean"] * v["cw"]
        g = (v.groupby(["date_ix", "permno"])
             .agg(num=("num", "sum"), den=("cw", "sum"),
                  n_spec=("specialist", "nunique"),
                  conf=("conf", "mean")).reset_index())
        g["score"] = np.where(g["den"] > 0, g["num"] / g["den"], np.nan)
        return g[["date_ix", "permno", "score", "n_spec", "conf"]]
    g = (v.groupby(["date_ix", "permno"])
         .agg(score=("dir_mean", "mean"), n_spec=("specialist", "nunique"),
              conf=("conf", "mean")).reset_index())
    return g


def per_spec_frame_raw(calls: pd.DataFrame) -> pd.DataFrame:
    """Every directional forecast, un-aggregated — the horizon cuts need it."""
    rows = []
    for r in calls.itertuples():
        for f in (r.forecasts or []):
            sgn = {"return_sign": 1.0, "beats_benchmark": 1.0,
                   "drawdown_exceeds": -1.0}.get(f["observable"], 0.0)
            if sgn == 0.0:
                continue
            rows.append({"arm": r.arm, "specialist": r.specialist,
                         "date_ix": r.date_ix, "permno": r.permno,
                         "dir_mean": sgn * (2.0 * float(f["probability"]) - 1.0),
                         "horizon_days": int(f["horizon_days"])})
    return pd.DataFrame(rows)


def per_spec_frame(calls: pd.DataFrame) -> pd.DataFrame:
    """One row per (arm, date, name, specialist) — the level ablations act on."""
    rows = []
    for r in calls.itertuples():
        for f in (r.forecasts or []):
            sgn = {"return_sign": 1.0, "beats_benchmark": 1.0,
                   "drawdown_exceeds": -1.0}.get(f["observable"], 0.0)
            if sgn == 0.0:
                continue
            rows.append({"arm": r.arm, "specialist": r.specialist,
                         "date_ix": r.date_ix, "permno": r.permno,
                         "dir": sgn * (2.0 * float(f["probability"]) - 1.0),
                         "horizon_days": f["horizon_days"],
                         "conf": (float(r.confidence)
                                  if r.confidence is not None else np.nan)})
    f = pd.DataFrame(rows)
    return (f.groupby(["arm", "specialist", "date_ix", "permno"])
            .agg(dir_mean=("dir", "mean"), conf=("conf", "mean"))
            .reset_index())


# ── the simulator wrapper ───────────────────────────────────────────────────

def simulate(score_by_date: dict, by_date, mkt, dates_k, LC, dec_ix, mkt_log,
             K: int, matching: str = "raw", turnover_budget: float = 1.0,
             cost_mult: float = 1.0) -> pd.DataFrame:
    bk = Book(cost_mult=cost_mult)
    for k in dates_k:
        d = by_date[k]
        s = score_by_date.get(k)
        if s is None or len(s.dropna()) == 0:
            continue
        w = pick(s.reindex(d.index), K, WMAX)
        if len(w) == 0:
            continue
        cols = d.loc[w.index, "col"].to_numpy().astype(int)
        scale = 1.0
        if matching in ("beta", "vol"):
            vol, beta = exante(LC, dec_ix, mkt_log, k, cols, w.to_numpy())
            tgt = ((1.0 / beta) if (matching == "beta" and np.isfinite(beta)
                                    and beta > 0)
                   else (float(mkt.loc[k, "mkt_vol_252"]) / vol
                         if (matching == "vol" and vol > 0) else 1.0))
            scale = float(np.clip(tgt, *SCALE_CLIP))
        if matching == "turnover":
            w = partial_rebalance(w, bk.w, turnover_budget)
        bk.step(k, w, scale, ret=d["fwd_ret_1m"], hs_bps=d["hs_bps"],
                sig_d=d["vol_252"] / np.sqrt(252.0), adv=d["adv"],
                price=d["price"], r_cash=float(mkt.loc[k, "cash_fwd_1m"]))
    return bk.frame()


def summarise(fr: pd.DataFrame, mkt, dec_dates) -> dict:
    net = fr["net"].to_numpy()
    kk = fr["date_ix"].to_numpy()
    mm = mkt.loc[kk, "mkt_fwd_1m"].to_numpy()
    yy = np.array([dec_dates[int(x)].year for x in kk])
    return {
        "n_months": int(len(net)),
        "cagr_net_pct": round(cagr(net) * 100, 3),
        "excess_cagr_pct": round((cagr(net) - cagr(mm)) * 100, 3),
        "vol_ann_pct": round(float(np.std(net, ddof=1) * np.sqrt(12) * 100), 2),
        "max_drawdown_pct": round(max_drawdown(net) * 100, 2),
        "turnover_1way_mean": round(float(fr["turnover_1way"].mean()), 4),
        "cost_pct_per_year": round(float(fr["cost"].mean()) * 12 * 100, 3),
        "gross_exposure_mean": round(float(fr["gross_exposure"].mean()), 4),
        "eff_n_mean": round(float(fr["eff_n"].mean()), 2),
        "excess_ruler": ruler(net - mm, yy),
    }


def rank_ic(scores: dict, by_date, dates_k, dec_dates,
            min_names: int = 8) -> dict:
    """Per-date Spearman IC of the score against the forward month, with MDE."""
    from scipy.stats import spearmanr
    ics, yy = [], []
    for k in dates_k:
        s = scores.get(k)
        if s is None:
            continue
        d = by_date[k]
        v = s.reindex(d.index)
        m = np.isfinite(v.to_numpy()) & np.isfinite(d["fwd_ret_1m"].to_numpy())
        if m.sum() < min_names or np.nanstd(v.to_numpy()[m]) == 0:
            continue
        ic = spearmanr(v.to_numpy()[m], d["fwd_ret_1m"].to_numpy()[m]).statistic
        if np.isfinite(ic):
            ics.append(float(ic))
            yy.append(dec_dates[k].year)
    r = ruler(np.array(ics), np.array(yy), periods=1)
    mde = r.get("mde_ann_pct")
    return {"mean_ic": round(float(np.mean(ics)), 4) if ics else None,
            "n_dates": len(ics),
            # in IC UNITS, not percent: `ruler` annualises and scales by 100,
            # which is right for a return series and wrong for a correlation.
            "ic_mde": (round(mde / 100.0, 4) if mde is not None else None),
            "t": r.get("t"), "detectable": r.get("detectable"),
            "blocks": r.get("blocks"), "halves_agree": r.get("halves_agree")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--K", type=int, default=K_PRIMARY)
    ap.add_argument("--perm", type=int, default=N_PERM)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    t0 = time.time()

    calls = pd.read_json(CALLS, lines=True)
    print(f"{len(calls)} calls on disk", flush=True)
    ps = per_spec_frame(calls)
    _raw = per_spec_frame_raw(calls)
    _raw = _raw[_raw["arm"] == "swarm"]
    ps_h = {"short": _raw[_raw["horizon_days"] <= 20],
            "long": _raw[_raw["horizon_days"] > 20]}
    sc_all = score_frame(calls)

    panel = pd.read_parquet(PANEL)
    cells = pd.read_parquet(LLM_CELLS)[["date_ix", "permno"]]
    panel = panel.merge(cells, on=["date_ix", "permno"], how="inner")
    panel["log_mcap"] = np.log(panel["mcap"].clip(lower=1.0))
    panel["log_adv"] = np.log(panel["adv"].clip(lower=1.0))
    by_date = {int(k): g.set_index("permno") for k, g in panel.groupby("date_ix")}
    mkt = pd.read_parquet(MARKET).set_index("date_ix")
    dates_k = sorted(by_date)
    LC, dec_ix, mkt_log = load_lc()
    dec_dates = pd.DatetimeIndex(
        np.load(AUX, allow_pickle=False)["dec_dates"].astype("datetime64[ns]"))

    regime = {k: ("risk_on" if (float(mkt.loc[k, "mkt_ret_252"]) > 0
                                and float(mkt.loc[k, "mkt_dd_252"]) > -0.10)
                  else "risk_off") for k in dates_k}

    def arm_scores(spec: dict, llm_override: dict | None = None) -> dict:
        src = spec["src"]
        g = swarm_score(ps, src, spec.get("roles"),
                        conf_weighted=bool(spec.get("conf")))
        llm_by = {int(k): v.set_index("permno")["score"]
                  for k, v in g.groupby("date_ix")}
        if llm_override is not None:
            llm_by = llm_override
        out = {}
        for k in dates_k:
            d = by_date[k]
            L = legs(d, regime[k], llm_by.get(k))
            use = {n: v for n, v in L.items() if n not in spec["drop"]}
            if "llm" in spec["drop"]:
                use.pop("llm", None)
            if not use:
                continue
            out[k] = sum(use.values()) / len(use)
        return out

    results: dict[str, dict] = {}
    ic_out: dict[str, dict] = {}
    nets: dict[str, pd.DataFrame] = {}
    nets_gross: dict[str, pd.DataFrame] = {}
    for name, spec in ARMS.items():
        sco = arm_scores(spec)
        fr = simulate(sco, by_date, mkt, dates_k, LC, dec_ix, mkt_log, a.K)
        if len(fr) == 0:
            results[name] = {"status": "NO_MONTHS"}
            continue
        nets[name] = fr
        frg = simulate(sco, by_date, mkt, dates_k, LC, dec_ix, mkt_log, a.K,
                       cost_mult=0.0)
        nets_gross[name] = frg
        results[name] = {"raw": summarise(fr, mkt, dec_dates),
                         "gross_0x": summarise(frg, mkt, dec_dates)}
        ic_out[name] = rank_ic(sco, by_date, dates_k, dec_dates)
        print(f"  {name}: {results[name]['raw']['excess_cagr_pct']:+.2f}%/yr "
              f"excess, IC {ic_out[name]['mean_ic']}", flush=True)

    # A3 matchings on the arms that matter most
    for name in ("full", "no_llm", "llm_only_swarm", "generic_instead_of_swarm"):
        if name not in nets:
            continue
        sco = arm_scores(ARMS[name])
        tb = float(np.median([nets[n]["turnover_1way"].median() for n in nets]))
        for m in ("beta", "vol", "turnover"):
            fr = simulate(sco, by_date, mkt, dates_k, LC, dec_ix, mkt_log, a.K,
                          matching=m, turnover_budget=tb)
            results[name][m] = summarise(fr, mkt, dec_dates)

    # ── the paired differences that decide it ───────────────────────────────
    def paired(x: str, y: str, src: dict | None = None) -> dict:
        src = src if src is not None else nets
        if x not in src or y not in src:
            return {"status": "MISSING"}
        A = src[x].set_index("date_ix")["net"]
        B = src[y].set_index("date_ix")["net"]
        idx = A.index.intersection(B.index)
        yy = np.array([dec_dates[int(k)].year for k in idx])
        return ruler((A.loc[idx] - B.loc[idx]).to_numpy(), yy)

    pairs = {
        "full_minus_no_llm": paired("full", "no_llm"),
        "full_minus_generic": paired("full", "generic_instead_of_swarm"),
        "swarm_minus_generic": paired("llm_only_swarm", "llm_only_generic"),
        "llm_only_minus_randtext": paired("llm_only_swarm", "randtext"),
        "full_minus_full_randtext": paired("full", "full_randtext"),
        "P8_minus_P7_confidence_weighting":
            paired("p8_confidence_weighted", "full"),
        "GROSS_full_minus_no_llm": paired("full", "no_llm", nets_gross),
        "GROSS_swarm_minus_generic":
            paired("llm_only_swarm", "llm_only_generic", nets_gross),
        "GROSS_llm_only_minus_randtext":
            paired("llm_only_swarm", "randtext", nets_gross),
    }
    for name in ARMS:
        if name in ("full",) or name not in nets:
            continue
        pairs[f"full_minus_{name}"] = paired("full", name)

    # ── ARM 1: shuffled-LLM, the decisive one ───────────────────────────────
    g = swarm_score(ps, "swarm", None)
    base = {int(k): v.set_index("permno")["score"]
            for k, v in g.groupby("date_ix")}
    pool_keys = [(k, p) for k in base for p in base[k].index]
    pool_vals = np.array([float(base[k].loc[p]) for k, p in pool_keys])
    rng = np.random.default_rng(PERM_SEED)
    perm_excess, perm_ic = [], []
    for i in range(a.perm):
        v = rng.permutation(pool_vals)
        sh: dict[int, dict] = {}
        for (k, p), val in zip(pool_keys, v):
            sh.setdefault(k, {})[p] = val
        shp = {k: pd.Series(d) for k, d in sh.items()}
        sco = arm_scores(ARMS["full"], llm_override=shp)
        fr = simulate(sco, by_date, mkt, dates_k, LC, dec_ix, mkt_log, a.K)
        kk = fr["date_ix"].to_numpy()
        mm = mkt.loc[kk, "mkt_fwd_1m"].to_numpy()
        perm_excess.append((cagr(fr["net"].to_numpy()) - cagr(mm)) * 100)
        if i < 40:                       # IC permutation is the expensive one
            perm_ic.append(rank_ic(sco, by_date, dates_k, dec_dates)["mean_ic"])
        if (i + 1) % 25 == 0:
            print(f"  shuffled {i+1}/{a.perm} ({time.time()-t0:.0f}s)",
                  flush=True)
    pe = np.array(perm_excess, dtype=float)
    obs = results["full"]["raw"]["excess_cagr_pct"]
    shuffled = {
        "n_permutations": a.perm,
        "observed_full_excess_cagr_pct": obs,
        "shuffled_mean_pct": round(float(pe.mean()), 3),
        "shuffled_sd_pct": round(float(pe.std(ddof=1)), 3),
        "shuffled_p05_pct": round(float(np.percentile(pe, 5)), 3),
        "shuffled_p95_pct": round(float(np.percentile(pe, 95)), 3),
        "permutation_p_value_one_sided":
            round(float((pe >= obs).mean()), 4),
        "observed_minus_shuffled_mean_pct": round(float(obs - pe.mean()), 3),
        "ic_permutation": {
            "n": len([x for x in perm_ic if x is not None]),
            "mean": (round(float(np.nanmean([x for x in perm_ic
                                             if x is not None])), 4)
                     if perm_ic else None),
            "p95": (round(float(np.nanpercentile([x for x in perm_ic
                                                  if x is not None], 95)), 4)
                    if perm_ic else None),
            "observed": ic_out["full"]["mean_ic"],
        },
    }

    # ── ARM 2: time-shifted ─────────────────────────────────────────────────
    tshift = {}
    for kk_shift in (1, 3, 12):
        shifted = {}
        for k in dates_k:
            src = base.get(k - kk_shift)
            if src is not None:
                shifted[k] = src
        sco = arm_scores(ARMS["full"], llm_override=shifted)
        fr = simulate(sco, by_date, mkt, dates_k, LC, dec_ix, mkt_log, a.K)
        tshift[f"k={kk_shift}"] = summarise(fr, mkt, dec_dates)
        nets[f"timeshift_{kk_shift}"] = fr
        pairs[f"full_minus_timeshift_{kk_shift}"] = paired(
            "full", f"timeshift_{kk_shift}")

    # ── NARROW DOMAIN: where, if anywhere, does the LLM carry information? ──
    # A4/§8: "LLM helps only in a narrow domain or horizon" is a SUCCESS, not a
    # consolation, so the subsets are cut and reported whether or not the
    # overall answer is a null. All cuts are pre-declared: market-cap quintile
    # (the panel's own stratification), horizon band (the score is already
    # split at 20 trading days), and role.
    narrow: dict = {"by_size_quintile": {}, "by_horizon_band": {},
                    "by_role": {}}
    g_all = swarm_score(ps, "swarm", None)
    llm_by = {int(k): v.set_index("permno")["score"]
              for k, v in g_all.groupby("date_ix")}
    qcut = {}
    for k in dates_k:
        d = by_date[k]
        r = d["mcap"].rank(method="first", pct=True)
        qcut[k] = np.clip((r * 5).astype(int), 0, 4)
    for half, lo, hi in (("small_half", 0.0, 0.5), ("large_half", 0.5, 1.0)):
        sub = {}
        for k in dates_k:
            s_k = llm_by.get(k)
            if s_k is None:
                continue
            r = by_date[k]["mcap"].rank(method="first", pct=True)
            m = (r > lo) & (r <= hi)
            sub[k] = s_k.reindex(by_date[k].index).where(m.to_numpy())
        narrow.setdefault("by_size_half", {})[half] = rank_ic(
            sub, by_date, dates_k, dec_dates, min_names=12)
    for q in range(5):
        sub = {}
        for k in dates_k:
            s_k = llm_by.get(k)
            if s_k is None:
                continue
            m = qcut[k] == q
            sub[k] = s_k.reindex(by_date[k].index).where(m.to_numpy())
        narrow["by_size_quintile"][f"Q{q+1}"] = rank_ic(
            sub, by_date, dates_k, dec_dates, min_names=6)
    for band in ("short", "long"):
        col = f"dir_mean"
        hz = ps_h[band] if band in ps_h else None
        if hz is None:
            continue
        gg = (hz.groupby(["date_ix", "permno"])["dir_mean"].mean()
              .reset_index())
        sub = {int(k): v.set_index("permno")["dir_mean"]
               for k, v in gg.groupby("date_ix")}
        narrow["by_horizon_band"][band] = rank_ic(sub, by_date, dates_k,
                                                  dec_dates)
    for role in SWARM_ROLES:
        v = ps[(ps["arm"] == "swarm") & (ps["specialist"] == role)]
        sub = {int(k): g.set_index("permno")["dir_mean"]
               for k, g in v.groupby("date_ix")}
        narrow["by_role"][role] = rank_ic(sub, by_date, dates_k, dec_dates)
    narrow["by_role"]["generic_analyst"] = rank_ic(
        {int(k): g.set_index("permno")["dir_mean"]
         for k, g in ps[ps["arm"] == "generic"].groupby("date_ix")},
        by_date, dates_k, dec_dates)
    narrow["by_role"]["randtext_analyst"] = rank_ic(
        {int(k): g.set_index("permno")["dir_mean"]
         for k, g in ps[ps["arm"] == "randtext"].groupby("date_ix")},
        by_date, dates_k, dec_dates)

    # ── §20 and the call census ─────────────────────────────────────────────
    from backend.services.llm_swarm import effective_distinct_ideas
    fl = []
    for r in calls.itertuples():
        for f in (r.forecasts or []):
            fl.append({"arm": r.arm, "ticker": r.permno,
                       "observable": f["observable"],
                       "horizon_days": f["horizon_days"],
                       "probability": f["probability"]})
    fdf = pd.DataFrame(fl)
    s20 = {arm: effective_distinct_ideas(g.to_dict("records"))
           for arm, g in fdf.groupby("arm")}

    census = (calls.groupby(["arm", "status"]).size()
              .unstack(fill_value=0).to_dict())
    rej: dict[str, int] = {}
    for r in calls.itertuples():
        for x in (r.rejections or []):
            rej[x["reason"]] = rej.get(x["reason"], 0) + 1

    # per-arm score distribution — the shuffled arm's premise, verified
    dist = {}
    for arm, g in sc_all.groupby("arm"):
        v = g["score"].dropna().to_numpy()
        dist[arm] = {"n": int(len(v)), "mean": round(float(v.mean()), 4),
                     "sd": round(float(v.std(ddof=1)), 4),
                     "p05": round(float(np.percentile(v, 5)), 4),
                     "p95": round(float(np.percentile(v, 95)), 4),
                     "share_positive": round(float((v > 0).mean()), 4)}

    out = {
        "label": "ARCHITECTURE_RESULT_ONLY",
        "K": a.K, "wmax": WMAX, "n_dates": len(dates_k),
        "first_date": str(dec_dates[dates_k[0]].date()),
        "last_date": str(dec_dates[dates_k[-1]].date()),
        "arms": results, "rank_ic": ic_out, "paired": pairs,
        "shuffled_placebo": shuffled, "time_shifted": tshift,
        "score_distribution": dist,
        "narrow_domain": narrow,
        "effective_distinct_ideas": s20,
        "call_census": census, "rejections": rej,
        "declared_non_run": DECLARED_NON_RUN,
        "null_by_construction": {
            "no_specialist_reliability":
                ("Amendment A5 fixes specialist reliability at neutral/equal "
                 "until forward records resolve, so removing it removes "
                 "nothing. The arm is identical to `full` BY CONSTRUCTION and "
                 "its difference is exactly 0.0 — printed rather than "
                 "simulated, because simulating it would imply it could have "
                 "come out otherwise.")},
        "wall_seconds": round(time.time() - t0, 1),
    }
    Path(a.out).write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {a.out} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
