# Kickoff — Investor Brain (next session)

Read `STATUS.md` first (one-screen state), then this. Workspace:
`C:\Users\mrthn\Aegis module`. Repo: github.com/Murathanx12/investing-test-module.

## State (2026-07-21 PM): v1.0 shipped AND adopted

The signal battery is complete (BRAIN-000..005 final, 007 not-run) and the one
survivor is PROMOTED: TRIAL-CMP-INSIDER-IC runs live in aegis-finance
(`insider_cmp:` forward clock, earliest decision 2027-07-21). The module's job
now shifts from building to (a) feeding the forward ledger and (b) hunting a
second survivor so BRAIN-007 fusion re-opens.

## Standing duties (calendar-driven, cheap, non-negotiable)

1. **Score the PDUFA ledger as calls mature.** 7 pre-registered calls, first
   event 2026-07-26 (SCPH) → scoreable ~21 trading days later (~late Aug).
   `.venv\Scripts\python -m scripts.ledger_score` — then register the NEXT
   batch of event calls (the calibration record is the product; it compounds
   only if fed).
2. **Quarterly artifact refresh** (next ~Oct 2026 when SEC publishes 2026Q2):
   `download_insider` → `build_insider_panel` → `export_routine_history`, then
   re-commit `cmp_routine_history.json.gz` into aegis-finance/backend/data/.
   Artifact >210d stale = every live score flags degraded (loud by design).

## The next research arcs (each a new pre-registered trial, one run each)

- **TRIAL-THEME-SUPPLY** — Murat's suppliers-vs-appliers thesis, the arc's
  headline study, still unrun. Now runnable at PAPER GRADE on the CRSP panel
  (better than the original EODHD plan). Two-arm: themes-vs-SPY (expected-loss
  arm) + suppliers-minus-appliers (the open question).
- **FDA event-drift** — sponsor→ticker PIT mapping is now buildable offline
  (CCM link + IBES cusip in data/wrds_raw); 2,742 NDA/BLA events harvested.
- **Low-turnover quality/size** (PLAN_B rung 2) — the Novy-Marx-Velikov class
  of net-of-cost survivors; less romantic, clears costs.
- Any second survivor re-opens **BRAIN-007 fusion** (weights pre-registered
  BEFORE seeing the singles — the doc is already written).

## Deferred hygiene (from AUDIT_2026-07-21)

M6 purged-CV post-test embargo < label horizon (fix BEFORE any crash/forward-
window label uses PurgedKFold) · generic-runner M4 NaN-renormalize port ·
sr_variance batch estimate · L8-L13 low-severity items.

## Hard rules (unchanged)

Pre-register before data · one run per hypothesis · two-arm with a leak bar ·
deflated numbers only · LLM never allocates · never write into aegis-finance
(promotion = human-reviewed bundle commit, as executed 2026-07-21).
