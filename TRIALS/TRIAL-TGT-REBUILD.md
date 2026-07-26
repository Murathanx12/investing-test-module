# TRIAL-TGT-REBUILD — target-price family rebuilt on nominal PIT data

Registered 2026-07-26 (round 8), FROZEN BEFORE the run. Candidates **#154
(tgt_upside) and #155 (tgt_ld)** — cumulative 155. Prior-check: tgt_upside
family = VOID (split-adjust look-ahead in the original IBES adjusted file);
rebuild was pre-authorized at panel rounds 4-6 once `ibes_adj`/`ptgdet`
landed (WRDS batch 4). This is the un-voiding, not a re-litigation: the
voided run produced NO adjudicated result.

## Hypothesis + priors

- Analyst 12-month price targets are systematically optimistic; RAW implied
  upside is a weak-to-perverse predictor because optimism concentrates in
  glamour/high-uncertainty names (Da-Schaumburg 2011; PSZ, Mgmt Sci 2025).
- PSZ conditional design: implied upside becomes informative among LOW
  target-dispersion names (analyst agreement = signal, disagreement = noise).
- **Declared priors:** arm A (raw upside) flat-to-negative largemid; arm B
  (low-dispersion-conditioned) positive IC, net survival uncertain —
  turnover is the risk (price in the denominator moves monthly).

## Construction (frozen)

Per formation month m (month-end), per permno (IBES cusip8 → permno via
`_cusip_sym`, batch-5 link):

1. ptgdet rows: horizon == 12, value > 0, estcur == USD (or missing),
   anndats in (m − 90 calendar days, m].
2. **Split guard (no adjustment arithmetic, the original sin):** drop any
   target whose IBES ticker has an `ibes_adj.spdates` in (anndats, m] —
   the target straddles a split event and is unusable nominally.
3. Per analyst (amaskcd) keep the latest target in the window; require
   **≥ 3 analysts**.
4. Price = |CRSP msf prc| at month m (nominal, matches nominal targets).
5. `tgt_upside` = median(targets)/price − 1. Direction +1.
6. `disp` = std(targets)/price. `tgt_ld` = tgt_upside where disp ≤
   cross-sectional monthly median (names above median dispersion → NaN).
   Direction +1.

Tags: source=analyst · horizon=3–12mo · turnover **declared MED-HIGH**
(house law skeptical) · role=PICKER.

## Runs + decision rule (frozen)

- Explore 2004-01..2018-12, both segments, standard ScanConfig (25 bps).
- **Graduation:** largemid t_net ≥ 1.5 AND t_ic ≥ 2.0 (standard frozen
  rule) opens confirm for that arm only.
- **Confirm** (2019-01..2024-12, one run, 25 bps): PASS if net excess > 0
  AND t_net ≥ 0.8 AND t_ic ≥ 1.5 (BRAIN-008/010 mirror, 72-month power
  note applies). DSR reported with n_trials = 155.
- No graduation → family adjudicated closed as picker (both arms), with
  dispersion IC banked to the combiner shelf if real.
- One-shot; crashes before results readable are repairable (disclosed).

## Result

(to be filled by the one run)
