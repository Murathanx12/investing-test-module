"""Append the GRAPH-COVARIANCE-1 registration (and later its verdict) to
TRIALS/registry.jsonl.

Two calls, deliberately separate so the git history shows the order:

    python -m scripts.register_graph_covariance_1              # BEFORE compute
    python -m scripts.register_graph_covariance_1 --verdict    # AFTER compute

The trial row must exist before any covariance matrix is graded — the registry
row plus the commit timestamp is the tamper evidence. The verdict row refuses to
write before `runs/GRAPH-COVARIANCE-1/grade_report.json` exists, because a
registry row without a receipt is a lie (the REVINFO-2 precedent).

GRAPH-COVARIANCE-1 ACCRUES ZERO ARMS — it cannot promote, seed or size
anything. It still increments the cumulative multiple-testing count, in the
conservative direction, because it looked at data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aegis_brain.config import MODULE_ROOT              # noqa: E402
from aegis_brain.gate.registry import register_trial    # noqa: E402

RECEIPT = MODULE_ROOT / "runs" / "GRAPH-COVARIANCE-1" / "grade_report.json"

HYPOTHESIS = (
    "Descendant of MARKET-GRAPH-1 H1, answering the question the GRAND-ARENA-1 "
    "verdict names as unasked: does a better covariance structure survive into "
    "portfolio outcomes? Commercial risk models assume the specific (residual) "
    "block is DIAGONAL; MARKET-GRAPH-1 measured that LLM-extracted economic "
    "relationships carry forward-residual-correlation information the trailing "
    "matrix lacks. H1: a residual-correlation block predicted WITH the semantic "
    "edge features produces a LOWER realised out-of-sample variance minimum-"
    "variance portfolio than the identical block predicted WITHOUT them. H2: "
    "the same improvement survives a LONG-ONLY, 10%-capped, total-return "
    "minimum-variance portfolio. PRIMARY: paired per-cut-date difference in "
    "realised annualised volatility of the residual GMVP, differenced WITHIN "
    "the date (S18), n = graded cut dates (not pairs), Newey-West 2 lags, "
    "SE = max(HAC, IID), MDE = 2.80 x SE (S19). Panel, universe, cut dates, "
    "residual definition, ridge and edge corpus inherited UNCHANGED from "
    "MARKET-GRAPH-1; the volatility block D and the PSD repair are IDENTICAL "
    "across all arms so only the correlation structure varies. NO NEW LLM CALL. "
    "Honest priors: H1 ~40/60 against, H2 ~15/85 against. ACCRUES ZERO ARMS. "
    "Full doc TRIALS/PREREG_GRAPH_COVARIANCE_1.md."
)

EXPECTED = (
    "PRE-REGISTERED POWER GATE, RUN FIRST AND WRITTEN BEFORE THE REAL ARMS: "
    "`oracle_on_edges` overwrites exactly the edge-carrying entries of the "
    "model_numeric matrix with the TRUE realised forward correlation - the "
    "ceiling on any edge-based correction at 0.58% pair coverage. If the "
    "oracle's improvement is inside its OWN MDE the trial terminates as "
    "UNDERPOWERED_BY_CONSTRUCTION and no null from a real arm is a kill; the "
    "escalation path is pre-committed (raise UNIVERSE_N per MARKET-GRAPH-1 "
    "section 10 lever 1, no new LLM spend, as a NEW prereg with a new name). "
    "This is GRAND-ARENA-1's selection-oracle lesson (oracle itself at 0.64x "
    "its MDE) applied BEFORE the result instead of after. "
    "Decision arms: model_numeric [rho_trail, rho_trail^2, same_sector] vs "
    "model_semantic (+ has_edge, log_n_edges, max_conf). Placebos that must be "
    "null: placebo_shuffled (node-label permutation, degree+confidence "
    "preserved), random_matched_density, placebo_stratified (permuted within "
    "date x same_sector x rho_trail decile - the load-bearing one, because a "
    "min-var solve weights high-rho pairs most and edge pairs sit at mean "
    "rho_trail 0.103 vs 0.0003). Context arms, never deciding: diagonal (the "
    "industry assumption), sample, ledoit_wolf, rmt_denoised. Reported never "
    "deciding: risk-forecast calibration (realised/predicted vol), realised max "
    "drawdown, effective bets 1/sum(w^2), top-eigenvalue share, condition "
    "number, pre-repair min eigenvalue, weight turnover."
)

KILL = (
    "Frozen BEFORE compute. ADOPT into research use only if ALL of: (1) the "
    "oracle gate passes; (2) model_semantic - model_numeric exceeds its own MDE "
    "with the sign meaning LOWER realised risk; (3) ALL THREE placebos are "
    "inside their own MDEs; (4) H2 holds on the long-only capped total-return "
    "portfolio. Otherwise: gate fails -> UNDERPOWERED_BY_CONSTRUCTION (escalate "
    "under a new name); gate passes and (2) fails -> NOT_DETECTABLE (an "
    "informative null, because the oracle said there was room); (2) passes and "
    "(3) fails -> PLACEBO_CONTAMINATED; (2) passes and (4) fails -> "
    "LONG_SHORT_ONLY (research result, NOT product value). Inside the MDE is "
    "NOT DETECTABLE - never a kill, never a win (S19). "
    "May NOT conclude: any alpha, Sharpe, return or skill claim (this trial "
    "contains no return forecast at all); that MARKET-GRAPH-1 H1 is weakened by "
    "a null here if the gate failed; that anything seeds, sizes or arms any "
    "lane (A5/A6/A7 - certification is forward-only); that the long-short "
    "primary is product value if H2 fails. Runtime assertions that VOID an arm: "
    "an arm receiving a PSD repair, solver budget, volatility block or "
    "constraint set different from the others; any forward quantity entering a "
    "non-oracle arm; any new LLM call."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdict", action="store_true")
    a = ap.parse_args()

    if not a.verdict:
        row = register_trial(
            name="GRAPH-COVARIANCE-1",
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

    row = register_trial(
        name="VERDICT-GRAPH-COVARIANCE-1",
        hypothesis=f"GRAPH-COVARIANCE-1 verdict: {r['trial_verdict']}. "
                   f"{r.get('verdict_line', '')}",
        expected_effect=json.dumps(r.get("headline", {}), default=str),
        kill_condition=KILL,
    )
    print(json.dumps({"registered": row["name"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
