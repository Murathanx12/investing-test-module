# NIGHT-8 — the extension list, executed

**Date:** 2026-08-10 (Murat away) · **Branch:** `main` · **Data grade:** `crsp`
**Receipts:** `runs/NIGHT8/` · **Manifest:** `docs/manifests/NIGHT8_MANIFEST.json`
**Standing:** pre-register before compute · power check may refuse · placebo gate
on control-armed designs · G7 for turnover-sensitive claims · holdout locked ·
no lane writes · an unresolved ending is a valid one.

---

## 0. The headline

**Three of tonight's five findings are about instruments, not about markets —
and two of them retract claims this programme has already published.**

That is not a disappointing night. NIGHT-7's own lesson was that the errors live
in the measuring apparatus and the write-up, not in the arithmetic; tonight the
apparatus was pointed at itself and it found things.

| # | finding | consequence |
|---|---|---|
| 1 | **The clock ensemble is NOT cheaper.** Normalised by average NAV it is *worse* at $1m and indistinguishable at $50m | retracts NIGHT-7B; CANON §16 |
| 2 | **G7 cannot price impact.** Cost per dollar traded is identical across a 1,000,000× range of liquidity | every capacity number this programme has quoted is a delay-only **lower bound**; CAPACITY-EDGE-1 blocked as scoped |
| 3 | the corpse check, the claim checker and the verdict referee all **failed their own calibration first** | each is now measured, and each ships with its error rate |

---

## 1. A0 — the amendments that had to land before any compute

Registered predictions in both preregs are unchanged. What changed is reasoning,
labels, and details that were still choosable — which is the only kind of change
a preregistration may take after the fact.

**T4b (selection bootstrap).** Prediction 2's *rationale* was backwards:
positive correlation among null candidates makes their maximum **less** extreme,
so a fixed winner looks **more** exceptional, not less. Three competing forces
are now tabulated instead of one wrong one. A White p-value is not numerically
comparable to a DSR number and the write-up may not phrase it as such. The trial
is renamed a **fixed-alternative search-burden audit (a lower bound)**, because
Aegis ran an *adaptive* search whose later branches depended on earlier outcomes
and a bootstrap over recovered finished series cannot reproduce that.
Implementation frozen: B=5,000, seed, Politis–Romano stationary bootstrap with a
shared block index, Monte-Carlo uncertainty on p, masked (never zero-filled)
missing history, and real Hansen studentisation or it ships labelled White only.
A `coverage_matrix.json` is written and read **before** the bootstrap runs.

**Trigger penalty.** A pass is now `DELIVERY_PASS`, not `CONFIRMED` — the prereg
already said the same history is reused, and the two sentences could not both
stand. The rule is directional: a large negative is `REJECTED`/harmful, not a
"same sign" pass. **"Zero incremental turnover" and "the vehicle is free" are
withdrawn** — the prereg contradicted itself, predicting in §5 the turnover rise
that §2 denied. The turnover escape hatch is removed and every arm goes through
G7. `TRIAL-PF8-TRIGGER-CONFOUND-1` registered: momentum was one confound, not
the only one, and the **path-geometry placebo** is the sharp test — among names
matched on trailing return *and* volatility, does actually breaching 20% below a
running peak still forecast worse outcomes than reaching the same endpoint
without breaching?

---

## 2. T1c — the ensemble cost claim, retracted

The reviewer flagged that $1,316,887 is not 50× $19,390. Checking that was right;
the $50m rung had been independently re-simulated (cost 36.5 → 39.0 bps; turnover
only 47.7× for 50× capital, because it could not fill). But checking it surfaced
something worse in my own claim.

**Both arms start at the same NAV and end at different ones.** The single clock
compounds at 13.45%/yr against the ensemble's 12.90%, so it trades more dollars
for the same turnover *rate* — and totalling cost in **dollars** silently rewards
the arm that made less money. The monthly panel says the two turn over at 0.468
and 0.468. Equal rates and unequal dollar totals is the tell.

