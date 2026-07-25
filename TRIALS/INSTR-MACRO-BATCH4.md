# INSTR-MACRO-BATCH4 — daily allocation-layer instruments (frozen BEFORE run)

**Registered:** 2026-07-25 (UTC). **Class:** 2 explore instruments + 2
descriptive instruments, ONE run each, results final. Explore window
2004-01..2018-12; **confirm 2019-2024 HELD OUT** exactly like the factory —
readable only by a future pre-registered confirm run. Data: on-disk ETF
daily closes (auto-adjusted = total-return proxy, disclosed) + GPR daily
snapshot (2026-07-24 vintage; revision caveat disclosed at round-2 panel).
Costs 5 bps one-way on traded value (liquid ETFs). Harness:
`aegis_brain/macro/daily_harness.py`; runner `scripts/run_macro_batch4.py`.

## 1. INSTR-REGIME-JM (supersedes INSTR-REGIME-HMM per round-4 amendment)

2-state statistical jump model (Bemporad/Nystrup lineage; Shu-Yu-Mulvey JAM
2024 application — verified round 4), NOT hmmlearn.

- **Features (SPY only):** EWMA(hl=10) daily return; EWMA(hl=21) vol;
  EWMA(hl=21) downside deviation. Standardized with expanding stats.
- **Causality (frozen):** centroids + standardization stats refit at each
  month-end on data through THAT month-end; days of month m use the m−1
  refit; daily state = FORWARD-filtered argmin (no backward pass — the
  filter at t sees only ≤t). Signal at close t → position at close t+1.
- **Jump penalty:** λ = 50 PRIMARY (frozen); λ ∈ {10, 100} reported as
  sensitivity diagnostics, never re-picked after results.
- **Allocation:** risk-on → 100% SPY; risk-off (higher-vol centroid) → 100%
  TLT. Benchmarks: SPY B&H, 60/40.
- **Pre-committed reading:** candidate for a future confirm registration
  IFF (net CAGR ≥ SPY B&H CAGR − 1pp) AND (maxDD ≤ ⅔ × SPY maxDD) AND
  (switches ≤ 12/yr). Anything else → instrument CLOSES with receipt.
  Prior: MEDIUM (regime timing is fragile; the JM's persistence penalty is
  the specific device claimed to fix it).

## 2. INSTR-TSMOM-XA

12-1 time-series momentum, cross-asset (SPY/TLT/GLD/USO; assets enter as
252d history exists — GLD 2005-11, USO 2007-04; disclosed staggering).

- Month-end signal: sign of return t−252→t−21. Position = sign ×
  min(0.10/σ_ann60, 1.5), EW across active assets, held one month, traded
  next day, 5 bps.
- Report: standalone net stats, corr w/ SPY, calendar-2008 return (the
  crisis-alpha claim), 50/50 overlay with SPY vs SPY B&H.
- **Pre-committed reading:** overlay candidate for confirm IFF standalone
  net Sharpe ≥ 0.3 AND calendar-2008 > 0 AND overlay maxDD ≤ 0.75 × SPY
  maxDD. Prior: STRONG (century-scale evidence, Moskowitz-Ooi-Pedersen,
  "two centuries" lit) — which is exactly why the reading is pre-committed.

## 3. INSTR-SBCORR (descriptive — never arms)

60d rolling SPY/TLT return correlation. Report (explore window, forward
windows truncated to stay ≤2018-12): % days positive; SPY fwd-21d mean by
corr sign; **dip-conditional** (SPY ≥5% below 63d high) fwd-21d by corr
sign — the "dip-buying is only safe when correlation is negative" gate
claim; GLD fwd-21d after corr flips positive. Ns disclosed.

## 4. INSTR-GPR-EVENT (descriptive — never arms)

GPR daily spikes: GPRD > trailing-756d mean + 2σ AND 30d local max;
clustered events within 30d dropped (count reported). Events 2002-06..
2018-11 (CAR window stays inside explore). CAR(0,+30 trading days): SPY
raw; USO and ITA excess-of-SPY (from their inceptions). Mean, hit rate, N.

## Result (filled AFTER the run — never edited)
_pending_
