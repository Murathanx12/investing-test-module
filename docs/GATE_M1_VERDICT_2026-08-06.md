# GATE-M1 FINAL VERDICT — full grid complete (2026-08-06)

**Registered design:** n=250 reps/cell, 13 cells (α∈{0}, {0.2,0.4,0.6}×{I1,I2,I3,I4}),
ρ_sig=0.5, DGP-A v6 null panels, CRN across α, frozen production replay
(21 signals + injected candidate = 42/cell, BRAIN-008 confirm, DSR/PBO ladder
at n_trials=42 primary / 179 recorded). Chain completed 2026-08-06 14:32
(2nd sentinel, chain.log). Tables: `runs/GATE-M1/stage3_tables.json`.

## Headline (Table 1)

| | α=0 base | α=0.2 | α=0.4 | α=0.6 |
|---|---|---|---|---|
| **FDR / false-kill (n42)** | FDR 0/250 (Wilson ≤1.5%) | 100% all designs | 100% all designs | 100% all designs |
| P(graduate) I1/I2/I3/I4 | 0 | .4/.4/0/0 % | 2.0/2.0/0/1.2 % | 6.8/6.4/0/4.0 % |
| P(confirm pass) | 0 | 0 | 0 | I1 1.2%, I4 0.8%, I2/I3 0 |
| P(adopt) | 0 | 0 | 0 | 0 |

**Zero adoptions in 3,250 cells. cap_crowded_out = 0 everywhere.**

## The Gate M criterion FIRES
False-kill at α=0.4 = **100%** (criterion threshold was ~50%). Confirmed on
all four injection designs at the full registered n.

## Stage attribution (Table 2) — what kills, per design
- **Explore t_net≥1.5 bar kills ~everything** (no_graduate ≥93% in every
  injected cell). Mechanism (threshold_sweep.json): null decile book
  E[t_net]=−0.91 from turnover cost drag; a TRUE α=0.4 edge averages t_net
  −0.23 but t_ic +1.67. The gate demands cost-beating proof at explore that
  the implementation cannot deliver even when the edge is real.
- **I1 (constant edge) answers the confirm-wall question:** for the survivors,
  confirm is a second independent killer — a0.6/I1: 17 graduate → 14 die at
  confirm, 3 pass → all 3 die at DSR. Even a NON-decaying edge that clears
  explore cannot get adopted under the current ladder.
- **I3 (small-only edge): structural blindness confirmed** — 0 graduations at
  every α. The largemid explore scan cannot see a small-cap edge at all.
- **I4 (size-correlated) ≈ I2/I1** — the size confound neither helps nor
  masks; graduation slightly below I1 (edge partially projected onto size).

## Posterior map: NOT shipped
Pre-registered monotonicity gate failed again at full n: bucket (2,1,0) has
1 obs vs (1,1,0)'s 21 → sparse-bucket violation (0.17 < 0.59). Per the
committed spec (33d1b66) the map does not ship. Re-estimate after
recalibration, when evidence actually flows past explore.

## Sensitivity + counterfactual
- IC-only explore gates (sweep, banked reps, no rescans): t_ic≥2.0 → FDR
  0.8%, power 38% @α=0.4; t_ic≥1.5 → FDR 3.6%, power 59%. Loosening the
  joint t_net gate maxes at ~22% power.
- ρ ∈ {0.3, 1.0} sensitivity waves NOT yet run (registered, ~4h each, I2-only).

## Standing recalibration proposal (MURAT-ATTENDED, not yet ratified)
Gate explore on t_ic (2.0 headline / 1.5 sensitivity), demote t_net to
diagnostic, move the cost hurdle to implementation/sizing (turnover
engineering + posterior sizing ladder). Then re-run this grid on the new
gate before any new family runs. See
aegis-finance/docs/OPUS_HANDOFF_DECISION_ENGINE_2026-08-05.md §2.

## Fidelity + injector (unchanged from stage commits)
Stage 1 (0a7e0fd): DGP-A v6, F1–F8 all PASS (deterministic c_t
re-standardization). Stage 2 (d97c9e1): injector certified — PF Sharpe
within 0.4% of target at all 36 gate cells, ≥99.95% nonzero, α=0 exact no-op.
