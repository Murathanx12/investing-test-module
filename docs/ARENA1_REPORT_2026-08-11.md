# ARENA-1 — 384 portfolios, frozen before scoring

**Manifest** `runs/ARENA1/ARENA_MANIFEST.json`, genome sha256 `f7f7e7ef7457be50`,
committed in `d0ab548` **before** any genome was scored.
**Window** 2002-01-31 .. 2022-12-31, 252 months. Holdout unread.
**Denominator: 384.** Every loser is preserved in `real_results.json`.

---

## The answer in one line

**Nothing graduates, and the reason is the useful part: a random-score control
genome ranked 4th out of 384.**

## What was actually asked

Murat: *"create hundreds of portfolios with its engine + LLM and do backtest
with real or made up data to test itself and learn to improve if its valid."*

Both halves were built. The real half searched 384 policies over 21 years of
point-in-time CRSP. The made-up half built 11 synthetic worlds where the answer
was planted, so the **search itself** could be scored rather than trusted.

The made-up half turned out to matter more, because it produced the number that
makes the real half readable.

## The false-discovery bar — the number this Arena exists to produce

| measurement | value |
|---|---|
| best of 384 genomes in a world where **nothing predicts anything** | **+4.77 %/yr** |
| best **random-score control** on the real panel | **+4.87 %/yr** |
| ⇒ false-discovery bar | **+4.87 %/yr excess CAGR** |

A maximum over 384 draws is a large number even when every draw is noise. Every
"best of N" this programme has previously reported was compared against this
quantity implicitly and without measuring it. It is now measured.

**Power curve** (`runs/ARENA1/power_curve.json`, 3 seeds per point). The
question is at what planted effect the best truth-carrying genome reliably
beats the best noise genome:

| planted decile spread | best truth | best noise | truth wins | truth share of top-10 |
|---:|---:|---:|---:|---:|
| +0 %/yr | +0.56 % | **+4.77 %** | 0 % | 0 % |
| +4 %/yr | +5.61 % | +3.69 % | 67 % | 53 % |
| **+8 %/yr** | +6.96 % | +3.70 % | **100 %** | 80 % |
| +16 %/yr | +9.70 % | +3.75 % | 100 % | 100 % |
| +32 %/yr | +15.66 % | +3.87 % | 100 % | 100 % |

**Detection threshold ≈ +8 %/yr decile spread.** Below that, an Arena ranking
is not evidence.

## The real result

384 genomes scored, 0 failures. 95 positive. The pre-declared selection rule
(net excess > 0, ≥ half the 3-year blocks positive, top-5-month share < 0.8,
turnover < 300 %/yr) leaves **66**. Of those 66, **2** clear the
false-discovery bar:

| genome | family | segment | k | weighting | reb | excess | t | blocks | turnover |
|---|---|---|---:|---|---:|---:|---:|---|---:|
| G0231 | profitability_small × low_volatility | small | 15 | fractional_kelly | 6 | **+5.06 %** | 1.19 | 6/7 | 1.23 |
| G0236 | profitability_small × low_volatility | largemid | 10 | inverse_vol | 12 | **+4.88 %** | 1.20 | 6/7 | 0.63 |

Both sit ~0.1–0.2 points above a bar built from noise, at t ≈ 1.2. Bonferroni
over 384 candidates gives **p_adj = 1.000**; the family-wise t required for
0.05 is **3.89**.

**Verdict: no genome graduates. ARENA-1 is a null.**

### The pre-registration earned its keep, visibly

The highest-excess genome in the whole pool is **G0245**
(`profitability_small × short_interest_level`, small, k=50, inverse-vol,
monthly) at **+6.06 %/yr, t 2.69, 7 of 7 regime blocks won** — the only genome
that beats the bar by a real margin and the only one with a t above 2.

It is **excluded**, because its turnover is **3.03** against a frozen gate of
3.00.

That is a 1 % overshoot on one axis disqualifying the best-looking result in
the search. Had the rule been written after the results, nobody would have set
the gate there. It was written before, so it stands. G0245 is recorded, not
promoted, and it is not a finding.

### What the top of the table actually looks like

