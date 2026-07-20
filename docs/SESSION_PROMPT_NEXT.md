# Kickoff — Investor Brain (next session)

Read `STATUS.md` first (one-screen state), then this. Workspace:
`C:\Users\mrthn\Aegis module`. Repo: github.com/Murathanx12/investing-test-module.

## If WRDS is re-enabled → do this FIRST (the whole critical path, one sequence)
1. HKU VPN on.
2. `.venv\Scripts\python -m scripts.build_crsp_panel`  (~2.6M rows → data/crsp_panel_2002)
3. Back up `data/crsp_panel_2002` to `OneDrive\AegisBackups`.
4. `.venv\Scripts\python -m scripts.run_trial_002`  — ONE run, record result in
   `TRIALS/TRIAL-BRAIN-002-crsp-holdband.md` as final (never edit after).
5. If Arm B survives its kill conditions → design the main-repo forward-trial promotion;
   if not → publish the negative. Either way, commit + push.
- Connect to WRDS ONLY via `aegis_brain.data.wrds_conn.get_connection()`. Never bare
  `wrds.Connection()` non-interactively (it floods failed logins → the 07-20 lockout).

## If WRDS still blocked → buildable now (no WRDS)
- **Insider Form-4 collector** (SEC EDGAR is public): opportunistic-vs-routine buys,
  microcap-tilted — the strongest documented edge in the roadmap. New pre-registered trial.
- **LLM narrative spike** (L1b): extract between-the-lines signal from FDA/EDGAR text →
  probabilistic calls into the event ledger (`events/ledger.py` is ready and tested).
- **FDA→ticker bridge** (provisional, non-PIT, clearly flagged): lets an event-drift
  study run at direction-check grade on the harvested 2,742 NDA/BLA events.

## Main repo (separate, if asked)
- Phase 0 Monday verifications: Alpaca DKNG/SLDP fills, congress collector 07:30 ET.
- Phase 1 TRIAL-THEME-SUPPLY (suppliers-vs-appliers) — the arc's headline study.

## Hard rules (unchanged)
Pre-register before data · one run per hypothesis · two-arm (leak control on GROSS
excess) · deflated numbers only · LLM never allocates · never write into aegis-finance.
