# PREREG — INTERNET-INVESTIGATOR-FWD-1 (does investigation beat the snapshot?)

**Drafted 2026-08-14, before a single prediction is emitted.** Ruled as the next
session by the brain after GRAPH-COVARIANCE-1 closed Track B's covariance
branch. Track C of `ROADMAP_BRAIN_V3_2026-08-14.md`.

The question the whole campaign has never actually asked:

> SWARM-1 gave fourteen "specialists" the same engineered point-in-time
> numerical snapshot and told them they had no live feed. **Does letting the
> model INVESTIGATE — search news, read filings, pull revisions, query options,
> query the market graph — add anything beyond the snapshot we hand it?**

## Hypotheses

> **H1 (primary).** An arm that can investigate produces **better-calibrated
> forecasts** than an arm given only the engineered numerical snapshot, measured
> as a paired Brier difference on identical cells.
>
> **H2.** Investigation *without* the engine snapshot (`C_tools_only`) is worse
> than the snapshot alone — i.e. the engine is carrying real weight, not
> ballast.
>
> **H3.** Ticker anonymisation does not improve forecasts. This is not
> decorative: it is the direct test of Glasserman & Lin's finding, banked in
> `NEGATIVE_RESULTS` §19, that anonymising tickers **improved** returns because
> the model's company knowledge is a negative distraction.

Honest priors, stated before running: **H1 ~35/65 against; H2 ~70/30 for;
H3 ~60/40 for.** H1's pessimism is not modesty — it is the base rate this
programme has earned. Two independent measurements already found the LLM at a
coin flip on stock direction, and the persona swarm added nothing at 5.2× the
calls.

## THIS TRIAL MAKES NO ALPHA CLAIM, AND CANNOT

It grades **forecast quality**, never returns. Nothing is traded, sized,
weighted or allocated. No lane is touched. That scoping is not a disclaimer —
it is what makes the trial admissible at all under `NEGATIVE_RESULTS` §19,
which requires any LLM-signal registration to rebut all three banked external
receipts. Rebutted below, individually, as the rule demands.

| §19 receipt | why it does not block this trial |
|---|---|
| **1. Kim/Muhn/Nikolaev withdrawn** — "GPT-4 beats analysts at earnings direction", withdrawn after the authors' own replication found inconsistencies | This trial is **forward-only**. Every record resolves against prices that did not exist when it was written, so the failure mode of that paper — an internal replication failure on historical data — is structurally impossible here. There is no historical fit to fail to reproduce. It also does not forecast earnings direction; see the observable choice below. |
| **2. FINSABER** — FinMem/FinAgent/FINCON alpha disappears over 2004–2024 after commissions; buy-and-hold wins | This trial makes **no trading claim**, so commissions cannot erase what is never claimed. FINSABER's finding is that agents do not beat buy-and-hold; this trial does not contest that and does not need to. The comparison here is **within** the LLM family — tools versus no tools on identical cells — which FINSABER did not run. |
| **3. Glasserman & Lin** — GPT headline sentiment profitable only gross, daily, short-heavy; "not a feasible strategy"; **anonymising tickers improved returns**; edge concentrates in large caps | Again a trading claim, against a forecast-quality metric. But the anonymisation finding is a live threat to *this* design, so it is promoted into a **pre-registered arm** (`B_anon`, H3) rather than argued away. If ticker knowledge is a net distraction, this trial will measure it. |

## The design was chosen against a measured clock, not a hope

Two things were computed **before this document was finalised**, and both are
committed alongside it.

**(a) `scripts/iif1_power.py` — nights of accrual to 80% power**, by how much
true-probability variation exists (`sigma_pi`) and how much of it the
investigating arm captures. Receipt: `runs/INTERNET-INVESTIGATOR-FWD-1/power.json`.

| `sigma_pi` | Brier ceiling | nights at k=10 | k=20 | k=40 |
|---|---:|---:|---:|---:|
| 0.02 | 0.00040 | **never** | **never** | **never** |
| 0.05 | 0.00250 | never–500 | never–250 | never–180 |
| 0.10 | 0.01000 | 180–never | 60–never | 40–180 |
| 0.15 | 0.02250 | 60–never | 40–500 | 20–350 |

(ranges span capture gaps of 0.05 to 0.30 over an arm-A capture of 0.30.)

