# NIGHT-7B — response to external review

**Date:** 2026-08-10 · **Branch:** `factory/night-7b` · **Receipts:** `runs/NIGHT7/`
**Reviews received:** 5 pasted, but **3 independent** — #3 and #5 are the same
document, and #4 is a transcript of the home session's own follow-up work
(the merge, the ROADMAP §12 "both tracks" decision, and Murat's reorder to
engine-and-ROI-first). Adjudicated below as three voices.

---

## 0. Scorecard on the reviewers

Applying the T1 standard to the reviewers themselves.

| review | verdict | note |
|---|---|---|
| **#3 / #5** (the methodology audit) | **strongest by a distance** | Caught a genuine error in my DSR wording, caught a self-inflicted CANON §15 violation, and proposed two experiments that both paid off. Every load-bearing claim carried its qualifier. |
| **#1** | mixed | Correct on the summary; but its headline "novel action" is actively harmful (see §5), and it invents numbers ("+1.0–1.5% expected edge", "105 high-turnover ideas") — the exact failure T1 documented. |
| **#2** | mostly ratification | Adds the A1-as-entry-veto idea (good, and #3 proposed a sharper version). Misquotes a cost figure ("$935k" — our numbers are $602,509 and $743,599). |

**Convergence (all three, independently): make citation qualifiers machine-required
metadata.** Adopted — see §6.

---

## 1. CORRECTION — the DSR wording was wrong ✅ fixed

Review #3/#5 is right, and this was my error.

> **Wrong:** "P(true excess Sharpe > 0) ≈ 0.55."
> **Right:** the historical survivor does not establish unique alpha once the
> search is accounted for.

DSR is not a Bayesian posterior over true alpha; it is a probabilistic-Sharpe
statistic against a *selection-adjusted benchmark Sharpe* under a sampling model.
I gave it more epistemic content than it carries, and then propagated the phrase
into STATUS, ROADMAP and memory.

The second half of the catch matters more. **GATE-M1 (2026-08-06) measured this
exact gate and found DSR ≥ 0.95 nearly powerless** — a measured 0% probability of
adopting a true α=0.6 edge. So T4 must not re-arm DSR as a universal kill gate.
The JSON always said `REPORTED-NEVER-DECIDING`; the prose now matches.

**DSR < 0.95 does not prove the strategy is false.** It says the historical
evidence, discounted for the search, is not exceptional.

