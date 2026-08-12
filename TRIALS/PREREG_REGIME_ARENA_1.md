# PREREG — REGIME-ARENA-1: does conditioning a decision OTHER THAN EXPOSURE on an observable state beat making the same decision unconditionally?

**Registered** 2026-08-12, GRAND-ARENA-1 **CHUNK 5**, **before any runner file
exists and before a single conditioned path is computed.**
**Binding law:** `aegis-finance/docs/GRAND_ARENA_1_AMENDMENT_A.md` §A2, §A3,
§A7, §A8, §A9, §A10, §A11. **Family:** regime / state-conditioning of
cross-sectional decisions. **ACCRUES ZERO ARMS.** No lane, no shadow default,
no order path, no sizing change, whatever the outcome.

---

## 0. What chunk 6 already settled, and why this trial is therefore NOT about exposure

EXPOSURE-ARENA-1 (`Aegis module` `ca438a6`, `aegis-finance` `54f99f6`) tested a
regime rule **as an exposure controller** across 144 arms on three beds:

* 42 of 45 configurations on BED-1 and 44 of 45 on BED-3 failed to clear their
  own MDE against a constant policy at matched average exposure. **Not one
  pre-registered primary configuration of any family cleared.**
* The one family that cleared did so on a single market path, mostly before
  1976, and is negative in every decade since 2005.
* The oracle bound proved the timing **information exists** (+21.563 pp/yr over
  matched at 10.4x MDE) and that the best observable controller captured
  **7.4%** of it. The failure is observability, not availability.
* The wealth frontier is monotone increasing in mean exposure on all three beds
  over 98 years. No interior optimum.
* The only detectable non-oracle result was **negative**.

**Therefore: regime → exposure is not re-run here, in any form.** No arm of this
trial changes how much is held. Gross exposure is 1.00 for every system in this
trial by construction, and that is verified rather than asserted.

**The open question chunk 6 did not touch** is whether a state label helps a
*different* decision: which names to hold, how to weight the signals that choose
them, and which risk model allocates inside them. That is what this trial asks,
and nothing else.

---

## 1. Resurrection / duplication declarations, argued rather than asserted

The linter matches this draft against chunk 6 on wording, because §0 above
*quotes* chunk 6 at length. That match is real and it is declared rather than
paraphrased away. The distinction is the **decision being conditioned**, and it
is structural, not rhetorical: gross exposure is **1.00 in every arm of this
trial by construction and is verified per arm**, so no configuration here can
express the hypothesis chunk 6 refuted.

Resurrects: PREREG_EXPOSURE_ARENA_1 — new instrument: the conditioned object changes from EXPOSURE to the CROSS-SECTIONAL decisions (which names, which signal weights, which risk model) on a 1,500-name monthly CRSP panel where gross exposure is pinned at 1.00 and verified per arm, so the de-risking channel that decided chunk 6 cannot exist here; and the comparator changes from a matched-average-exposure constant policy to the SAME decision machinery with the state label deleted.

Resurrects: EXPOSURE-ARENA-1 — new instrument: chunk 6 scored a regime rule as an exposure dial on three single-asset beds; this trial never varies exposure and instead scores the same class of state labels as a CONDITIONER of selection, strategy weighting and risk-model choice, with a placebo state (same marginals, permuted in time) that chunk 6 did not carry.

Resurrects: VERDICT-EXPOSURE-ARENA-1 — new instrument: chunk 6's verdict is treated as BINDING and its question is not re-asked — regime-to-exposure is excluded from the grid entirely. What is new is the oracle-state bound and the shuffled-state placebo applied to cross-sectional decisions, neither of which exists anywhere in the chunk 6 receipts.

**Also named, and NOT resurrected:** **TRIAL-COND-VT** (index-keyed conditional
volatility targeting) stays CLOSED and has no descendant here — it is an
exposure rule.

**Why these declarations are not a loophole.** The protection is that the
primary comparator is **the identical decision machinery with the state label
removed** — the same trailing-performance rotation over the same option set on
the same dates, choosing from the *unconditional* history instead of the
in-state history. A comparison that can only ever remove apparent edge, never
manufacture it. Every arm prints its own measured 80%-power MDE; the entire
configuration count is published; and nothing can be promoted from this chunk
by construction.

---

## 2. THE OBJECTIVE, FROZEN BEFORE ANY OPTIMISATION (§A9)

