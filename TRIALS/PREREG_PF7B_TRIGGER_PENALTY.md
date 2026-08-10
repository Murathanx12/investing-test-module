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

Because the vehicle adds no new trading DATES. Every other candidate for
improving the book adds rebalances, and NIGHT-7 measured what that costs. This
one changes which names a rebalance we are already paying for happens to pick.

---

# AMENDMENT 1 — 2026-08-10, before any compute

**Origin:** second external review pass. **Registered predictions in §5 are
UNCHANGED.** What changes is a verdict label that overclaimed, a decision rule
that was not directional, a cost premise that was assumed rather than measured,
and a battery of confounds that had not been named.

## A1.1 A pass here is not CONFIRMED

§6 already says, correctly, that the trigger evidence and this test use the same
history, so a pass is evidence about implementability and **not** independent
confirmation. §4 then labelled a pass `CONFIRMED`. Those two sentences cannot
both stand.

**Renamed: the positive state is `DELIVERY_PASS` (implementable in sample).**
`CONFIRMED` in taxonomy v2 is reserved for evidence from data that was genuinely
inaccessible during discovery — an untouched holdout, or forward record. This
trial has neither and cannot mint one.

## A1.2 The decision rule is now directional

§4 read `|t| ≥ 2.0` and `|effect| ≥ 1.0%/yr`, which on a literal reading would
label −2.0%/yr at t −3.0 a pass. The hypothesis is that the penalty **helps**.

| outcome | state |
|---|---|
| effect ≥ **+1.0%/yr** and NW(12) t ≥ **+2.0** | `DELIVERY_PASS` |
| effect ≤ **−1.0%/yr** and NW(12) t ≤ **−2.0** | `REJECTED` — the penalty is harmful; the trigger information does not transfer, or transfers with the wrong sign |
| anything else | `UNRESOLVED`, MDE printed |

## A1.3 "Zero incremental turnover" and "free" are withdrawn

§2 claimed zero incremental turnover; §5.1 simultaneously predicted P1 would
raise turnover. The prereg contradicted itself, and the earlier of the two
sentences is the one that was wrong. A swap at an already-scheduled rebalance
still crosses a spread, still pays impact, and swaps a name of one liquidity for
a name of another.

The defensible claim is: **no additional rebalance DATES, and an incremental
turnover cost that must be measured rather than assumed.**

**Consequently the turnover-invariant escape hatch in §4 is removed. Every arm
(P0–P3) goes through G7 regardless of what the monthly panel's turnover
difference is.** The panel-vs-G7 gap was measured at ~2.4 pts/yr twice
independently (NIGHT-6, NIGHT-7); a 0.05 turnover threshold read off the
instrument that is known to understate is not a safe gate. G7 already exists, so
there is no cost to simply using it.

## A1.4 Momentum was one confound. It was not the only one.

A 20% peak drawdown while held is not only a momentum sort — it also
mechanically selects on realised volatility, on distance-from-high, on beta, on
deteriorating liquidity, and on whatever fundamental deterioration drove the
fall. Surviving a momentum control is necessary and nowhere near sufficient.

Registered as **`TRIAL-PF8-TRIGGER-CONFOUND-1`**, to run beside this trial. The
write-up of either may not assert a *mechanism* until it lands:

1. Incremental association after within-month controls for: trailing 12m
   realised volatility, idiosyncratic volatility, distance-from-52w-high, beta,
   log size, ADV, Corwin-Schultz spread, industry, initial composite rank at
   entry, and the change in the profitability/value components since entry.
2. **The path-geometry placebo, which is the sharp test.** Among held names
   matched on trailing return *and* trailing volatility, does the *path* — having
   actually breached 20% below a running peak — still forecast worse forward
   returns than a matched name that reached the same endpoint without breaching?
   If yes, the finding is about path dependence and is genuinely interesting. If
   no, the trigger is a coarse proxy for return-and-volatility and should be
   replaced by those two variables directly, which are cheaper and better
   measured.

## A1.5 Ledger

`TRIAL-PF8-TRIGGER-CONFOUND-1` is a separate registration carrying its own
branch count. This amendment adds **0 branches** to PF7B-TRIGGER-PENALTY (the P0–P3
grid is unchanged); removing the turnover escape hatch removes one decision
point rather than adding one.
