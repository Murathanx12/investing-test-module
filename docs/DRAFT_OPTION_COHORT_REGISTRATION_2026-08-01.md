# DRAFT — option-implied cross-sectional cohort (NOT REGISTERED, NOT FROZEN)

**Status: DRAFT FOR REVIEW. Nothing here is registered. No candidate is counted.
Cumulative candidates remain 166.** Per roadmap v2 §3 P3 (AI_PANEL_2026-08-01_
ROUND16). Murat and the next session freeze or reject this after review.

Registered as **one cohort, all six arms together**, deliberately mirroring
INSTR-SMALL-SHELF, so the family cannot be garden-of-forking-paths'd one arm at
a time. If this is split into six separate registrations later, that is itself a
protocol violation.

---

## P0b verification — the data is on disk and it is good

Run this session against `data/wrds_raw/`. The pull completed while the session
was running (manifest `2026-08-01T12:27:44Z`, all 23 years present).

| check | result |
|---|---|
| vsurf month-end years 2002-2024 | **23/23 present, none empty** |
| rows/year | 226,480 (2002) -> 559,472 (2023); secids 2,588 -> 6,250 |
| `optionm_crsp_link` (wrdsapps.opcrsphist) | 121,773 rows; 34,881 with permno; 33,537 secids -> 28,156 permnos |
| link score quality | 28,336 of 34,881 at score **1** (best) |
| 2015 surface secids linkable to CRSP | **4,649 / 4,718 (98.5%)** |
| coverage of the traded universe, 2015-06-30 | **largemid 997/1000 (99.7%)**, small 1,693/1,955 (86.6%) |
| daily option volume aggregates | present (`optionm_opvol_daily`, cols: opt_vol, call_vol, put_vol, open_int, n_contracts) |

**ATM IV spot-check vs public history — AAPL (secid 101594 -> permno 14593),
30-day, mean of +/-50 delta:**

| date | our value | public expectation |
|---|---|---|
| 2008-09-30 | **0.805** | Lehman fortnight — extreme | OK |
| 2008-10-31 / 11-28 | 0.658 / 0.727 | crisis-elevated | OK |
| 2008 calm months | 0.37 - 0.48 | typical AAPL | OK |
| 2017 (all months) | 0.156 - 0.283 | famously quiet year | OK |
| 2020-02-28 / 03-31 | 0.489 / 0.536 | COVID crash | OK |

The surface is real, correctly scaled and correctly timed. **P0b is VERIFIED.**

### The one caveat, and it is not cosmetic

The 30-day +/-50-delta surface is **4.53% null overall** (96,778 / 2,135,956) —
and the nulls are **not random in time**:

| era | null rate |
|---|---|
| 2004-2006 (calm) | 0.77 - 0.90% |
| 2008 / 2009 | 3.56% / 4.85% |
| **2020** | **13.02%** |
| 2022 / 2023 | 6.71% / 8.69% |

OptionMetrics suppresses the surface when its fitting criteria fail, and that
happens **disproportionately in stress** — precisely the states where a
volatility-based signal is supposed to earn its keep. AAPL, the most liquid
optionable name in the world, has all eight surface points null on 2020-07-31
(the date itself is present with 4,240 other secids, so this is vendor
suppression, not a pull gap — likely the 4-for-1 split announced 2020-07-30).

**Consequence for the registration: the null-handling rule must be frozen up
front, because it has a selection effect.** Dropping nulls silently drops
stressed names in stressed months; forward-filling carries a stale calm-period
vol into a crisis. Neither is neutral. Draft rule below; this is the single most
important thing for review to rule on.

---

## Hypothesis (draft)

Option markets price information about the underlying that the equity
cross-section has not yet impounded. Six constructs, each with its own
literature, tested as one pre-declared cohort under the standard harness.

## Arms — six, each a counted candidate (would take cumulative 166 -> 172)

| # | arm | construct | direction | source |
|---|---|---|---|---|
| 1 | `iv_atm` | 30-day ATM IV level (mean of +/-50 delta) | -1 | vol-risk-premium / low-vol lineage |
| 2 | `riv_spread` | 30-day ATM IV minus trailing 21-day realised vol | -1 | Alexiou-Rompolis 2021 |
| 3 | `skew_25d` | 25-delta put IV minus 25-delta call IV, 30-day | -1 | Xing-Zhang-Zhao 2010 |
| 4 | `term_slope` | 91-day ATM IV minus 30-day ATM IV | +1 | Vasquez 2017, Kim 2020 |
| 5 | `os_ratio` | option volume / stock volume, monthly mean of daily | +1 | Johnson-So 2012 |
| 6 | `pc_volume` | put volume / call volume, monthly mean of daily | -1 | Pan-Poteshman 2006 |

