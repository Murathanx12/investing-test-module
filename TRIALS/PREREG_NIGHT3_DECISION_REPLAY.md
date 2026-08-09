# PRE-REGISTRATION — NIGHT-3: masked decision replay + the experience brain

**Registered:** 2026-08-09, by the commit that adds this file, **before** any
NIGHT-3 LLM call or grading run. Branch `factory/night-3`.
**Governing docs:** `aegis-finance/docs/EXECUTION_STANDARD_2026-08-08.md`
(§5.1-5.2 contamination protocol, both 2026-08-09 amendments),
`aegis-finance/docs/DESIGN_MEMORY_TAXONOMY_2026-08-09.md` (binding — the six
adopted deltas).
**Holdout:** 2023-01-01 .. 2024-12-31 unread. The loader refuses it.
**Instrument status:** the masking protocol is already MEASURED-VALID (AMNESIA:
0/240 identifications on masked, synthetic ≈ masked ΔBrier 0.0004,
instruction-based forgetting does nothing). Those arms are **not re-run**.

---

## 0. The one sentence this night is designed to answer

> **Does an LLM making portfolio decisions add anything over the numeric engine
> that already prints +4.67 %/yr — and does giving it memory of its own graded
> mistakes change that answer?**

Everything below exists to make that sentence falsifiable and cheap to falsify.

## 1. The decision environment (frozen)

At each formation month *t* in **2005-01-31 .. 2021-12-31** (204 months, all
before the holdout):

1. The engine screens the **small-cap** segment of the survivorship-free panel
   and emits a **slate of the top 40 names** by the PF-2 profitability composite
   (GP + OperProfRD + CBOperProf, the PROF-COMPOSITE-150 signal).
2. Each slate name is presented **masked**: sector, peer-count, and the same
   cross-sectional percentile facts the composite is built from. **No identity,
   no absolute date, no absolute prices, and — critically — no composite rank
   or score.**
3. The decider returns, for every one of the 40 names, `BUY | HOLD | SELL`, a
   conviction in [0, 1], and a one-enum reason.
4. A **book of 20 names, equal weight, held one month** is formed from the
   decisions (BUYs ranked by conviction; padded from HOLDs by conviction if
   fewer than 20 BUYs; truncated to the top 20 if more).

**Why this shape.** The engine's own ranking is a deterministic function of the
same percentile facts the LLM is shown. The two deciders therefore have an
**identical information set** and differ only in how they reason over it. The
comparison is paired on the same 40 names in the same month, so shared market
noise cancels and the difference series is what carries the signal.

## 2. Arms (frozen before compute)

| arm | decider | memory |
|---|---|---|
| **ENGINE** | composite rank, top 20 | — (control) |
| **A** | LLM | none |
| **E** | LLM | **episodic** — kNN over EXPERIENCEs resolved strictly before *t* |
| **EW40** | hold all 40 equally | — (control) |
| **RANDOM** | seeded random 20 of 40, 100 draws | — (placebo) |

Arm **D** (semantic / ABN posteriors) is built and run **only if arms A and E
complete with receipts**; a half-run D is worth less than a clean A/E. Arm
**C** is not run this night and is recorded as not-run rather than silently
dropped.

**Out-of-sample sequencing is absolute:** an EXPERIENCE is visible to arm E at
month *t* only if its outcome resolved **before** *t*. Arm E therefore starts
empty and warms up. Both the full window and a warm-only window (2010+) are
reported; the **full window is the deciding one**, the warm window is
disclosure.

## 3. Primary metrics (the deciding numbers, named now)

**M1 — DECISION vs ENGINE.** Net excess CAGR of arm A's book minus arm
ENGINE's book, over the full window, on the paired monthly difference series,
with a Newey-West t-stat. *This is the deciding number for "does the LLM add
anything".*

**M2 — MEMORY EFFECT.** Net excess CAGR of arm E minus arm A on the paired
monthly difference series, with a Newey-West t-stat. *This is the deciding
number for "does learning from its own mistakes help".*

Everything else — Brier, AUC, calibration, ECE, rank correlation, turnover,
per-regime blocks — is **reported, never deciding**.

## 4. Decision rule (frozen)

- **M1 ADOPT** (the LLM layer earns a role in selection) requires
  **≥ +1.5 %/yr with NW t ≥ 2.0** *and* the LLM book beating the RANDOM placebo
  band at p ≤ 0.05 *and* the anti-reward-hacking guard clean (below).
