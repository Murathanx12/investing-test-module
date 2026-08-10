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

---

## 6. The two scoreboards (added NIGHT-7, binding)

A portfolio can be a **good product** without containing **novel alpha**. AVUV is
the proof: a competently implemented, actively managed small-value fund that
almost certainly contains no undiscovered factor. Conflating the two scoreboards
is what made the last six nights feel like failure when half of them were
successes on the other board.

| | **Research scoreboard** | **Product scoreboard** |
|---|---|---|
| asks | is there incremental information after known factors? | would a real person end up with more money? |
| metrics | factor-residual alpha, incremental IC, MDE, placebo, era stability, forward evidence | terminal wealth, drawdown, cost, tax, capacity, usability |
| bar | t > 3 after trial-count deflation (Harvey-Liu-Zhu) | beat the accessible alternative net of everything |
| our status | **NOT MET** — DSR ≈ 0.55 at N=179 (NIGHT-7 T4) | **partially met and improving** |
| evidence type | inference (t-stats, needs decades) | arithmetic (costs, dates, fees — needs no t-stat) |

**They are never mixed in a single sentence.** A claim on the product board never
borrows credibility from the research board, and vice versa.

## 7. The craftsmanship ledger — the deterministic backbone

Israel, Jiang & Ross (*Craftsmanship Alpha*, JPM 44(2) 2018, verified): the
decisions made **after** choosing a style are themselves worth money. Our own
measurements now populate this ledger, and every line is **arithmetic, not
inference** — which is exactly why they are worth more than another t-stat.

| line | measured value | source | status |
|---|---|---|---|
| annual clock vs monthly | **+2.43%/yr** at $1m under daily execution ($602,509 avoided cost per $1m over 23yr) | NIGHT-6 G7 | **BANKED** |
| avoid trailing stops | **+3.08%/yr** vs running one ($743,599 avoided cost per $1m over 23yr) | NIGHT-7 T2b | **BANKED** |
| clock ensemble (12 staggered cohorts) | removes a **2.45 pt/yr** range of date luck at **zero** extra turnover | NIGHT-7 T3 | **BANKED** |
| fee vs AVUV (0.25%) | +0.25%/yr, deterministic | fund fact sheet | trivial |
| capacity below AVUV's floor | plausible, **not yet measured** | — | OPEN (ADV/price-impact test) |
| tax-loss harvesting | **1.10%/yr gross, 0.85% wash-sale-constrained** (Chaudhuri-Burnham-Lo FAJ 2020) | verified | **US-TAXABLE USERS ONLY — worth ≈0 to a HK-resident account. Never in our own target.** |

Against a *selection* residual whose probability of being positive is 0.55, the
implementation ledger is the stronger asset and should be the product's spine.

## 8. LLM role — settled (NIGHT-3 measured it, NIGHT-7 built the guard)

The LLM is a **measuring instrument**, never the decision-maker. Closed: NIGHT-3
rejected direct LLM stock selection (t 0.04 / 0.93 over 204 months, 16,320 graded
decisions), all five external reviews agreed independently, and the literature
concurs — under leakage control, LLM agent returns decompose into market and
style beta (FINSABER, KDD 2026; KTD-FIN, arXiv:2605.28359).

What the LLM *does* do, enforced by `aegis_brain/firewall/`:

1. **Extract** structured numbers from anonymised primary sources (10-K, 8-K, FDA,
   government releases) — never seeing prices, returns or outcomes.
2. **Adjudicate** read-only: explain, red-flag, veto — scored on Brier, never P&L.

Murat's "turn the world into numbers" ask lives in the **Event object**: an LLM
reads a primary source and emits `(observed_at, source_type, actors, event_class,
prior_expectation, surprise_direction, surprise_magnitude, fundamental_channel,
firm_exposure, horizon, counterevidence, confidence, provenance, decay_rule)`;
deterministic code attaches market data; small models test for **incremental**
information after PEAD/revision baselines. Beliefs update over **mechanism
claims**, never over ticker P&L.

