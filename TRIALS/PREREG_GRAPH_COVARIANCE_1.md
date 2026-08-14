# PREREG — GRAPH-COVARIANCE-1 (does the semantic graph make a better risk model?)

**Drafted 2026-08-14, before any covariance matrix is built or graded.**
Descendant of MARKET-GRAPH-1 H1, which is the only hypothesis in GRAND-ARENA-1
to clear its own bar with placebos intact (ΔR² +0.000968 vs MDE 0.000623,
t = 4.35). That result is about **co-movement**, and the GRAND-ARENA-1 verdict
names the unasked follow-up in one sentence:

> *"It is a risk-model result, and the honest next question is whether a better
> covariance structure survives into portfolio outcomes — which this campaign
> has not tested."*

This trial asks exactly that question and nothing wider.

## The specific claim being tested

Commercial equity risk models (Barra, Axioma) estimate a factor block and then
assume the **specific (residual) returns are mutually uncorrelated** — the
specific block is diagonal. That assumption is known to be wrong and is
expensive to fix from prices alone, because the residual correlation matrix is
the noisiest part of the estimate.

MARKET-GRAPH-1 established that LLM-extracted economic relationships carry
information about **forward residual correlation** that the trailing residual
correlation does not already have. So:

> **H1 (risk-model value).** A residual-correlation block predicted with the
> semantic edge features produces a **lower realised out-of-sample variance**
> minimum-variance portfolio than the identical block predicted without them.

> **H2 (product survival).** The same improvement survives into a **long-only,
> position-capped, total-return** minimum-variance portfolio — the constrained
> object a product could actually hold.

Honest priors, stated before running: **H1 ~40/60 against; H2 ~15/85 against.**
The reason for the pessimism is stated in advance and is the reason for the
power gate below: semantic edges cover **0.58%** of pairs, and a minimum-variance
portfolio is a smooth functional of the whole matrix. It is entirely possible
that information which is real at the pair level is economically invisible at
the portfolio level. H2 is additionally penalised because a long-only constraint
truncates precisely the hedging positions through which a corrected correlation
would express itself.

## Why realised minimum-variance variance is the right metric

It is the standard loss function for covariance quality (Ledoit–Wolf's own
criterion; Engle–Colacito). It involves **no return forecast**, so nothing here
can be contaminated by a return signal: given any two covariance estimates, the
one that produces the lower realised variance in the holding window is the
better estimate of covariance, and no other property of the estimator matters.

It is also, unlike ΔR² on pairwise correlation, a **portfolio outcome** — the
thing the verdict says was never tested.

## Design

Everything numeric is inherited unchanged from MARKET-GRAPH-1 stage 1
(`runs/MARKET-GRAPH-1/pairs.parquet`, `universe.parquet`,
`edge_instances.parquet`): the same 38 quarterly cut dates 2015-03-31 →
2024-06-28, the same top-300-by-CRSP-market-cap universe, the same residual
definition (market and own-FF12-sector-excluding-self, betas fitted on the
trailing 252 days and **applied** to the forward 126), the same edge corpus.
**No new LLM call is made in this trial.** Extraction is already paid for; every
arm below is a refit and a matrix solve.

At each cut date *t*:

1. A residual-correlation matrix `P_arm` is predicted for every pair in that
   date's universe, by a **fixed-alpha ridge fitted walk-forward on strictly
   earlier cut dates only** — the identical estimator, feature blocks, and
   walk-forward protocol as MARKET-GRAPH-1 stage 5.
2. `P_arm` is repaired to a valid correlation matrix by the **identical**
   procedure in every arm (symmetrise, unit diagonal, eigenvalue clip at 1e-8,
   rescale to unit diagonal). The minimum eigenvalue before repair is recorded
   per arm as a diagnostic.
3. `Σ_res = D P_arm D`, where `D` = diag(trailing residual volatility) is
   **identical across all arms**. Only `P` varies. This is the whole point: the
   volatility block is a different problem and is held fixed so that the
   measured difference is attributable to correlation structure alone.
4. The minimum-variance weights are solved and **held unchanged** over
   `(t, t+h]`, h = 126 trading days. Realised variance is computed from the
   realised residual return series over that window.

### Arms

**Decision arms** (the comparison that decides H1 is a *paired difference*
between the first two):

| arm | residual correlation block |
|---|---|
| `model_numeric` | ridge on `[rho_trail, rho_trail², same_sector]` — the MARKET-GRAPH-1 baseline |
| `model_semantic` | the same ridge **plus** `[has_edge, log_n_edges, max_conf]` — the MARKET-GRAPH-1 H1 model |

**Placebo arms** (must be null; any that is not voids the adoption):

| arm | construction |
|---|---|
| `placebo_shuffled` | node-label permutation within each cut date — degree sequence and confidences preserved exactly (MG1 control 1) |
| `random_matched_density` | same edge count per date, drawn uniformly, confidences resampled (MG1 control 3) |
| `placebo_stratified` | edge labels permuted **within each (cut date × same-sector × rho_trail decile) cell** (MG1 §8B). This is the load-bearing placebo here: edge-carrying pairs sit at mean rho_trail 0.103 against 0.0003 overall, and high-correlation pairs are exactly the ones a minimum-variance solve weights most. |

**Context arms** (reported, never deciding — they say where the decision arms sit
against practice, not whether the graph works):

`diagonal` (the industry-standard assumption), `sample` (trailing residual
correlation as-is), `ledoit_wolf`, `rmt_denoised` (Marchenko–Pastur).

### The known nuisance channel, named in advance

The semantic feature block is standardised, so on a pair with **no** edge the
block still contributes a constant offset rather than zero. A constant added to
every off-diagonal entry does change a minimum-variance solution. That channel
has nothing to do with which companies are related, and it is exactly what the
three placebos reproduce — each of them carries the same standardised block with
the same coverage and the same constant offset, and differs only in *which*
pairs carry an edge. This is why a placebo that is not null voids the result
rather than merely weakening it.

## The power gate — pre-registered, and it runs FIRST

GRAND-ARENA-1's most expensive lesson was measured on the selection instrument:
the **perfect-foresight oracle itself came in at 0.64× its own MDE**, so every
null in that family was uninterpretable — there was nothing detectable to find
even with the answer key. That was discovered after the fact. Here it is
discovered before.

**`oracle_on_edges`**: take the `model_numeric` correlation matrix and overwrite
**exactly the edge-carrying entries** with the **true realised forward
correlation** for that pair over `(t, t+h]`. Nothing else changes. This is the
maximum benefit any edge-based correlation correction can deliver at this
coverage — no real predictor can beat it.

**The gate:** the oracle's realised-variance improvement over `model_numeric`
must itself exceed its own 80%-power MDE.

- **If the gate fails**, the trial terminates as `UNDERPOWERED_BY_CONSTRUCTION`.
  The real arms are still run and reported, but **no null from them may be
  recorded as a kill**, and MARKET-GRAPH-1 H1 is not weakened by this trial. The
  escalation path is pre-committed: more edges via `UNIVERSE_N` (MARKET-GRAPH-1
  §10 lever 1, which costs **no** new LLM spend because the extraction corpus
  already exists), as a **new** pre-registration with a new name.
- **If the gate passes**, the size of the oracle's improvement is the yardstick
  the real arm is read against, and a real null becomes informative.

## Primary metric and inference

**Primary statistic (H1):** the paired per-cut-date difference in realised
annualised volatility of the residual minimum-variance portfolio,

```
d_t = vol_realised( GMVP[model_numeric] )  -  vol_realised( GMVP[model_semantic] )
```

positive = the semantic block produced a lower-risk portfolio. Differenced
**within the cut date** before any SE is taken (§18) — never two separate
significance claims.

- n for the SE is the number of **graded cut dates**, not pairs or names. Both
  are printed (§19).
- Cut dates are one quarter apart while the holding window is two quarters, so
  consecutive windows overlap by half: **Newey–West SE at 2 lags**.
- `SE = max(HAC, IID)`, per NIGHT-11 — the ruler is the wider of the two.
- **MDE = 2.80 × SE** (80% power, 5% two-sided). Identical constant to
  `mg1_config.MDE_Z` and `arena_core.MDE_Z`; the ruler is not re-derived here.
- Inside the MDE is **not detectable** — not a kill, not a win (§19).

**Primary statistic (H2):** the same paired difference, computed on the
**long-only, fully-invested, position-capped total-return** minimum-variance
portfolio, where `Σ_total = Σ_fit + D P_arm D` and `Σ_fit` (the covariance of
the fitted market+sector component over the trailing window) is identical
across arms.

## Decision rule — frozen

**ADOPT into research use** only if **all** of:

1. the oracle gate passes;
2. `model_semantic − model_numeric` on the primary statistic **exceeds its own
   MDE with the sign that means lower realised risk**;
3. **all three** placebos are inside their own MDEs;
4. H2 holds — the improvement survives the long-only capped total-return
   portfolio.

Outcomes if it does not:

| condition | recorded verdict |
|---|---|
| gate fails | `UNDERPOWERED_BY_CONSTRUCTION` — escalate edge count under a new name |
| gate passes, (2) fails | `NOT_DETECTABLE` — an informative null, because the oracle said there was room |
| (2) passes, (3) fails | `PLACEBO_CONTAMINATED` — not adopted |
| (2) passes, (4) fails | `LONG_SHORT_ONLY` — recorded as a research result, **not** product value |

**Nothing in this trial may set a lane, a weight, or a position size.** No
certification is claimed; certification is forward-only (A7). This is a
historical, `ARCHITECTURE_RESULT_ONLY` measurement under the same terms as its
parent.

## Reported, never deciding

Risk-forecast calibration (realised ÷ predicted portfolio volatility — a matrix
that calls a single economic bet "diversified" prints > 1); realised maximum
drawdown of each portfolio; effective number of bets `1/Σw²`; top-eigenvalue
share of the realised forward correlation among held names; condition number and
pre-repair minimum eigenvalue of every matrix; turnover of the weights between
cut dates. These describe the arms. None of them can promote or demote a
verdict, because none of them was named as a decision number before the run.

## Frozen parameters

Enumerated in `scripts/gc1_config.py`, committed before any covariance matrix is
built or graded. Nothing in that file may change after the first grading run; if
something must change it is a **new trial with a new name**. Everything
inherited from `mg1_config.py` is inherited by reference and is not re-chosen
here.

## Hard constraints

- **No new LLM call.** The edge corpus is frozen at the MARKET-GRAPH-1 artifact.
  Re-extracting would make this a different trial.
- The forward window supplies **outcomes only**. The only place a forward
  quantity may be read is inside `oracle_on_edges`, which is a declared power
  probe and can never be adopted.
- Every arm shares the same `D`, the same PSD repair, the same solver, the same
  constraints. If an arm needs its own treatment, that is a finding to report,
  not a fix to apply.
- Backtests on our data are direction checks, never alpha claims. No skill claim
  before 24 months of forward record.

## Corpse check

Run before registration; verdict recorded in the trial doc.
