# RECAL-1 VERDICT — run 2 FINAL (chain complete 2026-08-07 22:00)

Bank: 1250 reps × a0.0/base (250 CRN + 1000 fresh) + 250 reps × 10 injected
cells. Chain green end-to-end (wave 2 verified, wave 3 clean, coverage
assertions passed). All rates below are **per-candidate FPRs under DGP-A v6
and the registered selection rule** (Amendment 3 language) — the real-data
placebo (REAL-NULL-1) measures the persistent-candidate analogue ~2.3×
higher, which is why the replay is blocked pending REPLAY-2 regardless of
the ladder chosen here.

## 1. Acceptance targets — final scoreboard

| | target | result |
|---|---|---|
| A1 | FPR ≤ 5%, Wilson ≤ 8% | **PASS, tightened**: 15/1000 fresh = **1.5% [0.91, 2.46]** (run-1 n=250 gave [0.62, 4.04]) |
| A2 | P(adopt \| α=0.4, I1) ≥ 30% | PASS (43.6%) |
| A3 | P(adopt \| α=0.2, I1) ≥ 10% | PASS (16.4%) |
| A4 | P(grad \| α=0.4, I2) ≥ 30% | PASS (56.4%) |
| A5 | P(grad \| α=0.4, I3) ≥ 30% both-seg | MISS at top-5 (28.0%); **BRAIN-010 (top-10) delivers 42.4% adopt** — see §3 |
| A6 | posterior monotone → shipped | fine map still NON-MONOTONE (not shipped); **S3 ships, re-confirmed on fresh nulls with one band change** — see §2 |
| A7 | held-out within Wilson overlap | PASS everywhere measured |

## 2. Sizing ladder: fresh nulls demoted the middle band — this is the system working

Run 1 (250 nulls): never-confirm 0× / confirm t_ic<1.5 **0.25×** (p_real
0.601 on 7 null events) / ≥1.5 0.75×.
Run 2 (1250 nulls): the middle class now holds 61 null events of n=285 →
p_real **0.477 < 0.60 floor → 0×**. Final shipped S3:

| evidence class | n | p_real | size |
|---|---|---|---|
| never reached confirm | 1503 | 0.098 | 0× |
| adopted, confirm t_ic < 1.5 | 285 | 0.477 | **0× (was 0.25×)** |
| adopted, confirm t_ic ≥ 1.5 | 212 | 0.848 | 0.75× |

Consequence: an adoption with weak confirm evidence gets a ledger entry and
zero capital. The run-1 band was undersampled optimism; wave 3 existed to
catch exactly this, and did. (I2-conditioned ladder: still no ship — correct,
per the §1(a) decay arithmetic.)

## 3. BRAIN-010 (both-seg / top-10), scored exactly as registered — ALL PASS

Registered blind at wave-3 rep ~420/1000 (`BRAIN010_REGISTRATION_2026-08-07.md`),
scored on the 1000 fresh nulls, CRN-paired:

| rule | result |
|---|---|
| E1: point ≤ 0.05 AND Wilson-hi ≤ 0.065 | **PASS** — 29/1000 = 2.90% [2.03, 4.13] |
| E2: (B10 − B9) ≤ 2.0pp paired | **PASS** — +1.40pp (29 vs 15; 14 reps adopt under both) |
| E3: largemid power within Wilson overlap of freeze | **PASS** (0.432 vs 0.436; held-out 0.440 both) |
| Pre-registered prediction: FPR ∈ [1.5%, 3.5%] | **HIT** (2.90%) |

That is the third consecutive pre-registered parametric prediction to land
(RECAL-1 §11, run-2 §3 direction, now BRAIN-010). BRAIN-010 buys: small
segment 0.016 → 0.424 adopt at α=0.4 (0.784 at 0.6), I4 0.368 → 0.544, at
+1.4pp simulator FPR.

## 4. n=1250 selection sensitivity (labelled, freeze untouched)

With 625 nulls per half, run-1's runner-up becomes feasible and wins:
**explore 1.25 / confirm 0.5, largemid, top-5** — power 48.8% (held-out
48.0%), FDR 2.72% sel [1.71, 4.31] / 1.92% held-out [1.10, 3.33]. Recorded
as `brain009_selection_n1250.json`, SENSITIVITY ONLY. Note: a swap to 1.25
is threshold-contaminated territory (the largemid preview was run against
1.5; 1.25 admits strictly more of what was previewed) — if wanted, it needs
the same treatment BRAIN-010 got: a named registration with a blind test,
not a quiet swap.

## 5. The attended menu (nothing moves without Murat)

| option | sim FPR (n=1000 fresh) | power α=0.4 (I1 / I3 / I4) | contamination status |
|---|---|---|---|
| **BRAIN-009 (freeze)** | 1.5% | 0.436 / 0.016 / 0.368 | threshold previewed (disclosed) |
| **BRAIN-010** (registered, E1-E3 PASS) | 2.9% | 0.432 / **0.424** / 0.544 | cap+small clean; threshold same as freeze |
| 1.25/0.5 sensitivity | ~1.9-2.7% | 0.488 / 0.016 / — | would need blind registration |

My recommendation, for what it is worth: **BRAIN-010** — it is the only
option that repairs the measured structural blindness (I3), it passed a
blind test with a pre-registered prediction, and its +1.4pp simulator FPR
is honest coin. But per Amendment 3, the ladder choice is secondary to the
REPLAY-2 error-control redesign: whichever ladder is ratified, the replay
prints batch-level expected-false-adoption accounting derived from
REAL-NULL-1's real-data rates (explore ~0.082 persistent-arm, confirm
~0.36), not from these simulator numbers.

## 6. Standing state after this verdict

- RECAL-1 is **closed as a calibration exercise**: every acceptance target
  adjudicated, two ladders measured, sizing ladder shipped with
  fresh-null-confirmed bands.
- The replay remains **BLOCKED** (Amendment 3) until REPLAY-2 registers:
  batch-level error control, cap semantics, correlation-indexed veto (R²
  diagnostic first), real-data explore floor, joint ladder+sizing rule.
- One-shot discipline intact: 179 candidates still unadjudicated under any
  new ladder; small-segment candidate rows still unexamined.
