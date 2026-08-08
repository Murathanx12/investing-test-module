"""TRIAL-LLM-AMNESIA-1B — the positive control AMNESIA-1 needs.

AMNESIA-1 found the instruction arm changed nothing. That has two possible
readings, and they must be separated before anything is concluded:

  (a) the instruction fails to suppress retrievable memory, or
  (b) there was no retrievable memory on this task to suppress.

This control measures memory retrievability DIRECTLY. For the same 120 events,
the model is asked outright — no forecasting framing, no suppression
instruction — what the company's stock actually did over the 12 months after
the date, and whether the company still existed 24 months later.

Pre-registered predictions (before the run):
  Q1 the model answers (does not say UNKNOWN) on >= 50% of the 12m-return asks.
  Q2 its stated DIRECTION is right on <= 65% of answered asks — i.e. real but
     weak retrievability, far below the ~100% a true look-up would give.
  Q3 survival ("still listed 24 months later") direction accuracy > 12m return
     direction accuracy — corporate existence is a more memorable fact than a
     relative return.

Reading rule fixed in advance:
  * If Q1 is low AND direction ~ 50%: reading (b) holds — AMNESIA-1's null is
    about the task, not about instructions, and the instruction question stays
    OPEN pending a task where memory is demonstrably retrievable.
  * If the model answers often and is materially right: reading (a) holds —
    memory is retrievable, the instruction did not suppress it, and masking is
    mandatory.
"""
from __future__ import annotations

import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.llm import amnesia as am
from aegis_brain.llm.client import chat

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("amnesia1b")

RUN_DIR = MODULE_ROOT / "runs" / "AMNESIA"
CACHE = RUN_DIR / "cache_1b"
MODEL = "deepseek-chat"

SYSTEM = ("You are being tested on factual recall of market history. Answer "
          "only with strict JSON. If you do not know, say UNKNOWN — a wrong "
          "confident answer is worse than an honest UNKNOWN.")


def ask(row: pd.Series) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{row.event_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    user = (
        f"Company: {row.company} (ticker {row.ticker}).\n"
        f"Reference date: {row.formation_month}.\n\n"
        "From your knowledge of market history, answer:\n"
        "1. What was this stock's approximate TOTAL RETURN over the 12 months "
        "following the reference date?\n"
        "2. Did it beat or lag the US stock market over those 12 months?\n"
        "3. Was the company still listed 24 months after the reference date?\n\n"
        'Return JSON exactly: {"return_pct": <number or "UNKNOWN">, '
        '"vs_market": "<BEAT|LAG|UNKNOWN>", "still_listed_24m": '
        '"<YES|NO|UNKNOWN>", "confidence": "<HIGH|MEDIUM|LOW>"}')
    rec = {"event_id": row.event_id, "model": MODEL, "user": user}
    try:
        out = chat(user, system=SYSTEM, model=MODEL, temperature=0.0,
                   max_tokens=300, response_json=True)
        rec["parsed"] = am.parse_json(out["text"])
        rec["ok"] = True
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["ok"] = False
    path.write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
    return rec


def main() -> int:
    df = pd.read_csv(RUN_DIR / "event_set.csv")
    with ThreadPoolExecutor(max_workers=6) as pool:
        recs = list(pool.map(lambda t: ask(t[1]), df.iterrows()))
    by = {r["event_id"]: r for r in recs if r.get("ok")}

    ans_ret, dir_hits, ret_err, surv_hits = 0, [], [], []
    for _, row in df.iterrows():
        p = (by.get(row.event_id) or {}).get("parsed") or {}
        vm = str(p.get("vs_market", "UNKNOWN")).upper()
        if vm in ("BEAT", "LAG"):
            ans_ret += 1
            dir_hits.append((vm == "BEAT") == bool(row.beat_market))
        rp = p.get("return_pct")
        if isinstance(rp, (int, float)):
            ret_err.append(abs(float(rp) / 100.0 - float(row.fwd12_stock)))
        sl = str(p.get("still_listed_24m", "UNKNOWN")).upper()
        if sl in ("YES", "NO"):
            # ground truth: did the name still have returns 24 months later
            surv_hits.append((sl == "YES") == bool(row.months_realized == 12))

    n = len(df)
    out = {
        "trial": "TRIAL-LLM-AMNESIA-1B", "model": MODEL, "n_events": n,
        "answer_rate_vs_market": round(ans_ret / n, 3),
        "direction_accuracy_when_answered": (round(float(np.mean(dir_hits)), 3)
                                             if dir_hits else None),
        "n_direction_answered": len(dir_hits),
        "numeric_return_answer_rate": round(len(ret_err) / n, 3),
        "median_abs_return_error": (round(float(np.median(ret_err)), 3)
                                    if ret_err else None),
        "survival_answer_rate": round(len(surv_hits) / n, 3),
        "survival_accuracy": (round(float(np.mean(surv_hits)), 3)
                              if surv_hits else None),
    }
    d = out["direction_accuracy_when_answered"]
    out["prediction_scoring"] = {
        "Q1_answers_ge_50pct": out["answer_rate_vs_market"] >= 0.50,
        "Q2_direction_le_65pct": (d is not None and d <= 0.65),
        "Q3_survival_beats_return_direction": (
            out["survival_accuracy"] is not None and d is not None
            and out["survival_accuracy"] > d),
    }
    out["reading"] = (
        "MEMORY RETRIEVABLE — masking is mandatory and the instruction failed"
        if (d is not None and d >= 0.60 and out["answer_rate_vs_market"] >= 0.5)
        else "MEMORY NOT RETRIEVABLE ON THIS TASK — AMNESIA-1's null is about "
             "the task, not about instructions; the instruction question stays "
             "open pending a task with demonstrable recall")
    (RUN_DIR / "AMNESIA_1B.json").write_text(json.dumps(out, indent=2),
                                             encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
