# PREREG — REPLAY-2 (FROZEN 2026-08-08)

**Status: FROZEN. Murat attended 2026-08-08 and delegated the open parameters
("choose the best for me", on record in the session transcript). Ratified:**

1. **Ladder = BRAIN-010** (both-seg / top-10; E1/E2/E3 all PASS, blind,
   prediction band hit at 2.90%).
2. **Error control = D1 (BH step-up on empirical p-values, real-null floor),
   q = 0.10**, with D2 (e-BH) as challenger under the §1 Pareto rule —
   evaluated on the existing bank BEFORE the replay; whichever the
   pre-stated rule selects, ships.
3. **Episode floor for SUPPORT-INADEQUATE = 3 independent episodes.**
4. **OSAP predictors: ENTER as a SEPARATE batch (EXT-BANK-1), the 179
   untouched.** The 179 replay runs under this registration with its own
   BH accounting over its own 179-candidate denominator. The 209 OSAP
   predictors are a second, separately registered batch with their own
   denominator and their own (future) confirm registration — no mixing of
   deflation accounting in either direction. Murat's stated intent: keep
   the 179's potential fully intact AND gain the external bank.

Sizing S3 freezes jointly per §5. No parameter below may change after this
banner without a new trial ID.

Drafted 2026-08-07/08 from: Amendment 3 (F1-F6), review round 3 (Opus repo
review), review round 4 (GPT challenge response), REAL-NULL-1 (K=4000),
RECAL-1 run-2 final verdict.

---

## 0. What this registers

The error-control design, veto, cap semantics, sizing, terminal states, and
repair jurisdiction for the ONE-SHOT replay of the 179 banked candidates under
the ratified ladder. The ladder itself (BRAIN-009 vs BRAIN-010 — recommendation
on record: BRAIN-010) is Murat's separate attended call and is a parameter
here, not a subject of this registration.

## 1. Batch-level error control (fixes Amendment 3 F1)

Two candidate designs, both evaluable on the EXISTING bank (1250 null reps ×
segments) + REAL-NULL-1 machinery. No new grid nights required for this choice.

- **D1 — BH step-up on empirical p-values.** Each candidate's explore t_ic is
  converted to an empirical p-value against the measured null CDF of its
  assigned family (per §3's veto index), floored by the REAL-NULL-1
  persistent-arm CDF (the real-data floor: p95 ≈ 1.75-1.88, i.e. t_ic 1.5 is
  ≈ p 0.082 for persistent candidates, not p 0.036). BH at a pre-registered q
  across the full 179-candidate batch.
- **D2 — e-BH challenger (Wang-Ramdas 2022, JRSS-B 84(3)).** Monthly bounded
  scores under a conditional-randomization null → e-processes → e-BH, valid
  under arbitrary dependence.

**Selection rule (GPT §2.1, adopted):** D2 replaces D1 only if, on identical
CRN cells: FDR upper bound no higher, mean power ≥ +5pp, no registered
injection cell worse by > 2pp, ≤ half the compute. Otherwise D1 ships.
Evaluation uses the even/odd rep discipline (select on even, validate on odd).

## 2. Cap semantics (fixes F2)

The top-N cap is defined GLOBAL across the whole 179-candidate replay batch
(not per-family, not per-sub-batch), applied ONCE after the error-control step,
exactly as `ruleset.evaluate()` orders it. Its expected behavior in the real
geometry (~21-22 of ~67-70 largemid clearing 1.5; cap binding ~4:1) is measured
and printed, not assumed from the calibration geometry where it never bound
(E[qualifiers] 4.54 vs 5).

## 3. Veto index (fixes F3)

The family veto is CORRELATION-INDEXED, not lineage-indexed. Ship gate: the
pre-registered correlation-surface diagnostic on the 21 banked signals must
show R² ≥ 0.7 of family-null p95 on the correlation feature(s); otherwise the
veto reverts to a flat real-data floor for all candidates.

**Threshold rule (GPT §1.3, adopted):** each candidate's bar is
max(semantic-family p95, empirical-neighbor p95), where the empirical neighbor
is assigned by the frozen correlation surface BEFORE any confirm result is
seen. The frozen semantic ontology (`TRIALS/family_ontology.json`) is not
edited by this rule.

## 4. Expected-false-adoption accounting (fixes F4, F5)

Printed at the TOP of the replay output, before any candidate result:

- explore false-pass basis: REAL-NULL-1 persistent-arm 0.082 [0.0735, 0.0905]
  (NOT the simulator 0.036);
- confirm pass-given-graduation basis: REAL-NULL-1 118/328 = 0.360 (NOT the
  simulator 2-of-4);
- the implied E[false adoptions] and P(≥1) for the realized qualifier count
  under the chosen design, both columns (simulator-basis and real-basis),
  disagreement shown, per Handoff §7.

## 5. Joint ladder + sizing (fixes F6)

The ratified ladder and the S3 sizing bands (as re-confirmed by wave 3:
never-confirm 0× / weak-confirm 0× / confirm t_ic ≥ 1.5 → 0.75×) freeze as ONE
rule. No post-hoc sizing adjustment after any replay output is seen.

## 6. Terminal states and repair jurisdiction (round-4 adoptions)

- Terminal states: ADOPT / DEAD / ABORTED / **SUPPORT-INADEQUATE** (confirm
  window contains fewer than the pre-registered floor of independent episodes
  or effective cross-sectional clusters for episodic candidates).
- **Any repair after confirm reveal creates a NEW trial ID and resets the
  one-shot clock for that candidate.** No in-place rerun, however defensible
  the defect.
- Frozen before confirm opens: source snapshot + row-count hashes; dependency
  hash; per-candidate eligibility and polarity; missingness/ties/winsorization/
  stale-value rules; the exact abort-vs-score state machine; benchmark and
  cost fallback rules.

## 7. What is NOT in scope

- The 209 OSAP external predictors. They are candidate-eligible with confirm
  windows unread, but entering them moves the count off 179 and changes every
  deflation denominator — separate attended decision, separate registration.
- Any change to the frozen explore records of the 179.
- Small-segment candidate rows: still unexamined until the replay itself runs.

## 8. Attended decision points (Murat), in order

1. Ratify the ladder: BRAIN-009 vs **BRAIN-010 (recommended)** vs
   1.25/0.5-sensitivity (would need its own blind registration).
2. Approve the D1-vs-D2 selection rule and the BH q (proposed: q = 0.10).
3. Approve the episode floor for SUPPORT-INADEQUATE (proposed: ≥ 3 independent
   episodes).
4. Freeze this file.

Then, and only then: run the R² diagnostic → freeze the veto surface → one-shot
replay.
