# NIGHT-3 VERDICT — masked decision replay and the experience brain

**Trial:** `TRIAL-NIGHT3-DECISION-REPLAY-1` · pre-registration
`TRIALS/PREREG_NIGHT3_DECISION_REPLAY.md`, sealed **before** the first LLM call.
**Branch:** `factory/night-3` (Aegis module). No lane seeded, no flag flipped,
`paper_nav` untouched.
**Holdout:** 2023-01..2024-12 **verified unread programmatically** —
`scripts/night3_verify_holdout.py`: max decision 2021-12-31, max resolution
2022-01-31, and 0 of 2,728 cached prompts contain a real 2023+ date.
**Model:** `deepseek-chat`, temperature 0, every response cached immutably by
`(model_id, sha256(system+user))`. **Spend $2.33 of a $25 cap.**
**Denominator:** 406 graded LLM calls in the replay (2,728 cached prompts across
the whole night), 4 arm books, 100 placebo books, **16,320 graded decisions**.

---

## 1. The headline, and it was produced without an LLM

Inside the engine's own top-40 profitability slate, sorting by the composite is
worth **+1.46 %/yr at t = 0.43** (top-20 minus bottom-20 of the same 40 names,
204 months, gross). That is nothing. A stratified slate spanning all five
composite quintiles is **worse** (t = 0.15, mean monthly separation 0.054 % vs
0.14 %).

> **PROF-COMPOSITE's edge is MEMBERSHIP — which ~150 names out of ~2,000 — not
> ORDERING. At the monthly name level, inside that membership, nothing ranks:
> not the LLM, not the engine, not anything, at this sample size.**

**What this bought:** the stratified environment was built and then **not run**.
The power analysis is the receipt; a second 204-month LLM campaign would have
cost a night to learn the same thing.

### 1b. Independent corroboration, from numbers already on disk

**Not a new test** — a re-reading of the banked PF-1/PF-2 concentration grid. If
ordering carried information, deepening from 10 names to 150 would progressively
add worse names and returns would fall. They do not:

| names held (small-cap) | 10 | 25 | 50 | 100 | **150** | 200 |
|---|---|---|---|---|---|---|
| net excess CAGR | +4.46 % | +4.35 % | +4.71 % | +4.36 % | **+4.67 %** | +3.87 % |
| NW t | 1.92 | 2.00 | 2.30 | 2.36 | **2.52** | 2.34 |

Flat return, monotonically rising t. Names ranked 26th-150th are as good as
names ranked 1st-25th; breadth buys less noise around the same edge, and
dilution starts past ~200. Segment is what matters: **+4.67 % small, +2.29 %
all-cap, +1.56 % large/mid** — the same fact PF-2's factor gate saw from the
other side (`rmw` loading 0.135).

**Consequence for Murat's "bigger margins":** the lever is *membership* —
universe, depth, cost — not better picking. And an LLM asked to re-rank inside
the selected set is being asked to do the one job with no information in it.

---

## 2. M1 and M2 — the registered verdicts

204 months, 2005-01..2021-12, 40-name masked slate, 20-name equal-weight book,
25 bps on newly-added names, paired on the same names in the same month.

| arm | net excess CAGR | NW t | turnover (1-way, ann.) | recosted placebo p |
|---|---|---|---|---|
| ENGINE (composite top-20) | +3.64 % | 1.34 | 2.07 | 0.15 |
| EW40 (hold all 40) | +3.32 % | 1.54 | 1.90 | — |
| **A** — LLM, no memory | **+4.67 %** | 2.30 | 4.80 | 0.05 |
| **E** — LLM + episodic memory | **+6.21 %** | 2.58 | 5.86 | 0.01 |

**M1 (A − ENGINE): REJECT.** +1.03 %/yr in CAGR terms but mean monthly
difference **0.006 %**, **NW t = 0.04**.
**M2 (E − A): REJECT.** +1.54 %/yr, **NW t = 0.93**.

**Both registered predictions HIT (N1, N2).** And both were predictions against
my own arms.

### Why the standalone numbers must not be quoted instead

Arm E's +6.21 % at t 2.58 is the best number in the campaign and it beats 99 of
100 recosted random books. It is **not** evidence that memory works, for a
reason that has to be said plainly:

**those t-stats are computed against the benchmark, and every arm — including
the engine and the placebo — carries the same small-cap profitability
premium.** A t of 2.58 on arm E's excess is mostly *the strategy's* premium, not
the LLM's contribution. The paired difference is the instrument that isolates
the LLM, and it says nothing detectable. Substituting the standalone number for
the registered metric is precisely the metric substitution the registry exists
to prevent.

