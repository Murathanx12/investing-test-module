# PREREG — ANALYST-IDENT-1: is the small-cap sign disagreement coverage churn?

**Registered** 2026-08-11, NIGHT-10, before any statistic in §5 was computed.
**Family** analyst. **Data** `ibes.ptgsumu` (unadjusted), already on disk from
ANALYST-IBES-1. **Parent** ANALYST-IBES-1 (verdict
`docs/ANALYST_IBES_1_VERDICT_2026-08-11.md`).

**This trial does not search for a winner.** It is a diagnostic of an existing
UNRESOLVED verdict, and it accrues **zero** arms to the search denominator. If
it identifies the object, the delivery sweep that follows is a separate
pre-registration that *does* accrue. Saying so in advance is the point: a
diagnostic that quietly becomes a strategy search is how denominators get lost.

---

## 1. Why this is not re-litigation

ANALYST-IBES-1 returned **UNRESOLVED** in the small segment under its own
registered rule: two constructions of one idea disagreed in sign on the same
names in the same months.

| arm | construction | small, 1m, gross |
|---|---|---:|
| A2 `tgt_rev_breadth` | `(numup1m − numdown1m) / numest` | **+6.05 %/yr** |
| A3 `tgt_rev_3m` | Δ of the consensus target level over 3m | **−0.73 %/yr** |

The registered consequence was: *"They are two constructions of one idea. If
they disagree, the idea is not identified and no verdict may be issued for
either."* That is still binding. Nothing here lifts it, and no verdict on
either arm is issued by this trial.

What is being tested is the **successor hypothesis the parent verdict wrote
down in advance**, which has never been run:

> *"The most likely explanation is that `numup1m`/`numdown1m` count analyst
> ACTIONS while Δ-consensus mixes actions with COVERAGE CHURN — a new analyst
> initiating at a high target moves the mean without anyone revising anything.
> That is a testable successor, not a result."*

So the object under test is not "do analyst revisions predict returns". It is
**"are these two things measuring the same object at all"**. A measurement
question with a mechanical answer, asked before any further money question.

## 2. The mechanism, stated so it can be wrong

`meanptg_t` is the mean target across the `numest_t` analysts covering the name
in month *t*. Its change decomposes exactly into

    Δmeanptg  =  (revisions by continuing analysts)  +  (churn: entries/exits)

A single initiation at a target above the current mean raises `meanptg` with
**zero** analyst having revised anything. `numup1m`/`numdown1m` count revision
ACTIONS and are blind to that entry by construction.

The contamination scales with **1/numest**: one entrant among 3 analysts moves
the mean far more than one among 25. Small caps have thin coverage. So if churn
is the contaminant, the disagreement should be **concentrated exactly where
coverage is thin**, and should shrink or vanish when churn months are removed.

That gives the trial a second, independent prediction (§4.2) that is not
implied by the first — the design is not just "purge and hope".

## 3. Power check — run BEFORE the arms (a test that cannot see its own prior does not run)

Gate: the churn-free small-cap subsample must retain enough name-months to
detect a spread of the size in dispute. The disputed quantity is the gap
between +6.05 and −0.73 %/yr, i.e. ~6.8 points.

* **MDE target**: ≤ 4.0 %/yr annualised decile spread at 80% power, α = 0.05,
  two-sided, computed from the realised monthly dispersion of the churn-free
  subsample.
* **Retention floor**: the churn-free subsample must hold ≥ 30% of small-cap
  name-months AND ≥ 60 months with ≥ 20 names each.

**If either gate fails, the trial reports POWER_FAILED and stops.** No arm is
run, no number is quoted, and the small segment stays UNRESOLVED. A null from
an underpowered purge would be indistinguishable from "churn is not the
explanation", which is precisely the confusion this trial exists to remove.

## 4. Pre-registered predictions

