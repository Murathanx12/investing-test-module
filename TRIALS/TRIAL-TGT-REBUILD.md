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

## Result (one run, 2026-07-26): **REJECT — family closed as picker, both arms**

`data/factory/trial_tgt_rebuild.json`. 180 explore months; coverage healthy
(both arms scanned in both segments). Confirm gate never opened.

| arm / segment | net excess bps/mo | t_net | IC t | turnover 1-way |
|---|---|---|---|---|
| tgt_upside largemid | −90.0 | **−3.62** | −3.47 | 0.216 |
| tgt_upside small | −198.7 | **−7.21** | −3.23 | 0.308 |
| tgt_ld largemid | −43.5 | −2.58 | −3.77 | 0.453 |
| tgt_ld small | −7.9 | −0.34 | 0.18 | 0.599 |

- **Prior CONFIRMED, amplified:** raw implied upside is not weak — it is
  strongly PERVERSE. High-target-upside names (glamour, distressed
  optimism) underperform catastrophically, worst in small caps. This is
  the Da-Schaumburg optimism-bias result reproduced on clean nominal data.
- **PSZ conditioning moves the needle in the predicted DIRECTION but not
  to the predicted SIGN:** dispersion-conditioning halves the bleed
  (−90 → −43.5 largemid) yet IC stays negative (−3.77). On our
  universe/costs the published conditional effect does not exist.
- The negative IC is real information: LOW-implied-upside (modest
  expectations) names outperform. A mirror arm (long low-upside) would be
  a NEW candidate in a future batch — but at 22–45% one-way turnover the
  house law (only LOW survives costs) predicts net death; admissible, not
  queued.
- Split guard worked as designed (no adjustment arithmetic anywhere);
  the un-voiding is complete — the family now has an adjudicated result.

**Standing:** target-price family CLOSED as picker in both directions of
the tested arms. Analyst-source families are now 0-for-3 (rev_conf,
tgt_upside, tgt_ld) as pickers.
