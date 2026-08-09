# NIGHT-5 verdict — the night the measurements came back smaller than the decisions

Branch `factory/night-5`. Preregs committed **ec06dc6 at 14:20:04Z**, first
compute after. Holdout unread throughout. Nothing promoted, no lane seeded, no
flag flipped.

**One sentence:** two decisions taken on earlier nights turned out to rest on
differences too small to measure, the graveyard turned out to be half broken
experiments rather than half bad ideas, and the daily simulator says the monthly
harness has been telling the truth at retail size — and lying by 4 points about
the drawdown.

---

## T1 — merges + G7

`factory/night-3` and `factory/night-4` merged to `main` (`b3fc8fe`, night-3 is
an ancestor of night-4 so one merge lands both). Module suite green post-merge.

**G7, the sequential daily simulator, is built** (`aegis_brain/pf/daily_sim.py`)
and its first workload is the annual `PF-PROF-COMPOSITE-150`, as instructed.
G7 consumes **the monthly harness's own target holdings**, so any difference is
attributable to daily reality rather than to a different strategy being
simulated. Daily CRSP 2002-2024, 5,789 days, 804 names, 456 real delistings,
21 annual rebalances.

### What G7 found

| Start NAV | CAGR | vs monthly harness | daily maxDD | days with capped orders |
|---:|---:|---:|---:|---:|
| $1 m | 13.45 % | **−28 bps/yr** | −52.6 % | 56 / 5,789 |
| $10 m | 13.53 % | −20 bps/yr | −52.8 % | 519 |
| $100 m | 13.16 % | −57 bps/yr | −53.8 % | 3,347 |
| $500 m | 12.16 % | **−157 bps/yr** | −54.2 % | 5,428 (94 %) |

**1. The monthly harness is broadly honest at retail size.** Next-day-open
fills, quoted spreads, participation caps and daily marks cost **28 bps/yr** at
$1 m. That is a validation, and it is the first time this programme has had one.

**2. The drawdown we have been quoting is 4.1 points too shallow.** The monthly
scorecard's −48.4 % is a *month-end mark*. The daily path reaches **−52.6 %**.
That difference is the part of the experience the monthly harness never showed,
and it is the number the product note must carry.

**3. Capacity breaks between $100 m and $500 m.** At $100 m more than half of
all trading days have orders clipped by the 5 %-of-volume cap; at $500 m,
94 % do, and 157 bps/yr is lost. Below ~$10 m the book is implementable as
simulated. This is the first capacity measurement the programme has ever made —
the monthly harness cannot ask the question at all.

---

## T2 — TRIAL-PF5-REBAL-FRONTIER-1 → **UNRESOLVED**, and it corrects NIGHT-4

Incremental-alpha t across `{1, 3, 6, 12, 18, 24}` months, era costs at every
point: **3.12 · 3.30 · 3.58 · 4.50 · 4.00 · 5.60**. Not single-peaked (18 m
dips), argmax on the grid boundary — where the prereg forbids extending. By the
frozen rule that reads UNRESOLVED.

**The decisive number is not on the frontier, it is underneath it.**
`DIAG-PF5-FRONTIER-PAIRWISE-1`: of the **15 pairwise differences between the six
clocks, not one is significant**. Level correlations run **0.958 – 0.993** —
these are the same names traded on different schedules. 24 m minus 12 m is
+0.71 %/yr at **t 0.83**. For 12 m minus 1 m, the geometric and arithmetic
estimates *disagree on the sign*, which is as close to "unmeasurable" as a
number gets.

**Correction to NIGHT-4.** I reported that annual rebalancing "dominates the
registered monthly spec on every axis at once" and called it the night's most
useful result. The **mechanical** half of that is true and certain: turnover
0.48 vs 2.40, cost drag 31 vs 120 bps, and a book a person can actually hold.
The **return** half is not established — the t-statistic improvement from 3.65
to 4.50 sits inside noise. Annual should still ship, for the mechanical reasons
and because 24 m is a schedule nobody keeps; but it ships as an *operational*
choice, not a measured optimum.

