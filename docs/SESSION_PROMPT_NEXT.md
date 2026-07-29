# Kickoff — next session (written 2026-07-29, post-diagnostics)

Run `/go` first (Optimus MCP tools load verified state; confirm the deploy
commit and `nav.all_fresh`). Then read `STATUS.md` top entries and
`aegis-finance/docs/research/ROADMAP_2026-07-29_POST_FREEZE.md`. Workspaces:
`C:\Users\mrthn\aegis-finance` (product/prod), `C:\Users\mrthn\Aegis module`
(research), `C:\Users\mrthn\optimus` (context layer).

## Where the program stands (one paragraph)

Freeze holds at **159 cumulative trials**. The belief engine failed its
diagnostics (hedged base-rate emitter; phase 2 BLOCKED; descriptive-only).
Conditional VT rejected at confirm (family closed, NEG_RESULTS §21) — third
allocation instrument killed by the wall. The open frontier: **the paper**,
**the product's descriptive news surface**, the running forward clocks, and
(only as a new walled registration, research-round first) a successor belief
engine. Panel rounds are MANUAL: Murat pastes external reviews; the session
adjudicates into `AI_PANEL_<date>.md` with receipts.

## First: verify the Optimus restart (2 minutes, this session)

The brain_query fixes (floor 20.0 + abstention + domain scoping, optimus
`831cffe`) go live when the MCP server respawns. Verify live: a garbage query
must return `no_match`; "freeze 158 candidates" must hit `aegis-module`
material, no robotics. If the session still runs old code, tell Murat to
`/mcp` reconnect.

## Priority A (build session — Fable): EVENT-INTEL, the descriptive news brain

The adopted next product build (AI_PANEL_2026-07-29 §ADOPTED): upgrade news
from "headlines + summary" to **structured events with honest context** —
Murat's core product goal (news arrives → what it may mean), descriptive-only.

- Extractor service: input = existing feeds (news_intelligence/GDELT, EDGAR
  8-K, earnings calendar); output = typed events {scope (ticker/sector/macro),
  event_type (earnings/guidance/FDA-regulatory/M&A/macro-print/geopolitical),
  direction/magnitude, source+timestamp, confidence}. LLM extraction through
  the existing spend-guarded DeepSeek path with a deterministic keyword
  fallback; LLM never invents numbers — extraction only.
- Context card per event: attach ONLY measured descriptive context that
  already exists (e.g., screener stats, options surface, earnings history);
  where no measured base rate exists, the card says so explicitly. No
  buy/sell language anywhere (Brier gate never passed — A4/Goal 5).
- Surface: stock page + daily brief. Cache-honest, budget-honest.
- Discipline: silent-fragility-audit after building (the GDELT
  fabricated-calm lesson: failed feed → disclosed unavailable); offline
  tests in the fast suite; verify-prod-after-deploy exercising the CHANGED
  surface with a cache-busting request.
- Hard line: the moment any event output feeds an allocation, it needs
  pre-registration. Until then it never arms anything.

## Priority B (research session — Opus, `/model opus`): PAPER-1 skeleton

Assemble the paper draft from receipts (verify every number against the repo;
respect the do-not-cite list in FABLE_HANDOFF §6):
- Method: pre-registration + prior_check, explore/confirm wall, deflation vs
  cumulative count, KO cost model, and the **D3 scoring protocol** (persistence
  baseline never climatology; DM on Brier differences; N_eff; Murphy
  REL/RES/UNC — resolution is the payable part).
- Exhibits: the 159-trial graveyard; empty cost-killed cohort; contrarian-t
  (CZ-CALIB rank corr −0.544); the belief-engine null (D1–D4, verified);
  the conditional-VT held-out refutation (first long-only no-leverage SPY vol
  target with post-2010 held-out, named mechanism); TSMOM-XA as the lone
  confirmed survivor (defensive, not beat-SPY).

## Standing duties / attended (Murat)

- PDUFA ledger: first calls scoreable ~late Aug (`scripts.ledger_score`).
- Quarterly artifact refresh ~Oct 2026 (insider panel + routine history).
- Unset stale `AEGIS_SEED_*` flags on Railway.
- Conviction lane: keep logging real decisions (only forward test of
  stock-picking judgment).

## Do NOT

Reopen the cross-sectional search (freeze; ceiling re-check only legitimate
at ~196 with real hypotheses). Rebuild dead-list items (continuous OR
conditional VT, knowledge graphs, LLM-as-historical-predictor, vector-DB swap,
phase-randomised controls). Register anything without prior_check +
pre-registration. Arm anything from descriptive surfaces. Claim skill before
24 months. Touch `paper_nav` write paths without lane-integrity-check.
