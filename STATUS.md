# STATUS — current pointer (updated 2026-08-14)

**This file's narrative below stops at NIGHT-12 and is kept as history. The
current state of the programme is:**

- **`aegis-finance/docs/GRAND_ARENA_1_VERDICT.md`** — the campaign verdict
  (2026-08-12): one clean positive (MARKET-GRAPH-1 H1, a co-movement/risk-model
  result), LLM role measured at `PRESENTATION_AND_RESEARCH_ASSISTANCE`, no
  breakthrough awarded under A11.
- **`aegis-finance/docs/MARKET_GRAPH_1.md`** — the surviving result and its
  audits.
- **`aegis-finance/docs/NIGHT14_DISCHARGE.md`** — grading-clock fix; first
  forward resolutions land **2026-08-16**.
- **`aegis-finance/docs/ROADMAP_BRAIN_V3_2026-08-14.md`** — the post-arena
  direction (four tracks, eight experiment families).
- **`aegis-finance/docs/HANDOFF_OPUS5_2026-08-14.md`** — the active build/research
  handoff.
- **`aegis-finance/docs/GRAPH_COVARIANCE_1.md`** — the first Track B descendant,
  **closed 2026-08-14**. H1/H2 NOT DETECTABLE with all three placebos clean; the
  power gate failed and the chase produced the finding that matters: **perfect
  foresight of the realised forward correlation matrix is statistically
  indistinguishable from the trailing sample matrix** (t = 0.23 against MDE
  0.0019) while the industry-standard diagonal assumption is 86.6% worse
  (t = 12.60). There is no headroom for any correlation predictor to occupy at
  this universe size, so **do not build further "improve the covariance matrix"
  descendants**. MARKET-GRAPH-1 H1 is untouched — only its route through a
  min-variance solve is closed. $0 LLM spend.

---

# STATUS — handoff after NIGHT-12 (2026-08-11) [HISTORICAL]

**Read `aegis-finance/docs/SESSION_2026-08-11_NIGHT12.md` first**, then
`docs/REVINFO_1_SHORT_LEG_2026-08-11.md` and
`aegis-finance/docs/conviction_replay/conviction_replay_1.json`.

## THE HEADLINE

**1. The revision family SURVIVED its short leg — the first thing in this
programme that has.**

NIGHT-11 registered the short-leg decomposition as the cheapest test that could
kill the family. It did not kill it. Round 16 measured 88–99.9% of a comparable
spread living in the leg a long-only book cannot hold; here the short-leg share
is **41.8–52.1%, median 47.2%**, and **the long leg alone clears its own MDE in
6 of 7 licensed arms**:

| arm (small) | spread | **long leg** | MDE | t |
|---|---:|---:|---:|---:|
| `tgt_rev_breadth` h1 | +9.36 | **+4.48** | 3.21 | +3.91 |
| `eps_rev_breadth` h1 | +6.64 | **+3.24** | 2.57 | +3.53 |
| `eps_rev_breadth` h3 | +5.54 | **+3.08** | 2.26 | +3.82 |
| `eps_rev_breadth` h6 | +4.66 | **+2.72** | 2.19 | +3.47 |

Top decile alone: **+3.44 to +6.48 %/yr at t 2.88 to 5.45**.

Per **CANON §18** the claim that one leg carries more is tested on the PAIRED
difference with its own SE, never read off the share. **It is not detectable in
any of the 7 arms** (|t| ≤ 1.04, MDEs 2.1–4.3) ⇒ the honest reading is an even
split. Accrues **zero** — a re-partition of an already-registered result.

**STILL LAYER 1 AND STILL GROSS.** ANALYST-IBES-1 measured this family dying at
**10× turnover**. Surviving the short leg says nothing about surviving costs.

**2. Murat's selection cannot be distinguished from his own watchlist, and the
design says so honestly.** +34.6% vs +33.0%, difference **+1.6 pts against a
MEASURED MDE of 80 pts**, p 0.959 ⇒ `UNRESOLVED_ABSENCE_OF_EVIDENCE`. Under §19
this is NOT a finding that he has no skill; 13 names over one nine-month window
resolve nothing.

## THE NEXT TEST, REGISTERED

**Layer-2 decision boundary for `eps_rev_breadth` small** is now the
highest-value open question in the registry: most persistent arm, long leg
clears its MDE at h=1/3/6, never Layer-1 tested before NIGHT-11. **Carry the
turnover question through G7 in the SAME trial** — a long leg that survives its
short leg and then dies on costs is the most expensive way this family can still
fail. **This one ACCRUES.**

## WHAT NIGHT-12 ALSO BUILT (in aegis-finance)

* **BeliefState + PredictionRecord, frozen; the calibration clock started.**
  87 live DeepSeek forecasts over 31 names, effective distinct ideas 66 of 69
  (§20). Nothing resolves yet — shortest horizon is 5 trading days.
* **Counterfactual exit engine** — the leakage-free half of the "market
  laboratory" proposal. `sell_to_cash` was NEVER the best branch in 60 rows.
  The SOC question returns `NO_OBSERVABLE_SEPARATES_AT_THIS_SAMPLE`;
  `drawdown_from_peak` correlates +0.64 at p 0.021 against an MDE of 0.80 —
  significant BELOW its own MDE, the winner's-curse region §19 refuses.
* **Exposure controller v0** — never left `risk_on`; the finding is that his
  22.9% drawdown against SPY's 8.9% at beta 2.15 is a SIZING problem, not a
  market-timing one. The policy was NOT tuned until it fired.

## DEFECTS FOUND AND FIXED (each changed a number)

1. **APLT and SLNO silently excluded** from the replay — both delisted by cash
   takeover, no surviving bars. Carrying the payout was not enough without an
   entry price. APLT is his WORST holding and SLNO a watchlist WINNER, so the
   errors compound rather than cancel: including them moved the headline from
   **+11.7 to +1.6 pts**.
2. **Exit annotations attached to the wrong positions** (ALMS's exit price
   landed on DKNG) and the greedy strip dropped all three sold rows.
3. **"Top 13 by consensus" was 13 names from a FOURTEEN-way tie** with none
   strictly above — ties printed as a ranking, the NIGHT-10 defect again.
4. **Six LLM forecasts carried percent thresholds** (`|move| > 20.0` = 2000%),
   all from ONE specialist. Now refused at write time and VOIDED in place.
5. **`trim_*` win counts were a theorem, not a result** — convex combinations of
   hold and cash can never win a maximum. And `pct_of_peak` = 1 +
   `drawdown_from_peak`, the same feature counted twice.

## ANTHROPIC_API_KEY IS STILL EMPTY

The `.env` line carries a trailing comment, so a length check reports 79
characters and a live call fails. **Verified by calling, not by measuring a
string.** Every LLM finding in this programme remains a finding about DeepSeek.

## STILL OWED BY MURAT

cash · kill-condition rulings (ABSI/AMSC/HUBS/KYTX/SLDP) · `confirmed: true` ·
a real `ANTHROPIC_API_KEY` · seeding the shadow books · the graceful-degradation
ruling · **the transactions** — they are the only thing that can reconcile
+73.7% vs "+115%" and separate his selection from his sizing.

## SUITES

Aegis module **612 tests**. aegis-finance fast suite green (see the session doc
for the count). Both repos clean and pushed.