```
G0245  profitability_small × short_interest_level   +6.06   (EXCLUDED: turnover 3.03)
G0231  profitability_small × low_volatility         +5.06
G0236  profitability_small × low_volatility         +4.88
G0004  control_equal_weight  <- RANDOM SCORE        +4.87
G0225  profitability_small × low_volatility         +4.71
G0229  profitability_small × low_volatility         +4.65
G0008  control_equal_weight  <- RANDOM SCORE        +4.55
G0052  solo_profitability_small                     +4.44
```

Two of the top eight are books that picked their names **at random**. Any
reading of this table that treats positions 2–8 as a discovery is reading
noise. The one durable pattern is compositional rather than about signals:
everything near the top is small-cap, low-turnover, and diversified across
regime blocks — which is what the taxonomy already said in 2026-07.

## The synthetic worlds, and a finding about the flywheel itself

11 worlds, each verified against a matched unplanted control before use
(`runs/ARENA1/synthetic_results.json`).

The `analyst_skill` world plants a genuine **+8 %/yr** analyst-revision effect —
above the detection threshold — and the Arena **did not find it**: best
truth-carrying genome ranked **33rd**, zero analyst genomes in the top 10.

That is not a power failure. It is the registry working exactly as designed and
producing a consequence worth stating plainly:

> **The Arena cannot discover a mechanism the registry has forbidden it to lead
> with.** `analyst_target_level_haircut` is graded RISK_INPUT, so the generator
> only ever places it at weight 0.2 beside a weight-1.0 picker. No analyst-led
> genome exists in the pool, so no analyst-led genome can win — even in a world
> where analyst revisions are the truth.

This is the price of letting research constrain the search, and it is mostly
the right price: it is what stops raw analyst upside, momentum and 13F
following from walking back in. But it makes the research → PM loop
**one-directional**. The search can confirm what the lab believes and can never
overturn it.

**Recommended (not implemented tonight):** every future Arena carries a small
`heresy` sleeve — genomes that lead with a CLOSED or RISK_INPUT-only mechanism,
tagged, excluded from all selection, and reported separately. They cannot
promote anything; they exist so that if a corpse ever starts winning, something
in the system notices. Registered as an open question, not built.

## What was corrected mid-run, and why it is not tuning

**Scoring pass 1 is VOID** (`real_results_VOID_pass1_bad_benchmark.json`).

It benchmarked against `ret.where(eligible).mean(axis=1)` — a monthly-rebalanced
equal-weight portfolio of every eligible name. That object earns **17.97 %/yr in
small and 25.69 %/yr in largemid**, against **7.71 %** and **7.97 %** for
buy-and-hold, because monthly-rebalancing 1,926 microcaps harvests bid-ask
bounce nobody can trade. All 384 genomes came out negative against it —
including the control, which is what exposed it.

The correction is justified by an argument that does not mention any genome's
rank (the benchmark was un-investable, and was not the one the adjudicator
uses), and the genome pool and selection rule were untouched. The manifest hash
is unchanged.

Also corrected: the control genome scored every name **0.5**, so `argpartition`
returned the same arbitrary prefix of the permno ordering every month — one
specific book sorted by permno, not a control. It now uses a deterministic
per-name pseudo-random score, which is what made "a random book ranks 4th"
measurable.

## Honest limits

* **This is a SCREEN, not a verdict.** No placebo band, no factor alpha, no
  multiple-testing deflation inside the evaluator, no market impact (G8), no
  delisting stub. Impact and delisting both **flatter** small-cap high-turnover
  genomes, which is precisely where the top of this table lives.
* **Synthetic performance is never evidence of alpha.** The synthetic sections
  above score the Arena, never a strategy.
* **6 permitted signals were excluded** for lack of a panel implementation, each
  with a printed reason in the manifest: catalyst proximity, LLM event
  extraction, options expectation, macro regime, crash composite, rating drift.
  The search covered what it could reach, and the manifest names what it could
  not.
* **In-sample.** Every genome saw all 252 months. That is what the forward
  shadow register is for.

## What happens next

1. **Nothing is promoted.** No lane, no flag, no capital.
2. The two rule-survivors and the excluded G0245 go to the **forward shadow
   register** — not as winners, but because forward outcomes are the only
   evidence in this system that nothing has already seen.
3. `+4.87 %/yr` is now the standing bar for any ARENA-2 claim.
4. The `heresy sleeve` question is registered.
