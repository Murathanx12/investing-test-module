# INSTR-COST-REMEASURE-REJECTS — the cost-killed shelf under the KO ruler

Registered 2026-07-26 (round 10), FROZEN BEFORE the cohort is even listed.
Instrument, one shot, permanently closes the cost-killed shelf. Panel
round-10 mandate (both reviews: YES with airtight guardrails). This is a
measurement-instrument change applied uniformly — not re-litigation: no
spec, direction, window, or rule of any signal changes; only the cost
scalar (flat wall → KO invariance spreads, INSTR-COST-MODEL).

## Frozen cohort rule (mechanical; committed before application)

From the banked explore summaries (`data/factory/batch*_summary.csv`),
segment **largemid** (the graduation segment, where flat-25 most exceeds
realistic ~3-4 bps spreads), take every non-contaminated signal row with:

    t_ic >= 2.0            (rank leg PASSED)
    t_excess_gross >= 1.5  (gross leg PASSED)
    t_excess_net < 1.5     (net leg FAILED — died of costs alone)

This is exactly "graduation-but-for-costs." Signals killed on merits
(inverted, no rank, no gross) cannot enter — the filter excludes them
mechanically, whatever their family. An EMPTY cohort is a valid and final
result: it means the flat wall never falsely buried a graduate.

## Frozen procedure

1. Apply the rule; print the cohort (mechanical, no discretion).
2. Rebuild each cohort signal byte-identically from its original batch
   builder (same spec, direction, hold-band, window). Builder wiring for
   the specific names is mechanical plumbing, disclosed, not tuning.
3. Re-scan explore 2004-01..2018-12, largemid, under KO **half-spread
   primary** (per-name cost_frame; missing names fall back flat-25) and
   **full-spread stress**.
4. **Graduation re-check (unchanged rule):** t_net >= 1.5 AND t_ic >= 2.0
   under the primary arm.
5. Any graduate → ONE confirm run (2019-01..2024-12, largemid, KO half):
   PASS iff net excess > 0 AND t_net >= 0.8 AND t_ic >= 1.5 (the standard
   confirm mirror; 72-month power note applies). DSR reported at
   n_trials = 155 with the re-measure provenance disclosed.
6. Old (flat) and new (KO) outcomes recorded side by side, permanently.
   Failures under KO die permanently — no further cost-model appeals.

One shot; crashes before results readable are repairable (disclosed).

## Result (one run, 2026-07-26): **COHORT EMPTY — the flat wall never falsely buried a graduate. Shelf permanently closed.**

The frozen rule returned ZERO signals. Both near-miss tables banked
(`batch*_summary.csv` derived, disclosed):

- Rank-real rejects (t_ic ≥ 2, net < 1.5): best GROSS t is
  net_issuance_low at **1.48** — below the 1.5 gross bar, so it cannot
  graduate even at ZERO cost. Next: comp_issue_5y 1.42, then a cliff
  (0.77 and down). The issuance shelf remains "closest to the bar";
  the bar stands.
- Gross-passed-net-failed (t_gross ≥ 1.5, net < 1.5): **literally empty**
  — no largemid signal in 155 candidates ever had a gross-passing book
  that costs killed.

**The finding, stated for the paper:** in large/mid caps, trading costs
were never the sole executioner. Every largemid rejection was
INFORMATIONAL — the book was too weak gross, or the rank information
wasn't there. Combined with INSTR-COST-MODEL (realistic largemid spreads
~3-4 bps) and INSTR-CZ-CALIB (fame-proportional decay), the picture is
coherent: what is dead in large caps is dead because it was arbitraged
away, not because our cost assumptions were harsh. No KO re-scan was
needed — the procedure terminates at step 1 with a final, permanent
closure. No further cost-model appeals exist for the shelf.
