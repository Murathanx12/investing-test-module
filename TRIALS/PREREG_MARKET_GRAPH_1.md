# PREREG — MARKET-GRAPH-1 (semantic edges vs numeric edges)

**Drafted 2026-08-12, before any edge is extracted.** From Murat's architecture
review of 2026-08-12, which proposes that "the price of one stock and its
movements reflect other stocks", and that an LLM may know **why** two companies
are related before enough price history exists for correlation to discover
**that** they are.

## Hypothesis

> **H1 (transmission).** Economic relationships extracted by an LLM from text
> carry information about future cross-sectional co-movement that is **not**
> already in the trailing correlation matrix.
>
> **H2 (the interesting cell).** Pairs the LLM marks economically related but
> which are **not** yet statistically related — `semantic YES / numeric NO` —
> subsequently develop measurable co-movement more often than matched pairs
> drawn from `semantic NO / numeric NO`.

Honest prior, stated before running: **H1 ~50/50; H2 ~25/75 against.** H2 is the
seductive cell and the one most likely to be an artifact, for a reason stated in
advance: an LLM will happily assert a relationship between any two companies if
asked, and "not yet correlated" is exactly what a hallucinated edge looks like.
The 25% is not pessimism about the idea; it is the base rate for ideas that are
this attractive to believe.

## Design

**Edges are emitted BEFORE the evaluation window opens.** The LLM sees text up
to date *t* and emits a typed edge set. Numeric edges are computed from returns
up to *t*. Grading uses `(t, t+h]` only. No edge may be added, reweighted or
dropped after the window opens.

Edge types (fixed now): supplier, customer, competitor, commodity input, shared
technology, shared end-market, regulatory exposure, geographic exposure.
Each carries a direction and a `confidence` in [0,1].

**The 2x2, on out-of-sample co-movement:**

| | numeric YES | numeric NO |
|---|---|---|
| **semantic YES** | agreement — the easy cell, and mostly redundant | **H2: the claim** |
| **semantic NO** | hidden factor / flow — reported, not claimed | control |

## Primary metric

**Incremental out-of-sample explanatory power for pairwise co-movement in
`(t, t+h]`, from adding semantic edges to a model that already contains the
trailing correlation matrix.** One number: the improvement, with its own
Newey-West SE and its own 80%-power MDE (§19). Overlapping pair-windows are
dependent and the SE must say so.

For H2 specifically: the **difference** between `semantic YES / numeric NO`
pairs and matched `semantic NO / numeric NO` pairs, tested as a difference with
its own SE (§18) — never as two separate significance claims.

Reported, never deciding: edge counts by type, LLM confidence calibration,
sector composition, and how much of any effect is same-sector (a semantic edge
that only rediscovers GICS is a slow expensive sector dummy, and that must be
visible rather than argued about).

## Mandatory controls

1. **Shuffled-semantic placebo** — the identical edge set, permuted across
   pairs, preserving degree distribution and confidence distribution. This is
   the key arm: it separates *the relationships* from *adding another dense
   graph changed the model*.
2. **Same-sector-only control** — does the effect survive excluding same-sector
   pairs?
3. **Random-edge control** at matched density.
4. **Trailing-correlation-only baseline** — the thing to beat.
5. **Reversed-direction control** for directed edges: if supplier->customer
   transmission is real, customer->supplier at the same lag should be weaker.
   If both look equally good, the model found co-movement, not causation.

## Decision rule

- Adopt into research use only if the incremental number **exceeds its own MDE**
  AND survives the shuffled-semantic placebo AND survives the same-sector
  exclusion.
- H2 requires, in addition, that the reversed-direction control behaves as
  predicted. Without it, `semantic YES / numeric NO` is indistinguishable from
  "the LLM emitted a plausible sentence."
- Below MDE = **not detectable**, recorded as such, never a kill (§19).
- Nothing here reaches a portfolio surface in this trial. Descriptive only.

## Frozen parameters

Universe, `t` cut dates, horizons, edge taxonomy above, confidence field,
co-movement definition (residual return correlation after market and sector),
and the matching procedure for H2's control pairs.

## Hard constraints

- The extractor is given text **only up to `t`**. Any live web retrieval on a
  historical date is leakage by construction and is forbidden in this trial.
- `served_model` stored on every call.
- Edge extraction emits **no return forecast**. If the same call both names a
  relationship and predicts a move, the two cannot be graded apart.

## Corpse check

Run before registration; verdict recorded in the trial doc.
