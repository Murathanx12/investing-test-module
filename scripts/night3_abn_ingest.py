"""Feed NIGHT-3 experiences into the ABN — its first at-scale workload.

The belief network was built and unit-tested in NIGHT-1 on 480 amnesia
forecasts. NIGHT-3 produces roughly 16,000 graded decisions, which is the first
sample large enough to ask whether the two-timescale posteriors and the
promotion gate behave sensibly at scale.

Architecture rule, enforced by the code rather than by this docstring: **the
only write path into a posterior is a Resolution**, and a Resolution can only be
built from an observed outcome. No P&L number reaches a belief.

Cohort deflation matters here and is not cosmetic: forty decisions made in the
same month on the same slate are nearly one observation, not forty. The store is
told the cohort size so its effective-n deflation can do its job — otherwise the
posteriors would report a confidence the sample cannot support.

    python scripts/night3_abn_ingest.py [--arms A,E]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
import pathlib
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.abn import calibration as cal
from aegis_brain.abn import gate
from aegis_brain.abn.core import Claim, ClaimLedger, Resolution
from aegis_brain.abn.posterior import PosteriorStore
from aegis_brain.config import MODULE_ROOT

RUN_DIR = MODULE_ROOT / "runs" / "NIGHT3"
LEDGER_BASE = MODULE_ROOT / "ledger" / "abn_claims_night3"
OUT_BASE = MODULE_ROOT / "runs" / "ABN" / "abn_night3"


def conviction_to_probability(direction: str, conviction: float) -> float | None:
    """Monotone ENGINE-DERIVED map from an elicited conviction to a probability.

    The model was asked for a decision and a conviction, not for a probability
    that the name beats the market. This mapping is stated here rather than
    hidden: it is monotone, so every rank-based statistic (AUC, ordering) is
    unaffected by it, and Brier/calibration numbers computed downstream must be
    read as conditional on this choice.
    """
    if direction == "BUY":
        return 0.5 + 0.5 * conviction
    if direction == "SELL":
        return 0.5 - 0.5 * conviction
    return None                       # HOLD carries no directional claim


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="A,E")
    ap.add_argument("--suffix", default="",
                    help="read experiences_<arm><suffix>.jsonl; use '_smoke' to "
                         "dry-run without touching the campaign stores")
    args = ap.parse_args()
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    suffix = args.suffix

    LEDGER = pathlib.Path(f"{LEDGER_BASE}{suffix}.jsonl")
    OUT = pathlib.Path(f"{OUT_BASE}{suffix}.json")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if LEDGER.exists():
        LEDGER.unlink()                 # rebuilt from the append-only stores
    led = ClaimLedger(LEDGER)
    store = PosteriorStore()

    counts = {"claims": 0, "resolutions": 0, "holds_skipped": 0}
    per: dict[str, dict[str, list]] = defaultdict(lambda: {"p": [], "y": []})
    by_thesis: dict[str, dict[str, list]] = defaultdict(lambda: {"p": [], "y": []})
    missing = []

    for arm in arms:
        path = RUN_DIR / f"experiences_{arm}{suffix}.jsonl"
        if not path.exists():
            missing.append(str(path.name))
            continue
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        cohort = pd.Series([r["ts"] for r in rows]).value_counts().to_dict()
        for r in rows:
            p = conviction_to_probability(r["direction"], float(r["confidence"]))
            if p is None:
                counts["holds_skipped"] += 1
                continue
            claim = Claim(
                claim_class=f"slate_decision::{arm}",
                entity_key=f"permno:{r['entity_key']}",
                asof=r["ts"], kind="direction",
                statement=f"permno:{r['entity_key']} beats the market next month",
                anchor=float(p), anchor_units="prob", window_days=(0, 31),
                p_raw=float(np.clip(p, 0.0, 1.0)),
                context_key=r["market_regime"],
                source=f"{r['model_id']}|{r['brain_version']}")
            led.add_claim(claim)
            counts["claims"] += 1
            hit = bool((p >= 0.5) == (float(r["abnormal_return"]) > 0))
            res = Resolution(
                claim_id=claim.claim_id, resolved_on=r["resolved_ts"], hit=hit,
                realized=float(r["abnormal_return"]),
                realized_units="pct_excess_1m",
                source="crsp_panel stitched 1963-2022 + FF mkt (pinned vintage)",
                cohort_key=r["ts"])
            led.add_resolution(res)
            counts["resolutions"] += 1
            store.update(led.claims()[-1], res,
                         cohort_size=int(cohort.get(r["ts"], 1)), obs_sd=0.12)
            y = int(float(r["abnormal_return"]) > 0)
            per[arm]["p"].append(p)
            per[arm]["y"].append(y)
            by_thesis[f"{arm}|{r['thesis']}"]["p"].append(p)
            by_thesis[f"{arm}|{r['thesis']}"]["y"].append(y)

    if missing:
        print(f"MISSING experience files (skipped, not silently zeroed): {missing}")
    if not counts["resolutions"]:
        raise SystemExit("no resolutions ingested — refusing to write an "
                         "empty belief snapshot that would look like a result")

    out = {
        "workload": "NIGHT-3 slate decisions",
        "ledger": str(LEDGER.relative_to(MODULE_ROOT)),
        "chain_verified": led.verify(),
        "counts": counts,
        "probability_mapping": ("engine-derived monotone map from elicited "
                                "conviction; rank statistics are invariant to "
                                "it, Brier/ECE are conditional on it"),
        "calibration_by_arm": {
            a: cal.report(np.array(v["p"]), np.array(v["y"]), n_abstain=0)
            for a, v in per.items() if v["p"]},
        "calibration_by_thesis": {
            k: (cal.report(np.array(v["p"]), np.array(v["y"]), n_abstain=0)
                | {"n": len(v["p"])})
            for k, v in sorted(by_thesis.items()) if len(v["p"]) >= 50},
        "hit_rate_by_context": {
            f"{a}|{c}": store.hit_rate(f"slate_decision::{a}", c)
            for a in per for c in ("risk_on", "risk_off")},
        "attention_weights": {
            a: gate.attention_weight(store.hit_rate(f"slate_decision::{a}"))
            for a in per},
        "beliefs": store.snapshot(),
    }

    # the promotion gate, on every arm — it must refuse, and say why
    verdicts = {}
    for a in per:
        hr = store.hit_rate(f"slate_decision::{a}")
        half = max((hr["ci95"][1] - hr["ci95"][0]) / 3.92, 1e-9)
        t_like = (hr["mean"] - 0.5) / half
        verdicts[a] = gate.evaluate(gate.GateInput(
            claim_class=f"slate_decision::{a}", t_stat=float(t_like),
            n_resolutions=len(per[a]["p"]), months_forward=0,
            evidence_source="backtest"))
    out["promotion_gate"] = verdicts
    out["promotion_gate_note"] = (
        "Every arm is expected to be refused: this is replay evidence, and the "
        "gate refuses retrospective evidence by construction. A PROMOTE here "
        "would be a bug in the gate, not a discovery.")

    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in
                      ("counts", "chain_verified", "calibration_by_arm",
                       "hit_rate_by_context", "attention_weights",
                       "promotion_gate")}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
