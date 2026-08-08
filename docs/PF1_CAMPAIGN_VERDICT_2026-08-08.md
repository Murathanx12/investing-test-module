# PF-1 CAMPAIGN VERDICT — six engine-built portfolios, 63 years, one frozen rule

**Pre-registration:** `TRIALS/PREREG_PF1_FACTORY.md`, sealed by commit before
any registered compute. **Instrument:** `runs/PF/VALIDATION.json` (PF-HARNESS-
VALID, VERDICT PASS — the harness reproduced INSTR-ERA-BACKTEST-1's banked
numbers exactly before it was allowed to judge anything).
**Receipts:** `runs/PF/CAMPAIGN_PF1_FINAL.json`, one scorecard JSON + markdown
per configuration, six placebo bands.

**Multiple-testing denominator, printed as required: 448 experiments** — 48
strategy runs (6 bases × 8 one-at-a-time configurations) + 400 turnover-matched
placebo books (4 × 100 at the time of writing; the two remaining bands are for
strategies already failed on negative excess and cannot change a verdict).

**Holdout (2023-01 .. 2024-12) was NOT read.** The loader refuses it by default.

---

## 1. The result in one line

**No strategy cleared the full frozen bar. Two came close in ways that matter,
and each failed on exactly one gate — not on returns.**

| Strategy | window | net excess CAGR | t (NW) | max DD | P(DD>60%) | wealth vs bench | placebo | verdict |
|---|---|---|---|---|---|---|---|---|
| **PF-ENGINE-ALPHA** | 59.5y | **+5.21 %/yr** | 3.77 (2.72) | −35.4% | 0.005 | **15.6×** | **PASS** p=0.010 | FAILED — regime blocks 3/5 |
| **PF-PROF-COMPOSITE** | 40.2y | **+4.35 %/yr** | 2.32 (2.00) | −56.1% | 0.241 | 4.68× | **PASS** p=0.010 | FAILED — ruin 0.241 > 0.20 |
| PF-REGIME-SWITCH | 59.5y | +1.87 %/yr | 0.83 (0.69) | −30.9% | 0.002 | 2.72× | PASS p=0.010 | FAILED — G1, G6, regimes |
| PF-GP-SMALL | 40.2y | +1.79 %/yr | 1.39 (1.23) | −67.0% | 0.560 | 1.90× | PASS p=0.020 | FAILED — G1, G6, regimes, ruin |
| PF-INSIDER-TILT | 15.8y | −5.48 %/yr | −0.99 | −62.4% | 0.385 | 0.44× | n/a | FAILED — negative excess |
| PF-RISK-SAT-1 | 58.8y | −2.25 %/yr | 0.90 | −83.7% | **0.994** | 0.30× | n/a | FAILED — negative excess |

Benchmark throughout: CRSP value-weighted **total** return (the index SPY
tracks, extended to 1963 because SPY starts in 1993). Costs 25 bps one-way, or
the measured Kyle-Obizhaeva spread where the grid says so. Delisting returns
flow through; delisted names are liquidated to cash with costs charged.

## 2. The two that nearly made it

**PF-ENGINE-ALPHA** (quality + value + momentum + low-vol + lottery-aversion,
25 names, monthly, whole liquid universe) turned $1 into **15.6× what the
market did over 59.5 years**, at *lower* drawdown than the market (−35% vs
−50%), with 8 of 8 grid configurations positive, +4.20%/yr excess after
deleting its best year, +3.80%/yr after deleting its best 1% of months, and
+5.24% / +5.17% in the first and second halves of the panel. It beat all 100
turnover-matched random books.

It failed on one thing: **positive excess in only 3 of 5 evaluable regime
blocks.** It lagged the post-crisis bull (−1.5%/yr) and COVID 2020 (−12.2%/yr)
— both mega-cap-led melt-ups where a small/value/quality tilt is *expected* to
lag. That is a real property, not a fluke, and the rule was written before the
number existed, so it stands.

The honest qualifier that matters more than the verdict: **its FF5+UMD alpha is
+0.89 %/yr with t = 0.71.** The CAPM alpha is +5.85% (t 3.26), but once you
control for size, value, profitability and momentum, essentially nothing is
left. This portfolio does not contain new alpha — it is a *well-built,
low-drawdown harvest of known factor premia*, which is a legitimate product and
must be labelled as exactly that, never as engine skill.

