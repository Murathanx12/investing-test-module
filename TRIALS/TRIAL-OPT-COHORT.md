# TRIAL-OPT-COHORT — option-implied cross-section, seven arms, one cohort, one shot

**Registered 2026-08-01, FROZEN BEFORE ANY RUN CODE IS WRITTEN.**
Cumulative candidates **167-173** (seven arms, each counted).
Supersedes `docs/DRAFT_OPTION_COHORT_REGISTRATION_2026-08-01.md` (drafted by the
2026-08-01 Opus execution session, reviewed and frozen by the orchestrating
session the same day; the three open review questions are ruled below).
Data: P0b/P0c pulls, VERIFIED in the draft (23/23 vsurf years, largemid link
coverage 99.7%, AAPL ATM IV matches public history).

Registered as **one cohort, all seven arms together**, deliberately mirroring
INSTR-SMALL-SHELF, so the family cannot be garden-of-forking-paths'd one arm at
a time. Splitting it into separate registrations later is itself a protocol
violation.

## Hypothesis

Option markets price information about the underlying that the equity
cross-section has not yet impounded. Seven constructs, each with its own
literature, tested as one pre-declared cohort under the standard harness.

## Arms — seven, each a counted candidate

| # | arm | construct | direction | source |
|---|---|---|---|---|
| 167 | `iv_atm` | 30-day ATM IV level (mean of ±50 delta) | −1 | vol-risk-premium / low-vol lineage |
| 168 | `riv_spread` | 30-day ATM IV minus trailing 21-day realised vol | −1 | Alexiou-Rompolis 2021 |
| 169 | `skew_25d` | 25-delta put IV minus 25-delta call IV, 30-day | −1 | Xing-Zhang-Zhao 2010 |
| 170 | `term_slope` | 91-day ATM IV minus 30-day ATM IV | +1 | Vasquez 2017, Kim 2020 |
| 171 | `os_ratio` | option volume / stock volume, monthly mean of daily | +1 | Johnson-So 2012 |
| 172 | `pc_volume` | put volume / call volume, monthly mean of daily | −1 | Pan-Poteshman 2006 |
| 173 | `skew_resid` | residual of `skew_25d` from a **per-month cross-sectional OLS** on log(mktcap), trailing 21-day realised vol, mom_12_1, log(3-month mean dollar volume); regressors winsorised 1%/99% per month; names missing any regressor dropped | −1 | Wu-Tian 2023 (**style, not verbatim** — their structural proxies include default risk we do not hold; OUR four regressors are frozen here, before any run) |

Directions are declared **now**. A sign flip after the fact is a new candidate
in a future cohort, never a free retry — the programme has five recorded sign
reversals and this rule exists because of them.

## Ruling on the draft's three open questions (2026-08-01, orchestrating session)

1. **Null rule: DROP, as drafted** — frozen below, with one addition (the
   high-coverage robustness line).
2. **Wu-Tian residual-skew: ADDED as arm 7 (#173)**, not substituted for arm 3,
   with §23 + §26 declared against it. It is the cleanest available third test
   of the residualisation generalisation: two receipts exist (factor returns,
   §23; firm characteristics, §26) and a third independent construction class
   (option-implied skew) either establishes it as a house finding or bounds it.
   **Either outcome is informative, which is what earns it the candidate slot.**
3. **Small segment: RUN, worded precisely** — every small-segment statement in
   the results must say *optionable* small caps (86.6% linkage, missing names
   are the least-liquid tail, non-random).

## Declared prior: WEAK-NEGATIVE, with arm-specific receipts

1. **§23 + §26 against `skew_resid`:** residualisation has failed twice in two
   structurally different construction classes — the fitted leg carried the
   information both times (§23: fitted IC t 2.80 of 2.84; §26: t_ic(io_abn)
   6.89 < t_ic(io_level) 7.77). Prediction for the third test: **t_ic(skew_resid)
   ≤ t_ic(skew_25d)**, i.e. the receipts generalise.
2. **CZ-CALIB fame decay (−0.544):** arms 169 and 172 are large, famous
   published effects; that predicts decay here.
3. **Coverage:** the small segment loses ~13% of names non-randomly.

**House predictions to be scored (declared now):** `riv_spread` the most likely
single survivor at IC t 1.0-2.0 with net t < 1.0; `os_ratio` highest turnover
and dead net; `iv_atm` largely subsumed by banked volatility candidates;
**0-1 arms graduate.**

**External ledger predictions R15-2 / R15-3 attach here as scoreable
forecasts** (both: net t 0.4-1.0, IC t 1.0-2.0). Perplexity's round-16 restated
interval is logged as an echo of our own briefing (AI_PANEL round 16 §2) — it
is scored against DeepSeek's R15-2 only, not credited twice.

## Frozen evaluation (identical to every other cohort)

- Factory `scan_signal`, monthly formation, **explore 2004-01..2018-12 only**.
- Segments largemid + small (small = *optionable* small caps, per ruling 3);
  EW-universe benchmark; 30% hold band; deciles.
- Deciding cost arms: **largemid @ flat25**, **small @ KO-half**; zero-cost
  bound and flat-25 regression guard reported alongside (post-§25 convention:
  never a single-model cost number without the interval).
- Graduation: t_ic ≥ 2.0 AND t_gross ≥ 1.5 AND t_net ≥ 1.5, per segment. Only
  a graduate earns the one confirm shot (2019-2024: net > 0 AND t_net ≥ 0.8
  AND t_ic ≥ 1.5). **Confirm on a graduate is Murat's authorisation** — it
  burns the one read.
- DSR reported at n_trials = **173**.

## FROZEN NULL-HANDLING RULE

A name-month with a null in the arm's required surface field is **DROPPED for
that month** — not forward-filled, not imputed. The monthly count of dropped
names is recorded per arm and reported with the results, and the drop rate is
reported **split by market state (VIX tercile)** so the stress-correlated
missingness (0.8% in 2004-06 vs 13.0% in 2020) is visible rather than buried.

**Robustness line (added at freeze, reported never deciding):** for any arm
whose top-VIX-tercile drop rate exceeds 2× its bottom-tercile rate, the results
must also report the arm's IC sign and t on the **always-covered subsample**
(names with ≥95% surface coverage over the explore window), computed once. If
the sign flips there, the arm's verdict carries a disclosed selection caveat.
This line cannot graduate or kill an arm — it exists so a selection artifact
cannot hide inside a pass.

Rationale: forward-filling calm-period IV into a crisis month is a
lookahead-flavoured lie about what was knowable; dropping is honest but
selective, and the selectivity is measurable and now measured.

## Kill condition

One shot per arm, seven arms, one cohort. No arm's spec, direction, window,
null rule or bar may change after this commit; a crash before results are
readable is repairable (disclosed), a completed run is final. If no arm
graduates, the **option-implied cross-sectional family closes** — level,
spread, skew, term structure, flow and residual are all the mechanism classes
the literature offers, so this cohort is the family's one real test. Reported
never deciding: turnover, maxDD, coverage, per-arm null rates, the robustness
line. No forward lane is seeded by this trial under any outcome.
