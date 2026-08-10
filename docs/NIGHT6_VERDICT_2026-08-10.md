# NIGHT-6 verdict — the blocker wasn't real, and the monthly panel has been flattering churn

Branch `factory/night-6`. Prereg committed **9b8ad30** before any comparison ran.
Nothing promoted, no lane seeded, no flag flipped, holdout unread.

---

## 0. A correction I owe before anything else

NIGHT-4 and NIGHT-5 both closed with "a PIT-clean ETF feed is the one thing
Murat must supply". **That was my error, not a missing key.** Tested tonight:

| Key | Result |
|---|---|
| `POLYGON_API_KEY` | valid, but the plan excludes the timeframe — 403 `NOT_AUTHORIZED` |
| `FMP_API_KEY` | valid, but the legacy endpoint is retired (403) and its replacement is premium-gated for these symbols (402) |
| **`EODHD_API_TOKEN`** | **works, and has since July** — AVUV, DFSV, IJS, VBR, SPY, IWM, VTI, all with `adjusted_close` from inception |

I asserted a blocker for two nights instead of spending four minutes testing the
keys already in the environment. The same check dissolved a second one: SEC EDGAR
full-text search answers unauthenticated (HTTP 200), so `TRIAL-LLM-VETO-1`'s
"blocked — no EDGAR spine exists" is also not a blocker, only unbuilt work.

The overlap was better than I assumed too: I registered IJS at "~221 months".
It is **269**.

---

## 1. TRIAL-PF6-PRODUCT-REAL-1 → **UNRESOLVED**

The book against the funds a person could actually buy, replacing the Ken French
academic proxy. Deciding funds frozen before compute: IJS and VBR.

| Fund | Months | Excess /yr | t (paired, NW) | MDE |
|---|---:|---:|---:|---:|
| IJS (S&P 600 Value) | 269 | **+3.66 %** | **1.78** | 3.52 % |
| VBR (Vanguard Small Value) | 227 | **+4.03 %** | **1.80** | 3.47 % |
| AVUV (registered underpowered) | 39 | +1.46 % | **−0.02** | — |
| DFSV (registered underpowered) | 10 | −9.66 % | — | — |

Neither deciding fund reaches t ≥ 2.0. **UNRESOLVED**, published with its MDE per
the NIGHT-5 amendment: this comparison could not have detected a difference
smaller than ~3.5 %/yr.

### The disclosure that matters more than the headline

**One year carries almost half of it.** 2020 alone returns **+46.3 %** excess
against IJS. Remove that single calendar year:

| Fund | Full | **Ex-2020** |
|---|---:|---:|
| IJS | +3.66 %/yr, t 1.78 | **+2.01 %/yr, t 1.18** |
| VBR | +4.03 %/yr, t 1.80 | **+2.19 %/yr, t 1.27** |

The ex-2020 numbers land almost exactly on the French proxy's **+2.03 %/yr at
t 1.13** from NIGHT-4. Two independent instruments, the same answer: **about two
points a year, not distinguishable from zero.** The proxy was right.

Positive in **13 of 23 years** against IJS and **12 of 19** against VBR. Worst
year −19.2 % (2000) and −11.1 % (2022). Negative blocks, named as the standard
requires: *2004-2007 expansion* (−0.7 %/−1.0 %) and *2021-2022 inflation*
(−9.4 %/−9.1 %).

### The finding hiding inside a failed prediction

I predicted (R4, confidence 0.7) that the funds would **span** the book — that
its factor-adjusted alpha against them would have t < 2. Wrong, and not
marginally: alpha vs IJS is **+7.17 %/yr at t 5.07**, and adding NIGHT-4's own
small-cap profitability factor barely dents it (**+6.82 %, t 4.06**).

That is the opposite of NIGHT-4, where the same profitability factor absorbed
nearly everything. The reconciliation is not a contradiction, and it is the
product's real sentence:

> **IJS and VBR are *value* funds. They are not running our trade.** Beating them
> is a different-strategy comparison, not a same-strategy-cheaper one.
> **AVUV *is* running our trade** — small-cap value tilted to profitability — and
> against AVUV the book adds **+1.46 %/yr at t −0.02**, i.e. nothing, over the
> only 39 months we can measure.

**Predictions 1 of 4** (R1 HIT; R2, R3, R4 all MISS).

---

## 2. G7 clock comparison — the monthly panel has been flattering churn

NIGHT-5 found the six rebalance clocks statistically indistinguishable on the
monthly panel and kept annual on *mechanical* grounds. G7 can now measure that
mechanism instead of modelling it.

| Start NAV | Clock | Daily CAGR | vs its own monthly harness | Costs paid |
|---:|---:|---:|---:|---:|
| $1 m | monthly | 11.02 % | **−220 bps/yr** | **$935,674** |
| $1 m | annual | 13.45 % | −28 bps/yr | $333,165 |
| $50 m | monthly | 11.29 % | −193 bps/yr | $42.4 m |
| $50 m | annual | 13.20 % | −53 bps/yr | $16.9 m |

**Under daily execution, annual beats monthly by +2.43 %/yr at $1 m and
+1.91 %/yr at $50 m.** On a $1 m account the monthly clock pays **$602,509 more
in costs over 23 years — 60 % of the starting capital.**

**The important number is the ratio.** The monthly harness's modelled cost frame
put the annual advantage at about 89 bps/yr (120 − 31 bps of drag). G7 measures
**243 bps/yr**. The monthly panel understates the cost of frequent trading by
roughly **2.7×**.

This does not overturn NIGHT-5's statistics — the *paired daily* difference is
still only t 1.33 ($1 m) and t 0.99 ($50 m), because daily return noise swamps
it. But the cost saving is **accounting, not inference**: given those trades, at
those spreads, that money was spent. The mechanical case for annual is roughly
three times stronger than we had it.

### What this implies beyond this strategy

Every high-turnover candidate ever judged on the monthly panel with a modelled
cost frame was **flattered**. That cuts toward the graveyard census's
`REJECTED` column, not away from it: the 29 `IMPLEMENTATION_FAILED` rows and the
high-turnover `POWER_FAILED` rows are, if anything, deader than recorded. It is
also a standing reason to route any future turnover-sensitive claim through G7
before believing it.

---

## 3. Where the product note stands after tonight

`docs/PRODUCT_NOTE_v0.1_2026-08-09.md` needs one revision and one confirmation:

* **Confirmed:** the ~2 %/yr figure over a buyable alternative survives contact
  with real funds, once the COVID year is set aside. It remains at t ≈ 1.2.
* **Revised:** the honest comparator is **AVUV**, not IJS/VBR, because AVUV runs
  the same trade. Against it we have **39 months and no measurable edge**. The
  note should say that plainly rather than lead with the value-fund comparison,
  which flatters us for the wrong reason.
* **Strengthened:** the annual-clock recommendation. Not because the returns are
  better — that is still unmeasured — but because the costs it avoids are now
  measured rather than modelled, and they are large.

---

## 4. Scoreboard

Predictions **1 of 4** on the product trial. The three misses were all in the
same direction: I expected the real funds to be *harder* to beat than the
academic proxy and expected them to span the book. They were easier, and they do
not span it — because they are not running the same strategy, which is exactly
why beating them is the less interesting number.

Registry cumulative **102**. Denominator and deflated bars attached to the
artifact as standing procedure.
