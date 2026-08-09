# PRE-REGISTRATION — PF-2, the successor campaign

**Registered:** 2026-08-09, by the commit that adds this file, **before** any
PF-2 configuration was computed.
**Family:** PF-2. **Branch:** `factory/night-2` (cut from `factory/night-1`).
**Instrument:** the PF-1 harness, calibration receipt `runs/PF/VALIDATION.json`
(V1 reproduced INSTR-ERA-BACKTEST-1 to Δt = 0.00). Extended, not rebuilt.
**Governing rule:** `aegis-finance/docs/EXECUTION_STANDARD_2026-08-08.md`
**as amended 2026-08-09** (commit `001fa4d`): G4a factor gate, FACTOR-HARVEST
PRODUCT label, NEAR-MISS(gate) verdict class.
**Holdout:** 2023-01-01 .. 2024-12-31 stays unread. The loader refuses it.

---

## 1. What PF-1 left on the table (the premise, not a result of this campaign)

Banked, from `docs/PF1_CAMPAIGN_VERDICT_2026-08-08.md` (+ its 2026-08-09
addendum), 648 experiments:

- `PF-ENGINE-ALPHA`: +5.21 %/yr net excess over 59.5y, t 3.77 (NW 2.72), maxDD
  −35.4%, ruin 0.005, 15.6× benchmark terminal wealth, 8/8 grid positive,
  placebo PASS. Failed **only** regime breadth (3/5 blocks). **FF5+UMD alpha
  +0.89 %/yr, t 0.71** — a factor harvest, not engine skill.
- `PF-PROF-COMPOSITE`: +4.35 %/yr over 40.2y, 8/8 positive, placebo PASS.
  Failed **only** ruin (0.241 > 0.20). Its N=150 arm printed ruin 0.102.
- `PF-INSIDER-TILT`: −5.48 %/yr, 0/8, placebo FAIL. Construction defect noted:
  the signal is a small-integer buyer count.
- Timing (`PF-REGIME-SWITCH`) destroyed 3.34 %/yr. Concentration
  (`PF-RISK-SAT-1`) produced −2.25 %/yr at P(DD>60%) = 0.994.

## 2. Disclosures (things I know before the compute that could bias it)

1. **`PF-ENGINE-ALPHA-2`'s base configuration is arithmetically the same
   portfolio as PF-1's `PF-ENGINE-ALPHA`.** Its result is therefore ALREADY
   KNOWN (+5.21 %/yr, 3/5 blocks, FF5+UMD t 0.71). It is re-run for provenance
   under spec-hash v2 and as a harness re-validation, and it **does not count
   as a new test** in this campaign's denominator of novel experiments. Any
   deviation from the banked number is a harness regression and stops the
   campaign.
2. **`PF-PROF-COMPOSITE-150`'s numbers are partially known** — PF-1's grid ran
   an N=150 arm (+4.67 %/yr, ruin 0.102). This registration exists to test it
   as a *pre-declared candidate on its own frozen grid*, which is a different
   claim from a post-hoc rescue, but it is not a blind test and is not
   presented as one.
3. **The tie-heaviness of `insider:cluster12m` was measured before this
   registration** (a data property, not a return): among the top-100 ranked
   names per month, 2010-2020, the count signal carries a mean of **14 distinct
   values** — ~86 of 100 selections are decided by arbitrary tie-break. The
   tie-aware replacement carries 100/100. No return was computed to establish
   this.
4. **Spec-hash v2.** Adding the `blend_market` knob would have renamed every
   PF-1 artifact under v1 hashing, so the hash now omits default-valued fields.
   PF-1 hashes reproduce only at commit `c01388f`; PF-1 receipts on disk keep
   their v1 names. No PF-1 number changes.
5. No holdout data has been read by me or by any process in this campaign.

## 3. The registered candidates, with grids frozen here

