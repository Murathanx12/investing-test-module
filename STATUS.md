# Aegis Investor Brain — Status Snapshot

**As of:** 2026-07-21 (post-v1.0) · **Repo:** https://github.com/Murathanx12/investing-test-module
**Tests:** 61 green · **Cumulative trial count:** 21 (see TRIALS/registry.jsonl)

The one-screen picture of where the module is. Full architecture in ROADMAP.md;
per-session detail in docs/SESSION_*.md.

**2026-07-24 — TRIAL-BRAIN-006 FDA approval drift: REJECT** (pre-registered, one run): 671 in-panel NDA/BLA events 2002-2024; B large/mid -30.1 bps/mo net t=-0.89, B-PRI t=0.13, noise clean; micro segment untestable (2 live months) - daily-CAR revisit = NEW registration post crsp.dsf pull. Crosswalk data trap recorded: openFDA sponsor_name = CURRENT holder; roll-up events excluded as unattributable.

**2026-07-24 — TRIAL-THEME-SUPPLY basket arm: REJECT** (pre-registered, explore-only, one run): B-A spread t=0.10 (+3.2 bps) = NO cross-sectional info at annual cadence; micro B net t=-4.27; noise clean. Combined with 3b's cust_mom REJECT, the suppliers thesis is FULLY adjudicated - no holding period pays honest costs. Cumulative explore candidates 90.

**2026-07-24 — Factory batch 5: ZERO graduates (30 scans, priors 15/15 directional).** Sign reversals for batch 6: high-DTC (+, IC t 6.2), inst-persist (+, IC t 3.4). insider_cluster/insider_si VOID-DESIGN (need flag harness). defensive = screen-class (maxDD -35% vs -52..-82%). INSTR-HOLD-HORIZON: FLAT 14-17 bps/mo across 1-24mo bands - signal-band exits make long holds free. Cumulative candidates 120.

**2026-07-24 EOD — Batch 6 + BRAIN-009: ZERO graduates.** dtc arms post factory-best largemid net t (3.4/3.0) but FAIL the IC leg - rule held. inst-persist mirror refuted (both tails lose). cust_conc sign reversal book-inspected clean (IC t -7.4, Dhaliwal side). Insider clusters add nothing over single opportunistic buys (BRAIN-009 closed). Cumulative 130.

## 2026-07-22: STRATEGY FACTORY + BRAIN-008 (second survivor) + FULL WRDS HAUL

- **Strategy Factory** built (explore 2004-2018 / confirm 2019-2024 held out;
  docs/STRATEGY_FACTORY.md). Batch 1 (20 price/vol signals): ZERO graduates —
  Murat's dip-buy theses adjudicated and rejected. Batch 2 (10 fundamentals):
  zero largemid graduates, but small-cap gross_prof survived the pre-registered
  honest-cost re-test (50bps t 1.96; 75bps t 1.57).
- **TRIAL-BRAIN-008-grossprof-small: CONFIRM PASS** (one run, held-out 72mo):
  +24.1 bps/mo net (explore said +23.2 — replicated), IC t 4.29 OOS. Caveats:
  DSR 0.098 (n_trials=61), FF6 alpha negative (factor-tilt risk), NW t 0.77.
  **Second survivor → BRAIN-007 fusion pre-registration RE-OPENS.** Next:
  forward small-cap-quality paper lane (attended seed) + 1963-2001 robustness.
- **WRDS harvest #2+#3 (two Duo taps, zero failures, 629MB backed up):**
  seg_customer 667k links (Cohen-Frazzini → TRIAL-THEME-SUPPLY unblocked);
  13F mgr/breadth/top-10 best-ideas (3.6M rows) 1980→present; short interest
  5.2M; IBES recs 6.4M + price targets 2.5M; CRSP+funda+fundq+dsf-aggregate
  extensions back to 1963/1971; catalogs for comp_pit (12), optionm (578),
  ravenpack_trial, wrdsapps. Congress archives downloaded free (senate 8,350
  txns + kadoa 437 filers).
- Queued instruments: INSTR-GEMINI-SCORE, INSTR-CONGRESS-HIST,
  INSTR-OVERFIT-CEILING, INSTR-RL-ALLOC (see STRATEGY_FACTORY.md).

## 2026-07-21 (PM): PROMOTION EXECUTED — BRAIN-003 is live in aegis-finance

The INTEGRATION.md protocol ran end-to-end (human-authorized "adopt it"):
- Insider panel EXTENDED 2006→**2026Q1** (5 new SEC quarters + re-classify;
  852,512 purchases, 107,351 opportunistic; panel_end 2026-03-31).
- New `scripts/export_routine_history.py` → compact live-classification artifact
  (`cmp_routine_history.json.gz`, 25,020 insiders + 3,648 recent opportunistic
  buys, 0.22 MB) — closes the live false-zero gap the bundled scorer had.
- aegis-finance side: TRIAL-CMP-INSIDER-IC pre-registered (registry + doc),
  `insider_cmp:` forward collector wired beside the T9 clock. Forward IC clock
  runs from the next deploy. **Quarterly maintenance:** re-run download →
  build_insider_panel → export_routine_history, re-commit the artifact there.

