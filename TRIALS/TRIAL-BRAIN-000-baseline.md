# TRIAL-BRAIN-000-baseline

**Registered:** 2026-07-19 (UTC), BEFORE the panel cache finished building and before any
strategy return was computed on real data.
**Registry row:** `TRIALS/registry.jsonl` (`register_trial("TRIAL-BRAIN-000-baseline", ...)`)

## Hypothesis
The GKX "big three" families (momentum 12-1, short-term reversal, 6m volatility,
illiquidity) combined by a shallow GBM ranker produce a positive, cost-surviving
cross-sectional edge in the microcap-tilted EODHD 2017+ panel — because these are the only
signal families that survived the GKX signal zoo, and because our universe floor
($1 price, $200k/day median volume) sits in the limited-attention corner where they decay
slowest. Mechanism: underreaction + liquidity provision premia concentrated where
arbitrage capital doesn't operate.

## Literature prior
GKX (2020): NN monthly OOS R² 0.33–0.40%; momentum/liquidity/vol dominate; shallow > deep.
BUT the main repo's own TRIAL-MOM-BACKTEST #13 and #14 FAILED risk-adjusted as standalone
lanes on this very panel. Honest prior: **more likely than not this fails net of 25 bps**,
and its real purpose is validating that the harness cannot be fooled (Arm A).

## Expected effect size
Arm B: 0–60 bps/mo excess vs eligible-universe EW, annualized net Sharpe 0.3–0.8 if real.

## Expected decay / capacity
These are the most-published factors in existence; any edge here is panel-structure
(microcap tilt), not secret. Capacity ≪ $5M.

## Kill condition (pre-committed)
- Arm A (noise control) shows |t| ≥ 3 → **pipeline leak; all results void; fix before anything else.**
- Arm B net excess t-stat < 1 → baseline features REJECTED as a standalone edge; they
  remain as combiner inputs only, and the negative is published.
- Arm B edge present in full universe but absent (t < 1) in largest-500 subset AND the
  survivorship-bound gap > half the full-universe edge → treated as coverage artifact, REJECTED.

## Two-arm design
- **Arm A (expected null):** a single pure-noise feature through the identical harness/config.
- **Arm B (the claim):** the four PRICE_SIGNALS through the same harness/config.
- Both arms also run with `largest_n_by_dollar_vol=500` for the survivorship bound.

## Run spec (frozen)
- Panel: `data/panel_2017` cache, full window, min_months=13.
- Eligibility: price ≥ $1, 3m median dollar volume ≥ $200k (config defaults).
- Harness: WalkForwardConfig(min_train_months=24, refit_every=3, top_frac=0.10,
  long_short=False, cost_bps_one_way=25, ranker_kind="gbm", min_names_per_month=50).
- ONE run per arm. Results final. Gate report with cumulative n_trials (14 base + local).
- Grade: **direction check** (EODHD panel, Shumway stamp). Nothing enters paper_nav.

## Result (recorded 2026-07-19 after the single execution — final)
Ran 2026-07-19T06:33:29Z, `runs/TRIAL-BRAIN-000/results.json`, 89/81 test months.

- **Arm A (noise, full):** net Sharpe 0.374, excess t = **0.75** → below the |t| ≥ 3 leak
  bar. **No pipeline leak detected.** The harness passes its own control.
- **Arm B (GKX, full):** net Sharpe 0.429, excess t = 1.03, DSR = **0.148** at n_trials=15.
- **Arm B (largest-500):** net Sharpe 0.655 but excess vs its universe **negative**
  (t = −0.93). Edge absent in the coverage-clean subset → third kill condition fires.
- **Survivorship/coverage bound:** full-universe excess +0.295/mo vs largest-500 −0.297/mo.
- **Verdict: REJECT** (gate: DSR 0.148 < 0.95; PBO not computable; kill condition 3).

### Primary finding — the real product of this trial
The excess-return distributions (skew 8.8, kurtosis 78.7) exposed a **critical
panel-hygiene defect**: 5,938 observations with >1000% monthly returns (max 3.3×10⁹ —
SMVE 2022-02), 1,548 above 10,000%, and 21 returns ≤ −100% (impossible for real prices).
Offenders are concentrated in OTC/foreign listings (F/Y-suffix tickers). Because
"largest-500 by dollar volume" is itself computed from glitched Close×Volume, even the
survivorship arm is contaminated. **No signal conclusion beyond the leak check is
interpretable from this run.** The GKX baseline features are NOT killed as combiner
inputs — they were never fairly tested; re-testing on a hygienic panel requires a NEW
pre-registered trial (TRIAL-BRAIN-001), which counts as a new trial. This one stands as
registered and REJECTED.

### Follow-up (infrastructure, not a trial)
Panel hygiene v2: restrict the universe by EXCHANGE using the EODHD symbol-list metadata
(NYSE/NASDAQ/AMEX only — a universe definition, not result-driven data editing), null
impossible returns (≤ −100%), investigate the >200% tail against known corporate actions.
