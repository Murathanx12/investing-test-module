# INSTR-RESID-MOM — residual momentum: the one momentum variant with post-publication OOS survival

**Registered 2026-07-30, FROZEN BEFORE ANY SIGNAL CODE IS WRITTEN.**
Two candidates (largemid + small) → cumulative **162**.
Authority: Murat delegated the session; registered under the same S3 door as
TRIAL-COND-VT — same registry, same deflation count. Murat's to overrule.

---

## Admissibility — why this is not a re-litigation

The momentum-lane inquiry was **CLOSED** by the pre-registered stopping rule of
TRIAL-MOM-TREND (#14, NEGATIVE_RESULTS §10):

> Per the pre-registered stopping rule: the momentum-lane inquiry is CLOSED for
> this window. **No third variant.**

with the standing house qualifier that a closed family may only be re-entered
by a **new mechanism class**. Residual momentum qualifies, and the argument is
specific rather than rhetorical:

- #13 and #14 both ranked on **total** 12-1 return and differed only in *when
  the book was held* (unfiltered vs 10-month-SMA cash filter). The recorded
  cause of death was a **momentum crash**: maxDD −54.7%, and the trend filter
  made it **worse** (−61.3%) by selling the bottom and missing the V-rebound.
- Residual momentum changes **what is ranked**, not when it is held: the
  formation return is residualised against the factor model *before* ranking,
  which removes precisely the time-varying factor loadings (market beta, size,
  value) that produce the crash. The mechanism is orthogonal to the timing
  mechanism that failed twice.
- Blitz-Huij-Martens (JEmpFin 2011) and Blitz-Hanauer-Vidojevic (IRFA 2020,
  *The idiosyncratic momentum anomaly*) report comparable average returns at
  **roughly half the volatility**, robustness across global universes,
  **survival out-of-sample after publication**, and — load-bearing here — the
  **absence of the long-term reversal** that drives momentum crashes.

Prior-check run 2026-07-30 (`scripts.prior_check "residual momentum"
"idiosyncratic momentum" resid_mom`): 86 hits reviewed. No prior registration
of a residualised formation return anywhere in the corpus. Adjacent closed
families checked and distinguished: total-return momentum (#13/#14, this
document), `mom_6_1`/`mom_12_1` (batch 1, total return), low-vol/lottery
(`skew_low`, `max_low` — a *screen* on realised vol, not a residualised return),
`conn_mom`/`industry_mom`/`cust_mom` (spillover class, different information),
`qual_mom` (an interaction, refused as a casual blend).

---

## Frozen specification (Blitz-Huij-Martens 2011, followed verbatim — nothing invented)

At each formation month-end **m**, for every panel name:

1. **Estimation window:** months `m-35 … m` (36 monthly observations).
   Require **all 36** present; otherwise the name has no score this month.
2. **Model:** OLS of excess return `r_i,t − rf_t` on **FF3** — `mktrf`, `smb`,
   `hml` — from `data/ff_factors.parquet`
   (sha256 `54e3b8dd…0917eb11`, Ken French, coverage 1963-07..2026-05).
   FF3 is BHM's model and is frozen here; FF5/FF6 variants are **not** a retune
   option under this registration.
3. **Signal:** over the 11 months `m-11 … m-1` (the standard 12-1 skip — the
   most recent month **m** is excluded), take the model residuals `e_i,t` and set

       resid_mom_i,m = mean(e_i, m-11..m-1) / stdev(e_i, m-11..m-1)

   Direction **+1** (long high residual momentum). The standardisation by the
   residual standard deviation over the *same* window is BHM's definition and
   is part of the frozen spec, not a normalisation choice.
4. Names whose residual standard deviation is zero or non-finite get no score.

**PIT status:** every input (past returns, published FF factors) is known at
month-end `m`; the book is held over month `m+1`. No forward information. The
FF file is a pinned vintage whose mtime is an upper bound on its download date
(`ff_factors_VINTAGE.json`) — the factors themselves are published monthly with
a lag and are not restated, so the vintage risk here is nil, but it is stated.

**Harness:** byte-identical to every other factory scan — `factory/explore.py`,
top decile, 30% hold-band incumbency, EW-universe benchmark, explore window
2004-01..2018-12. No new harness code, no new economics.

---

## Frozen decision rule

**Segments and cost arms (both bars declared now, so neither is chosen later):**

| segment | cost | graduation bar |
|---|---|---|
| `largemid` | flat 25 bps (house standard) | `t_excess_net >= 1.5 AND t_ic >= 2.0` |
| `small` | **KO half-spread** (the measured small-cap cost, INSTR-COST-MODEL; ~12 bps) | `t_excess_net >= 1.5 AND t_ic >= 2.0` |

The small-segment cost arm is KO-half rather than flat-25/50 because
INSTR-COST-MODEL measured the flat wall to be a 2-4× over-penalty there; that
measurement predates this registration and is not conditional on
INSTR-SMALL-SHELF's outcome. Flat-25 small numbers are reported alongside, as
the comparability bridge to the other 159 candidates.

**Any graduate → ONE confirm run**, 2019-01..2024-12, same segment, same cost
arm. **PASS iff** mean net excess > 0 **AND** `t_excess_net >= 0.8` **AND**
`t_ic >= 1.5`. DSR reported at `n_trials = 162`. FF6 alpha reported.

**Always reported, never deciding:** turnover, maxDD (the co-primary *claim* of
the residual construction — BHM's headline is risk reduction, so a REJECT with
a materially shallower drawdown than `mom_12_1` is a meaningful negative
result and must be stated), the paired comparison against banked `mom_12_1`
rows, and monthly IC series.

---

## Kill condition (frozen)

No graduate in **either** segment → the residual-momentum family is **CLOSED**,
the momentum family is closed at **both** total-return and residual resolution,
and there is **no third variant** — a successor requires a mechanism class
distinct from both timing and residualisation, registered fresh. No parameter
switching: the 36-month estimation window, the FF3 model, the 11-month
`m-11..m-1` signal window, the standardisation, and the +1 direction are all
frozen. A sign flip is a new candidate in a future batch, not a free retry.

Confirm-window rule identical: any bar missed → REJECT, no re-reading.

---

## Honest prior (declared before the run) — **WEAK, and the adverse evidence is specific**

Stated before any residual-momentum number exists, because the adverse evidence
was found during the pre-registration audit and hiding it would invert the
purpose of this document.

**Banked `mom_12_1` on our own panel** (`data/factory/batch1_summary.csv`,
flat 25 bps, explore 2004-2018):

| segment | t_ic | t_gross | t_net | net excess |
|---|---|---|---|---|
| small | **+3.05** | **−1.50** | −1.94 | −39.7 bps/mo |
| largemid | +0.63 | −0.82 | −1.17 | −28.6 bps/mo |

**The binding constraint is the book, not the wall.** In small caps the *rank*
information in total-return momentum is already real and strong (IC t 3.05) and
the top-decile long book still loses **gross** (t −1.50). A transformation whose
documented benefit is better *ranking* and lower *volatility* therefore has to
do something the evidence does not directly promise: turn a gross-negative book
positive. It is coherent that it could — the top total-momentum decile in small
caps is a high-beta, high-vol basket and residualising strips exactly that
loading — but it is a mechanism story, not a measured one.

Against: five recorded sign reversals in this factory; CZ-CALIB rank correlation
**−0.544** between published t and our measured t (the more celebrated, the
deader); the confirm wall has killed every graduate handed to it except
gp-small; and the house's own receipt that in large/mid *nothing* had a
gross-passing book.

For: residual momentum is one of a short list of anomalies with an explicit
post-publication out-of-sample survival claim, and the failure it targets is a
failure this project measured itself rather than one it read about.

**Expected outcome: IC leg improves over `mom_12_1`, book leg remains negative
or marginal, 0 graduates.** A graduate would be a genuine surprise and is what
makes the trial worth its deflation slot.

---

## ⚠️ FIRST EXECUTION VOIDED — spec defect, disclosed with its numbers

The implementation placed the signal window at estimation-window positions
24..**35**. Position 35 is the **formation month itself**, so the first run
folded one-month reversal into a momentum signal and violated the frozen 12-1
skip. Caught by a spec test written after the run
(`tests/test_resid_mom.py::test_frozen_spec_constants`), not by inspection.

A run that does not implement the registered spec is not an execution of it —
the fix and re-run are repair, not a second bite. The void numbers are recorded
anyway, because a reader is entitled to check that the correction did not run
in the direction of a nicer answer:

| VOID run | segment | net bps | t_net | t_ic |
|---|---|---|---|---|
| resid_mom | largemid @ flat25 | −15.6 | −0.90 | −0.06 |
| resid_mom | small @ KO-half | −12.7 | −0.98 | −0.58 |

The defective version looked **worse** on rank (IC t −0.58 vs the corrected
+0.81) and **better** on the book (−12.7 vs −16.9 bps) — the signature of
one-month reversal being folded in. Verdict is REJECT under both.

## RESULT (one run of the corrected spec, 2026-07-30): **REJECT — no graduate in either segment. Family CLOSED.**

Artifact: `data/factory/instr_resid_mom.json`. 180 explore months, both
segments, `mom_12_1` re-run on identical windows and cost arms as the paired
control.

| | segment / cost arm | net bps/mo | t_net | t_gross | **t_ic** | turnover | **maxDD** |
|---|---|---|---|---|---|---|---|
| resid_mom | largemid @ flat25 *(deciding)* | −20.6 | −1.29 | −0.67 | **0.33** | 0.201 | −0.585 |
| mom_12_1 | largemid @ flat25 | −28.6 | −1.17 | −0.82 | 0.63 | 0.170 | −0.641 |
| resid_mom | small @ KO-half *(deciding)* | −16.9 | −1.34 | −0.83 | **0.81** | 0.207 | **−0.543** |
| mom_12_1 | small @ KO-half | −37.5 | −1.83 | −1.50 | **3.05** | 0.181 | −0.657 |
| resid_mom | small @ flat25 *(bridge)* | −20.8 | −1.65 | −0.83 | 0.81 | 0.207 | −0.546 |
| resid_mom | largemid @ KO-half *(reported)* | −12.5 | −0.78 | −0.67 | 0.33 | 0.201 | −0.582 |

Neither deciding arm comes close to `t_net >= 1.5 AND t_ic >= 2.0`. Confirm
window NOT opened.

### Implementation validation (run before the result was written up)

A null is worthless if the signal is broken, so three checks were run:

1. **Cross-sectional rank correlation with `mom_12_1`: mean 0.662** (median
   0.676, range 0.414–0.786, 268 months) — related but distinct, exactly as BHM
   describe residual vs total momentum. A broken signal would be near 0 or near 1.
2. **Coverage:** 3,424 names/month mean, 180/180 explore months scored — the
   1963-panel splice worked and no window was silently lost.
3. **Dispersion:** pooled mean −0.03, sd 0.26, range −2.66..+1.91 — a sane
   t-like ratio over 11 observations.

### The mechanism worked. That is why it failed.

FF3 regression of the top-decile book's excess return, explore window:

| book | segment | FF3 alpha | t(alpha) | β_mkt | β_smb | β_hml |
|---|---|---|---|---|---|---|
| resid_mom | largemid | −15.0 bps | −0.92 | **1.045** | 0.492 | −0.196 |
| mom_12_1 | largemid | −44.1 bps | −1.94 | 1.286 | 0.817 | −0.597 |
| resid_mom | small | −8.8 bps | −0.78 | **0.956** | 1.027 | +0.148 |
| mom_12_1 | small | **−52.4 bps** | **−3.04** | 1.189 | 1.207 | −0.268 |

Residualisation did precisely what BHM say it does: market beta returns to ~1.0
(1.19 → 0.96 in small), the size/value tilts shrink, max drawdown improves by
**11.4 points** (−65.7% → −54.3%), and the net bleed halves. The
significantly-negative FF3 alpha of the total-momentum book (−52.4 bps, t −3.04)
becomes indistinguishable from zero (−8.8 bps, t −0.78).

**And the rank information leaves with the tilt: small-cap IC t falls 3.05 → 0.81.**

The reading, which is the point of the trial: **in this window the cross-
sectional information in small-cap total-return momentum WAS its factor tilt,
not idiosyncratic continuation.** Strip the tilt and there is nothing
underneath. What residual momentum delivers is a better-behaved book with
nothing in it — lower beta, shallower drawdown, no alpha, no rank.

The one anomaly on our shortlist with an explicit post-publication OOS survival
claim does not survive on this panel, and it fails in a way that explains its
parent's failure rather than merely repeating it.

Per the frozen kill clause: **residual-momentum family CLOSED. The momentum
family is now closed at BOTH total-return and residual resolution.** No third
variant; a successor needs a mechanism class distinct from both timing and
residualisation, registered fresh. NEGATIVE_RESULTS §23.
