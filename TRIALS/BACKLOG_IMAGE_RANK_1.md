# BACKLOG — TRIAL-IMAGE-RANK-1 (REGISTERED, NOT RUN, NOT SCHEDULED)

**Registered:** 2026-08-10 · **Family:** N (extension) · **Stage:** backlog only
**Status:** **NO COMPUTE.** This exists so that a future night finds a
power check and a prior already written, instead of re-deriving enthusiasm.

## 1. The idea

Jiang, Kelly & Xiu (2023) render price history as an **image** — an OHLC bar
chart with a moving-average overlay — and train a CNN on it. The claim is that a
CNN discovers predictive chart structure that hand-specified momentum and
reversal variables miss, and that the learned patterns transfer across markets
and horizons.

The Aegis version would use the CNN's output as **one input to a ranker**, never
as a standalone book.

## 2. Why it is a backlog item and not a queue item

**The prior is skeptical, and specifically so.**

1. **The programme has already measured its price-factor shelf.**
   `TRIAL-BRAIN-002` rejected the GKX price big-three at net t −2.80 on this
   exact CRSP spine and demoted price characteristics to combiner-input-only
   status. A CNN on price images is a *richer encoding of the same information
   source*. It is not a new information source, and this factory's own record
   says the source is thin after costs.
2. **N1 is the cheaper version of the same question** and runs first. If a GBM
   over ten hand-built characteristics cannot beat three hand-written weights,
   a CNN over pixels of the same price history is not the next thing to try.
3. **Turnover.** Every image-based signal in the literature is refit and traded
   at monthly or higher frequency. NIGHT-6 and NIGHT-7 measured the monthly
   panel understating churn cost by ~2.4 pts/yr, and CANON §15 routes any such
   candidate through G7 before a net number may be quoted.

## 3. The power check, written now so it cannot be skipped later

The binding constraint is **not** GPU time. It is the same paired-MDE wall that
N1 registered: two long-only books drawn from the same 150-name pool correlate
0.85–0.95, so the minimum detectable paired difference is **2–4%/yr** on ~480
months.

**A CNN arm must therefore clear +3%/yr paired against the composite to be
readable at all.** No published image-based result of this kind, applied to a
long-only small-cap book net of era-appropriate costs, has claimed anything like
that. The honest expectation is that this trial would return `UNRESOLVED` with an
MDE near 3%/yr — which is the same non-answer 72% of the closed 179-signal search
already produced.

**Consequence, pre-committed:** this trial does not run until one of the
following is true.

- The **ordering** instrument is used as primary (monthly rank-IC, ~700
  observations) and the trial is registered as a *representation* question, not a
  money question; **or**
- a source of power appears that the current design lacks — a long-short
  formulation the book could actually hold, a much wider cross-section, or a
  materially higher-frequency panel; **or**
- N1's wide-shelf arms show that added representation capacity *does* improve
  ordering (prediction 2 of N1), which would be the first local evidence that
  richer encodings of price history buy anything here.

That last one is the honest trigger: **N1 is the cheap experiment whose result
decides whether this expensive one is worth running.**

## 4. If it ever runs

- Images built **point-in-time**, from the same CRSP daily spine G7 uses, with no
  forward window in the rendering.
- Purge and embargo identical to N1: the label window plus one month.
- Compared **paired against the composite** on the same pool and clock, with the
  ordering instrument reported beside the money instrument.
- Registered as a resurrection of `TRIAL-BRAIN-002` with the new instrument
  named, per the corpse-check rule.

## 5. Ledger

Adds **0 branches** — nothing is computed. If it is ever run it registers its
own.
