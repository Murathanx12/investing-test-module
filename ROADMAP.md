# Aegis Investor Brain — Module Roadmap

**Created:** 2026-07-19 (Sunday) · **Status:** ACTIVE · **Home:** `C:\Users\mrthn\Aegis module`
**Parent project:** `C:\Users\mrthn\aegis-finance` (read-only dependency — this module NEVER writes into it)

---

## 0. What this module is

The research lab for the Investor Brain arc: the place where candidate signals are engineered,
combined by a shallow ranker, run through honest walk-forward validation, and either **killed**
or **promoted** to pre-registration in the main aegis-finance registry for forward scoring.

This module was synthesized from five independent AI audits (Gemini, GPT, Claude ×2, plus a
repo inventory) of the "build a neural network that iterates from 2002 and learns from its
mistakes" vision. The audits converged on one decisive point:

> **The iterate-on-history-until-it-beats-SPY loop is the textbook overfitting machine**
> (Bailey & López de Prado, False Strategy Theorem). Every "learn from mistakes" pass on the
> same history fits that history. The legitimate version is expanding-window walk-forward
> where each era is genuinely out-of-sample — trained once, scored once, trial-counted.

So the Brain is **not** a deep end-to-end RL agent. It is a **calibrated hypothesis engine**:
LLM perceives and proposes; hand-designed economic signals encode hypotheses; a shallow model
ranks; a deflated-Sharpe gate adopts; forward paper accounts are the only scorecard.

### The strategic bet (write it on the wall)

Every anomaly that survives publication lives in the same corner:
**microcap + limited-attention + event-driven + hard-to-arbitrage.**
79% of professional large-cap funds lose to SPY; that game is unwinnable. But a solo book can
deploy into a $200M name that Citadel can't be bothered with. **Size is the edge, not the
handicap.** And the forward, pre-registered calibration record — hundreds of scored,
falsifiable event calls that cannot be faked or overfit — **is the product**, worth more than
any backtested Sharpe.

---

## 1. Architecture (layered, firewalled)

```
L0  DATA SPINE — point-in-time, timestamped, survivorship-aware
    EODHD 50,462-history archive (2017+ usable) · EDGAR (Form 4, 8-K, 13F) · openFDA ·
    congress collector · transcripts · [WRDS/CRSP when HKU approves → paper grade]
        │
L1  LLM LAYER — perception + hypothesis, NEVER allocation          ── FIREWALL ──
    (a) event extraction → scored, falsifiable PRE-event calls (base rate, kill condition)
    (b) narrative extraction from filings/transcripts (between-the-lines, not star ratings)
    (c) hypothesis generation → written hypothesis + mechanism + expected decay + kill condition
        │  (numbers and pre-registered hypotheses only cross the firewall)
L2  SIGNAL ENSEMBLE — hand-designed, economically grounded, one pre-registered trial each
    opportunistic-insider (microcap-tilted) · PEAD (microcap) · supplier-shock ·
    event-drift (FDA/PDUFA) · revisions · congress  — each with a documented literature prior
        │
L3  SHALLOW COMBINER — a RANKER, not a learner
    GBM baseline + 1–2 hidden-layer NN, cross-sectional rank output.
    GKX: shallow beats deep at this signal-to-noise. If it needs depth, it's overfitting.
    Trained ONLY via expanding-window walk-forward + purged/embargoed CV.
        │
L4  ADOPTION GATE — what makes it honest
    Deflated Sharpe vs CUMULATIVE trial count (main repo registry, currently 14) ·
    PBO < 0.5 · capacity/transaction-cost model in from day one · every candidate logged
    including rejects. A raw Sharpe with no trial count is inadmissible.
        │
L5  FORWARD PAPER ACCOUNTS — the only scorecard
    Backtests here are direction-check only (survivorship bounds reported). Promotion =
    a TRIAL-*.md in aegis-finance/docs/TRIALS/ + registry row, scored by the forward clocks.
    The accumulating calibration record is the moat.
```

## 2. Hard constraints (non-negotiable, inherited from CANON + the audits)

1. **Pre-register before touching data.** Hypothesis, mechanism, expected effect size,
   expected decay, kill condition — written to `TRIALS/` here *before* the run; promoted
   candidates re-registered in the main repo before forward scoring.
2. **One run per hypothesis.** No loop-back re-tuning after seeing the walk-forward result.
   A failed walk-forward is a published negative, not a tuning signal.
3. **Two-arm every anomaly test.** One arm expected to LOSE (e.g. plain customer-momentum
   post-2004, themes-vs-SPY). If the expected-loss arm wins, the pipeline has a leak — that's
   the real test.
4. **Report deflated numbers, always.** DSR with running cumulative trial count + PBO.
5. **Survivorship-bound every backtest** until WRDS: run largest-100 vs full-universe and
   report the gap as an explicit bias bound.
6. **The LLM never touches an allocation.** Perception and hypothesis only.
7. **Nothing from this module writes to aegis-finance** — not the PIT store, not `paper_nav`,
   not the registry DB. Promotion is done by a human committing a trial doc in the main repo.

## 3. Literature priors baked into the signals (calibrate, don't dream)

| Signal | Prior | Source |
|---|---|---|
| Opportunistic insider buys | ~82 bps/mo abnormal, microcap-concentrated, decays 6–12mo; opportunistic-vs-routine split is the whole edge | Cohen-Malloy-Pomorski |
| PEAD | Persistent but microcap-only since ~2006 | Martineau "Rest in Peace PEAD" |
| Customer/supplier momentum | Dead in canonical form (negative 2005–2018); the LLM-embedding second-order version is open | Cohen-Frazzini + 2026 embedding work |
| Analyst signals | Levels priced; *revisions* and LLM-extracted narrative survive | Barber 2001; 2025 LLM-narrative study |
| ML cross-section | NN monthly OOS R² ≈ 0.33–0.40%; shallow > deep; momentum/liquidity/vol dominate | Gu-Kelly-Xiu 2020 |
| Active management base rate | 79% of large-cap pros lose to SPY (2025); ~90% over 15y | SPIVA |

## 4. Phases

> **Progress (2026-07-20):** Phase 3 harness/gate/discipline ✅ built and exercised by two
> pre-registered trials (BRAIN-000/001, both honest REJECTs — see TRIALS/ and STATUS.md).
> Phase 4 CRSP loader ✅ coded, ⛔ blocked on WRDS re-enable. Phase 2 event ledger ✅ core
> built + FDA feed harvested. Phase 0/1 live on the main repo (not this module).

### Phase 0 — Monday verifications (2026-07-20, main repo, ~15 min)
- Did Alpaca DKNG 1,897 + SLDP 22,500 fill at the open? First divergence snapshot in `alpaca:equity`.
- Did the congress collector pull REAL data at 07:30 ET (watch for false-zero poisoning)?
- Live click-through of factor-lens / build-warning surfaces (`c4c6ea4`).
- *Registered isn't fired. No architecture work counts until the forward clocks genuinely run.*

### Phase 1 — TRIAL-THEME-SUPPLY (main repo discipline, this module's compute)
- Pre-register BEFORE any return is computed: PIT theme baskets frozen from thematic-ETF
  launch holdings (LIT '10, ROBO '13, HACK '14, BOTZ '16, QTUM '18 + 3–5 more), members
  classified supplier/applier from launch-date descriptions only.
- Study A: themes vs SPY (prior: lose ~4%/yr — the expected-loss arm).
- Study B: suppliers minus appliers within themes (Murat's thesis — genuinely open, humble prior).
- Data: EODHD panel 2017+ (survivorship-free window) + yfinance pre-2017 with bias bound.

### Phase 2 — Event Ledger v1 (extends `forecast_ledger.py` pattern)
- LLM extracts FDA/PDUFA dates + product launches → structured pre-event calls with base-rate
  probability and post-event drift expectation → PIT snapshots → scheduler scores at maturity.
- This is L1(a) and the start of the calibration record.

### Phase 3 — Brain v0 (THIS MODULE, starts now)
- `aegis_brain` package: EODHD panel loader (read-only) → feature engineering (momentum,
  liquidity, vol + L2 event features as they come online) → GBM/shallow-NN cross-sectional
  ranker → expanding-window walk-forward with purged/embargo CV, turnover + cost model →
  adoption gate (DSR/PBO vs cumulative count).
- Grade: **direction-check only** until WRDS. Deliverable: a harness so honest that a
  positive result survives its own audit.

### Phase 4 — WRDS unlock (HKU approved 2026-07-20)
- ✅ Account live, CRSP/Compustat confirmed (331 libraries, 28,913 real delisting returns).
- ✅ CRSP panel loader + hold-band harness built; TRIAL-BRAIN-002 pre-registered (n=17).
- ⛔ Account disabled by a login-flood misconfig (fixed); support ticket filed. On re-enable:
  build_crsp_panel → run_trial_002 at paper grade → promote survivors → NN up the queue.

### Ongoing
- ✅ EODHD archive backed up (1.07 GB) and FDA harvest backed up (16,195 events), OneDrive.
- WRDS: keep HKU VPN on for any pull; connect only via `wrds_conn.get_connection()`.
- QC lane backtest URLs still owed by Murat.

## 5. What we are explicitly NOT building

- A deep end-to-end network mining raw prices (GKX: it can't find mechanisms you didn't design in).
- An RL agent trained by iterating over 2002–2026 (sample-inefficient, memorizes regimes,
  False Strategy Theorem bait).
- An LLM that decides allocations (fragile, manipulable — see TradeTrap/AutoRedTrader red-teaming).
- A large-cap stock picker (the 79%-of-pros-fail game).
