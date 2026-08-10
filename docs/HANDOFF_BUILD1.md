# HANDOFF → BUILD-1

Written 2026-08-10 at the end of NIGHT-9, for the session that executes the
BUILD-1 package. Read this before `docs/BUILD1/BUILD1_OPUS_PROMPT.md`, because
some of B1–B3 is already built and you should extend it rather than start over.

---

## The mandate has changed, and it is binding

Aegis is now **three systems, not one**:

| system | question | effort |
|---|---|---|
| Research Lab | "what evidence do we actually possess?" | ~25% |
| **Portfolio Manager** | "given this book, this cash and this goal, what do I do today?" | ~55% |
| Opportunity / Intelligence | "where has the expected payoff changed most today?" | ~20% |

Neither is subordinate. Research gates set **reliability weights** on signals;
they do **not** block clearly-labelled OBSERVATIONAL information from reaching
the PM. The LLM never sizes; the engine never auto-trades; every real-money
action is Murat's, attended. Three constraints attached as binding by the brain:

1. **Stretch targets are goals, never forecasts, and the ruin number prints
   beside the dream number in the same font.** Moonshot mode is allowed;
   `P($100k+)` without `P(<$20k)` next to it is not.
2. **Unvalidated signals may flow, but wearing their label** — VALIDATED (with
   the receipt) or OBSERVATIONAL (reliability weight attached, not yet tested).
   The referee and claim-checker audit PM output exactly like research verdicts.
3. **The lab does not die — it becomes the PM's immune system.** It is the only
   reason we know the monthly panel lied, that G7 could not price impact, and
   that our own receipts carried a units bug.

---

## What is ALREADY BUILT — do not rebuild these

Committed to `aegis-finance` `main` at **`0c3f170`**. Write-up:
`aegis-finance/docs/PORTFOLIO_MANAGER_v1.md`.

| BUILD-1 item | status | where |
|---|---|---|
| **B2** position objects + book | **partly done.** `backend/data/murat_book.yaml` — ticker, dollars, cost basis, entry date, thesis, kill condition, plus wealth targets, sizing mode, watchlist and a `closed` list. Marked `confirmed: false` | `pm_engine.load_book` |
| **B3** Daily Portfolio v1 | **runs end to end on live data.** `python scripts/morning_brief.py`, `GET /api/pm/daily`. Portfolio state, wealth header with downside, per-holding BUY/ADD/HOLD/TRIM/SELL with dollars, threats, opportunity radar, replacement table | `pm_actions.daily_brief` |
| **B3** replacement edge | **done.** Names which holding funds which buy, net of a 40bp round trip | `pm_actions.replacement_edge` |
| **B4** Analyst Alpha v0 | **done, revisions over levels.** upside × breadth × freshness × 3m rating drift × 90d net upgrades, minus itemised penalties for dispersion, binary event, illiquidity, sub-$5 | `pm_engine.analyst_alpha` |
| **B6** goal-seek modes | **done.** growth / high_growth / moonshot change position limits ONLY. 20k paths, 12 monthly steps, one common factor at ρ 0.35 | `pm_actions.simulate_wealth` |
| portfolio memory | **done.** Append-only JSONL freezing price, target, dispersion, coverage, drift, thesis, kill condition per instruction; resolutions are new rows, never edits | `pm_journal` |
| tests | 26, offline, on the decision arithmetic | `backend/tests/test_pm_engine.py` |

**What that means for your night:** B3's acceptance criterion — "take a book and
output exact BUY/ADD/HOLD/TRIM/SELL with dollar amounts" — is **already met**.
Your job is to make it *right*, not to make it *exist*. The gaps below are the
real work.

---

## What is NOT built, in the order it matters

### B1 — the analyst data spine (**this is the real gate, and it was never run**)
v1 reads analyst data through **`backend/services/analyst_intelligence.py`,
which is Yahoo only**. That gives current consensus target (low/median/high),
consensus rating, a 4-month rating-trend table and ~30 recent rating actions
with firm and date. It gives **no target history**, so:

- `rating_drift_3m` is computed from Yahoo's 4-row trend table, not from real
  revisions;
- **ΔTarget over 7/30/90 days does not exist yet** — the single most important
  signal in the mandate is currently approximated by rating counts;
- there is **no analyst-level identity**, so the reliability database has
  nothing to key on.

