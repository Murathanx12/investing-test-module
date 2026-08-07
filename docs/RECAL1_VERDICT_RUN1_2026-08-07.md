# RECAL-1 VERDICT — run 1 (grid 2026-08-06 22:53 → 2026-08-07 02:15)

**Bank:** 250 reps, wave 1 only (a0.0/base + I1 × {0.2,0.4,0.6}), ρ_sig=0.5,
same SEED_BASE as M1 so the control arm is CRN-paired. Spec:
`RECAL1_SPEC_2026-08-06.md`. Freeze record: `runs/GATE-M1/brain009_frozen.json`.

## 1. The headline: the IC gate works

| | BRAIN-008 (frozen) | **BRAIN-009 (recalibrated)** |
|---|---|---|
| FDR (α=0, n=250) | 0.0% | **1.6%** (Wilson 0.44–5.65%) |
| P(adopt) α=0.2 / I1 | 0.0% | **16.4%** |
| **P(adopt) α=0.4 / I1** | **0.0%** | **43.6%** |
| P(adopt) α=0.6 / I1 | 0.0% | **79.6%** |
| held-out half (odd reps) | 0.0% | **44.0%** at α=0.4, FDR 1.6% |

Measured on the same 250 panels. The factory went from adopting **none** of
the real edges to adopting **44%** of a medium one, while still adopting junk
only 1.6% of the time.

**Acceptance targets:** A1 PASS (FDR 1.6% ≤ 5%, Wilson upper 5.65% ≤ 8%).
A2 PASS (43.6% ≥ 30%; the 50% stretch missed). A3 PASS (16.4% ≥ 10%).
A7 PASS — selection half 43.2% vs held-out 44.0%, no simulator overfit.
A4/A5 NOT MEASURED (see §3). A6 partially met (see §4).

**The pre-registered prediction (spec §11) was correct**, including its
caveat: it called explore t_ic ∈ [1.25,1.5], confirm t_ic ∈ [0.5,0.75], FDR
1–3%, power 35–47%, and predicted the stretch would be missed "narrowly and
by the confidence rule rather than the point estimate". Selection landed on
explore 1.5 / confirm 0.5, FDR 1.6%, power 43.6% — and the highest-power
ladder (explore 1.25 / confirm 0.5, **48.8%**) was rejected on its Wilson
bound alone (0.090 > 0.080) with a point FDR of 4.0%, inside the budget.

## 2. What the frozen ladder concedes — stated plainly

```
BRAIN-009: explore t_ic >= 1.5 (rank by t_ic, largemid, top-5 cap)
           confirm t_ic >= 0.5 + IC sign gate,  t_net diagnostic only
           DSR threshold 0.0   PBO threshold 1.0   book: production
```

**DSR and PBO both went inert.** Adoption is now decided entirely by the two
IC gates plus the IC sign gate. This is the outcome §1(b) and §10 predicted
and it must not be dressed up: the multiple-testing defence that remains is
(a) the IC stack itself, whose false-discovery rate is *measured* at 1.6%
rather than assumed, and (b) the DSR/PBO numbers, still computed and reported
per candidate but no longer gating. The calibration also shows why: DSR ≥ 0.95
on a 72-month single-signal book needs SR_ann ≈ 1.5 against ~0.03 delivered,
and PBO on a 42-book batch of which 41 are null is a coin flip (0.514 on the
α=0 cell, 0.586 on a cell holding a true α=0.6 edge).

The ratified starting point would **also** have adopted nothing: the seed
ladder (explore 2.0 / confirm 1.0 / engineered book / DSR 0.95 / PBO 0.5)
scores **0% power**. Calibrating the whole ladder, not just the explore gate,
was the load-bearing part.

Where true edges still die at α=0.4/I1: 37% never graduate, 3% are crowded
out by the top-5 cap, 16% fail confirm. Nothing dies at DSR or PBO.

## 3. What run 1 did NOT establish — a silent no-op

**Wave 2 never ran.** `run_rep_bank` skipped on the existence of the rep
*file*, and wave 1 had already created every file, so wave 2 reported
"exists, skipped" for all 250 reps in 24 seconds and exited 0. The chain
logged success. The M1 grid had avoided this only by putting the wave in the
filename.

This is the house failure mode — green, silent, empty — and it was mine. Two
fixes are in: the skip is now **cell-aware** (a rep merges the cells it is
missing, reusing scans already paid for), and every wave now runs a
**coverage assertion** over its own rep files and exits non-zero if any
requested cell is absent.

Consequence: A4 (I2 explore graduation), A5 (I3 structural blindness) and the
I4 size-confound arm are unmeasured, and the I2-conditioned posterior was
computed on n=0 for every α>0. It did not ship — the monotonicity gate caught
it — but the run cost the design sweep.

## 4. Sizing ladder: SHIPPED (coarse), fine map still not

The pre-registered fine map failed its monotonicity gate again (12 violations
on 2 coordinates, 46 on 3). The diagnosis is not the ordering: in high-
evidence buckets the α=0 count is **0 or 1**, and with Jeffreys add-half that
single observation swings P(α≥0.2) by ~0.23. That is bucket resolution
exceeding what 250 null reps support. The DSR axis was additionally dead on
arrival — its top bucket held n=1–3 across 1000 cells, because the frozen
ladder makes DSR inert — so it is dropped (spec §12).

Applying a *rule* rather than a pick — walk coarsenings finest-to-coarsest,
ship the first that is monotone on the selection half AND the held-out half
AND pooled — S5 fails, S4 fails on the odd half (correctly rejected), and S3
ships:

| evidence class | n | α=0 count | P(α≥0.2) | size |
|---|---|---|---|---|
| never reached confirm | 562 | 242 | 0.096 | **0×** |
| confirm t_ic < 1.5 | 231 | 7 | 0.601 | **0.25×** |
| confirm t_ic ≥ 1.5 | 207 | 1 | 0.830 | **0.75×** |

`runs/GATE-M1/sizing_ladder_r1_BRAIN-009_I1.json`. **Provisional**: the
coarsening ladder was defined after seeing run 1's violations, so S3 must be
re-confirmed on null reps it was not chosen on (run 2, wave 3).

## 5. Verdict

The recalibration is **established** on its binding targets and validated
out-of-sample. What is missing is breadth (the design sweep) and null
resolution (FDR precision, sizing-ladder confirmation) — both are compute,
both are scheduled as run 2, and neither threatens the headline result.
