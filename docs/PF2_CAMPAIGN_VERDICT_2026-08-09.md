# PF-2 CAMPAIGN VERDICT — the successors, the product track, and Murat's 11th account

**Pre-registration:** `TRIALS/PREREG_PF2_SUCCESSORS.md`, sealed by commit
`06a0cf7` **before** any PF-2 configuration was computed.
**Governing rule:** `EXECUTION_STANDARD_2026-08-08.md` as amended 2026-08-09
(commit `001fa4d`) — G4a factor gate, FACTOR-HARVEST PRODUCT label,
NEAR-MISS(gate) class.
**Instrument re-validation:** the harness reproduced PF-1's ENGINE-ALPHA at
**+5.21 %/yr, delta 0.000000** under the PF-2 extensions. The instrument did
not drift.
**Holdout (2023-01 .. 2024-12) was NOT read.** The loader refuses it.

**Multiple-testing denominator, printed as required: 342 experiments** — 32
strategy books (24 candidate grid configurations + 2 product alternatives + 5
PF-1 bases re-run as meta assets + 1 re-validation book) + 300 turnover-matched
placebo books + 10 meta-portfolio books. Receipts:
`runs/PF2/CAMPAIGN_PF2_FINAL.json`, one scorecard JSON + markdown per
configuration, three placebo bands, `runs/PF2/META_COMMON_WINDOW.json`.

---

## 1. The result in one line

**One candidate cleared every historical gate — the first in this project's
history — and it did so on evidence that already existed on disk, which is
exactly why it is labelled a candidate and not a graduate.**

| candidate | window | net excess | t (NW) | blocks | ruin | FF5+UMD α (t) | verdict |
|---|---|---|---|---|---|---|---|
| **PF-PROF-COMPOSITE-150** | 40.2y | **+4.67 %/yr** | 2.85 (2.52) | **5/5** | **0.102** | **+5.01 % (3.39)** | **WINNER (ENGINE SKILL) — retrospective** |
| PF-ENGINE-ALPHA-2 | 59.5y | +5.21 %/yr | 3.77 (2.72) | 3/5 | 0.005 | +0.89 % (0.71) | FAILED — 2 gates |
| PF-INSIDER-2-TIEAWARE | 15.8y | −5.16 %/yr | −0.50 | 2/5 | 0.621 | +3.35 % (0.76) | FAILED — placebo + negative |
| PF-META-1 (registered base) | 58.5y | +3.28 %/yr | — | — | 0.599 | +0.72 % (0.25) | LOSES to equal-weight |

## 2. PF-PROF-COMPOSITE-150 — every gate, and the reason to distrust it anyway

Three profitability measures (GP, OperProfRD, CBOperProf) averaged as a rank
composite, **150 small-cap names**, monthly, 25 bps, 1982-11 .. 2022-12.

| gate | bar | result | |
|---|---|---|---|
| G1 material | ≥ +3.0 %/yr | **+4.67 %/yr** | PASS |
| G3 grid | ≥ 6 of 8 positive | **8 of 8** | PASS |
| G4 placebo | > p95 of 100 random books | +4.67 % vs max −0.77 % (p 0.0099) | PASS |
| **G4a factor** | **α ≥ +2%/yr AND t ≥ 2.0** | **+5.01 %/yr, t 3.39** | **PASS** |
| G6 ex-best-year | ≥ +1.5 %/yr | +3.36 %/yr | PASS |
| G6 ex-top-1% months | ≥ 0 | +3.18 %/yr | PASS |
| regime breadth | ≥ 4 of 5 blocks | **5 of 5** | PASS |
| G8 ruin | P(DD>60%) ≤ 0.20 | 0.102 | PASS |

It also beats the equal-weight universe by **+5.36 %/yr (t 5.06)** — the
"could a monkey have done this" control — and every one of its 8 grid
configurations is positive. Sub-period stability is unusually good: first half
**+5.00 %/yr**, second half **+4.33 %/yr**.

