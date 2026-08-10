# PREREG — TRIAL-N1B-WHERE-DOES-THE-IC-LIVE-1 (REGISTERED, NOT RUN)

**Registered:** 2026-08-10 · **Family:** N (extension) · **Stage:** diagnostic
**Parent:** `TRIAL-N1-RANKER-VS-COMPOSITE-1` (IMPLEMENTATION_FAILED ×3; receipt
`runs/NIGHT8/N1_RANKER_VS_COMPOSITE.json`)

Resurrects: PREREG_N1_RANKER_VS_COMPOSITE — new instrument: decile-level IC
decomposition rather than a single full-cross-section statistic, which is the
only way to see whether an ordering advantage sits where a long-only book can
reach it.

## 1. What the parent established, and what it left open

Three learned rankers ordered the cross-section better than the hand-written
composite — ΔIC **+0.034 / +0.068 / +0.056** at paired t **4.18 / 4.09 / 3.46**
over 461 months — and none of them earned more. All three are
`IMPLEMENTATION_FAILED`.

**Turnover is ruled out as the explanation by measurement.** The best-ordering arm
(R2) had the *lowest* turnover in the table, 0.401 against the control's 0.460.

So the ordering advantage is real, it is large, it is not eaten by trading, and it
does not arrive in the book. **Where does it go?**

## 2. Hypothesis

**H1 (the §28 hypothesis).** Rank-IC is a full-cross-section statistic. The book
buys only the **top 150 names of the small segment**. This programme has already
measured, in §28, that 99.9%/88% of a long-short spread can live in the leg a
long-only book cannot hold. If the learned rankers' advantage is concentrated in
correctly identifying the *bottom* of the distribution — which is what a
tree ensemble trained on a symmetric loss should be good at — then a long-only
top-150 book is structurally unable to collect it.

**H2 (the compression hypothesis).** The advantage may be real at the top but
*compressed*: the learned rankers may order the top decile no better than the
composite does, spending their extra skill on distinctions among names nobody
holds.

**H0.** The advantage is present at the top and something else — liquidity,
size, or the eligibility mask — prevents its collection.

## 3. Design

Everything is a decomposition of series the parent already produced. No new
models are fitted and no new arms are created, so the ranker search is not
extended.

1. **IC by decile.** Recompute the monthly rank-IC restricted to each decile of
   each arm's own score. If the learned arms' advantage lives in deciles 8–10
   (the worst names), H1 is supported directly.
2. **Top-only IC.** Rank-IC computed among the top 150 names *each arm would
   actually hold*. This is the number that matters for a long-only book, and it
   is the one nobody has ever computed here.
3. **Hit rate on the left tail.** The share of each arm's bottom decile that goes
   on to a performance delisting or a bottom-quintile forward return. Bessembinder
   (`BESSEMBINDER-4PCT`) says the left tail is where a long-only book's realised
   return is decided; N2 separately found the composite already avoids the
   accruals/issuance/distress families at up to 15× better than chance.
4. **Overlap.** How many of the top 150 do the learned arms and the composite
   share? If overlap is high, the money difference is coming from a handful of
   names and is a small-sample story rather than a ranking story.

## 4. Decision rule (frozen)

| outcome | consequence |
|---|---|
| the ΔIC is concentrated in the bottom deciles **and** top-only IC is flat | **H1 supported.** The learned ranker's advantage is structurally uncollectable by this book. Record it and stop building long-only rankers on a symmetric loss. |
| top-only IC is materially better (paired t ≥ 2.0) while money is not | H0. Something between ordering and holding is losing it; register a construction trial, not a ranker trial. |
| top-only IC is flat and the bottom deciles are flat too | the parent's ΔIC is a middle-of-the-distribution artifact; report and close. |

**This diagnostic adopts nothing and may not adopt anything.** Its only outputs
are a supported hypothesis and, at most, a registered successor.

## 5. Registered predictions

1. **H1 is supported** — the advantage concentrates in the bottom deciles.
2. **Top-only IC is flat**, |t| < 2.0, between the learned arms and the composite.
3. **Overlap in the top 150 is above 50%**, so the two books are more alike where
   it counts than the full-cross-section ΔIC of 0.068 suggests.
4. If 1–3 hold, the honest consequence is that **a symmetric regression loss is
   the wrong objective for a long-only book** — which would be the first
   actionable design conclusion the ML track here has produced, and would be a
   registered successor rather than an adoption.

## 6. Ledger

Adds **0 branches** — this decomposes series the parent already produced and
fits no new model. Any successor it motivates registers its own.
