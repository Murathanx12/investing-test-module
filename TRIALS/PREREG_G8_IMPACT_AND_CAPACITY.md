# PREREG — TRIAL-G8-IMPACT-AND-CAPACITY-1

**Registered:** 2026-08-10 (NIGHT-9), before compute · **Family:** instruments
**Stage:** gate calibration · **Supersedes the scope of:** `CAPACITY-EDGE-1`
(blocked on NIGHT-8 because the instrument could not price what it was being
asked about)

Resurrects: CAPACITY-EDGE-1 — new instrument: a metaorder price-impact term
(`aegis_brain/pf/impact.py`) that charges size against ADV, where G7 charged
only delay.

## 1. What NIGHT-8 established

G7's cost per dollar traded is **31.00 bps at ADV multiples of 1,000,000×, 100×,
5× and 1×** — identical across a million-fold range of liquidity. G7 expresses
scarcity as *delay*: an order too large for the day is carried forward and
eventually fills at the same quoted terms. Consequently **every capacity number
this programme has published is a delay-only lower bound**, including NIGHT-5's
"$100m → $500m" and NIGHT-7's $50m rung.

## 2. What is being built, and what is deliberately not

`impact.py` implements the **metaorder square-root law**

> impact (fraction of price) = `coef` × `sigma_daily` × sqrt(`Q` / `ADV`)

charged on the whole order at creation and amortised across its fills, so
working an order down over more days does not escape it. That escape is exactly
what produced NIGHT-8's flat 31.00 bps.

**`coef` is a scenario, not a measurement.** The published prefactor range is
roughly 0.25–1.0 and we have no broker TCA of our own, so every number below is
quoted as a **low / base / high band** (0.25 / 0.50 / 1.00). A point estimate
would be a fabricated precision.

Not modelled, declared before any result is read: execution urgency/horizon
(`urgency_exp` defaults to 0, so a slower participation cap buys no relief),
permanent-versus-temporary decomposition, and cross-impact between names traded
together. G8 prices **size**, not **speed**.

**G7 is not modified.** `impact_coef = 0.0` skips the arithmetic entirely, and
the receipt records `execution_model: G7` or `G8` accordingly.

## 3. The instrument is calibrated before its verdicts are trusted

Fifteen invariants, in `tests/test_impact_g8.py`, all of them written from the
failure they prevent:

| invariant | why |
|---|---|
| `coef = 0` reproduces G7 | historical outputs must stay comparable |
| impact rises with order size, falls with volume, rises with volatility | the three things G7 could not see |
| concave: doubling size raises cost per dollar by √2, not 2 | capacity degrades smoothly, not at a cliff |
| a name with **no** volume is the *most* expensive case, not free | the natural bug is to charge zero for a division by zero |
| trailing ADV and sigma do not include today | an impact charged with today's volume is a look-ahead |
| explicit + impact = total, exactly | the accounting must close |
| bigger AUM costs more per dollar traded | **this is the property NIGHT-8 proved G7 lacks** |
| the warm-up fallback is never load-bearing in a warmed-up world | a fallback that fires silently is the house failure mode |

## 4. Design

**Part A — synthetic re-run of NIGHT-8's null.** The same worlds (ADV multiples
1e6 / 100 / 5 / 1) through G7 and through G8 at all three coefficients. G7's row
must reproduce 31.00 bps at every rung; G8's must not.

**Part B — the real book, re-simulated.** `PF-PROF-COMPOSITE-150` on the annual
clock, 2002–2024, starting NAV ladder $1m / $10m / $50m / $100m / $250m through
G7 and G8-base, with G8-low and G8-high at the two rungs that matter for the
answer. **Rungs are re-simulated, never scaled** (CANON §16).

**Capacity is defined operationally, not as a single number.** The frozen limit:

> the largest starting NAV at which **total cost drag ≤ 1.00% per year of
> average NAV** *and* **unfilled desired notional ≤ 1%** *and* the CAGR gap
> versus the $1m rung is ≤ 1.00 pt/yr — all three, under the **base** scenario,
> with the low/high band reported beside it.

## 5. Registered predictions

1. **G7's synthetic row reproduces 31.00 bps at every rung**, confirming the
   refactor changed nothing.
2. **G7's real ladder reproduces the published receipt** at $1m/$10m/$100m
   (36.5 / 37.5 / 39.0 bps). If it does not, everything else stops.
3. **G8-base at $1m adds under 15 bps** of traded value — a $1m book's orders
   are small against small-cap ADV.
4. **Impact bps scales roughly as √NAV**: 100× the capital, ~10× the impact bps.
5. **The base-scenario capacity limit lands between $10m and $100m of starting
   NAV** — well below NIGHT-5's "$500m", which was delay-only.
6. **The G7-vs-G8 gap at the top rung exceeds 2 pt/yr of CAGR**, i.e. the thing
   G7 could not see is economically decisive rather than a rounding term.

## 6. Decision rule (frozen)

| outcome | consequence |
|---|---|
| invariants pass and G7 reproduces | G8 is admissible; capacity may be quoted **as a band, with the coefficient named** |
| any invariant fails, or G7 does not reproduce | G8 is not admissible and no capacity number changes |
| G8-base capacity limit below $10m | the book is a personal-scale strategy; say so plainly in the product note |

**This trial adopts nothing and moves no weight.** It replaces a lower bound
with a scenario-conditional bound. A capacity number quoted without its
coefficient is a violation of this prereg.

## 7. Ledger

Adds **0 strategy branches** — no signal, weight, threshold or holding rule is
searched here. It is an instrument.
