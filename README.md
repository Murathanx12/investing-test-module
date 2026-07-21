# Aegis Investor Brain

A **calibrated hypothesis engine** for US equities — not a neural net that mines prices.
It engineers economically-grounded event signals, tests each as a pre-registered
hypothesis on paper-grade data, and — crucially — keeps a **forward, Brier-scored
calibration ledger** that is the only thing allowed to earn conviction. Backtests set
priors; the forward record is the product.

See **METHODOLOGY.md** for the full cited blueprint, **ROADMAP.md** for the architecture,
**INTEGRATION.md** for how this attaches to `aegis-finance`, **STATUS.md** for live state.

## Why this design

Iterating a model over history until it beats the S&P is a fraud generator (Bailey–López
de Prado False Strategy Theorem). So "learning" happens in three firewalled loops: a
shallow ranker refit per era (walk-forward, purged CV), a per-trial scientist loop
(pre-register → test once → publish pass/fail → deflate by cumulative trials), and a
forward calibration loop (live probability calls scored at maturity). Shallow beats deep
at this signal-to-noise (Gu-Kelly-Xiu); costs, not signal discovery, are the binding
constraint (Chen-Velikov: the average anomaly nets ~4-10 bps/mo).

## Results so far (all pre-registered, deflated, leak-checked)

| Trial | Signal | Verdict |
|---|---|---|
| BRAIN-000/001 | GKX price factors (EODHD) | REJECT — surfaced data poison + turnover drag |
| BRAIN-002 | GKX price factors (CRSP, paper-grade) | REJECT — dead net of 25 bps |
| **BRAIN-003** | **Opportunistic insider buys** | **First NON-REJECT** — survives kill conditions in large/mid caps (+17 bps/mo vs EW t=1.40; FF5+UMD α +102 bps/mo t=1.89); null in microcap. Weak positive prior; graduates to the forward ledger. |
| BRAIN-004 | PEAD / earnings surprise | REJECT — strong gross in microcap, dead net of costs |
| BRAIN-005 | Analyst revisions | REJECT — leak bar caught a benchmark bias; the "edge" was covered-vs-full-universe, not signal |
| BRAIN-007 | Fusion of survivors | NOT RUN — only 1 signal (insider) survived; fusion needs ≥2 |

**One survivor so far: opportunistic insider (large/mid), a weak positive prior.** Every
other signal is an honest, leak-checked REJECT — which is the machine working: it kills bad
ideas so the eventual forward record can be trusted. The insider signal is packaged as a
promotable scorer (`aegis_brain/export.py`); conviction is earned forward, not on backtest.

The forward ledger (`ledger/forward_calls.jsonl`) holds live pre-registered PDUFA calls,
Brier-scored via `scripts/ledger_score.py` as they mature.

## Layout

```
aegis_brain/
  config.py            paths + constants
  discipline/          DSR / PBO / PSR + purged CV (Bailey & López de Prado)
  data/                CRSP paper-grade panel (real delisting) + EODHD loader + WRDS conn
  events/              SEC insider collector, FDA feed, event ledger, realized returns, crsp_link
  signals/             price factors, SUE/PEAD, revisions, insider scorer (promotable)
  combiner/ranker.py   GBM + shallow-NN rankers (GKX: shallow > deep)
  harness/             walk-forward runner, flag-portfolio, ADV costs, FF5+UMD benchmark
  gate/                adoption gate (DSR vs cumulative trials, PBO) + local registry
  llm/                 DeepSeek perception layer — extraction only, forward-only, never allocates
  export.py            promotion-bundle generator (the firewall to aegis-finance)
TRIALS/                pre-registration docs — written BEFORE any run
ledger/                the forward calibration record (the product)
```

## Setup

```
python -m venv .venv
.venv\Scripts\pip install -e .[full]
.venv\Scripts\python -m pytest            # fast suite
```

Data (WRDS/CRSP/Compustat/IBES, SEC, FDA) is licensed and git-ignored under `data/` —
never committed. WRDS pulls go only through `aegis_brain/data/wrds_conn.py`.

## The seven rules (full: ROADMAP.md §2)

1. Pre-register before touching data. 2. One run per hypothesis. 3. Two-arm (leak bar on
gross excess). 4. Deflated numbers only. 5. Survivorship-honest (real CRSP delisting).
6. The LLM never allocates. 7. Nothing here writes into aegis-finance — promotion is a
human commit of a reviewed bundle.
