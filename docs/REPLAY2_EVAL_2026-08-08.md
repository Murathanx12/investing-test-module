# REPLAY-2 build — Phase-1 measurements (2026-08-08)

Both pre-registered diagnostics of the frozen `TRIALS/PREREG_REPLAY_2.md`
ran today. Raw outputs: `runs/REPLAY-2/` (gitignored); tracked copies of the
key numbers below.

## 1. Veto index: the correlation surface FAILED its ship gate → flat floor

`aegis_brain.calibration.veto_surface`, 40 (signal, segment) points, null
p95 from n=1250 bank reps, correlations on the real panel over the explore
window:

| scope | R² (|ρ| vol) | R² (vol + price) | gate |
|---|---|---|---|
| largemid | 0.140 | 0.141 | FAIL (< 0.7) |
| small | 0.163 | 0.206 | FAIL |

Why it fails: null p95 is not a monotone function of σ-correlation —
`high_52wk_prox` (ρ_vol 0.32) has p95 3.15 while `amihud_3m` (ρ_vol 0.49)
has p95 **−3.24** in small; directional null biases (negative means for
illiquidity/drawdown constructions) break any correlation-indexed surface.
**Consequence (pre-registered fallback): every candidate in the replay gets
the FLAT real-data floor** — empirical p-values against the REAL-NULL-2
persistent-arm CDF of its own segment. The max(semantic, empirical-neighbor)
refinement is moot; the frozen semantic ontology stays as documentation only.

## 2. D1 (BH q=0.10 on empirical p-values) vs fixed-threshold BRAIN-010

`aegis_brain.calibration.replay2_eval`, null CDFs built on one rep half,
rates read on the other, both directions (values below: cdf-even/eval-odd,
then cdf-odd/eval-even):

| cell | D1 adopt | B10 adopt | D1 E[null qualifiers] | B10 E[null qualifiers] |
|---|---|---|---|---|
| a0.0/base (n=625/half) | 0.000 / 0.002 | 0.029 / 0.027 | **0.16 / 0.10** | **9.03 / 8.96** |
| a0.2/I1 | 0.008 / 0.024 | 0.160 | 0.22 / 0.04 | 9.3 |
| a0.4/I1 | 0.088 / 0.184 | 0.440 / 0.424 | — | — |
| a0.6/I1 | 0.424 / 0.448 | 0.816 / 0.752 | — | — |
| a0.4/I3 | 0.072 / 0.024 | 0.424 | — | — |
| a0.4/I4 | 0.088 / 0.168 | 0.528 / 0.560 | — | — |

Reading, stated plainly:

- **D1 does what batch error control is for**: expected false qualifiers per
  batch collapse from ~9 to ~0.1-0.4, and the injected-candidate FPR to
  ~0-0.2%. Under the fixed threshold at replay scale, E[false adoptions] ≈
  2-3 with P(≥1) ≈ 0.9 (Amendment 3); under D1 that batch risk essentially
  vanishes.
- **The power cost is severe in this geometry**: at α=0.4, adoption falls
  from ~42-53% to ~9-18%. The sim batch holds ONE true effect among 42
  candidates, so BH sits at its Bonferroni corner (bar ≈ q/m). This is the
  worst case for BH by construction: **the step-up loosens as the number of
  true effects grows**, which the single-injection design cannot show. At
  the real replay (179 candidates), if several candidates are real, the
  realized bar is milder; if none are, the strict bar is exactly what we
  want. Stated before the replay, as a property of the procedure, not a
  post-hoc argument.
- Half-asymmetry at I3 (0.072 vs 0.024) is n=125 noise; intervals overlap.
- q stays 0.10 as frozen. No re-tuning after seeing these numbers.

## 3. D2 (e-BH): NOT EVALUABLE on the bank — D1 ships

The bank stores summary statistics only (no monthly IC series). Building
e-processes requires re-scanning, i.e. grid nights, which violates the
frozen "≤ half the compute" clause. Per PREREG_REPLAY_2 §1, D1 ships.
Recorded here rather than silently.

## 4. REAL-NULL-2 (pre-registered, launched 2026-08-08)

`TRIALS/PREREG_REAL_NULL_2.md` + `scripts/real_null_2.py`. Both segments,
K=5000 × φ ∈ {0.97, 0.99, 0.995, 0.999}, seed 20260808, raw samples saved —
the replay's flat-floor CDFs. Guard reproduced banked numbers exactly at
smoke and launch. Declared prior: small-segment P(t_ic ≥ 1.5) > largemid's
0.082, point guess 0.10-0.16; largemid must replicate 0.082 within
[0.06, 0.11] or the run is VOID pending diagnosis.

## What remains before the one-shot replay

1. REAL-NULL-2 lands → floor CDFs frozen.
2. The replay runner itself (blind build: reads `data/factory/
   batch*_summary.csv` only when fired; prints the §4 accounting table
   first; S3 sizing attached; terminal states incl. SUPPORT-INADEQUATE).
3. Fire. One shot, both accounting columns (sim-basis and real-basis).
