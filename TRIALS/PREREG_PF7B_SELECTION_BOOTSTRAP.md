# PREREG — TRIAL-PF7B-SELECTION-BOOTSTRAP-1 (T4b) — REGISTERED, NOT RUN

**Registered:** 2026-08-10 · **Family:** PF-7B · **Stage:** statistical audit
**Origin:** external review #3/#5 · **Supersedes as primary evidence:** `runs/NIGHT7/T4_DEFLATED_SHARPE.json`

## 1. Why

T4 deflated the survivor's Sharpe against the expected maximum of N pure-noise
draws, and reported a ladder over N because no single N is defensible. The
reviewer's objection is correct and better than the ladder:

> **Stop arguing about N. Measure it.**

**179 is simultaneously too high and too low.** Too high because many of the 179
candidates are correlated variants of the same idea, so the effective number of
independent draws is smaller. Too low because rank-shape, rebalance-frequency,
clock-phase and exit-rule branches were all explored *afterwards* on the same
history and never entered the count.

A parametric E[max SR] cannot resolve either objection. An empirical bootstrap
that preserves the candidates' actual correlation structure resolves both at once.

## 2. Hypothesis

**H0:** given the real cross-correlation and time dependence of the candidate
set, a null factory would produce a best-candidate statistic at least as good as
the survivor's with probability ≥ 0.05.

**H1:** it would not.

## 3. Design (White Reality Check / Hansen SPA family)

1. Assemble the monthly return series of every candidate whose series is
   recoverable (target: the 148-row graveyard plus the survivor and the PF-2/PF-4
   variants).
2. **Impose the null** by demeaning each candidate's excess series, so every
   candidate has true expected excess return zero while retaining its variance,
   skew, kurtosis and — critically — its correlation with the others.
3. **Block-bootstrap the SAME time blocks across ALL candidates simultaneously**
   (stationary bootstrap, mean block length swept over {6, 12, 24} months and
   reported for each). Sampling candidates independently would destroy the
   cross-correlation that is the whole point.
4. In each bootstrap universe, compute the **maximum** statistic across
   candidates.
5. The empirical p-value is the fraction of bootstrap universes whose maximum
   equals or exceeds the observed survivor statistic.

Run against **three statistics**, because the answer may depend on which one the
search was actually optimising:
- raw excess return vs the CRSP VW benchmark,
- FF5+UMD factor-residual alpha,
- the exact metric that selected the survivor (net excess CAGR).

Report **Hansen SPA** alongside White's Reality Check: SPA reduces sensitivity to
irrelevant poor alternatives, and our candidate set contains cost-destroyed books
at t −8.4 that should not be allowed to set the null's scale (the same rows that
made T4's RAW variance estimate over-deflate).

## 4. Decision rule (frozen)

- Report the empirical p-value. **No threshold is a kill gate.** GATE-M1 measured
  DSR ≥ 0.95 as nearly powerless, and this trial must not re-import a hard gate
  through the back door.
- The output is a **calibrated statement of search burden**, to be reported
  *beside* T4's DSR ladder, not above it.
- If fewer than 40 candidate series are recoverable, the trial is **VOID for
  insufficient coverage** and says so — a bootstrap over a biased subset of the
  search is worse than the parametric ladder it replaces.

## 5. Registered predictions

1. **Coverage will be the binding constraint**, not compute — most of the 179 do
   not have a monthly return series banked in a recoverable form.
2. **The empirical p-value lands between 0.05 and 0.40** — i.e. worse than the
   parametric N=179 read (which put the survivor essentially at the null's
   expected max) because correlation reduces the effective number of draws.
3. **Block length will not matter much** (results stable across 6/12/24), because
   the candidates' excess series have low autocorrelation.

## 6. Ledger

Adds **9 branches** (3 statistics × 3 block lengths). Counted before any result
is interpreted.
