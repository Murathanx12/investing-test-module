# PRE-REGISTRATION — EXT-BANK-1 designs (2026-08-08)

**Written and committed BEFORE EXT-POWER-1's M4 is scored** (scan mid-run at
registration time; none of these designs depends on any number in
`runs/EXT-NULL-1/scan_predictor.csv`, and registering now is what keeps them
free of the peeking asterisk). Registered under CANON §6. Authorized by Murat
2026-08-08 ("full freedom overnight", ML/brain work explicitly requested,
"don't overtrain, find the sweet spot").

Batch accounting: all TRIAL-EXT-* below are candidates in the EXT-BANK-1
denominator (separate from the 179 per PREREG_REPLAY_2 §4/§7). Confirm
windows stay SHUT for every design here; each confirm needs its own future
registration. Origin: adversarial strategy-agent round 2026-08-08; designs
adopted with credit, adjacencies to NEGATIVE_RESULTS checked per design.

---

## TRIAL-EXT-PROF-SMALL-1 — profitability family as one cohort, small segment

Cohort: OSAP `GP`, `OperProf`, `OperProfRD`, `CBOperProf`, `cfp`, `roaq`
(signs from source papers). Mechanism: long-leg, low-turnover profitability
premium, strongest in small caps (Novy-Marx 2013; Ball et al. 2016;
Israel-Moskowitz 2013 long-leg decomposition). Explore 2004-2018 only, small
segment, hold-band book, KO-half + flat-25 cost arms.

Gates: BRAIN-010 explore legs + money leg (t_net) + **registered
leg-decomposition prediction: long leg (top − universe) carries ≥ 50% of the
D10−D1 spread** (the discriminator against the §28 short-leg class).
Declared within-cohort contrast: `CBOperProf` ≥ `GP` (Ball et al. 2016).
Placebo: sign-scramble cohort null (below) + σ-family veto check.

KILL: (a) no member clears the BH-adjusted bar in the EXT-BANK-1
denominator; (b) long-leg share < 50% for every member → family closed for
long-only use; (c) contrast fails AND nothing clears → "Ball et al. does not
replicate here". One shot.

Ledger adjacency: §22 cash_prof small kill was threshold-only under the
~0%-power ladder — §34 is the named resurrection license; gp-small survivor
untouched. Honest prior: 2-3 members clear explore; the family may still be
one factor (gp) wearing six hats.

## TRIAL-EXT-COMPOSITE-1 — the 209-signal composites with a sign-scramble null

Arm A **EW-209**: equal-weight of per-month cross-sectional ranks of all 209
OSAP signals, each signed by the source paper, no selection. Arm B
**THEME-13**: signals averaged within Chen-Zimmermann category first, then
categories equal-weighted. Declared comparison: THEME-13 t_net ≥ EW-209
(mechanism diversification beats paper diversification). Mechanism:
combination diversifies estimation noise and NETS TURNOVER (DeMiguel et al.
RFS 2020; Green-Hand-Zhang 2017). Registered prediction: composite one-way
turnover < 0.10/mo via netting.

Explore-only, both segments, hold-band, KO-half + flat-25, gross bound
reported. **Placebo: sign-scramble null** — K=200 composites from the
identical columns with coin-flip signs (preserves all correlation structure,
destroys published information); composite t scored as empirical p against
this null, floored by the REAL-NULL persistent-arm CDF.

KILL: fails empirical-p vs own sign-scramble null, OR net t < 1.5 in both
segments, OR turnover > 0.20/mo (netting mechanism refuted). One shot per
arm. Honest prior: EW-209 clears gross, marginal net; McLean-Pontiff decay
means any future confirm shrinks hard.

## TRIAL-EXT-ISSUE-1 — external-financing cohort, small + largemid