Two things the summary row hides, stated plainly. **"5/5 blocks" is thinner
than it sounds** — bear-2022 is +0.12 %/yr, which is positive by 12 basis
points and would flip on rounding. The other four are +5.10 %, +11.69 %,
+3.13 % and +12.48 %, so the gate is not carried by that block, but it is not
five convincing wins either. And the book's **max drawdown is −52.5 %, slightly
worse than the benchmark's −50.3 %** — its low ruin number comes from
recovering, not from falling less.

**Why it has factor alpha when ENGINE-ALPHA does not.** Its FF5+UMD loadings
are `mktrf 1.07, smb 0.98, hml −0.19, rmw 0.14, cma 0.00, umd −0.17`. The
striking number is **rmw = 0.14**: a portfolio built entirely from
profitability signals loads almost nothing on the published profitability
factor. RMW is a value-weighted, large-cap-dominated construction; this book is
an equal-weighted small-cap one. The small-cap profitability premium is simply
not spanned by RMW — which is what Novy-Marx reported and what these betas
independently reproduce. That is a real economic mechanism (G5), not a
statistical curiosity.

**The honest counterweight, stated as prominently as the result:**

1. **This is not a blind test, and the deciding number pre-existed the
   registration.** PF-1's grid already contained an N=150 arm, and its card on
   disk already carried `ff5_umd: {ann_alpha 0.0501, t_alpha 3.39}` — the exact
   number G4a was applied to. The prereg disclosed that PROF-150 was "partially
   known" (§2.2); this is the full extent of it. What PF-2 genuinely adds is
   the pre-declared 8-configuration grid, the N=150 placebo band, and
   adjudication under a rule frozen in advance — not a fresh observation of the
   deciding statistic.
2. **The best available evidence that I did not peek is that I predicted the
   opposite.** Registered prediction P5 said PROF-150 would **fail** G4a
   ("profitability *is* RMW, a published factor"). It passed at t 3.39. A
   contaminated forecaster would have predicted correctly. Readers should
   weight that as they see fit; it is the only evidence available and I am not
   in a position to certify my own attention.
3. **CAPM alpha is much weaker: +3.35 %/yr at t 1.48.** The FF5+UMD alpha
   exceeds it because the book carries `smb ≈ 0.98` into four decades in which
   SMB paid little — the model expects less than the strategy delivered, so
   alpha rises. That is a legitimate reading of a factor model and it is also a
   reminder that a large part of the claim is "held small caps and was not
   punished for it".
4. **Two gates that decide graduation have not run at all:** G2 (the untouched
   holdout) and G7 (the full daily simulator). Under the frozen standard,
   nothing graduates without them.

**Disposition: WINNER (ENGINE SKILL) on the historical gate ladder, recorded
as RETROSPECTIVE.** It does not seed a lane. It earns exactly one thing: the
right to a written holdout firing plan (§7), to be executed as a separate
attended step.

## 3. PF-ENGINE-ALPHA-2 — the registered fix cannot work, for arithmetic reasons

The registered question was whether a **constant** market allocation (never a
timing rule) could close ENGINE-ALPHA's only PF-1 failure, regime breadth.

| config | net excess | blocks | FF5+UMD α (t) | ruin | ×bench |
|---|---|---|---|---|---|
| base | +5.21 % | 3/5 | +0.89 % (0.71) | 0.005 | 15.58 |
| N50 | +5.46 % | 3/5 | +1.71 % (1.50) | 0.008 | 17.74 |
| quarterly | +5.21 % | 3/5 | +1.24 % (0.98) | 0.005 | 15.58 |
| blend 25 % | +3.95 % | 3/5 | +0.64 % (0.68) | 0.006 | 8.12 |
| largemid | +3.60 % | 3/5 | −0.41 % (−0.38) | 0.011 | 6.78 |
| N50 + blend 40 % | +3.30 % | 3/5 | +0.99 % (1.45) | 0.013 | 5.79 |
| blend 40 % | +3.18 % | 3/5 | +0.49 % (0.65) | 0.009 | 5.42 |
| blend 50 % | +2.65 % | 3/5 | +0.40 % (0.64) | 0.013 | 4.12 |

