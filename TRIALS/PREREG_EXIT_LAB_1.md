# PREREG — EXIT-LAB-1: does any position-MANAGEMENT action beat holding, once the null gets a real denominator?

**Registered** 2026-08-12, GRAND-ARENA-1 PHASE 5+6, **before any state-action
row is generated.** **Family** position management / exit policy (disposition
of an already-held name), not selection. **Grade** simulated direction check on
CRSP daily 2002-2024. **ACCRUES ZERO ARMS** — nothing here can seed, arm, size
or default anything on any lane, shadow or live.

**Provenance.** Four independent measurements in this programme now point the
same way: the edge is in selection, the losses are in management and sizing.
NIGHT-12 found `sell_to_cash` was **never best in 60 rows** — but 60 rows from
ONE portfolio is not a denominator, it is an anecdote. NIGHT-13's
FACTORIAL-PM-1 measured management costing −20.5/−21.0 points on one bull
window. NIGHT-14's WINNER-GENOME-1 found selection below resolution at every
position budget while the budget itself dominated. This trial supplies the
missing denominator: **millions** of counterfactual position-state decisions
across ~11,000 securities and 23 years, and it is explicitly allowed to
**overturn** the cash null.

---

## 0. Corpse check

Run before writing §1 and re-run before commit:
`python scripts/lint_prereg.py TRIALS/PREREG_EXIT_LAB_1.md`.

**Resurrects, and why the instrument is new.**

- **TRIAL-COND-VT / EXPOSURE-CONTROL-1 (conditional vol-target, exposure
  ladders).** Those asked whether a *portfolio-level timing rule* improves ONE
  realised path (n = 1 book, n = 1 war). Nothing here is a portfolio-level
  timing rule and nothing here has n = 1. The unit is a **position-state** — one
  held name at one date with its own entry, its own unrealised P&L, its own
  drawdown-from-peak — and the estimand is the paired difference between two
  *dispositions of that same dollar*. A timing verdict on one path cannot answer
  a conditional question about position disposition, and the reverse is also
  true: no result here reopens the conditional-vol-target family.
- **NIGHT-7 trailing stop (−3.08%/yr under G7, CANON §15).** The trailing stop
  appears here **as a declared CONTROL, not as a candidate.** It is a known
  corpse. If it wins, that is a finding about the instrument, not a
  resurrection of the rule.
- **WINNER-GENOME-1.** That trial forms a portfolio on day 0 and holds or
  rebalances to fixed weights. It explicitly recorded (its §8.2) that it
  "structurally cannot measure execution". This trial measures exactly the thing
  WG1 said it could not see, on the same CRSP daily spine and the same delisting
  machinery. It is the complement, not a repeat.
- **The graveyard's selection families are NOT touched.** No hypothesis here is
  about which names to buy. `REPLACE` arms exist only to price the *opportunity
  cost of cash*, and their candidate ranking is a declared, unfitted proxy
  (§4), never an outcome-selected one.

---

## 1. Hypotheses

**H1 — the cash null, given its denominator (the deciding one).**
Over the full state population, `SELL→CASH` does not produce a higher mean net
sleeve return than `HOLD` at any evaluated horizon by more than that
difference's own 80%-power MDE. *Directional prior: HIGH that HOLD ≥ CASH
unconditionally (the equity risk premium alone predicts it); the informative
question is whether any CONDITIONING state flips it.*

**H2 — the conditional flip.** There exists at least one pre-declared state
partition (§6, the five questions) in which a non-HOLD action's paired
advantage over HOLD exceeds its own MDE, with a consistent sign across ≥5 of 8
regime blocks and both sample halves.

**H3 — replacement dominates cash.** `REPLACE→candidate` beats `SELL→CASH` by
more than its MDE, AND beats `REPLACE→random` by more than its MDE. The second
clause is the one that matters: without it, any replacement advantage is just
"being invested", which is H1 restated.