Also isolated, since NIGHT-4 moved two things at once: monthly under **era**
costs pays **176 bps/yr** of drag versus 120 under flat-25. Era costs punish
frequent trading harder than the flat model, which is a second reason the annual
config looked better than it had earned.

**Predictions 2/5** — P2 (t(1 m) < t(3 m)) and P3 (24 m turnover is not half of
12 m; 0.305 vs 0.478) HIT. P1, P4, P5 MISS.

---

## T3 — TRIAL-PF5-RANK-SHAPE-1 → **NO MEASURABLE SHAPE**

105 bucket books fitted, both clocks, on a structurally common month set
(1982-11 → 2022-12, 482 months) so that no bucket is measured on a different
panel than its neighbours.

* **Cochran Q p = 0.6927** on the primary 10-name grid: flatness not rejected.
* **The power number, which is the finding:** the curve could not have detected
  a monotone ramp smaller than **10.7 %/yr** from best to worst bucket at 80 %
  power (median per-bucket MDE **5.97 %/yr**). Per the prereg and the NIGHT-4
  retraction this reads **UNMEASURED, NOT ZERO**.
* Both clocks agree (S4 flat). Both era halves select S4 flat. All three
  constituent signals independently select S4 flat, except `CBOperProf` which
  prefers S3 at a gap far below the threshold.

### The registered arm that matters most

**A1 — ranks 11-20 minus ranks 1-10: +0.77 %/yr at t 0.16.**

NIGHT-4 observed +8.93 %/yr (t 2.38) against −1.17 % — a ~10-point gap — and on
that basis I un-cancelled the LLM re-ranking campaign. Measured on the full
eligible top-150 curve over 482 months, **the effect does not replicate**. It was
recorded as a hypothesis and it has now failed its first honest test.

**Consequence: the re-ranking campaign is NOT built on this data.** Stated
precisely, because the retraction taught this distinction the hard way: we have
not shown ordering is worthless. We have shown that if ordering is worth
anything inside this book, it is worth less than ~10.7 %/yr of spread, and this
panel cannot see it. A campaign needs an instrument with more power, not another
pass over the same 482 months.

*One honest wrinkle, reported rather than buried:* in the pre-2001 half Cochran
Q **does** reject flatness (p = 0.0376) while still selecting the flat model.
That p does not survive the family's own Bonferroni bar (0.0124), and post-2001
is p = 0.91. It is recorded as heterogeneity in the thin early panel, not as a
shape.

**Predictions:** Q1 (Q fails to reject) HIT. Q4 (bucket MDEs above 4 %/yr — they
are 5.97 %) HIT. Q3 (the 11-20 effect does not replicate) HIT, though its stated
mechanism — "it lives in one era half" — was not the way it failed. Q2 is void
(no shape won AIC by ≥ 2). **Q5 IS UNSCORED BECAUSE ARM A4 WAS NOT IMPLEMENTED**
— turnover and cost by bucket was registered and I did not build it. Recorded as
a miss of execution, not of prediction, and it belongs in the next campaign.

---

## T4 — verdict taxonomy v2 and the graveyard census

`aegis_brain/verdicts.py`, nine states, **23 unit tests**. The guards are
executable: a write-up whose statistics say `UNRESOLVED` cannot print `REJECT`;
`FACTOR_EXPLAINED` cannot be written as "no edge"; nothing may print "proves".
Several tests are sentences this project actually wrote.

**The tests caught two of my own bugs during this night**, which is the entire
argument for building them: an ordering assumption in `classify` that was
wishful rather than statistical, and a Python chained comparison
(`ic_t >= 3.0 > net_t`, which silently means `net_t < 3.0`) that labelled a
result with net t 2.31 as IMPLEMENTATION_FAILED.

### The census — 148 banked scan rows, 74 unique signals