**Every configuration is 3/5. Not one blend moved the gate.** The reason is
arithmetic, and I should have derived it before registering the fix:

> blended excess = X·mkt + (1−X)·r_s − mkt = **(1−X) · (strategy excess)**

A constant blend **scales every regime block's excess by (1−X) and preserves
its sign**. Measured, block by block, at X = 0.50: pre-2008 +6.78 → +3.42,
GFC +10.58 → +5.41, post-crisis bull −1.48 → −0.70, COVID −12.20 → −6.12,
bear-2022 +14.82 → +7.20. Every ratio ≈ 0.50; no sign flips. **A core-satellite
blend can never convert a negative block into a positive one.** It spends
excess return and buys no breadth.

That is a real and reusable finding — the regime-breadth gate is *invariant*
to allocation and can only be moved by changing *selection*. It is also a
methodological lesson recorded against myself: **P1 was not merely wrong, it
was unfalsifiable by construction, and one line of algebra before registration
would have shown it.**

**Verdict: FAILED** (regime breadth + G4a). Its product bar nevertheless
**passed** — 15.58× benchmark terminal wealth against ALT-MULTIFACTOR 8.94×,
ALT-VALUE-PROF 6.82×, equal-weight universe 1.13×, benchmark 1.00×, at ruin
0.005. Under the rule as frozen, a candidate failing two gates cannot take the
FACTOR-HARVEST PRODUCT label, and it does not get it here. See §8 for the
question that raises about the gate itself.

## 4. PF-INSIDER-2-TIEAWARE — the fix worked, the signal still did not

The construction defect was real and is now measured: PF-1's buyer-count
signal carried a mean of **14 distinct values in its top 100 names** — 86 of
100 selections decided by arbitrary tie-break. The replacement (dollar-weighted,
6-month recency half-life, scaled by the name's own dollar volume, winsorized
at $50M) carries **100 of 100 distinct**. The tie problem is fixed.

The returns did not follow: **−5.16 %/yr, 0 of 8 configurations positive,
placebo FAIL (p = 0.71 — 71 of 100 random books beat it)**. Its predecessor
was −5.48 %/yr, so prediction P6's "materially better" clause is a MISS; the
family verdict is unchanged.

One reading worth recording: the tie-aware signal **alone** (no GP sleeve)
prints −0.25 %/yr with 4/5 positive blocks, far better than the −5.16 % of the
combination. The drag in this window came from the quality sleeve, not the
insider signal. That is a hypothesis, not a result.

**Per the closing rule frozen in the pre-registration, the insider portfolio
family is now CLOSED.** No further insider construction is registered without
*new data* — not a new construction of the same data.

## 5. PF-META-1 — Murat's "11th account", answered

Six PF-1 strategies as assets; hold whichever has been winning; 25 bps to
switch. Recomputed on the **common window all books share** (1965-07 .. 2022-12),
because a 24-month lookback cannot trade until month 25 and comparing terminal
wealth across different inception dates is not a comparison:

| book | net excess | ×bench | ruin | maxDD | FF5+UMD α (t) | cash |
|---|---|---|---|---|---|---|
| PF-META-1__L12T2 *(grid)* | +6.32 % | **24.72** | 0.062 | −45.1 % | +2.64 % (1.38) | 0.0 % |
| META-BEST-SINGLE *(hindsight ref)* | +5.34 % | 15.18 | 0.004 | −35.4 % | +0.94 % (0.72) | 0.0 % |
| PF-META-1__L12T1_FREE *(no costs)* | +5.29 % | 14.84 | 0.510 | −47.7 % | +2.05 % (0.72) | 0.0 % |
| **META-EW** *(the control)* | **+3.84 %** | **7.18** | 0.097 | −51.4 % | +1.87 % (1.21) | 0.0 % |
| **PF-META-1** *(registered base)* | **+3.68 %** | **6.63** | 0.604 | −50.5 % | +0.72 % (0.25) | 0.0 % |
| PF-META-1__L6T2 | +3.41 % | 5.78 | 0.118 | −51.3 % | +0.45 % (0.26) | 0.0 % |
| PF-META-1__L12T1Q | +2.38 % | 3.42 | 0.663 | −61.9 % | −0.06 % (−0.02) | 0.0 % |
| PF-META-1__L6T1 | +2.23 % | 3.17 | 0.548 | −56.1 % | −0.62 % (−0.23) | 0.0 % |
| PF-META-1__L24T1 | +1.04 % | 1.72 | 0.840 | −67.3 % | −1.76 % (−0.59) | 0.0 % |
| PF-META-1__L24T2 | +0.84 % | 1.55 | 0.480 | −56.3 % | −2.24 % (−1.10) | 0.0 % |

**P7 HOLDS. The registered winner-chasing rule loses to simply holding all six
strategies equally** — 6.63× versus 7.18×, at *six times* the ruin probability
(0.604 vs 0.097) and 164 strategy switches versus 3. Switching costs alone take
1.6 %/yr (compare the base to the zero-cost variant). Timing at the strategy
level behaves exactly like timing at the stock level: it pays for the privilege
of being late.

**P8 MISSES.** One grid configuration — 12-month lookback, hold **top-2** —
returns +6.32 %/yr and 24.72× benchmark, beating both the equal-weight control
and the hindsight-chosen best single strategy, at ruin 0.062.

**I am not promoting it, and the grid's own shape is the reason.** Its
neighbours collapse: at hold-2, lookback 6 gives +3.41 % and lookback 24 gives
+0.84 %, so the 12-month cell is roughly double its nearest neighbours in both
directions. A real effect degrades smoothly; a spike surrounded by mediocrity
is what a lucky cell looks like. The one part that *is* mechanically credible is
top-1 → top-2: holding two strategies instead of one cuts ruin from 0.604 to
0.062 across every lookback, which is diversification doing what diversification
does, not a discovery.

Per the frozen rule, a grid config that passes where the base fails is a
**PF-3 registration, never a graduate**. If Murat wants the 11th account, this
is the honest form of it: *equal-weight all the lanes* (the control that won),
not *copy the winner* (the idea that lost).

## 6. Placebo bands (G4, hard gate)

100 turnover-matched random books per candidate, 300 in total.

| candidate | strategy excess | placebo mean | placebo p95 | placebo max | empirical p | gate |
|---|---|---|---|---|---|---|
| PF-PROF-COMPOSITE-150 | +4.67 % | −2.18 % | −1.28 % | **−0.77 %** | 0.0099 | **PASS** |
| PF-ENGINE-ALPHA-2 | +5.21 % | −1.95 % | −0.30 % | +0.91 % | 0.0099 | **PASS** |
| PF-INSIDER-2-TIEAWARE | −5.16 % | −3.69 % | +0.36 % | +1.85 % | 0.713 | **FAIL** |

PROF-COMPOSITE-150's band is the strongest control result the project has
produced: **not one of its 100 random books beat the benchmark at all** (best
was −0.77 %/yr) while the strategy earned +4.67 %/yr at matched turnover
(2.40 vs 2.47). The insider book, by contrast, was beaten by 71 of 100 random
books.

## 7. Holdout firing plan (WRITTEN, NOT EXECUTED)

Triggered only by PROF-COMPOSITE-150 clearing the historical ladder. Firing is
a separate **attended** step requiring Murat present; nothing here runs it.

- **Instrument:** `load_spine(..., allow_holdout=True)`, the single documented
  path past the loader's refusal.
- **Window:** 2023-01-31 .. 2024-12-31 (24 months), read **once**.
- **Spec:** frozen exactly as registered — three profitability signals, small
  segment, N=150, monthly, flat-25. No re-tuning, no variant selection.
- **Pre-registered pass bar (frozen here, before the read):** positive net
  excess CAGR vs the CRSP VW benchmark over the 24 months. Nothing else — a
  24-month window has no power for a t-statistic and quoting one would be
  theatre.
- **Failure is recorded and final.** A failed holdout is not re-run, not
  re-windowed, and does not become a "different question". Post-hoc edits
  contaminate and require a *new* holdout, which does not exist.
- **Even a pass does not seed a lane.** G7 (daily simulation) still sits
  between this and any paper account, and G9 is Murat's flag.

## 7b. Pre-registered predictions, scored

| # | Prediction | Result |
|---|---|---|
| P1 | At least one blend config reaches ≥4/5 regime blocks | **MISS** — 0 of 8; and it was arithmetically impossible (§3) |
| P2 | No ENGINE-ALPHA-2 config passes G4a | **HIT** — best was N50 at +1.71 %, t 1.50 |
| P3 | Blend 0.50 falls below the +3 %/yr bar | **HIT** — +2.65 % |
| P4 | ENGINE-ALPHA-PRODUCT beats all three investable alternatives | **HIT** — 15.58× vs 8.94 / 6.82 / 1.13 |
| P5 | PROF-COMPOSITE-150 clears G1 and ruin but FAILS G4a | **MISS** — passed at α +5.01 %, t 3.39 |
| P6 | INSIDER-2-TIEAWARE beats its predecessor materially, still under +3 % | **MISS** on "materially" (−5.16 % vs −5.48 %); HIT on the failure |
| P7 | **PF-META-1 does NOT beat META-EW** | **HIT** — 6.63× vs 7.18× |
| P8 | No META config beats META-BEST-SINGLE | **MISS** — L12T2 at 24.72× vs 15.18× |

**4½ of 8** (P6 splits). Better than PF-1's 2 of 5, and the two misses that
matter point in opposite directions: I was too pessimistic about the small-cap
profitability book and too confident that a blend could move a gate it cannot
touch.

## 8. Lessons recorded (forward-only; PF-2's own verdicts stand as adjudicated)

1. **Derive the algebra of a gate before registering a fix for it.** The blend
   family could not have moved regime breadth under any X. One line of algebra
   would have replaced eight backtests.
2. **The regime-breadth gate may be mis-specified for long-only factor books.**
   Requiring positive excess in ≥4 of 5 blocks asks a value/quality book to beat
   the market during mega-cap melt-ups, which is close to requiring dominance
   rather than edge. ENGINE-ALPHA-2 delivers 15.58× the market's terminal wealth
   at two-thirds its drawdown and cannot graduate. **This is flagged as a
   question for Murat, not changed** — retro-fitting a gate to admit the
   strategy that just failed it is precisely the sin the standard exists to
   prevent. Any change is dated, forward-only, and applies to PF-3 onward.
3. **A number already on disk is not a blind test**, even when the rule that
   judges it was frozen first. PF-3 should distinguish *registered-and-unread*
   from *registered-and-recomputed* in the receipt itself.
4. **Process hygiene:** two campaign processes ran concurrently for ~10 minutes
   (an orphaned launch plus the tracked one) before being detected and killed —
   the same incident class as PF-1. Write-once artifacts and deterministic
   computation meant no result was affected, and the duplicate's outputs are
   bit-identical by construction. Recorded because it is now twice.

## 9. What graduates tonight

**Nothing.** No lane seeded, no flag requested, no `paper_nav` touched, holdout
unread. One candidate earned a written holdout plan; one family closed; one
architectural idea (winner-copying) was answered with its own receipt.
