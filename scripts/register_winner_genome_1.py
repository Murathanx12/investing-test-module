"""Append the WINNER-GENOME-1 registration (and later its verdict) to
TRIALS/registry.jsonl.

Two calls, deliberately separate so the git history shows the order:

    python -m scripts.register_winner_genome_1              # BEFORE compute
    python -m scripts.register_winner_genome_1 --verdict    # AFTER compute

The trial row must exist before the simulation runs — the registry row plus the
commit timestamp is the tamper evidence. The verdict row refuses to write
before `data/factory/winner_genome_1_results.json` exists, because a registry
row without a receipt is a lie (the REVINFO-2 precedent).

WINNER-GENOME-1 ACCRUES ZERO ARMS — it cannot promote, seed or size anything.
It still increments the cumulative multiple-testing count, in the conservative
direction, because it looked at data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT
from aegis_brain.gate.registry import register_trial

RECEIPT = MODULE_ROOT / "data" / "factory" / "winner_genome_1_results.json"

HYPOTHESIS = (
    "Tournament-winner strategy families reconstructed from the winners' OWN "
    "PUBLIC DESCRIPTIONS (F1 momentum+volume+clean-price-action, F2 bet-on-"
    "volatility, F3 quality-momentum, F4 concentrated-sector, F5 speculative-"
    "underdogs) simulated under the 2025 Bloomberg handbook rules (long-only, "
    "no leverage, 20% position cap, 25 trading days, 2600 teams per arm) on "
    "CRSP daily 2002-2024 across 231 NON-OVERLAPPING tiled windows. PRIMARY: "
    "Delta-median = mean over windows of [median 5-week net return of family F "
    "- median of C3(F), the random control MATCHED on constituent-volatility "
    "bucket distribution, k, weights and rebalance], sampling unit = WINDOW "
    "(n=231), beside its own 80%-power MDE = 2.80 x max(NW-HAC, IID) SE. "
    "H1 selection shifts the median; H2 the families only fatten the right "
    "tail at matched or worse median (dispersion, not selection); H3 any "
    "advantage survives re-sizing at 10/5%/inverse-vol/ERC/half-Kelly. "
    "Honest prior: LOW for H1 (~20%), HIGH for H2 (~70%). ACCRUES ZERO ARMS. "
    "Full doc TRIALS/PREREG_WINNER_GENOME_1.md."
)

EXPECTED = (
    "Reported never deciding: max over 2600 draws (the number a leaderboard "
    "actually reports), P(arm produces the field winner), p5/p50/p95, worst "
    "case, skew, realised portfolio vol, and the selection-vs-sizing table "
    "(20%/10%/5%/inverse-vol/ERC/half-Kelly) with compound return, max "
    "drawdown, return-per-unit-vol and an explicitly-defined ruin probability "
    "(career NAV < 0.50 of start across the consecutive window sequence). "
    "Controls C1 equal-weight universe, C2 EW top-100 mktcap beside CRSP "
    "vwretd, C3 vol-matched random (per family), C4 unmatched random. "
    "Delisting returns spliced at dlstcd>=200 (Shumway -0.30 when missing)."
)

KILL = (
    "Frozen per family: SELECTION_DETECTED iff Delta-median >= its own MDE AND "
    "same sign in >=5/8 pre-declared regime blocks AND same sign in both "
    "sample halves; UNRESOLVED_UNSTABLE if above MDE but coverage fails; "
    "DISPERSION_ONLY if |Delta-median| < MDE while Delta-p95 clears its own "
    "MDE; UNRESOLVED if neither clears (never a kill, S19); "
    "SELECTION_HARMFUL if Delta-median <= -MDE. Runtime assertions that VOID "
    "an arm: vol-match histogram gap > 2pp, zero delisting terminations over "
    "the sample, lookahead perturbation proof failure, weight cap violation. "
    "May NOT conclude: any alpha/Sharpe/skill/money claim; anything about the "
    "actual winning teams (their holdings are NOT observable - the Bloomberg "
    "tables are aggregate across all competitors); that execution was "
    "measured (it structurally was not); that anything seeds, sizes or arms "
    "any lane."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdict", action="store_true")
    a = ap.parse_args()

    if not a.verdict:
        row = register_trial(
            name="WINNER-GENOME-1",
            hypothesis=HYPOTHESIS,
            expected_effect=EXPECTED,
            kill_condition=KILL,
        )
        print(json.dumps({"registered": row["name"],
                          "at": row["registered_at"]}, indent=1))
        return 0

    if not RECEIPT.exists():
        raise SystemExit(
            f"{RECEIPT} missing - the trial has not run; a registry row "
            f"without a receipt is a lie")
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))

    fam = "; ".join(
        f"{k}: dmedian {v['delta_median_pp']:+.3f}pp (MDE "
        f"{v['delta_median_mde_pp']:.3f}, t {v['delta_median_t']:+.2f}), "
        f"dp95 {v['delta_p95_pp']:+.3f}pp (MDE {v['delta_p95_mde_pp']:.3f}), "
        f"dmax {v['delta_max_pp']:+.2f}pp (MDE {v['delta_max_mde_pp']:.2f}), "
        f"median max-over-2600-per-window "
        f"{v['leaderboard_max_over_2600_per_window']['median_pct']:+.1f}%, p5 "
        f"{v['p5_pct']:+.1f}%, P(win) {v['p_produces_winner']:.3f} -> "
        f"{v['verdict']}"
        for k, v in r["families"].items())

    row = register_trial(
        name="VERDICT-WINNER-GENOME-1",
        hypothesis=f"WINNER-GENOME-1 verdict: {r['trial_verdict']}. {fam}",
        expected_effect=(
            f"Search denominator: {r['search_denominator']} arm x parameter "
            f"combinations executed ({r['search_denominator_failed']} voided/"
            f"failed). Windows {r['n_windows']}, teams/arm/window "
            f"{r['n_teams']}, universe median size {r['universe_median_size']}."
            f" Assertions: {json.dumps(r['assertions'])}. Sizing table and "
            f"ruin probabilities in the receipt; ruin defined as career NAV "
            f"< 0.50 of start over the consecutive window sequence."),
        kill_condition=KILL,
    )
    print(json.dumps({"registered": row["name"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
