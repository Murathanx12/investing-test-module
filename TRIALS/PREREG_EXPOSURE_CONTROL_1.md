# PREREG — EXPOSURE-CONTROL-1: a book-keyed exposure ladder, calibrated on six drawdowns, judged on the one it was built for

**Registered** 2026-08-11, NIGHT-13, **before any managed path is computed.**
**Family** de-risking overlay (allocation layer), S3 door — same registry, same
cumulative deflation count. **Parent** EXPOSURE-CONTROLLER-V0
(`aegis-finance/docs/conviction_replay/exposure_controller_v0.json` — the
market-keyed controller that correctly never fired) and CONVICTION-REPLAY-1's
capture measurement (book beta 2.15, vol 40.4%, maxDD −22.87% vs SPY −8.89%).

**This trial ACCRUES ONE ARM.** It can promote a policy to a shadow-book
default, so it counts.

Resurrects: TRIAL-COND-VT — new instrument: the rule is keyed to the BOOK's own
realized volatility, beta and drawdown path on a DAILY decision clock, not to
the index on a month-end clock. COND-VT's own post-mortem states the failure:
"a 63-day backward window cannot resolve a 23-day crash and a month-end clock
cannot act inside one." NIGHT-12 then measured the object-level gap: in the war
weeks SPY fell −4.49% while the book fell −22.87% — an index-keyed controller
was blind BY CONSTRUCTION for a beta-2.15 concentrated book. The conditional-VT
family (index-keyed, extremes-only, SPY) stays CLOSED; nothing here reopens it.

---

## 1. Hypothesis

For a concentrated high-beta book (β ≈ 2.15, ann. vol ≈ 40%), a mechanical
exposure ladder keyed to the book's own path —

- **vol target:** `w_vol = min(1, σ* / σ_book(63d))`
- **beta budget:** `w_beta = min(1, β* / β_book(63d vs SPY))` (β* frozen at 1.5,
  NOT tuned — on the levered-market calibration proxy realized beta is
  constant, so tuning it there would be degenerate; it is a prior, stated)
- **drawdown ladder:** if book drawdown-from-peak < −D*, exposure is
  additionally capped at 0.5 until drawdown recovers above −(D*−5pp)
  (pre-specified hysteresis re-entry) with a 10-trading-day minimum dwell
- combined `w_t = min(w_vol, w_beta, w_dd_cap)`, leverage cap 1.0, cash earns 0,
  **daily clock, applied with a one-day lag** (`ExposurePolicy` re-entry
  invariant inherited: the re-entry threshold is strictly inside the exit
  threshold, enforced at construction)

— reduces episode max drawdown **materially (≥5pp)** without giving up a
disqualifying share of terminal wealth. Exit and re-entry are ONE rule; the
"buy back in the dip" half is the hysteresis, not a forecast.

**Honest prior: LOW-MEDIUM.** The nearest relative with a receipt (COND-VT)
passed explore and failed confirm. The mechanism here is different (a 40%-vol
book reaches its vol/dd triggers far faster than SPY reaches its own), but the
literature graveyard on vol timing is deep, and n=1 on the held-out episode.

## 2. Data and windows, frozen

- **Calibration bed (proxy, disclosed):** daily levered-market path
  `r_book = 2.15 · mktrf + rf` from
  `data/wrds_raw/ff_factors_daily.parquet` (1926-07-01 → 2026-05-29).
  The proxy carries the right vol and beta but NOT idiosyncratic gap risk
  (biotech binaries) — disclosed limitation, stated in the verdict.
- **Calibration episodes (six, each = 252td burn-in + peak→trough + 12mo
  recovery):** 1973-74, 1987, 2000-02, 2007-09, 2020, 2022. Episode boundaries
  taken from the market path's own peak/trough dates, not hand-set.
