# Attaching the Investor Brain to aegis-finance

How the finished brain module plugs into the main `aegis-finance` project. The design
rule is a one-way firewall: **the brain never writes into aegis-finance.** It produces
reviewable artifacts; a human commits them across the boundary.

## 1. What the brain hands over

Three things, in increasing order of value:

1. **Signal scorers** — PIT-safe callables `score(ticker: str, as_of: str) -> float`,
   the exact shape aegis-finance's `pit_score_collector` closure expects. Registered in
   `aegis_brain/export.py::SIGNALS`. Promoted only after a signal SURVIVES its
   pre-registered kill conditions (not after it clears the deploy gate — the gate is
   likely unclearable on backtest; the forward ledger earns conviction).
2. **The forward calibration ledger** (`ledger/forward_calls.jsonl`) — the growing,
   timestamped, Brier-scored record of falsifiable event calls. **This is the product.**
3. **Promotion bundles** (`export/<signal>/`) — a draft `TRIAL-*.md`, a registry row, the
   signal spec, and a ledger snapshot, ready for a human to commit into aegis-finance.

## 2. The promotion protocol (the only path across the firewall)

```
# in the brain module:
.venv\Scripts\python -m aegis_brain.export      # writes export/<signal>/ bundles
```
Then a human:
1. Reviews `export/<signal>/TRIAL_DRAFT.md` + `registry_row.json`.
2. Commits them into `aegis-finance/docs/TRIALS/` and the main registry (`record_trial`).
3. Wires the scorer (`signal_spec.json::scorer_ref`) into a `pit_score_collector`.
4. The forward paper clocks score it. Conviction accrues forward — never from the backtest.

The brain has no write access and no code path into aegis-finance; step 2-3 are manual by
construction (CANON §7).

## 3. The signal contract

```python
from aegis_brain.signals.insider_scorer import opportunistic_insider_score
opportunistic_insider_score("KMI", "2016-06-30")   # -> float (distinct opportunistic buyers, trailing 12mo)
```
- **PIT-safe:** uses only filings observable by `as_of` (`filing_date <= as_of`). Never look-ahead.
- **Never raises**, returns `0.0` on unknown/unmatched — safe inside a collector loop.
- **Coverage:** bundled panel spans 2006-2024; for live dates, wire to the per-ticker
  Form-4 feed (aegis-finance `insider_form4.py` + our `classify_routine_opportunistic`) —
  same classifier, same filing-date stamping. Documented in the scorer module.

## 4. What is promotable now

| Signal | Status | Prior (deflated) |
|---|---|---|
| `opportunistic_insider` | ✅ survived kill conditions (BRAIN-003) | large/mid +17 bps/mo vs EW (t=1.40), FF5+UMD α +102 bps/mo (t=1.89); null in microcap. Weak positive prior; does not clear deploy gate. |
| PEAD/SUE, revisions, fusion | see TRIALS/ — promoted only if they survive | — |

The LLM perception layer (`aegis_brain/llm/`) feeds the ledger with probability calls; it is
**forward-only** and never allocates — it is not a promotable allocator, by design.

## 5. Install / import

```
pip install -e .            # from the module root (pyproject.toml)
# or path-import: the module is a read-only sibling of aegis-finance
```
Optional lanes (`pip install -e .[full]`): WRDS pulls, LightGBM, yfinance, tests.

## 6. Firewall invariants (must hold)

- The brain reads aegis-finance's EODHD archive and discipline canon; it writes **nothing** there.
- WRDS/licensed data stays in the brain's git-ignored `data/`; never committed, never crosses over.
- Promotion is a human commit of a reviewed bundle. No automated bridge exists or should be built.
