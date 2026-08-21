# PREREG — TRIAL-PREDMARKET-2: cross-venue divergence (Kalshi vs Polymarket) at daily observation

**Status:** DRAFT (unsigned; corpus accrual is context-only regardless of signature)
**Registered:** 2026-08-21
**Inception:** first PROD Polymarket snapshot written by `pi_prediction_markets`
(2026-08-21 17:55 ET or later). Dev smoke snapshots are excluded from grading.

## Why this trial exists

Murat asked (2026-08-21 evening) whether rejecting prediction-market
arbitrage is justified, given that real quant firms run it. The honest
answer: the arb is real FOR STREAMING, CAPITALISED, TWO-VENUE PLAYERS
(publicly reported through the 2024 US election cycle), and unmeasured for
our infrastructure (one daily snapshot, retail fees, no execution). This
trial replaces an asserted rejection with a measured one: if persistent,
above-cost divergences are visible at OUR observation frequency, the ESCALATE
branch produces a written execution proposal for Murat's decision; if not,
the rejection stands on receipts.

## Hypothesis (falsifiable, honest prior stated)

Cross-venue divergences between Kalshi and Polymarket mid prices on matched
event contracts, observed once daily, are predominantly within round-trip
costs or transient (closed by the next daily snapshot). Honest prior: the
REJECT branch — daily-frequency observation is ~4 orders of magnitude slower
than the players who close these gaps.

## Registration declarations

- slice_purpose: PAIRED (two venues graded on the same matched contracts;
  forward accrual only — no historical slice is read)
- hypothesis_source: public reporting of 2024-cycle Kalshi/Polymarket
  cross-venue arbitrage; docs/research/R1_LLM_FORECAST_CALIBRATION_2026-08-08.md
  for the fee/loss context
- hypothesis_source_window: 2023-01-01..2025-12-31 (entirely before this
  trial's forward-only inception)

## Power declaration (§64)

- declared_effect_size: 5 pp (the share of matched contract-days showing
  persistent above-cost divergence, vs a zero baseline — the smallest share
  that would justify drafting an execution proposal)
- event_frequency_per_year: 150 (matched contract-days/yr, conservative;
  the dependence unit is the EVENT — strikes and days within one event
  co-move, ~12–25 distinct matched events expected)
- outcome_dispersion: 22 pp (binary-indicator SD near p=0.05,
  sqrt(0.05·0.95) ≈ 0.218)
- n_required ≈ (2.8 × 0.22 / 0.05)² ≈ 152 matched contract-days — about one
  year of accrual at the declared frequency. The minimum window (150) is set
  at that scale deliberately.

## Primary metric (the ONE deciding number)

`persistent_above_cost_share`: the fraction of matched contract-days where
|mid_kalshi − mid_polymarket| > COST_BAR at snapshot T AND the same matched
contract still shows |Δmid| > COST_BAR at snapshot T+1 trading day. All other
cuts (by venue side, by category, by liquidity tier, non-persistent
divergence share) are reported, never deciding.

## Frozen parameters

- COST_BAR: 0.05 absolute probability. Derivation (declared, conservative):
  Polymarket taker fee schedule rate 0.04 (measured from the live API
  2026-08-21, `feeSchedule.rate`, takerOnly) + Kalshi fee ≈ 0.07·p·(1−p)
  round trip + both venues' observed spreads. A divergence below 0.05 is
  not claimed as money.
- Persistence horizon: the NEXT daily snapshot (both venues 17:55 ET).
- Venue price definitions: Kalshi mid per PREREG_PREDMARKET_1; Polymarket
  mid = (bestBid + bestAsk)/2.
- Polymarket collection scope: active, accepting orders, liquidity ≥ 1,000
  USDC, close within 400 days, volume24hr > 0.
- MATCHING SPEC GATE: the Kalshi↔Polymarket contract-matching procedure does
  not exist yet. It must be committed as
  `TRIALS/INSTR-PREDMARKET-MATCHING.md` BEFORE the first pair is graded;
  snapshots accrue blind to any matching and are eligible retroactively
  (prices were written before any pairing existed). The spec freezes on
  commit.

## Decision rule

- ESCALATE (a WRITTEN execution proposal goes to Murat — never execution
  itself, which this platform does not do): persistent_above_cost_share ≥ 5%
  over ≥ 150 matched contract-days spanning ≥ 12 distinct events and ≥ 3
  calendar months.
- REJECT WITH RECEIPTS (the standing rejection of divergence arbitrage
  becomes evidence-backed for this infrastructure): share < 5% at that
  sample. A null owes two tests: the equivalence bound is share < 2%
  (below half the escalation bar); 2%–5% is NOT_ESTABLISHED and continues
  accrual to 300 contract-days.
- Earliest decision: 2026-11-21. Crash-event override: SPY −20%
  peak-to-trough defers decisions to ≥ 6 months past trough.
- Contamination clause: snapshots with `pages_truncated > 0` on either
  venue, or matched pairs whose contract terms are found to differ in
  resolution criteria (recorded at matching time), are excluded — exclusion
  recorded per pair, never silently.

## What this rule may NOT do

- No execution, no accounts on either venue, no capital. The ESCALATE branch
  produces a DOCUMENT for an attended decision, nothing else.
- The corpus is DESCRIPTIVE CONTEXT: nothing in any scoring path may read it
  before a successor trial passes.
- No "signal", "predicts", or buy/sell framing anywhere it surfaces.
- Divergence is never reported as "profit available" without the COST_BAR
  and the persistence test attached.