**H4 — learning adds nothing over the best simple rule.** A fitted action-value
model, evaluated ONLY on purged embargoed out-of-fold data, does not beat the
best pre-declared baseline policy by more than the MDE of that difference.
*Honest prior: HIGH for H4 (i.e. we expect the learner to fail), because every
prior night in this programme that fitted a ranker earned less than it ordered
(NIGHT-8).*

---

## 2. Unit of observation, and the sampling unit

- A **position-state** is `(permno, decision date T0, entry cohort E)` — a name
  eligible at T0 that a book is assumed to have bought E trading days earlier.
- The **sampling unit for every inferential statement is the DECISION DATE**
  (n ≈ 276 month-ends), never the position. Positions inside one month share a
  market factor; counting them as independent manufactures significance. Stated
  before any number exists.
- **MDE = 2.80 × max(Newey-West, IID) SE** of the paired per-date difference,
  per CANON §19. Below its MDE is NOT DETECTABLE and is **never** reported as a
  kill.

## 3. The action space (all ten branches priced on the same dollar)

The sleeve is **1 dollar currently sitting in the position**. Every action is a
disposition of that dollar, so all ten are directly comparable.

| action | disposition over the horizon | traded fraction |
|---|---|---|
| `HOLD` | 1.0 in the name | 0.00 |
| `ADD_50` | 1.5 in the name, −0.5 funded by selling benchmark | 0.50 |
| `TRIM_10` | 0.9 in the name, 0.1 to cash at rf | 0.10 |
| `TRIM_25` | 0.75 / 0.25 cash | 0.25 |
| `TRIM_50` | 0.50 / 0.50 cash | 0.50 |
| `SELL_CASH` | 1.0 to cash at rf | 1.00 |
| `SELL_BENCH` | 1.0 to the market portfolio | 1.00 |
| `REPLACE_1` | 1.0 into the top-ranked PIT candidate | 2.00 (round trip) |
| `REPLACE_2` | 1.0 into the 2nd-ranked PIT candidate | 2.00 |
| `REDUCE_BETA` | `f = clip(1.0 / beta_i, 0, 1)` in the name, rest to cash | `1 − f` |
| `REPLACE_RND` | **control.** 1.0 into a uniformly random eligible name | 2.00 |

`REPLACE_RND` is declared here as a required control, not an eleventh
candidate: it is what separates "the ranker is good" from "being invested beats
cash".

### §3a — AMENDMENT, 2026-08-12, before any row was generated

A one-date smoke run (no outcome statistic computed, no comparison made) showed
the literal single-name reading of "best current candidate" is **degenerate as
an instrument**: with one candidate per date and the decision date as the
sampling unit (§2), the entire date's replacement outcome is one name's
outcome, so every replacement verdict would be UNRESOLVED by construction
rather than by evidence. The replacement arms are therefore run at **three
concentrations** — 1 name (`REPLACE_1N`, the literal reading, kept), 5 names,
and 20 names — each with its own equally-concentrated random control
(`REPLACE_RND`, `REPLACE_RNDW`). The action count goes from 11 to 16. **No
outcome was inspected before this amendment**; it is a power decision, and the
concentration dependence it creates is itself reported rather than chosen.
Additionally, the IBES target-upside **feature** (never an outcome) is
winsorised to [−95%, +500%] and the clip count reported: a mid-month `statpers`
ratioed against a month-end price straddles any split in between and prints
upside in the thousands of percent.

## 4. What is PIT and what is a declared proxy

- Prices, returns, volume, market cap, delisting: CRSP daily, strictly ≤ T0.
- **Costs are the repo's existing model, not a new one**: Corwin-Schultz
  high-low half-spread (21-day rolling median, capped 300 bps, floored at the
  half-tick $0.005/price) + 5 bps slippage + 1 bp commission, exactly as
  `aegis_brain/pf/daily_sim.py` charges. Charged on the traded fraction of each
  action at T0 only.
- **The candidate ranking is a DECLARED PROXY, and is named as one.** There is
  no oracle "best current candidate" that is not a look-ahead. The proxy is
  **12-1 momentum rank within the same eligible universe at T0** — chosen a
  priori because it is the single most-documented PIT cross-sectional ordering
  and needs no parameter search. A second ranker (`REV`: the NIGHT-11 revision
  panel score) is run as a robustness arm. Neither is claimed to be the best
  available candidate; both are labelled proxies throughout.