Keys present in `.env` and unused by the PM: **FINNHUB, FMP, POLYGON,
ALPHA_VANTAGE, EODHD, ALPACA**. B1 must call each endpoint and **print the
status code and a sample payload** — the standing rule; no "unavailable" claim
without a printed status code. Target *history* is the hard part; measure what
each free tier actually returns before designing anything on top of it.

### B5 — catalyst calendar
**Nothing exists.** No earnings dates, no PDUFA, no lockups, no offerings. For a
book with three pre-revenue clinical names this is the largest single gap in the
product — bigger than anything in the scoring.

### B7 — the reconstruction dataset
**Not started.** The source is `c:\Users\mrthn\Downloads\stock reseacrh old
files\market research (legacy)\stock (1).pdf` — 12 pages, dated 2025-11-07 and
2026-01-13, containing his portfolio and a 34-name watchlist with **entry price,
mark, 12-month analyst target and consensus rating for every name**. That is a
dated snapshot and must be preserved as historical observation, never refreshed
with current data. It is the highest-value dataset in the programme because it
is his actual process, and it is testable.

### The two assumptions that carry the whole product
- **`TARGET_HAIRCUT = 0.35`** — the fraction of analyst implied upside carried
  into the base case. Every probability the PM prints depends on it and it is
  fitted to **nothing**. Once the journal has ~50 resolved instructions, fit it
  and retire the assumption.
- **`DEFAULT_CORRELATION = 0.35`** — real correlation rises exactly when it
  hurts, so this understates a crisis.

---

## Research side: what NIGHT-9 left open

1. **N1B AMENDMENT 2 — the label test.** Registered before compute. Every
   rank-based axis says the learned rankers are better and the book still earns
   less; the remaining suspect is that the label is a demeaned **log** return
   while a long-only book is paid in **simple** returns. If the receipt key
   `label_test` exists in `runs/NIGHT9/N1B_WHERE_DOES_THE_IC_LIVE.json`, read
   it; if not, rerun `scripts/n1b_label_test.py`. **This is the highest-value
   research item in the programme** — if it lands, the conclusion is not
   "learning failed" but "we were grading on the wrong exam", and it invalidates
   the way ordering has been measured here.
2. **The phase axis is not trustworthy.** Twelve phases returned an identical
   excess CAGR (range 0.00 pt/yr), contradicting NIGHT-7's 2.45 pt/yr date-luck
   range. Either `run_book(phase=...)` is not staggering or the invocation is
   wrong. No phase claim may be made until this is resolved.
3. **G8 is built and calibrated but never pointed at the book.** Prereg
   `TRIALS/PREREG_G8_IMPACT_AND_CAPACITY.md`, 15 invariants green,
   `scripts/g8_impact_and_capacity.py` ready to run. **Explicitly BACKGROUND**
   per Murat: institutional capacity does not help a $45k account. Until it
   runs, every capacity number stays a delay-only lower bound (CANON §17).
   The personal-PM execution bar is different and much easier: *can $500–$10,000
   move without the spread eating the thesis* — `pm_engine._liquidity` already
   answers it crudely and should be sharpened, not replaced by G8.
4. **Not run and displaced by the pivot, not by a finding:** PF8 trigger
   confound (path-geometry placebo), T4b coverage matrix, N3b half-year placebo.

---

## Standing rules that did not change

Pre-register before compute; the power check may refuse and that refusal is a
result. Taxonomy v2; UNRESOLVED is legitimate. CANON §13–17 apply — masking a
name is not masking a date; turnover-sensitive claims go through G7; a cost
comparison quotes drag on average NAV and bps of traded, never dollar totals;
DSR is not a posterior; **an execution number carries the model that produced
it**. No lane or `paper_nav` writes. Holdout (2023-01+) locked. Keys env-only.
A "blocked" claim requires a printed status code. Run
`scripts/lint_prereg.py` before registering anything, and the verdict referee
over your own verdicts before STATUS.

**New:** use `aegis_brain/pf/stats.py`, not a hand-rolled `paired()`. It is
typed, and the annualising arithmetic is unreachable from the IC path.

---

## The two inputs only Murat can give

1. **His actual holdings** — tickers, **shares**, **cost basis**, **cash**.
   Everything the PM prints in dollars is a placeholder until then, and the
   banner says so on every run.
2. **The trade history** behind the 25k→45k year, for B7.

Treat both as private operational data: gitignored, per
`docs/BUILD1/PRIVATE_DATA_POLICY.md`.
