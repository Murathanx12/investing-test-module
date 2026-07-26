# INSTR-REGIME-ANALOG — phase 1: descriptive belief engine (frozen BEFORE build)

**Registered:** 2026-07-26 (UTC). **Class:** DESCRIPTIVE instrument — never
arms, no kill condition, no graduation path. Adopted as design spec at
panel round 10 (`aegis-finance docs/research/AI_PANEL_2026-07-26D.md`),
amended round 11 (episode clustering + agreement-based confidence, GPT
suggestions adjudicated). Engine `aegis_brain/macro/macro_analog.py`;
runner `scripts/run_regime_analog.py`. Prior-check transcript: 114 hits
reviewed 2026-07-26; all hits are the adoption/queue entries themselves.

## What it is / is not

State estimation, not prediction: the engine answers "which historical
periods most resemble today" and reports what happened AFTER those periods
as *distributions*. It never allocates, never signals, never arms.

## ⚠️ Contamination declaration (binding on all successors)

The engine reads the FULL history (including 2019+) — permissible because
it makes no allocative claim. Consequence, declared now: **any future
allocation rule derived from analog output inherits post-hoc provenance**
(designed after seeing the full history). Such a rule's explore evidence is
~zero-weight by construction; it must be pre-registered as its own walled
trial and leans on confirm+forward, exactly like JM2. The wall is not
retroactively laundered by putting a k-NN in front of it.

## Spec (frozen)

**Descriptor vector** (daily, ffill ≤5d, features start where data exists;
first complete vector expected ≈2000 after the 200d-MA warmup):

| # | feature | source |
|---|---|---|
| 1 | ln(VIX) | FRED VIXCLS |
| 2 | 21d change in ln(VIX) | FRED VIXCLS |
| 3 | HY OAS level | FRED BAMLH0A0HYM2 |
| 4 | HY OAS 63d change | FRED BAMLH0A0HYM2 |
| 5 | 10y−2y slope | FRED DGS10−DGS2 |
| 6 | 10y yield 63d change | FRED DGS10 |
| 7 | rate vol: 21d sd of daily Δ DGS10 (MOVE proxy) | FRED DGS10 |
| 8 | dollar 63d return (DTWEXM spliced to DTWEXBGS at 2019-12, ratio splice, disclosed) | FRED |
| 9 | oil 63d return | FRED DCOILWTICO |
| 10 | gold 63d return (FRED London fix; spliced to GLD if the fix series ends, disclosed) | FRED/disk |
| 11 | SPY 126d return | disk ETF parquet |
| 12 | SPY 21d realized vol | disk ETF parquet |
| 13 | sector dispersion: cross-sector sd of 63d returns | yfinance XLK/XLE/XLF/XLV/XLI/XLP/XLU/XLY/XLB |
| 14 | defensive RS: mean 63d ret (XLP,XLU,XLV) − (XLK,XLY,XLI) | same |
| 15 | breadth: share of the 9 sector ETFs above own 200d MA | same |

Insider flow (round-10 spec listed it): DEFERRED to phase 2 — panel data
starts 2006 and would cost 6 years of analog history; disclosed departure
from the adopted list.

**Standardization:** full-sample robust z (median/IQR) — descriptive-only
convenience, declared; any walled successor must recompute causally.

**Retrieval (deterministic, no fitted parameters):** query date q (default:
latest complete vector) → Euclidean distance in standardized feature space
to every day t ≤ q−63 (63-trading-day self-exclusion) → accept nearest
first with 21-trading-day non-max suppression around each accepted analog →
50 distinct analog days.

**Episodes (round-11 amendment):** accepted analogs within 126 trading
days of each other merge into an episode {date span, n analogs, mean
similarity}; report episodes, not a flat day list — PMs reason in
episodes ("2011 debt-ceiling stress"), not dates.

**Forward distributions from each analog date:** SPY total return at
3/6/12/24m (63/126/252/504 td); max drawdown within 12m; sector winner =
top sector ETF by fwd-6m return (from sector-ETF availability 1999+);
crash frequency = share of analogs with fwd-12m maxDD ≤ −15% and ≤ −20%.
Right-edge truncation: n reported per horizon, never imputed.

**BeliefState artifact (new class beside trials):**
`{query_date, run_timestamp, state_probs (fwd6m_positive, fwd12m_positive,
crash12m_dd15, crash12m_dd20 — analog frequencies, labeled estimates-not-
forecasts), confidence, evidence, engine_version}` appended to
`ledger/belief_states.jsonl` (gitignored data? NO — the ledger is the
tamper-evident record, committed). Confidence (frozen formula) =
sign-agreement of analog fwd-6m returns × (1 − mean analog distance
percentile). Evidence = today's top-5 most extreme features (|z|) +
per-episode 3 closest-matching features. **Trajectories:** the runner
supports month-end backfill so belief evolution 2000→present exists from
day one; a backfilled state is stamped `backfill=true`.

**LLM narrates; deterministic engine computes; nothing allocates.**
Phase 2 (separate future registrations, not licensed by this doc):
Bayesian prior→posterior updating, failed-thesis scoring of past beliefs
against realized outcomes (PDUFA-ledger pattern), evidence graphs,
insider-flow feature.

## Output (filled AFTER the build — engine outputs land in
`data/factory/regime_analog_*.json` + `ledger/belief_states.jsonl`)
