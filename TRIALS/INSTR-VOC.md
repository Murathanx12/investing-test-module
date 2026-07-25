# INSTR-VOC — falsification test of "virtue of complexity" on our data

**Registered:** 2026-07-26 (UTC), BEFORE the run. **Class:** instrument
(methodology receipt). ONE run, results final. Prior-check: 0 hits.

## Question
Kelly-Malamud-Zhou (JF 2024) claim market-timing Sharpe increases
monotonically in model complexity (random-feature ridge with P >> T,
"benign overfitting"). Three independent critiques (Nagel 2025; Buncic
2025; Cartea-Shi 2025) attribute the result to (a) a mechanical
volatility-timed momentum artifact and (b) benchmark-handicapping. If the
critics are right, complexity methods deserve ZERO factory attention; if
KMZ are right on our data, a complexity instrument class opens. Either way
the receipt is valuable.

## Frozen spec
- Market: EW CRSP monthly, delisting-adjusted, 1963-2024 (spliced
  msf_ext + msf; EW because no shrout pre-2002 on disk — disclosed).
- Features: 12 monthly lags, standardized per training window. RFF
  (sin/cos, ω ~ N(0, γ²I), γ=2, drawn ONCE seed 0). P ∈ {12 raw, 100,
  1000, 6000}. Ridge z = 1e-3 (dual/kernel solve). Rolling T=120 training.
- Positions: forecast / trailing 12m variance, normalized by trailing
  |position| mean (60m), capped [−1, 2]; identical pipeline for ALL
  strategies and the twin (no benchmark handicapping — the Buncic fix).
- **Benchmarks:** B&H; sign-TSMOM(12); vol-managed (Moreira-Muir); and the
  **Nagel mechanical twin** — linearly-declining weights on the last 12
  returns through the SAME position pipeline.
- Reads: pre-window 1974-2003 (outside both walls — declared readable),
  explore 2004-2018. **Confirm 2019-2024 sealed** unless the explore
  reading supports the claim.
- **Pre-committed reading:** "SUPPORTED" iff highest-P explore Sharpe >
  ALL benchmarks (incl. twin) AND Sharpe monotone-increasing in P AND
  corr(highest-P strategy, twin) < 0.9. Anything else = the claim fails on
  our data; the complexity class stays out of the factory.

## Result (filled AFTER the run — never edited)
_pending_
