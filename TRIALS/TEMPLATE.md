# TRIAL-<NAME>

**Registered:** <UTC timestamp — BEFORE any return is computed>
**Registry row:** appended to `TRIALS/registry.jsonl` via `register_trial()`

## Hypothesis
<One paragraph. The economic mechanism, not the pattern. Why should this edge
exist, who is on the other side of the trade, and why can't Citadel take it?>

## Literature prior
<What the published record says, including the decay story.>

## Expected effect size
<Honest number with units, e.g. "40–80 bps/mo gross in the microcap decile".>

## R13 — resolvability, declared BEFORE compute (required; `lint_prereg` refuses without it)
<Derive `declared_effect_size` from ECONOMICS — turnover, cost, capacity,
expected frequency, drawdown consequence, probability of ruin — and then ask
whether the corpus can resolve it. Never the other way round: choosing 10pp
because 25 episodes can see 10pp is the same error inverted.>

- event_frequency_per_year: <INDEPENDENT episodes of the conditioning state per
  year, not days. Crisis regimes ~0.7/yr; insider filings ~440,000/yr.>
- declared_effect_size: <e.g. 10pp — the smallest effect that would change a
  portfolio decision, with the economic argument above it>
- outcome_dispersion: <sd of the outcome in that state: a number in pp, or one
  of the measured presets `crisis` (17.7pp), `calm` (1.5pp), `single_name` (12pp)>
- corpus_years: <optional; defaults to 36, the N2 twelve-market span>
- outcome_horizon_days: <optional but strongly advised; turns on R13b's cap at
  252/H non-overlapping windows per year. Omitting it means n_available assumes
  every episode is independent.>
- dependence_unit: <one sentence naming what ONE independent observation is.
  Required below 20x headroom. "one non-overlapping 6-month block spanning the
  entire cross-section" is a declaration; "n/a" is not.>
- cross_sectional_k / cross_sectional_rho: <R13d. k co-moving series and their
  MEASURED average pairwise outcome correlation. Together they MULTIPLY the
  temporal count by k/(1+(k-1)rho), which is bounded by 1/rho -- eight equity
  ETFs at rho=0.488 are worth 1.81 series, however many more you add. Declaring
  k without rho is refused: the width is measurable on a policy-free surrogate
  before the test, so it is not something to assume. Use the older
  `cross_sectional_n` DIVISOR form instead only when your frequency already
  counts every series; declaring both is refused.>

## Slice claim (required; `lint_prereg` refuses without it)
<Which data does this trial claim, and for what? The register can only refuse a
trial that calls it, and the trial that will not call it is the one that needs
refusing. EXPLORE is a perfectly good answer and it costs the confirmation
claim, which is the point of saying it out loud before the numbers exist.>

- slice_purpose: <EXPLORE / TRANSFER / FOREIGN / CONFIRM / REANALYSIS / PAIRED>
- slice_securities: <CONFIRM only — the exact universe>
- slice_period: <CONFIRM only — start .. end>
- information_cutoff: <CONFIRM only. Required SEPARATELY from the period: two
  trials can share a price window and differ in what they were allowed to know
  inside it.>

## Calendar disjointness — R13e (required for CONFIRM / TRANSFER / FOREIGN)
<The paragraph that used to sit here asked you to "say so and expect to be
asked why". Nobody asks a paragraph. N9 confirmed on six securities in no prior
slice over a calendar that overlapped its own selection window: lift 1.464
(p=0.010) on the overlapping half, 0.765 (p=0.771) on the disjoint half, both
horizons. Holding out securities is not holding out data when the securities
co-move — so the coordinate is a field now, and `lint_prereg` refuses on it.>

- selection_period: <The window the thing being tested was CHOSEN, fitted or
  tuned on — INCLUDING the window a parent was selected on, since a descendant
  inherits it. `YYYY-MM-DD .. YYYY-MM-DD`, or `NONE` if the rule came from
  theory or literature rather than from a window of this corpus. `NONE` is a
  claim on the record, not a way past the field.>
- parent_trial: <The trial whose data selected this, or NONE. Declaring a
  parent AND `selection_period: NONE` is refused as a contradiction.>

## Provenance — R13f (required for CONFIRM / TRANSFER)

<Three different things a prior trial can be to this one, and one field for each
because collapsing them loses the distinction that matters. **The test is
selection, not citation.**>

- benchmark_source: <A trial supplying a number this one divides by or compares
  against, which chose nothing about the design. Its calendar is NOT spent. If
  a citation spent a calendar, no trial could ever quote a prior measurement.>
- parent_trial: <declared above — what was FITTED. R13e refuses an overlapping
  confirmation outright.>
- hypothesis_source: <The trial whose OUTCOMES are the reason this hypothesis,
  target, threshold or architecture exists at all, or NONE. It may have selected
  nothing and still have read these dates.>
- hypothesis_source_period: <The window that source read. Required whenever a
  source is named.>

<If the source's window overlaps this slice, the verdict is
`ADAPTIVE_HISTORICAL_VALIDATION`. That is **not a refusal** — the trial runs. It
is a ceiling on what may be written: validation on dates already seen by the
work that raised the question, never independent confirmation. Only a genuinely
untouched security/time/forward route upgrades it. IV-ORACLE-GAP-1's Phase B is
the case that produced this rule: `parent_trial = NONE` was true, WM0 fitted
nothing there — and WM0 read the whole panel end to end, which is why the
question exists.>

<The calendar gate then requires a gap, not merely zero overlap: labels run forward, so
the last rows of the selection window carry outcomes formed inside whatever
follows it. 7/5 x horizon + 14 calendar days — 1.5x was MEASURED failing on
15.7% of 20-bar boundaries against the real NYSE calendar. Clearing this lint
does not replace the purge `research_gym.lineage` derives from the index at run
time; it is the cheap check that runs before the compute, not instead of it.>

## Null specification (required whenever a p-value comes from a placebo)
<Which properties of the real treatment does your null hold fixed? Name them:
frequency, turnover, run_lengths, clustering, seasonality,
cross_sectional_sync. `research_gym.null_invariance` measures them and refuses
to produce a p-value from an ensemble that violates its own declaration. A
path-dependent outcome (drawdown, terminal growth) is moved by the ARRANGEMENT
of exposure and forces clustering and run lengths; a mean forward return is a
sum and does not. N21's matched-exposure placebo scattered its windows
uniformly, produced p=0.031, and the clustering-preserving null gave p=0.338.>

## Expected decay / capacity
<Horizon over which it should fade; rough $ capacity.>

## Kill condition
<Pre-committed: what result kills this line of inquiry. e.g. "net t-stat < 1
over the walk-forward window" or "edge only present in full universe but not
largest-500 (survivorship artifact)".>

## Two-arm design
- Arm A (expected LOSS): <the control that validates the pipeline>
- Arm B (the claim): <the actual hypothesis>

## Run spec (frozen before execution)
- Panel window, universe filters, cost bps, ranker kind, config — exact values.
- ONE run. The result is final for this trial.

## Result (filled in AFTER the run — never edited afterwards)
- Gate report (DSR at cumulative n, PBO, survivorship bound):
- Verdict: ADOPT-CANDIDATE / REJECT
- If REJECT: one-paragraph negative result → mirror to main repo NEGATIVE_RESULTS.md
