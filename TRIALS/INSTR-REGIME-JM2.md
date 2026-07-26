# INSTR-REGIME-JM2 — inflation-gated jump-model rotation (frozen BEFORE run)

**Registered:** 2026-07-26 (UTC). **Class:** allocation instrument, ONE
execution covering BOTH windows, results final. Runner `scripts/run_jm2.py`;
harness `aegis_brain/macro/daily_harness.py` + `aegis_brain/macro/
jump_model.py` (both REUSED byte-identical — the state machine is inherited,
not retested). Prior-check transcript: 104 hits reviewed 2026-07-26; all
hits are the JM1 receipt (which sanctions a successor as a NEW registration)
and the round-6/round-10 queue entries. No closed-family collision.

## ⚠️ POST-HOC-REPAIR PROVENANCE (mandatory declaration, panel round 6)

This design exists because 2022 killed JM1. INSTR-REGIME-JM
(TRIALS/INSTR-MACRO-BATCH4.md) passed all explore bars and was REJECTED at
confirm when its single safe asset (TLT) crashed alongside stocks in the
2022 inflation regime. JM2's inflation gate was reverse-engineered from
that observed failure. Therefore:

- **Explore 2004-2018 carries ~ZERO evidential weight.** The window
  contains no 2022-style inflation regime, and the designer has seen the
  full history. Explore is reported as descriptive context only.
- **Confirm 2019-2024 is WEAKENED evidence, not clean.** The event that
  motivated the repair (2022) sits INSIDE the confirm window. A confirm
  pass is necessary-but-weak: it shows the repair fixes the crash it was
  built to fix, which is close to circular. It cannot show the repair
  generalizes.
- **The only clean test is FORWARD.** A confirm pass earns forward
  paper-lane *candidacy* only (attended seed-a-lane, Murat's flag, 24-month
  clock), with this provenance block copied into the lane doc.

Both windows run in a single one-shot execution (explore cannot "earn"
confirm here because explore has no evidential weight — pre-declared to
close the opportunism channel). Results final; reruns forbidden; variants
are new registrations.

## Spec (frozen)

**State machine — inherited from JM1 unchanged:** 2-state statistical jump
model on SPY features (EWMA hl=10 daily return; EWMA hl=21 vol; EWMA hl=21
downside deviation; expanding standardization). Centroids + standardization
refit each month-end on data through that month-end; days of month m use
the m−1 refit; daily state = causal forward-filtered argmin. λ = 50 ONLY
(JM1's primary; sensitivities not re-run — the state machine is not the
hypothesis here, the gate is). Signal at close t → position at close t+1.
Costs 5 bps one-way on traded value.

**Inflation gate (the new element, frozen):** breakevens are rising iff
T10YIE(t) − T10YIE(t−126 trading days) > +0.10 percentage points, T10YIE
forward-filled ≤5 days. Threshold chosen a priori as economically
meaningful repricing (≈ one sd of 6-month breakeven changes), not tuned —
no other thresholds will be read as primary. Gate sensitivities {63d,
252d} at the same +0.10pp are computed and reported as diagnostics, never
re-picked (JM1 λ-sensitivity pattern).

**Allocation:**
- risk-on state → 100% SPY (unchanged from JM1);
- risk-off state, gate OFF (disinflationary/neutral) → 100% TLT (JM1's
  arm — correct in 2008/2020-type deflationary crashes);
- risk-off state, gate ON (inflationary) → 100% GLD; if GLD has <252d of
  history at t (pre-2005-11) → 100% cash at 0% return (no T-bill series on
  disk; conservative, understates JM2; disclosed).

**Data:** on-disk `data/macro/etf_daily_close.parquet` (SPY/TLT/GLD) +
NEW fetch: FRED T10YIE daily (starts 2003-01, fits the window; keyless
fredgraph.csv; snapshot stored `data/macro/fred_t10yie_snap20260726.csv`).
Registered BEFORE the fetch.

**Benchmarks:** SPY B&H, 60/40, and JM1 (λ=50, TLT-only — the ablation:
does the gate add anything beyond the state machine?).

## Pre-committed reading (frozen)

