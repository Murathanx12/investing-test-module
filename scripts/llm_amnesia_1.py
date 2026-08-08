"""TRIAL-LLM-AMNESIA-1 — can an instruction make an LLM forget? Measured.

Pre-registration: TRIALS/PREREG_LLM_AMNESIA_1.md (written before any call).

Four arms over one frozen event set (A0 named-raw / A1 named-instructed /
A2 masked / A3 synthetic), each with a contamination canary asked first, plus
a cheap baseline bank (climatology + out-of-sample logistic regression on the
same five features) because the LLM only earns attention above the baseline.

Every response is cached immutably at runs/AMNESIA/cache/<key>.json, so a
re-run costs nothing and the transcript is auditable.

    python scripts/llm_amnesia_1.py [--events 120] [--workers 6]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.llm import amnesia as am
from aegis_brain.llm.client import chat
from aegis_brain.pf.panel63 import load_spine
from aegis_brain.pf.signals import SignalLibrary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("amnesia")

RUN_DIR = MODULE_ROOT / "runs" / "AMNESIA"
CACHE = RUN_DIR / "cache"
MODEL = "deepseek-chat"
CLIMATOLOGY = 0.5


def call_cached(arm: str, ev: am.Event, kind: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = am.cache_key(arm, ev.event_id, kind, MODEL)
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    system, user = (am.canary_prompt(ev, arm) if kind == "canary"
                    else am.forecast_prompt(ev, arm))
    rec = {"arm": arm, "event_id": ev.event_id, "kind": kind, "model": MODEL,
           "system": system, "user": user}
    for attempt in range(3):
        try:
            out = chat(user, system=system, model=MODEL, temperature=0.0,
                       max_tokens=400, response_json=True)
            rec["raw"] = out["text"]
            rec["parsed"] = am.parse_json(out["text"])
            rec["usage"] = out.get("usage")
            rec["ok"] = True
            break
        except Exception as exc:
            rec["error"] = f"{type(exc).__name__}: {exc}"
            rec["ok"] = False
            time.sleep(2 * (attempt + 1))
    path.write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
    return rec


def logistic_baseline(df: pd.DataFrame) -> np.ndarray:
    """Out-of-sample logistic regression on the same five features (5-fold)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold

    cols = ["pct_ret_12m", "pct_vol_12m", "pct_gross_profit",
            "pct_book_to_market", "pct_mom_12_1"]
    X = df[cols].to_numpy(float) / 100.0
    y = df["beat_market"].astype(int).to_numpy()
    p = np.full(len(y), np.nan)
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(X, y):
        m = LogisticRegression(max_iter=1000).fit(X[tr], y[tr])
        p[te] = m.predict_proba(X[te])[:, 1]
    return p


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def auc(p: np.ndarray, y: np.ndarray) -> float:
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    from itertools import product
    wins = sum((a > b) + 0.5 * (a == b) for a, b in product(pos, neg))
    return float(wins / (len(pos) * len(neg)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=120)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    spine = load_spine("2004-01-31", "2022-12-31")
    lib = SignalLibrary(spine.panel)
    lib.preload(["native:mom_12_1", "native:vol_12m_low", "osap:GP", "osap:BM"])
    events = am.build_events(spine, lib, n_per_class=args.events // 2)
    frame = am.events_to_frame(events)
    frame.to_csv(RUN_DIR / "event_set.csv", index=False)
    log.info("event set frozen: %d events", len(events))

    jobs = [(arm, ev, kind) for arm in am.ARMS for ev in events
            for kind in ("canary", "forecast")]
    log.info("%d LLM calls (cached ones are free)", len(jobs))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        recs = list(pool.map(lambda j: call_cached(*j), jobs))
    ok = sum(r["ok"] for r in recs)
    log.info("calls complete: %d/%d ok", ok, len(recs))

    # ── assemble ────────────────────────────────────────────────────────────
    by = {(r["arm"], r["event_id"], r["kind"]): r for r in recs}
    y = frame["beat_market"].astype(int).to_numpy()
    base_p = logistic_baseline(frame)
    results: dict = {
        "trial": "TRIAL-LLM-AMNESIA-1", "model": MODEL,
        "prereg": "TRIALS/PREREG_LLM_AMNESIA_1.md",
        "n_events": len(events),
        "outcome_base_rate": round(float(y.mean()), 3),
        "baselines": {
            "climatology_0.5": {"brier": round(brier(np.full(len(y), CLIMATOLOGY), y), 4)},
            "logistic_oos_5feature": {"brier": round(brier(base_p, y), 4),
                                      "auc": round(auc(base_p, y), 3)},
        },
        "arms": {},
    }

    for arm in am.ARMS:
        p, keep, abstain, canary = [], [], 0, []
        for i, ev in enumerate(events):
            f = by.get((arm, ev.event_id, "forecast"))
            c = by.get((arm, ev.event_id, "canary"))
            canary.append(c["parsed"] if c and c.get("ok") else {})
            if not f or not f.get("ok"):
                continue
            d = f["parsed"]
            if d.get("abstain") is True:
                abstain += 1
                continue
            try:
                v = float(d["p_beat"])
            except (KeyError, TypeError, ValueError):
                continue
            p.append(min(max(v, 0.0), 1.0))
            keep.append(i)
        p = np.array(p)
        yy = y[keep]
        entry = {
            "n_scored": len(p), "n_abstain": abstain,
            "brier": round(brier(p, yy), 4) if len(p) else None,
            "auc": round(auc(p, yy), 3) if len(p) else None,
            "mean_p": round(float(p.mean()), 3) if len(p) else None,
            "sd_p": round(float(p.std()), 3) if len(p) else None,
            "realized_rate": round(float(yy.mean()), 3) if len(yy) else None,
        }
        if arm.startswith(("A0", "A1")):
            rec_yes = [c for c in canary if str(c.get("recall", "")).upper() == "YES"]
            entry["recall_rate"] = round(len(rec_yes) / max(len(canary), 1), 3)
            idx_yes = [i for i, c in enumerate(canary)
                       if str(c.get("recall", "")).upper() == "YES" and i in keep]
            idx_no = [i for i, c in enumerate(canary)
                      if str(c.get("recall", "")).upper() != "YES" and i in keep]
            pos = {v: k for k, v in enumerate(keep)}
            for label, idxs in (("brier_when_recall_yes", idx_yes),
                                ("brier_when_recall_no", idx_no)):
                sel = [pos[i] for i in idxs]
                entry[label] = (round(brier(p[sel], yy[sel]), 4) if len(sel) >= 5
                                else None)
                entry[label.replace("brier", "n")] = len(sel)
            # did the recalled direction match what actually happened?
            hits = [(c.get("direction", "").upper() == ("UP" if events[i].beat_market
                                                        else "DOWN"))
                    for i, c in enumerate(canary)
                    if str(c.get("recall", "")).upper() == "YES"]
            entry["recall_direction_accuracy"] = (round(float(np.mean(hits)), 3)
                                                  if hits else None)
        else:
            ident = []
            yerr = []
            for i, c in enumerate(canary):
                tk = str(c.get("ticker", "")).upper().strip()
                cn = str(c.get("company", "")).upper().strip()
                true_tk = events[i].ticker.upper()
                true_cn = events[i].company.upper()
                ident.append(tk == true_tk or (cn not in ("", "UNKNOWN")
                                               and cn.split()[0] in true_cn))
                yr = c.get("year") or 0
                if isinstance(yr, (int, float)) and yr > 1900:
                    yerr.append(abs(int(yr) - int(events[i].formation_month[:4])))
            entry["identification_rate"] = round(float(np.mean(ident)), 3) if ident else None
            entry["year_guessed_frac"] = round(len(yerr) / max(len(canary), 1), 3)
            entry["median_year_error"] = (round(float(np.median(yerr)), 1)
                                          if yerr else None)
        results["arms"][arm] = entry
        log.info("%s: brier %s auc %s %s", arm, entry["brier"], entry["auc"],
                 {k: v for k, v in entry.items()
                  if k in ("recall_rate", "identification_rate")})

    a = results["arms"]
    def g(arm, k):
        return a.get(arm, {}).get(k)
    results["gaps"] = {
        "instruction_effect_on_recall": (
            None if g("A0_named_raw", "recall_rate") is None
            else round(g("A1_named_instructed", "recall_rate")
                       - g("A0_named_raw", "recall_rate"), 3)),
        "instruction_effect_on_brier": (
            None if g("A0_named_raw", "brier") is None
            else round(g("A1_named_instructed", "brier")
                       - g("A0_named_raw", "brier"), 4)),
        "contamination_brier_A2_minus_A0": (
            None if g("A2_masked", "brier") is None
            else round(g("A2_masked", "brier") - g("A0_named_raw", "brier"), 4)),
        "synthetic_vs_masked_brier": (
            None if g("A3_synthetic", "brier") is None
            else round(g("A3_synthetic", "brier") - g("A2_masked", "brier"), 4)),
        "masked_vs_logistic_baseline": (
            None if g("A2_masked", "brier") is None
            else round(g("A2_masked", "brier")
                       - results["baselines"]["logistic_oos_5feature"]["brier"], 4)),
    }

    # pre-registered prediction scoring
    P = results["gaps"]
    results["prediction_scoring"] = {
        "P1_A0_recall_ge_40pct": (None if g("A0_named_raw", "recall_rate") is None
                                  else g("A0_named_raw", "recall_rate") >= 0.40),
        "P2_instruction_fails": (
            None if P["instruction_effect_on_recall"] is None else
            bool(abs(P["instruction_effect_on_recall"]) < 0.15
                 and abs(P["instruction_effect_on_brier"]) < 0.02)),
        "P3_masked_identification_le_10pct": (
            None if g("A2_masked", "identification_rate") is None
            else g("A2_masked", "identification_rate") <= 0.10),
        "P4_contamination_ge_0.02": (
            None if P["contamination_brier_A2_minus_A0"] is None
            else P["contamination_brier_A2_minus_A0"] >= 0.02),
        "P5_masked_does_not_beat_logistic": (
            None if P["masked_vs_logistic_baseline"] is None
            else P["masked_vs_logistic_baseline"] >= 0),
        "P6_synthetic_approx_masked": (
            None if P["synthetic_vs_masked_brier"] is None
            else abs(P["synthetic_vs_masked_brier"]) <= 0.01),
    }
    results["spend"] = {
        "calls": len(recs), "ok": ok,
        "prompt_tokens": sum((r.get("usage") or {}).get("prompt_tokens", 0)
                             for r in recs),
        "completion_tokens": sum((r.get("usage") or {}).get("completion_tokens", 0)
                                 for r in recs),
    }
    (RUN_DIR / "AMNESIA_1.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: results[k] for k in
                      ("baselines", "arms", "gaps", "prediction_scoring", "spend")},
                     indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
