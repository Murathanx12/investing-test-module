# TRIAL-BRAIN-003-opportunistic-insider

**Registered:** 2026-07-21 (UTC) — BEFORE any SEC Form-4 data is fetched, parsed, or
matched to returns. No insider return has been seen by the experimenter or any code.
**Registry row:** `TRIALS/registry.jsonl` (cumulative n → 18)
**Grade:** paper-grade backtest (CRSP returns). Still a direction-check, not a forward result.

## Hypothesis
On survivorship-free CRSP 2004→2024, a monthly long-only portfolio of microcap-tilted
stocks that had an **opportunistic** insider **open-market purchase** in the trailing month
(traded at the FILING date, held with a turnover band) produces positive net-of-cost excess
vs the eligible-universe EW. Mechanism (Cohen-Malloy-Pomorski 2012): routine insider trades
(diversification/liquidity/comp-scheduled) are uninformative; the residual *opportunistic*
purchases predict future news and earnings, and the effect is concentrated in small caps and
decays slowly (1–6 months), so it can plausibly survive turnover costs where price factors
(BRAIN-002) could not.

## Literature prior
CMP (JF 2012): opportunistic long-short ≈ **82 bps/mo value-weighted** (~180 bps EW),
routine ≈ 0; sample 1986–2007. Lakonishok-Lee: insider-buy effect ~7–8%/12mo, almost
entirely small-cap. Post-SOX (Aug 2002) Form-4 filed within 2 business days, so the info is
public fast and widely scraped — the residual edge now lives in low-attention microcaps.
**Honest prior: ~55/45 FOR** net survival (the best-net candidate in the methodology, but
scraping has compressed it; long-only + microcap-only + 25 bps is a real test).

## Expected effect size
Arm B (opportunistic): +20 to +70 bps/mo net excess; net Sharpe 0.3–0.8 if real.
Arm A (routine): ≈ 0 by construction (the placebo).

## Signal & classification (frozen definitions)
- **Source:** SEC EDGAR Form 4 filings, 2004→2024 (start 2004 so a 3-year trading history
  exists to classify insiders from ~2007; 2004–2006 accrue history only).
- **Transactions kept:** non-derivative **open-market purchases only — transaction code `P`**
  (Table 1). Codes A/M/F/G/S (grants, option exercises, tax-withholding, sells) excluded.
- **Routine vs opportunistic (CMP, point-in-time):** an insider is **routine** for a given
  trade if they placed a trade in the **same calendar month in ≥3 consecutive prior years**;
  otherwise **opportunistic**. Insiders without a classifiable 3-year history are dropped
  (not defaulted to opportunistic) — the conservative choice, pre-committed here.
- **Event timing:** the signal fires on the **filing date** (`observed_at`), never the
  transaction date. A stock is "flagged" for month M if ≥1 qualifying purchase was *filed*
  in the trailing ~21 trading days.
- **Issuer→CRSP mapping (PIT):** issuer CIK → ticker via the SEC CIK↔ticker map, matched to a
  CRSP `permno` through `msenames` ticker history **as of the filing date** (handles ticker
  reuse/changes). Microcap matches are hand-audited against the filing; ambiguous matches are
  dropped and the drop count reported. (A supplementary `comp.company` cik↔gvkey pull may be
  used to cross-check via the CCM link — one clean WRDS read if needed.)
- **Herding note (reported, not gating):** also record #distinct opportunistic buyers per
  stock-month for a later conditioning study; the primary signal is the binary flag.

## Arms (two-arm leak design)
- **Arm A — routine-insider buys (the placebo / expected-loss arm).** CMP says routine ≈ 0.
  If Arm A shows an edge comparable to Arm B, the alpha is NOT coming from the classification
  → confound/leak, and the result is void.
- **Arm B — opportunistic-insider buys** (the hypothesis).
- **Arm C — noise control** (random flag matched to Arm B's monthly count) for the gross-t
  leak bar, same as BRAIN-000/001/002.

## Run spec (frozen)
- Panel: `data/crsp_panel_2002` (paper-grade CRSP), restricted to 2004→2024.
- Eligibility: price ≥ $1, daily-equiv dollar volume ≥ $200k (config defaults); microcap-tilted.
- Construction: monthly rebalance, long-only, equal-weight the flagged names, **hold-band 30%**
  (keep a name while it stays flagged within the band), `cost_bps_one_way=25`,
  `min_names_per_month=20` (insider flags are sparser than price deciles).
- Benchmark: eligible-universe EW. Metric: net excess mean + t, gross excess t, net Sharpe,
  DSR vs cumulative n=18, PBO where computable. ONE run. Results final.

## Kill conditions (pre-committed)
1. **Arm C (noise) GROSS excess |t| ≥ 3** → pipeline leak, all results void.
2. **Arm A (routine) net excess t ≥ 2** (a real edge where theory says none) AND within
   0.5 t of Arm B → classification is not the alpha source → confound, void/flag.
3. **Arm B (opportunistic) net excess t < 1** (full window) → REJECT; published negative.
4. **Arm B post-2015 net excess t < 0.5** → flagged "decayed — do not promote" even if the
   full-window t clears 1 (scraping-compression check).

## Result (to be filled AFTER the run — never edited afterwards)
- Arm C (gross leak check):
- Arm A (routine placebo):
- Arm B (opportunistic) full:
- Post-2015 sub-window:
- Issuer→CRSP match rate / drops:
- Verdict:
