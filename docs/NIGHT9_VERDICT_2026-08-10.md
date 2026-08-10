# NIGHT-9 — 2026-08-10

Two halves, and the second one was ordered mid-session: a research half that
took N1B apart, and a build half that turned the programme's first product at
the account it is supposed to compound. The research half ends with the
sharpest open question this factory has produced. The build half ends with
something that runs.

**Branch:** `factory/night-9` (module) · `main` (aegis-finance, `0c3f170`)
**LLM spend:** $0 · **Holdout:** unread · **Lanes:** untouched

---

## 1. N1B — every rank-based axis says the learned rankers are better, and the book still earns less

Prereg `TRIALS/PREREG_N1B_WHERE_DOES_THE_IC_LIVE.md` + AMENDMENT 1 (the clock
axis, registered before compute after an external review named the confound) +
AMENDMENT 2 (registered after axes 1–5, before axis 7 ran).

**Step 0 — the parent did not persist its score frames**, so N1B could not
"decompose series that already exist". The re-fit was gated on reproducing the
parent's published statistics: ΔIC means, NW t's, money means and turnover, all
four arms. **The gate PASSED**, which is the first time this programme has
verified that re-running its own script reproduces its own receipt.

### The five decompositions, and what each one killed

| axis | result | what it rules out |
|---|---|---|
| **clock** | on-rebalance ΔIC **+0.0367 / +0.0611 / +0.0494** at t 3.97 / 3.88 / 3.10, against MDEs 0.019 / 0.032 / 0.032; off-clock ΔIC +0.0337 / +0.0680 / +0.0561 | the reviewer's hypothesis. IC was measured in 450 months and the book acts in 37, but the advantage is **the same size on the dates the book can trade**. My prediction 4 scored correct against the reviewer's |
| **rank** | base-decile ΔIC is **larger at the top than the bottom** — D1 0.046 / 0.125 / 0.107 vs D10 0.022 / 0.073 / 0.052 | **H1, the §28 hypothesis.** The advantage does not live in the leg a long-only book cannot hold. Prediction 1 REFUTED |
| **boundary** | ΔIC in ranks 100–250 of **+0.014 (t 1.09) / +0.093 (t 4.41) / +0.087 (t 4.41)** | "the model is worse exactly where selection happens" for the two wide arms |
| **top-K** | the learned arms' top-K beats the control's at **every** K — 25, 50, 100, 150, 300 | prediction 2 (flat top-only IC) REFUTED |
| **membership** | overlap is only **14–25%**; each rebalance swaps 112–129 of 150 names; the names they **add** beat the names they **drop** by **+3.3 / +5.9 / +5.2** points (t −1.72 / −2.15 / −2.27, MDEs 0.038 / 0.055 / 0.046) | prediction 5 (positive replacement loss) REFUTED, and prediction 3 (overlap > 50%) REFUTED badly |

Five axes, four registered predictions refuted, and **no remaining "where does
it go" answer**. Both instruments are looking at the same names on the same
dates and disagreeing about them.

### What that leaves, and it is about the instrument

The label is a demeaned **log** forward return. A long-only equal-weight book is
paid in **simple** returns. The difference between them is a variance penalty: a
name with an even chance of tripling or losing 80% has an expected simple return
of **+60%** and an expected log return of **−25%**. Ranking on mean log return
therefore systematically de-selects positively skewed names — the ones whose
right tail pays for a small-cap book.

If that is what happened, then **the ordering instrument this programme has been
using is misspecified for the book it was being used to judge**, and NIGHT-8's
headline ΔIC of +0.068 at t 4.09 was rewarding precisely the behaviour that lost
money. AMENDMENT 2 registers the test — same frozen scores, same months, same
top-150 sets, label changed from log to simple — with three predictions:
ΔIC shrinks by at least half, the top-150 delta turns negative, and the
composite's holdings are more positively skewed.

### The test ran, and it is the finding of the night

