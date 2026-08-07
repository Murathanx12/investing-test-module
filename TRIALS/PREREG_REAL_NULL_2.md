# PRE-REGISTRATION — REAL-NULL-2 (2026-08-08)

**Written BEFORE the run. Registered under CANON §6.** Successor to
REAL-NULL-1 (external review round, verified). This is measurement
infrastructure for the FROZEN REPLAY-2 registration, not a hypothesis test:
its output is the flat real-data null CDF that REPLAY-2 §3 mandates after the
correlation-surface gate FAILED (R² 0.14-0.21 vs the 0.7 bar,
`runs/REPLAY-2/veto_surface.json`, 2026-08-08).

## What is measured

Explore-window t_ic and confirm-window t_ic of provably information-free
persistent AR(1) signals (RNG independent of every panel input) on the REAL
CRSP panel, **both segments** (largemid = dollar-vol rank <= 1000; small =
1001-3000), replicating `explore.scan_signal`'s IC leg exactly (REAL-NULL-1
harness, verified against banked numbers).

## Frozen design (no knob may move after this file commits)

- Segments: largemid AND small (REAL-NULL-1 was largemid-only).
- phi grid: {0.97, 0.99, 0.995, 0.999} — the persistent arms only. REAL-NULL-1
  established real candidates are MORE persistent than any arm tested, so the
  pooled persistent CDF is a conservative (narrow-side) floor.
- K = 5000 draws per phi per segment -> pooled 20,000 samples per segment.
  p-value resolution 1/20001 = 5e-5, sufficient for BH at q/m = 0.10/179 = 5.6e-4.
- Seed: 20260808. Explore 2004-01..2018-12; confirm 2019-01..2024-12.
- **Raw samples saved** (`runs/REPLAY-2/real_null_2_{segment}.npz`: per-phi
  explore t_ic and confirm t_ic arrays). REAL-NULL-1 saved only summaries;
  the replay needs the CDF itself.

## What the output becomes (per the frozen REPLAY-2)

1. The pooled persistent-arm explore t_ic CDF per segment = the FLAT FLOOR
   for every candidate's empirical p-value in the one-shot replay (§3
   fallback branch, now the active branch).
2. The confirm-given-graduation pass rate per segment = the real-data basis
   of the expected-false-adoption accounting (§4).

## Guard (must pass before any number is read)

The harness must reproduce the banked largemid batch-1 numbers exactly:
vol_12m_low t_ic = 1.89, price_level t_ic = 2.12. **Limitation, stated:** no
small-segment guard is possible without reading small-segment candidate rows,
which stay unexamined until the replay (standing rule). The assurance for the
small segment is code identity — the segment mask is the only difference, and
it replicates `explore.segment_mask` verbatim.

## Declared prior (scored afterwards)

- Small-segment persistent-null P(t_ic >= 1.5) EXCEEDS largemid's 0.082 —
  the family-null tables show every sigma-family width larger in small
  (e.g. vol_12m_low p95 4.19 vs 2.97), and REAL-NULL-1's mechanism
  (heteroskedastic IC cross-section) is stronger in small caps. Point guess:
  0.10-0.16.
- Largemid reproduces REAL-NULL-1 within Monte-Carlo error (0.082 ± 0.01) —
  if it does not, one of the two harnesses is wrong and the run is VOID
  pending diagnosis.

## Kill / VOID conditions

- Guard mismatch -> VOID, no number reported.
- Largemid pooled P(t_ic >= 1.5) outside [0.06, 0.11] (REAL-NULL-1
  replication band) -> VOID pending diagnosis, not silently accepted.
