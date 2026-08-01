# INSTR-RANK-DEAD — where does the rank information go? (the replication bridge)

**Registered 2026-08-02, FROZEN BEFORE ANY RUN CODE IS WRITTEN.**
Instrument, one shot. Cumulative candidate **174**.
Authority: Murat's 2026-08-02 direction (continue working; the "are we testing
wrong / why do published projects conflict with us" concern is the explicit
motivation). Run assignment: next Opus session.

## Why this exists

**Rank-real/book-dead is now the most-repeated unexplained pattern in the
ledger**, three occurrences from three unrelated data sources:

| receipt | signal (segment) | IC t | gross t (long-only top decile) |
|---|---|---|---|
| §26 | `io_level` (small) | **11.29** | **+0.02** |
| §27 | `skew_25d` (optionable small) | **8.34** | ≈ +1 |
| §27 | `skew_resid` (optionable small) | 7.90 | ≈ +1 |

Simultaneously, Murat has raised the program's most important standing
question: published, well-documented results conflict with our rejections —
is the method broken? This instrument answers both with one decomposition,
because they are the same question: **published papers measure long-short,
value-and-equal-weighted, gross spreads; our graduation bar measures a
long-only, cost-charged top-decile book.** If the information lives in the
short leg or the untradeable tail, both facts are explained at once — and if
it doesn't, we have found a genuine anomaly in our own harness and must say so.

## Frozen scope — two signals, one window, all gross

Signals: **`io_level` (small)** and **`skew_25d` (optionable small)** — the two
independent data sources with the starkest pattern. Rebuilt from their frozen
trial builders (TRIAL-ABIO-KIRK, TRIAL-OPT-COHORT), unchanged: same direction,
same lag, same null rules, same universe eligibility. **Explore 2004-2018
only.** Everything below is GROSS — no cost model appears anywhere in this
instrument, so no cost dispute (§25) can touch it.

**The ladder (per signal):**

- **L1 — published conditions:** decile **long-short spread** (D10 − D1),
  equal-weighted AND value-weighted, monthly, gross. This is the construction
  class the literature reports.
