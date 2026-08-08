# PRE-REGISTRATION — TRIAL-LLM-AMNESIA-1 (2026-08-08)

**Written BEFORE any LLM call is made.** Registered under CANON §6.

## The question Murat asked

*"The LLM can't work on the past — true. But can we force DeepSeek not to
remember? We put guidelines saying don't use historical data. What do you
expect will happen, what should happen, what happened, what did we learn?"*

This trial answers it with a measurement instead of an opinion, and builds the
masked/synthetic scenario machinery (EXECUTION_STANDARD §5.1) at the same time.

## Design — one situation, four disclosure arms

Each event is ONE real historical situation (a US-listed largemid stock at a
formation month, described only by facts knowable at that month). The four arms
differ **only** in what identity/date information is disclosed and what the
model is instructed to do with its memory:

| Arm | Entity | Date | Instruction |
|---|---|---|---|
| **A0 NAMED-RAW** | real name + ticker | real, absolute | none |
| **A1 NAMED-INSTRUCTED** | real name + ticker | real, absolute | strong: "you are standing in {date}; you must not use any knowledge of what happened after it" |
| **A2 MASKED** | none (sector only) | none (relative "month 0") | masked-context framing |
| **A3 SYNTHETIC** | fabricated name + ticker | scrambled | explicit simulation framing, percentiles jittered ±3 |

Facts held identical across arms: liquidity segment, broad sector, and the
cross-sectional percentiles of trailing 12-month return, trailing volatility,
gross profitability, book-to-market and 12-1 momentum, all computed at the
formation month from the survivorship-free panel.

**Task (identical in all arms):** `P(this stock's total return over the next 12
months exceeds the US market's total return over the same 12 months)`, returned
as strict JSON with an ABSTAIN option.

**Canary call (separate, run BEFORE the forecast so it cannot prime it):**
- masked arms → "identify the company and the calendar year, or say UNKNOWN"
- named arms → "do you recall what happened to this company over the following
  12 months? RECALL-YES / RECALL-NO, and if yes, what?"

## Sample (frozen)

120 events: 60 outcome-positive (beat the market over the next 12 months) and
60 outcome-negative, drawn seeded (seed 20260808) from formation months
**2005-01 .. 2021-12**, largemid segment only — the segment where a model
plausibly knows the names, which is the point. Delisted names are kept:
realized months are compounded including the delisting return and the remainder
is treated as liquidated into the index.

Model: `deepseek-chat`, temperature 0, single sample per (event, arm, call).
Single-shot rather than median-of-10 is deliberate: this trial measures the
CONTAMINATION GAP between arms, not the production elicitation quality.

## Primary metric and decision rule

**Primary metric: the Brier score of each arm, and the arm-to-arm gaps.**

- **Instruction-effectiveness (the question asked):** ΔBrier(A1 − A0) and
  Δidentification/recall(A1 − A0). The instruction is judged EFFECTIVE only if
  A1's recall rate falls at least 30 percentage points below A0's AND A1's
  Brier moves at least 0.02 toward the masked arms. Anything less means the
  instruction is decoration, and masking is mandatory.
- **Contamination magnitude:** Brier(A2) − Brier(A0). This is how much of the
  named model's apparent skill was memory rather than reasoning.
- **Residual skill:** Brier(A2) and Brier(A3) versus the climatology baseline
  (the sample's 50/50 construction ⇒ Brier 0.25) and versus a logistic
  regression on the same five percentile features fitted out-of-sample. The
  LLM earns attention only if it beats the cheap baseline.

## Declared predictions (scored afterwards, hit or miss)

1. **A0 recall rate ≥ 40%** — the model will report remembering outcomes for
   large, famous names.
2. **The instruction FAILS: A1 recall within 15 points of A0, and
   |ΔBrier(A1−A0)| < 0.02.** Telling a model to forget does not remove the
   information from its weights; it removes it from the *stated rationale*.
3. **A2/A3 identification ≤ 10%** (masking works where instruction does not).
4. **Brier(A2) − Brier(A0) ≥ +0.02** — i.e. removing identity costs measurable
   accuracy, which is the size of the contamination.
5. **Neither A2 nor A3 beats the logistic baseline** on Brier. The honest
   expectation is that masked LLM forecasting on this task has little or no
   information content — consistent with every live-money LLM-forecaster
   benchmark in the R1–R4 corpus.
6. **A3 ≈ A2** within 0.01 Brier — a fabricated wrapper neither helps nor hurts
   once identity is already gone; its value is that it can be generated at
   unlimited scale for scenarios that provably cannot be memorized.

## What this trial may NOT do

No allocation, no lane, no signal. Outputs are (a) a measured answer to Murat's
question, (b) a calibrated masking protocol + contamination canary for
EXECUTION_STANDARD §5.1, (c) the scenario generator. Any claim of LLM alpha
still requires the forward claim ledger; replay produces bounds and baselines
only.

## One shot

Frozen sample, frozen prompts, one run. Prompts and responses are cached
immutably keyed by (arm, event_id) hash; a re-run reuses the cache. Changing a
prompt is a new trial ID.
