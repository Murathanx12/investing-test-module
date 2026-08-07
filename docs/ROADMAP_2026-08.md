# Research Roadmap — post-RECAL-1 (updated 2026-08-08)

Supersedes ad-hoc queues in the synthesis docs. Order is load-bearing.
Attended items are marked ⚑ (nothing moves without Murat).

## Phase 0 — decisions on the table now

| # | item | status |
|---|---|---|
| ⚑ 0.1 | Ratify ladder (recommendation: BRAIN-010 — E1/E2/E3 all PASS, prediction HIT 2.90%) | waiting on Murat |
| ⚑ 0.2 | Freeze `TRIALS/PREREG_REPLAY_2_DRAFT.md` (BH q, episode floor, D1-vs-D2 rule) | draft written; waiting on Murat |
| ⚑ 0.3 | Decide whether the 209 OSAP predictors enter the candidate bank (moves count off 179, changes deflation denominators) | waiting on Murat |
| 0.4 | Score EXT-POWER-1 M4 (fraction of 209 published predictors clearing explore in largemid) against the declared 30-50% prior | scan resumed, running |

## Phase 1 — REPLAY-2 build (compute-light, no grid nights)

1. R² correlation-surface diagnostic on the 21 banked signals (~20 min) —
   settles the veto index (ship gate R² ≥ 0.7, else flat real-data floor).
2. Evaluate D1 (BH on empirical p, real-null floor) vs D2 (e-BH) on the
   EXISTING bank, even/odd discipline. Pareto rule per REPLAY-2 §1.
3. Confirm-stage certification via block-wild resampling of cached confirm
   months (GPT §5.2): 100-500 cheap replicates per panel, validated against
   25 full panels within 2 pooled MCSE. ~1-3 core-hours.
4. ⚑ Freeze REPLAY-2 → one-shot replay with expected-false-adoption
   accounting (real-data basis: explore 0.082, confirm 0.360) printed first.

## Phase 2 — overnight-grid candidates (the ONLY things that still need nights)

| run | what | why |
|---|---|---|
| WORLD-8 certification | Insert the verified two-point rank-real/payoff-dead construction (GPT §5.1; competes with jackpot-compensation design) into DGP-A v6; F1-F8 must stay in tolerance; calibrate λ to IC targets | closes the "rank artifact wearing an edge's clothes" hole in injection design |
| WORLD-9 + future-seeded canaries | 32 canary generators, NIST/drand seed after commit, mutation-suite detection ≥ 95% | generalizes the `assert_coverage` lesson: execution can't be faked |
| (optional) correlated-candidate real-null | REAL-NULL-1 machinery, batches of signals sharing real residual structure — batch-level max-t behavior | feeds D1/D2 evaluation if the existing bank proves insufficient |

NOT needed: another A1-style fresh-null night. n=1000 already gives Wilson
[0.91, 2.46] (B9) / [2.03, 4.13] (B10); more reps tighten intervals without
changing any decision. The binding uncertainty is simulator FIDELITY
(real-null 2.3×), which more simulator reps cannot reduce.

## Phase 3 — era expansion (the "more than 2004-2018" environment)

Right instinct, with registration discipline. Current panel is
`crsp_panel_2002` (2002+). Expansion:

- **WRDS pulls needed:** CRSP MSF/DSF pre-2002 (back to 1971 to match OSAP;
  1926 available) **with delisting returns**; Compustat annual/quarterly
  pre-2002 + CCM link table; run the 1-hour WRDS entitlement audit first
  (also answers TAQ/Intraday-Indicators and Audit Analytics availability).
- **Already in hand:** OSAP signals 1971-12+ (5.4M rows cached); Fama-French
  factors; fja05680/sp500 membership 1996+ (universe half of NR §4).
- **What the eras buy:** (a) independent-episode counts for the
  SUPPORT-INADEQUATE floor (GPT §1.5); (b) a calibration/design testbed fully
  disjoint from BOTH one-shot windows — gate designs can be tuned on
  1975-2001 without touching 2004-2018 explore or 2019-2024 confirm;
  (c) era-robustness receipts for survivors.
- **Rules:** every new era is registered before first scan (CANON §6);
  pre-2004 cost models recalibrated (spreads/ticks differ — Rule 605 history
  reaches 2000, MIDAS 2012+); no era added to a candidate's evidence
  after its result is seen.

## Phase 4 — adopted-idea queue (credited; post-replay unless noted)

**Resurrections (tax + registration each):** rec_mom buy/hold rank band
(NMV 2016; the one clean cost-kill); §28 exclusion book (placebo-gated);
§17 mirror (tgt_upside_low — VOID-run provenance check first);
options-confirmed 13D (family tax, OptionMetrics banked).

**Infrastructure:** pre-trade intent hashing + version sleeves/shadow NAV for
lanes (GPT §1.6); OpenTimestamps hash-chaining of registrations; blind human
adjudication packet (HKU faculty/grad student) + NIST beacon audit sampling;
`/api/null/t_ic` + `/api/ledger` public endpoints (retention product);
entropy-pooling (BSD-3) portfolio adoption, gated: priors/views external to
the evaluated strategy.

**Data hunt (triage order):** MIDAS + Rule 605 (capacity curve, public);
Federal Register/GovInfo XML (as-published rule shocks); USPTO
ODP/PatentsView; N-PORT (2019+, redemption-fragility); FAERS quarterly
archives; Audit Analytics (entitlement-dependent); USAspending; EDGAR logs
attention conditioner (2003-2017).

**Paper track:** the citable experiment = Ruler Benchmark + randomized
ledger-access experiment (GPT §2.6 merged with round-3 adoption).

## Standing constraints (unchanged)

Small-segment rows unexamined until the replay fires. Freeze records never
edited (dated banners only). Keys env-only. Pre-register before compute.
Placebo gate on every control-armed design. LLM narrates, engine computes.
Guards need callable entry points + tests. No skill claims before 24 months
(lane inception 2026-06-08).
