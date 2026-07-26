# INSTR-COST-MODEL — Kyle-Obizhaeva invariance spreads replace the flat wall

Registered 2026-07-26 (round 9), FROZEN BEFORE the run. Instrument, never
arms; re-measures already-adjudicated runs under a better cost ruler (no
confirm-wall breach — those months were read by their own trials).

## Why KO and not Corwin-Schultz or Roll (the round-9 reviewer question)

Both proposed estimators are INFEASIBLE on our pull: Corwin-Schultz needs
daily high/low prices, Roll needs the daily return series — `dsf_monthly_agg`
carries neither (only per stock-month `vol_d`, `dollar_vol`, `n_days`,
max/min daily ret). What it does carry is exactly the input set for the
Kyle-Obizhaeva invariance spread — one of the proxy classes Chen-Velikov
validate against TAQ. Chosen on data feasibility, not preference.

## Frozen formula (verbatim source, KO Econometrica 2016 eq. 33 + Table 6)

    s/P = exp(-3.07) * sigma_day * (W / W*) ** (-1/3)
    W   = sigma_day * (dollar_vol / n_days)      [daily trading activity]
    W*  = 0.02 * 40 * 1e6 = 800,000              [benchmark stock]

Point estimate ln(s̄) = −3.07, invariance exponent −1/3 (their α̂₃ = −0.35,
se 0.003 — "economically close"); benchmark stock ⇒ ~9 bps quoted spread,
matching their Table 1 volume-group median (8.12 bps). One-way cost =
**s/2 (half-spread, PRIMARY)**; **s (STRESS)**. Clip [1, 500] bps.
Spread computed from the formation month's own realized dailies (known at
the month-end trade). Names missing daily stats fall back to the flat
cfg cost (disclosed per run).

## Sanity gate (frozen — catches unit errors)

CRSP share-volume unit ambiguity would shift spreads by 100^(1/3) ≈ 4.6×.
Gate: dollar-volume-rank **largemid median half-spread in 2004-2018 must
land in [2, 40] bps** and the **small-segment median must exceed the
largemid median**. Gate fails → fix units, disclose, rerun (mechanical).

## Re-measurement plan (frozen)

1. Regression guard: gp_base small explore at flat 50 bps must reproduce
   the banked 1.96 / +23.2 exactly (the flat path must be byte-identical
   after the harness extension).
2. gp_base and gp_ead, SMALL segment, explore AND confirm windows, under
   (a) KO half-spread primary, (b) KO full-spread stress.
3. Report spread distributions by segment × era (2004-2010 vs 2011-2018)
   for the paper.

**Frozen reading:** BRAIN-008's survivor status is AFFIRMED if confirm net
excess > 0 AND t_net ≥ 0.8 under the PRIMARY arm (same thresholds as its
original confirm rule). Stress arm reported either way. Primary kills it →
survivor demoted to "cost-model-sensitive" in the taxonomy and the paper
shows both hands. Insider survivor (flag harness) out of scope here —
separate re-measure queued.

One shot; crashes before results readable are repairable (disclosed).

## Result (one run, 2026-07-26): **GATES PASS; BRAIN-008 AFFIRMED and strengthened**

`data/factory/instr_cost_model.json`. Coverage 4,234 names/month.

- **Sanity gate PASS:** largemid median half-spread 4.2 bps (2004-2010) →
  3.4 (2011-2018); small > largemid throughout. Levels match the TAQ-era
  literature; CRSP units confirmed correct.
- **Regression guard PASS:** flat-50 path reproduces the banked 1.96/+23.2
  exactly — the harness extension left the flat path byte-identical.

| run (small) | KO half (primary) | KO full (stress) |
|---|---|---|
| gp_base explore | +28.7, t 2.43 | +25.0, t 2.12 |
| gp_base confirm | **+29.9, t 1.11** | +26.2, t 0.97 |
| gp_ead explore | +31.3, t 2.65 | +27.5, t 2.33 |
| gp_ead confirm | **+39.2, t 1.45** | +35.4, t 1.31 |

**AFFIRMED per the frozen rule** (confirm net > 0 AND t ≥ 0.8 in every
cell, both arms). Under invariance-realistic costs the survivor's confirm
t rises 0.89 → 1.11, and the EAD-timed variant reaches 1.45 — the flat
50 bps convention was OVER-penalizing this low-turnover small-cap book.

**Honest implication cutting the other way:** largemid realistic spreads
(~3-4 bps) are far BELOW the flat 25 bps wall, so cost-killed largemid
rejects with real rank information (e.g. si_trend: IC t 2.12, net t −0.92
at flat 25, turnover 0.33 → ~14 bps/mo of cost relief under KO) were
penalized too hard. A single pre-registered re-measure of the cost-killed
shelf (INSTR-COST-REMEASURE-REJECTS) is now ADMISSIBLE — a new measurement
condition, not re-litigation — but it must be one registration, deflated,
AND-rule intact. Queued for panel/Murat decision, not run.
