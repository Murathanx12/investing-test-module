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

## Result (filled AFTER the run 2026-07-25 — never edited)
`data/factory/macro_batch4.json`, explore window 2004-01..2018-12 (3,775 d).

### 1. INSTR-REGIME-JM — ALL THREE BARS PASS → confirm candidate
| | CAGR | vol | Sharpe | maxDD | switches/yr | %risk-off | t vs SPY (mo) |
|---|---|---|---|---|---|---|---|
| JM λ=50 (primary) | **11.2%** | 14.5% | **0.80** | **−26.6%** | **0.4** | 13.8% | 0.94 |
| JM λ=10 | 10.9% | 14.5% | 0.78 | −24.4% | 0.9 | 11.6% | 0.89 |
| JM λ=100 | 11.1% | 14.6% | 0.79 | −26.6% | 0.3 | 12.5% | 0.94 |
| SPY B&H | 7.7% | 18.3% | 0.50 | −55.2% | — | — | — |
| 60/40 | 8.0% | 10.1% | 0.81 | −29.9% | — | — | — |

Bars: CAGR ≥ SPY−1pp ✓ (+3.5pp), maxDD ≤ ⅔×SPY ✓ (26.6 ≤ 36.8), ≤12
switches/yr ✓ (0.4). λ-insensitive (all three settings pass — not a
parameter fluke). **Both hands:** t vs SPY only 0.94 (not significant); the
CAGR edge is concentrated in dodging ONE event (2008); worst month −13.1%
(a crash caught while risk-on); 60/40 matches the Sharpe with less vol.
The tradeable claim is crash-avoidance-without-return-sacrifice, and 2008
is a single observation — which is exactly what the held-out confirm
window (COVID 2020 + the 2022 stock-AND-bond crash, TLT's failure mode)
will interrogate.

### 2. INSTR-TSMOM-XA — bars pass BY THE LETTER; return drag disclosed
Standalone net: CAGR 2.7%, Sharpe 0.46 (bar ≥0.3 ✓), maxDD −12.1%,
calendar-2008 **+4.9%** ✓ (crisis alpha real in-window), corr w/ SPY 0.17.
Overlay 50/50: maxDD −28.9% ≤ 0.75×SPY ✓ — but CAGR 5.6% vs SPY 7.7%,
**t vs SPY −1.51**: the overlay is drawdown insurance PAID FOR in return.
Also disclosed: per-asset 10%-vol sizing ÷ 4 assets leaves portfolio vol at
6% — under-deployed vs portfolio-level vol targeting; a v2 sizing variant
would be a NEW registration, not a retune.

### 3. INSTR-SBCORR (descriptive) — the panel's gate claim REFUTED in-window
Corr>0 on 14.4% of explore days. SPY fwd-21d: +0.49% (corr+) vs +0.76%
(corr−) — mild. **Dip-conditional (the "master switch" claim): dips with
corr POSITIVE bounced +2.89% (n=50) vs +0.63% with corr negative (n=705) —
the OPPOSITE of "disable dip-buying when correlation flips positive."**
GLD after positive flips: −0.34% (n=17) — no gold-hedge signal. Caveats:
n=50 is thin and 2004-2018 contains no 2022-style inflation regime — the
claim's home turf is in the held-out window; the descriptive receipt stands
for this window only.

### 4. INSTR-GPR-EVENT (descriptive) — GPR spikes are not a sell signal
53 events (93 clustered drops disclosed), 2002-06..2018-11. SPY CAR(0,+30):
**+0.61%, 64% positive** — mild post-spike drift UP (threat-premium fade),
not a crash precursor. USO excess −2.47% (oil FADES after spikes — against
the rally intuition), ITA excess +0.91% (defense mildly positive, n=50).
Routes to the narrative/brain layer as calibrated context, never to a lane.

## CONFIRM pre-registration (frozen 2026-07-25 BEFORE touching 2019+)

Earned by the explore bars above; BRAIN-010 precedent (register → run same
day, byte-identical spec, zero tuning channel). ONE run each on held-out
2019-01..2024-12; runner `scripts/run_macro_confirm.py`.

- **INSTR-REGIME-JM-CONFIRM:** λ=50 ONLY (primary frozen; sensitivities
  are not re-read). Monthly expanding refits continue through 2024 (causal,
  full history from 2002). **PASS iff** net CAGR ≥ SPY(2019-24) − 1pp AND
  maxDD ≤ ⅔ × SPY maxDD AND ≤12 switches/yr. PASS → forward paper-lane
  candidate (attended seed-a-lane, Murat's flag — never auto). REJECT
  closes the instrument (receipt: TLT-failure-mode 2022 is inside).
- **INSTR-TSMOM-XA-CONFIRM:** identical spec. **PASS iff** standalone net
  Sharpe ≥ 0.3 AND calendar-2020 > 0 AND overlay maxDD ≤ 0.75 × SPY maxDD.
- Results final; reruns forbidden; variants are new registrations.

## Confirm result (one run 2026-07-25 — never edited)
`data/factory/macro_confirm.json`, held-out 2019-01..2024-12 (1,510 d).
SPY benchmark: CAGR 17.1%, maxDD −33.7%, Sharpe 0.90.

### INSTR-REGIME-JM λ=50 — **REJECT** (frozen bars: both return AND DD missed)
CAGR 14.0% (bar ≥16.1% ✗), maxDD −27.6% (bar ≤−22.5% ✗), 1.0 switches/yr ✓,
t vs SPY −0.98. The disclosed failure modes BOTH materialized: calendar-2022
**−21.6%** (risk-off into TLT during the dual stock-bond crash — the safe
asset wasn't) and calendar-2020 +4.8% vs SPY +18% (dodged the crash, missed
the rebound). Sharpe 0.83 vs 0.90 — respectable, but the registered claim
was crash-avoidance WITHOUT return sacrifice, and out-of-window it
sacrificed both bars. **The instrument CLOSES.** Second live-fire wall
validation (first on an allocation instrument): explore showed all-bars-pass
on the strength of one crisis (2008); the next two crises broke the spec.
Any successor (e.g. multi-asset risk-off basket instead of TLT-only, VIX
feature) is a NEW registration with this receipt as its prior.

### INSTR-TSMOM-XA — **PASS** (first macro instrument to survive the wall)
Standalone: Sharpe 0.47 ✓ (bar 0.3), calendar-2020 **+9.2%** ✓ (crisis
alpha REPLICATED in a second, unseen crisis; calendar-2022 −0.9% — flat
through the dual crash), maxDD −8.5%. Overlay: maxDD −18.8% ✓ (bar ≤−25.3%),
Sharpe 0.96 vs SPY 0.90, worst month −5.6% vs −12.5%.
**Both hands:** overlay CAGR 10.2% vs SPY 17.1% (t −1.86) — the return drag
is real and priced. This is a DEFENSIVE DIVERSIFIER receipt (Goal B:
sequence-risk/drawdown protection), NOT a beat-SPY claim. Consistent across
both windows now: 2008 +4.9%, 2020 +9.2%, 2022 ≈flat, positive standalone
Sharpe in both. Next step per house law: forward paper-lane candidacy
(attended seed-a-lane — Murat's flag, never auto), lane framed as
"defensive overlay vs 60/40 control", 24-month clock before any claim.