Directions are declared **now**, before any run. A sign flip after the fact is a
new candidate in a future cohort, never a free retry — the programme has five
recorded sign reversals and that rule exists because of them.

## Declared prior: WEAK-NEGATIVE, with one arm carrying a specific receipt

1. **§23 + §26 both bear on any residualised variant.** The panel proposed a
   Wu-Tian (2023) *residual*-skew arm. It is **deliberately excluded from this
   draft**, because residualisation has now failed twice in two structurally
   different construction classes: on factor returns (§23, fitted leg carried IC
   t 2.80 of 2.84) and on firm characteristics (§26, pooled t_ic(io_abn) 6.89 vs
   t_ic(io_level) 7.77, i.e. the residual carried *less* than the raw level). If
   review wants the residual-skew arm, it should be added as a **seventh** arm
   with those two receipts declared against it, not substituted for arm 3.
2. **CZ-CALIB fame decay (-0.544):** arms 3 and 6 are large, famous published
   effects. That predicts decay here.
3. **Coverage is a live constraint in small.** 86.6% linkage means the small
   segment loses ~13% of names non-randomly (the least optionable = least
   liquid). The small-segment result is therefore a statement about *optionable*
   small caps, and must be worded that way.

**Honest predictions to be scored (attach as scoreable forecasts):**
`riv_spread` is the most likely single survivor at IC t 1.0-2.0, net t < 1.0;
`os_ratio` highest turnover and dead net; `iv_atm` largely subsumed by the
existing volatility candidates already banked; **0-1 arms graduate.**

**External ledger predictions R15-2 / R15-3 attach here as declared, scoreable
forecasts** — with the caveat recorded in AI_PANEL round 16 §2 that
Perplexity's RIV-spread interval was numerically identical to DeepSeek's R15-2
(net t 0.4-1.0, IC t 1.0-2.0, 65%) and is logged as an **echo of our own
briefing, not an independent prediction**. It is scored, but not credited as
corroboration.

## Evaluation (draft — deliberately identical to every other cohort)

- Factory `scan_signal`, monthly formation, **explore 2004-01..2018-12 only**.
- Segments largemid + small; EW-universe benchmark; 30% hold band; deciles.
- Deciding cost arms: **largemid @ flat25**, **small @ KO-half**, with the
  zero-cost bound and flat-25 regression guard reported alongside (post-§25
  convention: never quote a single-model cost number without the interval).
- Graduation: t_ic >= 2.0 AND t_gross >= 1.5 AND t_net >= 1.5, per segment.
- Only a graduate earns the one confirm shot (2019-2024: net > 0 AND
  t_net >= 0.8 AND t_ic >= 1.5). Confirm on a graduate is Murat's authorisation,
  since it burns the one read.
- DSR reported at n_trials = 172.

## FROZEN NULL-HANDLING RULE (draft — the key review question)

Proposed, to be frozen before any run:

> A name-month with a null in the arm's required surface field is **DROPPED for
> that month** (not forward-filled, not imputed). The monthly count of dropped
> names is recorded per arm and reported with the results, and the drop rate is
> reported **split by market state** (VIX tercile) so the stress-correlated
> missingness is visible rather than buried.

Rationale: forward-filling a calm-period IV into a crisis month is a
lookahead-flavoured lie about what was knowable; dropping is honest but
selective, and the selectivity is at least *measurable*. Declaring the split-by-
state reporting now prevents the result being read as if coverage were uniform.

## Kill condition (draft)

One shot per arm, six arms, one cohort. No arm's spec, direction, window,
null-rule or bar may change after the freeze. If no arm graduates, the
**option-implied cross-sectional family closes** and is not reopened by a new
construct without a mechanism class distinct from level, spread, skew, term
structure and flow — which is all five mechanism classes the literature offers,
so in practice this cohort is the family's one real test. Reported never
deciding: turnover, maxDD, coverage, per-arm null rates.

## Open questions for review

1. Null rule: drop vs ffill-with-cap. (Recommendation: **drop**, as drafted.)
2. Include the Wu-Tian residual-skew arm as a 7th, with §23 + §26 declared
   against it? (Recommendation: **yes, as a 7th** — it is the cleanest possible
   third test of the residualisation generalisation, and the programme now has a
   strong enough prior that a third confirmation would let us state it as a
   house finding rather than a two-instance coincidence.)
3. Should the small segment be run at all given 86.6% coverage, or reported as
   "optionable small caps" only? (Recommendation: run it, word it precisely.)
