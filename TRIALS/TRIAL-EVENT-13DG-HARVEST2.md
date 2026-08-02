# TRIAL-EVENT-13DG-HARVEST2 — the terminal harvest test, cohort-matched on what predicts returns

**Registered 2026-08-02, FROZEN BEFORE ANY RUN CODE IS WRITTEN.**
Cumulative candidate **179** (one arm, one shot). **TERMINAL for the 13D
family, declared now: whatever happens here, the family resolves and no
further matching scheme, window or re-cut is registered.**
Authority: Murat's standing direction; HARVEST's attended question is ruled
YES-with-a-cap by the orchestrating session.

## Why one more is admissible — and why only one

HARVEST (178) ended NO CONCLUSION: its placebo gate fired (pooled null −102.9
bps, t −3.17), proving liquidity-rank matching does not control the activist
cohort — and, critically, **the true-date number was never computed**.
Because the real dates were never read, iterating the matching design leaks
nothing about the outcome: **calibrating an instrument on its own null is
legitimate; what is not legitimate is doing it forever.** Hence the cap.
This is the family's fifth candidate; §30's null-decomposition tells us
exactly which dimension the match missed, so exactly one redesign is
justified — the one that matches on it.

## What changes, and only this

The §30 decomposition showed random-date positions in 13D-targeted names
lose ~25 bps/mo gross to liquidity-matched controls: within segment+month,
activist targets are still the **laggard tail**. So the control now matches
on the return-relevant cohort traits directly:

**Control rule:** for each event, candidate controls are names in the same
**segment**, same **calendar month**, eligible (dollar-vol rank ≤ 3000 at
entry month-end), with **no 13D/13G event within ±60 calendar days**. Among
them, the control is the nearest neighbour by Euclidean distance in
**per-month standardised (log market cap, prior 6-month return)** — both
measured at the **last month-end strictly BEFORE the filing date** (the
cohort trait is PRE-filing laggardness; measuring it after would absorb the
event itself). One control per event, with replacement, ties broken by
smallest permno (determinism).

Everything else is HARVEST's frozen spec verbatim: `13d_first` events as
banked (7,360); window = first month-end on/after filing → third month-end
after entry; both legs identical window; deciding number = differenced NET
return, t clustered by entry month; KO-half round trip charged to the event
leg only; flat-25 guard + zero-cost bound reported.

## PLACEBO GATE — identical, and still in front

Five seeds of random filing dates on the same permnos through the identical
pipeline, run FIRST, real number computed ONLY on the passing branch
(compute-order is the tamper-evidence). Gate: pooled placebo |t| < 2.0.

## Bar / kill — with the terminal clause

- **Gate fails →** the family CLOSES, recorded as: *"the 13D timing effect
  is real at event resolution (§29); no admissible monthly-resolution
  design was found in two attempts; harvestability at the program's mandate
  resolution is unmeasurable, and therefore unclaimable."* No third design.
- **Gate passes, bar missed** (mean ≤ 0 or clustered t < 1.5) → the family
  CLOSES: *"real at event resolution, not harvestable at monthly entry net
  of costs, cohort-controlled."*
- **Gate passes, bar cleared** → the program's first explore graduate since
  gp-small. STOP: **confirm (2019-2024) requires Murat's explicit
  authorisation. Always.**
- One shot. Crash-before-readable repairable (disclosed); completed final.
  No forward lane seeded under any outcome.

## Honest prediction (declared before the run; the house is 0-for-2 on this family's stage predictions and says so)

Placebo gate: **passes this time** (~60% confidence — prior-return matching
targets the measured drag directly; residual risk is that "laggard" has more
dimensions than two). If the gate passes: differenced net **+8 to +25
bps/mo, clustered t 0.8-1.6, narrow fail** — unchanged from HARVEST, since
nothing about the entry-delay arithmetic changed. Most likely end-state:
the family closes with the §29 effect real and unharvestable, and the
program's search phase closes with it.

---

# RESULTS — run 2026-08-02, one shot, explore 2004-2018

**Chain:** frozen at module commit `c3e4f03` (control rule, gate, bar, terminal
clause and the honest prediction all declared before any run code existed) ->
`aegis_brain/factory/event_harvest.py` HARVEST2 section + `tests/test_event_harvest2.py`
(24 spec tests) written after -> `scripts/run_13dg_harvest2.py` -> one shot.

## FROZEN VERDICT: **NO CONCLUSION — the placebo gate FAILED again. By the terminal clause declared at freeze, THE 13D FAMILY CLOSES.**

Pooled placebo differenced net **-90.1 bps over the 3-month window (-30.0
bps/mo), clustered t -3.02**, against a gate requiring |t| < 2.0.

**The real number does not exist.** `gated_run` calls the real arm's closure
only on the passing branch; the gate returned `passed=False`, so the true-date
computation never executed in the process. Second time, same tamper-evidence.