- **M1 REJECT** if the difference is ≤ 0 or |t| < 2.0. A rejection routes LLM
  attention to narration and event triage, not stock selection — that is a
  publishable receipt, not a failed night.
- **M2 ADOPT** (memory helps) requires **≥ +1.0 %/yr with NW t ≥ 2.0**.
- **UNRESOLVED** is a legitimate verdict and must name its reason class
  (insufficient months, call failures, cache corruption, data defect).

**Anti-reward-hacking guard (gating, per the taxonomy §6).** Every decision arm
reports **exposure** (fraction invested), **abstention rate**, and **opportunity
cost of abstention** (what the passed-on names did). An arm whose apparent edge
comes from sitting in cash is reported as exactly that and cannot ADOPT.

**Multiple-testing denominator:** every arm × window × metric computed this
night is counted and printed in the campaign summary. No metric substitution.

## 5. Registered predictions (mine, before any call)

| # | prediction |
|---|---|
| **N1** | **M1 FAILS** — the LLM book does not beat the engine book. *Rationale: on digested percentile facts the masked LLM already lost to a 5-feature logistic regression (AMNESIA P5 HIT). The engine's ranking is the optimal deterministic use of exactly these facts.* |
| **N2** | **M2 FAILS** — memory produces < +1.0 %/yr or t < 2.0. *Rationale: kNN over 4k experiences of a near-coin-flip monthly outcome is a weak instrument; I expect the effect to be real-but-small at best and indistinguishable at this n.* |
| **N3** | The coherence battery passes **≥ 4 of 5** perturbation directions at pass rate ≥ 0.70. |
| **N4** | **NAME-ONLY beats chance materially** (AUC ≥ 0.55). The contamination ceiling is real and quotable. |
| **N5** | LLM decisions are **strongly correlated with the engine ranking** (mean per-month Spearman ρ ≥ 0.30) — the model largely re-derives the signal rather than adding orthogonal information. |
| **N6** | The repeat probe shows **≥ 90 % identical decisions at temperature 0** and **≥ 15 % flipped decisions at temperature 0.7** — i.e. the noise Murat described is real and is controlled by the cache, not by asking for consistency. |
| **N7** | The LLM does **not** hide in cash: exposure ≥ 0.95 in both arms. |
| **N8** | On re-review, the model **UNDER-reacts more often than it OVER-reacts** to resolved evidence. |

Predictions are scored publicly whether they hit or miss, as in PF-1 (2/5) and
PF-2 (4½/8).

## 6. Consistency protocol (frozen)

- Temperature **0** for every graded call.
- Every response cached **immutably** keyed by `(model_id, prompt_sha256)`. A
  cached key is never re-rolled, never overwritten. Cache writes are
  write-once; a differing re-computation raises rather than replaces.
- **Decision persistence:** a name carried from month *t−1* into month *t* is
  re-reviewed under the forced schema **OLD BELIEF → NEW EVIDENCE → BELIEF
  UPDATE → NEW BELIEF → reason enum**, and update-appropriateness is graded
  deterministically for **both** overreaction and underreaction.
- The model is **never prompted to "be consistent."** Consistency is measured
  by showing it its own prior claim and grading the delta.
- **Repeat probe:** a seeded 10 % subsample is re-issued under a cache-bypass
  nonce at temperature 0 and at temperature 0.7 to quantify response noise.
  Probe calls are logged separately and **never** enter the graded books.

## 7. Model-agnosticism (frozen)

Every EXPERIENCE, claim, posterior and cache record carries `model_id`. The
experience store, kNN retrieval, resolver, graders and gates are pure engine
code containing no model-specific logic. An optional paired-subset model-swap
probe runs **only if** an Anthropic key is present, capped at **$15**, with the
spend log printed; absent a key it is skipped and recorded as skipped.

## 8. Hard limits (unchanged)

No lane seeded, no flag flipped, `paper_nav` untouched, no key changes, no
holdout read, research branch only. Spend guard: hard cap **$25** on DeepSeek
for the night, checked before every call, campaign halts on breach rather than
degrading silently. If a stage's assumptions break, it is recorded and skipped
forward — never replaced by a weaker test in silence.

## 9. What this trial may NOT do

- May not seed a paper lane, whatever it finds. Arms live in the historical lab.
- May not be cited as alpha evidence. Its output is **bounds and baselines on
  the LLM layer**; the forward claim ledger remains the gold standard.
- May not have its arms, windows, metrics or thresholds amended after compute
  begins. An amendment invalidates the trial; record abandoned, register a
  successor.