Universe/eligibility/costs/benchmark unchanged from PF-1: survivorship-free
63-year CRSP panel with real delisting returns, price and dollar-volume floors,
benchmark = CRSP value-weighted **total** return, costs 25 bps one-way (or the
measured KO half-spread where a config says so), formation month m−1 → realized
month m.

### 3.1 PF-ENGINE-ALPHA-2 — can the regime hole be fixed WITHOUT timing?

Signals (unchanged): `osap:GP` 1.0, `osap:BM` 1.0, `native:mom_12_1` 1.0,
`native:vol_12m_low` 0.5, `native:max_ret_low` 0.5. Segment `all`, N=25,
monthly, flat-25, 1963-07..2022-12.

`blend_market = X` holds a **constant** X share of the market portfolio,
rebalanced monthly. It is an allocation frozen in the spec — it never reads a
regime, a trailing return, or a volatility state. Timing is not being retried.
The blend is charged: the satellite's own costs, a 3 bps/yr index-fund expense
on the market sleeve, and 25 bps on the monthly sleeve-rebalancing trade.

Grid (8, frozen): base · blend 0.25 · blend 0.40 · blend 0.50 · N=50 ·
N=50+blend 0.40 · segment `largemid` (the mega-cap-inclusive sleeve) ·
quarterly rebalance.

**The graduation candidate is the BASE.** The grid is robustness and answers
the descriptive question. A grid config that passes where the base fails is a
**PF-3 registration, never a graduate** — that rule is what makes an 8-config
grid honest.

### 3.2 PF-ENGINE-ALPHA-PRODUCT — is it worth buying, factor harvest or not?

Judged against what a person could actually buy, all run on the identical
panel, net of the same costs:

- `ALT-EW-UNIVERSE` — equal-weight of the eligible universe (the monkey);
- `ALT-VALUE-PROF` — `osap:BM` + `osap:GP`, all, N=150, monthly, flat-25;
- `ALT-MULTIFACTOR` — `osap:BM` + `osap:GP` + `native:mom_12_1`, all, N=150,
  monthly, flat-25;
- the benchmark itself.

**Product bar (frozen):** the candidate's excess terminal wealth exceeds ALL
of the above **and** its ruin P(DD>60%) ≤ 0.20. Passing means it may be called
a FACTOR-HARVEST PRODUCT. It may never be called engine skill unless G4a also
passes.

### 3.3 PF-PROF-COMPOSITE-150 — breadth as a first-class candidate

`osap:GP` + `osap:OperProfRD` + `osap:CBOperProf`, segment `small`, **N=150**,
monthly, flat-25. Grid (8): base · N=100 · N=200 · quarterly · KO costs
(2002+) · segment `all` · segment `largemid` · blend 0.25.

### 3.4 PF-INSIDER-2-TIEAWARE — one successor, then the family closes

`insider:tieaware12m` 1.0 + `osap:GP` 0.5, segment `all`, N=25, monthly,
flat-25, 2007-01..2022-12. The signal is dollar-value weighted, exponentially
recency-decayed (6-month half-life, 12-month window), scaled by the name's own
dollar volume, winsorized at $50M per transaction.

Grid (8): base · N=50 · N=100 · quarterly · tie-aware alone (no GP) ·
segment `largemid` · segment `small` · blend 0.25.

**Closing rule, frozen now:** if this fails, the insider-count family is CLOSED
and no further insider portfolio construction is registered without new data
(not a new construction of the same data).

### 3.5 PF-META-1 — Murat's "11th account that copies whatever worked"

Assets = the monthly NET return series of the six PF-1 base strategies.
Every review, rank by trailing return, hold the top-k equal-weighted, pay
25 bps on the switched fraction. Strictly walk-forward: the rank at month m
uses returns through m−1 only.

Grid (8, frozen): lookback 6/12/24 months × hold top-1/top-2 at monthly review
(6 configs) · lookback 12 hold-1 at quarterly review · lookback 12 hold-1 with
switching costs set to zero (the free-switching upper bound, reported as a
diagnostic, never a graduate).

