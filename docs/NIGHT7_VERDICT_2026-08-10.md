# NIGHT-7 VERDICT — 2026-08-10

**Branch:** `factory/night-7` · **Brief:** `docs/NIGHT7_BRIEF_2026-08-10.md`
**Receipts:** `runs/NIGHT7/` · **Preregs:** `TRIALS/PREREG_PF7_EXIT_SWEEP.md`,
`TRIALS/PREREG_TEXT_LAZY_SEMANTIC_DIFF.md` · **Tests:** 495 green (470 + 25 firewall)

---

## The headline

**No tested exit rule demonstrated an incremental benefit — and the trailing
stop, which the monthly panel ranked FIRST, loses 3.08%/yr once execution is
measured instead of modelled.**

*(Wording corrected after review: five arms failing to separate is evidence
about **these five rules on this book**, not a proof that exit policy is
irrelevant. The trailing-stop **implementation** is rejected outright; the
question of whether a stop **trigger** carries information is reopened as T2c
below.)*

Second headline, and the more consequential one for the programme:

**The survivor's excess Sharpe is not distinguishable from the best of its own
search.** Its annualised excess Sharpe is **0.449**; the expected maximum of 179
pure-noise draws over the same window is **0.431**. The Deflated Sharpe statistic
is **0.549** — which does **not** mean "a 55% chance the alpha is real" (see the
correction in §T4).

Third, unglamorous and immediately usable:

**Rebalance-date luck is worth a 2.45 percentage-point/yr range** (+2.24% to
+4.69% depending purely on which month you rebalance in). That is **three times
the entire spread across all five exit rules**, and it appears **cheap to
diversify away**.

*(Wording corrected after review, twice over: (a) the 2.45 pt/yr figure is a
max-minus-min **descriptive range** across twelve highly dependent cohorts — it
is not a confidence interval; (b) "free" was quoted from the **monthly panel's**
turnover number, which is precisely what CANON §15 — written the same night —
forbids. The G7 measurement that settles it is `runs/NIGHT7/T1b_ENSEMBLE_G7.json`
and is reported in §T3b.)*

---

## T0 — Housekeeping ✅

`factory/night-5` and `factory/night-6` merged to main (night-5 was an ancestor
of night-6, so one merge carried both). 470 tests green post-merge, including the
G7 and verdict-guard suites. `factory/night-7` cut from there.

## T1 — Citation gate ✅ · `runs/NIGHT7/VERIFIED_CITATIONS.md`

20 claims read at source. **The brain's prediction #1 named the wrong casualties
and was wrong about the mechanism.** Lazy Prices' "188 bps/month" is exactly what
the JF abstract says; 3S-Trader's "131.83%" is exactly what that paper reports.
The brain's own recollection (30–60bps/month) was the error.

What actually failed was subtler and more important:

> **The reviews almost never fabricated a number. They quoted real numbers with
> the qualifier removed — the qualifier that decides whether the number transfers
> to us.** A long-**short** alpha quoted to a long-only book. A
> rebalancing premium measured against **buy-and-hold** quoted as if it were
> alpha against a rebalanced benchmark. A 131.83% cumulative return quoted
> without its **Sharpe of 0.31** — which makes it evidence *against* the thing it
> was cited to support. Fabrication would have been easier to catch.

