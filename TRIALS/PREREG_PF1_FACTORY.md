# PRE-REGISTRATION — PF-1 portfolio factory batch (2026-08-08)

**Written BEFORE any PF strategy statistic exists.** Registered under CANON §6
and `docs/EXECUTION_STANDARD_2026-08-08.md` (simulate-first). The harness was
validated first and separately (`runs/PF/VALIDATION.json`, PF-HARNESS-VALID) —
this registration governs the six strategies frozen in
`aegis-finance/docs/ROADMAP_PORTFOLIO_BRAIN_2026-08-08.md` §3.

## 0. What this batch may and may not do

MAY: produce graduation scorecards (G1–G6, G8) and rank candidates by net
excess terminal wealth under the ruin constraint.
MAY NOT: seed a lane, flip a flag, touch `paper_nav`, or read the holdout.
Graduation to a paper lane additionally requires G7 (daily simulator, not built
yet) and Murat's attended flag. A WINNER here is a *candidate for G7*, nothing
more.

## 1. Instrument (frozen)

- Panel: `crsp_panel_1962_2001` + `crsp_panel_2002` stitched
  (`aegis_brain/pf/panel63.py`), real delisting returns, survivorship-free.
- Evaluable window **1963-07-31 .. 2022-12-31**. **HOLDOUT = 2023-01-31 ..
  2024-12-31, NOT READ** (the loader raises unless a holdout firing explicitly
  opts in). Firing the holdout is a separate attended one-shot.
- Benchmark: CRSP value-weighted **total** return (`mktrf + rf`, pinned Ken
  French vintage) — the index SPY tracks, extended back to 1963. SPY itself
  starts 1993 and cannot benchmark a 60-year panel. yfinance is not used.
- Costs: `flat25` (25 bps one-way, punitive) primary; `ko` (Kyle-Obizhaeva
  measured half-spread) as a perturbation **restricted to 2002+**, which is the
  KO frame's coverage. A `ko` spec without a frame raises rather than silently
  charging flat 25.
- Eligibility: production floors (price ≥ $1, median daily dollar volume ≥
  $200k) ∩ segment by formation-month dollar-volume rank
  (largemid ≤ 1000, small 1001–3000, all ≤ 3000).
- Book inception = first month the universe is thick enough (≥ `min_names`).
  Pre-inception months are excluded from the record, and each scorecard prints
  its true investable window. (Small-cap segments do not exist under the
  nominal dollar-volume floor before ~1982; that is data, not performance.)
- Every spec is hashed; every run writes `runs/PF/<name>__<hash>.{json,md}`
  write-once.

## 2. The six strategies (frozen; signal lists fixed before first compute)

| ID | Signals (weights) | Segment | N | Rebal | Cost | Window |
|---|---|---|---|---|---|---|
| PF-GP-SMALL | osap:GP (1.0) | small | 25 | 1m | flat25 | full |
| PF-PROF-COMPOSITE | osap:GP (1), osap:OperProfRD (1), osap:CBOperProf (1) | small | 25 | 1m | flat25 | full |
| PF-ENGINE-ALPHA | osap:GP (1), osap:BM (1), native:mom_12_1 (1), native:vol_12m_low (0.5), native:max_ret_low (0.5) | all | 25 | 1m | flat25 | full |
| PF-INSIDER-TILT | insider:cluster12m (1.0), osap:GP (0.5) | all | 25 | 1m | flat25 | 2007-01..2022-12 |
| PF-REGIME-SWITCH | ENGINE-ALPHA signals + `regime_rule=bull_risk_on` | all | 25 | 1m | flat25 | full |
| PF-RISK-SAT-1 | native:mom_12_1 (1.0), osap:GP (0.5) | all | 10 | 1m | flat25 | full |

Notes fixed in advance:
- **ENGINE-ALPHA is the panel-implementable proxy** of the production signal
  engine (quality + value + momentum + low-vol + lottery-aversion). The
  production engine reads yfinance and current fundamentals, neither of which
  is point-in-time; wiring it into a 63-year backtest would be look-ahead. The
  scorecard says so.
- **INSIDER-TILT** is window-limited by the SEC bulk archive (filings from
  2006-01; 12-month lookback ⇒ first usable formation 2006-12). It is expected
  to be UNDERPOWERED on money and is registered anyway, because "the test could
  not answer" is a recorded verdict class.
- **REGIME-SWITCH** uses walk-forward regime labels only: trailing 12-month
  market return > 0 with a trailing-vol brake, computed from closed months.
  No full-sample regime fit is permitted.
- **RISK-SAT-1** is the deliberately aggressive arm (10 names). Higher
  volatility is allowed; the ruin constraint (below), not Sharpe, is its bar.

## 3. Variation grid (frozen: one-at-a-time around each base)

