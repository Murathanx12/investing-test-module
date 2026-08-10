# PREREG — TRIAL-PF5-RANK-SHAPE-1

**Registered** 2026-08-09, **before any compute in this campaign**.
**Branch** `factory/night-5`. **Family** PF.

## 0. Disclosure of prior knowledge — read this first

This campaign is **not** starting from ignorance, and pretending otherwise would
make every number in it meaningless.

What we already saw, in NIGHT-4's retraction diagnostic
(`runs/PF4/RETRACTION_NIGHT3_5_2.json`): inside the engine's top-40 slate,
**ranks 11–20 returned +8.93 %/yr at t 2.38 while ranks 1–10 returned −1.17 %/yr**.
That was the best of four quartile contrasts, it failed Bonferroni within its own
tiny family, and it was recorded as a *hypothesis*, not a finding.

We also saw, in the boundary diagnostic (`runs/PF4/DIAG_BOUNDARY.json`), that
across ten-name windows *inside* ranks 1–150 flatness is **not rejected**
(Cochran Q 12.38, df 14, p 0.58), while ranks 1–150 average +3.84 %/yr against
−0.85 %/yr for ranks 151–300.

Those two observations point in opposite directions. The first says there is
shape inside the top of the book; the second says there is not. **This campaign
is scored against the shape hypotheses registered below, not against the memory
of ranks 11–20 winning.** Any post-hoc window that happens to win is reported as
a window, never as the result.

## 1. Question

Within the eligible top-150 of the profitability composite, does the *marginal*
contribution to alpha depend on rank — and if so, in what shape?

This matters for exactly one reason: **if the alpha surface inside the book is
flat, no selector — LLM or otherwise — can add value by re-ordering names inside
it, and the un-cancelled re-ranking campaign should not be built.** If it is
non-flat and the shape is stable, re-ranking has somewhere to work.

## 2. The shape family (registered now, four members)

For bucket index i = 1…B (bucket 1 = best-ranked), let a(i) be the annualized
FF5+UMD alpha of an equal-weight book holding only that bucket, rebalanced on
the same clock as the parent book, era-appropriate costs.

* **S1 MONOTONE-DECREASING** — a(i) declines with i. The textbook prior: the
  signal is informative and more signal is better.
* **S2 INVERTED-U** — a(i) peaks at an interior bucket. The NIGHT-4 hypothesis:
  the very top of the composite is contaminated (extreme profitability scores
  select for accounting artefacts, one-off items, or names about to mean-revert)
  so the best names sit just below the top.
* **S3 PLATEAU-THEN-DECAY** — a(i) is flat up to a breakpoint b, then declines.
  The membership reading: being *in* the book is what matters and rank inside it
  does not, up to the point where the signal runs out.
* **S4 FLAT / NOISE** — a(i) has no rank structure. The null.

## 3. Statistics (all registered, each mapped to a member)

Primary estimation window: **1963-07 → 2022-12** (482 tradable months), the same
window as every PF-4 number.

* **H-test (S4 vs the rest).** Cochran's Q inverse-variance homogeneity across
  the B bucket alphas. p ≥ 0.05 ⇒ **S4 is not rejected** and the campaign's
  answer is "no measurable shape at this power", with the MDE printed.
* **Trend (S1).** Spearman ρ between bucket index and a(i), and the slope of a
  weighted linear fit, with the NW(12) t on the slope.
* **Curvature (S2).** Weighted quadratic fit a(i) = α + βi + γi²; S2 requires
  **γ < 0 with |t_γ| over the family-Bonferroni bar AND the fitted vertex
  strictly interior** (not in the first or last bucket). A negative γ whose
  vertex falls outside the grid is a monotone shape, not an inverted U.
* **Breakpoint (S3).** Segmented fit over every admissible breakpoint b; S3 wins
  only if it beats S1, S2 and S4 on **AIC** and the pre-breakpoint slope is not
  significant.
