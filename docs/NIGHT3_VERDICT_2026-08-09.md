# NIGHT-3 VERDICT — masked decision replay and the experience brain

**Trial:** `TRIAL-NIGHT3-DECISION-REPLAY-1` · pre-registration
`TRIALS/PREREG_NIGHT3_DECISION_REPLAY.md`, sealed **before** the first LLM call.
**Branch:** `factory/night-3` (Aegis module). No lane seeded, no flag flipped,
`paper_nav` untouched, **2023-01..2024-12 holdout unread**.
**Model:** `deepseek-chat`, temperature 0, every response cached immutably by
`(model_id, sha256(system+user))`.

> *Placeholder — Sections 2 onward are completed when the 204-month replay
> finishes. Sections 1 and 3-6 are final and are reported whatever the replay
> returns.*

---

## 1. The headline, before the economics

**The most consequential number tonight was produced without an LLM at all.**

Inside the engine's own top-40 profitability slate, sorting by the composite is
worth **+1.46 %/yr, t = 0.43** (top-20 minus bottom-20 of the same 40 names,
204 months, gross of costs). That is nothing. A stratified slate spanning all
five composite quintiles is **worse** (+2.23 %/yr at **t = 0.15**, and a smaller
mean monthly separation: 0.054 % vs 0.14 %).

So, measured rather than assumed:

> **PROF-COMPOSITE-150's edge lives in MEMBERSHIP — which 150 names out of
> ~2,000 — and not in ORDERING. At the monthly name level, inside that
> membership, nothing ranks: not the LLM, not the engine, not anything, at this
> sample size.**

This reframes the registered question. M1 asks whether the LLM out-picks the
engine *within a set the engine has already chosen*, and the control it is
measured against turns out to have no measurable ordering skill of its own. A
null M1 therefore cannot be read as "the LLM is worse than a good selector"; it
reads as "neither the LLM nor the engine can order a homogeneous small-cap
profitability slate month by month".

**What this bought us:** the stratified environment was built and then **not
run**. The power analysis is the receipt. Running a second 204-month LLM
campaign to discover the same thing would have cost a night and taught nothing.

*(Receipts: `runs/NIGHT3/POWER_CHECK.json`,
`runs/NIGHT3/POWER_CHECK_STRATIFIED.json`. Oracle arms use hindsight, can never
be candidates, and exist only to bound what any decider could achieve.)*

### 1b. Independent corroboration — from numbers already on disk

This is **not a new test**. It is a re-reading of the PF-1/PF-2 concentration
grid, which was computed and banked before tonight. If the composite's ordering
carried information, deepening the book from 10 names to 150 would progressively
add worse names and the excess return would fall. It does not:

| names held (small-cap segment) | net excess CAGR | NW t |
|---|---|---|
| 10 | +4.46 % | 1.92 |
| 25 | +4.35 % | 2.00 |
| 50 | +4.71 % | 2.30 |
| 100 | +4.36 % | 2.36 |
| **150** | **+4.67 %** | **2.52** |
| 200 | +3.87 % | 2.34 |

**Flat return, monotonically rising t-stat.** Names ranked 26th to 150th are, on
this evidence, as good as names ranked 1st to 25th; all that breadth buys is
less noise around the same edge. Dilution only begins past ~200.

Segment, by contrast, is decisive: the same signal pays **+4.67 %/yr in small
caps, +2.29 % across all caps, +1.56 % in large/mid**. That is the same fact the
PF-2 factor gate saw from the other side (`rmw` loading 0.135 — RMW is
value-weighted and large-cap, so it does not span this).

Two independent measurements, one conclusion:

> **The strategy's edge is MEMBERSHIP — own a lot of profitable small caps.
> Ranking inside that membership carries no measurable information. So
> concentration adds risk without return (already measured: `PF-RISK-SAT-1`,
> −2.25 %/yr at P(DD>60 %) = 0.994), and an LLM asked to re-rank inside the set
> is being asked to do the one job with no information in it.**

---

## 2. M1 — does the LLM add anything over the engine?

*(completed on replay finish)*

