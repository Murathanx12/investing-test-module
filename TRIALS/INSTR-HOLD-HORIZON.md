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

## Result (filled AFTER the run 2026-07-24 — never edited)
`runs/INSTR-HOLD-HORIZON/results.json`:

| band | net excess bps/mo | NW t | one-way turnover %/mo | net Sharpe | names |
|---|---|---|---|---|---|
| 1m | 14.1 | 1.48 | 9.7 | 0.566 | 297 |
| 3m | 15.3 | 1.66 | 9.4 | 0.575 | 313 |
| 6m | 15.8 | 1.78 | 8.9 | 0.578 | 331 |
| 12m | 17.0 | 2.11 | 8.3 | 0.591 | 363 |
| 24m | 14.4 | 2.04 | 7.6 | 0.579 | 410 |

**The curve is FLAT — prior confirmed.** Net performance is insensitive to
refresh cadence from 1 to 24 months (14-17 bps/mo); the 12-month band is the
gentle optimum, and longer holds cost nothing while cutting turnover ~20%.
The composite's payoff decays slowly, as its quality label implies; the
hold-band (signal-exit) mechanism, not the calendar, does the selling work.
Plain-English answer to "how long to hold": with a signal-band exit, holding
a year-plus is free — churning faster buys costs, not returns. No fragility
for the SMQ lane's quarterly refresh (it sits on the flat part). Reported
only; nothing retuned.
