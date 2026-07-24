# TRIAL-THEME-SUPPLY-supplier-baskets

**Registered:** 2026-07-24 (UTC) — BEFORE implementation or any return join.
**Registry row:** `TRIALS/registry.jsonl`
**Grade:** paper-grade backtest (CRSP), explore/confirm protocol (this doc
registers the EXPLORE run only; a confirm run needs its own pre-registration).
**Cumulative explore candidates: 88 + 2 = 90** (one signal × two segments).

## Provenance
Murat's "buy the future early / suppliers of the winners" headline thesis.
The FAST cross-sectional arm (cust_mom, Cohen-Frazzini monthly link-momentum)
was adjudicated REJECT in batch 3b: 70% one-way monthly turnover, net ≈ 0.
This is the SLOW arm the 3b closure explicitly left open: thematic supplier
baskets at annual cadence — the turnover objection is removed by design, so
what remains is whether the information survives the slower clock.

## Hypothesis
Suppliers whose customers have performed strongly over the trailing year
(salecs-weighted 12-1 customer momentum) earn positive net-of-cost excess
returns vs the supplier universe over the FOLLOWING 12 months, on CRSP
explore window 2004-2018. Mechanism: gradual diffusion of customer-demand
news down the supply chain, too slow to be arbitraged at monthly frequency
but persistent at annual holding periods.

## Honest prior
~30/70 against. cust_mom's monthly IC t was only 1.6-1.8 (real-ish, weak);
annualizing loses timeliness and Madsen (2017) shows anticipated-earnings
effects partially pre-price customer links. The thesis survives only if the
diffusion horizon is genuinely long.

## Signal (frozen)
- Links: `seg_customer.parquet`, ctype=COMPANY only, customer name→gvkey via
  the audited normalized-exact matcher in `factory/altstores2.py` (unmatched
  links drop and are counted — understates, never overstates); PIT validity =
  srcdate + 6 months → srcdate + 30 months (same as cust_mom).
- Customer strength at formation = compounded return months t−12..t−2
  (12-1 momentum, skip the formation month t−1).
- Supplier score = salecs-weighted mean of matched customers' strength.
- Formation: each JUNE month-end (annual refresh, Fama-French convention).
- Portfolio: top decile of scored suppliers within segment, EW, held 12
  months via hold-band. Segments large_mid / micro (harness convention).

## Arms
- **B** top-decile suppliers (hypothesis). **A** bottom decile (spread test).
- **noise** — same monthly counts, suppliers drawn randomly from the scored
  (coverage) universe at each formation; gross |t| ≥ 3 voids the run.
- Benchmark = EW of the scored-supplier coverage universe within segment.

## Run spec
EXPLORE WINDOW ONLY: 2004-01..2018-12 (scan hard-stops at the boundary; 2019+
is held out and untouched). 25 bps one-way costs, min_names=10, metrics: net
excess vs coverage benchmark (NW t), gross t, B−A spread t, FF5+UMD alpha,
DSR vs cumulative candidate count (90). ONE run. Results final.

## Kill conditions
1. noise gross |t| ≥ 3 → leak, void.
2. B net t < 1 in BOTH segments → REJECT (thesis's basket arm closes; a
   different mechanism class would be a new registration).
3. B − A spread net t < 1 → no cross-sectional information at annual cadence
   (reported alongside 2).
4. PASS = B net t ≥ 1.5 in a segment AND spread t ≥ 1 → earns ONE
   pre-registered confirm run on 2019-2024 (separate registration, DSR
   deflated by the then-current cumulative count).

## Result (filled AFTER the run — never edited)
_pending_
