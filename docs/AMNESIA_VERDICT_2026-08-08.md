# Can you tell an LLM to forget? — measured, 2026-08-08

**Question (Murat):** *"The LLM can't work on the past — true. But can we force
DeepSeek not to remember? We put guidelines saying don't use historical data.
What do you expect will happen, what should happen, what happened, what did we
learn?"*

Two pre-registered trials answer it: **TRIAL-LLM-AMNESIA-1** (the four-arm
experiment) and **TRIAL-LLM-AMNESIA-1B** (the positive control that keeps the
first one honest). 1,080 `deepseek-chat` calls, temperature 0, every prompt and
response cached at `runs/AMNESIA/cache*`. Registrations were committed before
any call was made.

---

## 1. What I expected (written before the run)

Six declared predictions, in `TRIALS/PREREG_LLM_AMNESIA_1.md`:

| # | Prediction | Result |
|---|---|---|
| P1 | Named model reports recalling outcomes for ≥40% of famous names | **MISS** (15.8%) |
| P2 | **The instruction fails** — recall within 15pts of the un-instructed arm and ΔBrier < 0.02 | **HIT** |
| P3 | Masked identification ≤ 10% | **HIT** (0.0%) |
| P4 | Removing identity costs ≥ 0.02 Brier | **MISS** (0.007) |
| P5 | Masked LLM does not beat a 5-feature logistic baseline | **HIT** |
| P6 | Synthetic ≈ masked within 0.01 Brier | **HIT** (0.0004) |

4 of 6. The two misses are the interesting part and are discussed in §4.

## 2. What *should* happen (the design principle)

You cannot remove information from a model's weights with a sentence in the
prompt. The only thing an instruction can change is what the model *says*. So
the correct control is not "tell it to forget" — it is **make the question
unrecognizable**: strip the entity, strip absolute dates, express every fact as
a cross-sectional percentile, and then *verify* the stripping worked with a
canary that asks the model to identify what it is looking at. If it can, the
sample is burned.

That is the protocol frozen in `EXECUTION_STANDARD_2026-08-08.md` §5.1. This
trial's job was to check whether it survives contact with a real model.

## 3. What happened

**The setup.** 120 real situations (US largemid stocks, 2005–2021), outcome-
balanced 60/60 on "did it beat the market over the next 12 months". Each
situation is described by the same five point-in-time percentile facts in all
arms. Only the identity/date disclosure differs.

| Arm | Brier | AUC | answered | canary |
|---|---|---|---|---|
| A0 named, no instruction | **0.2495** | 0.550 | 115/120 | reports recall on **15.8%** |
| A1 named + "you are in the past, do not use later knowledge" | **0.2530** | 0.532 | 113/120 | reports recall on **15.8%** |
| A2 masked | **0.2568** | 0.519 | 117/120 | identified **0 of 120** |
| A3 synthetic (fake name, fake date, jittered facts) | **0.2564** | 0.521 | 120/120 | identified **0 of 120** |
| climatology (always 0.5) | 0.2500 | — | — | — |
| logistic regression, out-of-sample, same 5 features | 0.2538 | 0.511 | — | — |

**Finding 1 — the instruction does nothing.** Recall rate with and without the
suppression instruction: **15.8% vs 15.8%** — identical to three decimals. Brier
moved +0.0035, i.e. the instructed arm was very slightly *worse*. A strongly
worded "you are standing in {date}, you must not use knowledge of what happened
after it" changed the model's wording and not its behaviour.

**Finding 2 — masking works where instruction fails.** Across 240 masked and
synthetic canaries the model identified the company **zero times** and never
even volunteered a year. The masking protocol is now measured, not assumed.

**Finding 3 — synthetic scenarios are a valid substitute for real ones.**
A3 (fabricated company, fabricated date, ±3-point jittered percentiles) scored
within 0.0004 Brier of A2. This validates the scenario generator: we can
manufacture unlimited situations from the 63-year panel that provably cannot
exist in any training corpus, and the model behaves the same way on them.

**Finding 4 — on this task nobody has skill, including the LLM.** All four arms
sit at the climatology Brier of 0.25 with AUC 0.51–0.55, and the model hedges
hard (mean p 0.46, sd 0.08). The cheap logistic baseline is also at chance
(AUC 0.511). So this particular question — 12-month relative return from five
percentiles — carries little learnable signal for anyone, which limits how much
the contamination test could have detected. Stated as a limitation, not
explained away.

