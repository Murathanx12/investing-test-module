# PREREG — TEACHER-LIBRARY-1 (Track E): conditional structure in observed expert trades, not mean-actor skill

**REGISTERED — SIGNED 2026-08-22.**
SIGNED-BY: Murat Abdullaev — in-session approval 2026-08-22 ("All three
now" on the signature question), recorded by the working session. Drafted
and signed the same day, before any subgroup feature was computed and
before any forward observation accrued.

**§64 RESERVATION RECEIPT (computed at signature, from PROD stores):**
`pi_ownership_collect` prod receipts show ~1,741 events written per filing
day (2026-08-14: 1,746; 2026-08-17: 1,741) ≈ 430,000 events/yr; at the
local corpus's ~5.8% BUY fraction, S2-eligible purchases accrue in the
THOUSANDS per year against the 349 required — **S2 is powered with an
order of magnitude to spare; the 12-month window stands.** The congress
store exposes no count surface today, so **S3 and S4 remain
RESERVATION-GATED and MAY NOT RUN** until a session counts the prod
congress store and appends its §64 receipt beneath this line; if that
count fails the gate they are SHELF at birth, recorded.

**Family:** conditional-heterogeneity screen over disclosed actor trades.
**Grade:** SCREEN on forward accrual; any surviving subgroup earns a FORWARD
confirmation registration and nothing else. **ACCRUES ZERO ARMS. Never a
lane, never a signal, no buy/sell language anywhere it surfaces.**

## 0. Corpse check — predecessors are ALIVE, and this is not them

`python scripts/lint_prereg.py TRIALS/PREREG_TEACHER_LIBRARY_1.md`

The live predecessors measure MEAN-actor effects and stay untouched:
`TRIAL-CONGRESS-IC` (mean congressional IC, decision 2027-01-11),
`TRIAL-INSIDER-IC`/`TRIAL-CMP-INSIDER-IC` (2027-07-21), `TRIAL-ARK-IC`.
**This trial asks the question they cannot: is the information in WHO/WHEN/
WHAT-CONTEXT rather than in the average actor?** The stated prior is the
STOCK-Act literature's mean-politician null and our own 206-predictor NET
median of −0.12%/yr: H0 (no exploitable mean effect) is EXPECTED to hold.
hypothesis_source: Order 16 item 10 as amended (Capponi et al. congressional
heterogeneity; Cohen-Malloy-Pomorski routine-vs-opportunistic insiders;
Pyun leadership-ascension), adopted 2026-08-18 before any subgroup data was
inspected.

**H3 control (the 13F-popularity corpse):** popularity of an actor does not
constitute signal (MANAGER-* blocked on vintage grounds; 13F-popularity
refuted). Any subgroup whose membership reduces to "famous actor" must be
beaten by its own fame-stripped twin or it is the corpse again.

## 1. Substrates (both PIT by construction, disclosure-date-only)

- **Insider corpus:** `teacher_library/events.jsonl` via `pi_ownership_collect`
  (EDGAR `form.YYYYMMDD.idx`, published only after the filing day closes —
  nothing can see a filing before the world did). Local snapshot measured
  2026-08-22: 1,589 events, 486 distinct actors, 92 BUY / 516 SELL, median
  disclosure lag 2 days, exactly 1 cusip with ≥3 distinct buyers.
- **Congressional corpus:** the TRIAL-CONGRESS-IC PIT store (prod volume,
  collected daily 07:30 ET since 2026-07-17).
- Every event timestamp = DISCLOSURE acceptance timestamp. Trade-date
  fields are features (delay), never event times.

## 2. Declared subgroups (frozen at signature; each powers separately)

**Corpse-checked OUT (recorded, not run):** insider-cluster-buy as its own
subgroup. TRIAL-BRAIN-009-insider-cluster tested clusters-vs-singles on the
historical CRSP panel (flag-portfolio harness, the correct instrument after
the B5 VOID-DESIGN) and CLOSED REJECTED under its own kill condition; and
forward it accrues ~12 events/yr against a §64 requirement of ~349 at the
declared effect — unpowered at birth from both directions. Cluster buyer
count survives ONLY as a reported intensity covariate on S2 events (exactly
the role BRAIN-003 assigned it), with no verdict authority.

- **S2 opportunistic-insider (PRIMARY — the only subgroup powered on this
  draft's own estimates):** open-market BUY (`TRANS_CODE='P'`,
  acquired) by an insider who is NOT routine under the CMP classifier
  FROZEN in TRIAL-BRAIN-003 (routine = bought in the same calendar month in
  ≥3 consecutive prior years; unclassifiable insiders DROPPED, never
  defaulted). **Lineage, named per the corpse check:** TRIAL-BRAIN-003
  (2026-07-21) ran the historical CRSP version and closed
  FIRST_NON_REJECT — weak-positive prior (+20-60 bps/mo best cap segment,
  cap-segment-correct: large/mid ≥ micro) — and declared that conviction is
  earned FORWARD by pre-registered calls. S2 IS that declared forward leg,
  on the same classifier, so the historical prior and the forward evidence
  stay one lineage. Cap segment carries into the matching (size decile).
- **S3 congressional-committee-relevant (reservation-gated):** purchase
  disclosed ≤ 15 calendar days after trade by a member whose committee
  assignment has jurisdiction over the issuer's sector (mapping frozen at
  signature). At ~60 events/yr estimated, a 12-month window resolves ~3.6pp
  at best — S3 runs ONLY if the reservation count clears §64 at the 2.0pp
  declared effect (which likely requires a longer declared window or a
  higher measured rate); otherwise SHELF at birth, recorded.