| night | instrument | verdict |
|---|---|---|
| NIGHT-7 | monthly-panel turnover rate | "free" — violated CANON §15 |
| NIGHT-7B | total cost **dollars** | "cheaper by $19,390" |
| **NIGHT-8** | **cost drag / (average NAV × years)** | **indistinguishable** |

Normalised, at $1m the ensemble is **3.54 bps/traded and 0.011 pt/yr worse**; at
$50m the drag difference is 0.0016 pt/yr, which is 16 basis points of a
percentage point and noise. **The case for the clock ensemble rests entirely on
removing the 2.45 pt/yr date-luck range. It does not rest on cost, and the two
previous nights said otherwise.**

Written into **CANON §16**, with two corollaries the same run produced: capital
rungs are re-simulated and never scaled, and counters summed across sleeves
(`days_with_capped_orders`) are not comparable to a single book's.

---

## 3. N7 — the capacity instrument, calibrated

G7 was about to be asked whether the book has a capacity limit below AVUV's
floor. Nobody had asked whether it can tell a capacity effect from nothing.
Three synthetic worlds with known answers, through the real `simulate()`.

**What it does well.** In a world with no frictions and unlimited liquidity it
reproduces the target book's return to within **3.4 bps/yr** across six seeds —
false-positive rate **0%** at a 1%/yr threshold. Cost per dollar traded is
recovered **exactly**: 0.00 bps error at 5, 25 and 100 bps half-spreads.
Degradation is monotone in liquidity tightness.

**What it cannot do.**

| ADV multiple | cost, bps of traded | capped days |
|---|---|---|
| 1,000,000× | **31.00** | 0 |
| 100× | **31.00** | 1 |
| 5× | **31.00** | 173 |
| 1× | **31.00** | 886 |

Identical to two decimals across a million-fold range of liquidity. G7 charges
half-spread + slippage + commission on notional and **nothing that grows with
participation**. It models capacity as **delay** — unfilled orders are carried —
and never as **price**, which is the dominant capacity cost in the literature.
Even with a name's entire daily dollar volume equal to the position it must hold,
degradation reached only **0.065%/yr**, because an annual clock has a year to
work its orders down.

**Consequence.** Every capacity number this programme has quoted is a delay-only
**lower bound** — including NIGHT-5's "capacity breaks $100m → $500m" and
NIGHT-7's $50m rung. **CAPACITY-EDGE-1 is blocked as scoped:** it may not report
a capacity limit from this instrument without either adding a
participation-dependent impact term or labelling the result delay-only.

---

## 4. N5 — the corpse check is code now

`scripts/lint_prereg.py` scores a draft against all 298 recorded experiments —
148 graveyard rows, 89 registry trials, ~60 preregs — and returns BLOCKED /
DUPLICATE / RESURRECTION / PASS.

The distinction that earns its keep is **BLOCKED vs RESURRECTION**. The census
found the graveyard is mostly *not refuted*: 31 POWER, 29 IMPL and 14 DATA rows
never produced a usable number. Re-running those is often exactly right — with an
instrument that can see what the last one could not. So the escape hatch requires
naming it, and "we are trying again" does not parse as an instrument.

**It failed its own calibration three times before it was usable**, and each
failure is a test now:

1. The registry has no verdict *field* — outcomes were written into free text. A
   field read would have classed all 89 rows REGISTERED and the linter would
   never have blocked anything.
2. The blank `TEMPLATE.md` scored **BLOCKED** against a REJECTED trial on 56
   shared boilerplate terms. Document frequency measured across the *pool* never
   catches prereg furniture, because the pool is dominated by 148 short graveyard
   rows and the boilerplate sits at ~13%. Measured *within each source* it is
   caught.
3. Dogfooding caught the worst one: the linter **BLOCKED the IMAGE-RANK backlog
   item against N1's own preregistration**, a trial that had not run — because
   every prereg lists REJECTED in its decision-rule table as a possible future. A
   verdict now counts only when *attributed* ("Verdict: REJECT", or under a
   `## Result` heading). Across the folder: 27 BLOCKED → **17**, 22 PASS → **35**.