| | log label | simple label |
|---|---|---|
| **ΔIC R1 / R2 / R3** | +0.03399 / +0.06747 / +0.05558 (t 4.18 / 4.09 / 3.46) | **identical, to five decimals** |
| **top-25 delta** | **+0.067 / +0.071 / +0.079** | **−0.056 / −0.049 / −0.033** |
| **top-50** | positive | −0.059 / −0.054 / −0.041 |
| **top-100** | positive | −0.039 / −0.047 / −0.035 |
| **top-150** | positive | −0.029 / −0.041 / −0.036 |
| **top-300** | positive | −0.016 / −0.028 / −0.027 |

**Prediction 7 is refuted, and for a reason I should have seen before writing
it: rank-IC is invariant to any monotone transform of the label.** Log is a
monotone transform of simple return, so the ranks are the same and the
correlation is the same. ΔIC did not shrink by half; it did not move at all.

**Prediction 8 is confirmed, and it reconciles everything.** Under the label the
book is actually paid in, the learned rankers' top-K is **worse than the
composite's at every K and in every arm — 15 of 15 negative** — and the sign
agrees with the money result (−1.45 / −3.33 / −2.44 %/yr). No single top-K delta
clears |t| 2 (they run 0.98 to 1.70), so this is a **directional reconciliation,
not an independently significant effect**; but it is consistent across five cut
points, three architectures and the money instrument simultaneously.

### So the conclusion is about the instrument, not the models

**A rank correlation discards exactly the information a long-only book is paid
in.** A portfolio earns the arithmetic mean of the simple returns of the names it
holds; that quantity depends on the magnitude of the right tail, and rank-IC
throws magnitudes away by construction. Two rankings with identical ΔIC can
differ by percentage points of realised return, and here they do.

NIGHT-8 reported "two instruments — money and ordering — is what saved this from
a vacuous null". **It did not save it. The ordering instrument was measuring
something that cannot answer the question**, and its +0.068 at t 4.09 was
consistent with the learned rankers being *worse* for the book the whole time.
That number was never wrong; it was never evidence about money.

### The mechanism check is only two-thirds there, and that is reported

Prediction 9 said the composite's holdings would be more positively skewed.
Mean forward 12-month skewness of each arm's top 150: composite **1.599**,
R1 **1.724**, R2 **1.231**, R3 **1.075**. True for the two wide arms — and
**false for R1**, which is *more* skewed than the composite and still loses
money. So skew-avoidance explains R2 and R3 and does not explain R1. The
log-versus-simple reconciliation stands on the top-K reversal, which holds for
all three; the skew story is the proposed *mechanism* and it is confirmed in two
cases out of three.

**Consequence, and it is a standing one:** rank-IC may be reported as a
description of ordering. It may **not** be used as the corroborating instrument
when a money result is null, and it may never be described as "ordering better"
without the magnitude test beside it. The successor is a relabelling trial —
train on the arithmetic objective the book is paid in — not a new model class.

### Two self-inflicted bugs, both silent, both printed here

- **`membership` returned `None` for all three arms rather than raising** — the
  silent-fragility failure mode by name. Recomputed directly from the frozen
  scores.
- **The first fix was wrong and made it worse.** It blamed parquet for turning
  permno labels into strings and cast them back to `int`. The CRSP panel's own
  columns are `object`, so the cast produced **zero eligible names per month** —
  the same `None`, from the opposite cause. Verified against
  `elig.columns.dtype` before rerunning. A wrong fix that reproduces the
  original symptom is the most dangerous kind, and it is recorded rather than
  quietly overwritten.

### One axis is not trustworthy and is not being reported as a finding

The **phase** axis returned an identical excess CAGR for all twelve phases of
the control (range **0.00 pt/yr**), which contradicts NIGHT-7's measured 2.45
pt/yr date-luck range. Either the `phase` argument is not staggering the book as
its own docstring claims, or this invocation is mis-specified. **No phase claim
is made tonight.** It is a queue item.

