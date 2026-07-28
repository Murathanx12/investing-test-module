# TRIAL-EVENT-8K-FILTER — distress 8-K exclusion screen (batch 10, reframed)

**Registered:** 2026-07-27 UTC — BEFORE any 8-K data acquisition (no 8-K corpus
exists on disk; the EDGAR pull happens only after this doc's freeze commit).
**Registry row:** `TRIALS/registry.jsonl` via `register_trial()`.
**Counts:** +1 candidate → cumulative 156.

## Provenance (declared)

Batch 10 was originally conceived as a long-only, item-level 8-K PICKER. The
2026-07-27 external-evidence sweep (`aegis-finance docs/research/
RESEARCH_SWEEP_2026-07-27.md` §1.2) reframed it: Lerman & Livnat (RAST
15(4):752–778, 2010) show post-filing drift is concentrated in DISTRESS items
and the short leg — good news reacts at the event date (already
press-released), bad news at the filing date. The reframe comes from published
literature, not from our own data (no 8-K data has ever been touched by this
program), so it carries full evidential weight — this is NOT a post-hoc
repair.

**Declined at registration (prior-check receipts):**
- Item 2.02 earnings PICKER — PEAD is CLOSED in our ledger with an inverted
  in-window sign (pead_agree IC t −2.6, 5th sign reversal). Not registered.
- Any item-level SCAN across the 8-K taxonomy — L&L's 22-significant-items
  result is heavily multiple-tested (~125k filings); we register ONE
  pre-specified item set instead of scanning.

## Hypothesis

Names filing a distress 8-K — items **1.03** (Bankruptcy or Receivership),
**2.04** (Triggering Events That Accelerate or Increase a Direct Financial
Obligation), **5.01** (Changes in Control of Registrant) — earn significantly
negative forward market-adjusted returns over the following quarter.
Mechanism: the drift lives on the short side, where arbitrage is constrained
(borrow cost, unshortable distressed names), so underreaction persists on the
leg we cannot trade but CAN avoid. Long-only use is as an exclusion FILTER on
book universes (taxonomy Role=FILTER; the taxonomy's own defensive prior:
"STRONG as exclusion screen, WEAK as long-alpha").

**Honest prior:** MEDIUM for the cohort effect (documented magnitudes:
bankruptcy −15/−13/−19% at 30/60/90d; control/obligation −1.5 to −3.7%;
sample 2005–2006 only, gross, size/BM-matched). Book-level value is small
(rare events) — the claim is risk reduction, not alpha.

## Expected effect size

Flagged-cohort 63-trading-day market-adjusted return meaningfully negative
(−2% to −15% depending on item mix); book-level drag avoided: single-digit
bps/mo (flag incidence is low).

## Expected decay / capacity

Underreaction to public distress filings; should persist while shorting
distressed names stays expensive. Capacity irrelevant (avoidance screen).

## Kill condition (pre-committed)

Explore window: flagged-cohort mean 63td market-adjusted return NOT negative
with t ≤ −2.0 → **family CLOSED.** No item-set re-tuning, no horizon
switching, no picker retry. One run.

## Two-arm design

- **Arm A (control, expected ~0):** pseudo-event cohort — same names, filing
  dates shifted −12 months (or +12 where −12 precedes the panel), identical
  measurement. Validates the pipeline.
- **Arm B (the claim):** true flagged cohort as specified.

## Run spec (frozen before execution)

- Events: 8-K filings with item ∈ {1.03, 2.04, 5.01}, parsed from EDGAR
  **daily indexes** (PIT-safe; full/quarterly indexes are retroactively
  rebuilt and are BANNED as the event source). Filing date = index date;
  after-5:30pm-ET dissemination nuance accepted as-is (entry is next trading
  day regardless).
- Universe: names matchable to the module CRSP panel (existing PIT link).
- Entry: first trading day after filing date. Horizons 21/63/126 td;
  **deciding = 63 td**. Market adjustment: EW return of the name's factory
  segment (small / largemid by the standard dollar-volume ranks).
- Windows: explore 2004-2018; confirm 2019-2024 (untouched until explore
  passes). One run per window, results final.
- Confirm gate: same sign with t ≤ −1.5 → FILTER adoption candidacy on book
  universes (attended wiring; the filter only ever EXCLUDES — house never
  shorts).

## PRE-RUN ADDENDUM — measurement resolution (2026-07-28 UTC, before any EDGAR touch)

The frozen deciding metric ("63 **trading-day** market-adjusted return") is NOT
computable on the data this module holds. Verified at re-entry, before any 8-K
acquisition: the module has CRSP **monthly** (`crsp_msf`) and daily *aggregates*
(`dsf_monthly_agg`); the only true daily return file is `dsf_pharma_2002`
(750 pharma permnos). A general-universe `crsp.dsf` pull is an attended WRDS tap
(Duo). yfinance is barred as a historical source for delisted names (T7 —
and a distress cohort is exactly the delisted tail).

**Departure declared and authorized (Murat, 2026-07-28, before the pull):**

- Deciding metric becomes the **3-calendar-month market-adjusted return measured
  from the first month-end ON OR AFTER the filing date** — i.e. the compounded
  returns of the three months FOLLOWING the filing month. The filing month itself
  is excluded entirely, so no partial-month pre-filing return can leak in.
- Bar **UNCHANGED**: cohort mean not negative with t ≤ −2.0 → family CLOSED.
  Confirm gate unchanged (same sign, t ≤ −1.5).
- Everything else in the run spec is unchanged: item set, daily-index event
  source, PIT match, segment-EW market adjustment, Arm A/Arm B, one shot.

**What this costs, stated up front:** the announcement-window reaction is now
entirely excluded, so the measured effect is strictly weaker than Lerman &
Livnat's headline magnitudes (which are measured from the filing date). This
cuts both ways and is disclosed as such: it removes any "you captured the
event-day crash" objection, and it is the *implementable* resolution — an
exclusion screen on a month-end-formed book can only ever act at a month-end.
The trial is therefore a test of post-filing DRIFT, not of the event reaction.

A true 63-trading-day re-measurement after a `crsp.dsf` tap would be a NEW
registration (the BRAIN-006 → BRAIN-011 pattern), never a rerun of this one.

**Secondary (reported, not deciding):** the same cohort is also run through the
house calendar-time flag-portfolio harness. Event-time cohort t-stats are
overstated when events cluster (bankruptcies cluster hard in 2008-09); the
calendar-time arm is the cross-correlation-robust cross-check. If the two
disagree, both are reported and the frozen event-time rule still decides.

## What this rule may NOT do

Never a short signal, never a standalone lane, never buy/sell language. On a
pass it earns exclusion-screen candidacy only; wiring into any live universe
is a separate attended step.

## Result (filled in AFTER the run — never edited afterwards)

- Gate report:
- Verdict:
