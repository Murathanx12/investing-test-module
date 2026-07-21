# Aegis Investor Brain — Status Snapshot

**As of:** 2026-07-20 · **Repo:** https://github.com/Murathanx12/investing-test-module
**Tests:** 35 green · **Cumulative trial count:** 17 (14 main-repo base + 3 local)

The one-screen picture of where the module is. Full architecture in ROADMAP.md;
per-session detail in docs/SESSION_*.md.

## Pipeline status (L0 → L5)

| Layer | What | Status |
|---|---|---|
| L0 data | EODHD panel (direction-check) | ✅ built + cached (`data/panel_2017`, `_clean`) |
| L0 data | **CRSP panel (paper-grade)** | ✅ **BUILT** — 276 mo (2002→2024), 11,098 permnos, `data/crsp_panel_2002/` |
| L0 data | Compustat annual + quarterly, CCM link, IBES | ✅ harvested → `data/wrds_raw/` (fundamentals, rdq, revisions) |
| L1a events | openFDA approval feed | ✅ harvested 16,195 events 2002-2026 (2,742 NDA/BLA) |
| L1a events | sponsor→ticker PIT mapping | ⬜ next — CCM link + IBES cusip now available offline |
| L1b/c narrative + hypothesis | LLM perception layer | ⬜ not started (Phase 2+) |
| L2 signals | GKX price big-three | ✅ built (dead net of costs — see trials) |
| L2 signals | insider / PEAD / supplier | ⬜ next, each a new pre-registered trial |
| L3 combiner | shallow GBM + ≤2-layer MLP ranker | ✅ built |
| L4 gate | DSR vs cumulative n, PBO, survivorship bound | ✅ built |
| L4 harness | walk-forward + costs + **hold-band turnover control** | ✅ built |
| L5 forward | **event ledger** (Brier calibration record) | ✅ core built + tested |
| L5 forward | promotion to main-repo forward clocks | ⬜ manual, when a candidate survives |

## Trials run (all pre-registered, results final)

- **BRAIN-000** (EODHD) — REJECT. Surfaced OTC adjusted-close corruption (→ clean universe).
- **BRAIN-001** (EODHD clean) — REJECT on merits. GKX price factors don't beat universe
  net of 25 bps; **turnover drag (~45 bps/mo) is the killer** → hold-band added.
- **BRAIN-002** (CRSP, hold-band) — **pre-registered (n=17), staged, WRDS-blocked.**
  Spec frozen while the account was disabled (provably no data peeking).

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