- **L2 — leg split:** top-minus-universe (exactly the banked book's gross leg)
  vs **universe-minus-bottom** (the short leg's long-only mirror), EW, gross.
- **L3 — tradability split:** rank-IC computed separately within the upper and
  lower halves of the segment by dollar-volume rank (is the information
  concentrated below tradability?).

## Pre-declared readings (frozen now, so the result cannot be re-narrated)

- **R1 — "conditions, not code":** if L1 spread t ≥ 3.0 while the banked
  long-only gross t stays ≈ 0 (≤ 0.5), the conflict with published work is
  explained by construction conditions. The harness sees what the papers see;
  the wall rejects what a real long-only account cannot earn. House finding.
- **R2 — "the information is short-side":** if the bottom leg's t exceeds the
  top leg's by ≥ 2× (or bottom ≥ 2.0 while top < 1.0), recorded as: the rank
  information is concentrated in names to AVOID, not names to buy. A long-only
  mandate can use this only defensively (screening), never as a return source.
- **R3 — "below tradability":** if lower-half-liquidity IC t ≥ 2× upper-half,
  the information lives where the book cannot go.
- **R4 — "the puzzle stands":** if L1 is ALSO dead gross (spread t < 1.5 both
  weightings), the pattern is unexplained at this resolution; recorded as such,
  **no further re-cuts** — a mechanism-level hypothesis would need a new
  registration.

R1-R3 are not mutually exclusive; each is scored independently.

## Kill / scope

One shot. This instrument **cannot revive, graduate, or seed anything.** The
short legs and spreads are measured for explanation only — the program is
long-only by mandate and no short construct becomes a candidate here. Sign
flips remain banned. A crash before results are readable is repairable
(disclosed); a completed run is final.

## Honest prior (declared before the run)

R1 and R2 both fire: L1 spreads are large (the published effects are real as
*spreads*), and the bottom leg carries most of it (§26's own hypothesis line:
"information in the LOWER tail, unharvestable long-only"). If instead R4
fires, the next conversation is about the harness itself — stated in advance
so that outcome is a commitment, not an embarrassment to be buried.

---

# RESULTS — run 2026-08-02, one shot, explore 2004-2018, all gross

**Chain:** frozen at module commit `98c99e2` (readings R1-R4 and every
threshold declared before any run code existed) -> `aegis_brain/factory/
rank_dead.py` + `tests/test_rank_dead.py` written after -> guard passed ->
one shot. No repair was needed; nothing was re-cut.

## The guard passed exactly

The frozen builders were called unchanged and had to reproduce their banked
explore IC t before a single ladder number was computed. They did, to the
decimal, and so did the banked gross t that was never part of the guard:

| signal | months | IC mean | IC t measured | IC t banked | gross t measured | gross t banked |
|---|---|---|---|---|---|---|
| `io_level` (small) | 180 | 0.0491 | **11.29** | 11.29 | **+0.02** | +0.02 |
| `skew_25d` (optionable small) | 180 | 0.0218 | **8.34** | 8.34 | **+1.01** | +1.01 |

The receipts in §26 and §27 are reproducible from the frozen code. Whatever the
pattern is, it is not a transcription error.

## The ladder

All numbers gross, monthly, small segment, 180 months.

| rung | `io_level` bps/mo | t | `skew_25d` bps/mo | t |
|---|---|---|---|---|
| **L1** D10−D1 equal-weighted | **+145.8** | **5.92** | **+112.5** | **6.52** |
| **L1** D10−D1 value-weighted | **+77.6** | **3.96** | **+70.9** | **4.94** |
| **L2** top − universe (the banked book) | +0.2 | 0.02 | +12.4 | 1.01 |
| **L2** universe − bottom (the mirror) | **+150.6** | **8.50** | **+93.4** | **7.30** |
| **L3** rank-IC, upper liquidity half | 0.0323 | 7.55 | 0.0201 | 5.14 |
| **L3** rank-IC, lower liquidity half | 0.0531 | 9.29 | 0.0255 | 7.45 |

## Which pre-declared readings fired

| reading | `io_level` | `skew_25d` |
|---|---|---|
| **R1** conditions, not code | **FIRED** | no (see below) |
| **R2** the information is short-side | **FIRED** | **FIRED** |
| **R3** below tradability | no | no |
| **R4** the puzzle stands | no | no |

**R1 fired on `io_level`** — L1 spread t 5.92 (EW) and 3.96 (VW) against a
banked long-only gross t of +0.02. On `skew_25d` R1 misses on its literal
second clause only: the frozen text requires the banked gross t to be ≤ 0.5 and
it is 1.01. The first clause clears by a mile (spread t 6.52 / 4.94). Scored as
written, not as intended — but the substance is identical in both signals and
should be read that way.

**R2 fired on both, and it is the dominant reading.** The equal-weighted spread
decomposes almost entirely into the leg a long-only mandate cannot hold:
150.6 of 150.8 bps for `io_level` (**99.9%**) and 93.4 of 105.8 for `skew_25d`
(**88%**). (The two legs do not sum exactly to the L1 spread because L1 is a
plain decile sort while L2 is the banked book, hold band and all.)

**R3 did not fire on either signal, and that is the surprise.** The lower
liquidity half carries more IC than the upper — 9.29 vs 7.55 and 7.45 vs 5.14 —
but nowhere near the 2× the reading required (ratios 1.23 and 1.45). The upper,
more tradable half of the small segment carries strongly significant rank
information on its own. **The information is not hiding below tradability. It
is hiding in the short leg, at every level of liquidity.**

**R4 did not fire**, so the harness audit branch is not triggered and no
attended decision is owed on that front.

## What this answers

The standing question was whether we are testing strategies wrong. The answer
this instrument supports is: **no, we are testing a different thing, on
purpose, and the difference is the short leg.**

Under published conditions — decile long-short, gross, both weightings — both
signals produce large, highly significant spreads. A paper reporting either one
would be reporting a real number. Our harness sees exactly the same number; it
simply does not bank it, because the graduation bar reads a long-only,
cost-charged top-decile book, and the top decile is where these signals have
nothing to say. High institutional ownership does not predict outperformance;
LOW institutional ownership predicts underperformance. Low put-call skew does
not predict outperformance; high skew predicts underperformance.

Two consequences follow, and neither licenses any new work here:

1. **The conflict with the literature is resolved and is not a defect in the
   harness.** It is a mandate difference. Any future comparison of one of our
   rejections to a published effect must state the construction class or it is
   comparing two different objects.
2. **A long-only mandate can only ever use these signals defensively** — as an
   exclusion screen, never as a return source. Whether an exclusion screen
   survives our bars is a separate question that would need its own
   registration; the frozen scope forbids opening one here, and none was opened.

The value-weighted spread is materially smaller than the equal-weighted one in
both signals (77.6 vs 145.8; 70.9 vs 112.5), which is the usual small-name
tilt and is reported for completeness. It changes no reading.

## Scope honoured

Nothing was revived, graduated or seeded. No cost model was loaded. The confirm
window was not read. Cumulative candidate count unchanged at **174** for this
instrument; nothing new was registered.

## The declared honest prior scored

Declared before the run: *"R1 and R2 both fire ... if instead R4 fires, the next
conversation is about the harness itself."* R1 and R2 both fired (R1 on one
signal literally, both in substance); R4 did not. **Correct.** R3 was not part
of the prior and did not fire — the one thing this instrument taught that
nobody had predicted is that the information is NOT concentrated below
tradability.
