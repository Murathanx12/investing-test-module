# TRIAL-BRAIN-006-fda-approval-drift

**Registered:** 2026-07-24 (UTC) — BEFORE any FDA event is joined to a return.
(The number 006 was reserved for this study in METHODOLOGY when the openFDA
harvest landed; the sponsor→permno crosswalk was built first, return-blind.)
**Registry row:** `TRIALS/registry.jsonl`
**Grade:** paper-grade backtest (CRSP returns). Prior-setting; deploy gate separate.

## Hypothesis
On CRSP 2002→2024, a long-only calendar-time portfolio of stocks with an
ORIGINAL NDA/BLA approval in month t, entered at the START OF MONTH t+1 (the
approval-month return — including the announcement pop — is EXCLUDED by
construction) and held 3 months with a hold-band, earns positive net-of-cost
drift vs an industry-matched EW benchmark. Mechanism: underreaction to the
cash-flow implications of a branded-drug approval, à la PEAD; expected to be
concentrated where the approval is MATERIAL (small caps), diluted to noise in
mega-cap pharma.

## Literature prior
Approval-day CARs are real but small and mostly same-day (Sarkar–de Jong;
event centered on announcement, often after-close); approvals are partially
pre-announced by AdCom votes and PDUFA dates, so month t+1 drift requires
underreaction net of anticipation. BRAIN-004 just showed classic PEAD is dead
net of costs post-2006 except gross-only microcap drift. Honest prior:
**~35/65 against** any segment clearing net t>1; if anything survives, expect
the small segment / PRIORITY-review arm.

## Event set (frozen)
- `data/events/fda_approvals.parquet` filtered to NDA/BLA originals = 2,742
  events, 2002-01→2026-07 (study window ends 2024-12 with the CRSP panel).
- Sponsor→permno via `data/events/fda_crosswalk.parquet` (tiers: manual
  overrides hand/agent-verified with receipts → stocknames-exact date-valid →
  compustat-exact CCM date-bounded → stocknames-unique-ever → core-name;
  fuzzy candidates never auto-accepted; ambiguity dropped and counted).
- **Data trap caught pre-run (recorded like the IBES split bug):** openFDA
  `sponsor_name` is the CURRENT application holder, not the sponsor at
  approval — PE roll-ups (Azurity, Cosette, Acrotech, …) "sponsor" approvals
  that predate their founding because they bought the NDAs later. Such events
  are UNATTRIBUTABLE at approval time and are excluded-with-count
  (`match_source=retroactive_excluded`), never mapped to the current holder.
  Continuous holders (JNJ, MRK, LLY, listed biotechs) are unaffected.
- INCLUDED: events with a permno AND `in_panel_universe=True` (shrcd 10/11 at
  approval). ADR-parent, verified-unlisted, and retroactive-excluded events
  are EXCLUDED and counted (foreign mega-pharma approvals are not tradeable
  in the panel universe — disclosed coverage, not hidden).
- Crosswalk built 2026-07-24: 47.7% of events matched, 26.6% (729) in-panel;
  overrides provenance = model-knowledge + 3 agent-verified receipts, flagged
  for Murat spot-check (`fda_sponsor_overrides.csv`, `fda_crosswalk_review.csv`).
- Multiple approvals by one permno in one month = one event-month.

## Arms
- **Arm B** — all matched NDA/BLA event-months (hypothesis).
- **Arm B-PRI** — PRIORITY-review events only (stronger-catalyst sub-arm,
  reported alongside; ~27% of events).
- **Arm A (placebo)** — pharma/biotech universe WITHOUT an approval that month
  (SIC 2830-2836/8731 members of the panel): the industry benchmark itself.
  Arm B is measured as net excess vs this Arm-A EW portfolio, cap-segment-matched.
- **Arm C (noise)** — same event count with approval months randomly permuted
  within each permno's listed life (leak check; gross |t| ≥ 3 voids the run).
- **Cap segments:** large/mid vs small (panel dollar-volume rank split, same
  convention as the factory), reported side by side.

