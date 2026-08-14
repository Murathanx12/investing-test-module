"""ABLATION-FWD — the only evidence class that can ever certify. STATED-EMPTY.

Amendment A6 splits chunk 9 in two. `ABLATION-HIST` runs now and is
`ARCHITECTURE_RESULT_ONLY` — the foundation model may know later history, so a
good historical number is unfalsifiably contaminated. `ABLATION-FWD` is this
file: the harness and the accrual path, built now, filling **automatically** as
the swarm's forward records resolve.

**Its numbers are not fabricated, estimated, extrapolated or previewed.** Run
today it prints an empty table and the date. That is the correct output, and
printing anything else would be the exact failure the whole campaign is
designed to catch.

    python -m scripts.ablation_fwd            # today: STATED_EMPTY
    python -m scripts.ablation_fwd --json

WHAT IT WILL MEASURE, AND WHAT IT CANNOT
========================================
Available from the existing 20,073-record forward ledger the moment records
resolve:

1. **Brier by specialist, observable and horizon**, each beside its own
   80%-power MDE and its own n (CANON §19).
2. **Skill against climatology** — the base rate of the same observable at the
   same horizon over the same population. A Brier score with no baseline beside
   it is a number, not a skill claim.
3. **The shuffled placebo, forward.** The same multiset of stated probabilities
   permuted across (security, observable, horizon). This is Amendment A4's
   decisive arm and it costs nothing: if the forward Brier is no better than
   the shuffled Brier, the content is doing nothing forward either.

NOT available forward today, and stated rather than quietly omitted:

4. **generic-agent vs specialist-swarm.** The forward ledger contains swarm
   records only. The contrast needs forward records from a single generic
   agent, which have not been minted. The harness accepts them (`--arm-field`)
   the day they exist; until then the arm is `NOT_RUN_FORWARD`.
5. **Specialist reliability.** Amendment A5: neutral/equal until resolutions
   exist. This file is the thing that ends that — the first partial-pooled
   update is licensed by the first resolved batch and not before.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AF = Path(r"C:\Users\mrthn\aegis-finance")
LEDGER = AF / "backend" / "data" / "optimus" / "predictions.jsonl"
OUT = Path(__file__).resolve().parents[1] / "data" / "factory" / "ablation_fwd.json"

MDE_Z = 2.80
PERM_SEED = 20260812
N_PERM = 200
#: The earliest date on which ANY record in the forward ledger can resolve.
#: Read from the ledger, never hardcoded — a hardcoded date is a claim that
#: stops being true the moment the ledger changes.


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def brier_block(rows: list[dict]) -> dict:
    """Mean Brier with its own MDE, or a stated-empty block."""
    b = np.array([float(r["brier"]) for r in rows
                  if r.get("brier") is not None], dtype=float)
    n = len(b)
    if n < 8:
        return {"n": n, "brier": None, "mde": None,
                "status": "INSUFFICIENT_N"}
    se = float(b.std(ddof=1) / np.sqrt(n))
    return {"n": n, "brier": round(float(b.mean()), 5),
            "mde": round(MDE_Z * se, 5), "status": "OK"}


def climatology(rows: list[dict]) -> dict:
    """Brier of always predicting the observed base rate of the same cell."""
    by = defaultdict(list)
    for r in rows:
        if r.get("outcome") is None:
            continue
        by[(r["observable"], r["horizon_days"])].append(int(bool(r["outcome"])))
    out = {}
    for k, v in by.items():
        p = float(np.mean(v))
        out[f"{k[0]}@{k[1]}d"] = {"n": len(v), "base_rate": round(p, 4),
                                  "climatology_brier": round(p * (1 - p), 5)}
    return out


def shuffled_placebo(rows: list[dict]) -> dict:
    """A4 arm 1, forward and free: permute the stated probabilities."""
    res = [r for r in rows if r.get("outcome") is not None
           and r.get("probability") is not None]
    if len(res) < 30:
        return {"n": len(res), "status": "INSUFFICIENT_N",
                "note": "the decisive arm needs resolved records; it has none"}
    p = np.array([float(r["probability"]) for r in res])
    y = np.array([int(bool(r["outcome"])) for r in res])
    obs = float(np.mean((p - y) ** 2))
    rng = np.random.default_rng(PERM_SEED)
    perm = np.array([float(np.mean((rng.permutation(p) - y) ** 2))
                     for _ in range(N_PERM)])
    return {"n": len(res), "status": "OK",
            "observed_brier": round(obs, 5),
            "shuffled_mean_brier": round(float(perm.mean()), 5),
            "shuffled_p05": round(float(np.percentile(perm, 5)), 5),
            "permutation_p_value_one_sided": round(float((perm <= obs).mean()), 4),
            "reading": ("if the observed Brier is not better than the shuffled "
                        "Brier, the model's CONTENT is doing nothing forward "
                        "and only its noise moved the numbers")}


def _population_layer():
    """The aegis-finance module that owns the two-ledger distinction."""
    sys.path.insert(0, str(AF))
    from backend.services import evidence_population as EP    # noqa: PLC0415
    return EP


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ledger", default=None,
                    help="override the ledger file; the population still "
                         "decides which records are read")
    # NO DEFAULT, DELIBERATELY. "The forward ledger" is two populations with
    # two purposes — the campaign's ~20,073 records and the deployed product's
    # own accrual — and a report that does not say which it read is not a
    # report. Running without this refuses.
    ap.add_argument("--population", default=None,
                    help="campaign_forward | live_forward  (REQUIRED)")
    a = ap.parse_args()

    EP = _population_layer()
    try:
        pop = EP.parse(a.population)
    except EP.PopulationRequired as exc:
        print(f"REFUSED: {exc}")
        return 2

    ledger_path = Path(a.ledger) if a.ledger else EP.ledger_path(pop)
    lineage = EP.lineage(pop, ledger_path)
    rows = EP.read_population(pop, ledger_path)
    resolved = [r for r in rows if r.get("resolved_at")]
    due = sorted({r.get("resolves_after") for r in rows
                  if r.get("resolves_after")})
    earliest = due[0] if due else None

    by_spec: dict[str, list[dict]] = defaultdict(list)
    for r in resolved:
        by_spec[r.get("specialist", "?")].append(r)

    out = {
        "evidence_class": f"ABLATION_FWD / {pop.value.upper()}",
        "evidence_population": pop.value,
        "lineage": lineage,
        "two_ledger_fact": (
            "There are TWO forward evidence populations and this report used "
            f"exactly one of them: {pop.value}. CAMPAIGN_FORWARD is the "
            "research campaign's history, resolved locally and attended; "
            "LIVE_FORWARD is the deployed product's own accrual, resolved by "
            "pi_ledger_resolve on the persistent volume. They are never "
            "pooled — a combined estimate would need a prospectively declared "
            "pooling rule, and none is registered."),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "ledger": str(ledger_path),
        "records_total": len(rows),
        "records_resolved": len(resolved),
        "earliest_possible_resolution": earliest,
        "status": ("STATED_EMPTY" if not resolved else "ACCRUING"),
        "overall": brier_block(resolved),
        "by_specialist": {k: brier_block(v) for k, v in sorted(by_spec.items())},
        "climatology": climatology(resolved),
        "shuffled_placebo_forward": shuffled_placebo(resolved),
        "arms_not_run_forward": {
            "generic_agent_vs_specialist_swarm":
                ("the forward ledger holds swarm records only; the contrast "
                 "needs forward records from a single generic agent, which "
                 "have not been minted. NOT_RUN_FORWARD, not estimated."),
        },
        "reading": (
            "Nothing here is fabricated, estimated, extrapolated or previewed. "
            "With zero resolved records the correct output is an empty table "
            "and a date, and that is what this is."
            if not resolved else
            "Forward evidence. This is the only class that can certify, and "
            "even here every slice prints its own n and its own MDE."),
    }
    # One output file per population. A single ablation_fwd.json overwritten by
    # whichever population ran last is exactly the ambiguity this fixes.
    out_path = OUT.with_name(f"ablation_fwd_{pop.value}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str) if a.json else
          f"ABLATION-FWD / {pop.value.upper()}  status={out['status']}  "
          f"records={out['records_total']}  resolved={out['records_resolved']}  "
          f"earliest={out['earliest_possible_resolution']}\n"
          f"ledger={ledger_path}\n{out['reading']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
