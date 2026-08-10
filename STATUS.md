# STATUS — handoff after ARENA-1 (2026-08-11)

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
