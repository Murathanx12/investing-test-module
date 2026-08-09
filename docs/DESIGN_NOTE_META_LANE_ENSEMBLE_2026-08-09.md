# DESIGN NOTE 2026-08-09 — lane ensembles, and the cell we are declining to register

**This is a design note, not a registration.** It makes no money claim, opens no
trial, and nothing in it may be cited as evidence. Its purpose is to record one
generalization worth carrying forward and one temptation worth naming.

Adjudicated by Murat, 2026-08-09, on the PF-2 `PF-META-1` results.

## The temptation, named

PF-META-1's frozen grid was lookback ∈ {6, 12, 24} months × hold ∈ {top-1,
top-2}. One cell — **L12T2** (12-month lookback, hold top-2) — printed
**+6.32 %/yr and 24.72× the benchmark**, beating even the hindsight-chosen best
single strategy.

**We decline to register it.** Registering the best cell of a scanned grid is
the multiple-testing trap in its purest form: the grid was scanned precisely so
that its best cell could be found, and the best cell of any scanned grid is
positive by construction. The neighbours confirm it — the same top-2 rule at
lookback 6 gives **+3.41 %/yr** and at lookback 24 gives **+0.84 %/yr**. A real
effect does not evaporate when you nudge a lookback by six months; a lucky cell
does exactly that.

The honest reading of L12T2 is: *one draw from a six-cell scan landed high.*

## The generalization that IS credible

Across **every** lookback tested, moving from hold-top-1 to hold-top-2 cut ruin
by roughly an order of magnitude:

| | hold top-1 | hold top-2 |
|---|---|---|
| P(maxDD > 60 %) | 0.604 | 0.062 |

That is not a scan artifact — it holds at 6, 12 and 24 months, i.e. in every
cell rather than one of them. It is also not a discovery: it is diversification,
which is the one thing in this field that works without needing to be believed.

**Carry forward, for future lane-ensemble design:** an ensemble that concentrates
on a single trailing winner carries roughly ten times the ruin risk of one that
holds two, at no reliable return benefit. Any future ensemble construction
should default to holding more than one.

**Do not carry forward:** any specific lookback, any specific N, any expected
return figure from this grid.

## Relation to Murat's "11th account"

The registered question was whether a paper account that copies whichever
strategy has been winning should exist. On the common window the answer was
measured and is negative: winner-copying returned **6.63×** against
equal-weighting the same six strategies at **7.18×**, with ruin 0.604 vs 0.097
and 164 strategy switches against 3. Switching costs alone took 1.6 %/yr.

So the honest form of the 11th account is **equal-weight all the lanes**, not
**copy the winner** — and that construction is itself only a candidate, subject
to the same gates as anything else. This note does not register it.