* **Selection.** Model chosen by AIC across S1–S4. The reported verdict names
  the winner **and** the AIC gap to the runner-up; a gap below 2 reads
  **UNRESOLVED between those two shapes**, which is a legitimate outcome.

**Bonferroni within the family: 4 shape tests ⇒ two-sided bar t ≈ 2.50.** This
is *within-family*; the programme-wide denominator from
`aegis_brain/pf/ledger.py` is attached to the artifact separately and is the bar
any *claim* must clear.

## 4. Bucket resolution

* **Primary: 10-name buckets, B = 15**, covering ranks 1–150. Chosen for power:
  NIGHT-4's boundary work used ten-name windows and their alpha SEs were already
  wide.
* **Secondary, registered: 5-name buckets, B = 30.** Higher resolution, roughly
  √2 worse SE per bucket. Reported for shape *visualisation* and for the
  vertex location if S2 wins. **It cannot overturn the primary.** Recorded now
  so that "the 5-name curve showed it" cannot be produced later as the result.

## 5. Registered arms (reported, never the headline)

* **A1 — ranks 11–20 vs ranks 1–10 in the top-40 slate.** The NIGHT-4
  observation, re-run as one pre-declared contrast among many. Its p-value is
  reported with the explicit note that it is **not independent** of the
  observation that motivated it and therefore cannot confirm itself.
* **A2 — era-split stability.** The same curve fit separately pre-2001 and
  post-2001. **A shape that does not survive the split is noise, whatever its
  full-sample AIC.** This is the single most informative arm here and it is the
  one most likely to kill S2.
* **A3 — cross-signal replication.** The same bucket curve on the *individual*
  profitability signals that make up the composite, run independently. A shape
  that appears in the composite but in none of its constituents is a
  construction artefact of the compositing, not a property of profitability.
* **A4 — turnover and cost by bucket.** Deep buckets are smaller and less liquid;
  if a(i) declines with i partly because costs rise with i, that is an
  implementation fact and not a signal fact, and it must be visible.

## 6. Decision rule (frozen)

* **SHAPE ESTABLISHED** — requires (i) Cochran Q rejects flatness at p < 0.05,
  (ii) one shape wins AIC by ≥ 2, (iii) **the same shape wins in both era
  halves**, and (iv) the shape appears in at least one constituent signal (A3).
  Only then does the re-ranking campaign get built, and it gets built against
  *that* shape.
* **NO MEASURABLE SHAPE** — Q not rejected. Report the MDE per bucket in %/yr,
  state plainly that ordering inside the book is unmeasured at this power, and
  **do not** build the re-ranking campaign on this data. NIGHT-4's retraction
  already established that "unmeasured" must not be written as "zero".
* **UNRESOLVED** — anything else, including a shape that wins full-sample AIC
  but flips across the era split.

## 7. House prediction, registered before compute

* **Q1** — Cochran Q **fails to reject** flatness on the primary 10-name grid.
  Confidence 0.6. (The boundary diagnostic already said p 0.58 on 14 df over the
  same ranks; this is close to a re-run and I expect it to agree with itself.)
* **Q2** — if a shape wins AIC, it is **S3 plateau-then-decay**, not S2.
  Confidence 0.45.
* **Q3** — the ranks 11–20 effect (A1) **does not replicate** in the era split:
  it lives in one half. Confidence 0.65.
* **Q4** — bucket-level MDEs are **larger than 4 %/yr**, i.e. the honest answer
  is "we cannot see ordering effects smaller than a very large number".
  Confidence 0.7.
* **Q5** — A4 shows monotonically rising cost drag with bucket index, so any
  raw-return decline overstates the signal decline. Confidence 0.6.

## 8. What this trial may NOT do

* It may not select a rank window on its own output and then quote that window's
  return as an achievable strategy.
* It may not treat the 5-name grid as primary.
* It may not read a full-sample shape that fails A2 as a finding.
* Every bucket book fitted here is a test and enters the denominator.
