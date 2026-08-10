# PREREG — ANALYST-IBES-1: levels versus revisions, on real point-in-time analyst data

**Registered** 2026-08-11, before any statistic on this data was computed.
**Family** analyst. **Data** IBES (WRDS), pulled 2026-08-11, first read tonight.
**Registrant note:** this trial exists because an entitlement changed, not
because a prior verdict was disliked. See §7.

---

## 1. Why this is not re-litigation

`analyst_target_upside_xs` is CLOSED/PERVERSE in the signal registry: raw
implied upside ranked the cross-section with t −3.6 (largemid) and −7.2
(small), and TRIAL-TGT-REBUILD (#154-155) re-adjudicated REJECT on nominal
split-guarded data. The re-litigation ban applies to that mechanism and this
trial does not lift it.

What changed is the **instrument**, and it changed in a way that was previously
recorded as impossible. Every prior analyst result in this programme ran on
OSAP-derived characteristics. Tonight `ibes.ptgdet` and `ibes.ptgsumu` were
found readable on the HKU WRDS account (`runs/ARENA1/wrds_ibes_probe.json`,
verdict `IBES_TARGETS_READABLE`), giving:

* 1,352,950 monthly consensus target rows, 1999-03 to 2026-05
* 2,376,276 per-analyst target announcements across 17,364 analyst codes
* 4,312,643 EPS consensus rows with up/down revision counts, from 1985

**AMENDED BEFORE RUNNING, after `scripts/lint_prereg.py` flagged three prior
trials.** The first draft of this document proposed six arms. The corpse check
matched it against `TRIAL-TGT-REBUILD` (0.283), `TRIAL-BRAIN-005-revisions`
(0.249) and `VOID-TGT-UPSIDE-B3B-B3C` (0.202), and reading those three changed
what may honestly be asked:

* **EPS estimate revisions were already run on IBES statpers and rejected**
  (`TRIAL-BRAIN-005-revisions`, kill condition "B net t<1 both segs reject";
  `data/revision_panel.parquet`, 921,925 rows, is that panel). Proposed arm A4
  was that trial again. **Dropped as an accruing arm.**
* **Target dispersion conditioning was already run and adjudicated REJECT**
  (`TRIAL-TGT-REBUILD` arm B, PSZ low-dispersion). Proposed arms A5/A6 were
  that trial again. **Dropped as accruing arms.**
* **A prior target-level run was VOIDED for exactly the adjustment defect this
  document identifies** — `ibes.ptgdet` values are split-adjusted through the
  DOWNLOAD date, against nominal CRSP `prc`, giving future-split look-ahead
  (the alarm was a long book at tgt/price ≈ 0.02 and t = 7.12). That receipt is
  why this trial uses the **unadjusted `ptgsumu`** file and not `ptgdet`.

What survives as genuinely unrun is **narrower and more specific than "analyst
revisions"**: the *target*-revision objects — `numup1m`, `numdown1m` and the
consensus target series itself — which live in `ibes.ptgsumu`, **a table this
programme had never pulled before tonight** (`data/wrds_raw/` holds
ibes_ptgdet, ibes_epsus, ibes_actu_epsus, ibes_recdsum, ibes_adj, and no
ptgsum of any kind). EPS revision breadth is not target revision breadth, and
the July work tested the former.

**The corpses are ARMS, not omissions.** A1 and R1 below reproduce two known
kills on the new instrument. If they do not reproduce the known negative sign,
the instrument is suspect and every other arm here is void. They run first and
report whatever they say. They do **not** accrue to the denominator, because
replicating a kill is not a search for a winner — and they may not be quoted as
new evidence either way.

## 2. Questions

* **Q1 (levels).** Does high analyst-implied upside predict returns?
  Registered expectation: **NO, and negatively** — reproducing the prior sign.
* **Q2 (revisions).** Do target REVISIONS survive where LEVELS do not?
  This is the literature's claim and the thing Murat's Bloomberg process
  actually watched.
* **Q3 (net).** Does any arm survive honest costs at its own turnover?

## 3. Data and window

* Panel: `crsp_panel_2002`, 2002-01-31 .. 2024-12-31, 276 months, 11,098 permnos.
* IBES → CRSP via `wrdsapps_link_crsp_ibes.ibcrsphist`, honouring `sdate`/`edate`
  validity windows. Unmatched IBES tickers are DROPPED and the drop rate is
  reported; a link that silently matches nothing is the failure mode.
* **PIT rule:** at month-end `t`, use the latest `statpers <= t`. `statpers` is
  the IBES statistical cut-off, so this reads only what was published.
* **Unadjusted files only.** `ptgsumu`/`statsumu_epsus` are the `u` (unadjusted)
  variants. The adjusted files restate history for splits, which is look-ahead.
* **Split correction, declared in advance.** CRSP `month_end_price` in this
  panel is RAW (verified: NVDA shows factors 4.00 in 2021-07 and 10.00 in
  2024-06). Levels therefore need NO adjustment — target and price are both raw
  and same-dated. REVISIONS do: the split factor
  `f_t = price_{t-1}(1+ret_t)/price_t` is applied cumulatively to the target
  series before differencing, or a 10:1 split prints as a −90% revision.

## 4. Arms (frozen)

Long-only, top-N equal weight, `segment=small` and `segment=largemid` run
separately, `top_n=50`, monthly and quarterly clocks, `cost_model=flat25`
and `ko`.

**Accruing arms — the new question, and the only source of a claim:**

| arm | signal | registered prediction |
|---|---|---|
| A2 | `ibes:tgt_rev_breadth` = (numup1m − numdown1m)/numest | positive gross, **net-dead** |
| A3 | `ibes:tgt_rev_3m` = split-adjusted Δ consensus target, 3m | positive gross, **net-dead** |

**Replication arms — instrument checks, NON-accruing, no claim either way:**

| arm | signal | must reproduce |
|---|---|---|
| A1 | `ibes:tgt_upside` (level) | **NEGATIVE** (`analyst_target_upside_xs`, TRIAL-TGT-REBUILD) |
| R1 | `ibes:eps_rev_breadth` = (numup − numdown)/numest, FY1 | **net t < 1** (`TRIAL-BRAIN-005-revisions`) |

**Controls:**

| arm | signal | role |
|---|---|---|
| C0 | equal-weight the eligible universe | the denominator (CANON §16) |
| C1 | `random_score` at matched turnover, 100 draws | the placebo |

## 5. Predictions, and what would refute them

1. **A1 is negative** in both segments, and **R1 has net t < 1**. These are
   the instrument checks. Refuted — and the trial voided — if either comes out
   positive at |t| ≥ 2, which would mean the new ptgsumu instrument disagrees
   with two independently adjudicated results, and the right response is to
   doubt the instrument rather than to celebrate.
2. **A2/A3 gross > 0.** Refuted if target-revision breadth is flat or negative
   gross, which would kill the family outright rather than on costs.
3. **A2/A3 net ≈ 0.** The taxonomy classes analyst revisions as HIGH turnover,
   and every HIGH-turnover family in this programme has produced real IC and a
   dead book. Refuted if net excess ≥ +3 %/yr at |t| ≥ 2 against C0.
4. **The gross-to-net gap is larger for A2/A3 than for A1**, because revisions
   turn over faster than levels. This is the mechanism by which prediction 3 is
   expected to come true, and it is separately checkable.
5. **A2 and A3 agree in sign.** They are two constructions of one idea. If they
   disagree, the idea is not identified and no verdict may be issued for either.

## 6. Power check — this test can see its own prior

276 months. For a long-only 50-name book against the eligible-universe control,
observed tracking error in comparable PF campaigns is ~8%/yr, so
SE(annual excess) ≈ 8/√23 ≈ **1.67 %/yr** and the two-sided MDE at t = 2 is
**≈ 3.3 %/yr**. The decile spreads this family claims in the literature are
6–12 %/yr gross, so the test is adequately powered for Q2 and Q3.

It is NOT adequately powered to resolve a ±1 %/yr difference between two
revision constructions, and no such claim will be made.

## 7. Search denominator

**2 accruing arms** × 2 segments × 2 clocks × 2 cost models = **16 books**.
The denominator for any survivor claim is **16**, recorded before the first book
runs.

The 2 replication arms (A1, R1) produce 16 more books and accrue **zero**,
because their registered outcome is a kill that already exists: they can only
confirm or impeach the instrument, and an instrument check that "wins" is a bug
alarm, exactly as `VOID-TGT-UPSIDE-B3B-B3C` recorded when a target book printed
t = 7.12. If either replication arm comes out positive, this trial reports
INSTRUMENT SUSPECT and A2/A3 are void whatever they did.

The programme's cumulative candidate count stands at 179 (search CLOSED) plus
these 16 = **195** for any future deflated-Sharpe arithmetic.

No arm may be added after results are seen; a post-result variant is a NEW
trial with its own ID naming this one as parent.

## 8. Kill conditions

* IBES→CRSP link matches < 60% of target-carrying tickers ⇒ **DATA**, void.
* Mean scored names/month < 50 in a segment ⇒ that segment is **POWER**, void.
* A1 fails to reproduce a negative sign ⇒ **INSTRUMENT SUSPECT**, whole trial
  reported as unresolved regardless of what the other arms did.
* Any arm requiring a parameter chosen after seeing a result ⇒ **VOID**.

## 9. Standing constraints that bind this trial

* **NIGHT-9:** rank-IC may describe ordering only. Every verdict here is stated
  in SIMPLE-return money terms; IC is reported as a diagnostic beside it and
  may not carry a verdict on its own.
* **CANON §16:** the cost comparison uses C0 as denominator, not the winner's.
* **CANON §15:** ranking first on a frictionless panel is not a trading rule.

## 10. What a PASS would change

If A2/A3/A4 survive net, `analyst_target_revision` moves from HYPOTHESIS to
SUPPORTED in the signal registry, `allowed_in_pm` flips to true with a measured
`reliability_weight`, and the PM stops ranking on levels. If they do not, the
registry records the second independent kill of the analyst family as a picker,
and the PM's use of targets stays exactly where it is today: a RISK_INPUT for
sizing names chosen on other grounds, labelled OBSERVATIONAL.

Either outcome is worth the night. The one outcome that is not permitted is
quietly keeping the level signal because the revision signal failed.
