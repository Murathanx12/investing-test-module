# TRIAL-EVENT-13DG-HARVEST — is the 13D timing effect harvestable at monthly entry, cohort-controlled?

**Registered 2026-08-02, FROZEN BEFORE ANY RUN CODE IS WRITTEN.**
Cumulative candidate **178** (one arm, one shot).
Authority: Murat's standing "continue working" direction; the book stage's
attended question ("register a successor with a cohort-matched benchmark?")
is ruled YES by the orchestrating session, with the design defect it exposed
corrected structurally, not verbally.

## Why this exists — and what its predecessor could not answer

§29 established the first passing event family: 13D filings show real
post-filing drift vs matched controls (13d_first +152.2 bps over +1..+60,
clustered t 2.37), with the 13G placebo flat — intent, not disclosure.

The BOOK STAGE then failed (−41.0 bps/mo, t −2.63) — but its own placebo
showed the stage measured **cohort, not timing**: random-date books on the
same permnos produced the same negative excess. The frozen EW-universe
benchmark could not separate "activists file at good times" (§29's finding)
from "activists pick laggards" (what the book actually measured). Third
receipt for one lesson: §20, §28, book stage — **the control arm is the test.**

This trial asks the only still-open question: **does §29's timing effect
survive the monthly entry delay and costs, measured against the SAME
cohort-matched controls that established it?**

## Frozen design

**Arm (one):** `13d_first` events as banked and run (7,360; the rule-as-
written set, discrepancy already disclosed in the parent trial). 13d_all is
NOT tested — its +1..+60 was already below t 2.0 in the event study, and the
monthly entry delay consumes precisely its stronger short windows.

**Measurement:** event-study construction reusing the §29 control rule
VERBATIM (same segment, same calendar month, nearest dollar-volume rank, no
event within ±60 calendar days) — but the window is the monthly-implementable
one: from the first month-end ON OR AFTER the filing date, to the third
month-end after entry. Event and control legs measured over the identical
window. The deciding number is the **differenced net return**, t clustered by
entry month.

**Eligibility:** dollar-volume rank ≤ 3000 at entry month-end (micro excluded,
as in the book stage; the survivors-to-filing-month caveat carries over).

**Costs:** per-name KO-half round trip charged to the EVENT leg only (the
control is a paper benchmark and pays nothing — conservative against us);
flat-25 guard and zero-cost bound reported alongside (§25 convention).

## PLACEBO GATE (the book-stage lesson, made structural)

Before the real number is read: the identical pipeline runs on **five seeds
of random filing dates on the same permnos** (the book stage's diagnostic,
promoted to a gate). If the placebo's pooled differenced |t| ≥ 2.0, the
design has failed to control cohort and the verdict is **NO CONCLUSION —
nothing downstream is readable**, exactly as the sanity gate worked in
INSTR-CS-SPREAD. A design that cannot pass its own placebo does not get to
produce a tradability verdict.

## Bar / kill (frozen)

- **PASS:** placebo gate clean AND differenced net mean > 0 AND clustered
  t ≥ 1.5 → earns the confirm shot (2019-2024). **Confirm requires Murat's
  explicit authorisation. Always.**
- **FAIL:** placebo gate clean AND the bar missed → **the 13D family closes
  completely** for this program, recorded as: *"13D drift is real (§29),
  front-loaded inside the first post-filing weeks, and not harvestable at
  monthly resolution net of costs even cohort-controlled."* The program's
  lanes are monthly; a daily-resolution harvest is out of mandate and closes
  with the family (paper-noted, not re-registered).
- One shot. No re-cuts by cap, era, campaign type or window.
  Crash-before-readable repairable (disclosed); completed run final.

## Honest prediction (declared before the run)

From §29's own numbers: month-end entry forfeits the −1..0 and +1..+5 chunks
(≈ +100-116 bps of the +152) and part of +1..+20. Prediction: differenced net
**+8 to +25 bps/mo equivalent, clustered t 0.8-1.6, most likely a NARROW
FAIL** of the 1.5 bar; placebo gate passes (|t| < 1). If it instead clears,
the program has its first explore graduate since gp-small — and the confirm
decision is Murat's.

Both stage-level predictions on this family have missed in opposite
directions (event stage under-predicted, book stage over-predicted), both by
predicting timing while the stage measured cohort. This is the first stage
where the two are actually separated; scored either way.

---

# RESULTS — run 2026-08-02, one shot, explore 2004-2018

**Chain:** frozen at module commit `0951193` (arm, control rule, window, costs,
eligibility, bar, the placebo GATE and the honest prediction all declared before
any run code existed) -> `aegis_brain/factory/event_harvest.py` +
`tests/test_event_harvest.py` (28 spec tests) written after ->
`scripts/run_13dg_harvest.py` -> one shot.

## FROZEN VERDICT: **NO CONCLUSION. The placebo gate FAILED.**

Pooled placebo differenced net **-102.9 bps over the 3-month window (-34.3
bps/mo), clustered t -3.17**, against a gate that required |t| < 2.0.

**The real number does not exist.** `event_harvest.gated_run` calls the real
arm's closure only on the `passed` branch; the gate returned `passed=False`, so
the true-date computation was never executed in the process. That is the
compute-order tamper-evidence the freeze asked for, and the run log shows it:
five placebo passes, then the write-out, with no true-date matching in between.

## The gate, which is the whole result

Five seeds of filing dates redrawn uniformly at random across the explore
window, on the same permnos, through the identical pipeline — same control rule,
same window, same eligibility, same deciding KO-half cost arm.

| seed | n | event leg (bps/3mo) | control leg | **diff NET** | **t** | diff gross | t gross |
|---|---|---|---|---|---|---|---|
| 0 | 2,191 | 84.9 | 240.2 | **-184.9** | **-2.48** | -155.3 | -2.09 |
| 1 | 2,240 | 161.7 | 219.0 | -86.1 | -1.23 | -57.3 | -0.82 |
| 2 | 2,221 | 43.9 | 143.6 | -128.2 | -1.95 | -99.7 | -1.52 |
| 3 | 2,312 | 281.9 | 276.5 | -22.7 | -0.31 | +5.4 | +0.07 |
| 4 | 2,209 | 149.5 | 218.8 | -96.9 | -1.42 | -69.3 | -1.02 |
| **pooled** | **11,173** | **145.7** | **220.0** | **-102.9** | **-3.17** | **-74.3** | — |

Every seed is negative in net; four of five are negative in gross; one
individually breaches |t| 2.0. The gate reads the POOLED statistic, as frozen.

**Costs are not the whole story, and neither are they nothing.** The pooled
decomposition reconciles exactly: gross -74.3 bps minus the 28.5 bps round-trip
charged to the event leg only = -102.8, against the measured -102.9. So **72% of
the placebo effect is a gross cohort drag of -24.8 bps/mo that the matched
control does not remove**, and 28% is the deliberately one-sided cost
convention.

## What the gate actually caught — the design's null is not zero

The claim this stage was built on is that matching on segment, calendar month
and nearest dollar-volume rank controls the cohort. **It does not, at monthly
resolution.** Random-date positions in 13D-targeted names lose ~25 bps/mo gross
to their own matched controls. If the true timing effect were exactly zero, this
design would have reported roughly -103 bps and read it as a decisive fail. A
measurement whose null sits three standard errors below zero cannot be scored
against a bar written at zero, which is precisely the situation the gate was
frozen to detect, and precisely what the frozen text calls NO CONCLUSION.

Dollar-volume rank is a LIQUIDITY match, not a cohort match. Within a segment
and month, 13D targets are still the value/laggard tail, and the control rule
never touched that.

## Two independent cross-checks that the pipeline is sound

The house rule is to suspect the pipeline before believing a surprising number,
and this number was surprising (the freeze predicted a clean placebo at |t| < 1).
Two checks, neither requiring a re-run:

1. **The control leg reproduces a known quantity.** 220.0 bps over 3 months =
   **73.3 bps/mo**, against the book stage's independently measured EW
   eligible-universe benchmark of **+72.6 bps/mo**. A matched-control basket and
   a whole-universe basket landing within 0.7 bps/mo of each other is what a
   working benchmark looks like.
2. **The direction and magnitude agree with the book stage's placebo, reduced by
   the amount the matching does buy.** Book stage, random dates vs the unmatched
   EW universe: -39.9 to -85.9 bps/mo. Here, random dates vs matched controls:
   -34.3 bps/mo net, -24.8 gross. The matching removes roughly half the cohort
   drag and leaves the rest. Two constructions, same sign, magnitude reduced in
   the direction the matching predicts.

`n_entry_months` = 177 in every seed, which is exactly the count of entry
month-ends from 2004-01-31 to 2018-09-30 — the last entry whose third month-end
still lands inside explore.

## What this does NOT license

- **The frozen FAIL branch is NOT triggered.** Closure of the 13D family was
  conditioned on "placebo gate clean AND the bar missed". The gate was not
  clean, so **the family does not close and the harvestability question stays
  open and unanswered.** Reading the fail branch off a failed gate would be
  exactly the inference the gate exists to forbid.
- **NEG_RESULTS 29 is not retroactively damaged, and the bias runs in its
  favour.** The measured design bias is NEGATIVE. A design biased negative that
  nonetheless reported **+152.2 bps at clustered t 2.37** for `13d_first` over
  +1..+60 was, if anything, understating the effect. What is now known is that
  its control rule leaves a negative cohort residue at monthly horizons; the
  event-resolution finding stands, with that residue disclosed against it.
- **No debiasing, no re-cut, no successor is taken here.** Subtracting the
  placebo mean, or matching on characteristics instead of liquidity rank, would
  each be a NEW design against the deflation count — an attended decision, not a
  repair.

## Attrition, disclosed

Per seed, of 7,360 banked `13d_first` events: ~3,400 survive control matching
(a redrawn date frequently lands outside the name's live months, versus 5,542
matched on the real dates in NEG_RESULTS 29), ~1,140 are ineligible at entry,
~44 have a window that would cross the explore wall, and **~2,200 reach a
measurement.** Every event that reached matching got a control (3,375/3,375 and
so on for each seed). The placebo cohort is therefore ~46% of the arm, skewed
toward names alive across more of the window — a property of the redraw,
reported not repaired.

Missing return cells inside a window (name delisted, position in cash) ran
0.8-1.2% on the event leg and 1.1-1.8% on the control leg, treated as 0 per the
harness convention.

## Mechanical plumbing, disclosed (the freeze was silent, precedent followed)

Declared in the module docstring before the run, not chosen after: holding-period
returns COMPOUND; a missing monthly return contributes 0 and the fill rate is
reported; the KO half-spread is charged at the entry month-end and again at the
exit month-end (a round trip) on the event leg only; eligibility is checked on
the EVENT name at entry and the control is not separately re-screened (that would
deviate from "the parent's rule verbatim"); and **the explore wall binds the
WINDOW, not only the event date** — a filing whose third month-end lands in 2019
produces no measurement, where the parent CAR trial let a +60-trading-day window
spill past the boundary. That is stricter than precedent, in the direction of the
one rule the programme never trades against.

## The frozen prediction, scored — 0 of 1 scoreable, and 3 unscoreable BY DESIGN

Declared: *"differenced net +8 to +25 bps/mo equivalent, clustered t 0.8-1.6,
most likely a NARROW FAIL of the 1.5 bar; placebo gate passes (|t| < 1)."*

| leg | predicted | measured | verdict |
|---|---|---|---|
| placebo gate passes at \|t\| < 1 | clean | **\|t\| 3.17** | **MISS** |
| differenced net +8..+25 bps/mo | — | never computed | **UNSCOREABLE** |
| clustered t 0.8-1.6 | — | never computed | **UNSCOREABLE** |
| narrow fail of the 1.5 bar | — | never computed | **UNSCOREABLE** |

The three unscoreable legs stay unscoreable. Computing the real number now to
settle a prediction would be the exact violation the gate was built to prevent,
and the prediction is worth less than the gate.

**The one leg that could be scored is the one the house was most confident
about** — that the cohort problem had been solved structurally by borrowing the
parent's control rule. It had not been. Three stages of this family have now made
predictions and all three missed on the same axis: **the house keeps predicting
timing while its constructions keep measuring cohort.** The difference this time
is that the design caught it before the number existed instead of after.

## Scope honoured

One shot. The real arm was never computed. The confirm window was not read, no
forward lane was seeded, no re-cut was taken, no successor was registered.
Cumulative candidates unchanged at **178**.

## Attended decision owed

Whether a successor is registered that controls the cohort on RETURN-RELEVANT
characteristics (size / book-to-market / prior-return matching) rather than on
liquidity rank, with the same placebo gate in front of it — and whether that is
worth a candidate against the deflation count, given that this family has now
consumed four (175-178) and produced one real event-resolution effect with no
demonstrated path to a monthly account. That is Murat's call, not this session's.