**Controls (both required):** `META-EW` — hold all six strategies equally,
always; `META-BEST-SINGLE` — the best single strategy held throughout, which
uses hindsight to pick the asset and is therefore an unfair upper reference,
reported and never a gate.

**Primary metric:** net excess CAGR vs the benchmark, and the head-to-head
against `META-EW` on excess terminal wealth under the ruin constraint.

## 4. Predictions, registered before compute

| # | Prediction | Confidence |
|---|---|---|
| P1 | At least one blend config reaches ≥4/5 positive regime blocks | high |
| P2 | **No** ENGINE-ALPHA-2 config passes G4a (FF5+UMD α ≥ +2%/yr, t ≥ 2.0) — blending adds market beta, not alpha, so α shrinks roughly with (1−X) | high |
| P3 | The blends buy regime breadth by SPENDING excess return: blend 0.50 falls below the +3%/yr G1 bar | medium-high |
| P4 | ENGINE-ALPHA-PRODUCT beats all three investable alternatives on excess terminal wealth under the ruin constraint | medium-high |
| P5 | PROF-COMPOSITE-150 clears G1 and ruin but FAILS G4a — profitability *is* RMW, a published factor | medium-high |
| P6 | INSIDER-2-TIEAWARE beats its PF-1 predecessor (−5.48%/yr) materially but still fails to reach +3%/yr | medium |
| P7 | **PF-META-1 does NOT beat META-EW.** Selecting strategies by trailing performance is market timing at the strategy level, and timing has failed every test this project has run | high |
| P8 | No PF-META-1 config beats META-BEST-SINGLE | high |

P7 is the house prediction on Murat's own idea, written down so that being
wrong counts. If META-1 beats equal-weighting, the winner-copying paper account
becomes a live proposal and this document is the evidence that the result was
not fitted after the fact.

## 5. Decision rule v2 (frozen; applied by `scripts/pf_run_batch2.py`)

Per candidate, on its BASE configuration:

| gate | bar |
|---|---|
| G1 material | net excess CAGR ≥ +3.0 %/yr |
| G3 grid | ≥ 6 of 8 configurations with positive net excess |
| G4 placebo | strategy excess > p95 of 100 turnover-matched random books (HARD) |
| **G4a factor** | **FF5+UMD ann. alpha ≥ +2.0 %/yr AND t ≥ 2.0** |
| G6 robustness | excess ex-best-year ≥ +1.5 %/yr AND ex-top-1%-months ≥ 0 |
| regime breadth | positive excess in ≥ 4 of 5 evaluable blocks |
| G8 ruin | P(max DD > 60%) ≤ 0.20 |

Verdicts:

- **WINNER (ENGINE SKILL)** — all gates including G4a.
- **WINNER (FACTOR-HARVEST PRODUCT)** — all gates except G4a, **and** the
  §3.2 product bar passes. Never described as engine alpha, model skill, or a
  discovery, anywhere.
- **NEAR-MISS(gate)** — exactly one gate failed, placebo PASSED, excess > 0.
  Does not graduate; permits a successor registration.
- **UNRESOLVED(reason)** — window < 15 years, or positive but below the
  material bar.
- **FAILED** — anything else. Placebo failure is always FAILED.

Ranking objective throughout: **excess terminal wealth subject to the ruin
constraint** — never Sharpe maximization.

## 6. What this campaign may NOT do

- Not seed a lane, not flip a flag, not write `paper_nav`, not touch the 10
  live lanes. Research compute only.
- Not read the holdout. A holdout firing plan may be WRITTEN if something
  clears every gate; firing it is a separate attended step.
- Not retro-score PF-1 under the amended standard.
- Not promote a grid config that passed where its base failed. That is a PF-3
  registration with its own prediction.
- Not describe a G4a failure as skill, or a NEAR-MISS as a winner.
- Not substitute a metric, extend a window, or add a config after seeing a
  result. Any such change abandons the trial and registers a successor.
