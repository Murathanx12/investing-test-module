"""Append the INTERNET-INVESTIGATOR-FWD-1 registration to TRIALS/registry.jsonl.

    python -m scripts.register_internet_investigator_fwd_1              # BEFORE accrual
    python -m scripts.register_internet_investigator_fwd_1 --verdict    # AFTER 40 nights

The row must exist before the first prediction is emitted -- the registry row
plus the commit timestamp is the tamper evidence, and for a FORWARD trial it is
the only tamper evidence there can be. The verdict row refuses to write before
the receipt exists AND before the minimum accrual is reached, because a forward
verdict read early is peeking with extra steps.

ACCRUES ZERO ARMS -- it cannot promote, seed or size anything. It still
increments the cumulative multiple-testing count.
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
from scripts import iif1_config as C                    # noqa: E402

RUNS = MODULE_ROOT / "runs" / "INTERNET-INVESTIGATOR-FWD-1"
RECEIPT = RUNS / "grade_report.json"

HYPOTHESIS = (
    "Track C of ROADMAP_BRAIN_V3. SWARM-1 gave fourteen specialists the same "
    "engineered point-in-time snapshot and told them they had no live feed; "
    "this asks whether letting the model INVESTIGATE adds anything beyond that "
    "snapshot. FORWARD-ONLY. Five arms forecasting IDENTICAL cells (same "
    "triggered tickers, nights, observables, horizons) so the comparison is "
    "paired within the cell: A_snapshot (engineered numbers only), B_tools "
    "(snapshot + search_news/read_filings/query_revisions/query_options/"
    "query_prices/query_market_graph), C_tools_only, D_all (+ MARKET-GRAPH-1 "
    "semantic graph), B_anon (B with ticker identity masked). "
    "H1 PRIMARY: B_tools beats A_snapshot on paired Brier. H2: C_tools_only is "
    "worse than A_snapshot (the engine carries real weight). H3: anonymisation "
    "does NOT improve forecasts -- the direct test of Glasserman & Lin, banked "
    "in NEGATIVE_RESULTS S19. "
    "PRIMARY METRIC: paired per-night mean Brier difference; because cells are "
    "paired the irreducible pi(1-pi) term cancels EXACTLY, so the statistic is "
    "the difference in squared error against the true probability and nothing "
    "else. Collapsed to one number per night BEFORE any SE; n = graded NIGHTS "
    "not predictions; Newey-West 2 lags; SE = max(HAC, IID); MDE = 2.80 x SE "
    "(S19). Contract is MICROTASKS (event extractor / relationship extractor / "
    "expectations analyst / forecaster / critic) under the BELIEF-CHANGE "
    "contract prior-posterior-belief_change, where belief_change = 0 is a "
    "valid gradeable answer and the p != 0.50 refusal is RETIRED. "
    "THIS TRIAL MAKES NO ALPHA CLAIM AND CANNOT: it grades forecast quality, "
    "never returns; nothing is traded, sized, weighted or allocated. "
    "Honest priors: H1 ~35/65 AGAINST, H2 ~70/30 for, H3 ~60/40 for. "
    "ACCRUES ZERO ARMS. Full doc TRIALS/PREREG_INTERNET_INVESTIGATOR_FWD_1.md."
)

EXPECTED = (
    "DESIGN CHOSEN AGAINST A MEASURED CLOCK, BOTH RECEIPTS COMMITTED BEFORE "
    "THE PREREG WAS FINALISED. (a) iif1_power.py simulated nights-to-80%-power "
    "for the paired Brier statistic: at sigma_pi 0.02 it is NEVER detectable at "
    "any trigger count or effect size; at 0.10 it resolves in 40-250 nights at "
    "k=40. (b) iif1_sigma.py MEASURED sigma_pi as a variance-decomposition "
    "lower bound across trailing-vol deciles with the binomial sampling term "
    "subtracted, on 927,423 observations of the 400 largest names 2015-2024: "
    "return_sign 1d = 0.0036 (realised rate moves only 0.517->0.529), "
    "return_sign 5d = 0.0061, abs_move 5%/1d = 0.0450, 8%/5d = 0.0734, "
    "3%/1d = 0.0953, abs_move 5%/5d = 0.1183 (rate 0.052->0.442). "
    "CROSS-REFERENCED, THIS OVERTURNS THE ROADMAP DEFAULT: a direction-based "
    "primary NEVER resolves, so the PRIMARY OBSERVABLE IS MAGNITUDE -- "
    "abs_move_exceeds 5%/5d and 3%/1d. Direction observables are still recorded "
    "for the ledger and are PRE-DECLARED UNABLE TO RESOLVE THIS TRIAL; a null "
    "on them may not be reported as a kill. Deviation from the roadmap recorded "
    "as a deviation. "
    "HONEST DEFLATION STATED UP FRONT: the 0.1183 bound is measured from "
    "trailing volatility alone and arm A's snapshot already carries trailing "
    "AND options-implied vol, so arm A captures a large share of that budget "
    "before investigation adds anything; the residual budget H1 competes for is "
    "smaller and is not separately measurable in advance. "
    "Triggers: k=40/night, frozen numerical composite (1d residual return |z|, "
    "20d volume z, earnings within 5d, filing within 2d), NO LLM output in the "
    "trigger rule -- otherwise the arms stop seeing the same cells. k=40 not 10 "
    "because trigger volume is worth 2-3x in time-to-detection while the dollar "
    "ceiling is nowhere near binding (~$0.75/night expected against $10-15). "
    "NEGATIVE_RESULTS S19's three-receipt rebuttal is discharged in the prereg: "
    "(1) the withdrawn Kim/Muhn/Nikolaev paper's failure mode is structurally "
    "impossible forward-only; (2) FINSABER is a trading claim and this grades "
    "forecast quality with nothing traded; (3) Glasserman & Lin's anonymisation "
    "finding is PROMOTED INTO A PRE-REGISTERED ARM rather than argued away."
)

KILL = (
    "Frozen BEFORE accrual. H1 ADOPTED as a research result about FORECAST "
    "QUALITY ONLY if ALL of: (1) B_tools - A_snapshot exceeds its own MDE with "
    "the sign meaning better forecasts; (2) it holds on BOTH primary "
    "observables, or on the pooled statistic with singles printed beside it; "
    "(3) the SERVED MODEL is verified identical across arms; (4) the effect is "
    "not reproduced by B_anon in a way that says ticker identity rather than "
    "investigation did the work. Otherwise: (1) fails -> NOT_DETECTABLE; (1) "
    "holds and (2) fails -> SINGLE_OBSERVABLE_ONLY (reported, not adopted); (3) "
    "fails -> VOID and rerun with served models pinned. Reported prominently if "
    "they occur: C_tools_only beating A_snapshot (the engine snapshot is not "
    "carrying its weight); B_anon beating B_tools above its MDE (S19 receipt 3 "
    "REPRODUCED). Inside the MDE is NOT DETECTABLE -- never a kill, never a win "
    "(S19). "
    "MAY NOT BE READ AT ALL below 40 graded nights -- reading earlier is "
    "peeking, and the power table says nothing below 40 could clear its MDE. "
    "MAY NOT CONCLUDE: any alpha, return, Sharpe, skill or tradability claim "
    "(no return is forecast and nothing is traded); that direction is or is not "
    "forecastable (pre-declared underpowered); that anything seeds, sizes, arms "
    "or weights any lane or specialist (A5/A6/A7 -- certification is "
    "forward-only and needs 24 months). Runtime assertions that VOID an arm: an "
    "arm receiving a different cell set, a different served model, a trigger "
    "rule containing LLM output, any historical web retrieval, or nightly spend "
    "exceeding the ceiling unlogged."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdict", action="store_true")
    a = ap.parse_args()

    if not a.verdict:
        row = register_trial(
            name="INTERNET-INVESTIGATOR-FWD-1",
            hypothesis=HYPOTHESIS,
            expected_effect=EXPECTED,
            kill_condition=KILL,
        )
        print(json.dumps({"registered": row["name"],
                          "at": row["registered_at"]}, indent=1))
        return 0

    if not RECEIPT.exists():
        raise SystemExit(
            f"{RECEIPT} missing - the trial has not been graded; a registry row "
            f"without a receipt is a lie")
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))
    n = int(r.get("n_graded_nights", 0))
    if n < C.MIN_GRADED_NIGHTS_BEFORE_READ:
        raise SystemExit(
            f"{n} graded nights < {C.MIN_GRADED_NIGHTS_BEFORE_READ} required. "
            f"Refusing to write a verdict row: the pre-registration forbids "
            f"reading the primary this early, and a verdict written at n={n} "
            f"would be peeking with a registry row attached.")

    row = register_trial(
        name="VERDICT-INTERNET-INVESTIGATOR-FWD-1",
        hypothesis=f"INTERNET-INVESTIGATOR-FWD-1 verdict: {r['trial_verdict']}. "
                   f"{r.get('verdict_line', '')}",
        expected_effect=json.dumps(r.get("headline", {}), default=str),
        kill_condition=KILL,
    )
    print(json.dumps({"registered": row["name"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