---

## 2. G8 — the impact term G7 does not have

Prereg `TRIALS/PREREG_G8_IMPACT_AND_CAPACITY.md`. NIGHT-8 measured G7 returning
**31.00 bps per dollar traded at ADV multiples of 1e6, 100, 5 and 1** — flat
across a million-fold liquidity range, because it prices scarcity as delay.

`aegis_brain/pf/impact.py` implements the **metaorder square-root law**, charged
on the whole order at creation and amortised across its fills, so working an
order down over more days does not escape it — which was exactly G7's loophole.

**Built beside G7, not inside it.** `SimConfig.impact_coef` defaults to `0.0`,
at which value the arithmetic is skipped entirely and G7's published outputs are
reproduced; the receipt records `execution_model: G7` or `G8`.

**Fifteen invariants, each written from the failure it prevents** — including
the one NIGHT-8 proved G7 lacks (bigger AUM must cost more per dollar traded),
concavity (double the size, √2 the cost per dollar), and *a name with no volume
is the most expensive case, not the free one*. Two of them failed on the first
run and both were real: a warm-up window with no trailing ADV was charging the
opening trade — the largest in any run — the untradeable-name rate of 1000 bps,
and a NaN sigma fallback was truthy. Both fixed, both counted (`impact_warmup_orders`).

**The capacity ladder was NOT run**, deliberately. Murat's mid-session
instruction: *"spending weeks answering whether the strategy can deploy $500
million is not helping me manage $45,000 today."* The instrument exists, is
calibrated, and is ready. Until it runs, **every capacity number this programme
has published remains a delay-only lower bound** — which is now CANON §17.

---

## 3. A corrigendum: the N2 "15× better than chance" is withdrawn

NIGHT-8 reported that the composite avoids distressed names at ~15× better than
chance. That number divided the bite of **V5 — a random veto count-matched to
V4's 288 names/month** — by the bite of **V3 distress, which vetoes 60**.
Comparing a 288-name veto's bite to a 60-name veto's bite is not a probability
ratio; a factor of 4.8 of the "15" is the count difference alone.

Normalised properly (V5 pins the sampling frame exactly: 288 / 0.1387 = 2,076
names):

| arm | vetoes/mo | expected bite | observed | avoidance |
|---|---|---|---|---|
| accruals | 134.7 | 6.49% | 6.17% | **1.05× — chance** |
| share issuance | 142.9 | 6.88% | 3.10% | 2.22× |
| **distress** | 60.0 | 2.89% | 0.85% | **3.40×** |
| union | 288.0 | 13.87% | 9.31% | 1.49× |

**What survives:** the direction, at a quarter of the size, and only for
distress and issuance. **What does not:** the number 15, and the implication
that the effect is uniform across the three anomaly families — accruals is
indistinguishable from chance. Every *return* result in N2 stands unchanged; the
placebo gate was correctly matched to the arm it gates.

Receipt: `runs/NIGHT9/CORRIGENDUM_N2_AVOIDANCE.json`.

---

## 4. The units bug has a structural fix now, not just a guard

NIGHT-8 fixed `mde_annualized` and added a backstop. The *design* that produced
the bug survived: one generic `paired()` helper, copy-pasted across scripts, fed
monthly returns in some places and monthly rank-IC in others, with output fields
named for returns throughout. N1's published ordering table therefore carried an
`mde_annualized` on a Spearman correlation.

`aegis_brain/pf/stats.py` removes the generic entry point. Four typed functions
— return, IC, probability, Brier — each carrying `unit`, `frequency`,
`annualization` and `estimator`, with the annualising arithmetic reachable
**only** from the return-typed one. Seven tests assert the dimensional
invariants: a 0.001 monthly return difference becomes ~1.2%/yr; a 0.001 IC
difference stays 0.001, for ever.

---

## 5. The build half — Optimus Portfolio Manager v1