**PF-PROF-COMPOSITE** (GP + OperProfRD + CBOperProf, small caps) earned
+4.35%/yr over 40 years, 8 of 8 configurations positive, beat every random
book — and failed only the **ruin constraint**: a 24.1% modelled probability of
a 60% drawdown against a 20% tolerance. Its N=150 variant prints +4.67%/yr at
ruin 0.102, i.e. the breadth version would clear it. Promoting that variant now
would be exactly the post-hoc cherry-picking the standard exists to prevent, so
it becomes a **PF-2 registration**, not a rescue.

## 3. What died, and cleanly

- **PF-RISK-SAT-1** — the concentrated conviction satellite (10 names,
  momentum + quality). It **lost** to the market by 2.25%/yr over 59 years and
  carries a **99.4% probability of a 60% drawdown**. This is the direct answer
  to "does conviction add money": in this construction it adds ruin, not
  return. Concentration hurt everywhere it was tested — GP-SMALL's N=10 arm
  raised ruin from 0.56 to 0.87 while lowering excess return.
- **PF-INSIDER-TILT** — −5.48%/yr, 0 of 8 configurations positive. Recorded as
  a clean failure. One construction caveat for the successor: the signal is a
  discrete count of insider buyers, so its cross-sectional ranking is
  tie-heavy; a tie-aware construction is a different candidate, not a re-run.
- **PF-REGIME-SWITCH** — the walk-forward bull/bear overlay on ENGINE-ALPHA
  **destroyed 3.34 %/yr of excess return** (+1.87% vs +5.21%). Market timing
  has now failed every test this project has run.

## 4. Pre-registered predictions, scored

| # | Prediction | Result |
|---|---|---|
| 1 | GP-SMALL **and** PROF-COMPOSITE clear +3%/yr | **MISS** (PROF yes +4.35%, GP no +1.79%) |
| 2 | At least one strategy fails its placebo gate | **MISS** — all four tested passed |
| 3 | REGIME-SWITCH does not beat ENGINE-ALPHA | **HIT** (+1.87% vs +5.21%) |
| 4 | RISK-SAT-1: higher excess **and** higher ruin | **MISS on excess** (−2.25%), HIT on ruin (0.994) |
| 5 | INSIDER-TILT lands UNRESOLVED on window length | **MISS** — it failed on returns, not power |

**1 of 5.** The house remains bad at predicting its own results, which is the
reason the predictions are written down first.

## 5. Two methodological lessons (recorded, not acted on retroactively)

1. **The placebo gate is weaker than it looks.** Turnover-matched random books
   averaged −2 to −3 %/yr — trading costs alone sink random selection, so any
   strategy with positive net excess clears the gate almost automatically. It
   remains a necessary control (it kills construction artifacts) but it is
   **not** a test of whether an edge is merely factor exposure. The sharp tests
   are the equal-weight-universe control and the FF5+UMD regression — which is
   precisely where ENGINE-ALPHA's alpha disappeared. PF-2 should promote the
   factor regression to a gate.
2. **The verdict taxonomy needs a near-miss class.** "Failed one gate with
   everything else passing, placebo included" and "lost money for 59 years"
   both print FAILED, which loses information the standard cares about
   (WINNERS *and* UNRESOLVED, where unresolved ≠ dead). The frozen rule was
   applied as written tonight; PF-2's registration should carry a
   `NEAR-MISS(gate)` class.

## 6. What this means for the paper lanes

Under the frozen standard, **nothing graduates tonight** — no lane is seeded,
no flag is requested, and the GP lane proposal stays where it was, now with a
measured reason: GP-small alone is +1.79 %/yr with a 56% ruin probability at
25 names, which is not a book to run.

The two survivors of substance go to **PF-2** as registered successors:
ENGINE-ALPHA with a factor-neutral gate and a regime-breadth question, and
PROF-COMPOSITE at breadth (N=150) where its ruin number is inside tolerance.
G7 (the full daily simulator) still sits between any of them and a paper lane.
