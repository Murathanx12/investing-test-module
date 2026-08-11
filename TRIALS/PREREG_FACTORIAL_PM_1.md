# PREREG — FACTORIAL-PM-1: picks × management, his claim as a matrix

**Registered** 2026-08-11, NIGHT-13, **before any cell is computed.**
**Parent** CONVICTION-REPLAY-1 (UNRESOLVED, MDE 80pts) and
COUNTERFACTUAL-EXITS-1. **This trial ACCRUES ONE ARM** — it can confirm the
direction of a product-defining claim, so it counts.

**The claim under test (Murat, verbatim):** "my portfolio with good
timing/management would be a great winner with the stock picks."

## 1. Design — 3 evaluable books × 4 managements, identical data and dates

Window **2025-11-07 → 2026-08-10** (the sheets' window), prices =
`backend/data/conviction_prices.csv` (frozen CSV, APLT/SLNO handled per
CONVICTION-REPLAY-1's corporate-action machinery; synthetic names excluded
from daily-path statistics, included in period returns).

**Books:** B1 his 13 picks · B2 his 48 watchlist non-picks · B3 random-13
drawn from the 61-name pool (1,000 seeded draws; the CELL value is the
distribution, reported as median with p05–p95 — never one draw).
**B4 funnel candidates is registered as NOT_EVALUABLE in this window** — the
funnel ran in Aug-2026, so replaying it from Nov-2025 is look-ahead by
construction; it enters the matrix as a forward cell only, from 2026-08-11.
Recording the refusal is the point (a check that cannot run honestly is not
run).

**Managements, all mechanical, all parameter-frozen BEFORE this run:**
- **M1** equal-weight buy-and-hold (drifting; the CONVICTION-REPLAY-1 basket).
- **M2** vol-targeted: book-level exposure `w_t = min(1, 0.20 / σ_book(63d))`,
  daily, one-day lag, cash earns 0, costs 10 bps one-way on exposure changes.
  Parameters are `exit_engine` defaults frozen long before tonight
  (`vol_target_annual=0.20`, `vol_lookback_days=63`) — nothing tuned here.
- **M3** kill-condition-managed: positions exit when their §0 kill condition
  fires, **only where the condition is mechanically checkable point-in-time**
  from data on hand (a checkability audit runs FIRST; if fewer than 50% of a
  book's names are checkable the cell is `REFUSED_NOT_MECHANIZABLE` — thesis
  text is not silently converted into invented rules).
- **M4** full mechanical PM: the mirror lane's frozen rules (monthly HRP,
  5% drift trigger, 5 bps + 1 bp costs, max single name 25% —
  `book_lanes.yaml` mirror config, frozen 2026-06).

**The as-traded comparator for B1** comes from TRANSACTION-ENSEMBLE-1's Q4
bounds (a RANGE, never a point). If the ensemble reports `DATA_NEEDED` for Q4,
the as-traded column prints the range with that label.

## 2. Hypotheses, registered

- **H1 (his claim, direction):** B1×{M2 or M4} terminal wealth > B1×as-traded
  upper bound. Tested as a paired difference on the same price paths (§18),
  block-bootstrap (21td circular) SE, measured 80%-power MDE beside it (§19).
- **H2 (interaction):** the management effect (M2−M1, M4−M1) is LARGER on B1
  than on B3's distribution — a difference of differences with its own SE
  (§18). Registered expectation: NOT detectable at this sample.
- **H3 (the exposure story):** M2 reduces B1 max drawdown vs M1 by ≥5pp in the
  war sub-window (2026-06-04 → 2026-07-29) — descriptive receipt, n=1.

**Honest prior:** one nine-month window; CONVICTION-REPLAY-1's selection MDE
was 80pts. Management effects are paired-on-path so their MDEs will be far
smaller — but likely still above 9-month effects. Registered expectation:
**H1 resolvable in direction only if the effect is large; H2 UNRESOLVED.**

## 3. Decision rule, frozen

| outcome | verdict |
|---|---|
| H1 holds net of costs with the paired difference ≥ its own measured MDE | `CONFIRMED_IN_DIRECTION` — the product pitch ("bring your ideas, the engine manages them") gains its first licensed receipt; still NO alpha claim, NO skill claim |
| H1 sign positive but below MDE | `UNRESOLVED` |
| H1 sign negative | `DIRECTION_REJECTED` on this window — reported, with the window's one-bull-path caveat |
| any cell's inputs contaminated (per CONVICTION-REPLAY-1 defect class) | cell VOID, investigated before any number is reported |

## 4. What this may NOT do

- No annualization of a 9-month window into a headline.
- No cell promotes a strategy, seeds a lane, or arms anything.
- B3's distribution may not be collapsed to its mean alone (p05–p95 printed).
- The matrix may not be summarized without each cell's MDE beside it (§19).
- This does not and cannot grade Murat's skill (24-month rule; one window).

Receipts to `aegis-finance/docs/NIGHT13_FACTORIAL.md`.
