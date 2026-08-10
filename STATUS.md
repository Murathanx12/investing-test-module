# STATUS — handoff after NIGHT-5 (2026-08-09)

## Where the code is

* `main` (Aegis module) — **night-3 and night-4 merged** (`b3fc8fe`, approved at
  home). Module suite green post-merge.
* `factory/night-5` — **pushed, UNMERGED**, awaiting Murat's read.
* `aegis-finance` `main` — execution standard amended and pushed (`7556654`).
* Holdout unread throughout. Nothing promoted. No lane seeded, no flag flipped,
  no `paper_nav` touched, no keys changed.

## What NIGHT-5 changed

**Two decisions moved, both toward smaller claims.**

1. **Annual rebalancing ships for mechanical reasons, not measured ones.**
   `TRIAL-PF5-REBAL-FRONTIER-1` → UNRESOLVED. None of the 15 pairwise
   differences between the six clocks is significant (level correlations
   0.958–0.993; 24 m − 12 m = +0.71 %/yr at t 0.83). NIGHT-4's "annual dominates
   on every axis" keeps its mechanical half — turnover 0.48 vs 2.40, cost drag
   31 vs 120 bps, holdable by a human — and loses its return half.
2. **The LLM re-ranking campaign is NOT built.**
   `TRIAL-PF5-RANK-SHAPE-1` → NO MEASURABLE SHAPE (Cochran Q p = 0.6927 over 105
   bucket books). Arm A1: ranks 11-20 minus 1-10 = **+0.77 %/yr at t 0.16**, so
   NIGHT-4's +8.93 % vs −1.17 % does not replicate. Stated precisely: ordering is
   **unmeasured below ~10.7 %/yr**, not zero. The next instrument needs more
   power, not another pass over the same 482 months.

**G7 exists and has run.** First workload was the annual config, as instructed.
At $1 m NAV daily reality costs **28 bps/yr** against the monthly harness — a
validation. It also produced the two things the monthly harness cannot:

* daily max drawdown **−52.6 %** against the **−48.4 %** month-end figure we have
  been quoting (4.1 pp deeper);
* **capacity breaks between $100 m and $500 m** — 58 % then 94 % of days with
  orders clipped by a 5 %-of-volume cap, −157 bps/yr at $500 m.

**The graveyard is half broken experiments.** 148 banked rows: killed by the
idea **69**, killed by the experiment **74** (POWER_FAILED 31,
IMPLEMENTATION_FAILED 29, DATA_FAILED 14). Median MDE 3.74 %/yr against the
standard's own 3 %/yr bar. **14 rows never ran** and were counted as tests.
But the median point estimate is **−1.40 %/yr**, so most of these ideas really
are bad.

**The guards are code now.** `aegis_brain/verdicts.py`, 9 states, 23 tests —
UNRESOLVED cannot print REJECT, FACTOR_EXPLAINED cannot print "no edge".
They caught two of my own bugs during the night they were written.

## BLOCKED ON MURAT

1. **PIT-clean ETF price feed (Polygon or FMP) for AVUV, DFSV, IJS, VBR from
   2019-09.** Unchanged since NIGHT-4 and still the only blocker on the real
   product comparison. Env var only.
2. **Merge `factory/night-5`?**
3. **Product note v0.1** (`docs/PRODUCT_NOTE_v0.1_2026-08-09.md`) needs a read —
   it states a smaller claim than the roadmap started with.

## Recorded failures of execution (not of prediction)

* **Arm A4 of TRIAL-PF5-RANK-SHAPE-1 was registered and not implemented**
  (turnover and cost by bucket). Prediction Q5 is unscored. It belongs in the
  next campaign.
* Four G7 defects were found and fixed **before any number was reported**: CRSP
  `dlstcd` 100 means still-active (358 of 846 names); orders were re-derived
  daily against a drifting NAV, converting an annual clock to a daily one; a
  stale dollar-sized sell could open a short; and share-count marking at the raw
  close broke on splits (a **negative $49 m** dividend accrual). The spread
  estimator was also wrong — `(high−low)/2` is the intraday range, not the
  spread, and charged 200 bps; Corwin-Schultz with a half-tick floor charges 37.

## Queue, in the order I would take it

1. **`conc_low` resurrection** — the only genuinely distinct hypothesis in the
   graveyard shortlist (IC t 7.41, net t 2.31, killed by an underpowered
   screen). Registers as a NEW trial; the old test stays in the denominator.
   The other four shortlist names are the profitability family we already ship.
2. **A higher-power ordering instrument**, if ordering is to be pursued at all.
   482 months of 10-name buckets cannot see below ~10.7 %/yr.
3. **G7 arm A4** and a G7 run on the *monthly* clock, so the frontier's
   mechanical claim is verified under daily execution rather than assumed.
4. **ANALYST-LEDGER-1 first forward notes** — registered, machinery built,
   zero observations. Inception is the first note written.
5. `si_chg_low`, the 22 largemid KO re-adjudication, ISSUE-1, ML-1,
   INSTR-ERA-CAL-1, THEME-13 rerun, WORLD-8 grid.

## Standing, unchanged

Search CLOSED at 179 (148 banked rows). Denominator 821+ and rising; Bonferroni
4.01. 10 lanes forward, inception 2026-06-08, no skill claims before 24 months.
`crash_model.pkl` still broken (M3). LLM narrates, engine computes. No posterior
touches position sizes. Keys env-only.