**(b) `scripts/iif1_sigma.py` — `sigma_pi` measured, not assumed**, as a
variance-decomposition lower bound across trailing-volatility deciles with the
binomial sampling term subtracted. 927,423 observations, 400 largest names,
2015–2024. Receipt: `runs/INTERNET-INVESTIGATOR-FWD-1/sigma_pi.json`.

| candidate observable | base rate | realised rate range | `sigma_pi` lower bound |
|---|---:|---:|---:|
| `return_sign` 1d | 0.524 | 0.517 – 0.529 | **0.0036** |
| `return_sign` 5d | 0.556 | 0.550 – 0.568 | **0.0061** |
| `abs_move_exceeds` 5%/1d | 0.031 | 0.005 – 0.153 | 0.0450 |
| `abs_move_exceeds` 8%/5d | 0.072 | 0.012 – 0.255 | 0.0734 |
| `abs_move_exceeds` 3%/1d | 0.101 | 0.020 – 0.334 | 0.0953 |
| **`abs_move_exceeds` 5%/5d** | 0.184 | 0.052 – 0.442 | **0.1183** |

**Cross-referencing the two tables settles the observable choice, and it
overturns the roadmap's default.** Direction is 20–30× less forecastable than
magnitude, and at `sigma_pi ≈ 0.004` the power table says a direction-based
primary **never resolves** — not at any trigger count, not at any effect size.
A trial whose primary is "will the stock go up" would have spent real money for
years and been unable to say anything at the end of it. That is precisely the
failure GRAPH-COVARIANCE-1's power gate caught one step later, applied here one
step earlier.

**So the primary observable is MAGNITUDE, not direction** — and this is a
deliberate deviation from the roadmap's unspecified "same prediction contract",
made on measured power grounds and recorded as a deviation.

It is also the right question on the merits. Whether a stock moves more than 5%
this week is genuinely knowable in advance by someone who finds out there is a
PDUFA date on Thursday or an earnings call on Wednesday — exactly the kind of
fact an investigation tool can retrieve and an engineered snapshot may not
carry. Direction, on the same news, remains a coin flip. The trial is pointed at
the part of the problem where investigation could plausibly pay.

**One honest deflation, stated now rather than discovered later.** The 0.1183
bound is measured from trailing volatility alone, and arm A's snapshot already
contains trailing volatility *and* options-implied volatility. Arm A will
therefore capture a substantial share of that budget before investigation adds
anything. **The residual budget H1 competes for is smaller than 0.1183 and is
not separately measurable in advance.** If the trial returns a null, that
ambiguity is part of the reading and is not to be quietly dropped.

## Arms

Every arm forecasts the **same cells** — same triggered tickers, same nights,
same observables, same horizons — so the comparison is paired within the cell
and the vast common variance of "what the market did" cancels before any SE is
taken (§18).

| arm | sees |
|---|---|
| `A_snapshot` | the engineered numerical snapshot only (the current SWARM-1 architecture) |
| **`B_tools`** | snapshot **+ investigation tools** — the primary contrast |
| `C_tools_only` | tools only; no engine snapshot |
| `D_all` | snapshot + tools + the MARKET-GRAPH-1 semantic graph |
| `B_anon` | identical to `B_tools` with ticker identity masked (§19 receipt 3) |

**Tools** (all already built, all inside the firewall, no new vendor):
`search_news` (GDELT), `read_filings` (SEC EDGAR), `query_revisions`,
`query_options`, `query_prices`, `query_market_graph`. **No historical web
retrieval** — current internet only, which is trivially satisfied because the
trial is forward-only.

## Contract — microtasks with belief-change

Replacing the single mega-schema, per the roadmap's Track C:

1. **Event extractor** — what changed, when, who is affected, novelty,
   expectedness.
2. **Relationship extractor** (`D_all` only) — source, target, type, direction,
   mechanism, confidence.
3. **Expectations analyst** — what did the market likely believe before; what
   changed.
4. **Forecaster** — `prior / posterior / belief_change` per (observable,
   horizon). **`belief_change = 0` is a valid, gradeable answer** and the
   `p ≠ 0.50` refusal is retired. The candidate signal is `posterior − prior`.
5. **Critic** — why is this chain wrong; what evidence contradicts it; which
   placebo would falsify it.

Each microtask is separately gradeable. `served_model` is recorded on every
call, from the response body, never from the name requested.

