# PREREG — TRIAL-N1B-WHERE-DOES-THE-IC-LIVE-1 (REGISTERED, NOT RUN)

**Registered:** 2026-08-10 · **Family:** N (extension) · **Stage:** diagnostic
**Parent:** `TRIAL-N1-RANKER-VS-COMPOSITE-1` (IMPLEMENTATION_FAILED ×3; receipt
`runs/NIGHT8/N1_RANKER_VS_COMPOSITE.json`)

Resurrects: PREREG_N1_RANKER_VS_COMPOSITE — new instrument: decile-level IC
decomposition rather than a single full-cross-section statistic, which is the
only way to see whether an ordering advantage sits where a long-only book can
reach it.

## 1. What the parent established, and what it left open

Three learned rankers ordered the cross-section better than the hand-written
composite — ΔIC **+0.034 / +0.068 / +0.056** at paired t **4.18 / 4.09 / 3.46**
over 461 months — and none of them earned more. All three are
`IMPLEMENTATION_FAILED`.

**Turnover is ruled out as the explanation by measurement.** The best-ordering arm
(R2) had the *lowest* turnover in the table, 0.401 against the control's 0.460.

So the ordering advantage is real, it is large, it is not eaten by trading, and it
does not arrive in the book. **Where does it go?**

## 2. Hypothesis

**H1 (the §28 hypothesis).** Rank-IC is a full-cross-section statistic. The book
buys only the **top 150 names of the small segment**. This programme has already
measured, in §28, that 99.9%/88% of a long-short spread can live in the leg a
long-only book cannot hold. If the learned rankers' advantage is concentrated in
correctly identifying the *bottom* of the distribution — which is what a
tree ensemble trained on a symmetric loss should be good at — then a long-only
top-150 book is structurally unable to collect it.

**H2 (the compression hypothesis).** The advantage may be real at the top but
*compressed*: the learned rankers may order the top decile no better than the
composite does, spending their extra skill on distinctions among names nobody
holds.

**H0.** The advantage is present at the top and something else — liquidity,
size, or the eligibility mask — prevents its collection.

## 3. Design

Everything is a decomposition of series the parent already produced. No new
models are fitted and no new arms are created, so the ranker search is not
extended.

1. **IC by decile.** Recompute the monthly rank-IC restricted to each decile of
   each arm's own score. If the learned arms' advantage lives in deciles 8–10
   (the worst names), H1 is supported directly.
2. **Top-only IC.** Rank-IC computed among the top 150 names *each arm would
   actually hold*. This is the number that matters for a long-only book, and it
   is the one nobody has ever computed here.
3. **Hit rate on the left tail.** The share of each arm's bottom decile that goes
   on to a performance delisting or a bottom-quintile forward return. Bessembinder
   (`BESSEMBINDER-4PCT`) says the left tail is where a long-only book's realised
   return is decided; N2 separately found the composite already avoids the
   accruals/issuance/distress families at up to 15× better than chance.
4. **Overlap.** How many of the top 150 do the learned arms and the composite
   share? If overlap is high, the money difference is coming from a handful of
   names and is a small-sample story rather than a ranking story.

## 4. Decision rule (frozen)

| outcome | consequence |
|---|---|
| the ΔIC is concentrated in the bottom deciles **and** top-only IC is flat | **H1 supported.** The learned ranker's advantage is structurally uncollectable by this book. Record it and stop building long-only rankers on a symmetric loss. |
| top-only IC is materially better (paired t ≥ 2.0) while money is not | H0. Something between ordering and holding is losing it; register a construction trial, not a ranker trial. |
| top-only IC is flat and the bottom deciles are flat too | the parent's ΔIC is a middle-of-the-distribution artifact; report and close. |

**This diagnostic adopts nothing and may not adopt anything.** Its only outputs
are a supported hypothesis and, at most, a registered successor.

## 5. Registered predictions

1. **H1 is supported** — the advantage concentrates in the bottom deciles.
2. **Top-only IC is flat**, |t| < 2.0, between the learned arms and the composite.
3. **Overlap in the top 150 is above 50%**, so the two books are more alike where
   it counts than the full-cross-section ΔIC of 0.068 suggests.
4. If 1–3 hold, the honest consequence is that **a symmetric regression loss is
   the wrong objective for a long-only book** — which would be the first
   actionable design conclusion the ML track here has produced, and would be a
   registered successor rather than an adoption.

## 6. Ledger

Adds **0 branches** — this decomposes series the parent already produced and
fits no new model. Any successor it motivates registers its own.

---

# AMENDMENT 1 — 2026-08-10 (NIGHT-9), before any N1B compute

