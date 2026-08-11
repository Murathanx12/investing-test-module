# PREREG — TRANSACTION-ENSEMBLE-1: bounding his record without his records

**Registered** 2026-08-11, NIGHT-13, **before any ensemble member is generated.**
**Class:** measurement instrument. **This trial ACCRUES ZERO** — it can promote
nothing; it bounds what other trials may claim. **Parent**
CONVICTION-REPLAY-1 (`PREREG_CONVICTION_REPLAY_1.md`), whose declared limit —
"it cannot produce his NAV; the +73.7% vs '+115%' gap is NOT reconciled" — is
the question here.

**The ruling this implements (Murat 2026-08-11, as recorded in
`aegis-finance/docs/NIGHT13_BRIEFING.md` §1):** his instruction "make up
sensible data, choose the best outcome and validate it" is executed in its
licensed form — an ensemble of transaction histories consistent with every
known anchor, where only conclusions that hold across the ensemble are adopted.
Point-fabrication of personal records and post-hoc selection of a preferred
member are refused; the range IS the result.

---

## 1. The anchors (frozen inventory — a member must satisfy its declared subset)

1. 13 Nov-2025 portfolio names at sheet prices (2025-11-07 PIT sheet).
2. 14 Jan-2026 portfolio rows, two price columns (2026-01-13 PIT sheet).
3. Three exits, prices known, dates bounded to (2025-11-07, 2026-01-13]:
   TVTX @34.4, ALMS @10, SLDP @8.1.
4. 12 dated share counts at 2026-07-11 with logged marks (conviction log,
   immutable; the logged `price` is a MARK, not a fill — pm_reconcile.py:28-31).
5. QUBT: 300 (Murat-authoritative) with the book_lanes 200 kept as a bound arm.
6. Cash: unknown at every date — swept 0–30% of equity NAV.
7. "+73.7% / +$15,165 over ~1yr" (chat disclosure, no document).
8. "2025 +115%" (raw_text_2026-01-13.txt:2).
9. "$25k → $45k" legacy figure (PORTFOLIO_MANAGER_v1.md:3).
10. APLT $0.088/share on 2026-02-03 and SLNO $53.00/share on 2026-05-18
    (terminal cash events; entries from his sheet — reconstructed grade).

**Anchors 7, 8, 9 are mutually unreconciled.** Members satisfy MAXIMAL
CONSISTENT SUBSETS of the anchors, and every member is labelled with the subset
it satisfies. The inconsistency is an ensemble dimension, never resolved by
preference.

## 2. Generator, frozen

N ≥ 200 members (seeded `np.random.default_rng`, seeds recorded). Varied
dimensions: entry dates/prices within each name's sheet-to-log bounds; the
three exit dates within their interval; cash fraction; QUBT 300/200;
takeout-proceeds treatment (idle cash / SPY / pro-rata reinvest — the
`reinvest_in` sensitivity CONVICTION-REPLAY-1's docstring names but never
implemented); position weighting where share counts are unknown. Members
violating any anchor in their declared subset are rejected at generation, and
the rejection count is reported. NAV computation reuses `pm_engine.mark_book`
semantics so every member NAV carries the house valuation vocabulary.

## 3. The frozen question list (nothing added after generation)

- **Q1** What fraction of the +73.7%/"115%" headline is attributable to
  weighting/trading vs selection, as a RANGE across members?
- **Q2** Which anchor subsets are mutually consistent — i.e. does ANY
  transaction history exist satisfying {7,8} jointly, {7,9}, {8,9}, all three?
  (A empty subset is a finding: the anchors cannot all be true.)
- **Q3** The cost of his three exits (ALMS/TVTX/SLDP) as a range, in NAV terms.
- **Q4** Bounds for the `as-traded` arm consumed by FACTORIAL-PM-1.

## 4. Grading rule, frozen

A conclusion is **`ensemble_robust`** iff its SIGN and magnitude class agree
across every member of every maximal consistent anchor subset. Otherwise
**`DATA_NEEDED`**, carrying the minimal exact ask (e.g. "broker CSV export,
~2 minutes, resolves Q1 and Q3"). **No member is ever promoted, quoted alone,
or labelled 'most likely'.** §19: ranges are reported with member counts;
where a statistic admits an MDE it is measured, not derived.

## 5. What this may NOT do

- Write any member's numbers into murat_book.yaml, book_lanes.yaml, the
  conviction log, any lane, or any ledger — ensemble output lives only in
  `docs/NIGHT13_ENSEMBLE_NAV.md` + its JSON artifact, labelled SYNTHETIC.
- Train anything. Ensemble members are bounds, not data.
- Overturn CONVICTION-REPLAY-1's verdict (UNRESOLVED stands regardless).
- Claim skill in either direction.
