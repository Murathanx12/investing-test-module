"""Promotion / attachment interface to aegis-finance.

THE FIREWALL (CANON §7, ROADMAP §2.7): this module NEVER writes into aegis-finance.
It emits a reviewable **promotion bundle** — a draft `TRIAL-*.md`, a registry row, the
signal spec, and a snapshot of the forward calibration ledger — into `export/`. A human
reviews it and commits it into aegis-finance, where the forward paper clocks score it.
That human commit is the only path across the firewall.

A signal becomes promotable only after it SURVIVES its pre-registered kill conditions
(not after it clears the deploy gate — the gate is likely unclearable on backtest; the
forward ledger earns conviction). Each promotable signal ships as a PIT-safe scorer whose
signature matches aegis-finance's `pit_score_collector` closure: `score(ticker, as_of) -> float`.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from aegis_brain.config import MODULE_ROOT


@dataclass(frozen=True)
class SignalSpec:
    """The contract aegis-finance consumes. `scorer_ref` names the PIT-safe callable
    (module:function) with signature score(ticker: str, as_of: str) -> float."""
    name: str
    description: str
    scorer_ref: str
    pit_inputs: list[str]
    prior_from_backtest: str          # the honest, deflated prior (not a promise)
    kill_conditions: str
    survived: bool                    # passed its pre-registered kill conditions?
    trial_doc: str                    # source TRIAL-*.md in THIS module


# Registry of signals and their promotion status. Update as trials resolve.
SIGNALS: dict[str, SignalSpec] = {
    "opportunistic_insider": SignalSpec(
        name="opportunistic_insider",
        description=(
            "Long large/mid-cap stocks with a non-routine (Cohen-Malloy-Pomorski) "
            "open-market insider PURCHASE filed recently; low-turnover ~12mo hold."),
        scorer_ref="aegis_brain.signals.insider_scorer:opportunistic_insider_score",
        pit_inputs=["SEC Form 4 (filing-date stamped)", "CRSP/permno universe"],
        prior_from_backtest=(
            "BRAIN-003 (2006-2024): large/mid +17 bps/mo vs EW (t=1.40), FF5+UMD alpha "
            "+102 bps/mo (t=1.89), post-2015 t=1.30; NULL in microcap. Leak-checked "
            "(noise gross|t|<3). Weak POSITIVE PRIOR — does not clear deploy gate (DSR 0.26)."),
        kill_conditions="net t<1 both cap segments = kill; noise gross|t|>=3 = leak void",
        survived=True,
        trial_doc="TRIALS/TRIAL-BRAIN-003-opportunistic-insider.md",
    ),
}

LEDGER = MODULE_ROOT / "ledger" / "forward_calls.jsonl"
EXPORT_DIR = MODULE_ROOT / "export"


def promotable() -> list[str]:
    """Signals that survived their kill conditions — eligible for a promotion bundle."""
    return [k for k, s in SIGNALS.items() if s.survived]


def build_promotion_bundle(signal_name: str, out_dir: Path | None = None) -> Path:
    """Emit the aegis-finance handoff for one survived signal. Returns the bundle dir.
    Does NOT touch aegis-finance — a human commits the contents there."""
    if signal_name not in SIGNALS:
        raise KeyError(f"unknown signal {signal_name!r}; known: {list(SIGNALS)}")
    spec = SIGNALS[signal_name]
    if not spec.survived:
        raise ValueError(f"{signal_name} has not survived its kill conditions — not promotable")

    out = (out_dir or EXPORT_DIR) / signal_name
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1) the spec (machine-readable contract)
    (out / "signal_spec.json").write_text(json.dumps(asdict(spec), indent=2))

    # 2) a draft aegis-finance registry row (human commits it into the main registry)
    (out / "registry_row.json").write_text(json.dumps({
        "name": f"TRIAL-{signal_name.upper()}-forward",
        "hypothesis": spec.description,
        "expected_effect": spec.prior_from_backtest,
        "kill_condition": spec.kill_conditions,
        "source_module": "aegis-brain", "source_trial": spec.trial_doc,
        "drafted_at": stamp,
    }, indent=2))

    # 3) a draft TRIAL-*.md for the main repo's docs/TRIALS/
    (out / "TRIAL_DRAFT.md").write_text(
        f"# TRIAL-{signal_name.upper()}-forward (draft from aegis-brain, {stamp})\n\n"
        f"**Source:** aegis-brain `{spec.trial_doc}` · **Scorer:** `{spec.scorer_ref}`\n\n"
        f"## Hypothesis\n{spec.description}\n\n"
        f"## Prior (deflated, from backtest — NOT a promise)\n{spec.prior_from_backtest}\n\n"
        f"## PIT inputs\n" + "".join(f"- {i}\n" for i in spec.pit_inputs) +
        f"\n## Kill conditions\n{spec.kill_conditions}\n\n"
        f"## Forward scoring\nWire `{spec.scorer_ref}` into a pit_score_collector; score the "
        f"forward clocks. Conviction is earned forward, not by the backtest.\n")

    # 4) snapshot the forward calibration ledger (the track record)
    if LEDGER.exists():
        shutil.copy(LEDGER, out / "forward_calls_snapshot.jsonl")

    (out / "MANIFEST.txt").write_text(
        f"aegis-brain promotion bundle for '{signal_name}' generated {stamp}.\n"
        "Review, then a human commits TRIAL_DRAFT.md + registry_row.json into aegis-finance\n"
        "and wires the scorer into a forward collector. The brain never writes across the firewall.\n")
    return out


if __name__ == "__main__":
    for name in promotable():
        print("built bundle:", build_promotion_bundle(name))
