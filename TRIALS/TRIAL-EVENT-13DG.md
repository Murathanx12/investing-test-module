# TRIAL-EVENT-13DG — activist intent vs passive disclosure, control-armed

**Registered 2026-08-02, FROZEN BEFORE ANY RUN CODE IS WRITTEN.**
Cumulative candidates **175-177** (three arms, each counted).
Supersedes `docs/DRAFT_13DG_REGISTRATION_2026-08-01.md` (drafted 2026-08-01,
updated 2026-08-02 with measured collector output, frozen by the orchestrating
session 2026-08-02 after the hand-check below). Authority: Murat's 2026-08-02
"continue working" direction; the draft's counts were shown to him 2026-08-02.

## Data, verified

- Collector: `aegis_brain/data/edgar_13dg.py` via the `_sec_get` choke-point;
  92/92 quarters 2002-2024, zero failures; parser accounted for 38,752/38,752
  raw lines on the 2010Q1 audit.
- Resolution: **63.31%** of 681,411 accessions resolve to an unambiguous CRSP
  subject candidate (single CRSP-resolvable CIK). **Disclosed limitation,
  accepted at freeze:** this is a heuristic, not a verified role assignment;
  the unresolved 37% skews toward issuers outside our CRSP bridge. Exact role
  verification (~680k SGML header fetches, ~24h paced) is NOT done and would
  be a separate attended decision.
- **Hand-check (the freeze condition, run 2026-08-02): 3/3 known campaigns hit
  on their exact historical dates** — Icahn/Netflix SC 13D 2012-10-31, Third
  Point/Yahoo SC 13D 2011-09-08, JANA/Whole Foods SC 13D 2017-04-10, each on
  the correct permno, with the follow-on /A amendments present where expected.
- Explore-window events: 13D 12,447; 13G 73,340; 13D-first-in-24m 6,826;
  8,542 distinct permnos.

## Hypothesis

A Schedule 13D discloses a >5% stake held with **intent to influence**; a 13G
discloses the same threshold held **passively**. Brav-Jiang-Partnoy-Thomas
2008 and Klein-Zur 2009 report large positive announcement returns and drift
for 13D. The claim under test is narrower and control-armed:

> Names with a **13D** filing earn positive abnormal returns over +1..+60
> trading days relative to matched non-event names of the same segment, month
> and liquidity rank — and **13G filings do not**.

The 13G arm is the point: same threshold, same filer population, same
salience, differing only in declared intent. If both drift, the effect is
disclosure/selection; if only 13D drifts, intent is doing work. This is the
design §20 says 8-K should have had.

## Arms — three, each a counted candidate

| # | arm | construct |
|---|---|---|
| 175 | `13d_all` | every initial SC 13D (amendments excluded), event date = filing date |
| 176 | `13g_all` | every initial SC 13G (amendments excluded) — the intent placebo |
| 177 | `13d_first` | SC 13D with no prior 13D on the name within 24 months |