Cohort: `ShareIss5Y`, `ShareIss1Y`, `CompEquIss`, `NetEquityFinance`,
`NetDebtFinance`, `XFIN`, `CompositeDebtIssuance`. Mechanism: issuance times
overpricing (Bradshaw et al. 2006; Daniel-Titman 2006; Pontiff-Woodgate
2008); the only flow class whose turnover survives the §24 death line
(comp_issue_5y 0.104/mo banked). Declared contrast: composite equity+debt ≥
equity-only. Explore-only, BH within EXT-BANK-1, money leg, σ-family veto.
KILL: no member clears, or clears only where the σ-veto fires. Adjacency:
§22/§24 small kills were threshold-only (§34 license); largemid
comp_issue_5y rides REPLAY-2, untouched here.

## TRIAL-EXT-EXCLUDE-1 — lottery/distress exclusion overlay (long-only form of §28)

Avoid-composite from `MaxRet`, `IdioVol3F`, `OScore`, `zerotrade12M`,
`ShareIss1Y`, `FirmAge`(young). Test: does excluding the worst quintile from
the small long book (TRIAL-EXT-PROF-SMALL-1's book; EW universe fallback)
raise net t at incremental turnover ≤ 0.05/mo? Screen applied at formation
only. Mechanism: arbitrage asymmetry concentrates overpricing in the short
leg (Stambaugh-Yu-Yuan 2015; Bali-Cakici-Whitelaw 2011); §28 left the
exclusion form explicitly open. **Mandatory random-exclusion placebo** (5
seeds, same-size quintile): the screen must beat random (pooled |t| ≥ 1.5).
KILL: Δt_net ≤ 0, or ≈ random, or turnover > 0.05/mo. Same family tax as
the roadmap's §28 exclusion-book item (io_level variant) — one family, two
information sources, declared now.

## TRIAL-EXT-ML-1 — the honest ML combination (the "sweet spot" trial)

Model: **non-negative ridge** on the 209 sign-aligned rank features (small
and largemid separately) predicting next-month cross-sectional rank return.
Sign-alignment + non-negativity = the model can reweight published
directions but never flip them (kills the sign-mining channel INSTR-
OVERFIT-CEILING measured at fake-t 6.6). No deep nets: 180 explore months
cannot discipline them (Gu-Kelly-Xiu 2020 show shallow captures most of it).

Validation: walk-forward INSIDE explore only (fit 2004-2010 → predict 2011,
expand annually → 8 OOS years); λ per fold by purged CV with embargo on the
training slice; frozen grid λ ∈ 10^{-2..4}, 7 points, one path, reported in
full. **Benchmark to beat: EW-209 (arm A above) on identical OOS months,
book construction, and costs.**

KILL (any): pooled OOS net t advantage < +0.5 over EW-209; ML turnover >
1.5× EW; fitted weight mass > 50% on the σ/liquidity family (the §32
artifact in a regression coat). Any kill → EW stands as the house
combination and ML confirm never opens. Declared prior: ridge shrinks to
near-uniform and TIES the benchmark — the kill fires; a pass is a genuine
surprise. CANON note: this grazes the fit-on-returns rule; jurisdiction =
survivorship-free CRSP panel, explore-only, one shot, nothing touches a
lane without confirm + forward accrual.

## INSTR-ERA-CAL-1 — 1971-2003 as decay prior + gate testbed (calibration, not adoption)

Blocked on the WRDS pre-2002 CRSP pull. Measures (a) real-geometry
explore→pseudo-confirm transfer of the ratified ladder on 1971-1988 →
1989-2003; (b) per-signal McLean-Pontiff decay priors for OSAP signals
whose original samples end pre-2003. Output feeds REPLAY-2 §4 accounting.
Declared terminal at registration: NO candidate may be adopted from this
instrument. Failure mode: < 30 usable signals → reports UNINFORMATIVE.
Pre-2004 money legs run gross-only (cost model not calibrated there — stated).

---

## Execution order (frozen)

1. This file commits (before M4 scoring).
2. M4 scored when scan lands (pure EXT-POWER-1 protocol, unchanged).
3. PROF-SMALL-1 → COMPOSITE-1 (its null is the harness for both) →
   ISSUE-1 → EXCLUDE-1 → ML-1. Era work after the WRDS pull.
