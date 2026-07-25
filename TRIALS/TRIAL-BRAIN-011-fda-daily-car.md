# TRIAL-BRAIN-011-fda-daily-car — the pre-declared daily successor to BRAIN-006

**Registered:** 2026-07-25 (UTC), BEFORE the run. **Provenance:** BRAIN-006
(monthly resolution) = REJECT; the daily-CAR successor was pre-declared in
that adjudication as the only admissible retry class. NEW registration, not
a rerun. Crosswalk: v2 overrides sheet — agent-verified (3 chunked batches),
**Murat spot-check DONE 2026-07-25**, plus programmatic validation same day
(134 rows, 0 unparseable dates, 0 overlapping validity windows, 0 listed
rows missing tickers).

## Hypothesis
FDA NDA/BLA original-approval announcements are followed by a positive
post-announcement drift in the sponsor's stock over the T+1..T+20 trading-day
window (underreaction class; monthly cadence provably washed it out).
Horizon-first tags: source = filings/events; decay = days-weeks; turnover
class = N/A (event study, not a book); role = event-picker candidate.

## Frozen spec (one run)
- **Events:** `fda_crosswalk.parquet` rows with permno, NDA/BLA ORIG only
  (2,742 candidates), deduped to one event per permno per 30 calendar days
  (earliest kept; drops counted). Estimation feasibility: ≥60 valid return
  days in the estimation window, else dropped-with-count.
- **Explore events:** approval_date 2002-07-01..2018-12-31.
  **Confirm events (HELD OUT): 2019-01-01..2024-11-30** — read only by the
  confirm step below, gated on the explore bar.
- **Market model:** daily CRSP returns (`dsf_pharma_2002`), market = SPY
  (auto-adjusted closes, disclosed). α, β estimated OLS on trading days
  [−120, −30] relative to the event. AR_t = r_t − (α + β·r_m,t).
- **Primary statistic:** mean CAR(+1,+20) across events, cross-sectional t.
  Independence caveat disclosed (calendar clustering modest post-dedupe).
- **Descriptive (never the claim):** AR(0), CAR(−1,+2), CAR(+1,+5).
- **Exploratory secondary arm (no bar, round-4/5 framing):** pre-event
  attention = mean volume[−5,−1] / mean volume[−60,−11]; explore events
  split at the median; CAR(+1,+20) reported low vs high attention.
- **Diagnostics:** priority vs standard review; size split (median pre-event
  dollar volume).
- **Decision rule (frozen):** explore PASS iff mean CAR(+1,+20) > 0 AND
  t ≥ 2.0 → the confirm step runs (same spec byte-identical on held-out
  events; confirm PASS iff mean > 0 AND t ≥ 1.0 — power note: roughly half
  the explore N). Explore fail → REJECT, family closes at daily resolution
  too (NEGATIVE_RESULTS entry). |t| ≥ 7 anywhere = bug alarm, book
  inspection before any verdict.

## Result (one run 2026-07-25 — never edited)
`data/factory/trial011_fda_daily_car.json` (+ per-event parquet). Explore:
748 events after 30d dedupe (−153 disclosed), 500 usable (247 dropped
no-data/window — conglomerate sponsors outside the pharma-SIC dsf slice;
1 dropped est-obs).

### Verdict: **REJECT** (frozen bar: mean > 0 AND t ≥ 2.0; got t = 1.45)
The confirm gate never opened — 2019-2024 events remain unread.

- CAR(+1,+20) = **+2.1%, t 1.45** — economically large if real, but
  biotech cross-sectional noise swamps it. The whole drift is in the first
  five days: CAR(+1,+5) = +2.1% (t 1.52); days 6-20 add NOTHING.
- AR(0) = +0.43% (t 2.04) — a real same-day reaction exists (descriptive,
  not tradeable at close-to-close grade).
- **Attention arm (exploratory): OPPOSITE of the proposed gate.**
  High-attention events +3.59% vs low-attention +0.60% — the "low-attention
  drift" hypothesis fails its first data contact here (round-4's warning
  that the Chemmanur extrapolation was shaky proved right).
- Size: small half +4.0% (t 1.39) vs large half +0.2% — micro-concentrated,
  exactly where BRAIN-006 suspected it and exactly where our cost model has
  no faith. Priority +0.6% vs standard +2.9% — against anticipation
  intuition; consistent with priority approvals being better pre-priced.

**The FDA approval-drift family is CLOSED at both monthly AND daily
resolution.** What remains admissible: the FORWARD-only PDUFA ledger
(different event class, different clock — Brier-scored calls, first event
2026-07-26) and any CRL/AdCom event design as a NEW registration.
