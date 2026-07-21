# Investor Brain — Methodology

**Created:** 2026-07-21 · **Status:** ACTIVE blueprint · synthesized from four parallel
research sweeps (academic literature, open-source tooling, event-driven construction
recipes, and an inventory of the parent `aegis-finance` repo). Read alongside `ROADMAP.md`
(architecture) and `STATUS.md` (current state).

This document is the **how**. It converts the vision — "an autonomous brain that beats the
S&P by learning from events" — into a concrete, cited, buildable method that cannot fool
itself. Every design choice below traces to evidence in §11.

---

## 1. What the brain is (and is not)

The brain is a **calibrated hypothesis engine**, not a price-mining neural network.

The founding insight, confirmed by all five original audits and now by the literature
sweep: *iterating a model over 2002–2026 until it beats the S&P is the textbook
overfitting machine* (Bailey–López de Prado False Strategy Theorem, §11-#10). The expected
maximum Sharpe from N random strategies grows like √(ln N) — try enough configs and a
spectacular backtest is **guaranteed** whether or not any edge exists. A 2026 result
(§11-#12) shows walk-forward alone does **not** save you; only walk-forward + purging +
honest trial-accounting does.

So the brain does not learn by replaying history until it wins. It learns in three
firewalled loops (§2), each of which is provably out-of-sample.

**It is:** a shallow cross-sectional ranker fed by economically-grounded, pre-registered
signals, gated by a deflated-Sharpe adoption test, and scored forward by a live
calibration ledger.
**It is not:** a deep end-to-end net on raw prices, an RL agent trading its own P&L, or an
LLM that sizes positions. (§11-#1, #8, #17 — all three of these lose or overfit.)

---

## 2. The three learning loops

The word "learning" is used precisely. The brain updates at three timescales, none of
which can overfit the past:

1. **Ranker loop — weights, per era (in-sample, walk-forward).**
   A *shallow* model (gradient-boosted trees or a ≤2-hidden-layer MLP) re-fits each year on
   all data up to that date, then predicts the *next* year out-of-sample. Genuine learning
   from history, firewalled by expanding-window walk-forward + purged/embargoed CV.
   GKX (§11-#1) and a 2025 transformer horse-race (§11-#8) both show **shallow beats deep**
   at this signal-to-noise — if the model needs depth, it is memorising.

2. **Scientist loop — hypotheses, per trial (pre-registered).**
   Each signal is a written hypothesis with a mechanism, expected effect size, expected
   decay, and a kill condition, registered *before* the data is touched. We test once and
   publish the result — pass **or** fail. The cumulative trial count deflates every Sharpe
   (§5). "Learning" here is Bayesian updating over which mechanisms are real, encoded in the
   registry and the literature priors — never tune-until-it-works.

3. **Calibration loop — forward, live (the real "learn from mistakes").**
   The brain emits falsifiable, timestamped probabilistic pre-event calls ("P(this microcap
   drifts up over 21d after this FDA approval) = 0.63"), then scores them at maturity with a
   Brier score on data *that did not exist when it predicted*. The reliability curve reveals
   — un-fakeably — where it actually has edge. This is the only version of "learn from its
   mistakes" that cannot be gamed, because the test set is the future.

---

## 3. The signal library — ranked by *net-of-cost* survival

The binding constraint is not finding signals; it is that **turnover × microcap spread
eats almost everything** (§11-#19: net of effective spreads, the average anomaly earns
~4 bps/month, the best ~10, and many go negative post-2005). We therefore rank candidate
signals by their realistic *net* survival, not their headline gross alpha.

| Rank | Signal | Mechanism / prior | Net-of-cost verdict | Data |
|---|---|---|---|---|
| **1** | **Opportunistic insider buys** | Strip "routine" insiders; residual buys predict news (§11-#18) | **Best survivor** — low turnover, slow decay (1–6mo), small-cap-native, value-weighted 82 bps/mo survives HXZ | SEC Form 4 (EDGAR, public) |
| **2** | **FDA / BLA-NDA approvals** | Binary catalyst; microcap biotech gaps 10–200% | Tradeable per-event, but fat left tail (CRLs −50–80%) & capacity-limited; a *lottery/vol* exposure, not a tidy drift | openFDA (have 16,195 events) |
| **3** | **PEAD / earnings surprise (SUE)** | Underreaction to earnings; inattention (§11-#20, #23) | Marginal — dead for liquid names since ~2006, alive in microcaps only; needs hold-band | Compustat `rdq` + IBES (have both) |
| **4** | **Analyst revision momentum** | Sticky revisions drift; subsumes much of PEAD | Marginal — decayed in large caps, strongest in low-coverage names; hold-band | IBES `statpers` (have) |
| **5** | **GKX price big-three** (mom/liq/vol) | Classic cross-section | *Already tested → dead net of 25 bps* (BRAIN-001). Kept only as a ranker input, never standalone | CRSP (have) |
| **F** | **LLM narrative** (10-K/8-K/calls) | Read what numbers miss; predict the *surprise* not the price (§11-#17) | Feature source only, pending a clean lookahead-free calibration — never an allocator | EDGAR/transcripts |

**Design consequence:** we build in survival order. Insider first (best net edge, and the
Form-4 data is free), FDA second (data in hand, but treat as convex/tail-aware), PEAD and
revisions third (buildable today from Compustat+IBES, but expected marginal), LLM last and
only as a graded feature.

### Construction recipes (frozen definitions)

- **Opportunistic insider (§11-#18):** parse Form 4 from EDGAR; keep **open-market
  purchases only** (transaction code `P`); classify an insider *routine* if they traded the
  **same calendar month in 3+ consecutive prior years**, *opportunistic* otherwise (this
  rule is point-in-time by construction). **Trade at the filing date** (2-day lag post-SOX),
  not the transaction date. Herding (multiple insiders buying) strengthens it.
- **PEAD/SUE (§11-#20):** two SUE flavours — Foster time-series (Compustat `epspxq` seasonal
  random walk) and analyst-based (IBES actual − pre-announcement consensus). **Anchor
  everything to `rdq`, never fiscal period-end** (the #1 PEAD bug). Label = CAR over
  **[+2, +60] trading days**, skipping day 0/+1 to avoid the announcement jump. Report with
  and without microcaps. Use *unadjusted* IBES to dodge split-adjustment look-ahead.
- **FDA (§11-#21):** openFDA `submission_type=ORIG` & `submission_status=AP`; keep NDA/BLA,
  drop ANDA. Event date = `submission_status_date`. Sponsor→ticker map is the dominant
  error source — **hand-verify every microcap match**. Use bootstrap/rank tests (returns are
  non-normal, event-clustered), and never build long-only "buy approvals" without modelling
  the symmetric failure (CRL) gap-downs.
- **Revisions (§11-#4-methods):** net (up−down)/total over trailing 1–3mo from IBES
  `statpers` snapshots; weight fresh revisions over stale herding (Gleason-Lee). Must add
  incremental power over SUE in a nested test, or it is double-counting the same event.
- **Size interaction (§11-#24):** never trade size naked — it loads on distressed junk.
  Interact microcap with quality/profitability (GP/A). The survivable premium is small
  *high-quality* firms.

---

## 4. The model & features

**Model.** A cross-sectional **ranker**, not a return regressor. Two admissible forms,
both shallow: gradient-boosted trees (LightGBM, `num_leaves≤15`, `max_depth≤4`) and a
≤2-hidden-layer MLP. Both are already built (`combiner/ranker.py`). Output is a
cross-sectional score → long the top decile of the *eligible microcap-tilted* universe.

**Features (per stock-month), lagged to point-in-time before they touch the model:**
- Price/liquidity: 12-1 momentum, short-term reversal, realised vol, Amihud illiquidity,
  size, turnover. (GKX shows momentum/liquidity/vol dominate — §11-#1.)
- Event features: days-since / flag for opportunistic-insider buy; SUE (both flavours);
  revision momentum; dispersion; days-to/-from FDA event.
- Conditioning (inattention proxies, §11-#23): analyst coverage, turnover, announcement
  clustering — the *economic reason* the edges exist is that someone isn't looking yet.
- Quality interaction: GP/A, Piotroski (§11-#24).

**Feature whitelist discipline.** To avoid inventing overfit features, start from
published, audited characteristics: the **Chen-Zimmermann Open Source Asset Pricing**
catalog (200+ signals with PIT-correct construction code) and the **JKP** 13-theme factor
set (§11-#6, #7). Invent nothing that isn't grounded in a prior or a mechanism.

**Training.** Expanding-window walk-forward; purged + embargoed CV inside each window for
hyperparameters; one refit per year; no peeking forward, ever.

---

## 5. Validation & discipline stack (the adoption gate)

A raw Sharpe with no trial count is inadmissible. Every candidate clears **all** of:

1. **t > 3.0** minimum on the factor (Harvey-Liu-Zhu multiple-testing hurdle, §11-#4) —
   necessary, not sufficient.
2. **Deflated Sharpe Ratio ≥ 0.95** (§11-#9), deflated against the **shared cumulative
   trial count** — base **14** from aegis-finance, plus every local Brain trial (currently
   n=17). Every config variant tested increments N and makes the bar stricter.
3. **PBO < 0.5** via combinatorial purged CV (§11-#10, #11). No-PBO-no-ship.
4. **Net of a realistic microcap cost model** — effective half-spread + impact, budgeted at
   **25–45 bps/month one-way** (our own BRAIN-001 evidence + §11-#19). A signal that only
   clears at 5 bps is not real.
5. **Two-arm leak check** — one arm expected to LOSE; the leak-bar is on **gross** excess.
   If the expected-loss arm wins, the pipeline has a leak (this is how BRAIN-000 caught the
   OTC data corruption).
6. **Survivorship-honest** — now automatic: the CRSP panel carries real delisting returns.

These primitives are already vendored (`discipline/overfitting.py`, `purged_cv.py`) verbatim
from aegis-finance, and the gate (`gate/adoption.py`, `gate/registry.py`) enforces them.

---

## 6. Cost & capacity reality (the hold-band)

This section decides whether anything above is real. Novy-Marx–Velikov and Chen-Velikov
(§11-#19) are brutal: **turnover is destiny.** One-sided monthly turnover under ~50% can
keep a net spread; over ~100% almost never survives. Microcaps roughly **double** trading
costs — you are fishing in the one bucket where both the signal *and* the friction are
largest. That asymmetry (a solo book *can* trade $200M names a fund can't) is the whole
structural edge — but only if costed honestly.

**The single highest-leverage lever is the hold-band** (no-trade zone): enter on a strong
signal (top decile), but *hold* until it decays past a wider exit threshold rather than
rebalancing to a fresh top-decile each period. Cuts turnover 40–70% at minor gross cost.
Already built into the harness (`WalkForwardConfig.hold_band_frac`). Match rebalance
frequency to signal half-life (insider 1–6mo, PEAD ~60d, revisions 1–3mo → monthly-or-
slower with bands). Cap position size at a fraction of ADV and accept the capacity ceiling
as the price of the edge.

---

## 7. The LLM layer — perception only, look-ahead-clean

The LLM is a **feature extractor / probability estimator, never an allocator.** It emits a
falsifiable, timestamped probability ("P(positive earnings surprise next quarter)=0.63");
a separate, dumb, rules-based layer maps calibrated probabilities → positions. This keeps
allocation auditable and lets us score the LLM independently.

**The central validity threat is look-ahead by *training*** (distinct from data-snooping):
a frontier model has memorised the future for any pre-cutoff date. Prompting "pretend it's
2015" does **not** remove it (§11-#15, empirically). Two defenses, both mandatory:
- **Entity-neutering** (§11-#17, Gao-Jiang-Yan): strip firm names, tickers, dates so the
  model can't recall *which* firm/quarter it is, while preserving informational content.
  They provide a statistical test for residual leakage.
- **Point-in-time / vintage weights:** prefer ChronoBERT-style frozen-vintage models
  (§11-#14) over calling a frontier API on historical text; validate on post-cutoff events
  where possible.

**Calibration:** Brier score + reliability diagram + Expected Calibration Error; recalibrate
(isotonic/Platt) if systematically over/under-confident. Pin model version, temperature 0,
log prompt + input hash. The durable LLM edge is extracting *fundamental surprises* ahead of
consensus (§11-#17), not guessing price direction. The event ledger (`events/ledger.py`,
already built + tested) is the instrument that scores these calls forward.

---

## 8. What we reuse vs. build

Governing rule inherited from aegis-finance: **patterns re-implemented, not vendored** —
except a few license-clean shared primitives. As a *separate* module we may import aegis
primitives directly, preserving attribution.

**Reuse from aegis-finance (study/adapt):**
- `docs/CANON.md` — the 11 non-negotiable rules; the Brain inherits them verbatim.
- Validation: `overfitting.py`, `purged_cv.py` (already vendored), `walk_forward.py`,
  `factor_ic.py` (rank-IC), `metrics.py` (Brier + CI) — the readout engines.
- Signal scorers as *references*: `cross_sectional_momentum.py`, `pead_signal.py`,
  `quality_signal.py`, `estimate_revisions.py`, `liquidity_risk.py`, `insider_form4.py`.
- PIT plumbing: the `pit_observations` schema (`as_of` + `observed_at`, read-filtered),
  `pit_score_collector.py`, `forecast_ledger.py` → the pattern our event ledger extends.
- Registry: `experiment_registry.py` — the shared cumulative trial count (base 14). The
  Brain increments the *same* count; it never forks it.

**Borrow from open source (§11 tooling sweep):**
- **Tidy Finance (`py-tidyfinance`)** — the WRDS/CRSP/Compustat cleaning + CCM-linking +
  **reporting-lag and delisting conventions**. Fixes the two deadliest silent look-ahead
  bugs. Study and match its conventions.
- **Open Source Asset Pricing (Chen-Zimmermann)** + **JKP factors** — audited feature
  whitelist; use published priors, not invented features.
- **alphalens-reloaded** (IC/quantile/**turnover** tearsheets) + **empyrical-reloaded**
  (trusted Sharpe/Sortino/DD). **sec-edgar-downloader** (Form-4/8-K, gated by *acceptance
  timestamp*). **skfolio** (BSD, sklearn-native HRP allocator).
- **Avoid:** backtrader (dead, GPL), FinRL (RL overfit on sparse events), vectorbt as a
  parameter search (multiple-testing machine — cost-stress only), `mlfinlab` as a dependency
  (proprietary license — reimplement the ~50-line purged CV instead), OpenBB in the core
  (AGPL).

**Build new:** the Form-4 opportunistic-insider collector + classifier; the SUE/PEAD signal
on Compustat `rdq`+IBES; revision momentum on IBES `statpers`; the FDA sponsor→ticker
crosswalk; the LLM narrative→probability extractor with entity-neutering.

---

## 9. The novel thesis (the moat)

Most ML quant predicts next-month cross-sectional returns — crowded, and largely dead net
of costs (§11-#19). Our novelty is the **fusion under one honest scoreboard**:

> LLM perception turns unstructured events (FDA text, Form-4 filings, 8-Ks, earnings calls)
> into **structured, pre-registered, probabilistic pre-event calls** → a shallow ranker
> blends them with classic microcap factors and inattention conditioners → and the entire
> system is graded by a **growing, timestamped, forward calibration ledger.**

The product is not a backtest Sharpe anyone can fabricate. It is **the ledger** — hundreds
of scored, falsifiable, timestamped predictions that accumulate into a calibration record
no one can fake or overfit. For a solo operator deploying into capacity-constrained
microcaps that funds structurally cannot trade, that record *is* the defensible asset
(§11-#22: the edge lives in microcaps; the solo's advantage is being able to fish there).

---

## 10. Build roadmap (sequenced, each a pre-registered trial)

0. **BRAIN-002** — CRSP hold-band price-factor baseline (pre-registered n=17). The honest
   floor every signal must beat; validates the paper-grade pipeline end-to-end. *(running now)*
1. **BRAIN-003 — Opportunistic insider.** Build the Form-4 collector + routine/opportunistic
   classifier; pre-register; test on CRSP returns with hold-band + net cost. The best-net-
   edge candidate.
2. **BRAIN-004 — PEAD/SUE on `rdq`.** Both SUE flavours; [+2,+60] CAR; with/without microcaps.
3. **BRAIN-005 — Revision momentum**, tested for incremental power over SUE.
4. **BRAIN-006 — FDA event study**, tail-aware, on the hand-verified sponsor→ticker crosswalk.
5. **BRAIN-007 — The ranker fusion.** Combine surviving signals in the shallow ranker;
   full DSR/PBO gate against the (by-then-larger) cumulative count.
6. **LLM narrative spike** — entity-neutered probability calls into the event ledger; score
   forward. Promote only what the live Brier curve earns.

Promotion out of the module = a human commits a `TRIAL-*.md` + registry row in aegis-finance
for forward paper scoring. Nothing here writes to the main repo.

---

## 11. References (curated from the sweep)

**Cross-section / ML**
1. Gu, Kelly, Xiu (2020) *Empirical Asset Pricing via ML*, RFS — shallow>deep; nonlinear
   interactions carry the gains. SSRN 3159577.
6. Jensen, Kelly, Pedersen (2023) *Is There a Replication Crisis in Finance?*, JF — 13
   factor themes replicate OOS across 93 countries; free data at jkpfactors.com.
7. Chen, Zimmermann (2022) *Open Source Cross-Sectional Asset Pricing*, CFR — 200+ audited
   characteristics; openassetpricing.com.
8. (2025) *Transformers or Simple Neural Networks?*, Finance Research Letters — transformers
   don't reliably beat a 2-layer MLP on the cross-section.
5. Hou, Xue, Zhang (2020) *Replicating Anomalies*, RFS — ~65% fail once value-weighted &
   microcaps excluded.

**Overfitting defense**
9. Bailey, López de Prado (2014) *The Deflated Sharpe Ratio*, JPM. SSRN 2460551.
10. Bailey, Borwein, López de Prado, Zhu (2015-17) *PBO / False Strategy Theorem*.
11. López de Prado (2018) *Advances in Financial ML* — purged/embargoed & combinatorial CV.
12. (2026) *Spurious Predictability in Financial ML*, arXiv 2604.15531 — walk-forward alone
    is insufficient.
4. Harvey, Liu, Zhu (2016) *…and the Cross-Section of Expected Returns*, RFS — t>3.0 hurdle.

**LLMs in finance**
13. Lopez-Lira, Tang (2023) *Can ChatGPT Forecast Stock Price Movements?* — edge in small
    stocks/negative news; score post-cutoff text only. arXiv 2304.07619.
14. He, Lv, Manela, Wu (2025) *Chronologically Consistent LLMs (ChronoBERT)* — vintage
    weights remove training look-ahead. arXiv 2502.21206.
15. Glasserman, Lin (2023) *Assessing Look-Ahead Bias in GPT Sentiment* — prompt-level date
    constraints are empirically insufficient.
17. Gao, Jiang, Yan (2025) *A Test of Lookahead Bias in LLM Forecasts* — entity-neutering +
    a statistical leakage test. arXiv 2512.23847. Zhang, Zhou (2024) *EAR-AI* — LLM edge is
    predicting the fundamental *surprise*.

**Event studies**
18. Cohen, Malloy, Pomorski (2012) *Decoding Inside Information*, JF — opportunistic vs
    routine; ~82 bps/mo value-weighted. NBER w16454.
19. Chen, Velikov (2023) *Zeroing in on the Expected Returns of Anomalies*, JFQA; Novy-Marx,
    Velikov (2016) *A Taxonomy of Anomalies and Their Trading Costs*, RFS — net ~4-10 bps/mo;
    turnover is destiny.
20. Martineau (2022) *Rest in Peace PEAD* — dead for liquid names since ~2006, microcap-only.
21. openFDA Drugs@FDA API; biotech PDUFA event-study literature — binary catalyst, fat tails.
23. Da, Engelberg, Gao (2011) *In Search of Attention*, JF; Hirshleifer-Lim-Teoh (2009) —
    limited attention is the mechanism behind the drift.
24. Asness, Frazzini, Israel, Moskowitz, Pedersen (2018) *Size Matters, If You Control Your
    Junk*, JFE — interact size with quality.

**Tooling:** Tidy Finance (py-tidyfinance), Open Source Asset Pricing, JKP factors,
alphalens/empyrical-reloaded, sec-edgar-downloader, skfolio. Avoid: backtrader, FinRL,
vectorbt-as-search, mlfinlab-as-dependency, OpenBB-in-core.
