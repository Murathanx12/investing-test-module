# TRIAL-BRAIN-005-revisions

**Registered:** 2026-07-21 (UTC) — BEFORE any revision signal is computed or joined to a return.
**Registry row:** `TRIALS/registry.jsonl` (cumulative n → 20)
**Grade:** paper-grade backtest (CRSP returns). Prior-setting; deploy gate separate.

## Hypothesis
On CRSP 2006→2024, a long-only monthly portfolio of stocks in the top analyst-revision
quintile (net upward EPS-estimate revisions over the trailing 1-3 months) held with a
hold-band earns positive net-of-cost excess vs a cap-segment EW benchmark. Mechanism:
sticky under-reaction to revisions (Chan-Jegadeesh-Lakonishok / Gleason-Lee); revisions
often subsume PEAD. Prior: **decayed in large caps, marginal; strongest in low-coverage
names** — ~40/60 against clearing net t>1.

## Signal (frozen)
- From IBES `statsum_epsus`, keyed on `statpers` (the monthly consensus snapshot = the PIT
  anchor). Signal for month M uses only snapshots dated ≤ M-end.
- **Revision score** = net (# up − # down) EPS-estimate revisions over trailing 3 months
  of the FY1 mean estimate, scaled by dispersion; also report a simple Δmean/|mean|.
  Weight fresh revisions over stale (Gleason-Lee spirit).
- UNADJUSTED IBES (split-adjustment look-ahead guard). Coverage-sparse names (numest ≤ 1)
  flagged — a 1-analyst "revision" is unreliable.
- **Map to CRSP:** IBES cusip → gvkey (via Compustat cusip) → permno (CCM), as-of month-end.

## Arms
- **Arm B** top-revision quintile. **Arm A** bottom-revision quintile (expected-loss).
  **Arm C** noise. Cap segments large/mid vs micro.

## Run spec
- Long-only EW, monthly rebalance, hold-band, ADV cost, benchmark = cap-seg EW.
- Metrics: net excess (Newey-West t), gross t, FF5+UMD alpha t, net Sharpe, DSR/PBO.
- **Incremental test:** regress Arm B net excess on the BRAIN-004 SUE signal — the revision
  edge must add power OVER SUE (else it double-counts the same earnings event). ONE run.

## Kill conditions
1. Arm C noise GROSS |t| ≥ 3 → leak, void.
2. Arm B net t < 1 in BOTH cap segments → backtest REJECT.
3. Revision edge not incremental to SUE (nested-test coefficient t < 1) → flagged redundant.
4. Deploy gate: t > 3.4 AND DSR ≥ 0.95 AND PBO < 0.5 (expected unmet).

## Result (filled AFTER the run 2026-07-21 — never edited)
Data: 921,925 revision-panel rows (IBES FY1 statpers), 68.9% permno match, numest≥2 kept.

**v1 run VOIDED by the leak bar (a real bug, transparently):** the first run benchmarked the
analyst-covered portfolios against the FULL eligible universe. Covered names systematically
outperform uncovered, so the noise arm (random covered names) beat the benchmark: **noise
GROSS t = 4.02 (large/mid), 5.87 (micro) ≥ 3 → kill condition 1 (leak) → VOID.** The two-arm
design caught a benchmark-mismatch bias that would otherwise read as revision alpha.

**Instrument fixed once (benchmark = coverage-universe EW, `flag_portfolio` coverage param),
re-run once — final:**
- **Arm C (noise) leak check: PASS** — gross t = 0.28 (large/mid), 1.38 (micro), both <3.
  (The fix eliminated the leak — direct confirmation of the diagnosis.)
- **Arm B (top revisions):** large/mid -4.0 bps/mo net (t=-0.48), micro -29.2 bps/mo (t=-3.37).
  Both < 1. The apparent edge in v1 was ENTIRELY the covered-vs-full-universe bias.
- Arm B − Arm A spread net t = 0.35. Gate: DSR 0.294, PBO 0.057, REJECT.

### Verdict: **REJECT.** Once benchmarked against the analyst-covered universe it lives in,
revision momentum does NOT beat holding all covered names net of costs. A clean example of the
leak bar preventing a false positive. Not promoted; the incremental-vs-SUE test is moot (no edge).
