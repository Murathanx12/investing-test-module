# PREREG — TRIAL-PF5-REBAL-FRONTIER-1

**Registered** 2026-08-09, before any compute at frequencies other than the two
already banked. **Branch** `factory/night-5`. **Family** PF (portfolio factory).

## 1. Why this exists

NIGHT-4's most useful result was that the margin lived in implementation, not in
the signal: annual rebalancing under era-appropriate costs dominated the
registered monthly/flat-25 spec on every axis at once. That result rests on
**two** points of a curve (quarterly 3.95 % t 2.32, annual 4.40 % t 2.69) plus a
non-comparable third (monthly under *flat* 25 bps). Two points cannot
distinguish a frontier from a fluke.

External review's charge, adopted: *"annual won — but is it a smooth optimum on
an implementation frontier, or the lucky point of a small grid?"* If annual is a
spike, the honest reading is that we selected a rebalance frequency on 482
months of the same data that selected the strategy, and the shippable config is
not established.

## 2. Design

Same book definition throughout (`PF-PROF-COMPOSITE-150`, small segment,
top 150, EW, incumbency band 3×, min_names 100, 1963-07 → 2022-12).
**Only `rebalance_months` varies.** Costs are era-appropriate
(`era_cost_frame`, mechanical tick floor: $1/8 → 1997-06, $1/16 → 2001-03,
$0.01 after, base 25 bps) at **every** point, so the curve is like-for-like.

Grid: **{1, 3, 6, 12, 18, 24} months** — six points, all registered here.

Reported at every point: net excess CAGR vs CRSP VW, NW(12) t on the monthly
excess, FF5+UMD alpha and its t, **incremental alpha vs the EW eligible
universe** (NIGHT-4's primary instrument) and its t, one-way annual turnover,
realized cost drag in bps, max drawdown, and the pre-/post-2001 era split.

**No extension to daily or weekly.** The panel is monthly; a weekly frontier
would be manufactured, not measured. Recorded here rather than discovered later.

## 3. Primary metric and decision rule (frozen)

The deciding number is the **shape of the incremental-alpha t across the grid**,
not any single point.

Let `t(k)` be the NW(12) t on incremental alpha at frequency k months.

* **SMOOTH FRONTIER** — the shippable config stands — if `t(k)` is
  **single-peaked** over the grid AND the peak is not isolated: the two
  neighbours of the argmax are each within **1.0 t-units** of it. Under this
  outcome the frequency choice is a broad plateau and choosing 12m over 6m or
  18m costs little, which is what makes it defensible.
* **LUCKY POINT** — the annual choice is **withdrawn** and the shippable config
  reverts to being undetermined — if the argmax exceeds **both** neighbours by
  more than **1.0 t-units**, i.e. the win does not survive moving one grid step
  in either direction.
* **MONOTONE** — if `t(k)` is monotone increasing across the whole grid, the
  data say "trade as rarely as possible" and the boundary at 24m is not the
  optimum but the edge of the grid. The honest report is that the frontier is
  **not interior** and the grid does not contain the answer. No extension of the
  grid tonight — extending on seeing the boundary bind is the exact degree of
  freedom this document exists to remove.

Ties and non-single-peaked shapes that are not monotone read **UNRESOLVED**.

**The 1.0 t-unit threshold is frozen now** and is not a significance test; it is
a stability requirement. It was chosen before seeing four of the six points,
as roughly half the gap between the two banked points' t values (2.69 − 2.32 =
0.37) scaled up so that a "plateau" claim means something.

## 4. House prediction, registered before compute

Recorded so it can be scored, at the risk of being wrong in public:

* **P1** — the frontier is **smooth and single-peaked**, peak at 6m or 12m.
  Confidence 0.6.
* **P2** — `t(1m)` under era costs is **below** `t(3m)`; the monthly spec's
  120 bps cost drag is the binding cost and era costs make it worse pre-2001,
  not better. Confidence 0.75.
* **P3** — 24m turnover is **not** half of 12m turnover. Forced turnover from
  delisting and eligibility exit does not scale with the rebalance clock, so
  the turnover savings flatten out. Confidence 0.7.
* **P4** — 18m and 24m excess CAGR are **lower** than 12m: at some horizon the
  book is holding names whose profitability rank has decayed, and staleness
  costs more than the trading it saves. Confidence 0.55.
* **P5** — the argmax of raw excess CAGR and the argmax of incremental-alpha t
  are **not the same frequency**. Confidence 0.5.

## 5. What this trial may NOT do

* It may not re-open the strategy definition. Only `rebalance_months` moves.
* It may not extend the grid on seeing a boundary bind.
* It may not be quoted as evidence that the strategy works. Every point in the
  grid inherits NIGHT-4's spanning result: the book is small-cap profitability,
  and this trial measures only how expensively we harvest it.
* Its six points enter the programme-wide testing denominator
  (`aegis_brain/pf/ledger.py`) regardless of outcome.

## 6. Cost

Deterministic, no LLM calls, ~6 × 6 min of panel compute. This is the cheapest
question on the night's list and the one most likely to invalidate a decision
already taken.