## 9. Registered but unbuilt — the queue, with why

Each behind pre-registration **and a power check that can refuse it**, as T6 was
refused:

- **PRisk replication** — first extractor validation. Ground truth free and live
  (firmlevelrisk.com, 2002–2021q2, >11,000 firms, 81 countries). *If Layer 1
  cannot reproduce a published measurement, everything downstream is noise.*
  **Highest priority.**
- **Semantic diff (TEXT-SEMDIFF-1)** — registered, **power-failed as a money
  test** (MDE 4.52%/yr vs a 3.4%/yr optimistic prior), licensed only as extractor
  validation on filing-pairs.
- **Narrative-salience thematic entry** — Ben-David et al. (RFS 2023, verified):
  specialised ETFs lose ~30% risk-adjusted over five years, driven by
  overvaluation at launch, not fees. Murat's themes (semis, energy, defence,
  space, batteries, quantum) are **not rejected** — the **entry timing is
  inverted**. Exposure is interesting at the *bottom* of narrative salience,
  testable on the GDELT feed we already ingest.
- **Insider-disagreement interaction** — non-routine insider buys × analyst
  revision disagreement. Interaction, not standalone.
- **Capacity edge below AVUV's floor** — ADV participation and price-impact curve.
  The one AVUV axis with high plausibility and no measurement yet.
- **`conc_low` resurrection** — the only distinct candidate left in the 148-row
  graveyard, and it must now be re-read under the calibrated turnover penalty.

## 10. AVUV — corrected framing (binding)

**AVUV is actively managed.** Avantis runs daily active oversight, current-price-
based selection and deliberate implementation on $25B+. Every document calling it
"a rigid passive rule" is wrong and must be fixed. Our benchmark is a *competent
active implementer*, which makes beating it harder and more meaningful.

Standing product sentence, now carrying T4's number:

> Against the fund actually running our strategy (AVUV), we have **not shown an
> edge** (+1.46%/yr, t −0.02, 39 months). Against value ETFs and the Ken French
> proxy the convergent estimate is **~+2%/yr at t≈1.2**. After trial-count
> deflation, `P(true excess Sharpe > 0) ≈ 0.55`. What we *can* demonstrate is
> implementation: clock, churn, date luck and fees — arithmetic, not inference.

## 11. Excluded, permanently

Protected characteristics as features (CANON §12). The mechanisms are real and
are captured by board connections, prior employment, political appointments,
lobbying, campaign contributions, government contracts, disclosed ownership and
geographic revenue — all observable, all already in scope.

## 12. The strategic fork — MURAT'S DECISION, presented honestly

Both paths are legitimate. They compete for the same hours, so it is a choice.

**Path A — the fund.** Requires capital, t > 3 after deflation, and years of
forward record. It moves at one month per month and cannot be accelerated.
NIGHT-7's T4 says the research board is **not met today**, so Path A is gated on
evidence we do not have and cannot manufacture.

**Path B — research and infrastructure.** What we already own and nobody else
does: a **published graveyard** with a machine-enforced failure taxonomy, a
**pre-registration record with an external hash anchor** that cannot be backdated,
a **calibrated cost simulator** that has now overturned two of our own headline
results, and a **forward paper record** running since 2026-06-08. A first-authored
paper plus an open dataset is a citable asset — and it is what opens Path A later.

The honest asymmetry: Path A's output is uncertain and years away; Path B's is
nearly finished, unusual, and worth more at 18 than 1%/yr on a small account.
**Recommendation: Path B as the primary track, forward lanes continuing untouched
so Path A stays available.** Murat decides.

## 13. Regulatory guardrail

The SEC has brought AI-washing enforcement actions for misrepresenting how AI is
used. Marketing language such as "an AI brain that beats the market" must never
appear unless literally true and evidenced. Publishing negative results is legally
protective, not merely admirable.
