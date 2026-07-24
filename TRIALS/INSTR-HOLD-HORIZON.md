# INSTR-HOLD-HORIZON — refresh-cadence fragility of the BRAIN-007 composite

**Registered:** 2026-07-24 (UTC), BEFORE running. **Registry row:** `TRIALS/registry.jsonl`.
**Class:** measurement instrument (like INSTR-OVERFIT-CEILING) — reported
only, NEVER an adoption decision. The SMQ lane's quarterly artifact refresh
is frozen by TRIAL-SMQ-FWD and does not change based on this readout.

## Question (Murat's "how long should we hold?")
On the exact BRAIN-007 composite spec (insider+gp equal-weight z, top
quintile large/mid, ADV costs, 2006-2024 window — `run_trial_007.py`
mechanics verbatim), how do net excess return, turnover, and Sharpe vary
with the book's hold-band length: 1 / 3 / 6 / 12 / 24 months?

## Literature prior (2026-07-24 sweep)
Novy-Marx–Velikov: BANDING beats rebalancing less often; quality signals
decay over years, momentum over months — so the composite (quality-heavy)
should be nearly flat in net terms from 3mo out to 12-24mo, with turnover
(and costs) falling monotonically. If net performance COLLAPSES at long
bands, the composite's payoff is faster-moving than its quality label
implies — a fragility finding for the SMQ lane's refresh design.

## Frozen spec
Five configs = BAND_M ∈ {1, 3, 6, 12, 24}; everything else byte-identical to
TRIAL-BRAIN-007's frozen run (same window, universe, z construction, costs,
MIN_NAMES). Report per config: net excess bps/mo, NW t, mean one-way monthly
turnover, net Sharpe, mean names. 5 configs recorded in the honesty ledger.
No graduation rule — there is nothing to adopt; the deliverable is the curve.

## Result (filled AFTER the run — never edited)
_pending_
