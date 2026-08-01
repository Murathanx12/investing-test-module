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