Two tests pin both directions against the real corpus: an invented mechanism must
PASS, and a randomly chosen real corpse must still be caught. Wired into the
`pre-register-trial` skill as step 0, with its limits stated — it compares
**wording**, and PASS means **unmatched, not novel**.

---

## 5. N6 — the verdict referee

Five mechanical checks, each derived from a specific failure this programme made
in a write-up rather than in a calculation: verdict-language (NIGHT-4),
MDE-missing, citation-transfer (NIGHT-7), cost-denominator (CANON §16), and
branch accounting.

Validated retroactively on the documents whose errors are known:

- **NIGHT-7B line 74, "The ensemble is CHEAPER by $19,390" → cost-denominator
  blocker.** That is the exact claim §2 above retracts, and the rule derived from
  it fires on it.
- Four genuine MDE omissions across the NIGHT-6 and NIGHT-7 verdicts.

Its own first implementation missed the NIGHT-7B claim, accepting any `/yr`
within four lines as a denominator — an unrelated CAGR gap below the sentence
satisfied it. Tightened to require a cost normalisation specifically.

The module prints what it **cannot** check at the top of its own output: whether
a qualifier is honest, whether a mechanism is plausible, whether the statistics
behind a state were computed correctly. A finding is a reading list, never a
verdict.

---

## 6. Receipts that leave the laptop

`/runs/` is gitignored — correctly, it holds derived market data — so every
receipt this programme cites lived on one machine, and a reviewer following
`runs/NIGHT7/T2c_TRIGGER_MOM_CONTROL.json` got a 404.

`docs/manifests/` now holds the committable half: SHA-256 per artifact, the code
SHA, and the receipts' scalar contents, which are sufficient statistics and
contain no vendor data. Plus `claim_coverage`, which resolves every number in a
verdict document against this night's receipts and prior nights'.

**NIGHT-7B's only unbacked numbers are the two instances of `$935k`** — the
figure quoted *from* a review in order to reject it.

That checker also failed its own calibration first: with a relative tolerance it
"backed" **86.6%** of deliberately fabricated numbers. Precision-aware matching
plus a per-claim collision test took that to **1.9%**, and `calibrate()` now runs
inside every manifest so no coverage figure is ever quoted without its
false-positive rate beside it.

**The citation ledger** (`docs/CITATIONS.json`) makes the qualifier a required
field. T1 was a prose gate, and three reviews still arrived carrying stripped
qualifiers the same night it was written. Lazy Prices, Maeso–Martellini and
3S-Trader are in the ledger precisely so that quoting them as expectations for
this book raises an exception.

---

## 6. N1 — learning the weights orders better and earns less

The first ML-selection test this factory has run on its own book. 1984–2022, 461
months, 50 annual refits, 13-month purge, everything downstream of the score
identical across arms. Leak check passes.

| arm | turnover | money vs R0 | NW(12) t | MDE | ρ vs R0 | **ΔIC vs R0** | **IC t** | verdict |
|---|---|---|---|---|---|---|---|---|
| R0 hand-written composite | 0.460 | — | — | — | — | — | — | control |
| R1 GBM, same 3 features | 0.469 | −1.45%/yr | −0.98 | 3.10% | 0.903 | **+0.0340** | **4.18** | IMPLEMENTATION_FAILED |
| R2 GBM, wide shelf | **0.401** | −3.33%/yr | −1.31 | 4.56% | 0.748 | **+0.0675** | **4.09** | IMPLEMENTATION_FAILED |
| R3 MLP, wide shelf | 0.526 | −2.44%/yr | −1.07 | 4.15% | 0.809 | **+0.0556** | **3.46** | IMPLEMENTATION_FAILED |

**Every learned ranker orders the cross-section better than the hand-written
composite, and decisively.** Mean monthly rank-IC against the forward 12-month
return goes from **0.124** for the composite to **0.158 / 0.192 / 0.180**, at
paired t-statistics of 3.5 to 4.2 over 461 months. Learning the weights is not a
wash — it is a large, repeatable improvement in ordering, and it appears even in
R1, which sees **exactly the same three features** the composite does.

**None of them makes more money.** All three are negative on paired net excess and
none reaches |t| 2.0. `IMPLEMENTATION_FAILED` for all three: the information is
present and this construction cannot monetise it.

**The obvious explanation is ruled out by measurement.** The standard story is
that ML books churn. R2 has the **best ordering and the lowest turnover in the
table** — 0.401 against the control's 0.460. Whatever stops the ordering
advantage reaching the book, it is not trading cost.

Two things worth recording:

- **The pre-compute power table was accurate.** The prereg predicted an MDE of
  4.65%/yr at ρ = 0.75; R2 came in at ρ = 0.748 and MDE 4.56%/yr. Writing the
  power check before the run cost twenty minutes and made every null in this
  table readable instead of arguable.
- **The two-instrument design is what saved this from being a vacuous null.**
  Judged on money alone, N1 returns three UNRESOLVEDs with MDEs of 3–4.6%/yr and
  nothing is learned. The ordering instrument has 461 observations and no
  portfolio-construction noise, and it is where the answer lives.

**Predictions: 3 hits, 1 partial, 1 miss.** Prediction 2 (wide arms order better)
HIT. Prediction 3 (no arm reaches +3%/yr) HIT. Prediction 4 (MLP ≈ GBM) HIT —
consistent with the 2026-06-15 read that algorithm choice is negligible.
Prediction 1 PARTIAL — R1's money leg came in under |t| 1.0 as predicted, but my
stated reason ("almost nothing to learn from three correlated signals") was
**wrong**: R1 improved ordering at t 4.18. Prediction 5 MISS — I expected power to
be the binding constraint and no resolution; the binding constraint turned out to
be **delivery**, which is a different and more useful answer.

**What I am not claiming.** Why better ordering does not reach a long-only
150-name book is *not* established here. The programme's own §28 receipt — that
99.9%/88% of a spread can live in the short leg a long-only book cannot hold — is
the obvious candidate, and rank-IC is a full-cross-section statistic while the
book buys only the top 150 of the small segment. That is a hypothesis.
`TRIAL-N1B-WHERE-DOES-THE-IC-LIVE-1` is registered to test it, and it is the
highest-value open item this night produced.

## 7. N2 — refusing the worst: the book already does it

Across 179 candidates this factory had only ever tested picking the top. The veto
acts on the eligible set at the annual rebalance, before selection; the book still
holds 150 names and simply draws deeper.

| arm | effect | NW(12) t | MDE at t 2 | ρ vs control | verdict |
|---|---|---|---|---|---|
| V1 accruals | +0.62%/yr | 1.57 | 0.65%/yr | 0.9952 | UNRESOLVED |
| V2 net share issuance | +0.37%/yr | 1.54 | 0.42%/yr | 0.9980 | UNRESOLVED |
| V3 distress (OScore) | +0.02%/yr | 0.16 | 0.24%/yr | 0.9993 | UNRESOLVED |
| V4 union of the three | +0.85%/yr | 1.84 | 0.78%/yr | 0.9931 | UNRESOLVED |
| **V5 placebo, random** | **+0.00%/yr** | **0.01** | 0.92%/yr | 0.9906 | UNRESOLVED |

**The placebo gate passes cleanly.** A size-matched random veto of the same 288
names per month moves the book by **0.00%/yr at t 0.01** — as close to nothing as
this instrument can measure. So the small positive numbers in V1, V2 and V4 are
attributable to their signals rather than to the act of vetoing.

**Every arm is UNRESOLVED at the 1.5%/yr bar, and this time the design was not
the problem.** MDEs came in at 0.24–0.92%/yr, far *below* the bar, because the
vetoed books correlate 0.993–0.999 with the control. The point estimates are
simply small: V4's upper bound is +1.63%/yr, which fails to exclude the bar only
just.

The honest summary is a pattern rather than a number: **three independent anomaly
families all point the same way, all below the bar, and the placebo is exactly
zero.** That is worth more than any single t-statistic here.

**The diagnostic is the real finding, and it was registered as prediction 4.**

| veto | share of the **held book** removed |
|---|---|
| V3 distress | **0.9%** |
| V2 net share issuance | 3.1% |
| V1 accruals | 6.2% |
| V4 union | 9.3% |
| **V5 random, same size** | **13.9%** |

A random veto of *identical size* removes 13.9% of what the book holds; the union
of three anomalies removes 9.3%, and distress removes 0.9%. **The composite is
already avoiding these names — distress at roughly 15× better than chance.** The
answer to "is refusing the worst worth more than picking the best?" on this book
is that **the two are largely the same operation**: a profitability tilt is an
implicit distress veto.

Turnover corroborates it. The anomaly arms sit within 0.03 of the control's 0.478
and need no G7; the **random** veto costs 0.579 — a size-matched veto of names the
book actually wanted is the expensive one.

Predictions: 1 HIT (placebo ~0), 2 **MISS** (I expected distress to be strongest;
it is by far the weakest), 3 HIT, 4 HIT. **3 of 4.**

## 8. N3 — seasoning: POWER_FAILED, and the buckets were not what they looked like

Within month, each tenure bucket against the other names held that same month:

| bucket | effect | NW(12) t | MDE at t 2 | share of name-months | exit hazard |
|---|---|---|---|---|---|
| **m1_6** | **+4.27%/yr** | **+2.10** | 4.89%/yr | 0.196 | **0.0069** |
| m7_12 | −0.97%/yr | −0.56 | 4.08%/yr | 0.189 | **0.0721** |
| m13_24 | −0.32%/yr | −0.21 | 3.23%/yr | 0.208 | 0.0333 |
| m25_plus | −1.84%/yr | −1.44 | 3.17%/yr | 0.407 | 0.0241 |

**Verdict `POWER_FAILED` at the pre-registered bar.** The weakest bucket could not
have seen a 2%/yr difference, so **band tuning does not close** — which was the
decision this diagnostic existed to settle, and it did not settle it.

Prediction 1 (flat within month) is a **MISS**: fresh entrants beat their fellow
holdings by +4.27%/yr at NW t 2.10. Prediction 2 is a **HIT**, and it is the more
useful one — instrument A, measured against the benchmark rather than within
month, put the same bucket at **+11.28%/yr, t 3.09**, inflating it **2.6×**.
Prediction 3 is a **HIT**: m25_plus carries 40.7% of name-months.

**The finding I did not anticipate, and it changes the reading.** The monthly
exit hazard is 0.0069 in m1_6 and 0.0721 in m7_12 — a **tenfold jump**. On an
annual clock a name bought at a rebalance *cannot be sold until the next one*, so
"months 1–6" is a window in which exit is structurally impossible and "months
7–12" is the window holding everything about to be dropped. These buckets are not
"fresh vs stale". They are **first half-year vs second half-year of the holding
period**, and a premium that lives there may be a property of the rebalance cycle
rather than of freshness.

`TRIAL-N3B-FRESH-ENTRANT-CONFOUND-1` registered, not run: the NIGHT-7B momentum
and volatility control battery, plus a **half-year placebo** that splits the
holding year at its midpoint for *every* tenure cohort. If incumbents show the
same first-half tilt, this is a calendar artifact of the annual clock. My
registered prediction is that the placebo fires.

## 9. A units bug in a published receipt

Found while reading N3's output: an MDE of **0.587** for a long-only equity book
is 58.7%/yr, which is not a detectable-effect size — it is a units error.
`mde_annualized()` multiplies by 12 itself, and five call sites handed it a
series already multiplied by 12.