**Rulings at freeze (the draft's three open questions):** (1) the 13G placebo
is **counted** — a control that cannot lose is not a control; (2) amendments
are **excluded from all arms** (A/B use initial filings only; C additionally
requires the 24-month gap); (3) the announcement window −1..0 is **reported,
never deciding** — it is the sanity check that the event dates are real.

## Frozen evaluation

- Harness: `aegis_brain/factory/daily_events.py` (placebo-validated: random
  dates show +170 bps uncontrolled → −26 bps controlled).
- Windows: +1..+5, +1..+20, +1..+60 trading days; day 0 excluded (the
  announcement pop is not ours to have — 13Ds are filed within 10 days of
  crossing 5% and the pop concentrates at/before filing).
- Control arm MANDATORY: same segment, same calendar month, nearest
  dollar-volume rank, no event within ±60 calendar days. The differenced CAR
  is the only deciding number.
- Delisting-aware: `crsp.dsedelist` joined (dsf.ret verified NOT to contain
  delisting returns).
- Inference: t clustered by event month; iid t reported alongside.
- **Explore 2004-2018 only.** Era-split (2004-2010 vs 2011-2018) reported —
  declared before any number exists, because 13D filing volume falls
  2,756/yr → 1,024/yr across the sample and a pooled result is early-weighted.
- **A CAR result alone cannot graduate anything.** A passing arm must then be
  built as a monthly portfolio and cleared through `scan_signal` under the
  standard deciding cost arms before it earns the confirm shot. Confirm needs
  Murat's authorisation.

## Declared prior: WEAK-NEGATIVE

§20 (selection, not information — the direct receipt), CZ-CALIB fame decay on
a famous published effect, and the 13F ownership family now 8-for-8 dead
(§26). Different enough (event-timed, intent-labelled) that the question is
open; related enough that the prior transfers.

**Honest prediction to be scored:** 13D +1..+5 differenced CAR positive but
< 100 bps with clustered t 1.0-2.5; +1..+60 indistinguishable from zero; 13G
zero at all horizons; the 13D-minus-13G contrast smaller than the raw 13D
number; nothing graduates to a book.

## Kill condition

One shot per arm. If the **13D-minus-13G contrast** is not positive with
clustered t ≥ 2.0 in at least one window, the activist-intent mechanism is
recorded dead and the family closes — no re-cuts by market cap, campaign
type, filer identity or window. If 13D and 13G drift **together**, recorded
as "large-holder disclosure is a selection marker, not information" and both
close. Crash-before-readable repairable (disclosed); completed run final. No
forward lane seeded under any outcome.

---

# RESULTS — run 2026-08-02, one shot per arm, explore 2004-2018

**Chain:** frozen at module commit `98c99e2` (arms, windows, control rule,
kill condition, era split and the honest prediction all declared before any run
code existed) -> `aegis_brain/factory/event_13dg.py` +
`tests/test_event_13dg.py` written after -> one shot per arm.

**Frozen verdict: STOPPED. Two arms and both contrasts clear their CAR gate.**
Building a passing arm as a monthly portfolio and clearing it through
`scan_signal` is the attended next step; confirm needs Murat's authorisation
and was NOT read.

## The sanity check first — the event dates are real

The −1..0 announcement window is reported and never deciding. Its job was to
tell us whether to believe the nulls, and it answered clearly:

| arm | −1..0 differenced CAR | clustered t |
|---|---|---|
| `13d_all` | **+95.5 bps** | **7.74** |
| `13d_first` | **+116.3 bps** | **6.87** |
| `13g_all` | +9.7 bps | 1.64 |

13D filings move the stock on their own announcement window and 13G filings
essentially do not — which is what the institutional story predicts and what a
broken date pipeline could not produce. The nulls below are believable.

## Arms, differenced CAR vs matched controls (the only deciding number)

| arm | window | event leg | control leg | **differenced** | **clustered t** | iid t |
|---|---|---|---|---|---|---|
| `13d_all` (n 9,431) | +1..+5 | 136.3 | 39.8 | **+96.6** | **4.75** | 5.94 |
| | +1..+20 | 223.5 | 102.9 | **+120.7** | **3.38** | 4.72 |
| | +1..+60 | 370.9 | 265.7 | +105.2 | 1.74 | 2.47 |
| `13g_all` (n 59,598) | +1..+5 | 24.9 | 28.2 | −3.3 | −0.40 | −0.73 |
| | +1..+20 | 20.3 | 54.9 | −34.6 | −1.77 | −3.93 |
| | +1..+60 | 391.3 | 420.4 | −29.1 | −0.69 | −1.93 |
| `13d_first` (n 5,542) | +1..+5 | 142.8 | 47.0 | **+95.8** | **4.01** | 4.78 |
| | +1..+20 | 268.8 | 104.5 | **+164.3** | **4.07** | 5.07 |
| | +1..+60 | 443.8 | 291.6 | **+152.2** | **2.37** | 2.82 |

## The 13D-minus-13G contrast — the kill condition

Pooled regression of the differenced CAR on a 13D indicator, clustered on the
pooled event month (both arms share the calendar, so clustering arm-by-arm
would count each month's shock twice).

| contrast | window | 13G intercept | **contrast** | **clustered t** |
|---|---|---|---|---|
| `13d_all` − `13g_all` | +1..+5 | −3.3 | **+99.9 bps** | **4.25** |
| | +1..+20 | −34.6 | **+155.3 bps** | **3.76** |
| | +1..+60 | −29.1 | +134.3 bps | 1.96 |
| `13d_first` − `13g_all` | +1..+5 | −3.3 | **+99.2 bps** | **3.77** |
| | +1..+20 | −34.6 | **+199.0 bps** | **4.26** |
| | +1..+60 | −29.1 | **+181.3 bps** | **2.48** |

The kill condition required the contrast to be positive at clustered t ≥ 2.0 in
at least one window. **It clears in two windows for `13d_all` and all three for
`13d_first`.** The family does not close.

**The placebo did its job.** 13G — same 5% threshold, same filer population,
same salience, differing only in declared intent — is flat to mildly negative
at every horizon. The two do not drift together, so the "large-holder
disclosure is a selection marker" branch of the kill condition is refuted on
its own terms. Declared intent, not disclosure, is carrying the number.

## Era split (declared before any number existed)

| arm | era | +1..+5 | +1..+20 | +1..+60 |
|---|---|---|---|---|
| `13d_all` | 2004-2010 (n 5,129) | +83.1 (t 2.95) | +128.6 (t 2.96) | +95.0 (t 1.31) |
| | 2011-2018 (n 4,302) | +112.6 (t 3.84) | +111.2 (t 1.89) | +117.3 (t 1.16) |
| `13d_first` | 2004-2010 (n 2,973) | +83.1 (t 2.89) | +183.0 (t 3.42) | +157.9 (t 1.74) |
| | 2011-2018 (n 2,569) | +110.5 (t 2.80) | +142.8 (t 2.32) | +145.6 (t 1.60) |
| `13g_all` | 2004-2010 | −28.2 (t −2.47) | −55.4 (t −2.03) | −29.9 (t −0.45) |
| | 2011-2018 | +31.0 (t 4.57) | −5.9 (t −0.27) | −28.0 (t −0.63) |

The reason the split was declared in advance — 13D volume falls 2,756/yr →
1,024/yr, so a pooled number is early-weighted — turns out not to bite. The
short-horizon 13D effect is **larger** in the later era, not smaller, and the
sign is stable in both. The 13G arm is the one that flips sign across eras at
+1..+5 (−28.2 then +31.0), which is another reason it reads as noise rather
than an effect.

## One disclosed discrepancy, found before any CAR existed

The freeze quotes "13D-first-in-24m **6,826**". That figure cannot be
reproduced from the banked parquet under any reading of the rule the freeze
states. Measured, before the run:

| reading of "prior 13D within 24 months" | count |
|---|---|
| prior = initial SC 13D (the rule as written, **used**) | **7,360** |
| prior = SC 13D or SC 13D/A | 5,601 |
| as above, de-duplicating (permno, date) | 6,591 / 4,981 |
| 730 / 731 / 720-day lookback instead of 24 calendar months | ±40 |

The freeze's other counts all reproduce exactly (13D 12,447; 13G 73,340; 8,542
distinct permnos), so the event base is right and only this derived figure is
off. The trial was run on the RULE as written — prior = a prior INITIAL SC 13D
on the same permno, strictly earlier, within 24 calendar months — because
ruling (1) excludes amendments from all arms, giving **7,360** `13d_first`
events. No window, control, bar or arm definition was changed. Arm sizes as
run: `13d_all` 12,447 events / 5,129 permnos; `13g_all` 73,340 / 7,860;
`13d_first` 7,360 / 4,982.

## Disclosed limitations — both material to the attended step

1. **Control-matching attrition: 24.2% of 13D events never reach a CAR.**
   12,447 initial 13Ds in the explore window, 9,431 with a matched control; the
   3,016 losses are events whose permno has no CRSP dollar-volume observation in
   the filing month (18.7% for 13G, 24.7% for `13d_first`). Every event that
   reached matching got a control (9,431/9,431), so the loss is entirely at the
   liquidity-rank join. This is §20-shaped and must be treated that way: the
   dropped names are the ones already out of the trading data, and whether their
   post-filing returns would have been better or worse is unknowable from here.
   The result is a result on survivors-to-the-filing-month.
2. **Segment mix.** Of matched 13D events, 4,848 are small, 2,944 micro (rank
   > 3,000) and 1,639 large/mid. **31% of the effect's population sits outside
   the tradable universe entirely**, and the harness's segment bounds are the
   same as the factory's. A monthly book built from this cannot hold the micro
   third, and the CAR reported here does not tell us what remains once it is
   dropped. That question belongs to the `scan_signal` step, not to this one.
3. **63.31% subject resolution**, accepted at freeze and unchanged.

## The honest prediction scored — 3 of 5, and the misses matter

Declared at registration: *"13D +1..+5 differenced CAR positive but < 100 bps
with clustered t 1.0-2.5; +1..+60 indistinguishable from zero; 13G zero at all
horizons; the 13D-minus-13G contrast smaller than the raw 13D number; nothing
graduates to a book."*

| leg | predicted | measured | verdict |
|---|---|---|---|
| 13D +1..+5 positive, < 100 bps | yes, < 100 | +96.6 bps | **HIT** |
| 13D +1..+5 clustered t 1.0-2.5 | 1.0-2.5 | **4.75** | **MISS** |
| 13D +1..+60 ≈ zero | zero | +105.2, t 1.74 | **HIT** (below the bar) |
| 13G zero at all horizons | zero | −3.3 / −34.6 / −29.1, all \|t\| < 1.8 | **HIT** |
| contrast < raw 13D number | smaller | **larger in all three windows** | **MISS** |
| nothing graduates to a book | nothing | **not yet resolvable** | **PENDING** |

The size of the effect was called almost exactly and its significance was
badly underestimated — the prediction was calibrated on the WEAK-NEGATIVE prior
(§20, CZ-CALIB fame decay, the 13F family 8-for-8 dead) and that prior was
simply wrong for this family. The contrast miss has a clean cause: it was
predicted to shrink the 13D number, and instead the 13G leg is slightly
NEGATIVE, so differencing makes the contrast bigger. Both misses point the same
way — we expected an event family to die and it did not.

## Scope honoured

One shot per arm. No re-cuts by market cap, campaign type, filer identity or
window. The portfolio / `scan_signal` step was NOT taken, confirm was NOT read,
and no forward lane was seeded. Cumulative candidates unchanged at **175-177**.

---

# BOOK STAGE — authorised 2026-08-02, FROZEN BEFORE ANY RUN CODE

Authorised by the orchestrating session under Murat's standing "continue
working" direction; this stage was pre-declared in the frozen evaluation ("a
passing arm must then be built as a monthly portfolio..."). **No new
candidates** — this is the second stage of already-counted arms 175 and 177.
`13g_all` (176) failed its gate and gets no book.

## Frozen book construction (one book per passing arm, one shot each)

- **Events:** exactly the banked event sets as run (`13d_all` 12,447;
  `13d_first` 7,360 under the rule-as-written, discrepancy disclosed above).
- **Eligibility:** standard factory universe, dollar-volume rank ≤ 3000 at the
  entry month-end. The micro third is excluded by construction — that is the
  question this stage exists to answer.
- **Entry:** a name enters at the first month-end ON OR AFTER its filing date.
  **This forfeits the +1..+5 pop and part of +1..+20 by design** — a monthly
  book cannot trade the filing day, and pretending otherwise would be the
  lookahead this program exists to refuse. What is being tested is the
  harvestable REMAINDER of the drift.
- **Hold:** through the 3rd month-end after entry, then exit. A new initial
  13D on a held name resets the clock; no doubled positions.
- **Weighting:** equal-weight across active names, rebalanced monthly.
- **Benchmark:** EW of all eligible names (factory convention), pooled.
  Deciding number = pooled net excess vs this benchmark. Segment breakdown
  reported, never deciding (the largemid slice will be thin).
- **Costs:** deciding arm = per-name Kyle-Obizhaeva half-spread on actual
  entry/exit/rebalance turnover; flat-25 guard and zero-cost bound reported
  alongside (post-§25 interval convention).
- **Bar to earn the confirm shot:** pooled net excess t ≥ 1.5 with positive
  mean. The IC-t leg of the standard bar is N/A for a binary event signal —
  declared here, not decided after numbers exist. **Confirm (2019-2024) still
  requires Murat's explicit authorisation even on a pass.**

## Kill condition (book stage)

One shot per book. If neither book clears the bar, the recorded finding is:
**"13D drift is real at event resolution (§29) and unharvestable by a monthly
long-only book at realistic costs"** — the family closes at book resolution,
and a daily-rebalance harvest test would be a NEW registration against the
deflation count, not a retry of this one.

## Honest prediction (declared before the run)

Month-end entry forfeits most of the front-loaded drift, so: both books
positive but small, net excess **+5 to +35 bps/mo**, t **0.5-1.5**,
`13d_first` > `13d_all`, **neither clears the 1.5 bar**. The §29 prior was
wrong once already (predicted-dead family passed); recorded so this one can be
scored too, either way.
