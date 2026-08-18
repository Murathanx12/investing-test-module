# PREREG — AEGIS-NET-TOURNAMENT-1: does any model family beat a linear one on labels the sign-based corpses never tested?

**DRAFT FOR SIGNATURE — UNSIGNED. Drafted 2026-08-18 (Order 18 §3.4), before
any model in this tournament has been fitted and before any fold has been
scored.** Registration is the signature; until then no arm may be run.

**Family:** model-class tournament with feature-family ablation.
**Grade:** `ARCHITECTURE_RESULT_ONLY` on the historical panel. **ACCRUES ZERO
ARMS.** Nothing here promotes a model into a lane; a winner earns a forward
registration and nothing else.
**Dataset:** `backend/services/net_dataset.py` (built 2026-08-18, `8624ea3`).

---

## 0. Corpse check — the corpse is named, and so is the instrument

`python scripts/lint_prereg.py TRIALS/PREREG_AEGIS_NET_TOURNAMENT_1.md`

**Resurrects: G5 — "a learned conditional *shape* adds nothing even given an
oracle scale" (THREE RECEIPTS, ALL NEGATIVE).** New instrument: **the OUTCOME,
not the model.** All three G5 receipts, and the return-model work before them,
graded a learned function against a **directional / sign** target, where this
engine measures AUC 0.497–0.509 — a target with no measurable signal in it at
all. A tournament over model families on that target cannot come back positive
and would not deserve to. This trial replaces the target: the heads are
**cross-sectional rank, quantile bucket, magnitude exceedance, forward max
drawdown, and competing barriers**, none of which reduce to sign, and each of
which has a base rate this panel can actually resolve.

**This must be stated plainly because it is the whole justification: if the
tournament is run on a sign target it is G5 for a fourth time, and the answer
is already known.** The distinct claim is *"a richer model beats a linear one
on a NON-DIRECTIONAL forward label"*, and that claim has never been tested here.

**Standing (§59, and it caps what a win can say):** headroom in this programme
has been located in **scale, not shape**. So the honest prior on H1 is **LOW**,
and a null is the expected result rather than a disappointment.

---

## 1. The four outcomes, written before the data

Fixed here so the wording cannot be negotiated afterwards:

- **A non-linear family beats linear on the primary head, surviving the
  ablation and the shared-resample test** → we have a shape effect on a
  non-directional label, and it earns a FORWARD registration. Not a lane.
- **All families ≈ linear** → **the shape is linear; spend the next dollar on
  scale, coverage and cost, not on architecture.** Those words, verbatim.
- **All families ≈ the label's base rate** → the labels carry no learnable
  structure at this sample size, which is a statement about the *panel*, and
  the MDE says whether it is also a statement about the world (§19).
- **A family wins on ONE head only** → **that is a success, not a
  consolation.** It says which question this data can answer, and the other
  heads are then not "failures" but out-of-scope.

---

## 2. Hypotheses

**H1 (primary).** On the primary head, the best non-linear family's
out-of-fold score exceeds the regularised-linear baseline's by more than the
MDE of the paired per-date-block difference.

**H2 (ablation).** The winning family's margin over linear survives removal of
each feature family in turn. A margin that exists only with one family present
is a claim about that family, not about the model class, and is reported as
such.

**H3 (capacity).** Deeper networks (NN2, NN3) do not beat NN1 by more than the
MDE. *Directional prior: they do not.* On `n_effective` measured in DATE
BLOCKS, this panel does not have the sample to support capacity, and H3 exists
so that a deep model winning is recognised as surprising rather than expected.

---

## 3. The arms

Five model families, **identical data, folds, costs, labels, and resamples**:

| arm | model | notes |
|---|---|---|
| `LINEAR` | ridge / elastic-net, tuned inside each training fold only | THE BASELINE. Every claim is relative to it. |
| `LGBM` | LightGBM, NaN handled natively (never `fillna(0)`) | the incumbent tabular method |
| `NN1` | 1 hidden layer | |
| `NN2` | 2 hidden layers | |
| `NN3` | 3 hidden layers | |

