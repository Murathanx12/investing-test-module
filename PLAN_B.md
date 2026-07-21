# PLAN_B — what if every BRAIN-00x signal rejects?

DeepSeek's review asked for this explicitly, and it is good discipline: knowing the exit
strategy is what lets you run the gauntlet honestly instead of p-hacking a "win" out of a
dead signal. Written 2026-07-21, before BRAIN-003 has run.

## First: a backtest REJECT is NOT project failure
The deploy gate (t>3.4, DSR≥0.95) is likely unclearable on ~18 years for a single-digit-bps
net edge — by design (five-AI review, weakness #2). So "everything rejects the backtest" is a
*probable*, *acceptable* outcome, not an apocalypse. The project's product is the **forward
calibration ledger**, not a backtest Sharpe. A well-calibrated forward Brier record on event
calls is a real, sellable asset even if no single signal clears the confirmatory gate. We do
not abandon on backtest rejects; we keep the forward clock running.

## The escalation ladder (pursue in order, each pre-registered)
1. **Fusion before surrender (BRAIN-007).** Weakly-positive, weakly-correlated signals can
   clear net where singles don't (diversification of alpha; JKP: it's the *theme cluster*,
   not the lone factor, that survives). Pre-register the fusion weights BEFORE seeing singles.
2. **Rotate to the anomalies that DO survive net.** Novy-Marx-Velikov / Chen-Velikov: the net
   survivors are **low-turnover, high-capacity** — size×quality (AFP "junk"-controlled),
   value, profitability. Less romantic than microcap events, but they clear costs. A
   quality-tilted, low-turnover core is the honest default book.
3. **The original thesis — suppliers-of-demand / capex lead-lag (TRIAL-THEME-SUPPLY).** Murat's
   demonstrated edge (V3 synthesis: Micron/Marvell HBM capex read). Causal, defensible,
   low-turnover. Runs on the EODHD/CRSP panel we have. This is the headline arc, still unrun.
4. **Time-series trend / managed futures.** Cross-asset time-series momentum is one of the most
   robust, capacity-rich, out-of-sample-validated premia (Moskowitz-Ooi-Pedersen). Needs
   futures/ETF data — a new data lane, but a genuinely different, uncrowded-at-small-size edge.
5. **Volatility / variance risk premium.** Structurally positive, well-documented; needs options
   data and careful tail management. A later frontier.
6. **International / emerging equities.** Same signals, less-arbitraged venues (JKP shows the
   factors work in 93 countries). Data-cost heavy; a scaling move, not a first move.

## The floor
If 1-3 all fail forward too, the deliverable is the **honest negative + the calibration
methodology itself** — a documented, reproducible demonstration of how hard net-of-cost alpha
is, with a forward record proving we didn't fool ourselves. That is a real contribution and the
credibility base for any future capital. We publish it; we do not fake a win.

## Trigger
Revisit this ladder when either (a) BRAIN-003..006 + the BRAIN-007 fusion all reject on
backtest AND show no forward calibration edge after ≥30 scored calls, or (b) 12 months of
forward ledger shows Brier no better than base rate. Until then, the plan of record stands.