## Pipeline status (L0 → L5)

| Layer | What | Status |
|---|---|---|
| L0 data | EODHD panel (direction-check) | ✅ built + cached (`data/panel_2017`, `_clean`) |
| L0 data | **CRSP panel (paper-grade)** | ✅ **BUILT** — 276 mo (2002→2024), 11,098 permnos, `data/crsp_panel_2002/` |
| L0 data | Compustat annual + quarterly, CCM link, IBES | ✅ harvested → `data/wrds_raw/` (fundamentals, rdq, revisions) |
| L1a events | openFDA approval feed | ✅ harvested 16,195 events 2002-2026 (2,742 NDA/BLA) |
| L1a events | sponsor→ticker PIT mapping | ⬜ next — CCM link + IBES cusip now available offline |
| L1b/c narrative + hypothesis | **LLM perception (DeepSeek)** | ✅ built — neutered situation→calibrated P, forward-only, never allocates |
| L2 signals | GKX price big-three | ✅ built (dead net of costs — see trials) |
| L2 signals | **insider collector (SEC bulk)** | ✅ built + 10 tests (CMP routine/opp classifier); BRAIN-003 run pending |
| L2 signals | PEAD / revisions / supplier | ⬜ next, each a new pre-registered trial |
| L3 combiner | shallow GBM + ≤2-layer MLP ranker | ✅ built |
| L4 gate | DSR vs cumulative n, PBO, survivorship bound | ✅ built |
| L4 harness | walk-forward + costs + **hold-band turnover control** | ✅ built |
| L5 forward | **event ledger — FORWARD CLOCK RUNNING** | ✅ 7 real pre-registered PDUFA calls (Jul-Sep 2026); Brier-scored via yfinance at maturity |
| L5 forward | promotion to main-repo forward clocks | ⬜ manual, when a candidate survives |

## Trials run (all pre-registered, results final)

- **BRAIN-000** (EODHD) — REJECT. Surfaced OTC adjusted-close corruption (→ clean universe).
- **BRAIN-001** (EODHD clean) — REJECT on merits. GKX price factors don't beat universe
  net of 25 bps; **turnover drag (~45 bps/mo) is the killer** → hold-band added.
- **BRAIN-002** (CRSP, hold-band) — **REJECT (2026-07-21).** First paper-grade backtest.
  Price big-three GBM-ranked don't beat the EW CRSP universe net of 25 bps (net excess
  t=-2.80); leak check PASSED. Price factors permanently demoted to combiner-input-only.
- **BRAIN-003** (opportunistic insider, CRSP) — **FIRST NON-REJECT (2026-07-21).**
  Survives kill conditions in **large/mid caps** (+17 bps/mo vs EW t=1.40; FF5+UMD alpha
  +102 bps/mo t=1.89; post-2015 t=1.30), **null in microcap** — vindicating the cap fix.
  Leak PASSED; PBO 0.41; deploy gate NOT met (DSR 0.26). Weak-positive prior. **PROMOTABLE**
  (`export/opportunistic_insider/`, scorer `signals/insider_scorer.py`).
- **BRAIN-004** (PEAD/SUE) — **REJECT.** Strong gross surprise-drift in microcap (gross t=3.0)
  dead net of costs (B net t<1 both segs; B-A spread t=0.54). Leak-checked clean.
- **BRAIN-005** (revisions) — **REJECT.** Leak bar caught a benchmark-mismatch bias (noise gross
  t 4.0/5.9 → void); fixed (coverage-universe benchmark), re-run → the "edge" was the bias, not
  signal (B net t<1). A clean false-positive save.
- **BRAIN-007** (fusion) — **NOT RUN.** Only 1 signal survived; fusion needs ≥2. Re-opens later.

## The one blocker — CLEARED (2026-07-21)

WRDS account re-enabled by support; the whole harvest is done. Two Duo taps pulled
CRSP + Compustat (annual/quarterly) + CCM link + IBES (~7.4M rows) in one session, and
the CRSP paper-grade panel is built. **We now read local parquet — no more WRDS pulls.**
TRIAL-BRAIN-002 is unblocked and runs fully offline.

## Next: run the pre-registered trial (offline, no WRDS)

```
.venv\Scripts\python -m scripts.run_trial_002    # ONE run on data/crsp_panel_2002 -> record in trial doc
```

## Backups (OneDrive\AegisBackups)

- `eodhd_archive_2026-07-19.tar` (1.07 GB, 50,471 entries)
- `fda_approvals_2026-07-20.parquet` (16,195 events)
- `wrds_2026-07-21/` (184 MB) — raw tables + built CRSP panel + `WRDS_DATA_PREVIEW.xlsx`

## Buildable now without WRDS (candidate next chunks)

1. Insider Form-4 collector (SEC EDGAR is public) → opportunistic-vs-routine signal,
   new pre-registered trial. Strongest documented edge in the roadmap.
2. FDA event-drift study design doc (needs price+ticker link to run — partial until WRDS).
3. LLM narrative-extraction spike on the FDA/EDGAR text (L1b), scored into the event ledger.
