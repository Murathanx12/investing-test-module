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

---

# RESULTS — one shot taken 2026-08-02, explore only. FINAL.

**VERDICT (frozen bars, no arm graduated): all seven arms REJECTED. The
option-implied cross-sectional family CLOSES.** Level, spread, skew, term
structure, flow and residual are every mechanism class the literature offers,
and this cohort was the family's one real test. The confirm window
(2019-2024) was **NOT read** — no arm earned it.

**The pre-declared residualisation prediction HELD, in both segments — the
third receipt.**

| segment | `t_ic(skew_25d)` | `t_ic(skew_resid)` | prediction `resid <= raw` |
|---|---|---|---|
| large/mid | 1.17 | **0.41** | ✅ holds |
| small (optionable) | 8.34 | **7.90** | ✅ holds |

## Explore 2004-01..2018-12, 180 months (deciding arms in bold)

| arm | segment | cost arm | net bps/mo | t_net | t_gross | t_ic | turnover | maxDD |
|---|---|---|---|---|---|---|---|---|
| iv_atm | large/mid | **flat25** | **-2.6** | **-0.10** | **+0.05** | **1.85** | 0.076 | -0.326 |
| iv_atm | large/mid | zero-cost bound | +1.3 | +0.05 | +0.05 | 1.85 | 0.076 | -0.319 |
| iv_atm | large/mid | KO-half (reported) | +0.7 | +0.03 | +0.05 | 1.85 | 0.076 | -0.320 |
| iv_atm | small | **KO-half** | **+12.3** | **+0.53** | **+0.63** | **5.45** | 0.171 | -0.404 |
| iv_atm | small | zero-cost bound | +14.5 | +0.63 | +0.63 | 5.45 | 0.171 | -0.399 |
| iv_atm | small | flat25 guard | +6.0 | +0.26 | +0.63 | 5.45 | 0.171 | -0.412 |
| riv_spread | large/mid | **flat25** | **-47.4** | **-2.75** | **-0.51** | **-1.07** | 0.771 | -0.700 |
| riv_spread | large/mid | zero-cost bound | -8.8 | -0.51 | -0.51 | -1.07 | 0.771 | -0.675 |
| riv_spread | large/mid | KO-half (reported) | -18.2 | -1.06 | -0.51 | -1.07 | 0.771 | -0.682 |
| riv_spread | small | **KO-half** | **-55.2** | **-2.88** | **-1.68** | **+0.56** | 0.684 | -0.743 |
| riv_spread | small | zero-cost bound | -32.3 | -1.68 | -1.68 | +0.56 | 0.684 | -0.723 |
| riv_spread | small | flat25 guard | -66.5 | -3.46 | -1.68 | +0.56 | 0.684 | -0.752 |
| skew_25d | large/mid | **flat25** | **-27.0** | **-2.81** | **-0.21** | **1.17** | 0.500 | -0.522 |
| skew_25d | large/mid | zero-cost bound | -2.1 | -0.21 | -0.21 | 1.17 | 0.500 | -0.495 |
| skew_25d | large/mid | KO-half (reported) | -7.2 | -0.75 | -0.21 | 1.17 | 0.500 | -0.502 |
| skew_25d | small | **KO-half** | **-4.1** | **-0.34** | **+1.01** | **8.34** | 0.499 | -0.665 |
| skew_25d | small | zero-cost bound | +12.4 | +1.01 | +1.01 | 8.34 | 0.499 | -0.648 |
| skew_25d | small | flat25 guard | -12.6 | -1.03 | +1.01 | 8.34 | 0.499 | -0.668 |
| term_slope | large/mid | **flat25** | **-42.5** | **-3.46** | **-0.80** | **1.05** | 0.654 | -0.602 |
| term_slope | large/mid | zero-cost bound | -9.8 | -0.80 | -0.80 | 1.05 | 0.654 | -0.578 |
| term_slope | large/mid | KO-half (reported) | -16.3 | -1.33 | -0.80 | 1.05 | 0.654 | -0.584 |
| term_slope | small | **KO-half** | **-19.2** | **-1.45** | **-0.23** | **-0.68** | 0.589 | -0.636 |
| term_slope | small | zero-cost bound | -3.0 | -0.23 | -0.23 | -0.68 | 0.589 | -0.622 |
| term_slope | small | flat25 guard | -32.5 | -2.45 | -0.23 | -0.68 | 0.589 | -0.643 |
| os_ratio | large/mid | **flat25** | **-20.2** | **-1.90** | **-1.66** | **-3.15** | 0.052 | -0.623 |
| os_ratio | large/mid | zero-cost bound | -17.6 | -1.66 | -1.66 | -3.15 | 0.052 | -0.620 |
| os_ratio | large/mid | KO-half (reported) | -18.1 | -1.71 | -1.66 | -3.15 | 0.052 | -0.621 |
| os_ratio | small | **KO-half** | **-92.3** | **-6.68** | **-6.35** | **-6.11** | 0.162 | -0.701 |
| os_ratio | small | zero-cost bound | -87.7 | -6.35 | -6.35 | -6.11 | 0.162 | -0.696 |
| os_ratio | small | flat25 guard | -95.9 | -6.94 | -6.35 | -6.11 | 0.162 | -0.705 |
| pc_volume | large/mid | **flat25** | **-31.3** | **-2.15** | **-0.85** | **-1.98** | 0.380 | -0.595 |
| pc_volume | large/mid | zero-cost bound | -12.3 | -0.85 | -0.85 | -1.98 | 0.380 | -0.583 |
| pc_volume | large/mid | KO-half (reported) | -16.3 | -1.12 | -0.85 | -1.98 | 0.380 | -0.587 |
| pc_volume | small | **KO-half** | **-40.6** | **-2.34** | **-1.36** | **-3.10** | 0.543 | -0.646 |
| pc_volume | small | zero-cost bound | -23.5 | -1.36 | -1.36 | -3.10 | 0.543 | -0.624 |
| pc_volume | small | flat25 guard | -50.7 | -2.92 | -1.36 | -3.10 | 0.543 | -0.658 |
| skew_resid | large/mid | **flat25** | **-35.1** | **-3.35** | **-0.99** | **+0.41** | 0.494 | -0.581 |
| skew_resid | large/mid | zero-cost bound | -10.4 | -0.99 | -0.99 | +0.41 | 0.494 | -0.559 |
| skew_resid | large/mid | KO-half (reported) | -15.5 | -1.48 | -0.99 | +0.41 | 0.494 | -0.565 |
| skew_resid | small | **KO-half** | **-1.7** | **-0.12** | **+1.02** | **7.90** | 0.513 | -0.693 |
| skew_resid | small | zero-cost bound | +14.9 | +1.02 | +1.02 | 7.90 | 0.513 | -0.678 |
| skew_resid | small | flat25 guard | -10.7 | -0.74 | +1.02 | 7.90 | 0.513 | -0.696 |

Bar: t_ic >= 2.0 AND t_gross >= 1.5 AND t_net >= 1.5 per segment on the deciding
arm. **The zero-cost bound graduates nothing either** — the best zero-cost gross
t across all fourteen deciding cells is **+1.02** (skew_resid small). As in
NEG_RESULTS §26, costs are not the executioner; there was nothing to kill.

All small-segment statements here concern **optionable** small caps (ruling 3 at
freeze): ~33-35% of the ranked small universe has no usable surface in a given
month, and the missing names are the least liquid, so this is not a statement
about the small segment as a whole.

## DSR at n_trials = 173 (sr_variance = 0.019718, banked cross-section)

Expected max Sharpe under H0 at 173 trials is **0.3816 monthly**. The best
observed Sharpe across all fourteen deciding cells is **+0.0396** (iv_atm
small). **DSR = 0.0000 for every cell**, without exception. At this point in the
programme the multiple-testing hurdle alone disqualifies the entire cohort
before any cost or bar is applied.

## Frozen reporting: drop rate by VIX tercile

| arm | segment | low | mid | high | high/low |
|---|---|---|---|---|---|
| iv_atm | large/mid | 0.0134 | 0.0119 | 0.0088 | 0.66 |
| iv_atm | small | 0.3310 | 0.3380 | 0.3462 | 1.05 |
| riv_spread | large/mid | 0.0151 | 0.0132 | 0.0099 | 0.66 |
| riv_spread | small | 0.3314 | 0.3383 | 0.3468 | 1.05 |
| skew_25d | large/mid | 0.0134 | 0.0119 | 0.0088 | 0.66 |
| skew_25d | small | 0.3310 | 0.3380 | 0.3462 | 1.05 |
| term_slope | large/mid | 0.0134 | 0.0119 | 0.0088 | 0.66 |
| term_slope | small | 0.3310 | 0.3380 | 0.3462 | 1.05 |
| os_ratio | large/mid | 0.0155 | 0.0134 | 0.0090 | 0.58 |
| os_ratio | small | 0.3236 | 0.3316 | 0.3346 | 1.03 |
| pc_volume | large/mid | 0.0654 | 0.0721 | 0.0598 | 0.91 |
| pc_volume | small | 0.6755 | 0.6930 | 0.6765 | 1.00 |
| skew_resid | large/mid | 0.0285 | 0.0254 | 0.0193 | 0.68 |
| skew_resid | small | 0.3480 | 0.3548 | 0.3628 | 1.04 |

**The robustness line did NOT trigger for any arm** — every high/low ratio falls
in 0.58-1.05, far below the 2.0 threshold that would have required the
always-covered subsample.

This is worth stating plainly because it contradicts the concern that motivated
the rule. The raw surface null rate IS stress-correlated (0.8% in 2004-06 vs
13.0% in 2020), which is why the freeze demanded this reporting. But inside the
**ranked** universe and inside the **explore** window, it is not: large/mid drop
rates actually FALL in high-VIX months (0.0088 vs 0.0134), because volatility
spikes bring option activity to names that lacked it in calm periods. The 13%
figure was driven by 2020, which is in the confirm window and was not read here.
Same shape as the §26 staleness finding: a real, alarming raw number that turns
out not to touch the population being ranked. The frozen conditional was correct
to demand the check and correct not to fire.

## Scoring the house predictions declared at freeze

| declared prediction | outcome | scored |
|---|---|---|
| `t_ic(skew_resid) <= t_ic(skew_25d)` (the residualisation receipt) | 0.41 vs 1.17 large/mid; 7.90 vs 8.34 small | ✅ **HOLDS in both** |
| `riv_spread` the most likely single survivor, IC t 1.0-2.0 | IC t **-1.07** large/mid, +0.56 small | ❌ wrong, and sign-flipped |
| `riv_spread` net t < 1.0 | -2.75 large/mid, -2.88 small | ✅ (trivially) |
| `os_ratio` highest turnover | **LOWEST** (0.052 / 0.162) of all seven arms | ❌ badly wrong |
| `os_ratio` dead net | -20.2 and -92.3 bps/mo | ✅ |
| `iv_atm` largely subsumed by banked vol candidates | t_net -0.10 / +0.53, nothing to subsume | ✅ |
| **0-1 arms graduate** | 0 | ✅ |

Five of seven. The two misses are both about `riv_spread` and `os_ratio`, and
both are informative — see below.

## Scoring the external ledger forecasts

| # | reviewer | prediction | actual | verdict |
|---|---|---|---|---|
| **R15-2** | DeepSeek | RIV-spread, large/mid, explore: net t **0.4-1.0**, IC t **1.0-2.0** | net t **-2.75** (deciding) / -0.51 (zero-cost); IC t **-1.07** | ❌ **MISS on both legs** |
| **R15-3** | GPT | option-implied disagreement (skew / term-structure): net t **0.8-1.5**, IC t **1.5-2.4** | skew_25d large/mid net t -2.81, IC t 1.17; term_slope large/mid net t -3.46, IC t 1.05 | ❌ **MISS on both legs** |

**Disclosed spec mismatch on R15-3**, in the reviewer's favour and recorded
anyway: GPT specified *dispersion* of skew/term structure, and the cohort
registered skew and term-structure **levels**, not their cross-sectional
dispersion. R15-3 is therefore scored against the closest registered
constructs, not against its literal spec. The direction of the miss is large
enough (predicted net t 0.8-1.5, observed -2.81 and -3.46) that the mismatch
does not plausibly account for it, but the caveat belongs in the record.

Both misses share a structure: the reviewers predicted **modestly positive**
net t on option-implied signals in large/mid, and the measured result is
**significantly negative** net t driven by turnover of 0.50-0.77 one-way. No
external reviewer has yet produced a prediction this programme scored as a hit.

## The findings, under both hands

**1. Residualisation now has three receipts, across three construction
classes.** §23 stripped momentum on factor *returns* (fitted leg IC t 2.80 of
2.84). §26 stripped institutional ownership on firm *characteristics* (io_abn
6.89 < io_level 7.77). This trial stripped option-implied *skew* on four
characteristics (0.41 < 1.17 large/mid, 7.90 < 8.34 small). Three independent
mechanism classes, same direction every time, and the prediction was declared
before the run each time. **This is now a house finding, not a coincidence:**
in this harness, residualising a signal on characteristics moves information
into the fitted leg and leaves less in the residual. The practical consequence
is a standing prior — any future "abnormal X" construct starts with three
receipts against it and needs a mechanism argument for why it should differ.

**2. `os_ratio` is a significant ANTI-signal, and the direction was frozen at
+1.** Johnson-So (2012) predicts high option-to-stock volume forecasts high
returns; we measured t_ic **-3.15** large/mid and **-6.11** small, with net
**-92.3 bps/mo at t -6.68** in small. That is among the most strongly
significant results in the entire programme — pointing the wrong way. Under the
frozen rule a sign flip is a **new candidate in a future cohort, never a free
retry**, and none is opened here. This is the §17 pattern (analyst price targets
were an anti-signal too): the un-voided family is worse than dead. Note also
that os_ratio had the *lowest* turnover of all seven arms (0.052 large/mid), so
its negative net is not a cost artifact — the ranking itself is inverted.