- **S4 leadership-ascension (reservation-gated):** purchases by members
  within 90 days AFTER a declared ascension event (chair/ranking-member
  change). RARE by construction — EXPECTED to fail §64 and SHELF at birth
  unless the count at reservation says otherwise.

**The trial's headline claim is S2's.** S3/S4 are declared now so their
gating is on the record before any count is seen; their failure to power is
a recorded fact about accrual, never a "negative result" about the world.

## 3. §64 power gate AT RESERVATION (registration blocker)

At signature, the registering session computes per-subgroup forward n from
the PROD stores' measured accrual rates (not this draft's local snapshot)
and prints per-subgroup DECISION_MDE and STATISTICAL_MDE (they differ; both
are quoted, per 08-19). **A subgroup whose 12-month projected n cannot reach
its MDE at the declared effect size is SHELF at birth — recorded, not run.**
No subgroup may be re-powered mid-trial by widening its own definition.

declared_effect_size: 1.5% mean 21-day market-adjusted excess return per S2 event (the primary claim; consistent with BRAIN-003's +20-60 bps/mo prior compounded over a hold); 2.0% for the reservation-gated S3/S4
event_frequency_per_year: 400 (S2, the primary — from the local snapshot's 92 BUYs across a partial collection window scaled to the daily EDGAR cadence; gated S3 ~60, S4 ~8 run only if their reservation counts clear §64); the RESERVATION COUNT from the prod stores is the authority and overrides these numbers at signature
outcome_dispersion: 0.10 (21-day idiosyncratic sigma ~9-12% for small/mid caps on CRSP era panels; the matched-control pairing is what makes the MDE reachable at all)

## 4. Primary metric and decision rule (ONE number per subgroup)

**Primary:** mean 21-trading-day market-adjusted excess return of subgroup
events vs MATCHED CONTROLS (same date, same size decile, same sector, no
qualifying event in ±30 days), date-block bootstrap per §58 (n_effective
counts DATE BLOCKS; block unit derives from panel spacing). Entry at the
first close AFTER disclosure acceptance (+1 trading day — nothing trades on
information before it is public).

- **Multiplicity:** SCREEN = BH-FDR 0.10 with m = subgroups actually run;
  any EXPORT claim = Holm over the declared m=4 (§63, one decide()).
- **Adopt (→ forward confirmation registration only):** subgroup survives
  BH-FDR AND point estimate ≥ declared effect size AND ≥ 60% of date blocks
  positive.
- **Reject:** CI upper bound < declared effect size (a null owes two tests:
  the equivalence read prints beside the significance read).
- **Window:** forward accrual from signature; earliest decision = 12 months
  after signature or 100 subgroup events, whichever is LATER; evaluation
  cadence quarterly (reads before the earliest decision date are
  operational-health only, never graded).
- **Crash override:** SPY −20% from trailing high defers any decision to
  ≥6 months past trough.
- **Contamination clause:** a collector defect that misdates or drops
  events voids affected date blocks on discovery receipts, never the trial;
  >20% of blocks voided ⇒ trial re-registers as a successor.

slice_purpose: CONFIRM — S2 is the forward confirmation leg BRAIN-003
declared for its weak-positive historical prior, on the same frozen
classifier and a slice (forward accrual) the historical run never touched;
the gated S3/S4 are declared alongside but carry no confirm authority. All
subgroup definitions partition on ACTOR CONTEXT observable at disclosure
time; no slice conditions on outcomes, prices, or anything post-disclosure
window: forward from signature; earliest decision per §4; no backfilled
performance claims (T7: historical panels are direction-checks only and are
not this trial's evidence)
parent_trial: TRIAL-BRAIN-003-opportunistic-insider
selection_period: 2006-01-01 .. 2026-07-21 (the classifier, cap-segment reading, and effect-size prior were SELECTED on BRAIN-003's historical CRSP window, which closed 2026-07-21 — strictly disjoint from the forward slice below)
selection_window: 2026-08-23 .. 2027-08-23 (forward accrual only; extends only by the 100-event clause, never backward; no observation before signature is selected, graded, or eligible)
slice_securities: US common stocks (CRSP shrcd 10/11 equivalents), joined from Form 4 issuer CUSIP / congressional disclosure ticker; ETFs, ADRs, funds excluded
information_cutoff: the EDGAR acceptance timestamp (insiders) / disclosure filing timestamp (congress) of each event; entry is the first close STRICTLY AFTER that timestamp and every feature reads only data timestamped before it
slice_period: 2026-08-23 .. 2027-08-23 (forward accrual; extends only by the 100-event clause, never backward)
hypothesis_source_period: 1986-01-01 .. 2026-08-18 (CMP JF 2012 data 1986-2007; BRAIN-003 historical run CRSP 2006-2024, closed 2026-07-21; Order 16 adjudication 2026-08-18 — all strictly before the forward slice opens)
hypothesis_source_note: the forward window shares no observations with any source window, and because the hypothesis is IMPORTED a positive result is confirmation of an imported hypothesis, never independent discovery

## 5. Frozen parameters

Subgroup definitions (§2 verbatim) · delay bound 15 days (S3) · ascension
window 90 days (S4) · the CMP routine classifier frozen in BRAIN-003
(S2) · entry timing disclosure+1 close · horizon 21
trading days · matching spec (date, size decile, sector, ±30-day clean) ·
declared effect sizes (§3) · NANC/KRUZ monthly returns reported beside S3/S4
as implementation controls (what naive copying actually earns) — reported,
never deciding.

## 6. What this trial may NOT do

Promote anything into a lane or book · emit buy/sell/predicts language ·
widen a subgroup after seeing any read · pool subgroups post hoc · cite the
mean-actor predecessors' accruals as its own evidence · treat the NANC/KRUZ
controls as arms · run any subgroup that failed the §64 reservation gate.
