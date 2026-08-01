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