Segments: small and largemid, as defined in ANALYST-IBES-1 (unchanged, so the
parent's numbers are the control). Clock: 1m and 3m, as the parent.

### 4.1 Primary — the purge

Recompute A3 (Δ-consensus) on **churn-free name-months only**
(`numest_t == numest_{t−1}`, both present).

* **P1** — churn-free A3 in small turns **positive gross** and agrees in sign
  with A2. Predicted direction: positive.
* **P2** — the **churn-only** subsample (`numest_t ≠ numest_{t−1}`) carries A3
  **negative** in small, i.e. the contamination is where the sign came from.

### 4.2 Secondary — the coverage gradient (independent of §4.1)

Split ALL name-months into coverage quintiles by `numest`. The A2−A3 sign
disagreement must be **monotone decreasing in coverage depth**: largest in the
thinnest quintile, absent in the deepest.

* **P3** — |A2 − A3| in the thinnest `numest` quintile > that in the deepest,
  and the deepest quintile shows no sign disagreement.

This is the prediction that distinguishes "churn" from "some other small-cap
effect". A generic small-cap story predicts no coverage gradient within small
caps; the churn story requires one.

### 4.3 Placebo

* **P4** — a churn-free purge applied to **A2** (which is already blind to
  churn by construction) must leave A2 materially unchanged (|Δ| < 1.5 %/yr).
  If purging moves A2 as much as it moves A3, the purge is selecting on
  something other than churn and the whole design is void.

## 5. Decision rule, fixed now

| outcome | condition | consequence |
|---|---|---|
| **IDENTIFIED_CHURN** | P1 ✅ and P2 ✅ and P3 ✅ and P4 ✅ | The object is identified: A2 measures revisions, A3 is contaminated by coverage churn in thin-coverage names. A3 as constructed is retired as a revision proxy. The small segment moves from UNRESOLVED to "A2 is the licensed construction", and a SEPARATE pre-registration may then test delivery. Still no graduation: gross ≠ net. |
| **NOT_CHURN** | P1 ✗ | Churn is not the explanation. The successor hypothesis is REJECTED and recorded as such. Small stays UNRESOLVED and no further analyst delivery work runs tonight. |
| **PARTIAL** | P1 ✅ but P3 ✗ or P4 ✗ | The purge moved the number without the mechanism's fingerprint. Treated as NOT identified — reported, not believed. Small stays UNRESOLVED. |
| **POWER_FAILED** | §3 gate fails | Nothing is run or quoted. |

**No outcome of this trial permits a signal to change `allowed_in_pm`.**
`analyst_target_revision` stays HYPOTHESIS in the registry regardless.

## 6. What would make this trial wrong

* `numest` in `ptgsumu` may itself be a smoothed or restated count, in which
  case `numest_t == numest_{t−1}` does not mean "same analysts". This is
  checked first: if the count is non-integer or its month-over-month change
  distribution has no mass at zero, the trial reports DATA_QUALITY and stops.
* Churn and revision are correlated in reality — an analyst dropping coverage
  after a bad quarter is information. The purge therefore removes real signal
  along with the contaminant. This trial cannot separate those, and does not
  claim to: it asks only whether the two constructions can be reconciled, not
  which is the better predictor.
* Both arms remain **gross**. Nothing here touches the turnover finding, which
  is what actually killed the family (10.2× turnover, 5.67 points to costs).

## 7. Registry and canon

* CANON §16 — the cost denominator is not the winner's. No net numbers are
  quoted by this trial at all; it is a gross measurement question.
* NIGHT-9 — rank-IC may describe ordering, may not corroborate a money result.
  No rank-IC appears in the decision rule.
* The corpse this is not: `TRIAL-BRAIN-005-revisions` (EPS revisions, killed)
  and `TRIAL-TGT-REBUILD` (target levels, killed). Neither decomposed a
  consensus change into revision and churn components; both are carried as
  named priors, and this trial issues no verdict on either.
