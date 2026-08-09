# TRIAL-PF4-DECOMPOSITION-1 — what is the +4.67 %/yr actually made of?

**Registered:** 2026-08-09, before any PF-4 compute.
**Branch:** `factory/night-4`. **Family:** PF-4. **Class:** ADJUDICATION of an
existing product-track candidate (`PF-PROF-COMPOSITE-150`, spec hash
`a1265dc617fb`).

**Origin:** four external adversarial reviews of
`aegis-finance/docs/EXTERNAL_REVIEW_DOSSIER_2026-08-09.md`, adjudicated at home
by Murat. Three reviews independently converge on the same charge: a
monthly-rebalanced equal-weight small-cap book automatically harvests several
premia that have nothing to do with the profitability signal it is named after.
This trial is the test of that charge. It can only reduce the claim or leave it
standing; it cannot raise it.

---

## 1. Hypothesis

> **H:** After removing (a) everything the book shares with an equal-weight draw
> from its own eligible universe and (b) its loadings on the standard factors,
> the residual contribution of the profitability composite is materially
> positive — at least +2.5 %/yr.

**Honest prior, stated before compute:** the house believes the incremental
number survives above +2.5 %, on one banked piece of evidence and one
theoretical argument. The banked evidence is that the existing scorecard
already carries `excess_vs_ew_universe_cagr = +5.36 %/yr` at t 5.06 — the book
beats an equal-weight draw from its own universe by *more* than it beats the
market, which is the opposite of what "it's just the equal-weighting premium"
predicts. The argument against the house: that number is a RAW excess, and the
reviewers' claim is about ALPHA after factor loadings, which has never been run
against the EW universe. The house may be wrong for exactly that reason.

## 2. Primary metric — the ONE deciding number

**INCREMENTAL SIGNAL CONTRIBUTION** =
annualized FF5+UMD alpha of the **self-financing series**

    d_t  =  (book net monthly return)_t  −  (equal-weight eligible universe)_t

over the book's own window, with a Newey-West(12) t-statistic.

Why this and not the headline: `d_t` cancels, by construction, every effect the
book shares with a no-information draw from the identical universe — the
equal-weighting/rebalancing premium (Plyakha-Uppal-Vilkov), the size and
illiquidity premia of that universe, and the universe's own calendar effects.
The factor regression then removes what is left of the standard exposures. What
survives is what the *selection* did.

Everything else in §5 is **reported, never deciding.**

## 3. Decision rule (frozen)

| incremental alpha | NW t | verdict |
|---|---|---|
| ≥ +2.5 %/yr | ≥ 2.0 | **CONFIRMED** — PROF-COMPOSITE-150 keeps product-track candidacy; the product claim may quote the incremental number |
| ≥ +1.0 %/yr | any | **DIMINISHED** — candidacy retained, but every product statement must lead with the incremental number and disclose the decomposition |
| < +1.0 %/yr | < 1.5 | **CANDIDACY WITHDRAWN** — PF-ENGINE-ALPHA-PRODUCT-2 becomes the only product-track candidate; the paper pivots fully to methodology + negative result |

A result of "≥ +2.5 %/yr but t < 2.0" is **DIMINISHED**, not confirmed: the
point estimate does not clear the bar on its own.

**MDE clause (binding, §4.5 of the standard):** the verdict text must state the
minimum detectable effect at t = 2 for the primary series. A null reads
"smaller than X", never "zero". This clause exists because the house violated it
in NIGHT-3 (see `RETRACTION_NIGHT3_5.2` in this campaign).

**Multiple-testing disclosure:** PROF-COMPOSITE-150 was selected across a
cumulative programme denominator that must be printed in the verdict. The
verdict must state plainly which statistic is being stood on and whether it
clears the Harvey-Liu-Zhu (2016) t > 3.0 bar for a newly claimed factor.

## 4. Frozen parameters

* Window: the book's own inception window, **1982-11-30 .. 2022-12-31**
  (482 months). The holdout (2023-01+) is NOT read and `allow_holdout` stays
  `False`.
* Benchmark: CRSP VW total return (`mktrf + rf`), pinned Ken French vintage.
* Factors: `mktrf, smb, hml, rmw, cma, umd`, same pinned vintage. NW lags 12.
* EW universe control: `buy_and_hold_universe` as already implemented —
  equal-weight, monthly-rebalanced, the identical eligibility mask, **no costs
  charged** (charging the control would flatter the strategy).
* Characteristic-matched placebo: 100 draws, matching cells defined on
  **dollar-volume decile × 12-1 momentum decile × book-to-market decile**,
  computed within the eligible small segment at each formation month.
* Delisting sensitivity: −30 % (Shumway 1997) primary, −55 % (Shumway-Warther
  1999, NASDAQ) stress.
* Era cost floor: half-tick / price, with tick $1/8 through 1997-06,
  $1/16 through 2001-03, $0.01 thereafter.
* Seed 20260809 for every stochastic control.

## 5. Reported, never deciding

1. **EW-universe alpha** — FF5+UMD alpha of the equal-weight eligible universe
   itself. This is the rebalancing-premium leg the reviewers name.
2. **Liquidity/size shift** — rerun dropping the bottom 30 % of the eligible
   universe by dollar volume; Amihud illiquidity loading of the book.
