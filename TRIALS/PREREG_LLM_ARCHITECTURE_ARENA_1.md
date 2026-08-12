# PREREG — LLM-ARCHITECTURE-ARENA-1

**Drafted 2026-08-12, before any arm runs.** From Murat's architecture review of
2026-08-12 (archived `aegis-finance/docs/NIGHT14_ARCHITECTURE_REVIEW.md`).

## Provenance — the measurement that motivates this

LLM-SWARM-1 spent 8,014 calls on fourteen specialist personas and measured its
own ceiling:

| measured | value |
|---|---|
| records minted | 20,073 |
| `effective_distinct_ideas` ratio | **0.2996** |
| mean pairwise probability spread, same security x observable x horizon | **0.059** |

Fourteen personas behaved approximately as **one forecaster**. The review's
diagnosis is that this is a property of the PROMPT ARCHITECTURE, not of the
model: every role received the same point-in-time snapshot, was told it had
"no live feed", and was forced into the same large output contract (scenarios,
price targets, multi-horizon probabilities) regardless of its information class.
A geopolitical analyst and a forensic accountant were made to answer the same
question in the same shape, so they answered it the same way.

**That is a falsifiable claim and this trial falsifies or supports it.**

## Hypothesis

> Varying the **information pipeline** — what the model is given, in what
> sequence, and what it is asked to emit — produces materially more distinct
> information per dollar than varying the **persona** at fixed pipeline.

Honest prior: **70/30 in favour**, stated before running. The 0.059 spread is
strong evidence that persona variation is near-exhausted, but the possibility
this trial is built to detect is that the ceiling is the MODEL's, in which case
every arm lands at the same ratio and the answer is "stop buying diversity from
this vendor."

## Arms (identical items, identical targets, paired)

| arm | pipeline | output contract |
|---|---|---|
| **A0 SNAPSHOT-PERSONA** | the SWARM-1 prompt, unchanged | full (control) |
| **A1 FINE-GRAINED** | extract -> novelty -> expectedness -> propagate -> market-expectation -> discrepancy -> forecast, each a separate call with a small schema | smallest per step |
| **A2 BELIEF-UPDATE** | prior frozen BEFORE evidence, evidence shown, posterior emitted | prior, posterior, evidence, delta |
| **A3 ADVERSARIAL** | proposer -> refuter -> merge | claim + surviving claim |
| **A4 TOOL-CALL** | model requests what it wants from a PIT tool layer instead of being handed a fixed snapshot | free, plus tool trace |
| **A5 MODEL TIER** | best arm re-run on `deepseek-v4-pro` vs `deepseek-v4-flash`, paired | as that arm |

A0 is the control and it is the corpse: this trial's job is to beat a thing we
already built and already measured.

## Primary metric — declared before any arm runs

**P1 (immediate, leakage-free): `effective_distinct_ideas` per dollar, per arm.**

This is the §20 batch self-check applied across arms. It does **not** depend on
outcomes, so it is immune to the leakage question LLM-LEAKAGE-PROBE-1 is
currently deciding, and it is the direct successor to the 0.2996 measurement.

Reported beside it, never deciding: schema-valid rate, abstention rate, cost per
gradeable output, tool-call counts, served_model.

**P2 (immediate, PROVISIONAL): paired Brier skill vs climatology on historical
items.** Labelled `ARCHITECTURE_RESULT_ONLY`. **VOID if LLM-LEAKAGE-PROBE-1
returns an identified-vs-masked gap above its own MDE** — in that case the model
is scoring by recall and P2 measures memory, not pipeline.

**P3 (certification, resolves from 2026-08-16): forward Brier and rank-IC by
arm**, from records minted tonight into the forward ledger.

## Decision rule

- **P1 and P2 may only decide WHICH ARM GETS SCALED.** They are an exploration
  allocation, not evidence of skill.
- **No arm receives production weight, specialist authority, or a portfolio
  role from this trial.** That requires P3 with resolved forward records, and
  A5 of Amendment A binds unchanged.
- An arm whose P1 does not exceed A0's by more than A0's own measured
  dispersion across bootstrap resamples is **not detectably better** (§19) —
  recorded as such, never as a kill.
- If **no arm** beats A0 on P1, the finding is *the ceiling is the model's, not
  the prompt's*, and the correct response is to stop buying diversity from
  DeepSeek and spend the budget on the graph and teacher tracks instead. That
  outcome is a result, not a failure.

## Frozen parameters

Item set (securities x dates), horizons `(1,2,5,20,60,120,252)`, the climatology
baseline, the `effective_distinct_ideas` definition as already implemented, and
the arm definitions above. Temperature is a REPORTED covariate, not a tuned one.

## Hard constraints

1. **`served_model` is read off every response body and stored.** The requested
   name is not evidence: `deepseek-chat` and `deepseek-reasoner` both resolve
   server-side to `deepseek-v4-flash`, which voided one arm of a running trial
   on 2026-08-12.
2. **Historical records go to a separate ledger.** `predictions.jsonl` stays
   forward-only; its value is that it has never been backfilled.
3. **A4 may not use live web search on a historical date.** A search run today
   returns today's index — that is leakage by construction, not retrieval. A4 is
   therefore **forward-only**, or historical against an archived PIT corpus, and
   the report must say which.
4. **The p = 0.50 refusal is REPLACED in A2, not inherited.** Banning 0.50
   without offering an alternative teaches the model to say 0.51. A2's abstain
   channel is `posterior == prior`, which is a first-class, informative answer.
5. Descriptive-only. No arm's output reaches a buy/sell surface.

## Corpse check

Run before registration; verdict recorded in the trial doc.