**NO SECURITY-ID EMBEDDING IN ANY ARM.** A per-ticker embedding lets a network
memorise which names did well in the training window, which is survivorship
learned rather than inherited, and it would show up as a better score rather
than as an error. This is a **hard constraint**, not a hyperparameter.

**Feature families** (ablated one at a time in H2): price/technical ·
fundamental · macro/regime · options-implied · cross-sectional/relative ·
liquidity/microstructure. Family membership is frozen at registration.

---

## 4. Primary metric — the ONE deciding number

**Out-of-fold Spearman rank correlation between prediction and the
`cs_rank` head, averaged over date blocks, differenced against `LINEAR` on the
SAME resamples, with a block-bootstrap SE.**

Everything else — AUC, Brier on the barrier heads, drawdown-head MAE, per-head
tables — is **reported, never deciding**.

Reasons this head and not another:
- It is **cross-sectional**, so §58 applies in the direction that helps: a
  relative claim costs far less calendar than a market-level directional one.
- It is **not sign**, so it is not G5's target.
- It is **scale-free**, so the two thresholds problem that forced per-cell MDEs
  in IIF-1 does not arise here.

---

## 5. Decision rule

- **Adopt (forward registration, NOT a lane):** paired difference vs `LINEAR`
  positive, exceeding its own 80%-power MDE, surviving Holm-FWER at the
  DECLARED export budget (§63), and surviving every H2 ablation.
- **Reject:** paired difference at or below zero, OR inside the MDE with the
  MDE below the smallest difference that would matter (declared in §6).
- **NOT ESTABLISHED:** inside the MDE with the MDE ABOVE the smallest
  meaningful difference. Underpowered is not a kill (§19). This verdict must be
  reachable, and §7 asserts it is.
- **Minimum window:** the full frozen panel; no early stop, no peeking per
  fold.
- **Earliest decision date:** at completion of the pre-declared fold schedule.
  There is no interim read, because there is no cost to waiting — the panel is
  historical and complete.
- **Contamination clause:** any data defect found mid-run voids the affected
  folds and is reported with a count; folds are never silently dropped.

## 6. The smallest difference that would matter — DECLARED HERE, NOT AFTER

**Δρ ≥ 0.010** in mean per-date-block Spearman over `LINEAR`.

Declared before any fold is scored, for the IIF-1 reason: a bar chosen after
seeing the MDE makes "meaningful" true exactly when the instrument happens to
detect something. If the measured MDE turns out to exceed 0.010, the trial
returns NOT ESTABLISHED and says so at registration time rather than arguing
about it afterwards. **§64 requires this power check to run BEFORE the first
fit; it consumes no outcome and is therefore obligatory.**

## 6b. R13 — resolvability, declared BEFORE compute

The economics first, because deriving the effect size from what the corpus can
see is the same error inverted. A Δρ of 0.010 in mean per-block cross-sectional
rank correlation is roughly the smallest improvement that survives contact with
this programme's own cost model: at the turnover a rank signal implies and the
`COST_BPS_ONE_WAY` rates the Order 18 ruling permits, anything smaller is
inside the cost band and therefore `COST_MODEL_SENSITIVE` before it is
anything else. A model that cannot be told from linear net of costs is not a
model this programme would deploy, whatever it does gross.

- **event_frequency_per_year: 12.6** — non-overlapping 20-trading-day blocks
  (252/20). This counts BLOCKS, not rows and not name-dates: the primary metric
  is already a cross-sectional statistic, so the cross-section is consumed
  INSIDE one observation. Declaring `cross_sectional_k` on top would multiply a
  count that has already spent its cross-section, which is why neither it nor
  `cross_sectional_n` is declared here.
- **declared_effect_size: 1.0pp** — Δ Spearman = 0.010 over `LINEAR`, per §6.
- **outcome_dispersion: 5.0pp** — declared SD of the PAIRED per-block Δρ. Paired
  and not marginal: the arms see identical data and folds and are strongly
  correlated, so the marginal SD of a single arm's ρ (~8pp at 150 names) badly
  overstates the dispersion of their difference. This is a DECLARED value; it
  is re-measured on a policy-free surrogate before the first fit, and if the
  measurement comes in HIGHER the required sample grows and §5's NOT
  ESTABLISHED verdict is the honest outcome.
