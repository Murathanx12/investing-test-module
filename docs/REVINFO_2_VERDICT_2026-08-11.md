# REVINFO-2 VERDICT — UNRESOLVED: the boundary is too fine for this design to see, and the monthly clock is net-dead

**Trial** REVINFO-2 · **Registered** `TRIALS/PREREG_REVINFO_2_LAYER2.md` at
commit `7409bff`, before any Layer-2 statistic was computed · **Runner**
`scripts/run_revision_information.py`'s successor `scripts/run_revinfo_2.py` ·
**Receipt** `runs/REVINFO_2/revinfo2.json` (untracked — `runs/` is gitignored,
so every headline number is reproduced here) · **Window** 2002-01-31..2022-12-31,
252 months; daily spine truncated at 2022-12-31; **holdout unread.**

**Accrues ONE ARM to the search denominator**, as registered. Registry rows
`REVINFO-2` and `VERDICT-REVINFO-2` appended to `TRIALS/registry.jsonl`.

**The registered expectation was UNRESOLVED or NET_DEAD. The answer is both:
NET_DEAD at the monthly clock, UNRESOLVED at the quarterly and semi-annual
clocks, UNRESOLVED for the trial under the frozen rule.** Nothing is promoted,
nothing is killed that was not already priced, and no cell was selected over
another.

---

## 1. The verdict, by the frozen rule, cell by cell