- Analyst target upside, IBES revisions, SUE/earnings dates enter as **state
  features and baseline-rule inputs** with their own availability lags, never
  as outcomes.

## 5. Primary metric and decision rule

- **Primary horizon: 60 trading days.** Declared now. 1/5/20/120/252 are
  reported and never deciding.
- **Primary metric:** mean over decision dates of (per-date mean net sleeve
  return of policy P) − (same for `HOLD`), in percentage points.
- **Decision rule:** a policy is *detectable* only if |Δ| > its own MDE. A
  detectable positive Δ additionally requires sign consistency in ≥5 of 8
  pre-declared regime blocks (2002-03, 2004-06, 2007-09, 2010-12, 2013-15,
  2016-18, 2019-21, 2022-24) and in both sample halves to be called
  DIRECTION_SUPPORTED. Anything else is UNRESOLVED. **Nothing here promotes.**

## 6. The five pre-declared conditional partitions

Each is a state partition fixed BEFORE any outcome is seen, each answered with
its own MDE.

1. **Large winners.** `gain_since_entry` deciles; the top bucket (> +50%) is the
   headline. Estimand: Δ(`HOLD` − `TRIM_25`) and Δ(`HOLD` − `SELL_BENCH`).
2. **Events.** Days-since-earnings-announcement buckets {0-5, 6-20, 21-60, >60}
   crossed with SUE sign. Estimand: does Δ(`HOLD` − `SELL_CASH`) move with
   event proximity?
3. **Drawdown: damage or noise.** `drawdown_from_peak_since_entry` buckets
   crossed with revision-score sign. Estimand: Δ(`HOLD` − `SELL_CASH`) inside
   each cell. The hypothesis under test is that a drawdown with *deteriorating
   revisions* is different from one without.
4. **Replacement vs cash.** H3, on the full denominator and inside each
   partition above.
5. **Re-entry.** States where a declared de-risk trigger fired at T0: compare
   staying in cash to horizon h against re-entering the same name at +20 days.

## 7. Validation protocol for the learned arm

Purged, embargoed, walk-forward time splits (expanding train, 252-day embargo
between train and test, no random k-fold). **Every scaler, imputer and feature
selection is fitted INSIDE the training fold.** LightGBM first; a small NN
second; a conservative offline-RL action-value learner **only if** the simpler
learners beat the best baseline — that gate is declared here so it cannot be
opened after seeing a result.

## 8. What this trial cannot say, declared in advance

1. **It is not alpha evidence.** Simulated counterfactuals on historical data
   are DIRECTION CHECKS. No Sharpe claim, no money claim, no skill claim.
2. **The eligible universe is liquid-name-biased** (price ≥ $5, ≥252d history,
   63d median dollar volume ≥ $1m, top 1,500 by dollar volume). Positions that
   died *before* T0 cannot generate a decision at T0 — correctly, since the
   decision would not exist — but this does mean the state population is
   conditioned on survival TO the decision. Deaths AFTER T0 are fully modelled
   and counted.
3. **Entry cohorts are synthetic.** No real book bought these names. The
   entry-conditioned features (unrealised gain, drawdown-from-peak) are
   therefore properties of a *hypothetical* holder, and the trial measures what
   such a holder should have done, not what anyone did.
4. **One-shot decisions, not paths.** Each state resolves a single decision over
   a horizon. It does not compound a policy through time, so nothing here is a
   CAGR and nothing here is a lane.
5. **`REPLACE` arms inherit their proxy's limits.** A null on replacement is a
   null on *momentum-ranked* replacement, not on replacement in general.

## 9. Search denominator commitment

Every configuration executed — including failures, skips, and arms that
produced nothing — will be counted and printed in the report. Nothing will be
dropped for being unflattering, and nothing will be added after seeing a
result without being marked as post-hoc and reported-never-deciding.

---

*Registry: `EXIT-LAB-1`. Accrues zero arms; counts against every future
promotion.*