### 3B. The positive control (why the above is not over-read)

"The instruction failed to suppress memory" and "there was no memory to
suppress" look identical in aggregate. TRIAL-LLM-AMNESIA-1B asked the model
outright, with no suppression framing, what those same 120 stocks actually did.

- It **declined to answer on 95.8%** of them (5 of 120 answered).
- On the 5 it did answer: **5 of 5 correct**, every one a LAG call, every one a
  famous collapse — PYPL from 2021-10 (−64%), CHK from 2015-03 (−71%), GOEV
  from 2021-06 (−81%), THQI from 2007-01 (−41%), BTU from 2013-05 (−16%).
- Numeric 12-month returns: answered 4.2% of the time, median absolute error
  **43.6 percentage points** — the numbers are confabulated even when the
  direction is right.
- The survival leg of the control is **VOID by metric mismatch** (the question
  asked about 24 months; the available ground truth was 12-month realization).
  Recorded as a defect, not quietly dropped.

So memory is **real, sparse, and self-selecting**: roughly 4% of cases, and on
those it is essentially perfect.

**And the concentration check.** On those 5 memory-positive events, every arm
scored better than on the rest — including masked (0.175) and synthetic (0.147),
which cannot know the identity at all. With n = 5 this is weak evidence, but it
points the same way: those situations *looked* bad on the observable facts too.
The recalled cases were not cases where memory beat reasoning.

The pre-registered reading rule in 1B keyed on "answers often AND is right",
and the observed regime — answers almost never, but is perfect when it does —
was not one of its branches. The rule is recorded as insufficient rather than
forced onto the data.

## 4. What we learned

1. **Never accept an instruction as a control.** A guideline saying "don't use
   historical data" produced a measured effect of zero. Any future design that
   relies on one is invalid by this receipt.
2. **Masking is the control, and canaries are how you know it held.** 0/240
   identifications on this event schema. Every replay batch runs the canary; a
   sample that gets identified is burned and logged, never reused.
3. **Aggregate metrics hide contamination.** Removing identity cost only 0.007
   Brier overall — while 4% of cases carried near-perfect foreknowledge. A
   naive unmasked replay would surface exactly those few as spectacular calls
   and bury them in an unremarkable average. **Contamination must be measured
   per-case with a canary, never inferred from an aggregate score.**
4. **The model remembers catastrophes, not returns.** Every recalled case was a
   collapse. Any event class whose outcomes are dramatic (bankruptcies, failed
   drug approvals, blow-ups) is maximally contaminated; mundane outcomes are
   nearly clean.
5. **The synthetic path is open**, which answers the second half of the
   question. If a real-history replay cannot be trusted, we do not stop — we
   generate scenarios from real panel data with the names and dates replaced,
   and A3 shows the model treats them as it treats the masked originals.
6. **This task is retired for LLM evaluation.** 12-month relative return is
   unlearnable here for the LLM *and* the baseline, so it cannot discriminate
   between "no skill" and "no signal". AMNESIA-2 moves to short-horizon event
   reactions (5-day abnormal return around earnings / FDA decisions) where the
   baseline bank has measurable signal, with famous-case stratification and the
   positive control built in from the start.

## 5. What changes in the machinery

- `aegis_brain/llm/amnesia.py` is the masking + synthetic scenario generator,
  now validated. It is the input path for the NIGHT-2 replay harness.
- The four-arm design becomes the standard template for every new event class:
  no LLM number enters the claim ledger from an unmasked prompt.
- The contamination canary is a **gate**, not a diagnostic: burned samples are
  excluded before any scoring.
- The forward claim ledger (`aegis_brain/abn/`) remains the only place an LLM
  can earn credit, exactly as D3 says. Replay produces bounds and baselines.

**Receipts:** `runs/AMNESIA/AMNESIA_1.json`, `runs/AMNESIA/AMNESIA_1B.json`,
`runs/AMNESIA/event_set.csv`, prompt/response cache under `runs/AMNESIA/cache*`.
Registrations: `TRIALS/PREREG_LLM_AMNESIA_1.md`, registry rows
`TRIAL-LLM-AMNESIA-1`, `TRIAL-LLM-AMNESIA-1B`.