3. **Era-appropriate costs** — the tick-floor overlay, reported by half-window.
   *Recorded limitation:* the spine carries no daily high/low, so Corwin-Schultz
   and Abdi-Ranaldo (CHL) are **not computable** here. The tick floor is a
   mechanical LOWER bound on the true half-spread, so this arm **understates**
   cost and any excess it leaves standing is an upper bound.
4. **Self-built small-cap profitability factor** — EW top-30 % minus bottom-30 %
   of the same composite inside the same eligible universe, added as a seventh
   regressor. This is the correct spanning benchmark; RMW is value-weighted and
   large-cap dominated and is mechanically mismatched to this book.
5. **Calendar decomposition** — January vs non-January.
6. **Buy/hold spread grid** — `hold_band_mult` ∈ {1, 2, 3, 5, 10}
   (Novy-Marx & Velikov). *Recorded before compute:* the live spec already runs
   `hold_band_mult = 3.0`, i.e. buy at rank ≤150 and hold until rank >450, so
   the reviewer's proposed fix is already in place and tighter than proposed.
7. **Rebalance-frequency grid** — 1, 3, 6, 12 months.
8. **Event-time membership profile** — excess in months 1-6 / 7-12 / 13-24 / 25+
   of continuous membership, and the exit hazard.
9. **Product benchmark** — Kenneth French small/robust-profitability portfolios
   as the long-history buyable proxy. AVUV/DFSV from 2019-09 require a PIT-clean
   price source this repo does not have; that comparison is **deferred and
   named**, not silently dropped.
10. **Pre-1982 block** — see §7.

## 6. Registered predictions

Scored in the verdict, hits and misses both. External predictions are the
reviewer's own words, registered against them.

| # | source | prediction |
|---|---|---|
| R-1 | reviewer 4 | incremental profitability contribution lands **+1.5 to +2.5 %/yr** |
| R-2 | reviewer 4 | EW-universe control alpha **+1.5 to +2.0 %/yr** |
| R-3 | reviewer 4 | era-appropriate costs cost **−0.8 to −1.5 %/yr**, concentrated pre-2001 |
| R-4 | reviewer 4 | delisting imputation costs **−0.1 to −0.4 %/yr** |
| R-5 | reviewer 4 | marginal-decile alphas are **flat** if ordering is truly informationless |
| H-1 | house | incremental lands **above** R-1's band, ≥ +2.5 %/yr — because the banked EW-universe raw excess is +5.36 % at t 5.06 |
| H-2 | house | delisting delta **≤ 0.3 %/yr** |
| H-3 | house | non-January excess **≥ +2.5 %/yr** — January is not the majority of the effect |
| H-4 | house | the characteristic-matched placebo is **harder** than the turnover-matched one: its p-value exceeds 0.0099 but stays **< 0.05** |
| H-5 | house | the tick floor costs **more than 1.5 %/yr** pre-2001 — R-3 is too generous, because this book turns over 240 %/yr one-way, not the ~50 % the cited literature assumes |
| H-6 | house | tightening the buy/hold band from 3.0 to 2.0 changes net excess by **less than 0.5 %/yr** in either direction |
| H-7 | house | the self-built small-cap profitability factor **absorbs most of the FF5+UMD alpha** — the book is small-cap profitability, honestly named |

## 7. The pre-1982 block — a correction to the reviewer, registered before compute

Reviewer 4's A3 charges that the 1982-11 start on a 63-year panel is "an
unpre-registered researcher degree of freedom sitting directly on your only
surviving strategy."

**It is not a choice. It was checked before this registration was written**, and
the cause is worse in a more interesting way. The eligible small-cap universe is
*empty* before 1980 and has fewer than the spec's frozen `min_names = 100` until
1982-10. The mechanism is that `Panel.eligible()` applies a **nominal,
never-inflation-indexed floor of $200,000 monthly dollar volume**. In 1963 only
215 names in the entire CRSP universe clear it, and all of them are large caps
(rank ≤ 1000), so the intersection with the small segment (rank 1000-3000) is
empty by construction. $200k of 1963 purchasing power is roughly $2M today.

Consequences, all recorded here rather than in a footnote later:

* The start date is **data-determined by a parameter frozen in the spec before
  the run**, not chosen after seeing results. The reviewer's diagnosis is wrong.
* The reviewer's *instinct* is right anyway: an unexamined nominal floor silently
  costs the programme **19 years** of its own panel, and it does so for **every
  small-segment strategy ever run here**, not just this one.
* PF-4 therefore adds an arm: re-run with the floor indexed to the panel's own
  aggregate dollar volume, and report **1963-1982 as a REPORTED-NEVER-DECIDING
  block**. It cannot promote anything. If the effect is absent there, the
  verdict says so in §5.1 of the dossier.

## 8. Hard constraints

* No lane seeded, no flag flipped, `paper_nav` untouched, no key changes.
* The holdout is not read. `allow_holdout=False` everywhere; the verdict must
  carry the programmatic verification.
* Nothing here may promote a strategy. Every arm can confirm, diminish, or
  withdraw.
* This registration may gain annotations. Hypothesis, primary metric, decision
  rule, thresholds and window are frozen; changing any of them abandons the
  trial and requires a successor.
