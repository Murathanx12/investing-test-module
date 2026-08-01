# TRIAL-ABIO-KIRK — abnormal institutional ownership, three arms, one shot each

**Registered 2026-08-01, FROZEN BEFORE ANY RUN CODE IS WRITTEN.**
Cumulative candidates **164-166** (three constructs, each counted).
Queued as P3 #1 since round 15 (AI_PANEL_2026-07-30C_ROUND15.md §4); the
blocking column (`crsp.msf shrout`) landed in the P0 harvest 2026-07-30.
Authority: Murat's 2026-08-01 direction ("move on with the project", holders /
smart-money question named explicitly). Run assignment: the next Opus session
(OPUS_SESSION_PROMPT_2026-08-01.md) — registration deliberately precedes it.

## Hypothesis

Kirk (2025, *J. Accounting, Auditing & Finance* 41:524-546, DOI
10.1177/0148558x251319189) reports a **76 bps/mo** next-month high-minus-low
spread from *abnormal* institutional ownership — actual IO residualised on firm
characteristics — on 2.29M firm-months 1984-2022. The claim to test is that the
**abnormal** component of IO carries cross-sectional information that raw IO
does not, and that it survives our harness net of costs.

This is a different construction from every 13F variant we have rejected
(best_ideas count, breadth_chg, inst_persist both directions, own_dur_t10 —
all: real IC, dead net book), so the batch-3b rejections do not reach it.

## Declared prior: WEAK-NEGATIVE (from round 15 §4, restated)

1. **The residualisation receipt.** INSTR-RESID-MOM (§23): residualising
   momentum on factors stripped the information — the fitted leg carried
   IC t 2.80 of the total 2.84, the residual 0.58. IO-residualisation is a
   different operation (characteristics, not factor returns), so this raises
   the prior against without closing the question.
2. **CZ-CALIB fame decay** (rank corr −0.544): large published effects decay
   hardest here, and 76 bps/mo is a large published effect.
3. **Family history:** five 13F variants tested, all real-IC/dead-net.

Honest prediction: `io_abn` IC t 1.5-3.0 with net t < 1.0 in largemid;
`io_chg` shows the §24 flow pattern (highest IC, highest turnover, dead net);
no arm graduates.

## Frozen construction

**IO fraction.** For each cusip-quarter in `tr13f_ownership_ext` (fdate,
cusip, n_inst, inst_shares; 662,688 rows, 1980+):
`io = inst_shares / (shrout * 1000)` with shrout from `crsp_msf_shrout` at the
month-end equal to fdate (fdate is a quarter end). Link: tr13f 8-char cusip =
`crsp_stocknames.ncusip`, valid only where fdate ∈ [namedt, nameenddt]; if a
cusip maps to more than one valid permno, the name-month is dropped (no
discretion). io winsorised per-quarter at 1%/99% before any further step.

**Availability lag.** The signal usable at formation month-end m is the latest
fdate with **fdate + 60 calendar days ≤ m**. Deliberately more conservative
than the 45-day statutory 13F deadline, to absorb late and amended filings.

**Three arms, each a candidate:**

| # | name | construct | direction |
|---|---|---|---|
| 164 | `io_level` | io itself | +1 (comparison arm — raw level) |
| 165 | `io_chg` | io_q − io_{q−1}, same cusip | +1 (flow arm — §24 out-of-family test) |
| 166 | `io_abn` | residual of quarterly cross-sectional OLS: io ~ log(mktcap) + mom_12_1 + log(3m mean dollar vol) + 1/price + log(months since first CRSP obs), all regressors winsorised 1%/99% per quarter, OLS refit each quarter, names with any missing regressor dropped | +1 (the Kirk-style arm) |

**Disclosed deviation:** the characteristic set is *Kirk-style, not verbatim* —
we freeze OUR five characteristics here, before any run, rather than claim
fidelity to a paper whose full spec we do not hold. Whatever the result, it is
a result about THIS residualisation.

## Frozen evaluation

Factory harness `scan_signal`, monthly formation, **explore 2004-01..2018-12
only**; segments largemid + small; EW-universe benchmark; 30% hold band;
deciles. Cost reporting per the post-CS-SPREAD convention (§25): deciding arms
**largemid @ flat25**, **small @ KO-half**, with the zero-cost bound and the
flat-25 regression guard reported alongside — a single-model cost number is
never quoted without the interval.