Four items did not survive as used (Chaudhuri: **1.10/0.85**, not 1.08/0.82;
Maeso-Martellini: wrong benchmark, **withdrawn from our vocabulary**; 3S-Trader:
Sharpe omitted; reviews 2/3's bps tables: no source). Two were unverifiable.

**One verified finding corrects US, not them.** LAP (arXiv:2512.23847) and FinCAD
(arXiv:2605.24564) show outcome memory keyed on the **date**, not the entity —
positive in-sample, collapsing after the training cutoff, and worth up to −67.1%
of in-sample backtest return when suppressed. NIGHT-1 measured only that masking
hides the **company** (0/240 identifications). So:

> **Masking is necessary but not sufficient. NIGHT-1's headline is amended:
> masked replay is a REASONING laboratory, not an ALPHA-CERTIFICATION
> laboratory.** This is now enforced in code — `ExtractionRequest.alpha_certifiable`
> is `False` unless date/era leakage was controlled, not just entity.

## T2 — THE EXIT SWEEP ✅ `runs/NIGHT7/T2_EXIT_SWEEP.json`

Registered before compute (`a6abd30`). Entry held fixed at the banked book;
five exit arms; every arm fully invested at 150 names so cash drag cannot
masquerade as exit skill.

**Reconciliation passed exactly**: the exit code path reproduces the banked
baseline with `max abs monthly diff = 0.0` over 482 months. Without that, no arm
would have been interpretable.

| arm | net excess | gross excess | turnover | cost bps | paired Δ vs A0 | paired NW t | MDE |
|---|---|---|---|---|---|---|---|
| **A0** annual rank rebalance | **+4.40%** | +4.76% | 0.478 | 31.3 | — | — | — |
| **A1** trailing stop −20% | **+4.74%** | **+5.74%** | **1.298** | **86.6** | +0.34% | 0.27 | 1.21% |
| **A2** momentum hold | +4.17% | +4.51% | 0.452 | 30.0 | −0.23% | −1.15 | 0.46% |
| **A3** fundamental break | +3.95% | +4.32% | 0.496 | 33.5 | −0.46% | −1.24 | 0.67% |
| **A4** earnings-anchored | +4.18% | +4.57% | 0.519 | 34.0 | −0.22% | −0.77 | 0.41% |

**No arm reaches paired |t| ≥ 2.0.** Max is 1.24. Arm-to-arm correlation with
the baseline is 0.983–0.998 — five books sharing 150 names and one entry rule
are simply too alike to separate on 40 years. Best-worst spread: **0.79%/yr**.

**Verdict: UNRESOLVED for every arm.** The exit layer, as tested, does not
change the outcome measurably. That is a real answer to the brief's question,
and it is *not* "exits don't matter" — it is "these five exits, on this book, are
indistinguishable, and this design could not have seen a difference smaller than
0.4–1.2%/yr."

### T2b — the arm that had to be measured ⚠️ `runs/NIGHT7/T2b_EXIT_G7.json`

A1 ranked **first** on the monthly panel while trading **2.7×** as much. NIGHT-6's
rule exists for exactly this: the monthly panel understates churn cost, so a
high-turnover arm's monthly net is an upper bound, never a result. A1 went
through G7's daily simulator against A0 on the same daily spine, 2002–2024.

| at $1m NAV | A0 | A1 | difference |
|---|---|---|---|
| monthly panel says | +13.73% | +13.08% | **−0.65%/yr** |
| **daily execution says** | **+13.45%** | **+10.37%** | **−3.08%/yr** |
| costs paid over 23 years | $333,165 | **$1,076,764** | **+$743,599** |
| daily max drawdown | −52.6% | **−56.9%** | worse |

**On a $1,000,000 account, the trailing stop pays $743,599 more in costs over 23
years — 74% of starting capital — to end up 3.08%/yr behind.** At $50m the extra
bill is $31.2m. The monthly panel understated the penalty by **2.43 pts/yr** —
*the same magnitude NIGHT-6 measured for the monthly-vs-annual clock*. Two
independent turnover increments, the same understatement. That is now a
calibrated property of the panel, not an anecdote.

**A silent-fragility trap was found and fixed before this ran.** `holdings_out`
flagged only full rebalances, so exit-driven interim trades were invisible to
G7 — the highest-churn arm would have been measured on the *baseline's* trade
schedule and its churn cost would have vanished silently. The house failure mode,
aimed squarely at the arm most likely to be wrong.

**Product answer, and it is unambiguous: do not use trailing stops.** Note the
decomposition: A1's *selection* was the best of the five **gross** (+0.98%/yr,
t 0.94 — UNRESOLVED, so not a finding), and its *execution* destroyed three times
that. Bessembinder's mechanism was predicted to show up in the gross return; it
did not. It showed up in the bill.

## T3 — Clock ensemble ✅ `runs/NIGHT7/T3_CLOCK_ENSEMBLE.json`