- **outcome_horizon_days: 20** — every head shares ONE forward window
  (`net_dataset.label_row`), so the blocks are non-overlapping by construction
  rather than by intention.
- **dependence_unit:** one non-overlapping 20-trading-day block spanning the
  entire cross-section. Two names on the same date are ONE observation, because
  they share a market and their residual correlation is what §58 prices.
- **corpus_years:** the frozen historical panel's span, stated at registration.

**What this arithmetic implies, and it is the reason to declare it now:** at
1.0pp against 5.0pp dispersion, 80% power at α 0.05 needs ≈ **196 blocks ≈ 15.6
years** of non-overlapping 20-day windows. That is consistent with this
programme's standing finding that every library effect needs 14+ years, and it
means **the panel must span at least ~16 years or this trial returns NOT
ESTABLISHED by construction.** If the frozen panel is shorter, that is known
before a single model is fitted rather than months later dressed as a null.

## 7. Frozen parameters — none of these may move mid-trial

- Purged, embargoed walk-forward splits. **Never random k-fold.**
- `n_effective` counts **DATE BLOCKS, never rows.** A million rows on 500 dates
  is 500.
- **Shared resamples across every arm.** Unpaired draws measured ρ̄ 0.002 and
  k_eff 15.54 across 16 cells; shared, ρ̄ 0.920 and k_eff 1.08 — it was
  measuring the RNG. `k_eff` is PRINTED beside every comparison.
- **Barrier and path heads are evaluated ON the forward horizon only.** §65 is
  enforced as a type: `PathStatistic.scale_to()` raises.
- Costs: **`COST_BPS_ONE_WAY`**, the Order 18 §1 convention. Names whose
  verdict flips inside the declared liquid band are `COST_MODEL_SENSITIVE` and
  are **excluded from training**, never guessed.
- Seeds fixed; **reproducibility is a property of the PREDICTIONS**, and is
  asserted on them, not on the metric. (LightGBM's seed did nothing once —
  the drift was multithreaded histogram summation.)
- §37 applies to the winner: **a new instrument's first POSITIVE is the one
  that looks like it working.** The winner is re-run on a foreign slice with
  its own selection barred before anything is written down as a result.

## 7b. Slice claim

- **slice_purpose: EXPLORE**

EXPLORE and not CONFIRM, deliberately. This trial SELECTS among five model
families; a selection cannot also be its own confirmation, and calling it
CONFIRM would buy a stronger verdict with the same data. The confirmation is a
separate forward registration on a slice this trial never read.

**Claims:** the frozen historical US equity panel — universe × period × outcome
× cutoff as pinned by `net_dataset` at registration — for MODEL-CLASS
COMPARISON ONLY. It claims that slice as a `parent_trial`: the tournament
CHOOSES among model families using it, so it spends that calendar (§61 — the
test is SELECTION, and selecting is what this does).

**Does not claim:** any forward slice. A winner earns a FORWARD registration on
a slice this trial has not touched, with its own budget, and §37 requires it to
be re-run on a foreign slice with its own selection barred before the win is
written down. **The historical result caps at
`ARCHITECTURE_RESULT_ONLY`** and can certify nothing.

**Does not claim:** IIF-1's nights, the campaign forward ledger, or any lane.

## 8. What this trial may NOT do

- May not seed, promote, or influence any lane.
- May not produce buy/sell language anywhere it surfaces. Until it passes
  forward, any output ships as **labeled descriptive context** only.
- May not claim alpha from the historical panel. Survivor-affected historical
  fits are **direction-checks, never alpha evidence** (T7); selection claims
  validate FORWARD.
- May not report a per-head winner without its MDE beside it.
- May not substitute the primary metric, reweight the heads, or add an arm
  after the first fold is scored. Any of those invalidates the trial and
  requires a successor registration.
- May not annualise anything computed on the frozen window.

---

## Signature

Registered by: ............................................  Date: ..............
             Murat Abdullaev

*Registration commits §4's primary metric, §5's thresholds, §6's Δρ = 0.010,
and §7's frozen parameters. The git commit timestamp of this file is the
tamper evidence.*
