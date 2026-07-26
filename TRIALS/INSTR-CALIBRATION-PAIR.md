# INSTR-CZ-CALIB + INSTR-HARNESS-VALID — the calibration pair

Registered 2026-07-26 (round 8 queue), FROZEN BEFORE the run. Instruments,
never arms, no confirm wall (they analyze already-banked scan summaries +
external reference data; the only market data touched is the explore
window, read many times before). Purpose: validate the ruler before the
Chen-Velikov cost re-measurement — and make the paper defensible.

## INSTR-CZ-CALIB — our scans vs the Open Source Asset Pricing library

**Question:** does our harness rank signal strength the way the replicated
literature does, and is the level decay we observe (post-2004, post-
publication) systematic?

**Data:** `data/reference/osap_SignalDoc_snap20260726.csv` (Chen-
Zimmermann, 331 signals: in-sample T-Stat, sample years, sign) vs our
banked batch summaries (`data/factory/batch*_summary.csv`, explore
2004-2018).

**Frozen signal mapping (ours → OSAP acronym), declared before reading
any values:** gross_prof→GP, oper_prof→OperProf, asset_growth→AssetGrowth,
accruals_cf→Accruals, net_issuance→ShareIss1Y, comp_issue_5y→CompEquIss,
btm→BM, roe→RoE, mom_12_1→Mom12m, st_rev→STreversal, ltr→LTreversal,
max_low→MaxRet, vol_low→IdioVol3F, si_ratio→ShortInterest,
cust_mom→CustomerMomentum, industry_mom→IndMom. Matches that fail (acronym
absent or ambiguous) are dropped and listed; no post-hoc additions.

**Metrics + declared expectations:**
1. Spearman rank corr between OSAP |T-Stat| and our explore |t_ic|
   (largemid; the rank-information measure, least cost-contaminated).
   **Expect > 0** — the harness sees the same relative structure.
2. Level ratio: median(|our t_ic| / |OSAP t|). **Expect well below 1**
   (shorter window + post-publication decay, McLean-Pontiff).
3. Sign agreement vs OSAP `Sign`, with our known inversions (accruals,
   asset_growth) EXPECTED to disagree — publication decay hits hardest
   where the original t was loudest (descriptive).

**Reading:** rank corr ≤ 0 would indict the harness (or say the post-2004
window destroys all cross-signal structure — distinguishable by metric 3).
Either way the number goes in the paper.

## INSTR-HARNESS-VALID — proxy-factor replication vs Ken French

**Question:** does our panel's return construction (delisting handling,
month alignment, universe, segment split) co-move with the canonical
factors as it must if the plumbing is right?

**Constraint disclosed:** the panel carries no market-equity frame, so
exact VW SMB/HML replication is out of scope. Proxy factors from OUR
pipeline, explore window 2004-01..2018-12, vs `data/ff_factors.parquet`
(French, already on disk):

1. `mkt_ew` = EW mean monthly return of eligible universe → vs `mktrf+rf`.
   **Bar: corr ≥ 0.90** (EW vs VW gap acknowledged).
2. `smb_proxy` = EW small-segment mean − EW largemid mean (our
   dollar-volume segments) → vs `smb`. **Bar: corr ≥ 0.60.**
3. `umd_proxy` = mom_12_1 largemid top-decile excess-gross monthly series
   (recomputed via the standard scan) → vs `umd`. **Bar: corr ≥ 0.40**
   (long-only excess vs VW long-short gap acknowledged).

**Reading:** all three bars met → harness plumbing VALIDATED at proxy
resolution (recorded in the paper's methods). Any bar missed → named
defect hunt BEFORE the Chen-Velikov re-measurement (that is the point of
running this first).

One shot each; crashes before results are repairable (disclosed).

## Results

(to be filled by the one run)
