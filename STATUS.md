# STATUS — handoff after NIGHT-11 (2026-08-11)

**Read `aegis-finance/docs/SESSION_2026-08-11_NIGHT11.md` first**, then
`docs/REVINFO_1_VERDICT_2026-08-11.md` and
`aegis-finance/docs/ROADMAP_OPTIMUS_BRAIN_NIGHT11.md`.

## THE HEADLINE

**The programme has its first licensed Layer-1 evidence, and the instrument that
produced it has had its own promise verified against known answers.**

* **REVINFO-1** — analyst-revision information is REAL in **small caps out to
  about six months**. `tgt_rev_breadth` small **+9.36 %/yr at t 4.87** against
  its own MDE of 5.76, decaying 7.32 / 5.45 / 2.95 at h=3/6/12.
  `eps_rev_breadth`, never Layer-1 tested before, is the most persistent
  (t 5.10 / 4.71 / 3.65). **7 of 32 INFORMATION_PRESENT, 21 UNRESOLVED, 4
  NO_INFORMATION. Not one large-cap arm clears its MDE at any horizon.**

* **The instrument is calibrated.** Power at its own MDE under the significance
  rule measured **81.0%** against a target of 80 — the CANON §19 promise,
  checked against planted effects for the first time. 0.0% false positives,
  0.000 %/yr bias. `docs/INSTRUMENT_INFORMATION_CALIBRATION_2026-08-11.md`.

**This licenses a Layer-2 test and NOTHING else.** The spread is dollar-neutral
and Round 16 measured 88–99.9% of a comparable spread in the short leg a
long-only book cannot hold. **The short-leg decomposition is the cheapest next
test and it can kill the whole family.**

## THREE THINGS THAT WERE WRONG AND ARE NOW MEASURED

1. **The MDE and the t-stat used different standard errors** (P0-A). Fixed.
   ANALYST-IBES-1's detection range **6.3–19.9 → 6.47–24.82 %/yr**; 0 of 10 arms
   above their MDE before and after, so the NIGHT-10 finding got STRONGER.

2. **The external reviews' 4–10x power gain does not exist.** Measured on the
   real panel: **0.98x to 2.11x, median 1.63x** — and **0.98x/0.99x in large/mid,
   i.e. none at all**. A test asserting >2.0 failed at 1.31 and the failure is
   kept in the test file. An 8 %/yr MDE becomes ~5: it reopens some corpses and
   does not make the standard design adequate.

3. **The new instrument's own verdict rule was wrong** and real data caught it.
   `NO_INFORMATION` labelled arms at **t = 2.21** and **t = 2.72** "evidence of
   absence". It is now a one-sided equivalence bound; re-running the grid changed
   **7 of 32 verdicts — 5 false kills prevented, 2 kills correctly ISSUED.**

## THE CONSTRAINT THE RESCUE QUEUE MUST BE BUILT AROUND

The control arm `tgt_upside` (PERVERSE/CLOSED at −16.70 %/yr through a top-50
book) reads **−0.16 %/yr, t −0.03** cross-sectionally, and **+1.18 at the decile
level**. Its perversity lives in the extreme top ~3% where lottery junk sits.
The revision signals do the opposite — they STRENGTHEN as the instrument
concentrates (+9.36 breadth → +13.21 decile), so their information is broad.

⇒ **a corpse killed by a concentrated top-50 book is NOT automatically
re-testable by a cross-sectional instrument.** Every graveyard rescue carries
BOTH a cross-sectional and a tail-concentrated arm, or the queue will exonerate
tail-perverse signals by averaging their perversity away.

## NEXT, IN ORDER

1. The half-life as a **paired difference** (CANON §18). No half-life number may
   be quoted until then — the decay is monotone in every arm but untested.
2. **The short-leg decomposition** — highest information per unit of compute.
3. Layer 2, the decision boundary. This one **accrues** to the denominator.
4. The rescue queue, with both arms.
5. The roadmap: belief state, prediction ledger, category routing, LLM
   specialists, seeding the shadow books.

## STILL OWED BY MURAT

cash · QUBT 300 vs 200 · rulings on five kill conditions · `confirmed: true` ·
**a real `ANTHROPIC_API_KEY`** (still EMPTY — every LLM finding to date is a
finding about DeepSeek) · seeding the shadow books · the graceful-degradation
ruling (refusal → market-weight core + evidence-scaled tilts).

---

# Previous handoff — NIGHT-10 (2026-08-11)

**Read `aegis-finance/docs/HANDOFF_NIGHT10.md` first.**

## THE HEADLINE