**The first run was wrong, said so, and the guard is now permanent.** Shifting
`first_month` does not stagger this book: the small segment is too thin to seat
150 names until 1982, so all twelve "cohorts" collapsed onto one date and printed
twelve identical numbers. A real clock **phase** was added to the engine, plus a
check that refuses to report an ensemble whose cohorts do not have distinct
first-trade dates.

Real result, 12 phases, 1983-10 … 2022-12 (471 common months):

- Individual clocks: **+2.24% to +4.69%** excess CAGR — **a 2.45 pt/yr range**,
  σ across start dates **0.80%/yr**.
- Ensemble (1/12 per cohort): **+3.48%** vs mean-of-clocks **+3.43%** → gap
  **+0.04%**, i.e. no free lunch, exactly as it should be.
- Turnover **unchanged** (mean cohort 0.468; each cohort trades once a year, so
  the ensemble trades 1/12 of the book monthly at the same annual cost).
- Vol 20.93% vs mean cohort 21.14%; max DD −47.4% vs −47.7%. Correctly tiny — the
  cohorts hold overlapping books, so this diversifies **start date**, not market
  risk.

**Reading: an investor who picks one rebalance month is exposed to a 2.45 pt/yr
swing they cannot forecast, and can eliminate it for zero cost and zero extra
turnover.** This is a deterministic implementation claim. It is not alpha, it is
not quoted as alpha, and it is bigger than the whole exit-rule spread.

## T4 — Trial-count accounting ✅ `runs/NIGHT7/T4_DEFLATED_SHARPE.json`

Published as promised, and it does not flatter us.

Deflated Sharpe on the **excess** series (the claim is "it beats the market").
V[SR] is estimated from **our own graveyard**, not assumed — and reported under
three assumptions rather than one, because there is no single defensible value
and picking one silently is where this statistic usually goes wrong.

| V[SR] assumption | ann. σ of trial Sharpes | break-even N at DSR 0.95 |
|---|---|---|
| RAW graveyard (over-deflates: contains cost-destroyed books at t −8.4) | 0.486 | **1** |
| ROBUST (MAD-based, tail-resistant) | 0.345 | **2** |
| **NULL — all trials pure noise (most favourable defensible)** | 0.158 | **5** |

**Under every assumption, at every N ≥ 5, the survivor fails DSR 0.95.**

At the counts actually on record — 148 scored graveyard rows, 179 closed
candidates, **827** programme-wide (90 specs + 89 registered trials + 648 search
cells) — under the *most generous* assumption:

| N | E[max SR] under null (ann) | DSR |
|---|---|---|
| 50 | 0.359 | 0.725 |
| 148 | 0.421 | 0.575 |
| **179** | **0.431** | **0.549** |
| 821 | 0.505 | 0.357 |

The survivor's own annualised excess Sharpe is **0.449** (as banked) / **0.444**
(shippable annual). The expected maximum of 179 pure-noise draws over the same
window is **0.431**. **We beat noise-selected-179-times by 0.018 of Sharpe.**

> **The honest label, unchanged: factor harvest plus an unproven residual. The
> historical survivor does not establish unique alpha once the search is
> accounted for.** The brain's prediction #2 was correct.

### CORRECTION (external review, 2026-08-10) — what DSR 0.549 does and does not mean

Three reviewers read this section; one caught a real error in it, and the
correction is load-bearing enough to sit inside the result rather than in a
footnote.

**Wrong (as originally written here): "P(true excess Sharpe > 0) ≈ 0.55."**
DSR is not a Bayesian posterior over the strategy's true alpha. It is a
probabilistic-Sharpe-style statistic evaluating an observed Sharpe against a
*selection-adjusted benchmark Sharpe* under a sampling model. Calling it a
posterior gives it more epistemic content than it has.

**Right:** *the historical survivor does not establish unique alpha after
accounting for the search.* That is the claim the arithmetic supports.