| State | Rows |
|---|---:|
| REJECTED — powered, bar excluded | **69** |
| POWER_FAILED — could not have seen the bar | 31 |
| IMPLEMENTATION_FAILED — information present, money absent | 29 |
| DATA_FAILED — never produced a number | 14 |
| UNRESOLVED | 5 |

**Killed by the idea: 69. Killed by the experiment: 74.** The old ledger
recorded all of them identically.

* **Median MDE 3.74 %/yr against the standard's own +3 %/yr bar ⇒ 66 % of the
  scans could not have detected the effect we require.** RECAL-1 reached this
  from the other side in August: the graduation rule had a *measured 0 %*
  probability of adopting even a true α = 0.6 edge.
* **But the median point estimate is −1.40 %/yr.** The mass is genuinely
  negative. "The experiment was broken" does not rescue the central tendency,
  and this half of the answer is the one that does not flatter us.
* **14 rows never ran at all** (0–4 months) and were carried in the 0-for-179
  record as though they had been tested.

### A premise from the brief that does not survive

The night's brief expected two known biases to have penalised every small
candidate in the harness. Checked before use:

* **The never-indexed $200k floor does NOT apply to this search.** The scan ran
  on the 2002-2024 panel, where the small segment carries ~1,950 eligible names.
  The floor is a 63-year-panel problem — there it leaves the small segment with
  **0 eligible names in the 1960s and 1970s**.
* **Era costs apply only weakly** — the scan window is entirely
  post-decimalisation. The live warning is the scan document's own: 25 bps
  *understates* small-cap costs, so those rows are flattered, not penalised.

### Resurrection shortlist (5, none registered tonight)

`cash_prof` · `conc_low` · `fscore_lite` · `price_level` · `oper_prof`, all
small-segment, all IC t ≥ 6.6.

**Three of the five are the profitability/quality family we already ship** — the
shortlist mostly re-derives `PF-PROF-COMPOSITE-150`'s own constituents by a rule
written to look for something else. That is corroboration, not a new lead.
**Only `conc_low` is a genuinely distinct hypothesis**, and it is the one whose
money leg showed up (net t 2.31) while still failing the screen. Registering
five trials at the end of a night is how a shortlist becomes a fishing licence,
so none was registered.

---

## T5 / T6 / T7

* **T5** — five standing amendments appended to the frozen execution standard:
  mandatory era-cost stress, characteristic-matched placebo replacing
  turnover-matching as the edge gate, decision-branch counts on every scorecard,
  machine-enforced taxonomy, and no null without its MDE.
* **T6** — `ANALYST-LEDGER-1` registered (forward, explain-then-predict, paired
  bps metric, t ≥ 2.0 deflated, ≥ 24 months, zero lane influence). The **source
  policy is code** with 14 tests: filings/IR/wires may support an estimate;
  blogs, forums and aggregators are context only; unknown hosts are treated as
  context rather than optimistically allowed. Unsourced claims **flag** an
  estimate rather than deleting it, so the flag itself stays falsifiable (S1).
  All three house predictions are pessimistic.
* **T7** — `docs/PRODUCT_NOTE_v0.1_2026-08-09.md`. Core-satellite, honest
  numbers, blend table at 20/30/40 %, and an explicit list of what is not
  modelled (tax on ~48 %/yr turnover, capacity, behaviour).

---

## Scoreboard and what changed

**Predictions 5 of 8 scoreable** (T2 2/5, T3 3/3 scoreable, 1 void, 1 unscored
because I failed to build arm A4).

**Two decisions moved:**

1. Annual rebalancing ships on **mechanical** grounds — a fifth the turnover, a
   quarter the cost, and holdable by a human — **not** because it was measured
   to earn more. That claim is withdrawn.
2. **The LLM re-ranking campaign is not built.** The observation that un-cancelled
   it does not replicate. The correct reading is "unmeasured below ~10.7 %/yr",
   and the next instrument must have more power, not more passes.

**Two things got harder to fool:** the verdict guards are executable, and G7 can
now say how big the account can be before the backtest is describing a portfolio
that could not have been built.