An external review of NIGHT-8 identified a confound the original design cannot
see, and it is a good one. Registered here before the diagnostic runs.

## A1.1 The clock/objective mismatch

**Rank-IC was measured in every one of 450 months. The book acts once every
twelve.** The parent therefore compared an all-month statistical objective
against a once-a-year economic action. A model that ranks better in the eleven
months when the portfolio *cannot trade*, and no better on the dates it *can*,
would produce exactly the parent's result — ΔIC ≈ +0.07 at t ≈ 4 with no money —
and the original N1B design would never have found it, because every one of its
four decompositions is computed on all months.

This is now the **first** axis, ahead of the rank axis, because if it explains
the result then the §28 hypothesis is not needed at all.

## A1.2 The frozen-prediction problem, stated plainly

**The parent did not persist its score frames.** `scripts/n1_ranker_vs_composite.py`
holds them in memory and writes only the summary JSON. N1B therefore cannot
"decompose series that already exist" as its section 3 claims: step 0 is a
re-fit.

That re-fit is **not a new search branch**. It re-runs the parent's exact code
path, seed (`20260810`), parameters and arm order, and persists the four score
frames. It is admissible only if it **reproduces the parent's published
statistics**, so the reproduction is a gate, not a formality:

| quantity | source of truth | tolerance |
|---|---|---|
| mean rank-IC per arm | `runs/NIGHT8/N1_RANKER_VS_COMPOSITE.json` | 1e-4 |
| paired ΔIC mean and NW t | same | 1e-3 on the mean, 0.05 on t |
| paired money mean and NW t | same | 1e-4 on the mean, 0.05 on t |
| annual turnover per arm | same | 1e-3 |

**If it does not reproduce, N1B stops and reports a determinism failure.** A
factory that cannot reproduce its own published number by re-running its own
script has a worse problem than the one N1B was written to answer.

## A1.3 The six decompositions, frozen

Everything below is computed from the frozen score frames. **No model is fitted
inside N1B**, no new arm exists, and no threshold below adopts anything.

1. **`clock`** — ΔIC on the book's actual rebalance months versus all other
   months. Paired, NW(12), MDE reported for both subsamples.
2. **`rank`** — ΔIC and mean forward return restricted to each decile of the
   arm's own score. The original H1 test.
3. **`boundary`** — the same restricted to ranks **100–250** of the eligible
   set. The book holds the top 150; this is the only band where a ranking error
   changes what is held. A model can be globally better and locally worse.
4. **`topk`** — mean forward 12m demeaned return of the top **K = 25, 50, 100,
   150, 300** names by each arm's score, on rebalance months only.
5. **`membership`** — on actual rebalance dates, partition each arm's top 150
   against the baseline's: `common`, `baseline_only` (dropped), `model_only`
   (added). Report the **replacement loss**

   > `E[r(baseline_only)] − E[r(model_only)]`

   with a paired t over rebalance dates. **This is the sharpest single number in
   the diagnostic**: if it is strongly positive while global ΔIC is strongly
   positive, the model is more right about the cross-section and more wrong at
   the economic selection boundary, and that — not the bottom decile — is where
   the money went.
6. **`phase`** — decompositions 4 and 5 repeated for each of the twelve annual
   rebalance phases. The shipping vehicle is a twelve-sleeve ensemble; a story
   that holds in one phase and not the others is a date-luck story (2.45 pt/yr,
   NIGHT-7).

## A1.4 Pre-compute power, written down before the split

The clock axis splits 450 months into ~38 rebalance months and ~412 others, so
its MDE is **√12 ≈ 3.46×** the full-sample MDE. From the parent receipt
(monthly units — the parent's `mde_annualized` field multiplies an **IC**
difference by 12, which is meaningless for a correlation and is being fixed
separately tonight):

| arm | full-sample monthly MDE | ×3.46 = rebalance-month MDE | observed monthly ΔIC | powered? |
|---|---|---|---|---|
| R1 gbm narrow | 0.0066 | **0.0228** | 0.0340 | yes, by 1.5× |
| R2 gbm wide | 0.0123 | **0.0427** | 0.0675 | yes, by 1.6× |
| R3 mlp wide | 0.0119 | **0.0412** | 0.0556 | yes, by 1.3× |

So the clock axis **can** see an effect of the size the parent measured, if it
is there. It cannot see one half that size. That is stated now so it cannot be
discovered later.

The `membership` axis has ~38 paired observations and is the weakest; its MDE is
reported and a null there is `POWER_FAILED`, never "no difference".

