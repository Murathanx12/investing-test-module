# PREREG — CONVICTION-REPLAY-1: did his selection beat the pool he drew it from?

**Registered** 2026-08-11, NIGHT-12, before any forward return of either group
was computed. **Family** conviction / human-record. **Data**
`aegis-finance/docs/conviction_replay/` (two dated PDFs, parsed by
`backend/services/conviction_sheets.py`), prices by yfinance with the two
corporate actions recorded in `backend/services/conviction_prices.py`.

**EXPLORE / OBSERVATIONAL.** The design was written after seeing his history.
Nothing here can be confirmation of anything; the only confirmation instrument
available is the forward record, which is why Phase 3 starts the prediction
ledger tonight regardless of what this trial returns.

**Layer 1 only.** This asks whether his labels carried information. It may not
size a position, may not seed a lane, and may not license copying his style.

**Denominator.** Accrues **one** arm: the primary test in §3. The alternative
rankings in §4 are pre-specified comparisons within the same test, not separate
searches; they are reported whatever they show, and none of them may be
promoted to "the finding" after the fact if the primary comes back null.

---

## 1. What is being measured, and what cannot be

His sheets are dated point-in-time snapshots that record **both** his holdings
and the watchlist they were drawn from, priced the same day. That is what makes
the question identified: the counterfactual to his selection is written down.

The sheets carry **no share counts, no cash and no transactions.** They cannot
produce his NAV, and no number in this trial is his return. Every basket is
equal-weighted. The +73.7% brokerage figure and the "2025 +115%" sheet header
are **not reconciled by this trial and nothing is trained on either** — they
differ in window, weighting and cash treatment, and the inputs to settle that
are not in the repo. Carried as a labelled gap.

## 2. The instrument, and why it is not a t-test

13 picks against 48 non-picks, and the picks cluster in clinical biotech and
quantum/semis, so one sector move moves most of one side together. A t-statistic
would count that concentration as 13 independent draws and overstate its own
precision — exactly what CANON §19 exists to stop.

The test is a **label permutation**: under the null that his labels carry no
information, any 13 of the 61 were equally likely to be picks. The null is built
by reassigning labels across the observed return vectors, so the real
cross-correlation is carried into the null at no assumption cost.

**The MDE is measured, not derived** — effects of known size are planted in a
random 13 and the real test is run against them. NIGHT-11 found an MDE that had
been an unchecked formula silently fed the wrong standard error for months; no
MDE in this programme is quoted from a formula again.

## 3. The primary hypothesis, registered

**H1.** Over 2025-11-07 → 2026-08-10, the equal-weighted mean total return of
his 13 portfolio names exceeds that of the 48 watchlist names he did not hold.

Decision rule, frozen:

| outcome | verdict |
|---|---|
| difference ≥ MDE **and** permutation p < 0.05 | `SELECTION_INFORMATION_PRESENT` |
| p < 0.05 but difference < MDE | `UNRESOLVED — significant below the threshold at which this design finds effects reliably` |
| p ≥ 0.05, difference < MDE | `UNRESOLVED — absence of evidence, NOT a kill (§19)` |
| difference negative and ≥ MDE in magnitude | `SELECTION_PERVERSE` |

**The expected outcome is UNRESOLVED.** n is 13 names over one nine-month
window. Registering that expectation in advance is the point: a null must not be
reported as a discovery about his skill, and a hit must not be reported without
the MDE beside it.

## 4. Pre-specified comparisons (reported whatever they show)

Each is the same 61-name pool, ranked by a rule he could have followed instead,
top 13 taken, same window:

1. **`sheet_upside`** — analyst target ÷ his recorded price. *This is the one
   that matters.* If this beats his actual picks, the spreadsheet did the work
   and his thematic judgment subtracted. Uses HIS transcribed prices, because
   the question is what his spreadsheet would have said, not a clean feed.
2. **`consensus_rating`** — the big-bank endorsement heuristic, made testable.
3. **equal-weight all 61** — the pool itself.
4. **SPY / QQQ / IWM / XBI** — market, growth, small, biotech.

**Prior, registered:** ANALYST-IBES-1 graded analyst target LEVELS
**PERVERSE/CLOSED** at −16.70 %/yr through a top-50 book. If `sheet_upside`
ranks well here, that is **not** a refutation of the corpse — one window of 61
names cannot overturn a 20-year panel, and NIGHT-11 established that a corpse
killed by a concentrated book is not automatically re-testable by a different
instrument. It would be recorded as a coincidence to explain, not a rescue.

## 5. Secondary, registered

**H2 (exits).** Per sold position, the cost of selling = price at window end
minus sale price, over entry. **Registered prediction: the sign is NOT uniform
across his three recorded exits.** His self-diagnosis is that he exits too
early; TVTX (sold 34.4, later 22.8) and ALMS (sold 10, later 21+) already point
in opposite directions on his own sheet. A uniform "sells too early" finding
would be evidence the measurement is wrong, not that the diagnosis is right.

**H3 (rebalance).** Between the sheets he promoted 6 watchlist names into the
book and demoted 5. Measured forward from 2026-01-13, the promoted set vs the
demoted set — the same selection question asked of a decision made two months
later, and an INDEPENDENT second draw on the same skill.

**H4 (capture).** Up- and down-capture vs SPY, reported as a pair, for his book
and every lane. A book capturing 40% of upside and 40% of downside has lower
risk, not timing skill, and the pair is the only honest way to say so.

## 6. What may NOT be concluded

- That he has, or lacks, stock-selection skill. One window, 13 names.
- That his style should be copied into production because it made 70%.
- That any corpse is reopened. Reopening needs its own pre-registration.
- That a positive result licenses capital, a lane, or a position.
- A half-life, a Sharpe, or any money claim.

## 7. Kill condition for the trial itself

If the parsed sheets fail to reproduce his recorded prices against actual closes
for the large, unambiguous names (SPY-listed megacaps), the parse is wrong and
the trial is void rather than reported. *Checked before registration: 119 of 128
sheet prices are within 12% of the actual close on the sheet's own date; the
residual is his rounding, and it is why forward returns are computed from actual
closes and his prices are used only for the upside ranking he actually saw.*