Fixed in `docs/NIGHT7_VERDICT_2026-08-10.md` (headline + T4 + "what this night
changes"), `STATUS.md`, `ROADMAP.md` §6/§10, and the memory index.

**T4b is registered** (`TRIALS/PREREG_PF7B_SELECTION_BOOTSTRAP.md`): a White
Reality Check / Hansen SPA-style empirical selection-bias bootstrap that
block-bootstraps the *same* time blocks across all candidates, preserving their
real cross-correlation, and builds the distribution of the best statistic in a
null universe of *our own* candidates. That replaces arguing about N. Reviewer's
point that **179 is simultaneously too high and too low** (correlated variants
inflate it; rank-shape/clock/frequency/exit branches explored afterwards on the
same history deflate it) is recorded as the reason the bootstrap is the right
instrument.

## 2. CORRECTION — I violated my own CANON §15 the night I wrote it ⚠️→✅ measured

NIGHT-7 called the clock ensemble "free" on the strength of a **monthly-panel**
turnover number. CANON §15, written the same night, forbids exactly that. Fair
catch, and embarrassing in the right way.

**Measured** (`runs/NIGHT7/T1b_ENSEMBLE_G7.json`, 2002–2024 daily spine):

| at $1m | single clock (phase 5) | 12-sleeve ensemble |
|---|---|---|
| daily CAGR | +13.45% | +12.90% |
| lifetime cost | $333,165 | **$313,775** |
| turnover ($) | $91.2m | **$78.3m** |

**The ensemble is CHEAPER, not more expensive** — by $19,390 per $1m (and by
$1,316,887 per $50m, 2.6% of starting NAV). "Free" was wrong in the *conservative*
direction.

**The −0.55%/yr CAGR gap is not a cost.** The single clock here is **phase 5**,
which the monthly panel showed was an **above-average draw** (+4.11% vs the
12-phase mean +3.43%). Comparing the ensemble to a hindsight-selected good phase
and calling the gap a loss is the date-mining error the ensemble exists to
prevent. The gap *is* the date-luck finding, restated from the other side.

**Corrected wording, now standing:** *date-phase risk is real (a 2.45 pt/yr
descriptive range across twelve dependent cohorts — not a confidence interval),
and diversifying it away costs nothing and slightly reduces lifetime trading
costs.*

### A construction bug I caught in myself, mid-task

The first version of this measurement handed the simulator the **aggregate book
every month**. The simulator then traded monthly to reconcile the panel's monthly
drift against its own daily drift — spurious trades a real sleeve ensemble never
makes. It printed **−2.26%/yr and +$221,280 of extra cost**, and I nearly
reported it.

What caught it: measured turnover came out **1.51×** the single clock while the
panel said each sleeve turns over identically. That contradiction has no
explanation except a construction artifact. Rebuilt as **twelve independent
sleeves at NAV/12, each annual on its own phase, NAVs and costs summed** — which
is what the ensemble actually is. The discarded numbers are preserved in the
receipt under `rejected_construction`.

Same class of error as the `holdings_out` trap, found the same way: an invariant
that could not be true.

## 3. CLOSED — A3 segment drift, the prediction I failed to measure ✅

Late-computed, **non-decision-bearing**: it scores a prediction and changes no
verdict.

| arm | mean DV rank | drift first→last 5y | frac outside small |
|---|---|---|---|
| A0 baseline | 1802.8 | +361.6 | 0.161 |
| A1 trailing stop | 1734.6 | **+310.4** (least) | 0.187 |
| A2 momentum hold | 1801.7 | **+361.8** (most) | 0.160 |
| A3 fundamental break | 1804.3 | +350.2 | 0.162 |
| A4 earnings anchored | 1802.5 | +347.3 | 0.166 |

**Prediction 4: MISS.** A3 was *not* the worst drifter. More honestly, **no arm
differentiates**: the whole spread is 310–362 rank points on a 2000-wide segment.
The mechanism I hypothesised (unsold winners growing out of the segment) is not
visible at this resolution. Worker's score corrects to **1.5/5 with the fifth
item now resolved as a miss.**

## 4. NEW RESULT — the stop *trigger* carries information; the stop *vehicle* does not

Review #3/#5's best idea, and it paid off. G7 rejected the trailing-stop
implementation (−3.08%/yr). That says nothing about whether the trigger is
informative — a separable question, answerable without executing a single trade.

**Design.** Event study on the **baseline** book, which never sells on a stop. An
observer records the first trailing-stop trigger per holding episode and sells
nothing. Forward returns are demeaned **within month** against names held the
same month, so market direction, regime and the book's own factor tilt cancel.
1,833 triggers over 482 months.

**The obvious confound had to die first:** "fell 20% from its peak" is nearly a
momentum sort, and losers-continue-to-lose is Jegadeesh-Titman, not a discovery.
Three readings, all Newey-West with lags = horizon (forward *k*-month windows
sampled monthly overlap by *k*−1 months, so an i.i.d. t is inadmissible):

| horizon | RAW | MOM-NEUTRAL (residualised on within-month momentum rank) | MOM-MATCHED (same momentum quintile only) |
|---|---|---|---|
| +3m | −7.95%/yr (NW t −2.43) | −7.90% (NW t −2.43) | −8.40% (NW t −2.55) |
| +6m | −7.85%/yr (NW t −3.27) | −7.37% (NW t −3.04) | −7.44% (NW t −3.03) |
| +12m | −8.19%/yr (NW t −4.97) | −7.48% (NW t −4.37) | −7.24% (NW t −4.31) |

**It survives both controls essentially intact.** Momentum explains almost none
of it. (Newey-West *raised* the t-stats slightly — the diff series carries mild
negative autocorrelation.)

**What this is, stated precisely.** A measured within-book relative-return
difference: names that trigger a 20% peak-drawdown while held go on to
underperform their fellow holdings by ~7–8%/yr for at least a year, and not
because they are momentum losers.

**What this is NOT.** A strategy. NIGHT-7's own headline was a construction that
looked good and died on contact with execution — so this is registered, not
banked. It also adds to the trial denominator.

**Why it is nonetheless the most promising thing in weeks:** the natural vehicle
costs **zero extra turnover**. At the annual rebalance that is happening anyway,
penalise the rank of names that triggered during the year. No new trades, no new
churn, and therefore none of the −3.08%/yr that killed A1. Registered as
**TRIAL-PF7B-TRIGGER-PENALTY-1**, not run tonight.

That is precisely the "join two existing ideas to make a new one" Murat asked
for: take the information out of a failed high-frequency vehicle and deliver it
through the low-turnover clock we already ship.

## 5. REJECTED from the reviews, with reasons

1. **#1: "Run a robust optimization on the rebalance date using pre-2000 data;
   find the single date that maximises out-of-sample return."** **No.** This is
   date-mining a difference NIGHT-5 showed is unmeasurable (15 pairwise clock
   comparisons, none significant, ρ 0.958–0.993). The ensemble exists precisely
   to *stop choosing*. Picking the best historical phase is the error, not the
   fix — and #3/#5 independently says the same.
2. **#1: "+1.0–1.5% risk-adjusted expected edge from execution timing."**
   Invented precision, no derivation. This is the exact failure mode T1
   documented, arriving in a review *about* T1.
3. **#1: "105 high-turnover ideas are now more dead."** We never produced that
   number. The census is 148 rows / 74 killed by the experiment.
4. **#1: DSR tracker that auto-liquidates to cash when live Sharpe falls below a
   DSR threshold.** **Actively dangerous.** GATE-M1 measured this gate as nearly
   powerless; wiring an underpowered statistic to an automatic liquidation would
   convert a diagnostic into a capital-destroying trigger. Rejected on our own
   evidence.
5. **#2: "the graveyard as a reverse/short signal."** No mechanism, and the book
   is long-only. Also mines the graveyard, which is what the census warns against.
6. **#2: "$935k trading cost illusion."** Not our number ($602,509 / $743,599).

## 6. ADOPTED — infrastructure changes

- **Firewall: the veto channel was a loophole.** `set_weight()` raising is
  necessary, not sufficient — a VETO moves a name from eligible to weight zero,
  which is a portfolio decision. Now formalised: `CHANNELS` names five channels,
  only `portfolio_action` is owned by deterministic code; `VetoProposal` carries a
  **frozen reason vocabulary**, a Brier-scoreable probability, a resolution date
  and provenance; `apply_to_book()` **raises**; `Adjudication.to_veto_proposal()`
  is the only exit path from a VETO verdict. **32 firewall tests** (was 25).
- **CANON §15 scoped precisely** — the rule now targets *path-dependence*, not
  trading frequency: any strategy that can change positions **between scheduled
  snapshots** must be scored from the trade ledger. Monthly simulation stays valid
  for strategies whose only transactions occur on those dates and reconcile.
- **CANON §2 scoped** — it declared all backtests direction-checks-only because
  *free* data is survivorship-biased. The offline module runs CRSP/WRDS with real
  delisting returns. Both halves now stated separately, so NIGHT-7's inference is
  explicitly licensed and production free-data backtests remain restricted.
- **Citation qualifiers become required metadata** (all three reviews converged):
  every external empirical claim needs `population`, `sample_period`, `benchmark`,
  `long_only|long_short`, `gross|net`, `metric`, `risk_metric`, `horizon`,
  `effect_size`, `uncertainty`, `source_locator`, `pit_applicability`. A claim
  missing them cannot become a research prior. Registered for build.
- **NIGHT manifest + CI claim-check** — registered: a machine-readable map from
  every prose number to its receipt and JSON pointer, so CI can verify that a
  figure in a verdict doc is literally the figure on disk.

## 7. What did NOT change

The three headline results of NIGHT-7 survive review intact:

- **No tested exit arm demonstrated incremental benefit** (max paired |t| 1.24) —
  wording softened from "the exit layer is not where the money is," because five
  rules failing to separate is evidence about those five rules.
- **The trailing-stop implementation loses 3.08%/yr under measured execution**
  and pays $743,599 more per $1m over 23 years. All three reviews ratify;
  #3/#5 calls it one of the strongest findings in the project.
- **T6's power-check refusal** was correct and is ratified by all three.

## 8. Queue after this response

1. **T4b selection bootstrap** — the highest-value attack on the load-bearing
   claim. Registered, not run.
2. **TRIAL-PF7B-TRIGGER-PENALTY-1** — zero-turnover rank penalty at the annual
   rebalance. Registered, not run. **Most promising open item.**
3. Ship the clock ensemble to the shippable config (now G7-cleared: cheaper, and
   removes an unforecastable 2.45 pt/yr phase range).
4. Citation-qualifier schema + NIGHT manifest CI check.
5. PRisk extractor validation (unchanged, still gates the event pipeline).
