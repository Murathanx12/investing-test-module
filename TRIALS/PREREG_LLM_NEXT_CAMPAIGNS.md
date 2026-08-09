# PRE-REGISTRATION — the two LLM campaigns that replace decision replay

**Registered** 2026-08-09, before any compute on either. Both supersede "more
masked decision replay over digested numbers", which NIGHT-3 answered and which
the retraction of §5.2 does **not** reopen: the re-ranking campaign is
un-cancelled but goes to the back of the queue, behind these two.

**Why these two and not another replay.** NIGHT-3's binding constraint was
never the design, it was POWER. Grading a decider against next-month return, on
a 40-name slate, over 204 months, gives minimum detectable effects of
3.6–5.9 %/yr. Nothing that fits in one night can beat that ceiling by running
the same experiment more carefully. Both campaigns below escape the ceiling
instead of arguing with it — the first by changing the target to something with
a far lower noise floor, the second by changing the input to the one channel
never tested.

---

# TRIAL-LLM-PERSIST-1 — grade the model against a low-noise intermediate

## Hypothesis

> **H:** The LLM has skill at predicting whether a firm's profitability figure
> is *durable*, which is a question about accounting quality rather than about
> the market, and which can be graded without going anywhere near return noise.

Stated prior: **moderately optimistic on stage 1, pessimistic on stage 2.**
Durability of an accounting figure is exactly the kind of judgement a language
model should have some purchase on, and it is exactly the kind of judgement that
may still be worthless for returns once the market has priced it. Those are
different claims and this trial refuses to merge them.

## Target

For each name on a masked slate at formation month *m*:

    P(the firm is still in the top 30% of its eligible universe by the
      profitability composite at m+12)

Objective, computed from the same panel, no return involved, base rate printed
before any grading.

## Two strictly separated stages

**Stage 1 — is there any skill at all?**
Primary metric: **AUC** of the predicted probability against the realized
binary, out of sample, on masked slates.
Controls, all three required:
* random probabilities with the same marginal distribution;
* the naive baseline — the firm's own current composite rank;
* the persistence baseline — the firm's own realized persistence over the prior
  12 months.
**Adopt threshold:** AUC ≥ 0.58 **and** a 95 % CI excluding 0.55 **and** a
positive paired difference against *both* named baselines. Anything else is
UNRESOLVED, with the MDE printed.

**Stage 2 — does the skill convert into money?**
Runs **only** if stage 1 clears, and is fully deterministic once it does:
weight or filter membership by the predicted persistence and measure book excess
against the unweighted book, paired, same names, same months.
**Adopt threshold:** ≥ +1.0 %/yr paired excess at NW t ≥ 2.0.

A stage-1 pass with a stage-2 fail is a **publishable negative** and must be
reported as one, not buried: "the model can read accounting durability and the
market has already priced it" is a clean result.

## Frozen

Slate construction, masking and canaries as NIGHT-3. Temperature 0. Immutable
cache keyed by `(model_id, prompt hash)`. Elicitation in **integer basis points
or integer percent**, never decimals — the resolution finding from
`DESIGN_MEMORY_TAXONOMY §9` is binding forward. ~2,000 calls, $25 cap,
holdout untouched.

## Registered predictions

| # | prediction |
|---|---|
| P-1 | stage 1 clears: AUC lands in 0.58–0.66 |
| P-2 | the model beats the random control comfortably and beats the OWN-RANK baseline only narrowly or not at all — most of any apparent skill is rank-reading |
| P-3 | stage 2 fails: paired excess below +1.0 %/yr |
| P-4 | the model's stated confidence is again compressed — fewer than 10 distinct probability values across the whole campaign unless asked in basis points |

---

# TRIAL-LLM-VETO-1 — signal invalidity from raw text, as a veto not a ranker

## Hypothesis

> **H:** Given the raw 10-K, the LLM can identify names whose reported
> profitability is *unrepresentative of forward economics* — one-off gains,
> asset sales, going-concern doubt, a pending merger, a recent IPO, an
> accounting change — and excluding those names improves the book.

This is deliberately **not** a ranking task. NIGHT-3 established that the model's
ordering is orthogonal to the engine's (Spearman 0.014) and no better. A veto
asks the one question a numerical screen structurally cannot answer, and it is
the only remaining use for which there is a mechanism rather than a hope.

## BLOCKING DEPENDENCY, stated rather than discovered later

There is **no SEC EDGAR full-text spine in this repo**. This campaign cannot run
until one exists, PIT-stamped on filing date. Building it is a prerequisite
task, not part of this trial, and this registration is void if the spine is
built with any non-PIT shortcut.

## Design

Per name on the slate, one binary call over the filing's Item 1A + Item 7 with a
closed enum of reasons. Then, **within the same slate**:

    paired excess = mean forward excess of RETAINED names
                  − mean forward excess of VETOED names

**Control (required, registered now):** a random veto of identical count *and*
identical size/liquidity/momentum composition — the same characteristic-matching
discipline PF-4 introduced for the portfolio placebo, because a veto that
happens to remove small illiquid names would look like skill for reasons that
have nothing to do with text.

**Adopt threshold:** retained-minus-vetoed ≥ +1.5 %/yr at NW t ≥ 2.0 **and**
beating the characteristic-matched random veto at empirical p ≤ 0.05.

## Registered predictions

| # | prediction |
|---|---|
| P-5 | the model vetoes 8–20 % of names |
| P-6 | vetoed names underperform retained names, but by less than +1.5 %/yr — directionally right, economically short |
| P-7 | the characteristic-matched random veto captures **more than half** of whatever raw effect appears, because vetoable conditions cluster in small distressed names |
| P-8 | going-concern and pending-merger fire far more often than accounting-change, and the enum is dominated by two of the six categories |

## Common constraints for both trials

* Pre-registered before compute; this file is committed before either runs.
* The LLM never grades itself; grading is mechanical from the panel.
* No posterior touches position sizes. No lane, no flag, no `paper_nav`.
* Denominators printed; predictions scored including misses; MDE printed beside
  every null.
* Both campaigns count toward the programme-wide multiple-testing denominator
  maintained by `aegis_brain/pf/ledger.py`.
