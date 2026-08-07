# REPLAY-2 — PRE-FIRE ADDENDUM (committed before Stage A fires)

Two independent adversarial reviews (code attack + methodology attack,
2026-08-08 overnight) both returned DO-NOT-FIRE with executable paths to
FIRE. Every item below is either implemented in `replay_runner.py` at the
firing commit or committed here as binding interpretation. **No frozen
parameter (q, thresholds, cap, sizing, ladder) changed.**

## 1. Resolution of the §3 ambiguity — the conservative reading (methodology F1)

The correlation-surface gate failed (R² 0.14-0.21), which activated the
flat-floor fallback. But the D1 evaluation that justified BH used
per-signal null CDFs; the flat floor alone measures E[null qualifiers] ≈
7.8 on the simulator's own geometry because directional families dominate
(a pure-noise small price/vol construction clears the BH bar 17-49% of the
time once a few rejections exist; a real illiquidity edge can never clear).

**Binding resolution:** PREREG_REPLAY_2 §3's threshold-rule sentence — "each
candidate's bar is max(semantic-family p95, empirical-neighbor p95)" —
retains its SEMANTIC component, which never depended on the failed
correlation surface. The replay bar is therefore:

    BH(q=0.10) on p vs the segment's flat REAL-NULL-2 floor
    AND t_ic >= max(semantic-family p95, generic p95)

with families assigned statistics-blind by `TRIALS/family_ontology.json`
(written 2026-08-08 from construction code only, per KILL_AUDIT Amendment
2 §2 — the mandated file that did not previously exist). This caps the
σ-family false-pass at ≈5% and costs nothing for generic candidates.
Negative-bias families (illiquidity, drawdown) get the generic bar via the
max; their rejections exit as **UNMEASURED, not DEAD** (they were
structurally unable to clear a positive floor at any plausible effect size).

## 2. Empty-result interpretation (methodology F3) — committed BEFORE firing

This replay was configured to bound false adoptions at the cost of power:
P(adopt nothing) ≈ 0.90 if none of the candidates carry an edge, and
≈ 0.81-0.99 if three to five carry real α = 0.2-0.4 edges. An empty result
has a likelihood ratio near 1 between "the pool is dead" and "the pool
holds several modest real edges" and MUST NOT be reported as evidence that
the candidates were false. An empty result licenses exactly one claim: no
candidate cleared a bar calibrated so that noise almost never clears it.
Resurrection statuses (UNMEASURED / UNDERPOWERED / SUPPORT-INADEQUATE)
survive an empty replay unchanged. A non-empty result is the informative
branch; for generic-family adoptions the posterior odds are ≈ 4:1 real,
and for σ-aligned adoptions the family floor (not the flat floor) is the
operative error control.

EXT-POWER-1's external measurement (only 15.3% of 196 published predictors
clear even the plain explore bar in largemid) independently confirms that
low power against real effects is the expected regime.

## 3. Rank-signal adoptions (methodology F6)

An adoption whose printed gross-t receipt is ≤ 0 is a **rank-signal
adoption, not a tradeable-edge adoption**; its S3 size label is not
seedable capital. No lane is seeded from any replay adoption without a
separately pre-registered money-leg trial. (Consistent with S3 semantics
and attended seeding; contradicts nothing frozen.)

## 4. Accounting corrections (methodology F4/F7/F8, code F4/F5/F7)

- Both columns print: real-basis AND simulator-basis E[false adoptions].
- Real-basis figures carry "≥" labels: the persistent floor is a LOWER
  bound (real candidates are more persistent than any tested arm — the
  narrow side is the anti-conservative side for error control).
- The confirm-null basis is computed CONDITIONALLY from REAL-NULL-2's
  saved (explore, confirm) pairs at each segment's realized graduate bar
  (BH selection is stricter than the t≥1.5 conditioning of the marginal
  0.36); marginal ≥0.36 is the fallback when conditioning support < 50.
- Dependence caveat printed verbatim: BH's PRDS hypothesis is not
  assertible for a batch containing mirror constructions; the
  Benjamini-Yekutieli worst case is ≈ 0.54; the operative evidence is the
  measured CRN evaluation, not the theorem. False adoptions cluster within
  construction lineages; P(≥1) is optimistic in the tail.
- Cap-ordering disclosure: raw-t_ic ranking across segments favors small
  (wider floor); within-segment empirical p is printed per graduate.
- Denominator semantics: a candidate is a (signal, segment) row; the
  freeze output prints the reconciliation (universe rows, VOID rows,
  empty-t_ic rows, contaminated/burned exclusions) against the historical
  cumulative count, which includes event/macro/instrument trials that were
  adjudicated outside the batch CSVs.

## 5. Universe receipts (code F1/F2)

- `batch3a_daily_rerun.csv` (max_dret_low_D, ivol_low_D, amihud_D) and
  `batch5_defensive_rerun.csv` (defensive) ENTER the universe: their
  original summary rows are empty months=0 broken-pipe rows and the reruns
  are the valid explore statistics ("a broken pipe fixed, not a retry").
  Their old "closed as screen-class" status was an adjudication under the
  0%-power net-gated ladder — re-judging such kills is the replay's stated
  purpose. As σ-family constructions they face the family floor (small
  vol/max p95 ≈ 4.2-4.3), which is the registered defense.
- `batch3b_tgt_rerun.csv` stays OUT (both tgt_upside runs VOID, IBES
  receipt). `trial_tgt_rebuild.json` rows enter (split-guarded, confirm
  unread).
- Missing required inputs ABORT the run (no silent shrink). ALL selection
  inputs are SHA-256-hashed in the freeze output, including the rebuild
  json, the ontology, and the frozen family table.
- The firing commit hash is recorded in the freeze output's repo state;
  Stage A fires only from a clean checkout.

## 6. Small-segment floor discipline (methodology F10, code F8)

The prereg gave largemid a replication VOID band but small only a scored
prior. Extension, committed before the small run lands: **if the small
pooled P(t_ic ≥ 1.5) falls outside [0.08, 0.20]** (the declared-prior band
widened one notch on each side), the run is diagnosed before use exactly as
a largemid band violation would be. The small floor's certification is
code identity with the guarded largemid harness; the fired output states
this.

## 7. Verified-safe inventory (code F8)

empirical_p tie/monotonicity/resolution, bh_reject (0/22k mismatches vs
references), load_floor VOID refusal, REAL-NULL-2 guard gating both
segments, seed independence, stationary AR(1) init — all independently
verified by the code-attack agent. The K=3 smoke artifacts on disk cannot
fire the runner (status VOID-REPLICATION + n_pooled check).
