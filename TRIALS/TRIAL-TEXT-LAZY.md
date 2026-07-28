# TRIAL-TEXT-LAZY — 10-K/10-Q textual change (Lazy Prices), post-publication test

**Registered:** 2026-07-27 UTC — BEFORE any EDGAR full-text acquisition (no
10-K/10-Q text corpus exists on disk; the pull happens only after this doc's
freeze commit).
**Registry row:** `TRIALS/registry.jsonl` via `register_trial()`.
**Counts:** +2 candidates (cosine, Jaccard) → cumulative 158.

## Hypothesis

Firms whose periodic filings change LEAST year-over-year ("non-changers")
earn higher forward returns than changers (Cohen, Malloy & Nguyen, "Lazy
Prices," JF 75(3):1371–1415, 2020). Mechanism: investors underreact to
changes in filing language (risk factors, litigation, executive tone);
absence of change is the safe cohort. Long-only book = top-similarity names.

**Honest prior: WEAK for the long leg.** CMN's alpha is concentrated in the
SHORT (changer) leg; the non-changer long leg's alpha reverts within months.
Their sample ends 2014 with no post-publication test — our confirm window
(2019-2024) is entirely virgin territory for this anomaly, which makes the
result publishable either way given the CZ-CALIB context (a clean
post-publication replication attempt of a famous text anomaly). Post-2004
value-weighted accounting predictability is dead (Chen-Lopez-Lira-Zimmermann),
so largemid is expected net-dead; the small segment is the live shot.

## Literature prior

CMN 2020: L/S VW 34–58 bps/mo gross (t 3.59), EW 18–45 bps/mo, 1995-2014.
NOT the "188 bps/mo" figure sometimes quoted (that is a section-level
subsample upper bound). Low turnover (annual/quarterly formation) — fits the
house LOW-turnover law. No net-of-cost backtest exists in the paper.

## Expected effect size

Long-leg-only, net: 0–15 bps/mo small segment; largemid ~0. (The famous
number is the spread; we can only harvest the weak leg.)

## Expected decay / capacity

Published 2020 + heavily cited → post-publication decay expected
(McLean-Pontiff). That decay estimate is itself a deliverable.

## Kill condition (pre-committed)

No graduate under the standard frozen rule in explore → family CLOSED for
this program. **Pre-declared FILTER fallback (to avoid post-hoc):** if the
PICKER fails but the changer (bottom-similarity) cohort shows forward
market-adjusted return t ≤ −2.0 in the same explore run, a successor
FILTER registration (exclusion of extreme changers) is permitted as a NEW
trial; any other failure mode closes the family outright.

## Two-arm design

- **Arm A (control, expected ~0):** similarity computed on randomly paired
  same-form filings from DIFFERENT firms (matched segment) — pipeline
  validation; should carry no signal.
- **Arm B (the claim):** true YoY same-firm, same-form-type similarity.

## Run spec (frozen before execution)

- Text: EDGAR full-text 10-K and 10-Q, HTML/tables/XBRL stripped; YoY pair =
  same firm, same form type, adjacent fiscal years (10-Q matched to
  same-quarter prior year).
- Signals (directions declared): `text_cos`(+) = cosine similarity on term
  frequencies; `text_jac`(+) = Jaccard similarity on token sets. Two
  candidates, both segments, standard factory scan.
- Formation: filing month-end, PIT by filing date (no fiscal-period leak);
  staleness limit 15 months (a missed filing drops the name).
- Harness: byte-identical factory scan config (top-decile, 30pct hold-band,
  standard segments/costs — largemid 25 bps, small documented at 50 bps
  one-way, BRAIN-008 pattern). DEPARTURE DECLARED: CMN use monthly quintiles;
  we keep the house decile+hold-band harness so the result is comparable to
  the other 155 candidates — this is a construction difference and will be
  disclosed next to any claim.
- Windows: explore 2004-2018, one run; confirm 2019-2024 only for explore
  graduates, one run, final.

## PRE-RUN ADDENDUM — coverage shrink (2026-07-28 UTC, before any text pull)

The registration pre-authorized exactly one departure if the EDGAR text pull
proved infeasible: **shrink COVERAGE, never the window.** Exercised here, declared
before a single document was fetched.

**Coverage as run: 10-K only. 10-Q is dropped.**

- Binding constraint is FETCH TIME, not disk. SEC's cap forces ≤8 requests/s
  through one choke-point, so the pull is document-count-bound: the in-universe
  10-K set is ~90k documents (~3-4h); adding 10-Q multiplies that by ~4 and the
  pull stops fitting in a session. Disk is a non-issue by construction — the
  pipeline never persists raw filings (see `aegis_brain/events/filing_text.py`:
  one firm at a time, two token bags in memory, two floats out).
- Effect on the signal: formation becomes ANNUAL rather than quarterly. The
  frozen 15-month staleness limit already tolerates this (a 10-K-only firm-year
  chain never goes stale between filings). CMN report annual-formation results
  alongside quarterly, so the annual version is the paper's own weaker variant,
  not an invention of ours.
- Effect on power: fewer formation events and slower signal refresh → this is a
  LOWER-powered test than CMN's. Stated as such next to any claim. A null here is
  weaker evidence of absence than a full-coverage null would have been, and the
  writeup must say so rather than reporting "Lazy Prices does not replicate."
- **Windows UNCHANGED** (explore 2004-2018, confirm 2019-2024), signals unchanged
  (`text_cos`, `text_jac`, both +), harness unchanged, arms unchanged, one shot.

**Link departure (both round-12 trials):** the module's WRDS pull carries no `cik`
column, so filings are joined to permnos through a CIK bridge built from CRSP
historical name rows × EDGAR's `cik-lookup-data.txt` (every name a CIK ever filed
under, former names included). Both sides are historical registries, so the bridge
is survivorship-neutral — deliberately NOT `company_tickers.json`, which only
knows current filers and would silently delete dead firms. Filings whose CIK maps
to more than one permno inside the date window are DROPPED as ambiguous and
counted; the match rate is reported with the result.

## What this rule may NOT do

No short leg, no lane, no buy/sell language. Graduation earns confirm; a
confirm pass earns forward-clock candidacy only (attended).

## Result (filled in AFTER the run — never edited afterwards)

- Gate report:
- Verdict:
