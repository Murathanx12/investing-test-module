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

---

# AMENDMENT 1 — 2026-08-10, before any compute

**Origin:** second external review pass. **Registered predictions in §5 are
UNCHANGED** — an amendment that edited its own forecasts after seeing the
critique would not be a preregistration. What changes is the *reasoning* behind
prediction 2, the *name* of what this trial measures, and the implementation
details, which were under-specified and therefore still choosable.

## A1.1 Prediction 2's rationale was backwards

§5.2 predicts p ∈ [0.05, 0.40] and justified it with "correlation reduces the
effective number of draws" — implying correlation makes the survivor look worse.
That is the wrong direction. For a fixed number of null candidates, positive
correlation makes their **maximum less extreme** (at ρ→1 the max of N draws
collapses to a single draw). A less extreme null maximum makes a fixed observed
winner look **more** exceptional, not less.

Two forces actually push in opposite directions here, and neither is obviously
dominant:

| force | direction on the p-value |
|---|---|
| candidates are correlated variants ⇒ null max less extreme | **lower** p (survivor more exceptional) |
| block bootstrap preserves fat tails and autocorrelation the Gaussian parametric E[max SR] ignores | **higher** p |
| branches never counted in 179 (rank shape, clock, exits) enter the candidate set | **higher** p |

The prediction stands as registered; its stated mechanism does not.

## A1.2 A White p-value is not comparable to a DSR number

§5.2 says the result will be "worse than the parametric N=179 read". These are
different statistics with different nulls — White's Reality Check asks whether
the best model in a specification search beats a benchmark once data reuse is
counted; DSR is a probabilistic-Sharpe statistic against a selection-adjusted
benchmark Sharpe. **The write-up may not say "p = x, worse/better than DSR
0.549."** They are reported side by side and compared only in direction.

## A1.3 What this trial actually measures — renamed

It is registered as measuring "the search burden". It does not. Aegis did not
compute 179 fixed strategies and take the best: it ran IC gates, gross/net gates,
segment splits, confirmation eligibility, successor campaigns spawned *by earlier
results*, rank-shape exploration, clock exploration and exit follow-ups. A
bootstrap over recovered finished return series holds the alternative set fixed
and cannot reproduce an adaptive search whose later branches depended on earlier
outcomes.

**Renamed: FIXED-ALTERNATIVE SEARCH-BURDEN AUDIT (a lower bound).** The true
burden is at least this large. Whether the genealogy can be replayed —
which candidate passed, which earned confirmation, which spawned a successor — is
a separate and harder question, registered as a successor, not claimed here.

## A1.4 Implementation frozen now (was choosable, therefore a branch)

- **B = 5,000** bootstrap universes per (statistic × block length) cell.
- **Seed 20260810**, `np.random.default_rng`.
- **Stationary bootstrap of Politis & Romano (1994)**: geometric block lengths
  with mean L ∈ {6, 12, 24} months, wrapped, and the **same block index sequence
  applied to every candidate simultaneously** — that is what preserves the
  cross-section.
- **Monte-Carlo uncertainty on the p-value is reported**: √(p(1−p)/B). A p-value
  printed without it invites over-reading the third decimal.
- **Missing history is masked, never zero-filled.** Candidates have different
  inception dates and windows; a zero-filled month is a fabricated flat return
  that shrinks variance and inflates the winner. Each candidate keeps its own
  eligibility mask and contributes only to bootstrap months it actually spans.
- **Hansen SPA is implemented as Hansen (2005) specifies** — studentised
  statistic plus the sample-dependent recentring that excludes poor alternatives
  from setting the null's scale. A demeaned-max bootstrap relabelled "SPA" is
  not SPA, and if the recentring is not implemented the output is reported as
  White RC only.

## A1.5 Coverage must be described before the result exists

§4's "fewer than 40 recoverable ⇒ VOID" is a useful floor but a poor
representativeness test: 80 recovered rows that are all recent polished
candidates are more biased than 35 that span the search. **A
`coverage_matrix.json` — recovery rate by family, era, segment, verdict class and
stage — is written and inspected BEFORE the bootstrap runs.** If recovery is
concentrated in one family or one era, the trial reports that as its headline and
the p-value as a footnote.

## A1.6 Ledger

The amendment adds **0 branches**: B, seed, block-length grid and bootstrap
algorithm were previously unspecified and are now fixed, which removes
researcher degrees of freedom rather than adding them.
