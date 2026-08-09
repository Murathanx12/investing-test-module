"""TRIAL-NIGHT3-DECISION-REPLAY-1 — the masked decision replay.

Pre-registration: TRIALS/PREREG_NIGHT3_DECISION_REPLAY.md, sealed before this
file's first call. The decision rule in §4 is NOT restated here; it is imported
from the registration by reference and applied by `adjudicate()` below using the
constants frozen in §4.

    python scripts/night3_decision_replay.py [--first 2005-01-31]
                                             [--last 2021-12-31]
                                             [--slate 40] [--top 20]
                                             [--workers 8] [--arms A,E]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.night3 import decide as dec
from aegis_brain.night3 import persistence as pers
from aegis_brain.night3.experience import (Experience, ExperienceStore,
                                           attribute, classify_outcome)
from aegis_brain.night3.llmcache import LLMCache, SpendGuard
from aegis_brain.night3.slate import PROF_SIGNALS, build_slates, book_return
from aegis_brain.pf.panel63 import annualize, eligibility, load_spine
from aegis_brain.pf.signals import SignalLibrary, composite_score

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("replay")

RUN_DIR = MODULE_ROOT / "runs" / "NIGHT3"
MODEL = "deepseek-chat"
COST_BPS = 25.0
KNN_K = 8

# ── decision rule constants, frozen in PREREG §4 ────────────────────────────
M1_ADOPT_CAGR, M1_ADOPT_T = 0.015, 2.0
M2_ADOPT_CAGR, M2_ADOPT_T = 0.010, 2.0
PLACEBO_P = 0.05
EXPOSURE_FLOOR = 0.95


def nw_t(x: pd.Series, lags: int = 12) -> float | None:
    r = newey_west_tstat(x.dropna(), lags=lags)
    return None if r.get("t") is None else round(float(r["t"]), 2)


def make_experience(*, slate, cand, d, arm: str, regime_abnormal: float
                    ) -> Experience:
    """Grade one decision into an EXPERIENCE. Deterministic; no model input
    beyond the decision itself — attribution is computed, never elicited."""
    abnormal = cand.fwd_ret - slate.benchmark_fwd
    err = abnormal - d.expected_excess
    # target/invalidation are ENGINE-DERIVED from the elicited expectation for
    # slate decisions (eliciting two more numbers per name for 40 names would
    # cost more than it informs). Stated here rather than left implicit.
    target = d.expected_excess if d.expected_excess > 0 else 0.02
    invalidation = -max(2.0 * abs(d.expected_excess), 0.05)
    return Experience(
        ts=slate.formation_month,
        information_state_hash=slate.information_state_hash(),
        market_regime=slate.regime, event_class="monthly_slate",
        fingerprint=cand.fingerprint, model_id=MODEL if arm != "ENGINE" else "engine",
        brain_version=f"night3-1.0-arm{arm}", thesis=d.thesis,
        direction=d.direction, confidence=d.conviction,
        expected_return=d.expected_excess, horizon_months=1,
        target=target, invalidation=invalidation,
        resolved_ts=slate.realized_month, realized_return=cand.fwd_ret,
        benchmark_return=slate.benchmark_fwd, abnormal_return=abnormal,
        error=err,
        attribution=attribute(d.direction, abnormal, d.expected_excess,
                              regime_abnormal),
        outcome_class=classify_outcome(abnormal),
        lesson_text=(f"{d.direction} at conviction {d.conviction:.2f} expecting "
                     f"{d.expected_excess:+.1%}; realized {abnormal:+.1%} vs market"),
        entity_key=cand.permno)


def run_arm_A(slates, cache, workers) -> dict[str, dict]:
    """Arm A has no memory, so every month is independent and parallelizable."""
    def one(s):
        system, user, _ = dec.build_prompt(s, arm="A")
        rec = cache.call(system, user, temperature=0.0, max_tokens=3000,
                         tag=f"A|{s.formation_month}")
        return s.formation_month, rec
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(one, slates))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", default="2005-01-31")
    ap.add_argument("--last", default="2021-12-31")
    ap.add_argument("--slate", type=int, default=40)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--cap-usd", type=float, default=25.0)
    ap.add_argument("--placebo-draws", type=int, default=100)
    ap.add_argument("--min-slates", type=int, default=60,
                    help="refuse to adjudicate below this; lower ONLY for smoke "
                         "runs, which must also pass --out-tag")
    ap.add_argument("--out-tag", default="",
                    help="suffix for artifact names; a tagged run is a smoke "
                         "run and is never the campaign's receipt")
    args = ap.parse_args()
    tag = f"_{args.out_tag}" if args.out_tag else ""
    if args.min_slates < 60 and not args.out_tag:
        raise SystemExit("--min-slates below 60 requires --out-tag: a thin run "
                         "must be labelled, never mistaken for the receipt")

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    guard = SpendGuard(args.cap_usd)
    cache = LLMCache(RUN_DIR / "cache", MODEL, guard)

    # ── environment ─────────────────────────────────────────────────────────
    spine = load_spine("2003-01-31", "2022-12-31")
    lib = SignalLibrary(spine.panel)
    lib.preload(["native:mom_12_1", "native:vol_12m_low", "osap:GP", "osap:BM",
                 "osap:OperProfRD", "osap:CBOperProf"])
    elig = eligibility(spine, "small")
    score, sdiag = composite_score(lib, PROF_SIGNALS, elig)
    slates = build_slates(spine, lib, score, elig, first=args.first,
                          last=args.last, slate_n=args.slate)
    if len(slates) < args.min_slates:
        raise RuntimeError(f"only {len(slates)} slates (min {args.min_slates}) "
                           "— refusing to adjudicate a decision rule on a "
                           "sample this thin")
    bench = pd.Series({pd.Timestamp(s.realized_month): s.benchmark_fwd
                       for s in slates})

    # ── phase 1: arm A (parallel, memoryless) ───────────────────────────────
    log.info("phase 1 — arm A over %d slates", len(slates))
    a_recs = run_arm_A(slates, cache, args.workers)

    # ── phase 2: arms in lockstep, chronological (arm E needs its own past) ─
    log.info("phase 2 — chronological walk (arm E builds memory as it goes)")
    stores = {a: ExperienceStore(RUN_DIR / f"experiences_{a}{tag}.jsonl")
              for a in ("A", "E")}
    for s in stores.values():                     # write-once store, fresh run
        if len(s):
            log.info("resuming store with %d existing experiences", len(s))

    arms = ("ENGINE", "EW40", "A", "E")
    rows = {a: [] for a in arms}
    prev_picks: dict[str, set] = {a: set() for a in arms}
    parse_diag = {a: [] for a in ("A", "E")}
    prior_belief: dict[str, dict[str, dict]] = {"E": {}}   # permno -> last graded
    pending: dict[str, list] = {"E": []}          # awaiting embargo release
    reviews: list[pers.Review] = []
    rank_corr: list[float] = []
    e_mem_diag: list[dict] = []

    rng = np.random.default_rng(20260809)
    placebo = np.zeros((args.placebo_draws, len(slates)))

    for i, s in enumerate(slates):
        ts = s.formation_month
        by = s.by_label()
        regime_abnormal = float(np.mean([c.fwd_ret for c in s.candidates])
                                - s.benchmark_fwd)

        # release any prior beliefs whose outcome is now strictly in the past
        still = []
        for p in pending["E"]:
            if p["resolved_ts"] < ts:
                prior_belief["E"][p["permno"]] = p
            else:
                still.append(p)
        pending["E"] = still
        for p in prior_belief["E"].values():
            p["months_ago"] = max(1, i - p["slate_index"])

        decisions: dict[str, dict[str, dec.Decision]] = {}

        decisions["ENGINE"] = dec.engine_decide(s, top_n=args.top)
        decisions["EW40"] = {c.label: dec.Decision(
            label=c.label, direction="BUY", conviction=0.5,
            expected_excess=0.0, thesis="profitability") for c in s.candidates}

        rec = a_recs.get(ts)
        if rec and rec.get("ok"):
            d, pd_ = dec.parse_decisions(rec["raw"], s)
            parse_diag["A"].append({"ts": ts, **pd_})
            decisions["A"] = d
        else:
            parse_diag["A"].append({"ts": ts, "call_failed": True})
            decisions["A"] = {}

        system, user, edg = dec.build_prompt(
            s, arm="E", store=stores["E"], prior=prior_belief["E"], k=KNN_K,
            model_id=MODEL)
        erec = cache.call(system, user, temperature=0.0, max_tokens=3000,
                          tag=f"E|{ts}")
        e_mem_diag.append({"ts": ts, **edg.get("memory", {}),
                           "n_carried": len(edg.get("carried_labels", []))})
        if erec.get("ok"):
            d, pd_ = dec.parse_decisions(erec["raw"], s)
            parse_diag["E"].append({"ts": ts, **pd_})
            decisions["E"] = d
        else:
            parse_diag["E"].append({"ts": ts, "call_failed": True})
            decisions["E"] = {}

        # rank correlation of arm A's ordering against the engine's (N5)
        if decisions["A"]:
            common = [c for c in s.candidates if c.label in decisions["A"]]
            if len(common) >= 10:
                order = {"BUY": 0, "HOLD": 1, "SELL": 2}
                llm = [order[decisions["A"][c.label].direction]
                       - decisions["A"][c.label].conviction for c in common]
                eng = [c.engine_rank for c in common]
                rank_corr.append(float(pd.Series(llm).corr(pd.Series(eng),
                                                           method="spearman")))

        for arm in arms:
            dd = decisions[arm]
            if not dd:
                rows[arm].append({"ts": s.realized_month, "net": np.nan,
                                  "traded": np.nan, "n": 0, "exposure": 0.0})
                continue
            picks = (list(dd) if arm == "EW40"
                     else dec.build_book(dd, s, top_n=args.top))
            r, traded = book_return(s, picks, COST_BPS, prev_picks[arm] or None)
            prev_picks[arm] = {by[p].permno for p in picks if p in by}
            n_buy = sum(1 for x in dd.values() if x.direction == "BUY")
            rows[arm].append({
                "ts": s.realized_month, "net": r, "traded": traded,
                "n": len(picks), "n_buy": n_buy,
                "n_sell": sum(1 for x in dd.values() if x.direction == "SELL"),
                "n_hold": sum(1 for x in dd.values() if x.direction == "HOLD"),
                # a book is always fully invested by construction; exposure is
                # reported anyway so an arm that ever fails to fill is visible
                "exposure": 1.0 if picks else 0.0,
                "mean_conviction": round(float(np.mean(
                    [x.conviction for x in dd.values()])), 3)})

        # experiences + persistence reviews (arms A and E only)
        for arm in ("A", "E"):
            if not decisions[arm]:
                continue
            exps = []
            for lab, d in decisions[arm].items():
                c = by[lab]
                exps.append(make_experience(slate=s, cand=c, d=d, arm=arm,
                                            regime_abnormal=regime_abnormal))
                if arm == "E" and c.permno in prior_belief["E"]:
                    p = prior_belief["E"][c.permno]
                    reviews.append(pers.grade_review(
                        permno=c.permno, ts=ts, months_ago=p["months_ago"],
                        prior_direction=p["direction"],
                        prior_conviction=p["conviction"],
                        prior_expected=p["expected_excess"],
                        realized_abnormal=p["abnormal_return"],
                        new_direction=d.direction, new_conviction=d.conviction,
                        stated_old_belief=d.old_belief,
                        stated_update=d.belief_update))
            stores[arm].extend(exps)
            if arm == "E":
                for lab, d in decisions[arm].items():
                    c = by[lab]
                    pending["E"].append({
                        "permno": c.permno, "direction": d.direction,
                        "conviction": d.conviction,
                        "expected_excess": d.expected_excess,
                        "abnormal_return": c.fwd_ret - s.benchmark_fwd,
                        "resolved_ts": s.realized_month, "slate_index": i,
                        "months_ago": 1})

        # placebo: seeded random top-20 from the same 40, identical costs
        labs = [c.label for c in s.candidates]
        for j in range(args.placebo_draws):
            pick = list(rng.choice(labs, size=args.top, replace=False))
            placebo[j, i] = book_return(s, pick, COST_BPS)[0]

        if (i + 1) % 24 == 0:
            log.info("  %s  %d/%d  spend $%.2f  cache %s", ts, i + 1,
                     len(slates), guard.spent_usd, cache.stats())

    # ── phase 3: metrics ────────────────────────────────────────────────────
    log.info("phase 3 — metrics")
    series = {a: pd.Series({pd.Timestamp(r["ts"]): r["net"] for r in rows[a]}
                           ).astype(float) for a in arms}
    b = bench.reindex(series["ENGINE"].index)
    stats = {}
    for a in arms:
        net = series[a]
        ex = (net - b).dropna()
        stats[a] = {
            "months": int(net.notna().sum()),
            "cagr_net": round(annualize(net.dropna()), 4),
            "benchmark_cagr": round(annualize(b.dropna()), 4),
            "excess_cagr_net": round(annualize(net.dropna()) - annualize(b.dropna()), 4),
            "mean_monthly_excess": round(float(ex.mean()), 5),
            "t_excess_nw": nw_t(ex),
            "vol_annual": round(float(net.std() * np.sqrt(12)), 4),
            "turnover_1way_annual": round(float(np.nanmean(
                [r["traded"] for r in rows[a]]) * 12), 3),
            "mean_exposure": round(float(np.nanmean(
                [r["exposure"] for r in rows[a]])), 4),
        }
        if a in ("A", "E"):
            stats[a].update({
                "mean_n_buy": round(float(np.nanmean(
                    [r.get("n_buy", np.nan) for r in rows[a]])), 2),
                "mean_n_sell": round(float(np.nanmean(
                    [r.get("n_sell", np.nan) for r in rows[a]])), 2),
                "mean_conviction": round(float(np.nanmean(
                    [r.get("mean_conviction", np.nan) for r in rows[a]])), 3),
                "months_with_failed_call": int(sum(
                    1 for d in parse_diag[a] if d.get("call_failed"))),
                "months_with_missing_labels": int(sum(
                    1 for d in parse_diag[a] if d.get("missing"))),
            })

    def paired(x: str, y: str) -> dict:
        d = (series[x] - series[y]).dropna()
        return {"n": len(d), "mean_monthly": round(float(d.mean()), 5),
                "annualized": round(float(d.mean()) * 12, 4),
                "cagr_difference": round(annualize(series[x].dropna())
                                         - annualize(series[y].dropna()), 4),
                "t_nw": nw_t(d), "t_plain": round(float(
                    d.mean() / (d.std() / np.sqrt(len(d)))), 2) if len(d) > 2 else None}

    M1 = paired("A", "ENGINE")
    M2 = paired("E", "A")
    placebo_cagr = np.array([annualize(pd.Series(placebo[j],
                                                 index=series["ENGINE"].index))
                             for j in range(args.placebo_draws)])
    bench_cagr = annualize(b.dropna())
    placebo_excess = placebo_cagr - bench_cagr

    def placebo_p(x: float) -> float:
        return round(float(np.mean(placebo_excess >= x)), 4)

    # ── phase 4: adjudication against the frozen rule ───────────────────────
    def adjudicate(m: dict, arm: str, adopt_cagr: float, adopt_t: float,
                   need_placebo: bool) -> dict:
        reasons = []
        val = m["cagr_difference"]
        t = m["t_nw"] if m["t_nw"] is not None else 0.0
        if val < adopt_cagr:
            reasons.append(f"difference {val:+.2%} < {adopt_cagr:+.2%}")
        if abs(t) < adopt_t:
            reasons.append(f"|NW t| {abs(t):.2f} < {adopt_t}")
        p = placebo_p(stats[arm]["excess_cagr_net"]) if need_placebo else None
        if need_placebo and p > PLACEBO_P:
            reasons.append(f"placebo p {p} > {PLACEBO_P}")
        if stats[arm]["mean_exposure"] < EXPOSURE_FLOOR:
            reasons.append(f"exposure {stats[arm]['mean_exposure']} < {EXPOSURE_FLOOR}")
        return {"verdict": "ADOPT" if not reasons else "REJECT",
                "failed": reasons, "placebo_p": p}

    v1 = adjudicate(M1, "A", M1_ADOPT_CAGR, M1_ADOPT_T, True)
    v2 = adjudicate(M2, "E", M2_ADOPT_CAGR, M2_ADOPT_T, False)

    result = {
        "trial": "TRIAL-NIGHT3-DECISION-REPLAY-1",
        "prereg": "TRIALS/PREREG_NIGHT3_DECISION_REPLAY.md",
        "model_id": MODEL, "temperature": 0.0, "cost_bps": COST_BPS,
        "window": {"first": slates[0].formation_month,
                   "last": slates[-1].formation_month, "n_slates": len(slates), "smoke_run": bool(args.out_tag)},
        "environment": {"signal": [list(x) for x in PROF_SIGNALS],
                        "segment": "small", "slate_n": args.slate,
                        "book_n": args.top, "knn_k": KNN_K,
                        "signal_coverage": sdiag},
        "provenance": {"holdout_read": False,
                       "last_realized_month": slates[-1].realized_month,
                       "spine": spine.provenance},
        "arms": stats,
        "M1_llm_minus_engine": M1 | {"adjudication": v1},
        "M2_memory_minus_nomemory": M2 | {"adjudication": v2},
        "placebo": {"draws": args.placebo_draws,
                    "mean_excess_cagr": round(float(placebo_excess.mean()), 4),
                    "p95_excess_cagr": round(float(np.percentile(placebo_excess, 95)), 4),
                    "max_excess_cagr": round(float(placebo_excess.max()), 4),
                    "p_engine": placebo_p(stats["ENGINE"]["excess_cagr_net"]),
                    "p_armA": placebo_p(stats["A"]["excess_cagr_net"]),
                    "p_armE": placebo_p(stats["E"]["excess_cagr_net"])},
        "rank_correlation_vs_engine": {
            "n_months": len(rank_corr),
            "mean_spearman": round(float(np.nanmean(rank_corr)), 3) if rank_corr else None,
            "median_spearman": round(float(np.nanmedian(rank_corr)), 3) if rank_corr else None},
        "persistence": pers.summarize(reviews),
        "memory_growth": {"final_store_A": len(stores["A"]),
                          "final_store_E": len(stores["E"]),
                          "months_with_any_neighbour": int(sum(
                              1 for d in e_mem_diag if d.get("with_neighbours", 0) > 0)),
                          "final_pool": e_mem_diag[-1].get("pool") if e_mem_diag else 0},
        "spend": guard.as_dict(), "cache": cache.stats(),
        "experiment_count": {
            "llm_calls": guard.calls,
            "arm_books": len(arms), "placebo_books": args.placebo_draws,
            "graded_decisions": len(stores["A"]) + len(stores["E"]),
        },
    }
    (RUN_DIR / f"DECISION_REPLAY{tag}.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8")
    pd.DataFrame({a: series[a] for a in arms}).assign(benchmark=b).to_csv(
        RUN_DIR / f"arm_monthly_returns{tag}.csv")
    (RUN_DIR / f"persistence_reviews{tag}.json").write_text(
        json.dumps([r.__dict__ for r in reviews], indent=1, default=str),
        encoding="utf-8")
    (RUN_DIR / f"parse_diagnostics{tag}.json").write_text(
        json.dumps(parse_diag, indent=1, default=str), encoding="utf-8")

    print(json.dumps({k: result[k] for k in
                      ("window", "arms", "M1_llm_minus_engine",
                       "M2_memory_minus_nomemory", "placebo",
                       "rank_correlation_vs_engine", "persistence",
                       "memory_growth", "spend")}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