**3. The rank-real / book-dead pattern repeats, again.** iv_atm small t_ic
**5.45**, skew_25d small **8.34**, skew_resid small **7.90** — large, highly
significant rank information — against gross excess t of +0.63, +1.01 and +1.02.
Identical in shape to §26's io_level (t_ic 11.29, gross t +0.02). Three
consecutive trials have now produced high-IC/zero-book results in the small
segment, from unrelated data sources (13F ownership, option surface). The
hypothesis that keeps suggesting itself — the information sits in the lower
tail, unharvestable by a long-only top-decile book — remains **untested and
unregistered**. It is now the most-repeated unexplained pattern in the ledger
and is the obvious candidate for a dedicated instrument, which is a Murat
decision, not a session decision.

**4. Turnover is what kills the surface arms.** riv_spread (0.771), term_slope
(0.654), pc_volume (0.543), skew_resid (0.513) and skew_25d (0.500) all turn
over half to three-quarters of the book monthly. The gap between their zero-cost
and deciding numbers is 30-40 bps/mo. But the zero-cost bound still does not
graduate them, so this is an explanation of *how far* they are from viable, not
an argument that a cheaper implementation would rescue them.

## Repairs disclosed

**REPAIR 1 — the link-ambiguity rule, settled before any number existed.** The
first implementation applied TRIAL-ABIO-KIRK's blanket rule: drop a name-month
whenever one permno maps to more than one secid. Measured at 2011-06-30 that
dropped 1,041 permnos, of which **660 had no secid carrying data at all** (dead
OptionMetrics link records, almost all link score 4-5), **379 had exactly one
secid with data** (score 1), and **only 2 had more than one**. The blanket rule
was discarding 379 perfectly resolvable names a month — roughly 11% of the
usable cross-section — to disambiguate 2.

Fixed to judge ambiguity among secids that actually carry data that month, which
is the faithful reading of "drop when you cannot tell which one": the forward
direction (one secid, several permnos) is always dropped since nothing can
resolve it; the reverse is dropped only when more than one of a permno's secids
carries data. Effect: reverse-ambiguity drops fell **770,482 -> 658**, 1,501,004
dead duplicate secids were pruned instead, mean explore coverage rose from
2,291.9 to **2,352.7** names/month, and 99.98% of the links actually used are
score 1. The frozen spec is silent on link ambiguity, so this was a plumbing
choice either way; it was made before any signal number was visible and is
outcome-independent, since which arms it helps was unknowable at the time.

**REPAIR 2 — none.** No other change was made after the run began.

## Verification performed before and after the run

- **Build-time coverage guard** (`assert_inputs_cover_explore`), added because
  TRIAL-ABIO-KIRK was frozen against a table holding 1980-2001 for a 2004-2018
  question (§26). Verified vsurf / opvol / dsf 2003-2018 all present, active
  secid links at both explore boundaries (6,979 and 10,511), and 3,756 explore
  VIX observations. It is a run-time assertion, not a one-off check.
- `optionm_crsp_link.sdate/edate` are stored as **strings** in the parquet.
  Unparsed, every date-validity comparison would have been wrong; pinned by a
  test against the real file.
- **Zero infinities** in all three log regressors (log_mktcap, mom_12_1,
  log_dvol3m; finite ranges +11.3..+29.0, -1.00..+105.7, +3.36..+24.6). The run
  log emitted a `divide by zero encountered in log` warning, which is pandas
  masked-array noise at positions already NA — but `dropna` does not catch an
  `inf`, so this was checked directly rather than assumed, exactly as in §26.
- **37 spec tests written before the run**, including a test that the coverage
  guard fails loud on a missing input rather than returning an empty frame.

## Scope of the conclusion

One shot, taken and spent, seven arms. No graduate, no confirm read, no lane
seeded, no forward clock started. Cumulative candidates **173** (167-173
counted here, all rejected). The option-implied cross-sectional family is
**CLOSED** per the frozen kill condition.

What this does **not** license: a sign flip on `os_ratio`, a dispersion variant
of skew or term structure, a different residualisation regressor set, a
long-short rebuild, or a lower-turnover implementation of any arm — without a
fresh registration carrying these receipts as declared priors.

Artifacts: `scripts/run_trial_opt_cohort.py`, `aegis_brain/factory/optsurf.py`,
`tests/test_opt_cohort.py` (23 spec tests), `data/factory/trial_opt_cohort.json`.