### The control that can only undercut arm E — registered, running, incomplete

`DIAG-NIGHT3-MEMORY-PLACEBO-1`, registered before compute at 09:18 UTC. Arm
**E-SHUFFLED** sees memory of identical shape, volume and marginal outcome
distribution, with **only the situation→outcome mapping destroyed** by a seeded
permutation — in the kNN neighbours *and* in the persistence block. If
E-SHUFFLED matches E, what helped was the presence of a memory block, not its
content.

**Result: see §5b.** It changes no registered verdict — M2 is already REJECT,
and the control was never able to promote anything. Its job is to say whether
the little that arm E does have is about memory *content* or merely about a
memory *block* being present.

### What the test could ever have detected

| paired difference | monthly SD | **MDE at t = 2** | observed |
|---|---|---|---|
| A − ENGINE | 3.32 % | **5.58 %/yr** | +0.08 %/yr |
| E − A | 2.15 % | **3.62 %/yr** | +1.46 %/yr |
| E − ENGINE | 3.50 % | **5.89 %/yr** | +1.54 %/yr |

So "REJECT" means **"smaller than ~3.6-5.6 %/yr, if it exists at all"** — never
"zero". Note also that the registered rule's CAGR bars (+1.5 %, +1.0 %) are
*looser* than what its own t ≥ 2.0 requirement implies; the t-bar was the
binding constraint throughout. That is a design flaw in my registration, not in
the result, and it is recorded rather than quietly ignored.

### Two defects found in my own harness, corrected not caveated

1. **The placebo was overcharged.** Random books were billed 100 % turnover
   every month; a random 20-of-40 redrawn monthly actually turns over ~58 %.
   Recosting with the same incumbency accounting the real arms get moved the
   band from +0.60 % to **+1.53 %** mean and changed every p-value
   (ENGINE 0.04→**0.15**, A 0.02→**0.05**, E 0.00→**0.01**). The as-run numbers
   flattered the LLM arms.
2. **Persistence was over-graded.** The loop graded a re-review whenever a name
   had *any* prior belief, but the prompt only shows the 20 most recent priors
   under 12 months old. 3,450 of 7,490 recorded reviews were graded against a
   belief the model was never shown. N8 is scored on the **4,040 shown** only.

### Costs: the LLM's edge shrinks when billed properly

The replay charges one-way; production charges two-way. The LLM churns far more
than the engine (4.80 and 5.86 vs 2.07), so full costs hurt it more:
**M1 shifts −0.68 %/yr and M2 −0.26 %/yr.** Both still REJECT, and arm E's
standalone excess falls +6.21 % → **+4.75 %**.

---

## 3. The coherence gate, and what its failure actually was

100 synthetic scenarios × 5 perturbations × 2 sides = **1,000 calls, 500 usable
pairs**, one variable moving per pair.

| direction | registered format (decimal) | diagnostic (basis points) |
|---|---|---|
| valuation cheaper → more attractive | 0.66 · **34 ties · 0 wrong** | 0.90 · 10 ties · 0 wrong |
| earnings beat > miss | 0.56 · **44 ties · 0 wrong** | 0.87 · 12 ties · 1 wrong |
| bull ≥ bear regime | 0.75 · 25 ties · 0 wrong | 0.89 · 11 ties · 0 wrong |
| less geopolitical risk ≥ more | 0.95 · 5 ties · 0 wrong | 1.00 · 0 ties · 0 wrong |
| upward revisions > cuts | 0.93 · 7 ties · 0 wrong | 0.98 · 2 ties · 0 wrong |
| **passing at ≥0.70** | **3 of 5 → INCOHERENT** | **5 of 5** |

**The registered verdict stands: 3 of 5, prediction N3 MISS.** A gate re-run in
a friendlier format until it passes is not a gate.

But **0 wrong directions in 500 pairs**: the model never once reversed a
relationship. Every failure was a *tie*. `DIAG-COHERENCE-RESOLUTION-1` shows the
cause is **output quantization** — asked for decimals it answers in whole
percent steps, so it cannot express an effect smaller than one.

> **Engineering rule adopted forward-only: ask for integer basis points, report
> output resolution as a diagnostic, and never merge ties with reversals.**
> (Committed to `DESIGN_MEMORY_TAXONOMY_2026-08-09.md` §9.)