Recorded as frozen: *"the 13D timing effect is real at event resolution (§29);
no admissible monthly-resolution design was found in two attempts;
harvestability at the program's mandate resolution is unmeasurable, and
therefore unclaimable."* No third design.

## The gate, which is again the whole result

| seed | n | event leg (bps/3mo) | control leg | **diff NET** | **t** | diff gross | t gross |
|---|---|---|---|---|---|---|---|
| 0 | 2,114 | 107.4 | 203.1 | -124.8 | -1.77 | -95.6 | -1.36 |
| 1 | 2,160 | 170.7 | 256.0 | -113.7 | -1.73 | -85.3 | -1.30 |
| 2 | 2,150 | 72.9 | 238.3 | **-193.6** | **-2.77** | -165.4 | -2.37 |
| 3 | 2,238 | 276.8 | 210.2 | +38.8 | +0.52 | +66.6 | +0.90 |
| 4 | 2,139 | 173.4 | 208.8 | -62.7 | -0.91 | -35.4 | -0.51 |
| **pooled** | **10,801** | **161.4** | **223.3** | **-90.1** | **-3.02** | **-61.9** | — |

Four of five seeds negative in net, one individually breaching |t| 2.0; the
gate reads the pooled statistic, as frozen. `n_entry_months` = 177 in every
seed — again exactly the entry month-ends from 2004-01-31 to 2018-09-30.

Costs reconcile exactly: gross -61.9 minus the 28.2 bps round trip charged to
the event leg only = -90.1, against the measured -90.1. **69% of the placebo
effect is a gross cohort drag of -20.6 bps/mo the matched control still does
not remove;** 31% is the deliberately one-sided cost convention.

## The finding: §30's diagnosis of its own null was WRONG

HARVEST2 was built on §30's decomposition — that the residual drag was the
**size/laggard tail**, unmatched because dollar-volume rank is a liquidity
proxy. The successor matched on exactly that, and on real dates it worked as
designed: the residual size gap fell from **-0.265 to -0.086 SD** (68% closed)
and the prior-return gap from -0.050 to +0.028 SD (over-closed, sign flipped).

But on the **placebo dates the gate actually reads**, the two matchers are
nearly indistinguishable — and the drag barely moved:

| dates | matcher | n | event z_cap | control z_cap | **gap** | event z_ret | control z_ret | **gap** |
|---|---|---|---|---|---|---|---|---|
| REAL | HARVEST (dollar-vol rank) | 5,542 | -0.982 | -0.686 | **-0.265** | -0.168 | -0.116 | -0.050 |
| REAL | HARVEST2 (size + prior ret) | 4,525 | -0.948 | -0.862 | **-0.086** | -0.155 | -0.182 | +0.028 |
| placebo s0 | HARVEST | 3,375 | -0.835 | -0.769 | -0.070 | -0.121 | -0.096 | -0.021 |
| placebo s0 | HARVEST2 | 3,123 | -0.773 | -0.722 | -0.051 | -0.118 | -0.156 | +0.038 |
| placebo s1 | HARVEST | 3,423 | -0.831 | -0.766 | -0.065 | -0.121 | -0.140 | +0.030 |
| placebo s1 | HARVEST2 | 3,159 | -0.771 | -0.713 | -0.058 | -0.116 | -0.150 | +0.034 |

Read the placebo rows: the size gap the liquidity match left was **already only
-0.07 SD**, and closing it to -0.05 SD moved the gross drag from **-24.8 to
-20.6 bps/mo** — 17% of it. A 0.02-SD size imbalance cannot carry 20 bps a
month, and the return dimension was already over-corrected in the control's
favour, which should have made the drag WORSE if momentum were the mechanism.

**So the drag is not size and not prior return.** Whatever makes a 13D-targeted
name underperform a segment-, month-, liquidity-, size- and momentum-matched
non-target on RANDOM dates is a property of the cohort that none of five
matching dimensions reaches. It is a persistent name-level effect, not an
event-window one — which is precisely why it survives date randomisation.

## The pipeline was checked before the number was believed

1. **The control leg reproduces a known quantity.** 223.3 bps/3mo = **74.4
   bps/mo** against the book stage's independently measured EW eligible-universe
   benchmark of **+72.6 bps/mo** — within 1.8 bps/mo, and within 1.1 bps/mo of
   HARVEST's own 73.3. Three constructions, one benchmark.
2. **The direction and magnitude track HARVEST, reduced by what the new match
   buys.** -24.8 -> -20.6 bps/mo gross, -34.3 -> -30.0 net. Same sign, smaller,
   by about the amount the characteristic table says the matching improved.
3. **A pre-run plumbing probe** (disclosed below) confirmed the matcher's
   coverage and characteristic behaviour before the shot, touching no return.

## What this CLOSES and what it does not license

- **The 13D family is CLOSED**, on the frozen terminal clause, in the
  *unmeasurable* branch — not the *unharvestable* branch. The distinction is
  load-bearing: **nobody knows whether 13D drift is harvestable monthly.** Two
  admissible designs failed to produce a readable measurement, the freeze capped
  the attempts at two, and the honest statement is that the program cannot
  measure it, not that it is not there.
