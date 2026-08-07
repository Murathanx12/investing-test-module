# ONE-SHOT REPLAY — VERDICT (fired 2026-08-08, pre-dawn)

Registration: `TRIALS/PREREG_REPLAY_2.md` (frozen, Murat-ratified) +
`docs/REPLAY2_PREFIRE_ADDENDUM_2026-08-08.md` (two adversarial reviews'
conditions, all committed BEFORE firing). Firing commit c104bcc (Stage A),
cceb34f (Stage B resolver). Raw records: `runs/REPLAY-2/stageA_selection.json`,
`stageB_confirm.json`; tracked copies in `docs/replay_record/`.

## What fired

134 valid (signal, segment) explore rows → BH(q=0.10) vs the certified
REAL-NULL-2 floors (largemid 0.0839 in-band; small 0.1092 in-band, both
n=20,000, guards exact) → **48 BH survivors** → 6 killed by the
statistics-blind family floor → global top-10 cap by t_ic → **10 graduates,
all small-segment** (largemid's best, conc_low 4.46, was confirm-burned by
its own earlier trial; the next largemid t_ic 3.67 was a VOID row; the cap
then cut at t_ic 6.18, all small). Every graduate's explore t_ic (6.18-7.90)
exceeds ALL 20,000 draws of the information-free persistent null and, for
the four σ-family members, their OWN family's p95 as well.

The family floor killed exactly what it was built for: price_level/largemid
at its notorious 2.12, the daily vol arms in largemid, high_52wk_prox and
cg_overhang in small — six BH-passing σ-artifacts, zero capital risked.

## Stage B — all 10 reproduced exactly, all 10 ADOPTED at the 0.75× band

Resolver rebuilt every graduate from source; every explore line reproduced
to the printed decimal (no ABORTED). One confirm read each (2019-2024,
prod book, first read of the small confirm window in project history):

| signal | explore t_ic / t_net | confirm t_ic | confirm t_net | confirm bps/mo |
|---|---|---|---|---|
| cash_prof | 7.90 / 1.26 | 5.90 | 1.10 | +30.3 |
| max_dret_low_D | 7.71 / 0.00 | 5.40 | 0.01 | +0.3 |
| conc_low | 7.41 / 2.31 | 5.53 | **1.34** | **+43.7** |
| defensive | 7.10 / 0.77 | 5.53 | 0.37 | +17.2 |
| ivol_low_D | 6.93 / 0.29 | 5.31 | −0.08 | −4.5 |
| price_level | 6.63 / 0.37 | 5.47 | 1.01 | +38.8 |
| fscore_lite | 6.63 / 1.46 | 4.40 | 0.05 | +1.7 |
| oper_prof | 6.62 / 0.77 | 5.54 | 0.91 | +30.5 |
| roe | 6.27 / −0.24 | 5.71 | 1.28 | +30.4 |
| dtc_high | 6.18 / 0.68 | **7.71** | 0.53 | +10.7 |

## The honest reading, in order of certainty

1. **The small segment held a dense, real information pool.** Held-out
   confirm rank-IC t of 4.4-7.7 on ten candidates is beyond every measured
   null — the persistent information-free floor (confirm p99 ≈ 2.9) cannot
   produce this. NEGATIVE_RESULTS §34 ("nothing small was ever killed; it
   was never seen") is now an out-of-sample empirical fact, not an
   inference. The 0-for-179 record was an artifact of gates that could not
   see the one segment where the information lives.
2. **The σ-family caveat stands for four graduates.** max_dret_low_D,
   defensive, ivol_low_D, price_level carry the documented structural
   rank-IC channel (§32: zero alpha does not imply zero rank-IC under
   heteroskedastic skew) — persistence of their confirm IC was EXPECTED
   under the addendum's analysis and is NOT by itself evidence of
   tradeable edge. Their adoptions are information adoptions.
3. **Tradability is unproven per candidate.** No confirm money leg clears
   t ≥ 1.5 individually. Eight of ten are positive, five at +17 to +44
   bps/mo under flat-25 costs — and flat-25 is believed to UNDERSTATE
   small-cap costs (INSTR-SMALL-SHELF premise). Per the pre-fire addendum:
   **no lane is seeded from any of these adoptions without a separately
   pre-registered money-leg trial.** The ADOPT_075 size labels are S3
   ledger states, not deployments.
4. The worst-case accounting printed at fire time (E[false] ≥ 3.6, the
   marginal ≥0.36 fallback — conditioning support was 0 because no null
   draw reached the realized bar of 6.18) is now superseded by the realized
   evidence: each adoption's confirm IC sits beyond the null's p99 by 1.5-5
   sigma-equivalents. The binding uncertainty is not "is the IC luck" but
   "is the IC monetizable in small caps after real costs."

## Bookkeeping

- si_chg_low/small (t_ic 6.09, explore t_net 2.16 — the strongest money
  leg in the bank) missed the cap by ONE slot at rank 11. It exits
  UNADJUDICATED with confirm unread, available to a future registration.
  32 BH+family survivors below the cap are preserved likewise.
- Negative-bias families (illiquidity, drawdown) exit UNMEASURED, not
  DEAD, per the addendum (structurally unable to clear a positive floor).
- Largemid: zero graduates. Under the committed empty-result
  interpretation this licenses no claim about largemid's pool.
- Both one-shot windows are now spent for the 10 graduates; the small
  confirm window is spent for them alone (below-cap candidates' windows
  remain unread).

## Next steps (in registration order)

1. **TRIAL-REPLAY-BOOK-1 (to be registered):** ONE pre-registered money-leg
   trial of the adopted set as an equal-weight 10-signal small book —
   KO-half + stress-50 cost arms, §28 leg decomposition, random-book
   placebo. This is the tradability adjudication the confirm ICs earned.
2. If the book trial passes: attended paper-lane seeding (Murat flips the
   flag), forward clock starts, 24-month no-skill-claim rule applies.
3. EXT-BANK-1 cohort trials proceed independently (PROF-SMALL-1's OSAP
   externals overlap this adopted set at the construction level — a
   cross-validation opportunity, noted before its run completes).