**Across 21 configurations, ZERO reported an effect above their own 80%-power
MDE.** The standard adjudication shape this programme uses — EW top-50, monthly,
2002–2022 — resolves **6.3 to 19.9 %/yr**, roughly double the largest credible
equity anomaly.

* **ANALYST-IBES-1** re-run through the parent's own Factory (8 of 10 arms
  reproduce their published gross excess to **0.00 points**; the two
  `tgt_upside` arms do not and their readings are WITHHELD): 0 of 10 above MDE,
  1 of 10 significant at 5%.
* **HERESY-1** (research-only forever, control reproduced its kill): **11 of
  11** forbidden configurations below their MDE, across **6 distinct** closed
  signals.

A kill from such a design is **absence of evidence**, and this graveyard has
recorded it identically to **evidence of absence** for 195 experiments.

**Nothing is reopened.** Affected corpses get a `kill_power: INADEQUATE`
annotation and nothing else. Reopening one needs its own pre-registration, the
corpse as a control arm, and an instrument whose MDE clears the effect sought.
A multi-instrument kill is not overturned by one underpowered arm.

## The small-cap "disagreement" was never a disagreement

ANALYST-IBES-1 moved small to UNRESOLVED because A2 (+6.05 %/yr) and A3
(−0.73 %/yr) disagreed in sign. Tested on the **paired** monthly series
(correlation 0.578): mean difference **+3.70 %/yr, SE 3.60, t = 1.03.**

⇒ **CANON §18**: a registered prediction that two constructions AGREE is a claim
about their DIFFERENCE and must be tested as one.

**ANALYST-IDENT-1 → POWER_FAILED** before any arm ran: registered MDE target
4.0 %/yr, realised **10.8**, against a disputed gap of 6.8.

## Also on disk

* **`lint_batch()`** — `lint()` could never ask whether a batch is as many ideas
  as it claims. Ten LLM hypotheses each passed against 306 priors while 37 of
  their 45 mutual pairs sat at or above the 0.30 block threshold: **one
  connected component**. Calibrated first (8 real preregs → 6 groups; the only
  merge was the three genuine 13D/G variants). ⇒ **CANON §20**.
* **A correction.** The published "+4.87 %/yr false-discovery bar" does not
  trace to its receipt: `null_calibration` says **+2.73** (one seed), three null
  seeds give 2.73 / 4.16 / 7.43, and +4.87 is the real-data equal-weight control
  — the same genome as the separately-published "4th of 384". Two of the four
  headline numbers are one measurement counted twice. **ARENA-1's null survives
  at every candidate bar** (Bonferroni p_adj 1.000), and everything else in it
  validated on disk.

## Where the code is

* **Aegis module `main` `463bd0d`** — HERESY-1, ANALYST-IDENT-1, the power
  audits, `lint_batch`.
* **aegis-finance `main` `3847b2b`** — the registry-disciplined recommendation
  engine, the Investment Committee page, portfolio factory, capital frontier,
  LLM research roles, CANON §18–20.
* Holdout unread. No lane seeded, no flag flipped, no `paper_nav` touched, no
  capital, no order path. **LLM spend $0.0067 of $30.**
* Suite: **3,278 passed, 3 skipped.**

## What Murat owes

cash · QUBT 300-vs-200 ($893 of NAV, both carried) · rulings on 5 proposed kill
conditions (ABSI/AMSC/HUBS/KYTX/SLDP) · `confirmed: true` on the book.
**New: `ANTHROPIC_API_KEY` is present in `.env` but empty**, so the Claude path
was unavailable all night.

## What Optimus wants next

**Raise instrument power before searching again** — everything else is
downstream of a detection threshold that cannot see the effects being hunted.

---

## Previous status (ARENA-1, 2026-08-11)

**Read `aegis-finance/docs/HANDOFF_ARENA1.md` first.** It carries the four
numbers, the one thing Murat has to do, and the contradiction the product now
prints about itself. `aegis-finance/docs/RESEARCH_PM_FLYWHEEL.md` is the
architecture Murat asked for: research and portfolio management as one loop
rather than two priorities competing.

## Where the code is

* **Aegis module `main` `580c9ed`** — ARENA-1 and ANALYST-IBES-1.
  `d0ab548` froze the 384-genome manifest *before* anything was scored.
* **aegis-finance `main`** — the book reconciliation, the signal registry, the
  opportunity funnel, the shadow register and the evidence-conflict warning.
* Holdout unread. No lane seeded, no flag flipped, no `paper_nav` touched, no
  capital, no order path. **LLM spend: $0.**

## The four numbers

