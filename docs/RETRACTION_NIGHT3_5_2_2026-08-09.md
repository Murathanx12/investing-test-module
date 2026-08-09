# RETRACTION — NIGHT-3's "membership not ordering"

**Issued** 2026-08-09, in response to four external adversarial reviews.
**Supersedes** the claim wherever it appears: `NIGHT3_VERDICT_2026-08-09.md`,
`aegis-finance/docs/SESSION_2026-08-09_NIGHT3.md`,
`aegis-finance/docs/EXTERNAL_REVIEW_DOSSIER_2026-08-09.md` §5.2, and the
2026-08-09 memory entry.
**Receipt** `runs/PF4/RETRACTION_NIGHT3_5_2.json`, `runs/PF4/slate_rank_quartiles.csv`.

---

## What was claimed

> **The edge is MEMBERSHIP — which ~150 names out of ~2,000 — not ORDERING.**
> … Selection is answered.

and, acting on it, the stratified re-ranking follow-up was built and cancelled,
with "the power analysis is the receipt" given as the reason.

## What the evidence actually supports

Inside the engine's own 40-name slate, top-20 minus bottom-20 by the composite,
204 months, Newey-West(12):

| statistic | value |
|---|---|
| point estimate (annualized arithmetic mean) | **+1.68 %/yr** |
| geometric top-minus-bottom | +1.46 %/yr |
| t | **0.54** |
| standard error, annualized | 3.10 %/yr |
| **95 % CI** | **[−4.39 %, +7.75 %]/yr** |
| MDE at t = 2 | 6.19 %/yr |

> **Corrected claim:** within-slate ordering is **UNMEASURED** below roughly
> ±6 %/yr. The honest statement is "smaller than 6.2 %/yr", not "zero". The
> upper end of that interval contains an effect that would more than double the
> product.

Membership remains the larger and far better-measured effect. It is not the
only one, and it was never shown to be.

## The oracle bracket, which must now be printed beside the claim every time

| arm | excess CAGR vs benchmark |
|---|---|
| perfect-foresight top-20 of 40 (ORACLE) | **+205.2 %/yr** |
| equal-weight all 40 | +3.86 %/yr |
| anti-oracle bottom-20 of 40 | −73.1 %/yr |

Gross of costs and unattainable by construction — this is the *width of the
achievable band*, not a return. Its reading is the opposite of what the verdict
said: **ordering information exists in this environment in abundance.** What is
unmeasured is how much of it the composite captures.

## The alternative the test could not see

A top-minus-bottom spread is blind to a non-monotone structure. Splitting the
same slate into quartiles of engine rank, the same 204 months:

| quartile of composite rank | mean monthly | excess CAGR | t vs benchmark |
|---|---|---|---|
| q1 — ranks 1-10 (best) | 1.038 % | **−1.17 %** | 0.24 |
| q2 — ranks 11-20 | **1.715 %** | **+8.93 %** | **2.38** |
| q3 — ranks 21-30 | 1.433 % | +4.88 % | 1.82 |
| q4 — ranks 31-40 | 1.040 % | −0.48 % | 0.40 |

**The relationship is an inverted U, not a monotone decline.** The composite's
own top decile performs no better than its bottom decile; the second and third
quartiles carry the return. A top-20-minus-bottom-20 spread averages q1+q2
against q3+q4 and cancels almost exactly — which is why it printed a null while
ordering was in fact doing something.

**What this is not.** q2's t = 2.38 is the best of four comparisons; the
Bonferroni-adjusted bar is ≈ 2.50 and it does not clear it. This is a
**hypothesis generated on the same data**, not a finding. It must be
pre-registered and tested out of sample before it may size anything. It is
recorded here because it falsifies the *withdrawn* claim, which is a lower bar
than establishing a new one.

## Three further concessions, recorded

1. **The two derivations were not independent.** The within-slate spread and the
   10-to-150 concentration grid are both computed inside a set already selected
   on the composite. Range restriction attenuates any within-set relationship
   mechanically. They are one restriction sampled at two depths. The verdict
   called them independent corroboration; that was wrong.
2. **The concentration grid confounds three things.** Going 10 → 150 names
   changes composite depth, idiosyncratic diversification *and* the
   size/illiquidity mix at once. A genuine decline in signal quality offset by
   rising size and illiquidity premia produces exactly the flat raw curve we
   banked. The test that separates them is marginal-decile **alphas**, run in
   `TRIAL-PF4-DECOMPOSITION-1`.
3. **The six grid points are not six observations.** The 150-name book contains
   the 100-name book contains the 50-name book; their sampling errors are near
   0.9 correlated. Reading "flat" across nested portfolios by eye is not a test.

## The process miss

The rule broken is the house's own: `EXECUTION_STANDARD` §4.5 — *a null reads
"smaller than X", never "zero"*.

The aggravating detail is that the correct reading was already written down, by
the house, before the verdict. `runs/NIGHT3/POWER_CHECK.json` carries, in its
own `interpretation` field:

> "If that ordering value is near zero, a null M1 means the TEST cannot separate
> deciders, not that the LLM adds nothing — and the verdict must be UNRESOLVED,
> not REJECT."

That sentence was written, banked, and then not followed. The ledger and the
hash chain could not catch it, because it is not an integrity failure — it is an
inference failure, and the apparatus has no instrument for those. That is the
single most useful thing the external review surfaced.

## Consequences

* The withdrawn claim may not be quoted again in any document.
* Every future statement of the membership result must carry the interval and
  the oracle bracket.
* **The LLM re-ranking campaign is un-cancelled.** It was cancelled on a null
  that could not support the decision. It does not automatically resume — it
  goes back into the queue behind the redesigned campaigns, and if it runs it
  targets the non-monotone structure above, pre-registered, not a monotone
  re-rank.
* Scored against the house: **1 process miss**, recorded in the campaign
  scorecard alongside the two harness defects found in NIGHT-3 itself.