Per strategy, exactly **8 configurations**: base, `top_n` ∈ {10, 50, 150},
`rebalance_months` = 3, `cost_model` = ko (2002+ window), `segment` ∈ the two
segments the base does not use. 6 × 8 = **48 strategy runs**, plus 6 placebo
bands (100 draws each) = the batch's multiple-testing denominator, printed on
every scorecard. A full cross was rejected deliberately: it would multiply the
denominator to buy robustness information that OAT already gives.

The **N=150 breadth arm** is included because banked prior evidence (not PF-1
evidence) says breadth is the axis that matters most for this family:
INSTR-ERA-BACKTEST-1 / PF-HARNESS-VALID measured CBOperProf small 1985-2001 at
t 3.99 vs the equal-weight universe at decile breadth (N≈154) and t 2.11 at
N=25, same signal, same window. A grid that stopped at N=50 would have been
unable to distinguish "the signal is weak" from "the book is too concentrated
to express it".

**Disclosure (CANON: every examination leaves a ledger entry).** Before this
grid was sealed, one smoke test of the harness ran GP/small/N=25 over the
**2002-2022** window (not a registered configuration; artifact not written):
net excess CAGR −1.05 %/yr, t 0.39. It is recorded here so the batch's honest
denominator includes it, and because it motivated checking that the grid could
separate breadth from signal — the fix above was chosen from banked era
evidence, not from that number, and no registered configuration was altered in
response to a registered result (none existed yet).

## 4. Primary metric and decision rule (frozen)

**Primary metric: net excess CAGR vs the CRSP VW benchmark over the strategy's
investable window.** Everything else is reported, never deciding.

A strategy is a **WINNER** only if ALL hold:

- **G1 material**: net excess CAGR ≥ **+3.00 %/yr**.
- **G4 placebo (hard gate)**: net excess CAGR > the **p95** of 100
  turnover-matched random books (AR(1)-persistent random scores, ρ searched so
  placebo turnover matches the strategy's within 10%). Failing this is FAILED,
  whatever G1 says.
- **G6 not one year / one tail**: excess CAGR excluding the single best excess
  year ≥ **+1.50 %/yr**, AND excluding the top 1% of months ≥ **0 %/yr**.
- **Regime**: positive net excess in **≥ 4 of the 5 evaluable gate blocks**
  (pre-2008, GFC, post-crisis bull, COVID, 2022 bear). The 6th block
  (2023+) is the holdout and is not evaluated here.
- **G3 robustness**: positive net excess CAGR in **≥ 6 of the 8** OAT
  configurations.
- **G8 ruin**: bootstrapped P(max drawdown worse than 60%) ≤ **0.20**
  (paired stationary block bootstrap, 12-month blocks, 5000 paths).

**UNRESOLVED** (explicitly not dead): placebo PASS and positive excess, but a
threshold missed for a reason the test cannot resolve — window too short
(< 15 years), universe structurally thin, or the metric's confidence interval
spans the bar. The reason class is recorded.

**FAILED**: placebo FAIL, or negative net excess CAGR.

Ranking among winners: **excess terminal wealth multiple vs benchmark**,
subject to the G8 ruin constraint — not Sharpe.

## 5. Frozen parameters (may not be tuned mid-batch)

`hold_band_mult = 3.0`; `min_names = 100`; weighting `ew`; delisted/no-return
names force-liquidated to cash at the month's start with costs charged; cash
earns the 1-month bill; bootstrap block 12 months / 5000 paths / seed from the
spec; placebo ρ tolerance 10%, 100 draws, seeds `spec.seed + 1000 + i`.

## 6. Declared predictions (scored afterwards, hit or miss)

1. **PF-GP-SMALL and PF-PROF-COMPOSITE clear G1** (≥ +3%/yr net excess) on the
   full panel — the era instrument already printed CBOperProf net t 4.30 over
   1985-2001, so the direction is not in question; the open question is whether
   a 25-name portfolio at punitive costs keeps ≥3%/yr.
2. **At least one strategy FAILS its placebo gate.** Small-cap concentrated
   books carry a size/illiquidity premium that random selection also harvests;
   if nothing fails, suspect the placebo, not the strategies.
3. **PF-REGIME-SWITCH does NOT beat PF-ENGINE-ALPHA** on excess CAGR (timing
   overlays have failed every previous test in this project: Markov timing
   dead on receipts, COND-VT rejected §21).
4. **PF-RISK-SAT-1 has a higher excess CAGR and a materially higher ruin
   probability** than ENGINE-ALPHA — the concentration trade, stated in advance.
5. **PF-INSIDER-TILT lands UNRESOLVED** on window length.

## 7. One shot

The 42 runs execute once under this registration. A configuration not listed in
§2–§3 is a NEW registration, not a retry. Post-hoc edits to a spec after seeing
its number contaminate it; the affected strategy is recorded as VOID and gets a
new ID.