## 4. NAME-ONLY — the ceiling could not be measured as registered

Real ticker, real date, **no financial data**, on the identical 120-event set
AMNESIA used. **The model abstained 120 of 120**, basis `no_information`. Zero
scored events ⇒ **N4 UNRESOLVED**.

`DIAG-NAME-ONLY-FORCED-1` removed the abstain door:

| arm | Brier | AUC |
|---|---|---|
| **NAME-ONLY forced** (identity + date only) | **0.2483** | **0.571** |
| A0 named + full percentile facts | 0.2495 | 0.550 |
| A1 named + "ignore what you know" | 0.2530 | 0.532 |
| A2 masked | 0.2568 | 0.519 |
| A3 synthetic | 0.2564 | 0.521 |
| out-of-sample logistic, 5 features | 0.2538 | 0.511 |

Two things, said together or not at all: **on identity alone the model scores at
least as well as it does with the data** — and **none of it is significant**
(bootstrap 95 % CI **[0.481, 0.656]**, P(AUC ≤ 0.5) = 0.068, n = 120). Every arm
in that table sits within noise of a coin flip.

The forced arm used **5 distinct probability values** across 120 events
(0.35-0.55, sd 0.042) — the same coarse-output signature as §3, found
independently.

**Standing rule:** any future unmasked diagnostic must be quoted against the
forced number *and* against the fact that the unforced model declines 100 % of
the time.

## 5. Consistency — measured, never requested

**Repeat probe (N6 HIT on both conditions).** Identical prompts, re-asked:

- **temperature 0 → 96.5 % of per-name decisions identical.** The residual
  **3.5 %** is irreducible provider-side non-determinism and is a standing
  caveat on every graded call here.
- **temperature 0.7 → 21.6 % of decisions flip.** More than one name in five
  changes its BUY/HOLD/SELL on a re-ask of the same question.

That is Murat's noise complaint with a number on it, and it is why the immutable
cache — not a "please be consistent" instruction — is the mechanism.

**Decision persistence, shown-only (n = 4,040 reviews, 2,954 graded):**

| verdict | n |
|---|---|
| appropriate | 1,229 (41.6 %) |
| underreaction | 714 |
| overreaction | 674 |
| **direction-inconsistent** (large swing *against* the evidence) | **337** |

**N8 HIT, but barely** — 714 vs 674 is a difference of 40 in 2,954. The honest
reading is that the model over- and under-reacts about equally, and swings hard
against its own evidence 11 % of the time.

## 5b. The control: arm E's memory does not work because of its content

`DIAG-NIGHT3-MEMORY-PLACEBO-1`, registered before compute, run over the full
204 months. **Arm E-SHUFFLED** received memory of identical shape, volume and
marginal outcome distribution, with **only the situation→outcome mapping
destroyed** by a seeded permutation — in the kNN neighbours *and* in the
persistence block.

| arm | net excess CAGR | NW t |
|---|---|---|
| A — no memory | +4.67 % | 2.30 |
| **E-SHUFFLED — scrambled memory** | **+5.07 %** | 1.87 |
| E — real memory | +6.21 % | 2.58 |

**E − E-SHUFFLED = +1.13 %/yr, NW t = 0.43**, against a 4.52 %/yr MDE.

> **Verdict: MEMORY CONTENT NOT DEMONSTRATED.** Scrambled memory still beats no
> memory (+5.07 % vs +4.67 %), and real memory is not distinguishable from
> scrambled memory. Most of arm E's apparent advantage survives destroying
> everything the memory was supposed to *know* — so what helped was the memory
> **block**, not its **content**.

Stated with the same discipline applied everywhere else tonight: this is *"not
demonstrated at this sample size"*, not *"zero"*. The MDE is 4.52 %/yr and the
observed gap is 1.13 %/yr; a real content effect smaller than that would be
invisible here.

This is why the control was worth $0.82 and 50 minutes. Without it, arm E's
+6.21 % at t 2.58 — the best number in the campaign, beating 99 of 100 recosted
random books — would have been sitting in this document looking like learning.

**The number that matters most here:** the model's *stated* update
("STRENGTHEN"/"WEAKEN"/"MAINTAIN"/"REVERSE") matches its own *measured*
conviction change only **63.3 %** of the time. It restates the prior belief we
showed it with 97.4 % accuracy — trivially, since we showed it — but its account
of how it changed its mind disagrees with what it actually did in **more than
one case in three.** Another measured instance of the canon rule: **the LLM's
self-report is not evidence.**

