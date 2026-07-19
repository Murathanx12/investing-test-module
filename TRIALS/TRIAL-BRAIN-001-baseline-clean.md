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

## Result (to be filled AFTER the run — never edited afterwards)
- Arm A:
- Arm B (full clean universe):
- Arm B (largest-500):
- Survivorship bound:
- Verdict:
