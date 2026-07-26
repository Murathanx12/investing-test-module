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

## Result (one run, 2026-07-26): **PASS + UPGRADE — with the decomposition shown**

`data/factory/instr_anomaly_time.json`. Coverage: 90.2% of 136,546
firm-years re-timed; median rdq lag 53 days; **median 4.0 months of
availability reclaimed**. Same-run baseline reproduced the recorded batch-2
numbers exactly (2.35/1.96, +27.8/+23.2) — code-path integrity confirmed.

| run (small, 50bps) | net excess bps/mo | t_net | IC t | turnover |
|---|---|---|---|---|
| explore gp_base | +23.2 | 1.96 | 6.03 | 0.092 |
| explore gp_ead | **+25.9** | **2.19** | 6.18 | 0.092 |
| confirm gp_base | +24.1 | 0.89 | 4.29 | 0.095 |
| confirm gp_ead | **+33.5** | **1.24** | 4.35 | 0.095 |

Gate opened (2.19 ≥ 1.96 ≥ 1.5). Confirm PASS (net>0, t 1.24 ≥ 0.8,
IC t 4.35 ≥ 1.5) and UPGRADE (1.24 ≥ 0.89) — **by the letter of the
frozen rule.**

**Both hands (post-run diagnostics on the fixed runs, disclosed):**

- Paired book-level net diff: explore +3.3 bps/mo (t 1.07), confirm
  +2.7 bps/mo (t 0.39). The book genuinely improves, weakly, in BOTH
  windows, at literally identical turnover (the re-timing is costless).
- Decomposition of the confirm +9.4 excess-net headline: **+2.7 from the
  book, +6.8 from a lower benchmark** — the EAD universe admits ~37 more
  recently-reported names/month whose average return is lower. The
  headline overstates the tradeable effect ~3×.
- Largemid stays net-dead (−0.19 explore) — no revival claim.

**Adoption rationale (honest):** anomaly-time availability is ADOPTED for
the module fundamentals stack because (a) it is strictly more PIT-correct —
the 6-month lag was conservatism, not information; rdq is the true public
date; (b) the book-level effect is weakly positive in both windows and
free; (c) the frozen rule says so. It is NOT adopted on the +9.4 headline,
which is mostly benchmark composition. Bowles et al.'s "month-1
concentration" is directionally present but small in our small-cap
50bps-cost world — consistent with our house law that honest costs shrink
everything.

**Consequences:** future fundamentals registrations may declare EAD
availability at freeze time (per-row rdq with +6mo fallback, this spec).
BRAIN-008's confirmed record and its forward clocks are UNCHANGED — this
instrument upgrades the toolkit, not the survivor's history. The
conditional inv_div-EAD retry (round-7 review Hyp C) is now admissible as
a future pre-registration.