**Graduation (explore):** t_ic ≥ 2.0 AND t_gross ≥ 1.5 AND t_net ≥ 1.5 on the
deciding arm, per segment. Only a graduating arm earns the one confirm shot
(2019-2024: PASS = net > 0 AND t_net ≥ 0.8 AND t_ic ≥ 1.5).

**Pre-declared decisive comparison (the headline regardless of graduation):**
if **t_ic(io_abn) ≤ t_ic(io_level) + 0.5** in the pooled explore scan, the
finding is recorded as *"residualisation added nothing over the raw level"* —
the §23 result repeated in a second construction class. Declared now so the
comparison cannot be reframed after the numbers exist.

## Kill / scope

One shot per arm. No spec, lag, winsorisation, characteristic set, or bar may
change after this commit; a crash before results are readable is repairable
(disclosed), a completed run is final. No forward lane is seeded by this trial
under any outcome — a graduating arm goes to confirm, and a confirm pass goes
to the standing queue for an attended seed decision.

**Disclosed limitations (known before the run):** (a) 13F restatements are
unresolved in tr13f (Cao, Da, Jiang & Yang, Mgmt Sci 2026: restatements are
common and strategically timed) — our snapshot is the original filings;
(b) s34-derived inst_shares can exceed shares outstanding (double counting) —
handled only by the frozen winsorisation; (c) shrout is month-end while fdate
holdings are as-of quarter-end — same date, different sources, minor
misalignment possible on corporate actions.

---

# RESULTS — one shot taken 2026-08-01, explore only. FINAL.

**VERDICT (frozen bars, no arm graduated): all three arms REJECTED.**
`io_level`, `io_chg` and `io_abn` each fail the explore bar in both segments.
The 13F ownership family is now closed at **level, flow AND residual**
resolution — eight variants, zero survivors.

**Pre-declared decisive comparison — the headline, and it fired:**

| pooled explore IC t | value |
|---|---|
| `t_ic(io_level)` | **+7.77** |
| `t_ic(io_abn)` | **+6.89** |
| gap | **-0.88** (frozen margin: +0.50) |

Since -0.88 <= +0.50, the finding is recorded exactly as registered:
**"residualisation added nothing over the raw level."** Residualising on five
firm characteristics did not merely fail to add information — it *removed*
some. This is NEG_RESULTS §23 (INSTR-RESID-MOM) reproduced in a second,
structurally different construction class: there the residualisation was on
factor *returns*, here on firm *characteristics*, and both times the fitted leg
carried the information and the residual carried less.

The confirm window (2019-2024) was **NOT read**. No arm earned it.

## Explore 2004-01..2018-12, 180 months (deciding arms in bold)

| arm | segment | cost arm | net bps/mo | t_net | t_gross | t_ic | IC mean | turnover | maxDD |
|---|---|---|---|---|---|---|---|---|---|
| io_level | largemid | **flat25** | **-19.0** | **-1.91** | **-1.42** | **1.64** | +0.0095 | 0.097 | -0.620 |
| io_level | largemid | zero-cost bound | -14.1 | -1.42 | -1.42 | 1.64 | +0.0095 | 0.097 | -0.616 |
| io_level | largemid | KO-half (reported) | -15.4 | -1.55 | -1.42 | 1.64 | +0.0095 | 0.097 | -0.617 |
| io_level | small | **KO-half** | **-1.4** | **-0.14** | **+0.02** | **11.29** | +0.0491 | 0.087 | -0.671 |
| io_level | small | zero-cost bound | +0.2 | +0.02 | +0.02 | 11.29 | +0.0491 | 0.087 | -0.669 |
| io_level | small | flat25 guard | -4.1 | -0.41 | +0.02 | 11.29 | +0.0491 | 0.087 | -0.672 |
| io_chg | largemid | **flat25** | **-46.2** | **-3.50** | **-2.40** | **-3.34** | -0.0107 | 0.291 | -0.644 |
| io_chg | largemid | zero-cost bound | -31.6 | -2.40 | -2.40 | -3.34 | -0.0107 | 0.291 | -0.632 |
| io_chg | largemid | KO-half (reported) | -35.1 | -2.66 | -2.40 | -3.34 | -0.0107 | 0.291 | -0.636 |
| io_chg | small | **KO-half** | **-30.0** | **-2.47** | **-1.80** | **-0.07** | -0.0002 | 0.251 | -0.649 |
| io_chg | small | zero-cost bound | -21.9 | -1.80 | -1.80 | -0.07 | -0.0002 | 0.251 | -0.642 |
| io_chg | small | flat25 guard | -34.4 | -2.84 | -1.80 | -0.07 | -0.0002 | 0.251 | -0.652 |
| io_abn | largemid | **flat25** | **-4.5** | **-0.46** | **+0.32** | **1.66** | +0.0101 | 0.154 | -0.507 |
| io_abn | largemid | zero-cost bound | +3.2 | +0.32 | +0.32 | 1.66 | +0.0101 | 0.154 | -0.498 |
| io_abn | largemid | KO-half (reported) | +1.2 | +0.12 | +0.32 | 1.66 | +0.0101 | 0.154 | -0.501 |
| io_abn | small | **KO-half** | **+7.4** | **+0.87** | **+1.16** | **10.64** | +0.0406 | 0.068 | -0.645 |
| io_abn | small | zero-cost bound | +9.9 | +1.16 | +1.16 | 10.64 | +0.0406 | 0.068 | -0.643 |
| io_abn | small | flat25 guard | +6.5 | +0.76 | +1.16 | 10.64 | +0.0406 | 0.068 | -0.646 |

