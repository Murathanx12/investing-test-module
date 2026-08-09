"""DIAG-NIGHT3-MEMORY-PLACEBO-1 — does arm E's memory work because of its CONTENT?

Arm E posted the campaign's best standalone excess. Before that gets called
learning, it has to survive the control that isolates the only thing "learning"
could mean here.

The control destroys **exactly one** property: the mapping from a situation to
its outcome. Everything else is held identical —

  * the same kNN neighbours are retrieved (same fingerprints, same distances),
  * the same number of memory lines appears in the prompt,
  * the same marginal distribution of outcomes (a permutation preserves it),
  * the same track-record block, the same persistence block, the same schema.

Only *which* outcome is attached to *which* situation is scrambled, with a fixed
seed. If the model does just as well on scrambled memory, then what helped was
the presence of a memory block, not its content — and no learning claim
survives.

This arm can only undercut arm E. It cannot promote anything.

    python scripts/night3_memory_placebo.py [--workers 8]
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
log = logging.getLogger("memplacebo")

RUN_DIR = MODULE_ROOT / "runs" / "NIGHT3"
MODEL = "deepseek-chat"
COST_BPS = 25.0
KNN_K = 8
OUTCOME_FIELDS = ("abnormal_return", "error", "outcome_class", "attribution",
                  "realized_return", "lesson_text")


class ShuffledStore(ExperienceStore):
    """An ExperienceStore whose retrievals carry someone else's outcomes.

    Subclassed rather than reimplemented so the retrieval maths, the embargo and
    the neighbour ordering are literally the same code as arm E used. The
    permutation is drawn once per query from the embargoed pool, seeded by the
    query timestamp, so it is deterministic and reproducible.
    """

    def __init__(self, path, seed: int = 20260809) -> None:
        super().__init__(path)
        self.seed = seed

    def retrieve(self, fingerprint, ts, k=8, event_class=None):
        real = super().retrieve(fingerprint, ts, k=k, event_class=event_class)
        if not real:
            return real
        pool = self.available_at(ts)
        if not pool:
            return real
        rng = np.random.default_rng(
            abs(hash((self.seed, ts, tuple(fingerprint)))) % (2 ** 32))
        donors = rng.integers(0, len(pool), len(real))
        out = []
        for r, d in zip(real, donors):
            swapped = dict(r)
            for f in OUTCOME_FIELDS:
                swapped[f] = pool[int(d)][f]
            out.append(swapped)
        return out


def nw_t(x: pd.Series, lags: int = 12):
    r = newey_west_tstat(x.dropna(), lags=lags)
    return None if r.get("t") is None else round(float(r["t"]), 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", default="2005-01-31")
    ap.add_argument("--last", default="2021-12-31")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--cap-usd", type=float, default=25.0)
    args = ap.parse_args()

    src = RUN_DIR / "experiences_E.jsonl"
    if not src.exists():
        raise SystemExit("arm E's experience store is missing — the control "
                         "must reuse arm E's own memory, not a fresh one")

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
    log.info("%d slates; arm E store has %d experiences", len(slates),
             sum(1 for _ in src.open(encoding="utf-8")))

    # the shuffled view is built over a COPY so the campaign store is untouched
    shadow = RUN_DIR / "experiences_Eshuf_source.jsonl"
    shadow.write_bytes(src.read_bytes())
    store = ShuffledStore(shadow)

    rows, prev, prior, pending, mem_diag = [], set(), {}, [], []
    rng = np.random.default_rng(20260809)
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
        # scramble the persistence outcomes too: the control destroys the
        # situation->outcome link everywhere memory appears, not just in the kNN
        if prior:
            keys = list(prior)
            vals = [prior[k]["true_abnormal"] for k in keys]
            perm = rng.permutation(len(keys))
            for k, j in zip(keys, perm):
                prior[k]["abnormal_return"] = vals[int(j)]

        system, user, edg = dec.build_prompt(s, arm="E", store=store,
                                             prior=prior, k=KNN_K,
                                             model_id=MODEL)
        rec = cache.call(system, user, temperature=0.0, max_tokens=3000,
                         nonce="|memplacebo", tag=f"Eshuf|{ts}")
        mem_diag.append({"ts": ts, **edg.get("memory", {})})
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
        if (i + 1) % 24 == 0:
            log.info("  %s %d/%d spend $%.2f", ts, i + 1, len(slates),
                     guard.spent_usd)

    ser = pd.Series({pd.Timestamp(r["ts"]): r["net"] for r in rows}).astype(float)
    prior_run = json.loads((RUN_DIR / "DECISION_REPLAY.json").read_text(encoding="utf-8"))
    arms = pd.read_csv(RUN_DIR / "arm_monthly_returns.csv", index_col=0,
                       parse_dates=True)
    bench = arms["benchmark"]
    bcagr = annualize(bench.dropna())
    d_EsE = (arms["E"] - ser).dropna()
    out = {
        "diagnostic": "DIAG-NIGHT3-MEMORY-PLACEBO-1",
        "is_gate": False,
        "model_id": MODEL, "n_months": int(ser.notna().sum()),
        "shuffled_fields": list(OUTCOME_FIELDS),
        "arm_Eshuffled": {
            "cagr_net": round(annualize(ser.dropna()), 4),
            "excess_cagr_net": round(annualize(ser.dropna()) - bcagr, 4),
            "t_excess_nw": nw_t(ser - bench),
            "turnover_1way_annual": round(float(np.nanmean(
                [r.get("traded", np.nan) for r in rows]) * 12), 3)},
        "arm_E_for_reference": {
            "excess_cagr_net": prior_run["arms"]["E"]["excess_cagr_net"],
            "t_excess_nw": prior_run["arms"]["E"]["t_excess_nw"]},
        "arm_A_for_reference": {
            "excess_cagr_net": prior_run["arms"]["A"]["excess_cagr_net"],
            "t_excess_nw": prior_run["arms"]["A"]["t_excess_nw"]},
        "E_minus_Eshuffled": {
            "n": len(d_EsE),
            "mean_monthly": round(float(d_EsE.mean()), 5),
            "cagr_difference": round(annualize(arms["E"].dropna())
                                     - annualize(ser.dropna()), 4),
            "t_nw": nw_t(d_EsE),
            "mde_annualized_at_t2": round(
                2 * float(d_EsE.std() / np.sqrt(len(d_EsE))) * 12, 4)},
        "spend": guard.as_dict(), "cache": cache.stats(),
    }
    dd = out["E_minus_Eshuffled"]
    out["verdict"] = (
        "MEMORY CONTENT NOT DEMONSTRATED — arm E is not distinguishable from "
        "the same memory with its situation-to-outcome mapping destroyed"
        if (dd["t_nw"] is None or abs(dd["t_nw"]) < 2.0) else
        "CONTENT EFFECT SURVIVES THE SHUFFLE — worth a registered successor")
    (RUN_DIR / "MEMORY_PLACEBO.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    ser.to_csv(RUN_DIR / "arm_Eshuffled_monthly.csv")
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