## 6. What the belief network saw — its first at-scale workload

**10,154 claims → 10,154 resolutions, hash chain verified.** 6,166 HOLDs
correctly carry no directional claim.

Reliability of arm A, raw:

| stated probability | n | realized hit rate |
|---|---|---|
| 0.0-0.2 (high-conviction SELL) | 795 | 0.439 |
| 0.2-0.4 | 1,568 | 0.474 |
| 0.6-0.8 | 290 | 0.452 |
| 0.8-1.0 (high-conviction BUY) | 2,520 | 0.489 |

**A 5-point spread across the entire conviction range**, on a 47.5 % base rate.
Monotone in the right direction and economically nil. ECE **0.316 raw**, 0.205
after Platt (α = √3) — severely overconfident. Arm E: ECE 0.299 → 0.188.

**Cohort deflation did its job:** 3,560 resolutions in one cell deflate to
**n_eff 12.4**, because forty decisions on the same slate in the same month are
about one observation. The promotion gate refused every arm with all three
reasons (retrospective evidence, 0 forward months, t below 4.0) — which is the
gate working, not a finding.

**Behavioural difference worth recording:** on a slate selected *for
profitability*, the LLM reasons mostly by **momentum** — arm A: momentum 68 %,
reversal 22 %, profitability 4 %. Memory shifts it toward the fundamentals
(arm E: momentum 58 %, reversal 18 %, profitability 12 %, value 3 %). So memory
changes *how it thinks*, measurably, without changing outcomes detectably.

## 7. Prediction scorecard — 5 of 7 resolved

| # | prediction | result |
|---|---|---|
| N1 | M1 fails — LLM does not beat the engine | **HIT** (+1.03 %/yr, t 0.04) |
| N2 | M2 fails — memory does not clear the bar | **HIT** (+1.54 %/yr, t 0.93) |
| N3 | coherence ≥4/5 directions | **MISS** (3/5; 0 wrong, 115 ties) |
| N4 | NAME-ONLY AUC ≥ 0.55 | **UNRESOLVED** (120/120 abstained) |
| N5 | LLM rank correlates with engine, ρ ≥ 0.30 | **MISS** (mean Spearman **0.014**) |
| N6 | ≥90 % identical at T=0, ≥15 % flipped at T=0.7 | **HIT** (96.5 % / 21.6 %) |
| N7 | exposure ≥ 0.95, no hiding in cash | **HIT** (1.00 both arms) |
| N8 | under-reacts more than it over-reacts | **HIT, marginally** (714 v 674) |

**5/7 resolved.** (PF-1 scored 2/5; PF-2 4½/8.)

**N5 is the interesting miss.** I predicted the LLM would largely re-derive the
composite. Its ordering is instead **orthogonal** to the engine's — mean
Spearman 0.014 over 204 months. It is not copying the signal; it is doing
something else entirely, and that something else is not detectably better.

## 8. What was NOT done, recorded rather than omitted

- **No EDGAR/FDA text spine.** The registered TEXT-vs-NUMBERS arm did not run.
  The decision environment was built from the CRSP panel instead, which needs no
  external fetch and answers the registered question directly. **Raw text
  remains the single untested channel** where the LLM could still add value —
  and the standing AMNESIA warning says digested numbers are exactly where it
  loses. This is the top NIGHT-4 candidate.
- **`DIAG-NIGHT3-MEMORY-PLACEBO-1` DID complete** (§5b) — it was still running
  when §2 was first drafted, and that paragraph has been replaced by the result.
- **Arm C (structured event memory) not run**; arm D (semantic/ABN) was ingested
  but not run as a decision arm.
- **The stratified environment was built and deliberately not run** (§1).
- **Model-swap probe skipped** — no Anthropic key present, as the registration
  allowed.

## 9. Verdict

**`TRIAL-NIGHT3-DECISION-REPLAY-1`: M1 REJECT, M2 REJECT.**
**`DIAG-NIGHT3-MEMORY-PLACEBO-1`: memory content not demonstrated** — scrambled
memory is indistinguishable from real memory (t 0.43) and still beats no memory.

The LLM layer does not earn a role in stock selection on this evidence. Per the
registration, that routes LLM attention to **narration and event triage**, not
picking — and that is a receipt, not a failed night.

The deeper result is the one from §1: **the ordering problem the LLM was asked
to solve has no measurable signal in it for anyone.** Before asking whether a
reasoner is good at a task, measure whether the task is doable. We now do that
first.
