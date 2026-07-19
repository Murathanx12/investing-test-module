# TRIAL-BRAIN-001-baseline-clean

**Registered:** 2026-07-19 (UTC), BEFORE the clean panel cache finished building and before
any strategy return was computed on it.
**Registry row:** `TRIALS/registry.jsonl`
**Predecessor:** TRIAL-BRAIN-000 (REJECTED — surfaced the OTC data-glitch defect; its
universe was underspecified. This trial is the same frozen spec on the corrected
universe DEFINITION and counts as a new trial: cumulative n → 16.)

## Hypothesis
Identical to TRIAL-BRAIN-000: the GKX big-three families combined by a shallow GBM ranker
produce a positive, cost-surviving cross-sectional edge — now on the properly defined
universe (NYSE/NASDAQ/AMEX/NYSE ARCA/NYSE MKT/BATS common stock only, impossible returns
nulled). Mechanism unchanged: underreaction + liquidity-provision premia in the
small/limited-attention corner of the LISTED market.

## Literature prior
Unchanged from 000 (GKX 2020; main-repo momentum lane failures). Honest prior: coin-flip
at best net of 25 bps; the clean universe removes the fake upside AND the fake noise.

## Expected effect size
0–60 bps/mo excess vs eligible-universe EW; net annualized Sharpe 0.3–0.8 if real.

## Kill condition (pre-committed, same structure as 000)
- Arm A (noise) |t_excess| ≥ 3 → pipeline leak; all results void.
- Arm B net excess t < 1 → baseline REJECTED as standalone edge; published negative;
  features remain combiner inputs only.
- Arm B edge present full-universe but absent (t < 1) in largest-500 with a gap > half
  the full edge → coverage artifact, REJECTED.

## Two-arm design & run spec (frozen)
Identical to TRIAL-BRAIN-000 except the panel: `data/panel_2017_clean`
(list_clean_symbols + RET_FLOOR/RET_CAP nulling). WalkForwardConfig(min_train_months=24,
refit_every=3, top_frac=0.10, long_short=False, cost_bps_one_way=25, ranker_kind="gbm",
min_names_per_month=50). Largest-500 arms use restrict_training_to_eligible=True.
ONE run per arm. Results final. Direction-check grade (Shumway stamp, no CRSP delisting
returns until WRDS).

## Result (recorded 2026-07-19 after the single execution — final)
Ran 2026-07-19, `runs/TRIAL-BRAIN-001/results.json`, clean panel (12,419 names,
6,701 in-window deaths, ~4,500 eligible/month).

- **Arm A (noise):** net excess t = −3.68 (full) / −4.02 (largest-500). **The |t| ≥ 3
  condition fired as written.** Decomposition: GROSS excess +11 bps/mo, t = 1.19 —
  statistically zero, no leak. The entire net drift is the cost drag (1.8 traded/mo ×
  25 bps = 45 bps/mo) measured with high precision. **The control condition was
  misspecified by the experimenter**: leak detection must be stated on gross excess
  (a leak inflates gross); net excess of a random book is expected-negative by exactly
  its costs. Recorded as a specification error, not a pipeline leak. Future trials use
  gross-excess t for the leak bar (harness now reports both).
- **Arm B (full clean universe):** net Sharpe 0.179, net excess t = **−1.40** →
  kill condition 2 fires on the merits. DSR = 0.124 at n_trials = 16.
- **Arm B (largest-500):** net Sharpe 0.63, net excess t = 0.77 → nothing.
- **Verdict: REJECT.** On the clean panel the GKX big-three via shallow GBM ranker does
  NOT beat its eligible-universe EW net of 25 bps. Consistent with the stated prior and
  with the main repo's momentum-lane failures (#13, #14).

### What was actually learned (the point of a baseline)
1. **Turnover is the killer.** A monthly-refit decile book trades ~180%/month one-way →
   45 bps/mo drag swamps any 0–60 bps/mo edge. Turnover control (hold bands, slower
   rebalance, rank-persistence requirements) is a first-class design constraint for every
   future L2/L3 candidate, not an afterthought.
2. The harness is unbiased gross of costs (noise gross t ≈ 0 in both universes) and the
   clean-universe hygiene removed the fat-tail contamination (Arm B skew fell from 8.8
   to 0.24, kurtosis 78.7 → 4.1). Infrastructure validated.
3. Published negative: generic price factors alone, naively rebalanced, are dead net of
   realistic microcap costs — the corner's edge, if any, must come from EVENT signals
   (insider/PEAD/FDA) and/or turnover-aware construction. This sharpens Phase 1–2 focus.