## Triggers — sparse, frozen, identical across arms

**k = 40 per night**, ranked by a composite unusualness score frozen in
`iif1_config.py` and computed from point-in-time data only: 1-day residual
return |z|, 20-day volume z, earnings within the next 5 trading days, and a
filing in the last 2 trading days. The **same 40 names go to every arm.** The
trigger rule is numerical and contains no LLM output; if it did, the arms would
not be paired.

k = 40 rather than 10 because the power table says trigger volume is worth
2–3× in time-to-detection, and the budget is not the binding constraint — at
5 arms × 40 triggers × ~5 microtasks ≈ 1,000 calls/night, and MARKET-GRAPH-1's
measured $0.00073/call on document-sized payloads, the expected spend is
**≈ $0.75/night against a $10–15 ceiling.** The binding constraint on this trial
is the clock, not the money, and the design is set accordingly.

## Primary metric and inference

**Primary (H1):** the paired per-night mean Brier difference

```
d_n  =  mean over that night's cells of  [ (p_A − y)² − (p_B − y)² ]
```

positive = `B_tools` forecast better. Because the cells are paired, the
irreducible `π(1−π)` term cancels **exactly**, and `d` is the difference in
squared error against the true probability and nothing else.

- Collapsed to **one number per grading night** before any SE is taken; n is the
  number of graded **nights**, not predictions, and both are printed (§19).
- **Newey–West at 2 lags**; `SE = max(HAC, IID)`; **MDE = 2.80 × SE**.
- Primary observables: `abs_move_exceeds` **5%/5d** and **3%/1d**.
- Inside the MDE is **not detectable** — never a kill, never a win.

**Pre-declared as underpowered by construction:** the direction observables
(`return_sign`, `beats_benchmark`) are recorded on every cell for the ledger and
**cannot resolve this trial**. At a measured `sigma_pi` of 0.0036–0.0061 the
power table says never, at any n. A null on them is not evidence of anything and
may not be reported as a kill. This is declared here so it cannot be discovered
afterwards and spun either way.

## Decision rule — frozen

**H1 ADOPTED** (as a research result about forecast quality, and nothing else)
only if **all** of:

1. `B_tools − A_snapshot` on the primary observables **exceeds its own MDE**
   with the sign meaning better forecasts;
2. it holds on **both** primary observables, or on the pooled statistic with the
   single-observable results printed beside it;
3. the **served model is verified identical across arms** — an arm silently
   served a different model is a model comparison wearing an architecture
   costume, which this programme has already been burned by once
   (`deepseek-chat`/`reasoner` were both `v4-flash`);
4. the effect is **not** reproduced by `B_anon` alone in a way that says ticker
   identity, rather than investigation, did the work.

| condition | recorded verdict |
|---|---|
| (1) fails | `NOT_DETECTABLE` — investigation not shown to add forecast quality |
| (1) holds, (2) fails | `SINGLE_OBSERVABLE_ONLY` — reported, not adopted |
| (3) fails | `VOID` — rerun with served models pinned |
| `C_tools_only` beats `A_snapshot` | reported prominently: the engine snapshot is not carrying its weight |
| `B_anon` beats `B_tools` above its MDE | **§19 receipt 3 REPRODUCED** — a finding in its own right, and a serious one |

**Nothing here may set a lane, a weight, a specialist score or a position size**
(A5/A6/A7). Certification remains forward-only and requires 24 months of record.

## Stopping and cost

- Registration precedes accrual; the registry row plus commit timestamp is the
  tamper evidence.
- **Nightly ceiling $10–15**, enforced by `research_budget.require()` before
  every wire request including retries, and **logged from served responses**,
  never estimated.
- A first-night **pilot** measures true cost and latency per arm before the
  nightly job is armed; if measured spend exceeds the ceiling at k = 40, k is
  reduced and the reduction is recorded with the number that forced it.
- Minimum accrual before the primary is READ AT ALL: **40 graded nights.**
  Reading earlier is peeking, and the power table says nothing below 40 could
  clear its MDE anyway.

## Frozen parameters

Enumerated in `scripts/iif1_config.py`, committed before the first prediction is
emitted. Nothing there may change after accrual begins; if something must, it is
a new trial with a new name.

## Corpse check

Run before registration; verdict recorded in the trial doc. `NEGATIVE_RESULTS`
§19's three-receipt rebuttal requirement is discharged above.
