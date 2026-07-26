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

## Result

(to be filled by the one run)
