# PREREG — TRIAL-PREDMARKET-1: Kalshi market-implied probabilities vs house probability models

**Status:** DRAFT (unsigned; corpus accrual is context-only regardless of signature)
**Registered:** 2026-08-21
**Inception:** first PROD daily snapshot written by `pi_prediction_markets`
(2026-08-21 17:55 ET or later, on the Railway volume). The 2026-08-21 dev
smoke snapshot (6,640 rows, written minutes before this registration was
committed) is a smoke test and is EXCLUDED from grading — accrued-before-
commit data is never grandfathered.

## Hypothesis (falsifiable, honest prior stated)

On macro event contracts (Kalshi categories Economics / Financials / Companies,
resolving within 12 months), house probability models mapped to the same
observable will NOT beat the market mid-price on forward Brier. Honest prior:
the market wins — R1 (2026-08-08) recorded Economics & Business as the widest
published LLM-vs-crowd Brier gap (0.198 vs 0.147), and 6/6 LLM forecasters lost
real capital on Kalshi even at crowd-matching Brier. The value of the trial is
(a) a fast-resolving graded forecast ledger and (b) a live calibration
benchmark for the house crash/regime/event models — not an expected win.

## Primary metric (the ONE deciding number)

Mean forward Brier difference (house − market_mid) over PAIRED resolved
events, where market_mid = (yes_bid + yes_ask)/2 in dollars at the last daily
snapshot ≥ 7 calendar days before contract close_time. Everything else
(volume-weighted variants, categories split, horizon splits) is reported,
never deciding.

## Registration declarations

- slice_purpose: PAIRED (forward accrual only — the two legs are graded on the
  same resolved events; no historical slice is read by this trial)
- hypothesis_source: docs/research/R1_LLM_FORECAST_CALIBRATION_2026-08-08.md
  (external literature survey; Halawi et al. per-category Brier table)
- hypothesis_source_window: 2023-01-01..2025-12-31 (the surveyed literature's
  data window — entirely before this trial's inception, which is forward-only
  from 2026-08-21)

## Power declaration (§64, quoted before any confirmation)

- declared_effect_size: 5 pp (0.05 mean paired Brier difference — the scale of
  the R1-documented LLM-vs-crowd gap, 0.198 − 0.147; the smallest difference
  anyone would act on)
- event_frequency_per_year: 36 (paired resolved events/yr, conservative:
  CPI 12 + FOMC 8 + payrolls 12 + GDP 4; multiple strikes per event are ONE
  event for counting — strikes co-move, and the EVENT is the dependence unit
  for the bootstrap)
- outcome_dispersion: 10 pp (SD of per-event PAIRED Brier difference, 0.10 —
  both legs graded on the same outcome, so components are correlated and the
  difference is tighter than a raw Brier SD ~0.20)
- STATISTICAL_MDE_80 at n=36: 2.8 × 0.10/√36 ≈ 0.047 — the design can resolve
  the declared effect at the minimum window, in ~12 months of accrual.
- DECISION threshold (−0.02, economic bar) is BELOW the n=36 MDE: a
  NOT_ESTABLISHED at n=36 therefore continues accrual to n=100
  (MDE₈₀ ≈ 0.028) before any equivalence claim is made. A null owes two tests.

## Decision rule

- ADOPT ("house model calibrated vs market" claim earned; signal use still
  requires a successor prereg): Brier_house − Brier_market < −0.02 with a 95%
  bootstrap CI excluding 0, over ≥ 36 resolved paired events.
- REJECT (market stands as the probability oracle; house event-probabilities
  remain descriptive; the corpus remains a benchmark feed): difference ≥ 0, or
  CI includes 0, at ≥ 36 resolved paired events.
- Minimum window / earliest decision: n ≥ 36 resolved paired events (above the
  linter's n_required 31 at the declared power fields) AND no earlier than
  2026-11-21.
- Crash-event override: SPY −20% peak-to-trough defers any decision to ≥ 6
  months past trough.
- Contamination clause: contracts whose resolution source changes mid-life, or
  snapshots taken while the API returned partial pages (receipt
  `pages_truncated > 0`), are excluded — exclusion recorded per event in the
  grading receipt, never silently.

## Frozen parameters

- Snapshot cadence: one per market per UTC day, scheduled 17:55 ET.
- Price definition: market_mid as above; dollars, from the API's
  `yes_bid_dollars` / `yes_ask_dollars` fields.
- Watched categories: Economics, Financials, Companies (config
  `PREDICTION_MARKET_CATEGORIES`).
- PAIRING SPEC GATE: the mapping from house model outputs to specific
  contracts does not exist yet. It must be committed as
  `TRIALS/INSTR-PREDMARKET-PAIRING.md` BEFORE the first pair is graded;
  contracts snapshotted before the pairing spec exists are eligible for
  pairing (prices were written blind to any pairing), but no grading happens
  until the spec is committed. The spec is then frozen like any parameter.

## What this rule may NOT do

- The corpus is DESCRIPTIVE CONTEXT. Nothing in any scoring path
  (arena_composite, signal_engine, lane logic, fragility composite) may read
  it before a successor trial passes.
- No "signal", "predicts", or buy/sell framing anywhere it surfaces.
- No execution, no Kalshi account, no capital — paper measurement only
  (R1's receipt on real-capital losses is the standing reason).
- A zero-market snapshot day is written as a receipt with
  `status: ok_empty` — never inferred from silence.