**ONE objective.** The **arithmetic mean monthly net portfolio return**,
annualised x12, of a long-only unlevered book charged the repo G7 cost model.
Nothing else is optimised anywhere in this trial. Geometric CAGR, drawdown,
volatility, turnover and effective-N are **reported, never deciding** (§A9: a
risk statistic may qualify a verdict, it may never rescue one, and the objective
may not be swapped after seeing results).

**PRIMARY METRIC — the headline of the whole chunk.** For every decision family
`F` and every state definition `s`:

```
D_cond(F, s)  =  mean_monthly_net( F | state = s )  -  mean_monthly_net( F | NO STATE )
```

paired on the same months, annualised x12. `F | NO STATE` is the **control**: the
identical rotation machinery over the identical option set, choosing from the
whole realised past instead of the in-state past. **"Regime-conditioned X beats
unconditioned nothing" is explicitly not a result and is not computed.**

**THE RULER (§19).** Sampling unit = the MONTH. `MDE = 2.80 x max(Newey-West,
IID) SE` of the paired monthly difference series, annualised x12
(`scripts/arena_core.ruler`, reused verbatim from PORTFOLIO-ARENA-1). **Below
its own MDE is NOT DETECTABLE — never a kill and never a win.**

---

## 3. The bed, declared as found

`data/factory/arena_panel.parquet`, built by `scripts/arena_panel.py` for
PORTFOLIO-ARENA-1 and **reused unmodified**:

* **263 monthly decision dates, 2003-01-31 → 2024-11-29.**
* **1,500 eligible CRSP names at every date** (price >= $5, >= 252 days of
  history, 63-day median dollar volume >= $1m, top 1,500 by that median).
* **7,283 CRSP delistings spliced.** A death is a realised return, never a
  disappearance.
* Every feature computed from rows at or before the decision date; the forward
  return runs decision-date → next decision date, disjoint from every feature by
  construction.
* Cost model **G7, reused**: Corwin-Schultz half-spread stamped per name per
  date (median 24.2 bps) + 5 bps slippage + 1 bp commission, charged on the
  one-way traded fraction. A name with no CS estimate pays that date's 90th
  percentile. Index legs pay a declared 5 bps.

**Burn-in, frozen:** the first **36** decision dates are pre-rotation (every arm
holds the frozen default) and the primary metric is evaluated on decision dates
36..262 inclusive, **n = 227 months**, identically for every arm.

**§A7 is binding.** This is CRSP 2002-2024, interrogated across many nights of
this programme. It is development and secondary validation. **Nothing in this
trial can be certified by it.**

---

## 4. The three decisions, and their option sets — frozen

**Six base signals**, all PIT panel columns, all rank-normalised
cross-sectionally by `arena_systems.z`:

| id | column | direction |
|---|---|---|
| `MOM` | `mom_12_1` | high |
| `REV` | `rev_score` | high |
| `SUE` | `sue` | high |
| `TGT` | `tgt_upside` | high |
| `LOWVOL` | `vol_252` | low |
| `NMAX` | `max5` | low (Bali-Cakici-Whitelaw lottery demand) |

**Five risk schemes**, inside a FIXED selection:

| id | weights |
|---|---|
| `EW` | equal |
| `IVOL` | 1 / `vol_252` |
| `IVAR` | 1 / `vol_252`^2 |
| `MINVAR1F` | analytic minimum variance under a one-factor model (`beta_252`, `ivol_252`, trailing market variance), long-only, renormalised |
| `IBETA` | 1 / max(`beta_252`, 0.2) |

**D1 SELECTION** — which of the six signals ranks the top-K.
**D2 WEIGHTING** — the blend weights over the six signals' z-scores: `softmax`
of the cross-signal-standardised trailing rank-IC, temperature **1.0, frozen**.
**D3 RISK MODEL** — which of the five schemes allocates inside a selection held
FIXED at the equal-weight six-signal composite top-K. (Selection is deliberately
frozen in D3 so the only thing conditioned is the risk model.)

**The conditioning rule is identical for all three families**, so the state is
the only thing that varies:

> At decision date `k`, for each option `o`, compute its trailing score = the
> mean realised net monthly return (D1, D3) or mean rank-IC (D2) of that option
> over the **conditioning set**. Choose the argmax (D1, D3) or the softmax blend
> (D2). The conditioning set is *all past months with realised outcomes* for the
> control, and *past months carrying the current state label* for a conditioned
> arm.
>
> **Minimum in-state history: 12 months.** Below it the arm falls back to the
> unconditional choice; below 12 unconditional months it uses the frozen default
> (the equal-weight composite for D1/D2, `EW` for D3). **The fallback rate is
> reported for every arm** — an arm that never actually conditioned is not
> evidence about conditioning.

---

## 5. The state definitions — frozen, complete, and A2-compliant

**§A2 binds: HMM is a CONTROL, not a feature.** Known-answer calibration put HMM
state recovery at 58.8% against a 76.0% Bayes ceiling with every WORLD-C cell
only PARTIAL. It enters labelled `NOT_TRUSTED` and it may not be promoted by
this trial whatever it prints.

| id | definition | class |
|---|---|---|
| `S_NONE` | one state | **CONTROL — the comparator** |
| `S_VOL3` | expanding-quantile terciles of trailing 63d market vol | simple observable |
| `S_DD2` | market 252d drawdown <= -10% vs > -10% | simple observable |
| `S_TREND2` | trailing 252d market return > 0 vs <= 0 | simple observable |
| `S_YC2` | sign of DGS10 - DGS2 | simple observable, **snapshot vintage declared** |
| `S_BREADTH3` | expanding terciles of the cross-sectional share of names with `mom_12_1` > 0 | simple observable |
| `S_KMEANS3` | k-means(3) on five standardised state features, refit annually on data <= t | clustering |
| `S_BOCPD2` | Bayesian online changepoint run-length <= 6 months vs > (`backend/services/anomaly_detector.BayesianChangepoint`, imported not reimplemented) | change-point |
| `S_HMM2`, `S_HMM3` | Gaussian HMM on monthly market returns, refit annually on data <= t, **filtered** posterior state at t | **CONTROL (§A2), NOT_TRUSTED** |
| `S_SUP2` | supervised: LightGBM trained on state features to predict which base signal wins next month, purged expanding walk-forward, out-of-fold only | supervised interaction |
| `S_SHUFFLE3` | **PLACEBO** — labels with the same marginal frequencies and block structure as `S_VOL3`, permuted in time, seed 20260812 | **PLACEBO** |
| `S_ORACLE2` | **IMPOSSIBLE** — sign of NEXT month's market return | availability bound |
| `S_LEAKY3` | **TRIPWIRE** — `S_VOL3` with FULL-SAMPLE tercile breakpoints | look-ahead tripwire |

`S_YC2` uses the 2026-07 FRED snapshot. Treasury constant-maturity yields are
not revised, but the arm is labelled `SNAPSHOT_VINTAGE` throughout and may not
be read as point-in-time-clean.

---

## 6. Look-ahead: the tripwire is mandatory and it must have teeth

Chunk 6's tripwire caught an "oracle" that was secretly a momentum rule. The
equivalent failure here is **a state label fitted on the full sample and then
used to condition** — the single most likely way this trial fools itself.

1. **Perturbation proof.** For every state definition: corrupt every panel and
   market row strictly after a probe date, recompute, and require the label at
   the probe to come back **bit-identical**. Required for every real state.
2. **The tripwire.** `S_ORACLE2` and `S_LEAKY3` are **REQUIRED TO MOVE** under
   the same perturbation. A causality proof that could not have produced a
   violation is worthless (the WORLD-I argument). If the harness fails to catch
   either, **the assertion is rebuilt, not the failing arm dropped**, and the
   rebuild is recorded.
3. **Decision-level proof.** The proof is repeated on the *chosen option*, not
   only on the label: the signal chosen at the probe date must also come back
   bit-identical.
4. All learned states (`S_KMEANS3`, `S_HMM2/3`, `S_SUP2`) are fitted on an
   expanding window ending at the decision date, refit annually, **never
   random k-fold**, with a 2-decision-date purge on the supervised arm (longer
   than its 1-month label horizon).

---

## 7. Hypotheses, with honest priors

