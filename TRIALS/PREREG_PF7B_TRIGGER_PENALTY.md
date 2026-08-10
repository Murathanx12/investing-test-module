# PREREG — TRIAL-PF7B-TRIGGER-PENALTY-1 (REGISTERED, NOT RUN)

**Registered:** 2026-08-10 · **Family:** PF-7B · **Stage:** backtest
**Origin:** external review #3/#5 · **Evidence:** `runs/NIGHT7/T2c_TRIGGER_MOM_CONTROL.json`

## 1. What we already measured

Names in the baseline book that trigger a 20% peak-drawdown while held go on to
underperform their fellow holdings by **−7.2% to −8.4%/yr** at 3/6/12-month
horizons, Newey-West t **−2.4 to −4.4**, and the effect **survives** both
within-month momentum residualisation and momentum-quintile matching. 1,833
triggers, 482 months, observation only — no trades were executed to produce it.

Separately, G7 measured that **acting** on the trigger costs −3.08%/yr and
$743,599 per $1m over 23 years. So the information is real and the obvious
vehicle is ruinous.

## 2. Hypothesis

**H1:** the trigger's information can be delivered at the annual rebalance —
which happens anyway — as a rank penalty, capturing part of the −7%/yr avoidance
at **zero incremental turnover**.

**H0:** it cannot. Either the information does not survive being delayed to the
annual clock (it decays within the year), or the penalty displaces names whose
replacement is no better, so net excess is unchanged.

## 3. Design

Entry, universe, clock, costs and benchmark identical to
`TRIAL-PF7-EXIT-SWEEP-1` A0 — the banked annual book. **The only change is at the
annual rebalance:** a name that triggered a ≥20% peak drawdown at any point in
the preceding 12 months has its composite score penalised before selection.

Arms (penalty strength is the only swept parameter, and it is a **pre-declared
grid, not a search**):

| arm | penalty |
|---|---|
| P0 | none (= A0 baseline, the control) |
| P1 | triggered names demoted below all non-triggered names (hard exclusion for one year) |
| P2 | triggered names' percentile reduced by 0.10 |
| P3 | triggered names' percentile reduced by 0.25 |

## 4. Primary metric and decision rule (frozen)

- **Primary:** paired monthly difference vs P0, annualised, Newey-West(12) t.
- **CONFIRMED** only at paired **|t| ≥ 2.0** *and* |effect| ≥ **1.0%/yr**, same
  sign. Otherwise **UNRESOLVED**, with MDE printed.
- **Turnover invariant (the whole point):** each arm's one-way annual turnover
  must stay within **0.05** of P0. If an arm exceeds it, the "zero extra
  turnover" premise has failed and the arm goes through **G7** before any net
  number is quoted (CANON §15).
- Verdicts in taxonomy v2.

## 5. Registered predictions

1. **P1 (hard exclusion) turns turnover UP by more than 0.05** and fails the
   invariant — excluding ~all triggered names forces replacements.
2. **No arm reaches paired |t| ≥ 2.0.** The −7%/yr is a *within-book relative*
   effect on a minority of names; diluted across 150 positions and delayed to an
   annual clock, the portfolio-level effect should be roughly
   (fraction triggered) × (effect) × (delay decay), which is likely under 1%/yr.
3. **The point estimates are nonetheless positive for P2/P3** — direction should
   survive even if magnitude cannot be resolved.

## 6. Honest caveats, declared before compute

- The trigger evidence and this test use **the same history**. This is a
  *within-sample* delivery test of an effect measured on that sample, so a pass
  is evidence about implementability, **not** independent confirmation of the
  effect.
- It adds **4 branches** to the constraint ledger.
- The event study is on names **held by the book** — a selected sample. The
  effect may not generalise to the eligible universe.

## 7. Why this is worth running

Because the vehicle is free. Every other candidate for improving the book costs
turnover, and NIGHT-7 measured what turnover costs. This one changes which names
a rebalance we are already paying for happens to pick.