## Run spec
- Monthly CRSP panel `crsp_panel_2002` (survivorship-free, delisting returns).
- Long-only EW calendar-time portfolio, enter month t+1, hold 3 months
  (overlapping thirds), 25 bps one-way costs on turnover, benchmark =
  industry/segment EW as above.
- Metrics: net excess vs benchmark (Newey-West t), gross t, FF5+UMD alpha t,
  net Sharpe, DSR vs cumulative candidate count at run time, months with <5
  names disclosed. ONE run. Results final.

## Kill conditions
1. Arm C noise GROSS |t| ≥ 3 → leak, void.
2. Arm B net t < 1 in BOTH cap segments AND Arm B-PRI net t < 1 → backtest
   REJECT (forward PDUFA ledger continues regardless — different instrument).
3. Coverage floor: if matched in-panel events < 600 the run still executes but
   the verdict is capped at "insufficient-coverage, no promotion" regardless
   of t-stats (sparse-event small-sample guard).
4. Deploy gate: t > 3.4 AND DSR ≥ 0.95 AND PBO < 0.5 (expected unmet).

## Result (filled AFTER the run 2026-07-24 — never edited)
Data: 671 matched in-panel events (277 PRIORITY) 2002-2024 — coverage floor
600 MET. min_names=5. Run: `runs/TRIAL-BRAIN-006/results.json`.

- **Noise (timing placebo) leak check: PASS** — gross excess t = 0.06
  (large/mid), micro unmeasurable; both < 3.
- **Arm B (all NDA/BLA):** large/mid **−30.1 bps/mo net excess, t = −0.89**
  (gross t −0.68 — not even a gross effect); micro: only 2 live months —
  in-panel approval names are overwhelmingly large/mid, the micro segment is
  effectively untestable at monthly resolution.
- **Arm B-PRI (PRIORITY):** large/mid +10.3 bps/mo net, t = 0.13 (41 live
  months). FF5+UMD alpha +139.6 bps/mo t = 1.56 — suggestive, NOT the
  pre-registered metric, and on 41 months.
- Gate: DSR 0.014 (n_trials=36, module-registry counter per BRAIN-004
  convention), verdict REJECT.

### Verdict: **REJECT** (kill cond 2: B net t < 1 both segments AND B-PRI
net t < 1). No post-approval drift net of costs at monthly resolution in the
tradeable (shrcd 10/11) universe — if anything B is mildly negative, consistent
with approval-day full-pricing + sell-the-news. Leak-checked clean.

### ANNOTATION 2026-07-24 (post-run crosswalk correction — verdict unaffected)
Chunked agent verification of the overrides sheet (probe + 3 sequential
batches, all receipts in agent transcripts) corrected the crosswalk AFTER the
run: APIL ≠ Allergan/AGN — those NDAs are P&G→Warner Chilcott lineage (PG
pre-2009-10-30, WCRX after; WCRX is shrcd 12, outside the panel universe);
Tolmar pre-2004 events are Atrix Labs (ATRX); Journey events attach to
FBIO/DERM; minor date fixes (Bayer NYSE end 2007-09-26, SRA end 2007-04-24,
ANIP 2013-06-19, ETON 2018-11-13, VRX→BHC 2018-07-16). Net book delta:
3 permno-corrected + 5 removed + 7 added = 15/671 events (2.2%). Per the
one-run rule the trial is NOT rerun; a 2.2% book change cannot move
t = −0.89 across the pre-registered t ≥ 1 bar in either arm. Crosswalk v2 is
the artifact of record for any FUTURE registration (e.g. the daily-CAR study). — where the hypothesis put the
effect — could not be measured (2 live months): this is a COVERAGE limit, not
evidence of absence; a daily-resolution CAR study on `crsp.dsf` (next WRDS
pull) would be a NEW registration, not a rerun. (2) The forward PDUFA Brier
ledger is a different instrument and continues untouched. (3) ADR-parent
mega-pharma events (Novartis/AZN/…) were excluded by the frozen universe rule.
