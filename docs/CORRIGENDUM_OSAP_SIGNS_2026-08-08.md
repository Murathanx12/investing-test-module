# CORRIGENDUM — OSAP double-sign defect (caught by INSTR-ERA-BACKTEST-1 P4)

The OSAP wide download (`signed_predictors_dl_wide`) ships columns
PRE-SIGNED (higher value = higher predicted return). The adapter
(`aegis_brain/factory/osap.py`, from the 2026-08-07 external-anchor
session) applied the documentation Sign field AGAIN, double-flipping all
96 scanned sign=−1 signals. Proof: osap_MaxRet small 2004-2018 t_ic
**−7.74** vs the internal same-construction replay adoption
max_dret_low_D **+7.71** (and IdioVol3F −7.45 vs ivol_low_D +6.93 — exact
mirror magnitudes). The adapter is fixed (direction always +1; doc Sign
kept as provenance). The era instrument's registered P4 prediction MISSED
solely because of this defect — the instrument chain caught the bug, which
is what it exists for.

## Blast radius, adjudicated

| artifact | status |
|---|---|
| THE REPLAY (Stage A/B, 10 adoptions) | **UNAFFECTED** — internal signals only |
| REAL-NULL-2 floors, family ontology, book trial | UNAFFECTED |
| PROF-SMALL-1, EXT-CONFIRM-1 (GP/OperProfRD) | UNAFFECTED — all-(+1) cohorts |
| EXT-POWER-1 M4 | **CORRECTED** (IC sign flip is exact for the anti-book): largemid 30/196=15.3% → **52/196 = 26.5% [20.8, 33.1]** (prior 30-50%: now grazes the band — the miss shrinks to marginal); small 91/196 → **98/196 = 50.0%** |
| EXT-COMPOSITE-1 EW-209 arm | **VOID BY DEFECT** — the composite mixed 113 correct and 96 inverted columns; its KILLED verdict is unadjudicated. Corrected rerun = NEW registration (partial-peek asterisk: corrupted result was seen) |
| EXT-EXCLUDE-1 | **VOID BY DEFECT** — the avoid-composite ranked pre-signed columns with raw-characteristic orientations, so the screen excluded partly the WRONG tail. KILLED verdict unadjudicated; corrected rerun = NEW registration |
| INSTR-ERA-BACKTEST-1 | −1 rows corrected by exact IC flip: P4 re-scored **HIT** (MaxRet +7.27, IdioVol3F +6.53, vol_12m_low 5.40, price_level 5.90 — all ≥ 3); as-run P4 stays MISS-by-instrument-defect in the record. Money legs of −1 signals need rescans (t_net not sign-symmetric) — not needed for any current decision |

## Era instrument headline (unaffected +1 signals, 1985-2001 small, out of BOTH one-shot windows)

P1 HIT: GP gross t 3.23, OperProfRD 3.01, **CBOperProf 5.23 (net t 4.30
even at flat-25)**. P2 HIT: family IC ≥ 3.6 in every sub-split, all seven
members. P3 (decay direction): era gross > modern explore gross for the
GP class — consistent with post-publication decay. The profitability
family's small-cap edge is three-decade real; what 72-month windows
cannot prove, 17-year windows can.

## Meta-lesson (ledger-grade)

A guard on a +1 signal cannot catch a sign-convention bug. The catch came
from REDUNDANCY: internal and external implementations of the same
construction running in the same window. Standing rule adopted: any
external data adapter must include at least one sign=−1 (or
direction-sensitive) reconciliation against an internal implementation
before its scans are believed.
