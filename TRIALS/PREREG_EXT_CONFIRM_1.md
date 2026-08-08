# PRE-REGISTRATION — TRIAL-EXT-CONFIRM-1 (2026-08-08)

**Written BEFORE any confirm statistic exists for these candidates.**
Registered under CANON §6, EXT-BANK-1 accounting.

## Candidates (2, named, one confirm read each — then spent forever)

- **osap_GP** (Novy-Marx 2013), small segment. Explore (seen, disclosed):
  t_ic 7.24, t_net 2.40 flat / 2.46 KO-half, long-leg share 0.289.
- **osap_OperProfRD** (Ball et al. 2016 operating profitability ex-R&D),
  small segment. Explore (seen, disclosed): t_ic 8.92, t_net 2.81 flat /
  3.00 KO-half, long-leg share 0.222.

Why these two and only these two: they are the only external candidates
that cleared BH + BOTH cost arms in TRIAL-EXT-PROF-SMALL-1 (killed as a
family by the defective share gate, defect documented in its verdict).
Full explore disclosure means this trial's ONLY new evidence is the
held-out 2019-2024 window — which is untouched for both.

## Design (frozen)

Confirm scan 2019-01..2024-12, small segment, production book mechanics
(top decile, 30% hold band), flat-25 AND KO-half cost arms, leg
decomposition reported. Guard: the harness must reproduce each candidate's
banked explore line exactly (7.24/2.40; 8.92/2.81 from
`runs/EXT-BANK-1/trial_ext_prof_small_1.json`) before the confirm read.
Money-leg placebo: 5 seeded information-free persistent AR(1) signals
(φ=0.99, seeds 11-15) through the identical single-signal confirm book.
Information null: REAL-NULL-2 small pooled confirm CDF (n=20,000, saved).

## Decision rule (frozen, per candidate)

- INFORMATION: confirm ic_mean > 0 AND t_ic ≥ 0.5 (BRAIN-010 wall), with
  empirical p vs the REAL-NULL-2 small confirm CDF printed.
- **MONEY (the object of this trial): TRADABLE-PASS iff confirm t_net ≥ 1.5
  flat-25 AND ≥ 0.8 KO-half AND exceeds every placebo's confirm t_net.**
  WEAK if flat-25 t_net in [0.8, 1.5) and above all placebos (attended
  seeding decision, no default). FAIL otherwise.
- A TRADABLE-PASS candidate becomes the first external candidate eligible
  for an attended forward paper-lane proposal (Murat flips any flag; the
  24-month no-skill-claim clock applies from inception).

## Declared prior (scored afterwards)

Post-publication decay (McLean-Pontiff ≈ halving) off explore t_net
2.4-2.8 over a 72-month window predicts confirm t_net ≈ 0.8-1.6. Point:
GP 1.1, OperProfRD 1.4. P(≥1 TRADABLE-PASS) ≈ 0.35; P(both) ≈ 0.10.
Most likely wrong because: 2019-2024 contains the 2020-2021 junk rally —
profitability's worst historical regime — so the miss direction is DOWN.

## One shot

Output `runs/EXT-BANK-1/trial_ext_confirm_1.json` write-once. Any repair
after reveal is a new trial ID.
