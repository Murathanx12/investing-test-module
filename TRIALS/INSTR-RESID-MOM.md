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
