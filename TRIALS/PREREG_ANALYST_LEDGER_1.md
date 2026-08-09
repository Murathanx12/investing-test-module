# PREREG — ANALYST-LEDGER-1 (forward, explain-then-predict)

**Registered** 2026-08-09, NIGHT-5. **Forward-only.** Inception is the first
note written after this document is committed; no retrospective note may enter.
**Nothing in this trial touches a lane, a weight, or a position.**

## 1. What this is for

Murat's ask, verbatim: *"compare estimation vs the real findings … how can we
not repeat the same mistake, how can we repeat the same win."* Every LLM result
this programme has is **retrospective replay**, and NIGHT-3 established the
ceiling of what replay can settle: M1 and M2 both REJECT, at MDEs of 3.6–5.9 %/yr.
Replay cannot answer the question Murat is actually asking, for a reason that is
structural rather than fixable — the model has read the future of every month it
is replaying, and the masking work (NIGHT-1, 1,080 calls) showed instruction-based
forgetting does nothing.

The only instrument that can answer it is a **forward** ledger where the
estimate is written down before the outcome exists. This is that ledger.

## 2. The loop (frozen)

1. **The engine decomposes first.** For each name the engine emits its own
   decomposition — factor loadings, the profitability composite's inputs, the
   liquidity picture, what is already priced. The LLM never sees a blank page,
   because a blank page is where narrative goes.
2. **The LLM reads, under the source policy** (`aegis_brain/analyst/source_policy.py`,
   14 unit tests). Allowed: SEC and regulator filings, company releases and IR,
   transcripts, exchange notices, major wires. Blogs, forums and aggregators are
   **context only** and may never support an estimate. Unknown hosts are treated
   as context, never optimistically allowed.
3. **Every fact carries a source.** A claim with no allowed source is marked
   `unsourced` and the note's estimate is **flagged** — not discarded. Discarding
   flagged estimates would destroy the only evidence that could ever settle
   whether the flag predicts anything.
4. **The estimate is in BASIS POINTS**, not adjectives. NIGHT-3 measured this:
   the model's coherence was 3/5 in prose and **5/5 when the same question was
   asked in basis points**. The format is part of the instrument.
5. **The engine scores.** Resolution is deterministic, from realized data, by
   the existing `abn` resolver. **The LLM never grades itself** — standing rule.
6. **A postmortem card per resolved claim**: what was estimated, what happened,
   which sources were used, whether the note was flagged, and the engine's own
   estimate for the same name over the same window.

## 3. Primary metric and the standing bar

**Primary: the paired difference between the LLM-adjusted estimate and the
engine-only estimate, in bps, over the same names and the same windows,** with
a Newey-West t. The pairing is the whole design: an unpaired LLM number carries
the same strategy premium every arm carries, which is the metric substitution
NIGHT-3 caught itself making.

**The bar:** the ledger clears only when the paired difference is positive at
**t ≥ 2.0 after the programme-wide deflation** in `aegis_brain/pf/ledger.py`,
over **at least 24 months** of forward notes. No skill claim before 24 months
regardless of any interim number — the standing rule, unchanged.

**Reported, never deciding:** hit rate, Brier score against climatology,
calibration curve, abstention rate, source-tier mix, and the flagged-vs-clean
split. Any of these may kill enthusiasm; none of them may promote.

## 4. Registered secondary questions (they are the point of the design)

* **S1 — does the flag predict?** Are flagged estimates measurably worse than
  clean ones? If they are not, the source policy is costing effort for nothing
  and should be simplified. Registered so the policy itself is falsifiable.
* **S2 — does the model add anything the engine does not already have?** The
  decomposition is shown first precisely so that "the LLM agreed with the
  engine" is measurable and cheap to detect. NIGHT-3 found LLM ordering was
  **orthogonal** to the engine (Spearman 0.014) and that orthogonality bought
  **no** diversification (best blend IR 0.516 vs arm E's own 0.527). Forward
  data is the only place that can change.
* **S3 — repeat the win, avoid the mistake.** Every resolved claim is filed with
  its situation fingerprint under ticker-blind retrieval and an outcome embargo.
  The question is whether the postmortem cards, fed back as context, improve
  later estimates. **Standing caveat, from our own data:** the NIGHT-4
  re-measurement found the memory effect is **+2.56 %/yr at t 1.52** — twice what
  we published but still not demonstrated — and that a situations-only arm
  (neighbours shown, outcomes withheld) scored *below* no-memory at all. Memory
  is REOPENED, not established, and this ledger must not assume it.

## 5. Hard constraints

* **Zero influence on lanes, weights or positions until the bar clears.** The
  ledger is an instrument, not an allocator.
* **The LLM narrates; the engine computes.** Unchanged.
* **No posterior touches position sizes.** Unchanged.
* **Spend cap $10/month**, hard. The ledger stops rather than overspends.
* **Keys env-only.**
* **Immutable response cache** keyed by `(model_id, sha256(system+user))`, as in
  NIGHT-3, so every number is reproducible and re-runs cost nothing.
* Notes are written **before** the resolution window opens; a note whose window
  has already closed is void, not late.

## 6. House prediction, registered before any forward note exists

* **A1** — the paired difference does **not** clear the bar in the first
  24 months. Confidence 0.7. Recorded because the honest prior after NIGHT-1
  through NIGHT-4 is that this programme has never found the LLM adding money,
  and a forward ledger is more likely to confirm that cheaply than to overturn
  it.
* **A2** — flagged estimates are **not** measurably worse than clean ones, at
  this sample size, because the sample will be far too small to see it.
  Confidence 0.6. If A2 lands, the correct reading is "unmeasured", and the
  policy stays on the grounds it was adopted on — hygiene, not measured effect.
* **A3** — the model's estimates will correlate more with recent price action
  than with the filings it cites. Confidence 0.55. This is the specific failure
  mode worth catching, and it is why the source tier mix is recorded per note.

## 7. What this trial may NOT do

* It may not be quoted before 24 months, whatever an interim number says.
* It may not substitute an unpaired standalone return for the paired metric.
* It may not silently drop flagged notes from the analysis.
* It may not re-enter retrospective notes if the forward sample is thin.
* Its notes count in the programme-wide testing denominator.