Bar was t_ic >= 2.0 AND t_gross >= 1.5 AND t_net >= 1.5, per segment, on the
deciding arm. The **zero-cost bound never graduates any arm either** — the best
zero-cost net t across all six deciding cells is +1.16 (io_abn small). Costs are
not what killed this; there was nothing to kill.

## Scoring the honest prediction registered before the run

| registered prediction | outcome | scored |
|---|---|---|
| `io_abn` IC t 1.5-3.0 in largemid | 1.66 | PASS |
| `io_abn` net t < 1.0 in largemid | -0.46 | PASS |
| `io_chg` highest turnover | 0.291 / 0.251 vs 0.097 / 0.087 — 3x the level arms | PASS |
| `io_chg` dead net | -46.2 and -30.0 bps/mo, t -3.50 / -2.47 | PASS |
| `io_chg` **highest IC** | **WRONG** — it had the *lowest*: pooled t_ic -2.37, and -3.34 in largemid | FAIL |
| no arm graduates | none did | PASS |

Five of six legs correct. The miss is worth keeping: we predicted the §24 flow
pattern (*flows carry more rank information than levels, and less tradability*)
and got only its second half. Institutional-ownership **change** is not a
high-IC/high-turnover signal here — in largemid it is a **negative** signal
(t_ic -3.34), i.e. names institutions bought last quarter underperform next
month. That is the Dasgupta-Prat-Verardo (2011) persistence result appearing
with the sign their paper predicts, and it means §24's "flow" generalisation
does **not** extend to 13F ownership flow. §24 is narrowed accordingly, not
extended.

## The finding under both hands

**The uncomfortable one first.** `io_level` in small carries a mean rank IC of
**+4.91% with t 11.29**, and `io_abn` in small **+4.06% with t 10.64**. Those
are among the largest IC t-statistics in the entire 166-candidate programme.
And the book earns **+0.02 and +1.16 gross t** — nothing. This is the starkest
instance yet of the pattern the ledger keeps producing: *rank information that a
long-only top-decile book cannot convert*. With turnover of only 0.068-0.087
one-way, this is not a cost story either — the zero-cost bound is still flat.

The mechanism the numbers point to: the information sits in the **lower** tail.
Low-IO small names — the neglected, un-held micro end — reliably underperform;
high-IO small names are merely average. A long-only decile book buys the top and
never harvests the short leg, so a large full-cross-section IC converts to zero
excess return. This is a hypothesis consistent with these numbers, **not a
tested claim** — testing it means a new registration (a short-leg or
long-short construction), and this trial does not license one.

**The other hand.** Nothing here rescues the family. The declared prior was
WEAK-NEGATIVE on three grounds (the §23 residualisation receipt, CZ-CALIB fame
decay at -0.544 on a large published effect, and five-for-five 13F rejections)
and all three held. Kirk's reported 76 bps/mo high-minus-low did not survive
transplant into a long-only, cost-charged, EW-benchmarked harness on
2004-2018 US data — which is what a long-short academic spread usually does
here, and is why the harness exists.

## Repairs disclosed (both found BEFORE the run, no results seen)

