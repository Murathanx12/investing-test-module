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

## Data departures (disclosed at fetch 2026-07-26, before any results)

- **HY OAS (BAMLH0A0HYM2): FRED now serves only a rolling ~3-year window**
  (787 obs from 2023-07-25; explicit `cosd` ignored — ICE licensing
  truncation). Credit features (#3, #4) therefore use the **Baa−10y
  spread (DBAA − DGS10, 1986+)** — the classic full-history credit-stress
  proxy. The truncated HY-OAS stays in the snapshot for recent-window
  cross-checks only.
- **Gold: LBMA fix series removed from FRED entirely (404)** → GC=F COMEX
  front-month futures via yfinance, 2000-08-30+. No splice needed.
- Consequence: first complete descriptor vector ≈ **2000-12** (gold 63d
  return + sector 200d-MA warmup), not ~2000-01. Spec table entries 3, 4,
  10 read as amended here; nothing else changes.

## Output (filled AFTER the build 2026-07-26)

**Built and live.** Engine `aegis_brain/macro/macro_analog.py` (7 unit
tests green), runner `scripts/run_regime_analog.py`. 6,053 complete
descriptor vectors 2002-07-03 → 2026-07-24 (disk SPY starts 2002-01, so
first complete vector is 2002-07, not the amendment's ~2000-12 estimate —
the disk-SPY constraint, not gold/sectors, binds; disclosed).
**283 belief states in `ledger/belief_states.jsonl`** (282 month-end
backfill rows stamped `backfill=true` + the current state).

**Current state (query 2026-07-24, confidence 0.811):** nearest episodes =
Oct-2018 vol spike, mid/late-2021, the 2016-18 grind. Analog frequencies
(estimates-not-forecasts): fwd-6m positive 84% (median +4.6%), fwd-12m
positive 82% (median +10.9%), fwd-12m maxDD ≤−15% in 34.7% of analogs
(≤−20%: 16.3%). Fwd-6m sector winners across analogs: XLE 14, XLK 12,
XLU 8. Most-extreme features today: gold_ret63 z −1.5 (post-rally
give-back), oil_ret63 −0.8, r10_chg63 +0.7.

**Face-validity receipts (backfilled trajectory, descriptive):**
- 2020-03-31: top episodes = GFC (2007-08→2009-04) + 2002-03 bear;
  crash15 0.42; confidence 0.60 — the library found the right shelves.
- 2021-12-31: top episodes = 2017→2020-01 melt-up + **Oct-2007** (the
  prior cycle top, one month before this one); crash15 0.36.
- 2022-09-30: top episodes = 2008-05→08 + the 2021-22 decline itself.
- Confidence correctly SAGS in stress (0.43-0.60) vs calm (0.76-0.81) —
  analog disagreement is informative.

**Disclosed limitations:** (1) pre-~2010 backfill rows draw on a shallow
candidate library (5-8 years) — episodes degenerate toward "the whole
library"; weight early-trajectory beliefs accordingly. (2) Episode
chaining is transitive (analogs ≤126td apart merge), so dense analog runs
can span years; acceptable descriptive behavior, better clustering is a
phase-2 item. (3) 2008-09-30 showed fwd6m_positive 0.72 — analog
frequencies are BASE RATES conditioned on state similarity, not
forecasts; the artifact class exists to make this distinction auditable.

**Amendments applied at round 11 (adjudicated before build):** episode
clustering (GPT retrieve→cluster→explain) + agreement-based confidence
(GPT uncertainty proposal). Deferred to phase 2 as registered: Bayesian
updating, failed-thesis scoring (PDUFA-ledger pattern), evidence graphs,
insider-flow feature.

---

## Diagnostics D1–D4 (2026-07-29) — run per FABLE_HANDOFF_2026-07-29, kill lines pre-committed in that doc (aegis-finance @ da6b22d, committed before any run)

Full reports: `docs/DIAG_D1_D2_2026-07-29.md`, `docs/DIAG_D3_2026-07-29.md`
(504-td deciding run; `_exc63` companion), independently verified by an
adversarial recompute of every deciding number (all confirmed; report-prose
defects found and corrected inline).

- **D1 analog age — kill line (>40% of analogs within 12mo) DID NOT FIRE:**
  10.78% ≤12m pooled, median analog age 4.93y. The red team's distance-doubling
  did not reproduce at the real spec (1.13×, not 2.06×); 63-td vs 504-td analog
  sets Jaccard 0.676.
- **D2 effective dimension — kill line (D_A(90%)≥5) FIRED: D_A(90%)=9** (robust
  across six estimator variants). But the prescribed remedy fails on
  measurement: 2–3-PC retrieval changes ~80–87% of analogs while moving
  state_probs by only 0.02–0.05 — because the published beliefs sit within
  0.06–0.13 of unconditional base rates. **Retrieval is close to a no-op on the
  output**; the deciding question was never dimension, it was resolution.
- **D3 causal scoring (504-td: standardization AND outcome aggregation causal)
  vs PERSISTENCE:** fwd6m_positive BEATS (DM t_NW −2.31 / boot −2.20, N_eff
  54.9) — but 87.6% of the win is ΔREL (hedging vs a 0/1 baseline);
  fwd12m/dd15/dd20 INCONCLUSIVE. **REL_eng > RES_eng on all four outcomes: a
  constant forecast at the base rate scores a strictly better Brier than the
  engine everywhere** (+0.031/+0.044/+0.095/+0.040). Full-sample-z
  contamination was real but not load-bearing (no verdict changed). The 63-td
  run's dd15/dd20 "wins" were carried by the outcome-aggregation leak.
- **D4 confidence channel:** Pearson corr(distance, |error|) 0.104/0.063
  (return-sign — under the 0.15 kill line) vs 0.204/0.259 (crash outcomes).
  Spearman flips the first two; no monotone confidence→resolution pattern.
  UNRESOLVED — not settled either way.
- **Engine defects found:** (1) `retrieve_analogs` guards candidate count, not
  acceptance count under NMS — 56/283 shipped states (2003–2007) and 59/239
  causal states (2006-09→2011-08, the whole GFC block) silently used <50
  analogs (min 3–4). Any successor must guard and disclose `n_analogs_used`.
  (2) One duplicate ledger row (2026-07-24).

**Consequence (binding on phase 2):** phase 2 as designed (allocation layer on
these belief states) is NOT supported — the states are hedged base-rate
emitters with weak, statistically unconfirmed resolution. The engine stays
live as descriptive narration only (its registered role; it never armed). Any
successor engine is a NEW walled registration and must fix acceptance-count
disclosure, use causal standardization from birth, score vs persistence with
the D3 harness, and demonstrate resolution before any allocation use. The
fwd12m horizon (RES/UNC 29.3%) is where a successor should look first.
