# PREREG — TRIAL-N1-RANKER-VS-COMPOSITE-1

**Registered:** 2026-08-10 · **Family:** N (extension) · **Stage:** backtest
**Data grade:** `crsp` (CRSP security universe with delisting returns; Compustat/OSAP
features under PIT reporting-lag controls)

Resurrects: TRIAL-BRAIN-002-crsp-holdband — new instrument: a PAIRED comparison
against the hand-written composite on the same 150-name pool and the same annual
clock, instead of an absolute test against universe EW on a monthly clock. The
shared pool cancels most of the return noise, which is where the power comes
from; and the annual clock removes the 180%/mo turnover that BRAIN-001 named as
the killer rather than the ranker.

## 1. The question

Every strategy this factory has adopted uses **weights a human wrote**. The
surviving book is three profitability signals at equal weight — a choice made by
hand, defended by economics, never compared against the alternative of letting a
model choose. The literature (Gu, Kelly & Xiu 2020) says learned weights beat
written ones. This factory has never tested it *on its own book*.

> **Does learning the weights beat writing them?**

## 2. What already happened, and why this is not that

`TRIAL-BRAIN-001` (EODHD 2017+): GKX big-three via shallow GBM, **REJECT**, Arm B
t −1.40, DSR 0.124. Diagnosis in the trial doc: *turnover is the killer* —
monthly-refit decile books traded ~180%/mo one-way for a 45 bps/mo drag.

`TRIAL-BRAIN-002` (CRSP 2002-2024, hold-banded): **REJECT**, Arm B net excess
−56 bps/mo, t −2.80; gross also negative; DSR 0.0146. Consequence recorded at the
time: *price factors are permanently demoted to combiner-input-only status — they
may feed the ranker as features but are never a standalone strategy.*

Three things differ here, and all three are the reason the old null does not
answer this question:

| | BRAIN-002 | N1 |
|---|---|---|
| comparison | absolute, vs eligible EW universe | **paired, vs the hand-written composite** |
| clock | monthly | **annual**, the clock the book actually runs |
| features | the price big-three as the strategy | profitability composite ± a declared shelf, price factors **as ranker inputs only** |

N1 respects BRAIN-002's ruling rather than reopening it: price characteristics
enter as combiner inputs, never as a standalone book.

## 3. Arms (pre-declared; a grid, not a search)

| arm | ranking function | features |
|---|---|---|
| **R0** | the banked hand-written composite (**control**) | GP, OperProfRD, CBOperProf at equal weight |
| **R1** | GBM ranker | **the same three features** — isolates *learning the weights* at fixed information |
| **R2** | GBM ranker | the three + a declared shelf of seven native characteristics |
| **R3** | one-hidden-layer MLP ranker | the same wide shelf as R2 — isolates *model class* |

Declared shelf (frozen now, all already implemented and PIT):
`native:mom_12_1`, `native:rev_1m`, `native:vol_12m_low`, `native:max_ret_low`,
`native:price_level`, `native:liq_high`, `native:mom_36_13_low`.

Everything downstream of the score is **identical across arms**: small segment,
top 150, equal weight, hold band 3×, annual rebalance, era-appropriate KO costs,
the same eligibility mask, the same benchmark.

## 4. Training protocol (frozen)

- **Target:** forward 12-month log return, **cross-sectionally demeaned within
  month**, so the model learns ordering and cannot learn market timing.
- **Features:** cross-sectional percentile ranks within the eligible set, month
  by month — scale-free and directly comparable to how the composite is built.
- **Walk-forward, expanding window.** Refit at each annual rebalance; predict only
  months after the fit.
- **Purge and embargo:** the 12-month label window plus one month = **13 months**
  removed from the end of every training set. A model trained on a label that
  overlaps its prediction month is the leak this design exists to avoid.
- **Minimum training window:** 120 months. No prediction before it.
- **Hyperparameters frozen before compute** (they are not a search): GBM =
  400 trees, depth 3, learning rate 0.03, min 200 samples per leaf, subsample
  0.7. MLP = one hidden layer of 16 units, ReLU, early stopping on a
  chronological 15% tail of the training window. Seed 20260810.
- **Training rows capped at 300,000**, drawn uniformly at random with the same
  seed when the expanding window exceeds it. Frozen here because it is a
  compute decision that touches the result, and a compute decision made after
  seeing a result is a researcher degree of freedom. The cap binds only in the
  late window, and it binds identically for every arm.
- **Missing features:** LightGBM handles NaN natively and is given the raw
  ranks. The MLP cannot, and gets `SimpleImputer(strategy="median")` fitted on
  the training window only.

## 5. Power check — done BEFORE compute, and it constrains the claim

The baseline book's monthly excess vol is 6.01% (ann. 20.8%) over 482 months.
For a paired difference the detectable effect depends almost entirely on how
correlated the two books are:

| ρ(R0, Rk) | ann. sd of the difference | MDE at abs t 2.0, n=482 |
|---|---|---|
| 0.95 | 6.6% | **2.08%/yr** |
| 0.90 | 9.3% | **2.94%/yr** |
| 0.85 | 11.4% | **3.60%/yr** |
| 0.75 | 14.7% | **4.65%/yr** |

Two books drawn from the same 150-name pool should correlate 0.85–0.95, so the
MDE is **2–4%/yr**. Consequences, accepted in advance:

- **The bar is +3.0%/yr**, the standard's own adoption bar. A tighter bar would
  be unreachable and registering one would be theatre.
- **This design cannot resolve a 1–2%/yr difference and will not claim to.** If
  the realised MDE exceeds 3.0%/yr the verdict is **POWER_FAILED** whatever the
  point estimate says.
- What it *can* answer is the question actually worth answering: **is learning
  the weights a large win?** A null here rules that out; it does not rule out a
  small one.

## 6. Two questions, two instruments

The money question is underpowered by construction. The **ordering** question is
not, and conflating them is how a factory concludes "ML doesn't work" from a
portfolio-construction null.

- **Primary (money):** paired monthly net excess vs R0, annualised, Newey-West(12).
  Bar ±3.0%/yr as above.
- **Primary (ordering):** monthly **rank-IC** of each score against the forward
  12-month return within the eligible set, compared **paired** across arms. Roughly
  700 monthly observations and no portfolio-construction noise, so this resolves
  ordering differences the money instrument cannot see.

A result where the ranker orders better but does not earn more is
`IMPLEMENTATION_FAILED`, not `REJECTED` — that is a real and distinct state in
taxonomy v2, and it is the single most common outcome in this graveyard.

## 7. Decision rule (frozen)

| outcome | state |
|---|---|
| paired net excess ≥ +3.0%/yr and NW t ≥ +2.0 | `CONFIRMED` — learned weights beat written ones |
| paired net excess ≤ −3.0%/yr and NW t ≤ −2.0 | `REJECTED` — writing them is better |
| ordering IC materially better (paired t ≥ 2.0) while money is null | `IMPLEMENTATION_FAILED` |
| realised MDE > 3.0%/yr | `POWER_FAILED`, MDE printed |
| otherwise | `UNRESOLVED`, MDE printed |

**Leak check (voids everything):** an arm whose GROSS paired excess exceeds
+10%/yr is treated as a **leak until proven otherwise**, not a discovery. The
purge is the only thing standing between a forward-12m label and its own
prediction month, and a spectacular result is the symptom of it failing.

## 8. Registered predictions

1. **R1 ≈ R0.** Learning three weights over three highly correlated profitability
   signals has almost nothing to learn; I expect abs t < 1.0 and an UNRESOLVED.
2. **R2 and R3 order better than R0 on rank-IC** (paired IC t ≥ 2.0) — more
   information should improve ordering.
3. **No arm reaches +3.0%/yr net.** The wide-shelf arms will hold different names
   with more turnover, and NIGHT-7 measured what turnover costs.
4. **R3 (MLP) ≈ R2 (GBM).** The 2026-06-15 deep-research read was that algorithm
   choice is negligible (p = 0.640); this is a cheap direct test of that on our
   own data.
5. **The binding constraint is power, not the model.** Most likely single
   outcome across arms: UNRESOLVED with an MDE near 3%/yr.

## 9. Ledger

Adds **3 branches** (R1, R2, R3 against the R0 control). Counted before any
result is interpreted. Denominator moves 827 → 830.