| | |
|---|---|
| **+4.87 %/yr** | false-discovery bar: best of 384 portfolios when nothing predicts anything |
| **−8 to −18 %/yr** | analyst-implied upside as a picker, **gross**, 21 years of PIT IBES |
| **+1.5 to +6.1 %/yr** | analyst target **revisions**, gross — real, net-dead on 10× turnover |
| **4th of 384** | where a book picking names **at random** ranked in the Arena |

## ANALYST-IBES-1 — the honest backtest of Murat's process

`docs/ANALYST_IBES_1_VERDICT_2026-08-11.md`. Receipts
`runs/ARENA1/ANALYST_IBES_1/`.

The WRDS probe found `ibes.ptgdet` readable, so the object retail vendors gate
at 402/403 was available all along and B1's conclusion was true of the retail
layer only. 6 tables pulled, 9.6 m rows, 1976–2026, IBES→CRSP link match 92.7 %.

**The corpse linter cut the trial before a number was computed.** It matched
the first draft against TRIAL-TGT-REBUILD, TRIAL-BRAIN-005-revisions and
VOID-TGT-UPSIDE-B3B-B3C; reading those three reduced 6 arms to 2 accruing arms,
because EPS revisions and target dispersion had already been killed. What was
genuinely unrun is narrower than "analyst revisions" — the *target*-revision
objects in `ibes.ptgsumu`, a table never pulled here before.

Both replication arms reproduced their known kills, so the accruing arms are
readable. **Levels lose 8–18 %/yr gross. Revisions earn 1.5–6.1 %/yr gross and
die on turnover.** The two revision constructions **disagree in sign in the
small segment**, so by the registered rule the idea is not identified there and
no verdict may be issued. Nothing graduates.

The levels-vs-revisions distinction the PM was built on is real and now
measured. Its tradability is not established.

## ARENA-1 — 384 portfolios, frozen first

`docs/ARENA1_REPORT_2026-08-11.md`. Manifest sha `f7f7e7ef7457be50`.

95 of 384 positive, 66 pass the frozen selection rule, **2** clear the
false-discovery bar, both at t ≈ 1.2, Bonferroni p_adj = 1.000. Two of the top
eight pick their names at random. **ARENA-1 is a null.**

**The pre-registration worked visibly:** the highest-excess genome (G0245,
+6.06 %/yr, t 2.69, 7/7 regime blocks) is excluded because turnover is 3.03
against a frozen gate of 3.00. Recorded, not promoted.

**Power curve:** the Arena reliably separates truth from noise only at a
planted decile spread of **+8 %/yr** or more.

## Three defects found, each of which would have produced a confident wrong answer

* The synthetic world generator reconstructed returns *after* planting in a way
  that **cancelled the plant exactly**. Every known-answer test would have run
  against a null world while reporting an effect size.
* A pure **noise** signal shows a **+1.7 %/yr decile spread** in that generator,
  because persistent AR(0.8) noise correlates with the fixed beta draw and holds
  it for years. Kept as part of the null and reported, not tuned away.
* **Scoring pass 1 is VOID**: it benchmarked against a monthly-rebalanced
  equal-weight universe earning 17.97 %/yr small and 25.69 % largemid, against
  7.7–8.0 % buy-and-hold. All 384 genomes were negative against it — including
  the control, which is what exposed it.

## The honest gap in the flywheel

The Arena **did not find** a planted +8 %/yr analyst effect, because the
registry grades that signal RISK_INPUT so no analyst-*led* genome exists in the
pool. **The search can confirm what the lab believes and can never overturn
it.** A "heresy sleeve" is registered as the fix and deliberately not built.

## Decisions that are Murat's

**Cash.** That is the whole list. Holdings, share counts and 7 of 12 cost bases
were recovered from `book_lanes.yaml` + the conviction decision log + the
January PDF; he should never have been asked to re-type them. Two smaller
confirmations: QUBT 300 or 200, and that MSTR / FSLR / ELF / APLT are exited.

## Queue

1. **Close the evidence conflict** — the funnel's output becomes the PM's
   candidate list, replacing a watchlist ranked on a PERVERSE signal.
2. The **heresy sleeve**, so the loop can run backwards.
3. **Fit `TARGET_HAIRCUT`** — IBES now makes an empirical estimate possible.
4. **Per-analyst reliability** from `ptgdet` (17,364 analyst codes on disk;
   needs `ibes.adj` because the values are download-date adjusted).
5. Placebo band on ANALYST-IBES-1 (dropped for time, declared).
6. Health canary for the registry / funnel / shadow ledger.
7. **Background, unchanged:** G8 capacity ladder, PF8 trigger confound, T4b,
   N3b, the phase axis.
