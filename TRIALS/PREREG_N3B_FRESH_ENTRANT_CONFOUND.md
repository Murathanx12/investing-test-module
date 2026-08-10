# PREREG — TRIAL-N3B-FRESH-ENTRANT-CONFOUND-1 (REGISTERED, NOT RUN)

**Registered:** 2026-08-10 · **Family:** N (extension) · **Stage:** diagnostic
**Parent:** `TRIAL-N3-SEASONING-1` (POWER_FAILED at its own bar; receipt
`runs/NIGHT8/N3_SEASONING.json`)

Resurrects: PREREG_N3_SEASONING — new instrument: the within-month momentum and
volatility control battery built for the NIGHT-7B trigger study, plus a
half-year placebo that the parent's bucket definition cannot separate on its own.

## 1. What the parent found

Within month, against the other names held that same month:

| bucket | effect | NW(12) t | MDE at t 2 | share of name-months |
|---|---|---|---|---|
| **m1_6** | **+4.27%/yr** | **+2.10** | 4.89%/yr | 0.196 |
| m7_12 | −0.97%/yr | −0.56 | 4.08%/yr | 0.189 |
| m13_24 | −0.32%/yr | −0.21 | 3.23%/yr | 0.208 |
| m25_plus | −1.84%/yr | −1.44 | 3.17%/yr | 0.407 |

The parent's frozen rule returned **POWER_FAILED** — the weakest bucket could not
have seen the 2%/yr bar — so band tuning did **not** close, and the m1_6 row is
suggestive rather than established.

## 2. The two confounds the parent could not separate

**(a) Tenure is endogenous**, as the parent declared before compute. A fresh
entrant is a name whose composite score just rose.

**(b) The bucket boundary is mechanical, and this was not anticipated.** The
monthly exit hazard is **0.0069** in m1_6 and **0.0721** in m7_12 — a tenfold
jump. On an annual clock a name bought at a rebalance *cannot* be sold until the
next one, so "months 1–6" is a window in which exit is structurally impossible
and "months 7–12" is the window that contains everything about to be dropped.
The buckets are therefore not "fresh vs stale" so much as **first half-year vs
second half-year of the holding period**, and any comparison between them carries
that asymmetry.

## 3. Design

Same book, same within-month construction. Three additions:

1. **Momentum and volatility controls**, exactly as in
   `scripts/pf7b_trigger_momentum_control.py`: RAW, residualised on within-month
   momentum rank, and matched within momentum quintile. Repeated with trailing
   12-month realised volatility.
2. **The half-year placebo.** Split the holding year at the *midpoint* for names
   of every tenure, not only for new entrants, and compare first-half against
   second-half within each tenure cohort. If a first-half premium appears for
   *incumbents too*, the effect is about position in the rebalance cycle and not
   about being newly selected — which would make it a calendar artifact of the
   annual clock rather than a seasoning effect.
3. **Power stated first.** The parent's MDE was 4.89%/yr against a 2%/yr bar. The
   bar here is raised to **4.0%/yr** so it sits above the MDE, and if the
   realised MDE still exceeds it the verdict is `POWER_FAILED` again and the
   family stays open but unmeasured.

## 4. Decision rule (frozen)

| outcome | state |
|---|---|
| m1_6 survives both control batteries **and** the half-year placebo is null, at ≥ +4.0%/yr and NW t ≥ 2.0 | `CONFIRMED` — register a band/entry-timing trial. Adopts nothing. |
| the half-year placebo shows the same premium for incumbents | `PLACEBO_FAILED` — a calendar artifact of the annual clock |
| the effect dies under momentum or volatility control | `REJECTED` — it was a factor tilt wearing a tenure label |
| realised MDE > 4.0%/yr | `POWER_FAILED`, MDE printed |

## 5. Registered predictions

1. **The half-year placebo fires.** I expect incumbents to show the same
   first-half tilt, making this a property of the annual rebalance cycle rather
   than of freshness.
2. **What survives the momentum control will be smaller than +4.27%/yr** but not
   zero — the composite is a profitability composite, not a price one, so
   momentum should explain less of it than it did for the stop trigger.
3. **It will still be POWER_FAILED**, because the m1_6 bucket holds under 20% of
   name-months and the parent's MDE was already 4.89%/yr.

## 6. Ledger

Adds **3 branches** (momentum control, volatility control, half-year placebo).
