# Kickoff — Investor Brain session 2

Paste-ready. Workspace: `C:\Users\mrthn\Aegis module` (read ROADMAP.md + docs/SESSION_2026-07-19.md first).

## Phase 0 — Monday verifications (main repo, ~15 min, FIRST)
1. Alpaca paper mirror: did DKNG 1,897 + SLDP 22,500 fill at Monday's open?
   Check `alpaca:equity` PIT key for the first divergence snapshot.
2. Congress collector: did the 07:30 ET run pull REAL data (not false zeros)?
3. If either failed → fixing the forward clocks outranks everything below.

## Phase 1 — TRIAL-THEME-SUPPLY (the arc's main event)
Pre-register in aegis-finance `docs/TRIALS/` + registry row BEFORE any return is computed:
- PIT theme baskets from thematic-ETF launch holdings (LIT '10, ROBO '13, HACK '14,
  BOTZ '16, QTUM '18 + 3–5 more), members classified supplier/applier from
  launch-date descriptions only, frozen.
- Study A (expected loss): themes vs SPY. Study B (Murat's thesis): suppliers − appliers
  within themes.
- Compute on this module's `data/panel_2017` cache (rebuild via
  `scripts/build_panel_cache.py` if missing) + yfinance pre-2017 with survivorship bound.

## Phase 2 — Event ledger v1
LLM extracts FDA/PDUFA dates + product launches → scored falsifiable pre-event calls →
PIT store via the `forecast_ledger.py` pattern (main repo). LLM never touches allocation.

## This module's queue (Phase 3 continuation)
- Act on TRIAL-BRAIN-000's verdict per its pre-committed kill conditions (doc is final —
  do not re-run).
- Next signals to wire into L2 as collectors mature: opportunistic-insider (microcap),
  PEAD (microcap), event-drift. Each = new pre-registered trial.
- If WRDS approval lands: Phase 4 — swap L0 to CRSP/Compustat PIT, rerun at paper grade.