- **§29 is untouched and the bias still runs in its favour.** The measured
  design bias is NEGATIVE in both matchings; a negatively-biased design that
  reported +152.2 bps at clustered t 2.37 was understating, not manufacturing.
- **No debias, no re-cut, no successor, no forward lane.** Subtracting the
  placebo mean is a new design; so is a third matching scheme. Both are barred
  by the terminal clause, and neither is registered.
- **The gate itself graduates.** Two designs, two firings, two results that
  would have been read as decisive fails against a bar written at zero. Every
  control-armed design in this program now carries a random-date placebo gate
  in front of the result — the standing rule adopted after §30 has paid for
  itself a second time in a single day.

## Attrition, disclosed

Per seed, of 7,360 banked `13d_first` events: ~3,940 have no segment that month
(the permno is outside the daily panel's ranked universe on a redrawn date),
~117 have no characteristics at the pre-filing month-end, ~135 find no
admissible candidate, leaving ~3,160 matched; of those ~965 are ineligible at
entry and ~43 would cross the explore wall, so **~2,160 reach a measurement**
(~29% of the arm). Missing return cells inside a window ran 0.8-1.2% on the
event leg and 0.8-1.3% on the control leg, treated as 0 per the harness
convention.

On REAL dates the new rule matches **4,525** events versus the parent rule's
5,542. The gap is the price of the new rule: a control must now also be
eligible at the entry month-end and carry six months of return history and a
market cap at the pre-filing month-end. Disclosed, not repaired.

## Mechanical plumbing, disclosed (freeze silent, precedent followed)

Declared in the module before the run, not chosen after:

* **The +/-60cd contamination exclusion is applied against the ARM's own event
  frame**, exactly as `daily_events.match_controls` does. The freeze's phrase
  "no 13D/13G event within +/-60cd" sits under a heading reading "What changes,
  and only this" — the metric. Widening the exclusion to the full banked
  13D+13G universe (85,787 filings) would be a second, stricter change the
  freeze does not authorise, and it would break the placebo's symmetry by
  testing redrawn arm dates against a fixed real exclusion set.
* **Per-month standardisation is over the eligible universe** (factory
  universe, rank <= 3000) in the characteristic month — the population controls
  are drawn from. Standardising over all names would let micro junk inflate the
  return dimension's SD and quietly re-weight the metric back toward size, the
  failure being corrected. Coverage: 2,468-3,000 eligible names carry both
  characteristics in every one of the 180 explore months; no month is degenerate.
* **Prior 6-month return compounds and requires all six monthly returns**; no
  winsorisation (the freeze authorises none, and nearest-neighbour matching is
  not a regression).
* **Market cap is |month-end price| x shrout x 1000**, the same construction
  `abio.py`, `optsurf.py` and `rank_dead.py` use for `log_mktcap`.
* **Ties break to the smallest permno** by sorting the candidate pool ascending
  before the argmin; the run is reproducible to the row.
* **Events with no segment are RETAINED with a null control** rather than
  vanishing from the frame as they do in the parent matcher, so attrition adds
  up to the arm. This changes the reported denominators versus HARVEST, not any
  measured quantity.
* **A pre-run plumbing probe was executed and is disclosed:** the matcher was
  run once on real dates to measure timing (1.0s), match rate (4,525/7,360) and
  the characteristic gaps in the table above. It computed no return, no leg and
  no difference — characteristics are the matcher's INPUTS. The trial's one shot
  remained the single invocation of the deciding pipeline.

## The frozen prediction, scored — 0 of 1 scoreable, 3 unscoreable BY DESIGN

Declared: *"Placebo gate passes this time (~60% confidence). If the gate passes:
+8 to +25 bps/mo, clustered t 0.8-1.6, narrow fail."*

| leg | predicted | measured | verdict |
|---|---|---|---|
| placebo gate passes (~60%) | clean | \|t\| 3.02 | **MISS** |
| differenced net +8..+25 bps/mo | — | never computed | **UNSCOREABLE** |
| clustered t 0.8-1.6 | — | never computed | **UNSCOREABLE** |
| narrow fail of the 1.5 bar | — | never computed | **UNSCOREABLE** |

The three unscoreable legs stay unscoreable, permanently. **Four stages of this
family have now made stage-level predictions and all four missed** — event
stage under-predicted, book stage over-predicted, HARVEST predicted a clean
placebo, HARVEST2 predicted a clean placebo *and* named the wrong mechanism for
why the first one fired. The declared residual risk ("laggard has more
dimensions than two") is the leg that came true, and it was written as the
minority case.

## Scope honoured

One shot. The real arm was never computed. The confirm window was not read, no
forward lane was seeded, no re-cut was taken, no successor was registered, and
none may be. Cumulative candidates **179**, unchanged from this session's start.