**REPAIR 1 — the frozen spec named a table that cannot answer the question.**
The registration specifies `tr13f_ownership_ext` and quotes its row count
(662,688, "1980+"). That file in fact spans **1980-03-31..2001-12-31 only**; the
explore window 2004-2018 contains **zero rows** of it. The 2002-2025
continuation of the identical WRDS s34 series is `tr13f_ownership` (1,169,903
rows). Run literally as written, the trial would have produced no scored month
at all. We read the **union** of both files, having first verified they are one
series split by era: identical dtypes, disjoint fdate ranges, no duplicate
(fdate, cusip), 8-char cusips in both, and a continuous boundary
(2001Q4 -> 2002Q1: 11,374 -> 11,221 cusips; median inst_shares 858,827 ->
862,849; median n_inst 8 -> 9). No lag, winsorisation, characteristic, direction
or bar changed. In practice the explore window is served entirely by
`tr13f_ownership`. Recorded here because the discipline that matters is *when*
the fix was made: before any number existed, so it cannot have been
outcome-conditional.

**REPAIR 2 — month-end matching.** The spec takes shrout "at the month-end equal
to fdate". CRSP month-end dates are **trading**-day month ends (2002-03-28)
while 13F fdate is a **calendar** quarter end (2002-03-31), so exact date
equality matches almost nothing. Matched on calendar year-month instead, which
is what the phrase means.

## Mechanical plumbing (spec silent; disclosed, not hidden)

- Characteristics for the residual regression are read at the **fdate**
  month-end — the information contemporaneous with the holdings snapshot. The
  60-day availability lag is then applied to the residual, so a score used at
  formation month *m* rests only on data >= 60 days old.
- "Months since first CRSP obs" = min(`namedt`) per permno from
  `crsp_stocknames` (full CRSP history, not the 2002+ panel window, which would
  truncate every incumbent to the same age).
- The availability rule is a forward-fill with **no staleness cap**, because the
  frozen text says "the *latest* fdate with fdate + 60 calendar days <= m" and
  names no cap. Measured rather than assumed harmless — see below.
- A (fdate, permno) pair reachable from two different cusips is dropped on the
  same no-discretion principle the spec states for the forward direction.

## Construction diagnostics

| quantity | value |
|---|---|
| ownership rows read (both era files) | 1,832,591 |
| rows surviving the date-valid ncusip link | 1,213,060 |
| dropped, cusip -> >1 permno (the frozen ambiguity rule) | **0** |
| dropped, permno -> >1 cusip (the mirror rule) | **0** |
| quarters | 180 |
| name-quarters with io | 850,131 |
| name-quarters with io_abn | 344,367 |
| mean explore coverage — io_level / io_chg / io_abn | 7,661 / 7,597 / 7,039 names |

The no-discretion ambiguity rule cost **nothing**: zero rows dropped in either
direction. Worth recording — the rule was written to be safe, and it turns out
to be free.

**Staleness of the uncapped forward-fill**, measured because it was the one
plumbing choice that could have quietly changed the question:

| population | median months since fdate | p95 | >6m | >12m |
|---|---|---|---|---|
| all panel columns | 4.96 | 146.98 | 46.9% | 44.3% |
| **ranked largemid** | **3.02** | **4.96** | **0.5%** | 0.3% |
| **ranked small** | **3.02** | **4.96** | **1.2%** | 0.5% |

The alarming 47%-stale figure is entirely dead names that are never ranked.
Among names the scan actually ranks — eligible and inside the segment — the
quarter in use is 3.0 months old at the median with a p95 of 5.0, exactly the
quarterly cadence plus the 60-day lag, and under 1.2% ever exceeds six months.
The uncapped fill is harmless where it matters, and now that is measured rather
than asserted.

One further check, run because the run log emitted a `divide by zero in log`
warning: **zero infinities in all five regressors** (log_mktcap, mom_12_1,
log_dvol3m, inv_price, log_age all finite where non-null). The warning is pandas
masked-array noise — `np.log` touching the masked buffer at positions that are
already NA. `dropna` would not have caught an `inf`, so this was verified
directly rather than assumed.

## Scope of the conclusion

One shot, taken and spent. No arm graduates, no confirm read, no lane seeded,
no forward clock started. Cumulative candidates **166** (164-166 counted here,
all rejected). The disclosed limitations registered before the run stand
unchanged: 13F restatements are unresolved in tr13f (Cao, Da, Jiang & Yang, Mgmt
Sci 2026), s34 double-counting is handled only by the frozen winsorisation, and
shrout is month-end while fdate holdings are quarter-end.

What this does **not** license: a sign flip, a long-short rebuild, a different
characteristic set, or a decile-tail variant, without a fresh registration.

Artifacts: `scripts/run_trial_abio_kirk.py`, `aegis_brain/factory/abio.py`,
`tests/test_abio_kirk.py` (14 spec tests, written before the run),
`data/factory/trial_abio_kirk.json`.