**And a second guard-rail, from our own record.** GATE-M1 (2026-08-06) measured
this exact gate and found **DSR ≥ 0.95 has almost no power against realistic
injected edges** — the ratified ladder had a *measured 0% probability* of
adopting a true α=0.6 constant edge. NEGATIVE_RESULTS records the same. So DSR
must not be re-armed here as a universal kill gate; the JSON has always carried
`status: REPORTED-NEVER-DECIDING`, and this prose now matches it.

**DSR < 0.95 does NOT prove the strategy is false.** It says the historical
evidence, discounted for the search, is not exceptional. Those are different
claims and only the second is ours.

**The right way to settle it is not to argue about N.** A reviewer's proposal —
adopted and registered as **T4b** — is an empirical selection-bias bootstrap:
block-bootstrap the *same* time blocks across all candidates so their real
cross-correlation and time dependence survive, impose the null, and build the
empirical distribution of the best statistic in each bootstrapped universe. That
answers "how often would a null factory of *our* candidates produce a winner this
good?" directly, in the White Reality Check / Hansen SPA tradition, instead of
debating whether N is 179 or 40 or 5. Note that **179 can be simultaneously too
high and too low**: too high because many candidates are correlated variants, too
low because rank-shape, clock, frequency and exit branches were all subsequently
explored on the same history.

This does not retract NIGHT-4's decomposition (the +4.23% was real and was then
spanned by a self-built profitability factor). It removes the last basis for
treating the residual as demonstrated skill.

## T5 — The firewall, in code ✅ `aegis_brain/firewall/` · 25 tests

Murat's brain, built so it cannot fool us. Three layers, one irreversible
boundary, and the boundary **raises** rather than being documented:

- **Layer 1 extraction** — `ExtractionRequest` refuses outcome-shaped context
  (regex over ret/price/pnl/alpha/label/forward/…); `Extraction` refuses to exist
  without a full `ProvenanceStamp` (as_of, doc id, model ver, prompt hash) and
  refuses to emit outcome-shaped fields; every field needs a confidence, because
  an unscored field cannot be calibrated and an uncalibratable field is not a
  measurement.
- **The crossing** — `LearningSample` is the only place an outcome appears, and
  it rejects any outcome timestamped at or before the extraction's `as_of`.
  `to_layer1_payload()` exists **solely to raise**, so the attempt to feed
  outcomes backwards fails loudly instead of being written by someone who assumed
  it was allowed.
- **Layer 3 adjudication** — read-only. `set_weight()` raises. A `VETO` without a
  rationale raises. Its `probability` is Brier-scoreable, so an adjudicator that
  vetoes indiscriminately becomes measurably badly calibrated and loses standing.

**"The brain learns" now has a precise meaning:** the calibration map
`(feature_type × regime × model_version) → realised skill`. It needs hundreds of
**scored predictions**, not hundreds of backtests — which is why the forward
paper lanes are the asset and the backtest is not.

**Not licensed:** no self-improving memory loop until Layer 1 has a measured
calibration curve. First registered target: **PRisk replication** (Hassan et al.
QJE 2019; firmlevelrisk.com verified live 2026-08-10 — free, 2002–2021q2,
>11,000 firms, 81 countries).

## T6 — Semantic diff: REGISTERED, **NOT RUN** ✅ `TRIALS/PREREG_TEXT_LAZY_SEMANTIC_DIFF.md`

The power check ran before the compute, and it refused the compute.

Prior, derived in the open: **188 bps/mo** (verified) → long-leg only **×0.30**
(generous; our own §28 measurement implies ×0.01–0.12) → McLean-Pontiff decay
**×0.5** → **≈3.4%/yr**, and that is the optimistic end.

Power on the usable window (EDGAR full text is 2001+, so 264 months; σ = 3.06%/mo
measured from this harness on that exact window):

- **MDE at t=2.0: 4.52%/yr.** At the Harvey-Liu-Zhu t=3 bar: **6.78%/yr.**
- **MDE > prior. POWER_FAILED before compute. The money version does not run.**

Running it would have produced a null that says nothing — the exact failure the
graveyard census found in 66% of the closed search. **We did not add row 149.**

