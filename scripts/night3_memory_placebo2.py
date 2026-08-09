"""DIAG-PF4-MEMORY-PLACEBO-2 — the three things the first control got wrong.

`DIAG-NIGHT3-MEMORY-PLACEBO-1` scrambled arm E's situation→outcome mapping once,
with one seed, permuting globally, and concluded "memory content not
demonstrated". External review found three defects in that design, all of which
push the same way — toward over-controlling and therefore toward the null:

  1. A permutation PRESERVES THE MARGINAL DISTRIBUTION, and therefore preserves
     the base rate. If what memory actually contributes is base-rate calibration
     rather than situation-specific recall, the scrambled arm receives the entire
     benefit and the comparison is rigged toward "no content effect". The missing
     arm is SITUATIONS-ONLY: you have seen these situations before, here is how
     many, and you are told nothing about what happened.

  2. ONE SEED. t = 0.43 rested on a single permutation realization with no
     estimate of the scrambled arm's own sampling variability. +5.07 % could
     simply have been a high draw.

  3. GLOBAL PERMUTATION leaks era information through the situation half — a
     1970s-style situation could be handed a 2010s outcome. Permuting WITHIN
     REGIME removes that channel.

This script runs one arm per invocation so the seeds parallelize across
processes and a crash costs one arm. Aggregation is `night3_memory_agg.py`.

    python scripts/night3_memory_placebo2.py --mode situations_only
    python scripts/night3_memory_placebo2.py --mode shuffled --seed 7
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.harness.benchmark import newey_west_tstat
from aegis_brain.night3 import decide as dec
from aegis_brain.night3.experience import ExperienceStore
from aegis_brain.night3.llmcache import LLMCache, SpendGuard
from aegis_brain.night3.slate import PROF_SIGNALS, book_return, build_slates
from aegis_brain.pf.panel63 import annualize, eligibility, load_spine
from aegis_brain.pf.signals import SignalLibrary, composite_score

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("memplacebo2")

RUN_DIR = MODULE_ROOT / "runs" / "NIGHT3"
OUT_DIR = MODULE_ROOT / "runs" / "PF4" / "memory"
MODEL = "deepseek-chat"
COST_BPS = 25.0
KNN_K = 8
OUTCOME_FIELDS = ("abnormal_return", "error", "outcome_class", "attribution",
                  "realized_return", "lesson_text")


class RegimeShuffledStore(ExperienceStore):
    """Arm E's own store, with outcomes swapped WITHIN market regime.

    Subclassed rather than reimplemented so the retrieval maths, the outcome
    embargo and the neighbour ordering are literally the code arm E ran. The
    donor is drawn from the embargoed pool restricted to the neighbour's own
    regime, so the scramble destroys the situation→outcome mapping without also
    handing the model an outcome from a different era.
    """

    def __init__(self, path, seed: int, stratify: bool = True) -> None:
        super().__init__(path)
        self.seed = seed
        self.stratify = stratify

    def retrieve(self, fingerprint, ts, k=8, event_class=None):
        real = super().retrieve(fingerprint, ts, k=k, event_class=event_class)
        if not real:
            return real
        pool = self.available_at(ts)
        if not pool:
            return real
        rng = np.random.default_rng(
            abs(hash((self.seed, ts, tuple(fingerprint)))) % (2 ** 32))
        by_regime: dict[str, list] = {}
        if self.stratify:
            for r in pool:
                by_regime.setdefault(r.get("market_regime", ""), []).append(r)
        out = []
        for r in real:
            cand = (by_regime.get(r.get("market_regime", ""), pool)
                    if self.stratify else pool)
            if not cand:
                cand = pool
            donor = cand[int(rng.integers(0, len(cand)))]
            swapped = dict(r)
            for f in OUTCOME_FIELDS:
                swapped[f] = donor[f]
            out.append(swapped)
        return out


def nw_t(x: pd.Series, lags: int = 12):
    r = newey_west_tstat(pd.Series(x).dropna(), lags=lags)
    return None if r.get("t") is None else round(float(r["t"]), 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=["shuffled", "situations_only"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-stratify", action="store_true")
    ap.add_argument("--first", default="2005-01-31")
    ap.add_argument("--last", default="2021-12-31")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--cap-usd", type=float, default=25.0)
    args = ap.parse_args()

    tag = (f"situations_only" if args.mode == "situations_only"
           else f"shuf{args.seed}{'' if not args.no_stratify else '_global'}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"ARM_{tag}.json"
    if out_path.exists():
        log.info("%s already exists — write-once, nothing to do", out_path.name)
        return 0

    src = RUN_DIR / "experiences_E.jsonl"
    if not src.exists():
        raise SystemExit("arm E's experience store is missing — every memory "
                         "control must reuse arm E's own memory, not a fresh one")

    guard = SpendGuard(args.cap_usd)
    cache = LLMCache(RUN_DIR / "cache", MODEL, guard)

    spine = load_spine("2003-01-31", "2022-12-31")
    lib = SignalLibrary(spine.panel)
    lib.preload(["native:mom_12_1", "native:vol_12m_low", "osap:GP", "osap:BM",
                 "osap:OperProfRD", "osap:CBOperProf"])
    elig = eligibility(spine, "small")
    score, _ = composite_score(lib, PROF_SIGNALS, elig)
    slates = build_slates(spine, lib, score, elig, first=args.first,
                          last=args.last, slate_n=40)
    log.info("%d slates, mode=%s tag=%s", len(slates), args.mode, tag)

    if args.mode == "shuffled":
        shadow = OUT_DIR / f"experiences_src_{tag}.jsonl"
        shadow.write_bytes(src.read_bytes())
        store = RegimeShuffledStore(shadow, seed=args.seed,
                                    stratify=not args.no_stratify)
        memory_mode = "full"
        nonce = f"|memplacebo2|{tag}"
    else:
        store = ExperienceStore(src)          # real memory, outcomes withheld
        memory_mode = "situations_only"
        nonce = "|memplacebo2|situations_only"

    rows, prev, prior, pending = [], set(), {}, []
    rng = np.random.default_rng(20260809 + args.seed)
    for i, s in enumerate(slates):
        ts = s.formation_month
        by = s.by_label()
        still = []
        for p in pending:
            if p["resolved_ts"] < ts:
                prior[p["permno"]] = p
            else:
                still.append(p)
        pending = still
        for p in prior.values():
            p["months_ago"] = max(1, i - p["slate_index"])
        if args.mode == "shuffled" and prior:
            # scramble the persistence outcomes too: the control destroys the
            # situation->outcome link everywhere memory appears. This block is
            # already within-month and therefore within-regime by construction.
            keys = list(prior)
            vals = [prior[k]["true_abnormal"] for k in keys]
            perm = rng.permutation(len(keys))
            for k, j in zip(keys, perm):
                prior[k]["abnormal_return"] = vals[int(j)]

        system, user, _edg = dec.build_prompt(s, arm="E", store=store,
                                              prior=prior, k=KNN_K,
                                              model_id=MODEL,
                                              memory_mode=memory_mode)
        rec = cache.call(system, user, temperature=0.0, max_tokens=3000,
                         nonce=nonce, tag=f"{tag}|{ts}")
        if not rec.get("ok"):
            rows.append({"ts": s.realized_month, "net": np.nan})
            continue
        d, _pd = dec.parse_decisions(rec["raw"], s)
        if not d:
            rows.append({"ts": s.realized_month, "net": np.nan})
            continue
        picks = dec.build_book(d, s, top_n=args.top)
        r, traded = book_return(s, picks, COST_BPS, prev or None)
        prev = {by[p].permno for p in picks if p in by}
        rows.append({"ts": s.realized_month, "net": r, "traded": traded})
        for lab, dd in d.items():
            c = by[lab]
            pending.append({"permno": c.permno, "direction": dd.direction,
                            "conviction": dd.conviction,
                            "expected_excess": dd.expected_excess,
                            "true_abnormal": c.fwd_ret - s.benchmark_fwd,
                            "abnormal_return": c.fwd_ret - s.benchmark_fwd,
                            "resolved_ts": s.realized_month, "slate_index": i,
                            "months_ago": 1})
        if (i + 1) % 36 == 0:
            log.info("  %s %s %d/%d spend $%.2f", tag, ts, i + 1, len(slates),
                     guard.spent_usd)

    ser = pd.Series({pd.Timestamp(r["ts"]): r["net"] for r in rows}).astype(float)
    arms = pd.read_csv(RUN_DIR / "arm_monthly_returns.csv", index_col=0,
                       parse_dates=True)
    bench = arms["benchmark"]
    bcagr = annualize(bench.dropna())
    dE = (arms["E"] - ser).dropna()
    out = {
        "diagnostic": "DIAG-PF4-MEMORY-PLACEBO-2", "is_gate": False,
        "arm_tag": tag, "mode": args.mode, "seed": args.seed,
        "stratified_within_regime": (args.mode == "shuffled"
                                     and not args.no_stratify),
        "model_id": MODEL, "n_months": int(ser.notna().sum()),
        "cagr_net": round(annualize(ser.dropna()), 4),
        "excess_cagr_net": round(annualize(ser.dropna()) - bcagr, 4),
        "t_excess_nw": nw_t(ser - bench),
        "turnover_1way_annual": round(float(np.nanmean(
            [r.get("traded", np.nan) for r in rows]) * 12), 3),
        "E_minus_this": {
            "n": len(dE),
            "cagr_difference": round(annualize(arms["E"].dropna())
                                     - annualize(ser.dropna()), 4),
            "t_nw": nw_t(dE),
            "mde_annualized_at_t2": round(
                2 * float(dE.std() / np.sqrt(len(dE))) * 12, 4)},
        "spend": guard.as_dict(), "cache": cache.stats(),
    }
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    ser.to_csv(OUT_DIR / f"arm_{tag}_monthly.csv")
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