## 3. The coherence gate, and what its failure actually was

`TRIAL-COHERENCE-BATTERY-1`, 100 synthetic scenarios × 5 perturbations × 2
sides = **1,000 calls, 500 usable pairs**. One variable moves per pair;
everything else is byte-identical.

| direction | registered format (decimal) | diagnostic format (basis points) |
|---|---|---|
| valuation cheaper → more attractive | 0.66 · **34 ties · 0 wrong** | 0.90 · 10 ties · 0 wrong |
| earnings beat > miss | 0.56 · **44 ties · 0 wrong** | 0.87 · 12 ties · 1 wrong |
| bull regime ≥ bear regime | 0.75 · 25 ties · 0 wrong | 0.89 · 11 ties · 0 wrong |
| less geopolitical risk ≥ more | 0.95 · 5 ties · 0 wrong | 1.00 · 0 ties · 0 wrong |
| upward revisions > cuts | 0.93 · 7 ties · 0 wrong | 0.98 · 2 ties · 0 wrong |
| **directions passing at ≥0.70** | **3 of 5 → INCOHERENT** | **5 of 5** |

**The registered verdict stands: 3 of 5, INCOHERENT, prediction N3 MISS.** The
gate was pre-registered with the decimal response format and its bar frozen; it
is not re-scored because a different format did better. That is the whole point
of freezing it.

But the decomposition the grader was built to expose says what the failure *is*:
**0 wrong directions in 500 pairs.** The model never once reversed a
relationship. Every failure was a **tie** — it gave the same number to both
sides. `DIAG-COHERENCE-RESOLUTION-1` (registered before compute, explicitly
unable to overturn the gate) re-asked the identical scenarios in **basis
points** and ties collapsed from 115/500 to 35/500.

> **The model's directional logic is sound; its numeric resolution is not.
> Asking for decimals costs you the ability to detect small effects. Ask for
> basis points.**

That is an engineering conclusion for how we elicit numbers, and it applies to
every downstream elicitation in this project.

## 4. NAME-ONLY — the contamination ceiling could not be measured as registered

`TRIAL-NAME-ONLY-1`: real ticker, real date, **no financial data at all**, on
the identical 120-event set AMNESIA used.

**The model abstained on 120 of 120**, stated basis `no_information` every time.
Zero scored events. The registered prediction N4 (AUC ≥ 0.55) is therefore
**UNRESOLVED**, not hit and not missed.

`DIAG-NAME-ONLY-FORCED-1` (registered before compute) removed the abstain door:

| arm | Brier | AUC |
|---|---|---|
| **NAME-ONLY forced** (identity + date only) | **0.2483** | **0.571** |
| A0 named + full percentile facts | 0.2495 | 0.550 |
| A1 named + "ignore what you know" | 0.2530 | 0.532 |
| A2 masked | 0.2568 | 0.519 |
| A3 synthetic | 0.2564 | 0.521 |
| out-of-sample logistic on 5 features | 0.2538 | 0.511 |

Two things must be said together, or the number misleads:

1. **On identity alone the model scores at least as well as it does with the
   data.** Whatever A0's edge over masked was, it was not analysis.
2. **None of it is significant.** Bootstrap 95 % CI on the forced AUC is
   **[0.481, 0.656]**, P(AUC ≤ 0.5) = 0.068, n = 120. Every arm in that table
   sits within noise of a coin flip. The honest reading is *"12-month
   beat-the-market on single names is a task on which none of these methods
   demonstrably works"*, and the contamination ceiling is at most a whisper.

Also measured, and consistent with §3: the forced arm used **5 distinct
probability values** across 120 events (range 0.35-0.55, sd 0.042). The same
coarse-output signature appears in two independent experiments.

**Standing rule from this:** any future unmasked diagnostic must be quoted
against the forced NAME-ONLY number *and* against the fact that the unforced
model declines 100 % of the time. The two say different things and neither
substitutes for the other.

## 5. Consistency — measured, never requested

*(repeat probe + persistence grading completed on replay finish)*

## 6. Prediction scorecard

*(completed on replay finish)*
