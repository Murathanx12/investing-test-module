# INSTR-OVERFIT-CEILING — the self-deception ceiling of our own library

**Registered:** 2026-07-25 (UTC), BEFORE the run. **Class:** instrument
(measurement). Never arms a lane, never promotes a signal, results final.

## Question
How impressive can a result look on THIS data through pure post-hoc
selection — no information, only mining? The answer is the empirical
boundary against which every future explore number is read, and it
quantifies why the explore/confirm wall is mandatory (BRAIN-010 just
demonstrated it live-fire on one candidate; this measures it on ~53).

## Frozen design
- **Library:** batches 1, 2, 5, 6, 7 — CLOSED families only. The insider
  family (insider_cluster, insider_si) is EXCLUDED: BRAIN-003 is a live
  promoted trial and its family must not touch confirm data outside its own
  registrations. gross_prof and conc_low have already had their one confirm
  run (adjudicated); their inclusion reveals nothing promotable.
- **Contamination clause:** every library signal (and close variants) is
  already barred from future confirm registration by family closure /
  completed adjudication. The confirm-window information this instrument
  reveals therefore CANNOT leak into any future promotion decision. Newly
  registered signals (batch 8+) are NOT in the library.
- **Scans:** `scan_signal` mechanics byte-identical to the factory (top
  decile, 30% band, 25 bps, min_names 100), segment largemid, FULL window
  2004-01..2024-12 — the confirm window is deliberately included; that is
  the point of the instrument.
- **Mining arms (selection and evaluation on the SAME full window):**
  A best-1 by t; B top-5 EW; C best-1 allowing sign flips (the realistic
  mining move — we have recorded 4 sign reversals ourselves); D top-5 EW
  with flips. Flip series = negated long-book series (cost-identical proxy,
  disclosed approximation — a true short book differs).
- **Wall curve:** rank all signals by explore-window t (2004-2018), report
  each one's confirm-window t (2019-2024) — the empirical explore→confirm
  decay across the whole library, plus rank correlation.
- **H0 reference:** Bailey/López de Prado expected-max-Sharpe of N
  zero-skill trials (N = library and N = 2×library with flips), sr_std from
  the library cross-section.
- **Fragility:** split-half t (2004-06/2014, 2014-07/2024) of each mined arm.
- Drops counted and printed, never silent. ONE run.

## What the numbers will be used for
- The "ceiling" t = arm C/D result ≈ what a motivated researcher can
  manufacture here with zero information. Any explore t at or below it is
  hypothesis-generation only (already house law; now with a number).
- The decay curve calibrates how much explore rank survives out-of-window —
  context for reading all past and future explore tables.
- t≈7 bug-alarm rule gets an empirical basis: if the ceiling shows mining
  cannot manufacture t>~4 here, anything larger is a book/data bug, not skill.

## Result (filled AFTER the run 2026-07-25 — never edited)
`data/factory/overfit_ceiling.json` + `overfit_ceiling_monthly.parquet`.
53/53 scanned, 0 dropped.

### The ceiling
| arm | picked | mean bps/mo | t | SR ann | t half1 / half2 |
|---|---|---|---|---|---|
| A best-1 | dtc_high | 35.3 | 2.94 | 0.69 | 2.28 / 2.04 |
| B top-5 EW | dtc_high, dtc_qual, payout_yield, own_dur_t10, conc_low | 28.5 | 3.27 | 0.71 | 1.46 / 3.02 |
| C best-1 + sign flips | dtc_low FLIPPED | 88.8 | **6.16** | 1.44 | 3.24 / 5.27 |
| D top-5 EW + flips | dtc_low^f, illiq^f, dtc_high, dtc_qual, seasonality^f | 51.3 | **6.58** | **1.44** | 3.73 / 5.53 |

H0 (zero-skill) expected max t: **3.59** (N=53), **3.98** (N=106 with flips).

**Readings (both hands):**
1. **Honest-direction mining (A/B, t 2.9–3.3) sits BELOW the zero-skill
   expected max** — a "best signal of the library" full-sample t≈3 is
   literally indistinguishable from selection noise. This is the number to
   hold against every future explore table.
2. **Sign-flip mining manufactures t 6.2–6.6 / Sharpe 1.44** — a track
   record that would embarrass most funds, built from zero information. It
   exceeds the H0 max because dtc is a REAL full-window book-level mean
   effect with no rank IC (the exact b6 AND-rule catch) — mining plus one
   rank-free anomaly is enough. Sobering: the split-half check does NOT
   catch it (t>3 both halves). Only the IC leg + cost/capacity honesty do.
3. **t≈7 bug-alarm calibrated:** mining tops out ≈6.6 here, so anything ≥7
   on this data is a book/data bug, not skill — now an empirical rule.

### The wall, empirically (explore→confirm decay, all 53)
Rank correlation explore-t → confirm-t = **0.49**: explore ranking is a
weak-but-real predictor, and top-of-table shrinks brutally — dtc_qual
3.39→1.30, dtc_high 3.03→1.29, conc_low 2.28→**−0.05** (the BRAIN-010
live-fire KILL, reproduced), earn_stab 0.14→−0.58. The other hand,
disclosed: the value class IMPROVED out-of-window (re_me 0.28→1.30,
payout_yield 0.80→1.63, btm 0.61→0.70 — value's 2019-2024 comeback). Those
families are CLOSED and stay closed (contamination clause: this instrument's
confirm-window reveal is exactly why they are barred from resurrection) —
that is the wall's false-negative cost, now quantified. Regime-dependence
receipt for the allocation layer, not a stock-selection do-over.
