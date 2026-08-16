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

## R13 — resolvability, declared BEFORE compute (required; `lint_prereg` refuses without it)
<Derive `declared_effect_size` from ECONOMICS — turnover, cost, capacity,
expected frequency, drawdown consequence, probability of ruin — and then ask
whether the corpus can resolve it. Never the other way round: choosing 10pp
because 25 episodes can see 10pp is the same error inverted.>

- event_frequency_per_year: <INDEPENDENT episodes of the conditioning state per
  year, not days. Crisis regimes ~0.7/yr; insider filings ~440,000/yr.>
- declared_effect_size: <e.g. 10pp — the smallest effect that would change a
  portfolio decision, with the economic argument above it>
- outcome_dispersion: <sd of the outcome in that state: a number in pp, or one
  of the measured presets `crisis` (17.7pp), `calm` (1.5pp), `single_name` (12pp)>
- corpus_years: <optional; defaults to 36, the N2 twelve-market span>

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
