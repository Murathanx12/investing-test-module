"""ABN end-to-end on real data: claims -> ledger -> resolutions -> beliefs -> gate.

The amnesia trial produced exactly what the belief network eats: 480 forecasts
made from point-in-time facts, each with a later, deterministically observed
outcome. This script runs the whole loop on them and prints what the brain
believes afterwards — including the part where the promotion gate refuses to
promote anything, because replay evidence cannot promote.

It is also the working demonstration of the architecture's one rule: the only
thing that touched a posterior was a Resolution.

    python scripts/abn_ingest_amnesia.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.abn import calibration as cal
from aegis_brain.abn import gate
from aegis_brain.abn.core import Claim, ClaimLedger, Resolution
from aegis_brain.abn.posterior import PosteriorStore
from aegis_brain.config import MODULE_ROOT

RUN_DIR = MODULE_ROOT / "runs" / "AMNESIA"
LEDGER = MODULE_ROOT / "ledger" / "abn_claims_amnesia.jsonl"
OUT = MODULE_ROOT / "runs" / "ABN" / "abn_amnesia_demo.json"


def market_context(asof: str, mkt: pd.Series) -> str:
    """Walk-forward context bucket — trailing 12m market sign, closed months only."""
    m = pd.Timestamp(asof)
    hist = mkt.loc[mkt.index <= m].tail(12)
    if len(hist) < 12:
        return "unknown"
    return "bull" if float((1 + hist).prod() - 1) > 0 else "bear"


def main() -> int:
    from aegis_brain.pf.panel63 import load_spine

    events = pd.read_csv(RUN_DIR / "event_set.csv").set_index("event_id")
    spine = load_spine("2004-01-31", "2022-12-31")
    ctx = {eid: market_context(r.formation_month, spine.mkt)
           for eid, r in events.iterrows()}

    if LEDGER.exists():
        LEDGER.unlink()                      # demo ledger, rebuilt each run
    led = ClaimLedger(LEDGER)
    store = PosteriorStore()

    n_claims = n_res = n_abstain = 0
    per_arm: dict[str, dict[str, list]] = {}

    for path in sorted((RUN_DIR / "cache").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec.get("kind") != "forecast" or not rec.get("ok"):
            continue
        eid, arm = rec["event_id"], rec["arm"]
        if eid not in events.index:
            continue
        ev = events.loc[eid]
        d = rec.get("parsed") or {}
        p = d.get("p_beat")
        abstain = d.get("abstain") is True or not isinstance(p, (int, float))

        claim = Claim(
            claim_class=f"equity_beat_12m::{arm}",
            entity_key=f"permno:{ev.permno}",
            asof=str(ev.formation_month),
            kind="direction",
            statement=f"permno:{ev.permno} beats the market over 12 months",
            anchor=(float(p) if not abstain else None),
            anchor_units="prob",
            window_days=(0, 365),
            p_raw=(min(max(float(p), 0.0), 1.0) if not abstain else None),
            context_key=ctx.get(eid, "unknown"),
            abstain=abstain,
            abstain_reason="out_of_scope" if abstain else "",
            source=f"{rec['model']}|{arm}",
        )
        led.add_claim(claim)
        n_claims += 1
        if abstain:
            n_abstain += 1
            continue

        # ── the resolution: deterministic, from realized panel returns ──────
        res = Resolution(
            claim_id=claim.claim_id,
            resolved_on=str((pd.Timestamp(ev.formation_month)
                             + pd.DateOffset(months=12)).date()),
            hit=bool((float(p) >= 0.5) == bool(ev.beat_market)),
            realized=float(ev.fwd12_stock - ev.fwd12_market),
            realized_units="pct_excess_12m",
            source="crsp_panel stitched 1963-2022 + FF mkt (pinned vintage)",
            cohort_key=str(ev.formation_month),
        )
        led.add_resolution(res)
        n_res += 1

        cohort = int((events.formation_month == ev.formation_month).sum())
        store.update(led.claims()[-1], res, cohort_size=cohort, obs_sd=0.30)

        a = per_arm.setdefault(arm, {"p": [], "y": [], "abstain": 0})
        a["p"].append(float(p))
        a["y"].append(int(bool(ev.beat_market)))

    for arm in per_arm:
        per_arm[arm]["abstain"] = sum(
            1 for c in led.claims()
            if c["claim_class"].endswith(arm) and c["abstain"])

    out = {
        "ledger": str(LEDGER.relative_to(MODULE_ROOT)),
        "chain_verified": led.verify(),
        "claims": n_claims, "resolutions": n_res, "abstentions": n_abstain,
        "beliefs": store.snapshot(),
        "calibration": {arm: cal.report(np.array(v["p"]), np.array(v["y"]),
                                        n_abstain=v["abstain"])
                        for arm, v in per_arm.items()},
        "hit_rate_by_context": {
            f"{arm}|{c}": store.hit_rate(f"equity_beat_12m::{arm}", c)
            for arm in per_arm for c in ("bull", "bear")},
        "attention_weights": {
            arm: gate.attention_weight(store.hit_rate(f"equity_beat_12m::{arm}"))
            for arm in per_arm},
    }

    # the promotion gate, on the best-looking arm
    best = min(per_arm, key=lambda a: cal.brier(np.array(per_arm[a]["p"]),
                                                np.array(per_arm[a]["y"])))
    hr = store.hit_rate(f"equity_beat_12m::{best}")
    t_like = ((hr["mean"] - 0.5) / max((hr["ci95"][1] - hr["ci95"][0]) / 3.92, 1e-9))
    out["gate"] = {
        "best_arm_by_brier": best,
        "evaluated": gate.evaluate(gate.GateInput(
            claim_class=f"equity_beat_12m::{best}", t_stat=round(t_like, 2),
            n_resolutions=len(per_arm[best]["p"]), months_forward=0,
            evidence_source="replay")),
    }

    # the embargo, demonstrated rather than asserted
    sample = led.claims()[0]
    out["embargo_demo"] = {
        "claim_asof": sample["asof"], "resolvable_on": sample["resolvable_on"],
        "visible_one_month_later": led.retrieve(
            str((pd.Timestamp(sample["asof"]) + pd.DateOffset(months=1)).date())
        )[0]["resolution"],
        "visible_after_the_window": led.retrieve(
            str((pd.Timestamp(sample["resolvable_on"]) + pd.DateOffset(days=1)).date())
        )[0]["resolution"],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in
                      ("chain_verified", "claims", "resolutions", "abstentions",
                       "hit_rate_by_context", "attention_weights", "gate",
                       "embargo_demo")}, indent=2, default=str))
    for arm, r in out["calibration"].items():
        print(f"\n{arm}: coverage {r['coverage']}  raw Brier {r['raw']['brier']} "
              f"(ECE {r['raw']['ece']}) -> calibrated {r['calibrated']['brier']} "
              f"(ECE {r['calibrated']['ece']})")
    print(f"\nwritten -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
