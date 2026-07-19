# Aegis Investor Brain (research module)

The research lab for the Aegis Investor Brain arc. See **ROADMAP.md** for the full
architecture, constraints, and phase plan.

This module is a **read-only consumer** of the main project at
`C:\Users\mrthn\aegis-finance` (EODHD price archive, discipline canon). It never writes
into the main repo, its PIT store, or its experiment registry. Promotion of a surviving
candidate = a human commits a `TRIAL-*.md` in the main repo and the forward clocks score it.

## Layout

```
aegis_brain/
  config.py               paths + constants (EODHD archive location, panel window)
  discipline/             vendored DSR/PBO/PSR + purged CV (Bailey & López de Prado)
  data/eodhd_panel.py     read-only loader over the 50,462-history EODHD archive
  signals/                hand-designed, economically grounded features (L2)
  combiner/ranker.py      GBM + shallow-NN cross-sectional rankers (L3)
  harness/runner.py       expanding-window walk-forward w/ costs + turnover (the honest loop)
  gate/                   adoption gate (DSR vs cumulative trials, PBO) + local trial registry
TRIALS/                   pre-registration docs — written BEFORE any run
tests/                    fast suite
```

## Rules (short form — full version in ROADMAP.md §2)

1. Pre-register before touching data. 2. One run per hypothesis. 3. Two-arm tests.
4. Deflated numbers only. 5. Survivorship-bound every backtest until WRDS.
6. LLM never allocates. 7. Never write into aegis-finance.

## Setup

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest tests -q
```
