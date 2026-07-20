# TRIAL-BRAIN-002-crsp-holdband

**Registered:** 2026-07-20 (UTC) — BEFORE the CRSP panel was ever fetched (the WRDS
account was literally still in login cool-down when this spec was frozen). No CRSP
return has been seen by the experimenter or any code in this repo.
**Registry row:** `TRIALS/registry.jsonl` (cumulative n → 17)

## Hypothesis
On survivorship-free CRSP 2002→2024 (real delisting returns), the GKX big-three families
combined by a shallow GBM ranker, held with a turnover band (buy top decile, keep while
in top 30%), produce positive net-of-cost excess vs the eligible-universe EW. Mechanism:
same as BRAIN-000/001 (underreaction + liquidity premia strongest in small/limited-
attention names) — now with the two defects fixed that made 001 unreadable: turnover
drag (hold band cuts trading ~2-4x) and universe hygiene (CRSP-canonical).

## Literature prior
GKX 2020 equal-weighted long-short NN decile Sharpe 2.45 leans on exactly this small-cap
corner but GROSS; net-of-cost survivability is the open question. Momentum standalone
failed in the main repo (#13/#14). Honest prior: **modest positive gross edge is likely
(it's the most replicated result in the field), net-of-25bps survival is genuinely open
— maybe 40/60 against.**

## Expected effect size
Arm B full universe: +10 to +50 bps/mo net excess; net Sharpe 0.4–0.9 if real.

## Expected decay / capacity
Published factors; expect the 2002–2024 walk-forward to show weakening in the later
third (post-2015). Capacity ≪ $5M in the microcap tail.

## Kill conditions (pre-committed)
1. Arm A (noise) **GROSS** excess |t| ≥ 3 → pipeline leak, all results void.
2. Arm B net excess t < 1 (full universe, whole window) → REJECT; published negative;
   price factors permanently demoted to combiner-input-only status in this project.
3. Arm B edge entirely absent (net excess t < 0.5) in the post-2015 sub-window →
   flagged "decayed — do not promote" even if the full-window t clears 1.

## Arms & run spec (frozen)
- Panel: `data/crsp_panel_2002` (crsp.msf ∩ msenames shrcd 10/11 exchcd 1/2/3, msedelist
  dlret compounded, Shumway fill only where dlret missing), window 2002-01 → panel end.
- Eligibility: price ≥ $1, daily-equivalent dollar volume ≥ $200k (config defaults).
- Arm A: single noise feature. Arm B: the four PRICE_SIGNALS. Both also at
  largest_n_by_dollar_vol=500 with restrict_training_to_eligible=True (capacity/robustness
  read — CRSP makes it a size split, no longer a survivorship bound).
- WalkForwardConfig(min_train_months=60, refit_every=3, top_frac=0.10,
  hold_band_frac=0.30, long_short=False, cost_bps_one_way=25, ranker_kind="gbm",
  min_names_per_month=50).
- ONE run per arm. Results final. Gate: DSR vs cumulative n=17, PBO where computable.
- Grade: **paper-grade backtest** (first in the project). Still not a forward result —
  promotion still requires the main-repo forward clocks.

## Result (to be filled AFTER the run — never edited afterwards)
- Arm A (gross leak check):
- Arm B full:
- Arm B largest-500:
- Post-2015 sub-window:
- Verdict:
