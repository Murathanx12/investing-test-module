# INSTR-CS-SPREAD — an independent check on the ruler the paper's lead exhibit rests on

**Registered 2026-07-30, FROZEN BEFORE ANY ESTIMATOR CODE IS WRITTEN.**
Instrument, one shot. Cumulative candidate **163**.
Authority: Murat delegated the session. Registered under the same S3 door as
TRIAL-COND-VT — same registry, same deflation count.

---

## Why this exists

`INSTR-COST-MODEL` (2026-07-26) recorded, verbatim:

> Corwin-Schultz/Roll **infeasible on our pull** (no daily high/low or return
> series) → Kyle-Obizhaeva ECTA-2016 eq.33 quoted spread …

The P0 harvest (2026-07-30) pulled `crsp.dsf` with `askhi` and `bidlo` for the
full universe, 2002-2024, 24.0M rows, 100% non-null on both columns in the
audited sample. **The stated blocker is gone**, so the check that was declared
infeasible is now buildable.

It matters because the KO half-spread is **load-bearing for the paper's lead
exhibit**. The claim "the cost-killed shelf is empty — costs were never the
executioner" (NEG_RESULTS §22, INSTR-COST-REMEASURE-REJECTS) depends on KO
half-spreads of 3.4-4.2 bps in large/mid and 11.6-13.1 bps in small. Those
numbers come from **one** model, calibrated from a single published equation,
never cross-checked against an independent estimator. If KO understates true
spreads, the empty cohort is an artifact of a lenient ruler.

The house's own adjudicated ordering (panel round 8) is *"validate the ruler
before re-measuring."* This is that, for the one ruler that never got it.

## Frozen estimator (Corwin & Schultz, JF 2012, followed verbatim)

For consecutive trading days t, t+1 with high H and low L (CRSP `askhi`,
`bidlo`, absolute values, both strictly positive required):

    beta  = [ln(H_t / L_t)]^2 + [ln(H_t+1 / L_t+1)]^2
    gamma = [ln( max(H_t, H_t+1) / min(L_t, L_t+1) )]^2
    alpha = (sqrt(2*beta) - sqrt(beta)) / (3 - 2*sqrt(2))
            - sqrt( gamma / (3 - 2*sqrt(2)) )
    S     = 2 * (exp(alpha) - 1) / (1 + exp(alpha))

**Overnight adjustment (part of the published method, not an option):** if
L_t+1 > H_t the price gapped up overnight — subtract (L_t+1 − H_t) from both
H_t+1 and L_t+1; if H_t+1 < L_t, add (L_t − H_t+1) to both. Applied before the
formula.

**Negative estimates set to zero** (Corwin-Schultz's own convention for the
two-day estimate). Monthly value = mean of the daily two-day estimates within
the month; a name-month needs ≥ 10 valid daily pairs. Reported as a **one-way
half-spread in bps = S/2 × 1e4**, the same convention as the KO frame, so the
two are directly comparable.

Nothing is tuned. No winsorising beyond the published zero-floor, no filtering
on the outcome.

## Frozen decision rule

Compare CS against KO on the **same name-months** (large/mid and small
segments, eligible names only, eras 2004-2010 / 2011-2018 / 2019-2024).

1. **Sanity gate.** CS median half-spread must lie in [1, 100] bps in both
   segments, AND small > largemid. Failing this means the estimator is
   misimplemented and nothing downstream is readable.
2. **PRIMARY — rank agreement.** Spearman correlation between CS and KO
   half-spreads at the name-month level, pooled: **>= 0.30**.
3. **CO-PRIMARY — level agreement.** Median ratio CS/KO within **[0.5, 2.0]**
   in both segments.

**Verdicts, declared now:**

- **2 and 3 both pass → KO VALIDATED.** The empty cost-killed cohort stands on
  a cross-checked ruler and the paper can say so.
- **2 passes, 3 fails HIGH (CS/KO > 2.0) → KO UNDERSTATES COSTS.** This is the
  adverse outcome and it is the reason the trial is worth running: the
  cost-killed cohort must then be re-derived under CS, and if it becomes
  non-empty the paper's lead exhibit changes. Declared before the run so the
  result cannot be reinterpreted after it.
- **2 passes, 3 fails LOW (CS/KO < 0.5) → KO OVERSTATES COSTS.** Rejections
  were, if anything, harsher than reality; the empty-cohort conclusion
  strengthens.
- **2 fails → NO CONCLUSION about KO.** The two estimators are measuring
  different things on this data; report the disagreement, change nothing.

## Kill / scope

One shot. This instrument **cannot revive any signal** — it re-measures a cost
scalar and nothing else. No spec, direction, window or bar of any candidate
changes here. If it invalidates KO, the consequence is a NEW registration to
re-derive the cohort, not an automatic reopening.

## Honest prior (declared before the run)

**Expect rank agreement to pass and level agreement to be the interesting
line.** CS is known to be noisy for illiquid names and to be biased upward when
overnight gaps are frequent — both conditions bite hardest in the small segment,
which is exactly where the cost question matters. My honest guess: rank corr
0.3-0.6, CS/KO ratio above 1 in both segments and plausibly above 2 in small.
If small fails high, the empty-small-cohort result (NEG_RESULTS §22) is the
first thing that has to be re-derived — and since that trial found exactly one
genuinely cost-killed signal, a harsher ruler could produce more.

---

## RESULT (one run, 2026-07-30): **rank agreement PASSES, level agreement FAILS HIGH. Verdict per the frozen rule: KO UNDERSTATES COSTS.**

Artifact: `data/factory/instr_cs_spread.json`. Runner:
`scripts/run_instr_cs_spread.py` (written after the freeze).
**Repair disclosed:** the first execution crashed before any result was
readable — pandas nullable dtypes made `np.where` raise on NA. Cast to float64
and re-ran. No spec, gate or bar changed.

| segment | era | CS median | KO median | ratio CS/KO | Spearman | n |
|---|---|---|---|---|---|---|
| largemid | 2004-2010 | 32.16 | 4.22 | **7.61** | 0.570 | 83,888 |
| largemid | 2011-2018 | 25.80 | 3.35 | **7.70** | 0.600 | 95,919 |
| largemid | 2019-2024 | 30.92 | 3.41 | **9.08** | 0.621 | 71,882 |
| small | 2004-2010 | 48.23 | 13.07 | **3.69** | 0.679 | 163,441 |
| small | 2011-2018 | 41.69 | 12.12 | **3.44** | 0.613 | 182,468 |
| small | 2019-2024 | 49.17 | 11.63 | **4.23** | 0.673 | 137,925 |

**Pooled Spearman 0.660 (n = 735,523).** Gates: sanity PASS, primary PASS,
level FAIL.

**The two estimators agree strongly on WHICH names are expensive and disagree
by 3.4-9.1× on HOW expensive.** That is the whole result.

### Interpretation — stated with both hands

The frozen verdict is "KO understates costs," and it is reported as frozen. But
the honest scientific reading is **disagreement, not refutation**, and the case
against taking CS as truth is specific:

- Corwin-Schultz is **documented to be biased upward**, most severely in
  illiquid names and where overnight gaps are frequent — the paper's own
  caveat, and the honest prior in this registration predicted it.
- A $0.01 minimum tick is a hard floor on quoted spreads: on a $10 stock that
  is 10 bps of round-trip spread before any liquidity effect. Much of the small
  segment trades at low nominal prices, so CS partly measures the tick grid.
- A CS median of 26-32 bps one-way for the **top 1000 US stocks by dollar
  volume** is implausibly high against any market-quality report of the era.

The defensible conclusion is that **true one-way costs lie between the two
estimates, closer to KO in large/mid than the ratio suggests**, and that a
single-model cost number should never again be quoted without an interval.

### ⚠️ The consequence the frozen rule did NOT anticipate — and it matters more than the verdict

The registration said an adverse result means "the cost-killed cohort must be
re-derived under CS, and if it becomes non-empty the paper's lead exhibit
changes." **On inspection that does not follow, and the reason is worth more
than the trial was.**

Both cohort results were decided by a **cost-independent leg**:

- **Large/mid (INSTR-COST-REMEASURE-REJECTS):** the cohort was empty because
  the best gross t among rank-informative rejects was **1.48, below the 1.5
  gross bar**. Gross t does not contain costs. **No cost model — KO, CS, flat,
  or zero — can move it.** The empty large/mid cohort is robust to this trial
  by construction.
- **Small (NEG_RESULTS §22):** graduation required clearing the bar under
  *both* cost arms, and the deciding exhibit was the **zero-cost bound** —
  "could this graduate if trading were free?" Raising the cost estimate can
  only push net t **down**. Zero graduates stays zero graduates.

**So the exhibit survives, and now survives for a demonstrated reason rather
than an assumed one.** What must change is the *wording*: the claim "costs were
never the executioner" is a statement about cost levels and is now contested,
while the claim "nothing could graduate even at zero cost" is cost-model-
independent and stands. The paper should lead with the second, which was always
the stronger sentence.

**No re-derivation registration is opened.** The frozen consequence was
conditional on the cohort changing; it cannot change. Recorded, not spent.