Bars identical to JM1, evaluated on CONFIRM 2019-2024 only:
net CAGR ≥ SPY(2019-24) CAGR − 1pp AND maxDD ≤ ⅔ × SPY maxDD AND ≤12
switches/yr (state switches; gate flips inside risk-off count as trades,
reported separately).

- **PASS →** forward paper-lane candidate (attended; provenance block
  travels with it). NOT a promotion — nothing here is promotable without
  a forward record.
- **Any bar missed → instrument CLOSES.** Family verdict: single-trigger
  regime rotation (JM state machine + one macro gate) is closed; further
  successors require genuinely new information (new data class, not
  another repair of the same machine) and inherit both receipts.
- Also reported, both hands, no gates: calendar-2020 and calendar-2022
  returns (did the gate actually route 2022 risk-off out of TLT?),
  explore-window gate activity (how often the gate fires when it can't
  matter), t vs SPY and vs JM1 monthly.

**Prior: WEAK-MEDIUM.** Gold's inflation-crisis hedge record is mixed
(2022 GLD was ≈flat — the gate's best case is damage *reduction*, not a
2022 win); the honest expectation is that JM2 beats JM1 in 2022 but may
still miss the CAGR bar (2020 rebound-miss was the OTHER JM1 failure and
the gate does nothing about it).

## Result (filled AFTER the run 2026-07-26 — never edited above this line)

`data/factory/jm2.json`, one execution, both windows. 252 causal refits.

### VERDICT: **REJECT — instrument CLOSES; single-trigger regime-rotation family CLOSED**

Confirm 2019-2024 (the only gate): CAGR **13.4%** (bar ≥16.1% ✗), maxDD
**−29.8%** (bar ≤−22.5% ✗), switches 1.0/yr ✓. Two of three frozen bars
missed.

### The finding that matters: the repair made its own target crash WORSE

| confirm 2019-24 | CAGR | Sharpe | maxDD | cal-2020 | cal-2022 | t vs SPY |
|---|---|---|---|---|---|---|
| JM2 (gated) | 13.4% | 0.81 | −29.8% | +4.8% | **−23.9%** | −1.13 |
| JM1 ablation (TLT-only) | 14.0% | 0.83 | −27.6% | — | −21.6% | −0.98 |
| SPY B&H | 17.1% | 0.90 | −33.7% | +18% | — | — |

t(JM2 vs JM1) = **−1.18**: the inflation gate is a net negative out of
window. Mechanism: **2022's bond crash was real-rate-driven — T10YIE
peaked in April 2022 and FELL through the worst of the TLT collapse** —
so a breakeven-momentum gate switched risk-off capital back INTO TLT
precisely when the repair was supposed to route it out (only 9.5% of
confirm risk-off days were gated to GLD/cash; gate flipped 3× while
risk-off). The post-hoc repair failed to fix the exact crash it was
reverse-engineered from. 2020's rebound-miss (+4.8% vs SPY +18%) was
untouched, as predicted in the prior.

### Explore (declared ~zero weight — and the declaration was earned)

Explore 2004-2018 FLATTERED the repair: CAGR 12.2% vs SPY 7.7%, maxDD
−20.4% (JM1: −26.6%), calendar-2008 **+32.4%**, t vs JM1 +0.83 — GLD
rallied through the 2008-2011 inflation-scare windows and made the gate
look like a pure upgrade. Had explore carried weight, JM2 graduates.
Confirm inverted it. This is the cleanest live receipt yet for the
post-hoc-provenance rule: an explore pass on a repaired design measured
exactly nothing.

### Diagnostics (frozen, never re-picked): lb=63 confirm CAGR 15.0%/maxDD
−27.6% (still misses both bars), lb=252 12.9%/−31.7% (worse). No lookback
rescues the design — the failure is the gate's information, not its speed.

### Closure terms

Single-trigger regime rotation (JM state machine + one macro gate) is
CLOSED with two receipts (JM1: safe asset crashed; JM2: gate mistimed the
same crash). Any successor needs a genuinely different information class
(e.g. the ANALOG belief engine's multi-feature state estimate) and starts
as a NEW walled registration inheriting both receipts. NEG_RESULTS §18.
