# TRIAL-<NAME>

**Registered:** <UTC timestamp — BEFORE any return is computed>
**Registry row:** appended to `TRIALS/registry.jsonl` via `register_trial()`

## Hypothesis
<One paragraph. The economic mechanism, not the pattern. Why should this edge
exist, who is on the other side of the trade, and why can't Citadel take it?>

## Literature prior
<What the published record says, including the decay story.>

## Expected effect size
<Honest number with units, e.g. "40–80 bps/mo gross in the microcap decile".>

## Expected decay / capacity
<Horizon over which it should fade; rough $ capacity.>

## Kill condition
<Pre-committed: what result kills this line of inquiry. e.g. "net t-stat < 1
over the walk-forward window" or "edge only present in full universe but not
largest-500 (survivorship artifact)".>

## Two-arm design
- Arm A (expected LOSS): <the control that validates the pipeline>
- Arm B (the claim): <the actual hypothesis>

## Run spec (frozen before execution)
- Panel window, universe filters, cost bps, ranker kind, config — exact values.
- ONE run. The result is final for this trial.

## Result (filled in AFTER the run — never edited afterwards)
- Gate report (DSR at cumulative n, PBO, survivorship bound):
- Verdict: ADOPT-CANDIDATE / REJECT
- If REJECT: one-paragraph negative result → mirror to main repo NEGATIVE_RESULTS.md
