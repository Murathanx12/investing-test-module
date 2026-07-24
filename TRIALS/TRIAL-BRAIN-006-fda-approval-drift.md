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

## Result (filled AFTER the run — never edited)
_pending_