Book: long-only EW top-N on `ibes:eps_rev_breadth`, small segment (dollar-volume
rank 1001–3000 — REVINFO-1's universe, unchanged), incumbency band 3×,
2002–2022. Both registered sizes reported; **neither selected.** H2 is the
headline: the same book through `daily_sim` at `impact_coef = 0` (G7), NET
excess CAGR vs CRSP value-weighted, beside its own 80%-power MDE
(`max(HAC, IID) × 2.8`, §19). The MDE comparison is made on the arithmetic
annualised mean, per the house convention in `scorecard._power_block`; the
geometric CAGR excess is printed beside it.

| cell | G7 net excess (geo) | arith | own MDE | NW t | blocks + | turnover (G7) | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| n50 m1 | **−6.05** | −4.29 | 8.84 | −1.36 | 2/5 | 10.71× | **NET_DEAD** |
| n50 m3 | −1.73 | +0.10 | 9.10 | +0.03 | 2/5 | 3.12× | UNRESOLVED |
| n50 m6 | −0.67 | +1.04 | 10.28 | +0.28 | 2/5 | 1.55× | UNRESOLVED |
| n100 m1 | **−5.02** | −3.43 | 7.71 | −1.24 | 2/5 | 9.65× | **NET_DEAD** |
| n100 m3 | −1.03 | +0.66 | 8.68 | +0.21 | 2/5 | 2.95× | UNRESOLVED |
| n100 m6 | +0.43 | +1.93 | 8.45 | +0.64 | 3/5 | 1.50× | UNRESOLVED |

All numbers %/yr. "blocks +" = positive-excess EXECUTION-STANDARD gate blocks of
the 5 evaluable inside the window (holdout block not read; the gate needs ≥4).

**NET_DEAD at m1 is by the registered definition**, not by a t-stat: the point
estimate is ≤ 0 and the whole 95% interval sits below the +3%/yr economic
threshold (upper bounds **+1.90** and **+1.97 %/yr** for n50/n100). The
information ANALYST-IBES-1 and REVINFO-1 both saw gross at the monthly clock —
reproduced here: gross excess **+4.77 %/yr** through the monthly harness —
**cannot be collected long-only at 10× turnover.** The 10×-turnover death
ANALYST-IBES-1 measured for this family is now confirmed on this signal with a
sequential daily simulator rather than a flat cost assumption.

**UNRESOLVED at m3/m6 is absence of evidence, not a kill (§19).** The slow
clocks are net-positive in arithmetic mean (+0.10 to +1.93 %/yr) against MDEs
of 8.45–10.28 %/yr. This design — one book, 252 months — resolves nothing
smaller than ~8 %/yr net, and no credible net effect for this family is that
large. §7 of the prereg said this in advance: **"if the book's own MDE exceeds
its point estimate, the trial has answered 'this design cannot see it'"** —
which is the answer.

No cell passed H2, so the VOID clause (H1 fails while H2 passes) never armed.

## 2. H1 — the decision boundary is not established

`E[r_entrant − r_incumbent]` at the book's own traded boundary, paired per
rebalance, EW compounded over the holding period, Newey-West on the event
series, delist-driven exits excluded (a delisting is not a decision).

| cell | E[entrant − incumbent] %/yr | own MDE | NW t | events | mean entrants/leavers |
|---|---:|---:|---:|---:|---|
| n50 m1 | +2.09 | 6.99 | +1.03 | 251 | 44.1 / 43.8 |
| n50 m3 | −3.49 | 8.19 | −1.19 | 83 | 39.0 / 38.1 |
| n50 m6 | +2.35 | 11.20 | +0.59 | 41 | 39.2 / 37.5 |
| n100 m1 | +1.94 | 5.45 | +1.17 | 251 | 79.0 / 78.5 |
| n100 m3 | −3.00 | 6.03 | −1.53 | 83 | 73.3 / 71.8 |
| n100 m6 | +1.31 | 6.88 | +0.57 | 41 | 74.4 / 71.5 |

**Not one cell clears its own MDE, and the sign flips at the quarterly clock.**
The registered claim was `> 0`; the honest reading is that the boundary effect,
if it exists, is smaller than ~5.5–11 %/yr — which is to say this instrument
cannot see it. The m3 negatives are below their MDEs and may NOT be read as
"entrants underperform"; they are recorded because hiding a sign flip is how a
programme talks itself into a boundary that was never measured.

Note what this bounds: REVINFO-1's Layer-1 cross-section carries ~+3 %/yr in
the long leg across ~1,700 names. The boundary a 50–100-name book actually
trades is a far noisier object, and the churn at that boundary (44 of 50 names
replaced per month on average) is exactly why the m1 cells die net.

## 3. H3 — the direction registered in advance, seen but not detectable

Differences between ADJACENT frequencies, paired monthly G7 net returns, each
with its own SE (§18) — never read off two levels.

| difference | mean %/yr | HAC SE | own MDE | NW t | geometric diff |
|---|---:|---:|---:|---:|---:|
| n50: m3 − m1 | **+4.39** | 1.88 | 6.02 | +2.33 | +4.32 |
| n50: m6 − m3 | +0.95 | 1.98 | 5.53 | +0.48 | +1.05 |
| n100: m3 − m1 | **+4.09** | 1.41 | 4.20 | +2.90 | +3.99 |
| n100: m6 − m3 | +1.26 | 1.20 | 3.35 | +1.06 | +1.46 |

The registered direction (net improves as holding lengthens) appears in all
four differences, and the m3−m1 step is significant at 5% in both sizes —
**but below its own MDE in both**, which is the §19 region where significant
findings systematically overstate themselves. It corroborates NIGHT-6's
+2.43 %/yr (annual beats monthly, different family) in direction. **No
frequency is declared the survivor.** The m6−m3 step is indistinguishable from
zero, so "slower keeps improving" is NOT established — what is seen is "monthly
is the expensive clock," which the turnover receipts already price.

## 4. Turnover receipts — the prior reproduced to the third decimal

| clock | monthly-harness 1-way ann (n50 / n100) | G7 1-way ann (n50 / n100) | prior (ANALYST-IBES-1) |
|---|---|---|---|
| m1 | 10.614× / 9.568× | 10.71× / 9.65× | **10.614×** |
| m3 | 3.150× / 2.980× | 3.12× / 2.95× | 3.150× |
| m6 | 1.588× / 1.517× | 1.55× / 1.50× | — |

Realised turnover for the n50 m1 cell equals the ANALYST-IBES-1 prior
**exactly** (10.614× vs 10.614×; same construction, independent re-run), and
the monthly-harness reference reproduces that trial's receipt to the decimal
(net excess −1.05 %/yr, gross +4.77). Nothing came in below the prior, so the
pre-registered "cheaper book is a bug" investigation never armed. G7 charged
41–45 bps per dollar traded (Corwin-Schultz half-spread + 5 bps slippage +
1 bp commission, tick floor) against the harness's flat 25 — the gap between
the −1.05 monthly reference and the −6.05 G7 number at m1 is that repricing
plus next-day fills and participation caps (908 of 5,287 days had capped
orders at a $1m book in this segment — liquidity binds even at $1m).

## 5. Controls

**The corpse (`tgt_upside`), both registered arms, sign reproduced in both:**

| arm | number | sign gate |
|---|---:|---|
| cross-sectional (Layer-1 instrument, small h=1) | −0.155 %/yr (MDE 13.27, t −0.03) | ✅ negative |
| tail-concentrated: monthly harness gross | **−8.56 %/yr** | ✅ negative |
| tail-concentrated: monthly harness net | −10.42 %/yr | ✅ |
| tail-concentrated: G7 net | **−17.29 %/yr** (own MDE 23.32, t −1.21) | ✅ |

The NIGHT-11 standing rule is why both arms exist: the corpse is flat in the
cross-section and catastrophic in the concentrated top-3%, and this pipeline
reproduces exactly that signature.

**Pure noise, turnover-matched** (`np.random.default_rng`, seed 20260811,
AR(1) ρ = 0.249 matched to the m1 signal book's 10.6×; realised 10.02×):
G7 net excess **−11.45 %/yr geometric, −9.39 arithmetic — above its own MDE of
8.58 (t −3.07).** The pipeline earns nothing from nothing and pays the full
execution bill, detectably. This is the only number in the trial that clears
its own MDE, and it is the cost of the monthly clock measured with no
information in the book.

**Post-hoc diagnostic (NOT registered, no claim):** the paired monthly
difference signal-minus-noise at m1 is +5.10 %/yr (HAC SE 2.21, t 2.31) against
an MDE of 6.57 — the signal's gross information is visible net of the shared
cost bill, and below the detectable threshold. Recorded as a diagnostic only.

## 6. A defect found in the sibling and measured rather than argued

`scripts/g7_daily_sim.py` passes `effective = test` month-end to the simulator —
on a month-end-labelled panel that is a ~1-month implementation lag, while
`daily_sim`'s own docstring specifies "decision on the month-end close, trade
the NEXT trading day." This trial trades at formation month-end + 1 day (the
module's contract) and ran the sibling's convention as a sensitivity arm on
n50 m1: sibling-timing net excess **−7.59 %/yr vs −6.05** base; the paired
difference is +1.47 %/yr (HAC SE 1.81, t 0.81) against an MDE of 6.14 — **not
detectable, and no verdict here depends on the choice.** For the annual-clock
book G7 was built on, NIGHT-5 already measured the gap at ~28 bps. Flagged for
the sibling script; nothing retroactive is claimed.

## 7. What may NOT be concluded

- **That REVINFO-1 is overturned or confirmed.** Layer 1 stands as measured:
  the cross-section carries the information. Layer 2 says a 50–100-name
  long-only book at monthly turnover cannot keep it, and the slower clocks are
  below this design's resolution. A Layer-2 result cannot re-grade a Layer-1
  one in either direction.
- **That ANALYST-IBES-1 is overturned.** It is corroborated at m1 — by
  construction-level reproduction, not analogy.
- **That m6 (or any clock or size) "works".** +0.43 %/yr geometric against an
  8.45 MDE is nothing at all under §19, and picking the best of six cells is
  the exact move the prereg forbade.
- **Any money claim, Sharpe, or skill claim.** No forward record exists here.
- **No half-life claim** — H3's m6−m3 step is indistinguishable from zero.

## 8. What would move this question

The trial's own §7 answered "this design cannot see it": a one-book design
resolves ~8 %/yr net, and the interesting region is +1 to +3. What would
actually shrink the MDE is the same lesson as NIGHT-11's instrument work:
breadth (many overlapping-cohort books rather than one), longer windows, or a
paired design against a matched passive book so the common small-cap variance
cancels — the signal-minus-noise diagnostic above (SE 2.21 vs the raw arm's
3.16) is the hint, not the result. That is a successor registration, not an
amendment to this one.
