# STATUS — handoff after NIGHT-7 (2026-08-10)

## Where the code is

* `main` (Aegis module) — **night-5 and night-6 merged** (night-5 was an ancestor
  of night-6, so one merge carried both). Suite green post-merge.
* `factory/night-7` — **UNMERGED**, awaiting Murat's read. 495 tests green
  (470 + 25 new firewall tests).
* `aegis-finance` `main` — CANON amended with four new rules (§12–§15) and six
  new closed rabbit holes.
* Holdout unread throughout. Nothing promoted. No lane seeded, no flag flipped,
  no `paper_nav` touched, no keys changed. LLM spend this night: **$0** (no
  extraction experiments ran — T6 was refused by its own power check).

## What NIGHT-7 found

Full detail: `docs/NIGHT7_VERDICT_2026-08-10.md`. Receipts in `runs/NIGHT7/`.

**1. The exit layer is not where the money is either.** Five registered exit
arms, entry held fixed on the banked book, all fully invested at 150 names.
Reconciliation exact (max abs monthly diff **0.0** vs the untouched banked path).
**No arm reaches paired |t| ≥ 2.0** — max is 1.24; best-worst spread 0.79%/yr;
arm correlations 0.983–0.998. All five UNRESOLVED, with MDEs 0.41–1.21%/yr
printed beside them.

**2. The arm the monthly panel ranked FIRST loses 3.08%/yr in reality.** The
trailing stop showed +0.34%/yr net (and the best gross, +5.74%) while trading
2.7× as much. Under G7's daily simulator on the same spine it lands **3.08%/yr
behind** the baseline at $1m and pays **$743,599 more in costs over 23 years —
74% of starting capital**. The monthly panel understated the churn penalty by
**2.43 pts/yr**, *the same magnitude NIGHT-6 measured for the monthly clock*.
Two independent turnover increments, one understatement — the panel's churn bias
is now a calibrated property, and it is CANON §15.

*A silent-fragility trap was caught first:* `holdings_out` flagged only full
rebalances, so exit-driven interim trades were invisible to G7. The highest-churn
arm would have been measured on the **baseline's** trade schedule and its cost
would have vanished silently.

**3. Rebalance-date luck is worth a 2.45 pt/yr range — and is free to remove.**
Twelve staggered annual cohorts: individual clocks span **+2.24% to +4.69%**
excess CAGR (σ 0.80%/yr). The ensemble lands at the mean (+3.48% vs +3.43%, gap
+0.04% — no free lunch) at **unchanged turnover** (0.468). Date luck is **three
times** the entire spread across all five exit rules.

*The first run of this was wrong and says so in the receipt:* shifting
`first_month` does not stagger the book (the small segment cannot seat 150 names
until 1982, so all 12 cohorts collapsed onto one date). A real clock phase was
added, plus a guard that refuses to report an ensemble whose cohorts share a
first-trade date.

**4. The survivor does not survive trial-count accounting. Published anyway.**
Deflated Sharpe on the excess series, with V[SR] estimated from **our own
graveyard** and reported under three assumptions rather than one. **Under every
assumption, at every N ≥ 5, it fails DSR 0.95.** Under the most
strategy-favourable defensible assumption (all trials pure noise), at N=179:

> **DSR = 0.549.** The survivor's annualised excess Sharpe is 0.449; the expected
> maximum of 179 pure-noise draws over the same window is 0.431. **We beat
> noise-selected-179-times by 0.018 of Sharpe.**

**CORRECTED after external review (NIGHT-7B):** the original wording here —
"P(true excess Sharpe > 0) ≈ 0.55" — was **wrong**. DSR is not a Bayesian
posterior over true alpha; it is a probabilistic-Sharpe statistic against a
selection-adjusted benchmark Sharpe. The claim the arithmetic supports is:
**the historical survivor does not establish unique alpha once the search is
accounted for.** And DSR is **not** re-armed as a kill gate — GATE-M1 measured
DSR ≥ 0.95 as nearly powerless. `T4b` (empirical selection bootstrap) is
registered to replace arguing about N.

**5. The firewall is code, not a design note.** `aegis_brain/firewall/`, 25 tests.
Layer 1 refuses outcome-shaped context and unstamped extractions; the crossing
(`LearningSample`) rejects outcomes not strictly after the extraction's `as_of`,
and `to_layer1_payload()` exists solely to raise; Layer 3's `set_weight()` raises
and its vetoes are Brier-scoreable.

**6. A citation gate that corrected US, not just them.** 20 claims read at source.
The reviews' failure mode was **not fabrication** — it was correctly quoted
numbers stripped of the qualifier that decides whether they transfer (a
long-short alpha quoted to a long-only book; a buy-and-hold-relative rebalancing
premium quoted to a rebalanced benchmark; a 131.83% return quoted without its
Sharpe of 0.31, which reverses its meaning). But one verified finding amends
**our** record: **masking the name is not masking the date** (LAP
arXiv:2512.23847, FinCAD arXiv:2605.24564). NIGHT-1's 0/240 result measured
entity masking only ⇒ masked replay is a reasoning laboratory, not an
alpha-certification laboratory. Now CANON §13 and enforced in code.

**7. T6 was registered and then refused by its own power check.** The semantic-diff
prior (188bps/mo verified → long-leg ×0.30 → decay ×0.5 ≈ **3.4%/yr**) sits below
the design's MDE (**4.52%/yr** at t=2 on the 264-month EDGAR window, **6.78%** at
the Harvey-Liu-Zhu bar). **The money version does not run. We did not add row
149.** Licensed instead as a Layer-1 extractor validation on filing-pairs.

## Predictions

Worker **1.5 / 5** (one clean hit, two clean misses, one half, **one not measured
— an execution miss, recorded**). Brain **2 / 4** with two halves. The
instructive miss: I predicted the trailing stop would lose by *selling winners*
(Bessembinder). It lost by *paying the spread*. The mechanism imported from the
literature was wrong; the cost model we already owned was right.

## Attended decisions waiting on Murat

1. **Merge `factory/night-7`** (and push the `aegis-finance` CANON amendment).
2. **The strategic fork** — ROADMAP §12. Path A (fund) is gated on evidence T4
   says we do not have. Path B (research/infrastructure) is nearly finished and
   is what opens Path A later. Recommendation is Path B primary, forward lanes
   untouched. **This is his call, not the session's.**
3. **Accept the corrected product sentence** (ROADMAP §10) — it now carries the
   DSR number, so it claims less than the current product note.

## Queue, re-ordered by NIGHT-7

1. **PRisk replication** — first extractor validation; ground truth free and live.
   Nothing in the LLM programme is worth building until Layer 1 is calibrated.
2. **Re-read the graveyard under the calibrated turnover penalty** — every
   high-turnover corpse was judged on a panel that flattered it, so they are
   *more* dead. `conc_low` remains the only distinct resurrection candidate.
3. **A3 segment drift** — registered, not measured. Cheap; do it first.
4. **Capacity below AVUV's floor** — the one AVUV axis with high plausibility and
   no measurement.
5. **Revise the product note** to lead with AVUV and carry the DSR number.
6. Narrative-salience thematic entry · insider-disagreement interaction ·
   EDGAR full-text spine · ANALYST-LEDGER-1 first forward notes.

**Nothing is blocked on Murat except his decisions.** No endpoint was reported as
blocked this night without being called first.
