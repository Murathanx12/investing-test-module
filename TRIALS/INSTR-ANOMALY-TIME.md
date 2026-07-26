# INSTR-ANOMALY-TIME — announcement-date availability for annual fundamentals

Registered 2026-07-26, FROZEN BEFORE the run. Candidate **#153** (deflation
applies). Prior-check transcript: "anomaly rdq availability" → 21 hits, all
reviewed — the EAD upgrade was queued at the 2026-07-26 research sweep and
endorsed by both round-7 panel reviews; no closed family is re-entered
(the SIGNAL is unchanged; only its availability timing is tested).

## Hypothesis

Bowles, Reed, Ringgenberg & Thornock (JF 2024, "Anomaly Time"): anomaly
returns concentrate in the period immediately after the information release;
fixed-lag conventions (ours: `datadate + 6 months`) systematically discard
the highest-alpha window. In our comp_fundq, annual (Q4) results carry
`rdq` with median lag **39 days** (p90 77d, coverage 70.8% of rows) — the
convention wastes ~4.5 months. Re-timing the confirmed survivor
(BRAIN-008 gross profitability, small segment) onto announcement-month
availability should preserve or improve net performance. If it does, every
fundamentals signal inherits the fix; if it does not, the 6-month
convention stays and the anomaly-time claim is dead on our data.

## Variant construction (frozen)

- **Values:** byte-identical to `load_characteristics()` `gross_prof`
  (Novy-Marx GP/AT). Nothing about the signal changes.
- **Availability:** for each (gvkey, datadate) firm-year, match the
  comp_fundq row with the same gvkey and datadate (the Q4 report). If
  `rdq` is non-null AND `datadate < rdq <= datadate + 183 days`, then
  `avail_month = MonthEnd(rdq)`; otherwise per-row fallback to the
  baseline `datadate + 6mo` (keeps the universe fixed; isolates timing).
- Same ffill stale limit (18 months), same direction (+1), same panel
  (crsp_panel_2002), same ScanConfig mechanics.
- **Tags:** source=accounting · horizon=annual · turnover=LOW · role=PICKER.
- **Link caveat (disclosed):** CCM link validity was checked at datadate;
  rdq is ≤183d later. Marginal link-window drift is possible and accepted.

## Runs (one shot)

Explore window 2004-01..2018-12, same code path for baseline and variant:

1. `gp_base` (datadate+6) and `gp_ead` (rdq-timed) — small + largemid at
   25 bps; small additionally at 50 bps (the survivor's pre-registered
   honest-cost level). The in-script baseline re-computation is the
   comparator (already-adjudicated data; not a new candidate).
2. Coverage diagnostics: share of firm-years re-timed; median months gained.

## Decision rule (frozen)

- **Primary:** small-segment **50 bps** `t_excess_net`, variant vs
  same-run baseline.
- **Confirm gate OPENS** iff variant small t_net(50bps) ≥ same-run baseline
  AND ≥ 1.5.
- **Confirm** (2019-01..2024-12, ONE run, 50 bps, small, baseline re-run
  alongside for apples-to-apples): **PASS** if net excess > 0 AND
  t_net ≥ 0.8 AND t_ic ≥ 1.5 (mirrors TRIAL-BRAIN-008's frozen rule and
  its power note — 72 months cannot deliver t≥2 at this effect size).
  **UPGRADE** verdict — "anomaly-time availability ADOPTED for the
  fundamentals stack" — iff additionally confirm t_net ≥ same-run baseline
  confirm t_net.
- **NEUTRAL/KILL:** explore variant < baseline → no improvement; the
  6-month convention stays; NEGATIVE_RESULTS entry (the Bowles effect does
  not survive our costs/universe).
- Largemid is a secondary diagnostic only — a largemid revival would need
  the standard graduation bar in a FUTURE registration, never this one.
- One-shot: single execution; crashes before any result is readable are
  repairable and disclosed (INSTR-VOC precedent).

## Result

(to be filled by the one run)
