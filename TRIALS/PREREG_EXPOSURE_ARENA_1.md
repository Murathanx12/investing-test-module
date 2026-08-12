# PREREG — EXPOSURE-ARENA-1: eight exposure controllers against a matched-average-exposure frontier that is built before any of them exists

**Registered** 2026-08-12, GRAND-ARENA-1 **CHUNK 6**, **before any controller
path is computed and before the frontier file exists on disk.**
**Binding law:** `aegis-finance/docs/GRAND_ARENA_1_AMENDMENT_A.md` §A1, §A7,
§A9, §A10, §A11. **Family:** exposure / de-risking overlay (allocation layer).
**ACCRUES ZERO ARMS.** No lane, no shadow default, no order path, no sizing
change, whatever the outcome. This is a measurement chunk in a research
campaign.

**Parents, named because they constrain what this may claim:**

* **EXPOSURE-CONTROL-1** (NIGHT-13, `UNRESOLVED` by 1.4 bps of terminal
  wealth; the constant-exposure control BEAT the ladder on the holdout) —
  `TRIALS/PREREG_EXPOSURE_CONTROL_1.md`, receipts
  `aegis-finance/docs/NIGHT13_EXPOSURE_CONTROL.md`.
* **TRIAL-COND-VT** (index-keyed, month-end conditional vol targeting —
  CLOSED; passed explore, failed confirm).
* **KNOWN-WORLD-L** (GRAND-ARENA-1 Phase 1): in a world built with **no timing
  edge at all**, the evolutionary learner produced Sharpe 0.500 vs a static
  0.478 by sitting at zero exposure 52% of months. Only matched-average-exposure
  comparison and its own MDE refused it. That world is the reason this chunk has
  the shape it has.
* **EXIT-LAB-1**: the cost model, the regime-block/half convention and the
  "print the whole search denominator" convention are reused verbatim.

---

## 0. Resurrection declarations, argued rather than asserted

Resurrects: PREREG_EXPOSURE_CONTROL_1 — new instrument: the **matched-average-exposure frontier is the PRIMARY comparator and is computed and written to disk BEFORE any controller exists**, replacing a wealth bar measured against the unmanaged book; and the denominator moves from 6 calibration episodes plus ONE 188-day holdout window (whose own terminal-wealth-ratio SE was 0.165 — it could not distinguish 0.85 from 0.70) to **~24,700 daily observations spanning 1926-07-01 to 2024-12-31 across three beds, ten decade regime blocks and both sample halves**, a ~11x reduction in the standard error of the very statistic that decided the parent trial (sqrt(24700/188) = 11.5).

Resurrects: TRIAL-COND-VT — new instrument: the question is inverted. COND-VT asked whether index-keyed volatility targeting beats buy-and-hold, and that question stays CLOSED. This trial never compares a controller to buy-and-hold as its primary metric; it compares every controller to **its own average exposure held constant**, which is a comparison COND-VT never made and which can only ever REMOVE apparent edge, never manufacture it. A null here corroborates COND-VT; a positive here would license nothing on its own, because §A11 requires replication and §A7 forbids certification on this data.

**Why these declarations are not a loophole.** Both parents are `UNRESOLVED` /
closed *timing* questions, and the honest risk of re-running them is that a
larger denominator eventually finds a false positive. The protection is
structural, not rhetorical: (i) the primary comparator is the one that
*subtracts* the de-risking channel; (ii) every arm prints its own measured
80%-power MDE and below-MDE is never a win (§19); (iii) the entire
configuration count — including every failed and unflattering config — is
published as the denominator (§A8); (iv) nothing can be promoted from this
chunk by construction.

---

## 1. THE OBJECTIVE, FROZEN BEFORE ANY OPTIMISATION (§A9)

**ONE wealth objective.** Net **annualised terminal log wealth** (net CAGR) of
the managed path over the full evaluation sample of the bed, with cash earning
the daily risk-free rate and all trading charged (§4). Nothing else is optimised
and nothing else is maximised anywhere in this trial.