**The damage, and its limit.** NIGHT-7's trigger receipts reported MDEs of 0.43
to 1.43 — **43% to 143% per year**. The true values are those divided by twelve:
3.6% to 11.9%/yr. **The finding is unaffected**: the 12-month trigger effect is
−8.19%/yr against a corrected MDE of 3.6%/yr, consistent with its NW t of −4.97,
and those scripts' verdict logic read t-statistics rather than MDEs. No published
prose quoted the wrong numbers, so no claim in a verdict document is wrong — but
the receipts were, and the manifest embeds receipts. Both are regenerated. The
older scripts (`pf4`, `pf5`, `pf6`, `pf7_exit_sweep`) always passed the raw
monthly series and were never affected.

`mde_annualized` now **raises** above 50%/yr rather than returning it. The
docstring states the contract in one line. The guard is honest about being a
backstop: a twelvefold inflation of a genuinely small MDE lands below the
threshold and still passes, and there is a test asserting exactly that.

## 10. The referee on this document

Run before shipping, as the extension list required. **Zero blockers.** Four
questions, all read and all legitimate: a derived ratio (47.7), a runtime corpus
count (298), an HTTP status code (404), and `$935k` — the fabricated figure
quoted from a review in order to reject it.

It was not clean first time. On its first pass over this document the referee
produced **nine blockers, eight of them false**, and fixing them improved the
instrument rather than the prose:

- **Table blindness.** An `MDE` column header sits above every row of a long
  table; a three-line window never reaches it. Context is now the whole table
  block for a table row.
- **`\bMDE\b` does not match "MDEs".** The word boundary fails on the plural, so
  a sentence that *did* state the MDE was flagged for not stating it.
- **A quoted claim was read as an asserted one.** The module blocked this
  document for containing the NIGHT-7B sentence it exists to criticise.

The one true positive it kept finding was mine to fix in the prose, not in the
code.

## 11. Ledger

| trial | branches | outcome |
|---|---|---|
| `TRIAL-N1-RANKER-VS-COMPOSITE-1` | 3 | IMPLEMENTATION_FAILED ×3 (§6) |
| `TRIAL-N2-NEGATIVE-SELECTION-1` | 5 | UNRESOLVED ×5, placebo PASS (§7) |
| `TRIAL-N3-SEASONING-1` | 1 | POWER_FAILED (§8) |
| `TRIAL-PF8-TRIGGER-CONFOUND-1` | registered, not run | 0 tonight |
| `TRIAL-N1B-WHERE-DOES-THE-IC-LIVE-1` | 0 (decomposes existing series) | registered, not run |
| `TRIAL-N3B-FRESH-ENTRANT-CONFOUND-1` | registered, not run | 0 tonight |
| `TRIAL-IMAGE-RANK-1` | backlog only, no compute | 0 |
| T1c, N5, N6, N7 | instruments, not strategies | 0 |

Denominator **827 → 836**.

## 12. What was not done, and why

**N4 (`LLM-VETO-CAL-1`) was not run.** The extension list called it cheap; it is
not. Scoring an LLM's veto/keep calls on masked historical 10-Ks against
later-arriving ground truth needs three things, and only one of them is in this
repository: CRSP delisting codes are here and already used by G7; **10-K text is
not**, and guidance-cut and restatement outcomes are **not**. Building the EDGAR
retrieval, the masking, and the outcome joins is a night's work in itself, and
the extension list's own stop rule put N1, N2 and N5 ahead of it. A half-built
calibration would have produced a number nobody could trust, which is the
failure mode this whole night was about. Registered properly and queued, with
the one usable ground-truth source named.

**The trigger penalty and T4b were not run.** Their amendments landed (§1), and
running either the same night the amendments were written would have defeated
the point of writing them before compute.

**No lane was touched, the holdout was not opened, and no LLM spend was
incurred** — the budget for the night went unused because the work that needed
it was the work that got deferred.