| # | hypothesis | prior |
|---|---|---|
| **H1** | At least one (family, state) beats its own unconditional twin by more than that arm's own 80%-power MDE, with the sign in >= 5/8 regime blocks and both halves, surviving beta- and vol-matching. | **LOW, ~12%.** Chunk 6 found nothing observable in the neighbouring decision; §A1's de-risking trap does not apply here but the observability problem does. |
| **H2** | The shuffled-state placebo is indistinguishable from the real states. | **HIGH, ~70%.** If true, "conditioning" is a random partition of the trailing window and the result is a sample-size effect, not information. |
| **H3** | The HMM (§A2 control) does not beat the simple observable states. | **HIGH, ~75%.** 58.8% state recovery against a 76.0% ceiling. |
| **H4** | The oracle state bound is large — conditioning information exists and observable states capture almost none of it, reproducing chunk 6's shape on a different decision. | **HIGH, ~80%.** |
| **H5** | Conditioning raises turnover and a material share of any gross gain is eaten by G7 costs. | **MEDIUM, ~55%.** |
| **H6** | The look-ahead tripwire (`S_LEAKY3`) beats its PIT twin `S_VOL3`, demonstrating that this bed can express the failure mode the tripwire exists to catch. | **MEDIUM, ~50%. If it does NOT, the tripwire is weak on this bed and that must be stated, not glossed.** |

---

## 8. Decision rule, frozen before any path exists

Per (family, state), on the PRIMARY configuration (K = 20, 1x costs, raw):

* **`CONDITIONING_DETECTED`** iff **all** of: `D_cond` >= its own MDE; sign
  agrees in >= 5/8 pre-declared regime blocks (2002-03, 2004-06, 2007-09,
  2010-12, 2013-15, 2016-18, 2019-21, 2022-24); both sample halves; the effect
  survives beta-matching and vol-matching (§A3); **and** it exceeds the
  same-family `S_SHUFFLE3` arm by more than the MDE of that difference.
* **`PLACEBO_EQUIVALENT`** if detectable against the unconditional control but
  **not** against `S_SHUFFLE3`. Reported as a finding, not a win.
* **`EXPOSURE_ARTEFACT`** — cannot occur by construction (gross is 1.00 for
  every arm) and is verified, not assumed. If a measured gross exposure differs
  from 1.00 the arm is voided and the discrepancy published.
* **`NOT_DETECTABLE`** if |`D_cond`| < its MDE. **Never a kill (§19).**
* **`CONDITIONING_HARMFUL`** if `D_cond` <= -MDE with the same coverage.
* **`DIAGNOSTIC`** for `S_ORACLE2` and `S_LEAKY3` — never a result, only a bound.

**§A11(4)** ("a regime-conditioned improvement that replicates") may be awarded
**only** if `CONDITIONING_DETECTED` holds for the same state in **two of the
three decision families independently** and survives the placebo. One family
clearing is not a replication and the word BREAKTHROUGH is not used.

---

## 9. Required reporting, whatever the outcome (§A8, §20)

* **The complete search denominator** — every configuration executed, including
  every failure and every voided arm.
* **PBO** by CSCV over the whole family of conditional systems, and **DSR**
  computed for the FAMILY, not for the winner.
* **§20 batch self-check** — mean absolute pairwise correlation of the monthly
  `D_cond` series and the implied **effective distinct arms**. Chunk 6 measured
  47 configs as 2.02-2.40 effective arms; a similar collapse is expected and
  must be stated.
* **Raw AND matched** (§A3) on beta, volatility, gross exposure, concentration
  (effective N) and turnover, for every primary arm.
* **Cost sensitivity** at 0x / 1x / 2x on every primary arm.
* **Fallback rates** — how often each conditioned arm failed to find 12 in-state
  months and silently became its own control.
* **Every defect**, recorded rather than tidied away.

---

## 10. What this trial may NOT conclude

1. **Nothing about exposure.** Chunk 6 owns that question and this trial has no
   exposure arm.
2. **No alpha, Sharpe, skill or money claim.** No lane, no shadow default, no
   sizing change, no product default, no buy/sell language.
3. **Nothing certified (§A7).** CRSP 2003-2024 is interrogated data.
4. **A null is a null on THESE states and THESE decisions**, bounded by the
   oracle arm, and every arm's MDE says exactly how large an effect would have
   had to be.
5. **The HMM may not be promoted** whatever it prints (§A2).
6. **A plausible-looking label sequence is not evidence.** No state earns
   authority from its labels reading sensibly against known history.
7. **`lint_prereg` PASS means UNMATCHED, not novel** — it knows nothing about
   the literature, and regime-switching asset allocation is a large published
   field.