What *is* licensed is the version that isn't a strategy test at all: semantic
diff as a **Layer-1 extractor validation**, scored by rank IC on filing-pairs
(thousands per year) against non-price ground truth. Our own graveyard shows the
asymmetry — rows with rank-IC t 6.63 and net t 0.37 on the same signal.

---

## Predictions, scored

**Worker's five (written before compute, prereg §5):**

| # | prediction | outcome |
|---|---|---|
| 1 | no arm reaches paired \|t\| ≥ 2.0 | ✅ **HIT** (max 1.24) |
| 2 | A1 most negative in gross and net; negative gross | ❌ **MISS, badly** — A1 was **best** in both (gross +5.74% vs 4.76%) |
| 3 | A2 lowest turnover **and** net above A0 | ⚠️ **HALF** — lowest turnover ✅ (0.452), but net −0.23% below A0 ❌ |
| 4 | A3 drifts furthest from the small segment | ⛔ **NOT MEASURED** — I did not instrument held-name dollar-volume rank. A miss of execution, recorded as one |
| 5 | best-worst spread > 1.5%/yr | ❌ **MISS** (0.79%) |

**1.5 of 5.** The two clean misses are informative: I expected the trailing stop
to lose by *selling winners* (Bessembinder). It didn't — it lost by *paying the
spread*. The mechanism I imported from the literature was the wrong one, and the
cost model I already had was the right one.

**Brain's four (brief §5):**

| # | prediction | outcome |
|---|---|---|
| 1 | ≥2 flagged review numbers fail; Lazy Prices + 3S-Trader the casualties | ⚠️ **HALF** — count right (4 failed as *used*), both named casualties **verified as quoted** |
| 2 | DSR leaves the survivor below the bar; label stays factor-harvest | ✅ **HIT**, and understated |
| 3 | no exit arm beats baseline at paired t ≥ 2 ✅; **trailing-stop arms land NEGATIVE net** | ⚠️ **HALF** — first clause hit; A1 was **positive** on the panel (+0.34%) and only went negative (−3.08%) under **measured execution**, not for the predicted reason |
| 4 | ensemble within ±0.3%/yr of mean; dispersion reduced by >half | ✅ **HIT** (+0.04%); second clause is trivially true — an ensemble has no cross-date dispersion **by construction** |

---

## What this night changes

1. **The turnover gate is now calibrated, not cautionary.** Two independent
   measurements (NIGHT-6 clock, NIGHT-7 stop) put the monthly panel's
   understatement of churn cost at **≈2.4 pts/yr** for a ~0.8 turnover increment.
   Every high-turnover candidate in the graveyard was judged on that panel. This
   cuts **toward** the REJECTED column, and it means the resurrection queue should
   be re-read: high-turnover corpses are *more* dead, not less.
2. **The survivor's label is now bounded.** The historical record does not
   establish unique alpha once the search is counted; the excess Sharpe (0.449)
   sits essentially on the expected maximum of its own null (0.431). Any document
   implying more must be corrected — including the product note. This is *not*
   a proof the strategy is false, and DSR is not re-armed as a kill gate
   (GATE-M1 measured that gate as nearly powerless).
3. **Implementation is measurably worth more than selection.** Date luck
   (2.45 pt/yr range, removable free) and churn (2.4 pt/yr, avoidable) both exceed
   the entire measured spread across five exit rules (0.79 pt/yr) and the
   deflated residual of the entry signal itself. This is the craftsmanship-alpha
   thesis, arriving as our own measurement rather than as a citation.
4. **Two claims retired.** Maeso-Martellini's ">100bps rebalancing premium" is
   withdrawn (wrong benchmark). NIGHT-1's masking headline is amended (entity ≠
   date).

## What is still open

- **A3's segment drift** — registered, not measured. Cheap; do it first next time.
- **The 179-candidate resurrection queue** must be re-read under the calibrated
  turnover penalty. `conc_low` remains the only distinct candidate.
- **PRisk replication** — the first extractor validation, now unblocked and
  registered but unbuilt.
- **Product note** must be revised to lead with AVUV **and** to carry the DSR
  number. It currently implies more than T4 supports.
- **Path A / Path B** remains Murat's decision (see ROADMAP §12).
