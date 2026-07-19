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

## Result (to be filled AFTER the runs — never edited afterwards)
- Arm A:
- Arm B (full universe):
- Arm B (largest-500):
- Survivorship bound:
- Verdict:
