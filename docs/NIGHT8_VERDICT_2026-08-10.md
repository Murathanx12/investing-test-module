# NIGHT-8 — the extension list, executed

**Date:** 2026-08-10 (Murat away) · **Branch:** `main` · **Data grade:** `crsp`
**Receipts:** `runs/NIGHT8/` · **Manifest:** `docs/manifests/NIGHT8_MANIFEST.json`
**Standing:** pre-register before compute · power check may refuse · placebo gate
on control-armed designs · G7 for turnover-sensitive claims · holdout locked ·
no lane writes · UNRESOLVED is a valid ending.

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

## 7. Ledger

| trial | branches | status |
|---|---|---|
| `TRIAL-N1-RANKER-VS-COMPOSITE-1` | 3 | see §8 |
| `TRIAL-N2-NEGATIVE-SELECTION-1` | 5 | see §9 |
| `TRIAL-N3-SEASONING-1` | 1 | see §10 |
| `TRIAL-PF8-TRIGGER-CONFOUND-1` | registered, not run | 0 tonight |
| `TRIAL-IMAGE-RANK-1` | backlog only, no compute | 0 |
| T1c, N5, N6, N7 | instruments, not strategies | 0 |

Denominator **827 → 836**.
