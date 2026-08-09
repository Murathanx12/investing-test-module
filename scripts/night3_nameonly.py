"""TRIAL-NAME-ONLY-1 — the contamination ceiling.

Registry row committed 2026-08-09 before this file existed. Design authority:
`DESIGN_MEMORY_TAXONOMY_2026-08-09.md` §5.

AMNESIA already measured named / named+instructed / masked / synthetic on this
exact 120-event set; **those arms are not re-run**. This adds the one arm that
was missing: **real ticker, real date, and NO numeric facts at all.**

What it measures is the ceiling. Whatever score the model reaches on identity
alone is the most that any unmasked diagnostic could ever be crediting to
"analysis" — because on this arm there is nothing else to analyse. Every
unmasked number we might one day be tempted to quote has to be read against it.

    python scripts/night3_nameonly.py [--workers 8]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.night3.llmcache import LLMCache, SpendGuard, parse_json

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nameonly")

RUN_DIR = MODULE_ROOT / "runs" / "NIGHT3"
EVENTS = MODULE_ROOT / "runs" / "AMNESIA" / "event_set.csv"
MODEL = "deepseek-chat"

SYSTEM = ("You are a careful equity analyst. You answer only with strict JSON "
          "matching the requested schema.")

ASK = ('Return JSON exactly: {"p_beat": <number 0-1>, "abstain": <true|false>, '
       '"basis": "<one of: recall, general_reasoning, no_information>"}\n'
       "p_beat = probability that this stock's TOTAL RETURN over the NEXT 12 "
       "MONTHS from the date given exceeds the US stock market's total return "
       "over the same 12 months.")


# DIAG-NAME-ONLY-FORCED-1 only: the abstain door is removed. Registered as a
# diagnostic; it cannot overturn TRIAL-NAME-ONLY-1's UNRESOLVED verdict.
ASK_FORCED = ('Return JSON exactly: {"p_beat": <number 0-1>, '
              '"basis": "<one of: recall, general_reasoning>"}\n'
              "p_beat = probability that this stock's TOTAL RETURN over the "
              "NEXT 12 MONTHS from the date given exceeds the US stock "
              "market's total return over the same 12 months.\n"
              "You MUST give a number. Abstaining is not available. If you "
              "recall anything about this company around that date, use it; "
              "otherwise give your best estimate and say so.")


def user_prompt(row, forced: bool = False) -> str:
    return (f"Company: {row.company} (ticker {row.ticker}).\n"
            f"Today's date: {row.formation_month}.\n\n"
            "You are given NO financial data about this company — no returns, "
            "no valuation, no profitability, no momentum. Only its identity and "
            "the date.\n\n" + (ASK_FORCED if forced else ASK))


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def auc(p: np.ndarray, y: np.ndarray) -> float:
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    wins = sum((a > b) + 0.5 * (a == b) for a, b in product(pos, neg))
    return float(wins / (len(pos) * len(neg)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--cap-usd", type=float, default=25.0)
    ap.add_argument("--forced", action="store_true",
                    help="run DIAG-NAME-ONLY-FORCED-1 (no abstain option)")
    args = ap.parse_args()

    if not EVENTS.exists():
        raise SystemExit(f"{EVENTS} missing — NAME-ONLY must run on the SAME "
                         "event set AMNESIA used, not a fresh sample")
    df = pd.read_csv(EVENTS)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    guard = SpendGuard(args.cap_usd)
    cache = LLMCache(RUN_DIR / "cache", MODEL, guard)

    def one(row):
        rec = cache.call(SYSTEM, user_prompt(row, args.forced),
                         temperature=0.0, max_tokens=200,
                         tag=f"nameonly{'F' if args.forced else ''}|{row.event_id}")
        out = {"event_id": row.event_id, "beat": bool(row.beat_market),
               "p": None, "abstain": None, "basis": None}
        if rec.get("ok"):
            try:
                d = parse_json(rec["raw"])
                out["abstain"] = bool(d.get("abstain", False))
                out["basis"] = str(d.get("basis", ""))
                out["p"] = float(np.clip(float(d["p_beat"]), 0.0, 1.0))
            except (ValueError, KeyError, TypeError) as exc:
                log.warning("unparseable %s: %s", row.event_id, exc)
        return out

    rows = list(df.itertuples())
    log.info("%d NAME-ONLY calls (cached ones are free)", len(rows))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        recs = list(pool.map(one, rows))

    scored = [r for r in recs if r["p"] is not None and not r["abstain"]]
    p = np.array([r["p"] for r in scored])
    y = np.array([int(r["beat"]) for r in scored])
    bases: dict[str, int] = {}
    for r in recs:
        if r["basis"]:
            bases[r["basis"]] = bases.get(r["basis"], 0) + 1

    amnesia = {}
    apath = MODULE_ROOT / "runs" / "AMNESIA" / "AMNESIA_1.json"
    if apath.exists():
        a = json.loads(apath.read_text(encoding="utf-8"))
        amnesia = {k: {"brier": v.get("brier"), "auc": v.get("auc")}
                   for k, v in a.get("arms", {}).items()}
        amnesia["logistic_oos_5feature"] = a["baselines"]["logistic_oos_5feature"]

    result = {
        "trial": ("DIAG-NAME-ONLY-FORCED-1" if args.forced
                  else "TRIAL-NAME-ONLY-1"),
        "is_gate": not args.forced,
        "abstain_available": not args.forced,
        "prereg": "registry row 2026-08-09 + DESIGN_MEMORY_TAXONOMY §5",
        "model_id": MODEL, "temperature": 0.0,
        "event_set": "runs/AMNESIA/event_set.csv (IDENTICAL to AMNESIA-1)",
        "n_events": len(recs), "n_scored": len(scored),
        "n_abstain": int(sum(1 for r in recs if r["abstain"])),
        "n_unparseable": int(sum(1 for r in recs if r["p"] is None)),
        "outcome_base_rate": round(float(np.mean([int(r["beat"]) for r in recs])), 3),
        "brier": round(brier(p, y), 4) if len(p) else None,
        "auc": round(auc(p, y), 3) if len(p) else None,
        "mean_p": round(float(p.mean()), 3) if len(p) else None,
        "sd_p": round(float(p.std()), 3) if len(p) else None,
        "stated_basis": dict(sorted(bases.items(), key=lambda kv: -kv[1])),
        "comparison_arms_from_AMNESIA_1": amnesia,
        "interpretation": (
            "This AUC is the CONTAMINATION CEILING: the most that identity "
            "alone can buy on this event set. Any future unmasked diagnostic "
            "must be quoted against it or not quoted."),
        "spend": guard.as_dict(), "cache": cache.stats(),
    }
    (RUN_DIR / ("NAME_ONLY_FORCED.json" if args.forced else "NAME_ONLY.json")).write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