**PRIMARY METRIC — the headline of the whole chunk.** For every dynamic
controller `X` on every bed:

```
D_matched(X)  =  netCAGR(X)  -  netCAGR( MATCH(w̄_X) )      [pp/yr]
```

where `w̄_X` is X's own realised mean **applied** exposure over the evaluation
window and `MATCH(w̄)` is the constant-exposure policy at that same mean, paid
the same cost model, cash at the same risk-free rate. `D_matched` is the
controller's **timing content**: the part of its result that is not explained by
holding less.

**Risk profiles are reported SEPARATELY and are NOT inside the objective**
(this is the §A9 trap the amendment names, and it is closed here): max drawdown,
CVaR(5%) of monthly net returns, and ruin probability are each reported for
every controller beside the matched control at the same mean exposure. They may
qualify a verdict. They may never rescue a wealth objective, and the objective
may never be swapped for one of them after seeing results.

**Ruin probability, definition stated as required.** `P(ruin)` = the probability
that a **10-year (2,520 trading day)** path, drawn by 21-day circular block
bootstrap (N = 2,000, seed 20260812) from the controller's own **net daily
return series**, at any point falls below **0.50 x its starting wealth**. This
is a property of the return distribution, not of the historical path, and it is
computed identically for every arm including the matched controls.

---

## 2. Hypotheses, with honest priors

| # | hypothesis | prior |
|---|---|---|
| **H1** | At least one dynamic controller beats its own matched-average-exposure cousin on net CAGR by more than that arm's own 80%-power MDE, with the sign holding in >= 6/10 regime blocks and both halves. | **LOW, ~15%.** Five nights point at exposure; none has yet produced timing content over "hold less". WORLD-L showed the failure mode from the inside. |
| **H2** | Controllers reduce drawdown/CVaR/ruin materially versus 100% exposure, and the matched-exposure control reduces them **just as much**. | **HIGH, ~75%.** This is the NIGHT-13 holdout result (constant control: dd -11.50% vs ladder -12.55%, wealth 0.914 vs 0.850) generalised. |
| **H3** | The **learned** controller (G) invents a timing rule that looks good raw and dies against the matched control, reproducing WORLD-L on real data. | **MEDIUM-HIGH, ~60%.** Explicitly the adversarial case; the evolutionary searcher is included *because* it is the learner that did this in the known-answer world. |
| **H4** | The oracle upper bound (H) is large, i.e. a great deal of timing value exists in principle and the failure of A-G is a failure of *observability*, not of *availability*. | **HIGH, ~85%.** WORLD-D's known-answer form: perfect foresight was worth +19.03%/yr while the best observable-precursor policy was worth +3.01%/yr — 84% unreachable in principle. |
| **H5** | Any controller that does clear H1 on one bed fails to replicate on the other two, or in one of the two halves. | **MEDIUM, ~50%.** Stated in advance so a single-bed positive cannot be reported as a finding. |

---

## 3. The beds, frozen

| bed | series | span | days (approx) | role |
|---|---|---|---|---|
| **BED-1 — MARKET (PRIMARY)** | `r = mktrf + rf`, the CRSP value-weighted market total return, `data/wrds_raw/ff_factors_daily.parquet` | 1926-07-01 → 2024-12-31 | ~24,700 | primary; the far larger denominator |
| **BED-2 — LEVERED 2.15x** | `r = 2.15*mktrf + rf`, the frozen NIGHT-13 proxy for a concentrated high-beta book | 1926-07-01 → 2024-12-31 | ~24,700 | the parent's own bed, so the parent is directly comparable |
| **BED-3 — REAL CRSP BOOK** | equal-weighted daily return of the top-1,500-by-63d-median-dollar-volume liquid universe (price >= $5, >= 252d history), monthly reconstitution, CRSP delisting returns spliced at `dlstcd >= 200`, from `data/factory/wg1_panel.npz` | 2002-01-02 → 2024-12-31 | ~5,700 | **DEVELOPMENT / SECONDARY VALIDATION ONLY (§A7).** Carries the idiosyncratic gap risk BED-1/2 structurally cannot. |