- **Held-out test (real book, ONE evaluation, after parameters freeze):**
  the equal-weighted conviction book from
  `aegis-finance/backend/data/conviction_prices.csv`
  (2025-11-07 → 2026-08-10, synthetic names APLT/SLNO excluded from daily
  stats), with the war episode boundaries 2026-06-04 → 2026-07-29 reported
  separately inside the full window. Realized book beta for `w_beta` uses a
  63-day rolling window vs SPY. **The war episode is tuned on by NOTHING.**

## 3. Calibration protocol, frozen before any run

Grid (registered in full, nothing added later):
`σ* ∈ {0.15, 0.20, 0.25}` × `D* ∈ {10pp, 15pp, 20pp}` = 9 candidates.
β* = 1.5 fixed. Dwell = 10td fixed. Lag = 1td fixed. Costs: **10 bps one-way
base** (decides), 50 bps stress (reported — the real book is small-cap).

**Selection criterion (frozen):** among candidates achieving maxDD reduction
≥ 5pp in ≥ 4/6 episodes, pick the one with the highest mean episode terminal
wealth ratio (managed/unmanaged); ties → lowest turnover. If NO candidate
achieves the coverage condition, the trial reports that and stops —
**the holdout is not opened.**

## 4. Decision rule, frozen

| outcome | verdict |
|---|---|
| calibration coverage met AND held-out war episode: managed book maxDD shallower by ≥5pp net of base costs AND terminal wealth ratio ≥ 0.85 over the full holdout window | `ADOPT_AS_SHADOW_DEFAULT` — the policy becomes an `ACTIVE_DEFAULT` label on paper/shadow books only; **nothing arms, no lane seeds, no order path** (signal_registry.yaml:486 discipline) |
| calibration met, war episode dd reduction < 5pp or in the wrong direction | `UNRESOLVED` — one episode cannot kill a rule calibrated elsewhere; policy shelved, NOT defaulted |
| calibration coverage NOT met | `CALIBRATION_FAILED` — reported, holdout unopened |
| any episode where the managed proxy's terminal wealth ratio < 0.60 | `REJECT` regardless of drawdown numbers — the cure costs more than the disease |

**§19:** every dd/wealth/turnover number prints beside a measured MDE
(block-bootstrap, 21td circular, planted-effect power at 80%); per-episode
numbers are descriptive receipts, n=1 each, and say so. **§18:** any
"managed beats unmanaged" claim is the paired difference on the same path with
its own SE. **Causality guard:** the runner must reproduce COND-VT's
perturbation proof — the weight at a named date is bit-identical after
perturbing all later data; failure aborts.

## 5. What this may NOT do

- No crash prediction claim, no alpha claim, no Sharpe headline. The claim is
  path-risk shaping, priced in forgone terminal wealth.
- It may not be tuned on, or evaluated against, the war episode during
  calibration — the holdout opens once, after the grid choice is committed in
  the output artifact.
- It does not reopen TRIAL-COND-VT (index-keyed timing stays closed).
- `ADOPT_AS_SHADOW_DEFAULT` labels paper/shadow evaluation only. Seeding any
  lane remains Murat's attended decision (`seed-a-lane`). No skill claims
  before 24 months of forward record.

## 6. Controls

- **Unmanaged book** — the yardstick every number is paired against.
- **Index-keyed corpse as control:** EXPOSURE-CONTROLLER-V0's policy run on the
  same episodes — it should fire rarely/never on the proxy episodes' index leg
  while the book-keyed rule fires; if the corpse fires just as well, the
  book-keying added nothing and the verdict says so.
- **Constant-exposure control:** the static exposure w̄ equal to the managed
  path's own mean exposure, same costs — separates "timing the ladder" from
  "just holding less" (§16-adjacent; the ladder must beat its own average
  exposure held statically on drawdown at comparable wealth, else the finding
  is "hold less", which is cheaper).

## 7. Result

Filled after the run, never edited. Receipts to
`aegis-finance/docs/NIGHT13_EXPOSURE_CONTROL.md`.
