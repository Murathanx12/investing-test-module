# TRIAL-BRAIN-004-pead-sue

**Registered:** 2026-07-21 (UTC) — BEFORE any SUE is computed or joined to a return.
**Registry row:** `TRIALS/registry.jsonl` (cumulative n → 19)
**Grade:** paper-grade backtest (CRSP returns). Prior-setting; deploy gate separate.

## Hypothesis
On CRSP 2006→2024, a long-only portfolio of stocks in the top SUE (standardized
unexpected earnings) quintile, entered the day AFTER the earnings-announcement date
(`rdq`) and held ~3 months with a hold-band, earns positive net-of-cost drift vs a
cap-segment-matched EW benchmark. Mechanism: investor underreaction to earnings news
(Bernard-Thomas); post-2006 the drift is concentrated in small/low-attention names
(Martineau "Rest in Peace PEAD"), so honest prior is **marginal net of costs**.

## Literature prior
PEAD ~5%/quarter top-decile spread in 1980s-90s; largely gone for liquid names since
~2006 (announcement-day repricing). Surviving drift is microcap/low-coverage. Prior:
**~40/60 against** any segment clearing net t>1; if anything survives, expect micro.

## Signal (frozen)
- **SUE (two flavours, both reported):**
  (a) *Analyst-based* — (IBES actual EPS − last pre-`rdq` consensus mean) / price, using
      UNADJUSTED IBES to avoid split-adjustment look-ahead.
  (b) *Time-series (Foster)* — (epspxq − epspxq four quarters prior) / σ(trailing 8q of
      seasonal differences), from Compustat quarterly.
- **Event date = `rdq`** (report date). Enter the day AFTER `rdq` (skip day 0/+1 to avoid
  the announcement jump and stale-price microstructure). Hold ~3 months (63 trading days).
- **PIT:** everything lagged to `rdq`; Compustat fundamentals only used once `rdq` has passed.
- **Map to CRSP:** Compustat gvkey→permno via CCM (as-of `rdq`); IBES cusip→gvkey→permno.

## Arms
- **Arm B** top-SUE quintile (hypothesis). **Arm A** bottom-SUE quintile (expected-loss/
  placebo — should underperform; a spread that is 0 means no PEAD). **Arm C** noise.
- **Cap segments:** large/mid vs micro (dollar-volume median split), reported side by side.

## Run spec
- Long-only EW, 3-month hold-band, ADV cost model, benchmark = cap-seg EW. Both SUE flavours.
- Metrics: net excess vs EW (Newey-West t), gross t (leak bar), FF5+UMD alpha t, net Sharpe,
  DSR/PBO vs cumulative count + configs. ONE run. Results final.

## Kill conditions
1. Arm C noise GROSS |t| ≥ 3 → leak, void.
2. Arm B net t < 1 in BOTH cap segments → backtest REJECT (forward-only still allowed).
3. Arm B − Arm A spread net t < 1 → no tradeable drift (the direct PEAD test).
4. Deploy gate: t > 3.4 AND DSR ≥ 0.95 AND PBO < 0.5 (expected unmet).

## Result (filled AFTER the run 2026-07-21 — never edited)
Data: 671,955 SUE events (Compustat rdq + IBES), 74.6% permno match, sue_ts on 71.8%.
Benchmark = SUE-coverage-universe EW within segment (the announcing names).

- **Arm C (noise) leak check: PASS** — gross excess t = -0.03 (large/mid), 0.17 (micro), both <3.
- **Arm B (top SUE):** large/mid +3.5 bps/mo net (t=0.23), micro -12.7 bps/mo (t=-0.83).
  Micro GROSS t=3.02 (real gross PEAD survives in microcap) but DEAD net of costs.
  FF5+UMD alpha large/mid +80 bps/mo (t=1.97) — suggestive but not the pre-registered metric.
- **Arm B − Arm A spread net t = 0.54** (the direct PEAD test) < 1 → no tradeable drift.
- Gate: DSR 0.245, PBO 0.114, REJECT.

### Verdict: **REJECT** (kill cond 2: B net t<1 both segments; kill cond 3: spread t<1).
Classic PEAD confirmed dead net of costs — strong GROSS surprise-drift in microcaps (gross
t=3.02) entirely eaten by turnover/spread, exactly as Martineau ("Rest in Peace PEAD") and
Chen-Velikov predict. Leak-checked clean. Not promoted.