**§A7 is binding and is stated here rather than in a footnote:** CRSP 2002-2024
has been interrogated across many nights of this programme and **is not a
pristine holdout**. BED-3 is development and robustness. BED-1/2 extend to 1926
and the pre-2002 portion is materially less interrogated by this programme, but
it is *public, ancient, and famous*, and no foundation model or human is naive
to 1929, 1973 or 1987. **Nothing in this chunk may be called certified.**
Certification requires genuinely untouched data or the forward paper
tournament, and this document says so in advance so the verdict cannot claim
otherwise.

**Evaluation window per bed** excludes a frozen 252-trading-day warm-up at the
start (the longest trailing window any controller uses), so no arm is scored on
days where its own signal did not exist. The warm-up count is printed.

---

## 4. Costs — the repo's model, not a new one

| bed | one-way cost charged on |Δw| | provenance |
|---|---|---|
| BED-1, BED-2 | **5.0 bps** | `scripts/exit_lab_core.py::BENCH_BPS = 5.0` — "all-in cost of the market leg (an index fund, not a small cap). Declared, not fitted." |
| BED-3 | **30.2 bps** | EXIT-LAB-1's measured Corwin-Schultz half-spread **median 24.2 bps** on this exact universe + `SimConfig.slippage_bps 5.0` + `SimConfig.commission_bps 1.0` = 30.2 |

**Cost sensitivity, pre-declared:** every headline is re-reported at
**0x (gross), 1x (decides), 2x, 4x**. The 0x column exists because EXIT-LAB-1
found a verdict that lived entirely in the cost term, and a reader is entitled
to see which channel decides this one.

Cash earns the daily risk-free rate `rf` (NIGHT-13 froze cash at 0 and recorded
that as a limitation worth ~1.5pp on its holdout; that limitation is removed
here, identically for every arm including all matched controls, and it is
declared **before** any result).

**Application convention, frozen:** a weight decided from data at `t` is applied
to the return of `t+1` (one-day lag), for every controller without exception,
including the oracle. Turnover is `|w_t_applied - w_{t-1}_applied|`.

---

## 5. THE MATCHED-AVERAGE-EXPOSURE FRONTIER — built FIRST (§A1)

**Stage 2 of the runner, executed before any controller module is imported, and
written to `data/factory/exposure_arena_1_frontier.json` before Stage 3
begins.**

For `w̄` on the frozen grid `0.00, 0.05, 0.10, ..., 1.00` (21 points) and, per
bed, additionally at the exact realised `w̄_X` of every controller once known,
the constant-exposure policy is simulated: constant `w̄` in the book, `1 - w̄` in
cash at `rf`, one initial rebalancing trade from 1.0 charged at the bed's cost,
zero ongoing turnover. Every metric of §6 is computed on it.

**A dynamic controller is scored against the frontier point at its OWN realised
mean applied exposure.** The frontier is a pure function of `w̄` and the bed. It
has no free parameters, no fitting step, and it exists on disk before any
controller path is computed, so **it cannot be tuned to lose.**

The four §A1 controls, all reported for every controller:

| control | definition |
|---|---|
| **(a)** 100% exposure | `w = 1.0` |
| **(b) MATCHED — the one that decides** | constant `w = w̄_X`, X's own realised mean applied exposure |
| **(c)** static beta targeting | `w_t = min(1, β*/β_63d(book vs market))`, `β* = 1.5` frozen (NIGHT-13's stated prior, never tuned) |
| **(d)** static volatility targeting | `w_t = min(1, σ*/σ_63d(book))`, `σ* = 0.15` frozen |

**Declared degeneracies, stated in advance so they are not reported as
findings.** On BED-1 the book IS the market, so `β_63d = 1` and control (c) is
`w = 1` identically. On BED-2 `β_63d = 2.15` by construction, so control (c) is
the constant `w = 0.698` — a de-lever, not a signal; NIGHT-13 recorded the same
thing. Control (c) is non-degenerate only on BED-3.

> **The sentence this trial is built to be able to say, quoted from §A1 and
> pre-committed here:** *if a controller cannot beat its dumb matched-exposure
> cousin, it did not discover timing — it discovered de-risking.* If that is
> the result, it will be written in those words.

---

## 6. Scoring — the §A10 decomposition, every number beside its own MDE

Per controller, per bed, per cost multiplier:

1. **terminal wealth** (and vs matched)
2. **net CAGR** (PRIMARY OBJECTIVE) and **`D_matched`** (PRIMARY METRIC)
3. **max drawdown** (daily marks)
4. **CVaR(5%)** of monthly net returns
5. **bull capture** = mean net return on days the *book* is up / mean book return on those days
6. **bear capture** = same on days the book is down
7. **missed-upside cost** = annualised `Σ (1 - w_t) * r_t` over days with `r_t > 0`
8. **avoided-loss benefit** = annualised `Σ (1 - w_t) * (-r_t)` over days with `r_t < 0`
9. **turnover** = `Σ |Δw|` (one-way, x NAV) and annualised
10. **costs paid**, bps of NAV per year
11. **time spent de-risked** = share of days with `w < 0.999`, plus share with `w < 0.5`
12. **re-entry efficiency** = (annualised book return during de-risked spells) − (annualised book return over the whole sample). Negative = the controller was out during genuinely bad stretches. A *spell* is a maximal run of days with `w < 0.75`. Reported with its own MDE.
13. **ruin probability** as defined in §1.

**Identity check that must hold (asserted at runtime, aborts on failure):**
`netCAGR(X) - netCAGR(FULL)` must equal `avoided − missed − costs` in log-wealth
terms to float tolerance. Items 7 and 8 are otherwise decorative.

**MDE (§19), measured not assumed.** For any paired difference of two daily net
return series on the same dates, MDE(80%) is computed from a **21-day circular
block bootstrap (N = 2,000, seed 20260812)** on the *demeaned* paired daily
log-return difference: `MDE_daily = q95(null mean) − q20(null mean)`, reported
annualised as `MDE_daily * 252` in pp/yr. This is `mde_wealth()` from
`scripts/run_exposure_control_1.py`, reused. Drawdown MDEs use the planted-shave
method of `mde_dd_vs_bar()` from the same file. **Below its own MDE is NOT
DETECTABLE — never a kill and never a win.**

**Regime blocks and halves.** BED-1/2: ten decade blocks
`1926-34, 1935-44, 1945-54, 1955-64, 1965-74, 1975-84, 1985-94, 1995-2004,
2005-14, 2015-24`; halves split at 1975-12-31. BED-3: EXIT-LAB-1's eight blocks
`2002-03, 2004-06, 2007-09, 2010-12, 2013-15, 2016-18, 2019-21, 2022-24`; halves
split at 2013-06-30. Sign consistency of `D_matched` is reported for every arm.

---

## 7. The controllers, all parameters frozen here

Every controller outputs a weight in `[0, 1]` decided from data `<= t`, applied
at `t+1`. No leverage anywhere.

| id | controller | frozen primary configuration | declared grid (all executed, all reported) |
|---|---|---|---|
| **A** | `FULL` | `w = 1` | — |
| **B** | `STATIC_50` | `w = 0.5` | — |
| **C** | `VOL_TARGET` | `w = min(1, 0.15/σ_63d)` | `σ* ∈ {0.10, 0.15, 0.20, 0.25}` x `window ∈ {21, 63, 126}` = 12 |
| **C2** | `BETA_TARGET` | `w = min(1, 1.5/β_63d)` | `β* ∈ {1.0, 1.5, 2.0}` = 3 |
| **D** | `LADDER` (NIGHT-13, imported verbatim, **not re-tuned**) | `min(w_vol, w_beta, w_dd)`, `σ*=0.15, D*=10pp, β*=1.5`, dwell 10td, hysteresis 5pp | the parent's full 3x3 `σ* x D*` grid = 9 |
| **E** | `REGIME` (observable state, §A2: HMM is a control, not a feature) | 2x2 state = (book price vs its 200d MA) x (σ_63d vs its trailing 5y median); exposure map **(up,lo)=1.0 (up,hi)=0.7 (down,lo)=0.6 (down,hi)=0.3**, declared a priori | MA ∈ {50, 100, 200} x {2x2 map, trend-only map (1.0/0.5)} = 6 |
| **F** | `EVENT` (geopolitical) | monthly `GPRH` (Caldara-Iacoviello historical GPR, 1900-), **lagged one full month**, z-scored on a trailing 10-year window; `w = 1.0` if `z <= 1.0` else `0.5` | threshold `∈ {0.5, 1.0, 1.5}` x floor `∈ {0.3, 0.5, 0.7}` = 9, plus a daily-`GPRD` variant on 1985+ = 1 |
| **G** | `LEARNED` | see §7.1 | 3 families x 1 primary mapping = 3, plus per-family folds |
| **H** | `ORACLE` | perfect foresight of the next 21 trading days' book return; `w = 1` if positive else `0`, decided every 21 days | daily-foresight variant = 1; `k`-day ∈ {1, 21, 63} = 3 |

**Controller F carries a disclosed defect and is labelled with it.** The GPR
series is a **revised, backfilled newspaper text index**; the archive in
`data/macro/gpr_snapshots/` is a 2026-07 vintage. Its historical values are
**not point-in-time**. Controller F is therefore an **optimistic bound** on what
a geopolitical conditioner could have done, is labelled `NON_PIT` in every
table, and may not be promoted, quoted as tradeable, or compared to the PIT
controllers as an equal.

### 7.1 The learned controller (G), protocol frozen

* **Features (all causal, from the book path and rf only, plus GPR for the one
  declared variant):** `σ_21, σ_63, σ_252` (annualised realised), `σ_21/σ_252`,
  `log(P/MA50)`, `log(P/MA200)`, drawdown from 252d peak, `mom_252`, `mom_21`,
  downside/upside semi-vol ratio (63d), `rf` level, 63d change in `rf`.
* **Target:** forward 21-trading-day book excess log return.
* **Protocol:** expanding-window walk-forward. First training block 1926-07-01
  → 1955-12-31; retrain every 5 calendar years; **purge + embargo of 42 trading
  days** (twice the label horizon) between train and test. **Every scaler and
  imputer fitted inside the training fold.** Predictions used out-of-fold only.
* **Families (chosen from the KNOWN-WORLDS §5 trust table, with its verdicts
  quoted):** `ridge` (TRUSTED as a detector), `lightgbm` (TRUSTED with the
  stated caveat that any conditional structure needs independent confirmation),
  `evolutionary` (CONDITIONALLY TRUSTED — *"it invented a timing rule in world L
  that only matched-exposure comparison plus an MDE refused. Never report an
  evolutionary result without both."* Both are the primary metric here, which is
  why it is included rather than excluded).
* **Explicitly NOT run:** conservative offline-Q. KNOWN-WORLDS §5 rates it
  **NOT TRUSTED for exit/action work** — structurally biased toward the
  do-nothing/cash action, because a pessimism penalty has nothing to subtract
  from cash's certain zero. In an *exposure* trial that bias is exactly the
  failure mode under test, and it would enter as a broken instrument. This is a
  **declared non-run**, recorded in the denominator as such.
* **Exposure mapping, frozen:** `w = clip(0.5 + 0.5 * z, 0, 1)` where `z` is the
  fold's prediction standardised by the **training fold's** prediction mean and
  sd. The evolutionary family instead searches genomes of 3 `(feature,
  threshold, w_lo, w_hi)` rules combined by `min`, population 200, 40
  generations, fitness = training-fold net log wealth, `np.random.default_rng`
  seed 20260812.

---

## 8. Decision rule, frozen

Per controller x bed, on the primary configuration, at 1x costs:

| condition | verdict |
|---|---|
| `D_matched >= its own MDE` **AND** same sign in >= 6/10 (BED-3: >= 5/8) regime blocks **AND** same sign in both halves | **`TIMING_DETECTED`** |
| `D_matched >= its own MDE` but coverage fails | **`UNRESOLVED_UNSTABLE`** |
| `\|D_matched\| < its own MDE` **AND** the controller's maxDD is shallower than `FULL` by >= 5pp | **`DE_RISKING_ONLY`** — reported in §A1's words: *it did not discover timing, it discovered de-risking* |
| `\|D_matched\| < its own MDE` and no material drawdown change | **`UNRESOLVED`** (never a kill, §19) |
| `D_matched <= -its own MDE` with coverage | **`TIMING_HARMFUL`** |

**Chunk-level headline, frozen:** *did ANY controller reach `TIMING_DETECTED`
against its matched-average-exposure control* — and if so, on how many of the
three beds, since §A11(3) names exactly this as a candidate BREAKTHROUGH and
**one bed is not a replication**. The word BREAKTHROUGH may be used only if the
same controller family clears on **>= 2 beds and both halves of each**, and even
then the report must state that §A7 forbids calling it certified.

**§20 batch self-check, pre-committed.** Across all executed configurations the
report prints: how many arms clear their own MDE, against the nominal
false-positive expectation at the one-sided 5% rate implied by the MDE
construction, and the **effective** number of distinct configurations (mean
absolute pairwise correlation of the arms' daily `D_matched` series), because
44 configurations that are variations of four mechanisms are not 44 independent
chances.

**Runtime assertions that VOID an arm (abort, not warn):**
1. **Look-ahead perturbation proof** — for each controller, at a named probe
   date, every return strictly after the probe is perturbed and the decided
   weight must come back **bit-identical**. Failure aborts the run. (The oracle
   is exempt **by construction and is labelled IMPOSSIBLE**; its perturbation
   test is asserted to FAIL, which is the proof the harness can detect
   look-ahead at all.)
2. The `avoided − missed − costs` identity of §6.
3. Zero NaN weights; every weight in `[0, 1]`; the warm-up exclusion applied.
4. The matched-exposure frontier file exists on disk with an earlier mtime than
   every controller artifact.

---

## 9. What this may NOT conclude

1. **No alpha claim, no Sharpe headline, no skill claim, no money claim.** No
   lane, no shadow default, no sizing change, no product default, no buy/sell
   language. Nothing here moves anything.
2. **No certification (§A7).** BED-3 is interrogated data; BED-1/2's pre-2002
   history is public and famous. Certification is the forward paper tournament
   or genuinely untouched data, and this trial has neither.
3. **A null on these eight controllers is a null on THESE controllers.** It is
   not "exposure timing is impossible". The oracle arm exists precisely to say
   how much was available and therefore how much a better-observed controller
   could still find.
4. **Below MDE is not a kill (§19).** Every not-detectable arm's MDE is printed
   so a reader can see exactly how large an effect would have had to be.
5. **BED-1 and BED-2 have no idiosyncratic gap risk** — a diversified market
   path scaled up is not a concentrated book, and a gap jumps *through* a daily
   overlay. BED-3 is the partial answer; a 12-name book is still not measured.
6. **Controller F is not point-in-time** (§7) and is an optimistic bound.
7. **This is a single-asset exposure overlay.** It says nothing about which
   names to hold, and nothing about intraday execution, tax, liquidity needs or
   any constraint a real saver optimises that this instrument never measured.

## 10. Result

Filled after the run, never edited. Receipts to
`aegis-finance/docs/GRAND_ARENA_EXPOSURE.md`; artifacts
`data/factory/exposure_arena_1_*.json`; runner
`scripts/run_exposure_arena_1.py` (+ `exposure_arena_core.py`).