Shipped in `aegis-finance` at `0c3f170`. Full write-up:
`aegis-finance/docs/PORTFOLIO_MANAGER_v1.md`. One command
(`python scripts/morning_brief.py`) or one endpoint (`GET /api/pm/daily`)
returns the morning: portfolio state, the twelve-month distribution with the
downside printed beside the target, per-holding BUY/ADD/HOLD/TRIM/SELL with
dollar amounts and kill conditions, threats, a ranked opportunity radar over the
watchlist, and which holding funds which purchase.

It runs on live data. On the reconstructed $45k book it currently reports a
median twelve-month outcome near **$64,500**, **P(reach $100k) ≈ 20%**,
**P(below $30k) ≈ 6%**, an expected maximum drawdown of **−27%**, and about one
path in twenty going through a drawdown worse than −50%. The required return for
the target is **+122%**.

Two construction bugs were found and fixed while building it, both of which had
produced confident nonsense — a mixed-object distribution that recommended
selling seven of eleven positions, and a cap-before-normalise that collapsed a
conviction book to equal weight. Both are documented in the module docstrings
rather than silently corrected.

**The book is marked `confirmed: false`.** Positions were reconstructed from the
January 2026 research PDF, which lists tickers, entry prices and analyst targets
but no share counts and no cash. Every dollar figure carries a banner until
Murat corrects it.

---

## 6. Predictions scored

| # | prediction | outcome |
|---|---|---|
| N1B-1 | H1 supported: ΔIC concentrates in the bottom deciles | **REFUTED** — it is larger at the top |
| N1B-2 | top-only IC flat, \|t\| < 2 | **REFUTED** — the learned arms win at every K |
| N1B-3 | top-150 overlap above 50% | **REFUTED** — 14–25% |
| N1B-4 | the clock is NOT the explanation | **CORRECT** (against the reviewer's hypothesis) |
| N1B-5 | replacement loss positive | **REFUTED** — the added names beat the dropped ones |
| N1B-6 | wide phase spread | **UNRESOLVED, and deliberately with no MDE.** The referee flags a null without a minimum detectable effect, correctly — but an MDE would be a lie here. The axis returned an identical number for all twelve phases, so the estimate is not small, it is *degenerate*: there is no dispersion to compute a standard error from. The instrument is broken, not underpowered, and quoting an MDE would dress a broken measurement as a weak one |
| N1B-7 | ΔIC shrinks by half under a simple-return label | **REFUTED** — it does not move at all; a rank correlation is invariant to a monotone relabelling, which is the whole point |
| N1B-8 | the top-150 delta turns negative | **CORRECT** — negative at every K and in every arm, 15 of 15 |
| N1B-9 | the composite's holdings are more positively skewed | **PARTLY** — true for R2 and R3, false for R1 |
| G8-1..6 | the capacity ladder predictions | **NOT RUN** — deprioritised mid-session, registered and unresolved |

Four of five substantive predictions refuted is the night's most useful fact: a
prereg whose predictions all come true is usually a prereg written after the
compute.

---

## 6b. Ledger

**NIGHT-9 adds 0 strategy branches.** No signal, weight, threshold, holding rule
or clock was searched. N1B fitted no model (its step-0 re-fit had to reproduce
the parent exactly or void), G8 is an execution instrument, and the corrigendum
and the typed-stats split are corrections. The trial-count denominator stays at
**179**, unchanged since the search closed.

## 7. What is NOT claimed

- No capacity number. G8 exists and is calibrated; it has not been pointed at
  the real book.
- No phase or date-luck claim.
- Nothing about the label test unless its receipt key exists.
- Nothing about whether the portfolio manager's analyst layer *works*. It is
  labelled `observational, unvalidated` in every payload it emits, and that is
  the honest description until the research lab grades it.
- PF8 trigger confound, T4b coverage matrix and N3b were **not run**. They were
  on the night's list and were displaced by the pivot, not by a finding.
