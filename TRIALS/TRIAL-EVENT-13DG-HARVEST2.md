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