## A1.5 Decision rule, amended (frozen)

| outcome | consequence |
|---|---|
| ΔIC on rebalance months is at or below its MDE while off-clock ΔIC is large | **clock mismatch.** The parent's ordering advantage is real and is measured on dates the book cannot act. The licensed successor is a *delivery* trial (N1C: frozen ranker × twelve-sleeve delivery), not a loss-function trial. |
| ΔIC survives on rebalance months **and** concentrates in deciles 8–10 with flat top-150 IC | **H1 supported** — structurally uncollectable long-only; a symmetric loss is the wrong objective. |
| ΔIC survives on rebalance months, top-150 IC is flat, and `replacement loss` is strongly positive | **boundary failure** — the model is worse exactly where selection happens. Register a construction trial. |
| none of the above separates | report the decomposition and close; the parent's ΔIC is a middle-of-distribution artifact. |

**No branch of this table adopts anything or changes a weight.**

## A1.6 Registered predictions (amendment)

Scored alongside the original three.

4. **The clock is NOT the explanation** — ΔIC on rebalance months will be within
   1 standard error of ΔIC off-clock. I am registering against the reviewer's
   hypothesis, because the features are slow-moving annual accounting ranks and
   there is no mechanism I can name that would make July special.
5. **Replacement loss is positive** — the names the learned rankers add
   underperform the names they drop, on rebalance dates.
6. **The phase axis will show a wide spread** (range ≥ 2 pt/yr across the twelve
   phases in top-150 forward return), consistent with NIGHT-7's date-luck range,
   and no phase will reverse the sign of the money result.

## A1.7 Ledger

Still **0 new branches**: no model is fitted, no arm is added, and the re-fit in
step 0 must reproduce the parent exactly or the trial voids. The six
decompositions are one pre-registered diagnostic reported together, not six
chances to find a story — and the write-up reports every axis, including the
ones that separate nothing.

---

# AMENDMENT 2 — 2026-08-10, after axes 1-5, BEFORE the axis it registers

## A2.1 What the first five axes did to the hypothesis

Every rank-based axis says the learned rankers are better, and the book says
they earn less. Specifically: the advantage survives on the book's own
rebalance months (so it is not a clock artifact), it is LARGER in the top decile
than the bottom (so it is not the §28 hypothesis), it is large in the
selection boundary band, the top-K forward label beats the control at **every**
K from 25 to 300, and the names the learned rankers **add** beat the names they
**drop** by 3.3 to 5.9 points of forward label.

There is no longer a "where does it go" answer available. Both instruments are
measuring the same names and disagreeing about them.

## A2.2 The remaining explanation, and it is about the instrument

**The label is a demeaned LOG return. A long-only equal-weight book is paid in
SIMPLE returns.** Those two are not the same objective, and the gap between them
is exactly a variance penalty: a name with an even chance of tripling or losing
80% has an expected simple return of +60% and an expected log return of −25%.
Ranking on mean log return therefore systematically DE-selects positively skewed
names — and in a small-cap universe those are the names whose right tail pays
for everything else (Bessembinder).

If that is what is happening, then **the ordering instrument this programme has
been using is misspecified for the book it is being used to judge**, and
NIGHT-8's ΔIC of +0.068 at t 4.09 was rewarding precisely the behaviour that
lost money.

## A2.3 The test, registered before it is computed

Recompute two axes with the label changed from demeaned log forward return to
**demeaned simple forward return**, everything else identical — same frozen
scores, same months, same eligibility, same top-150 sets. No model is refitted.

1. `ic_simple` — monthly rank-IC and paired ΔIC against the simple-return label.
2. `topk_simple` — the same top-K sweep against the simple-return label.
3. `skew` — the mean forward SKEWNESS of the names each arm holds, as the
   mechanism check. If the mechanism is right, the composite's top-150 must be
   more positively skewed than the learned rankers'.

## A2.4 Registered predictions

7. **ΔIC shrinks by at least half** under the simple-return label.
8. **The top-150 delta turns negative** — the learned rankers' top-150 earns a
   LOWER mean simple return than the composite's, reconciling with the money.
9. **The composite's holdings are more positively skewed.**

If 7 and 8 both hold, the conclusion is not "learning failed". It is **"we were
grading on the wrong exam"**, and the licensed successor is a relabelling trial,
not a new model class.

If they do not hold, the money/ordering contradiction is unexplained and stays
that way in the write-up. An unexplained contradiction is a legitimate ending.

## A2.5 Ledger

Still **0 new branches**: no model is fitted, no arm added, no threshold tuned.
Two decompositions of the same frozen predictions under a different label.
