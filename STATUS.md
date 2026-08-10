# STATUS — handoff after NIGHT-8 (2026-08-10)

## Where the code is

* `main` (Aegis module) — NIGHT-7 and NIGHT-7B merged; **NIGHT-8 committed on
  `main`**. Suite green.
* `aegis-finance` `main` — CANON §2 scoped by data grade, §15 scoped to path
  dependence, **§16 added** (a cost comparison needs a denominator that is not
  the winner's).
* Holdout unread throughout. Nothing promoted. No lane seeded, no flag flipped,
  no `paper_nav` touched, no keys changed. **LLM spend this night: $0** — the
  work that needed the budget (N4) is the work that got deferred, and it was
  deferred for a stated reason rather than quietly dropped.

## What NIGHT-8 found

Full detail: `docs/NIGHT8_VERDICT_2026-08-10.md`. Receipts in `runs/NIGHT8/`,
hashes and embedded scalars in `docs/manifests/NIGHT8_MANIFEST.json`.

**Three of five findings are about instruments, and two retract published
claims.** That is the right shape for this programme right now: NIGHT-7's lesson
was that the errors live in the apparatus and the write-up rather than the
arithmetic, and tonight the apparatus was pointed at itself.

**1. The clock ensemble is NOT cheaper — NIGHT-7B is retracted.** Both arms start
at the same NAV and end at different ones, so totalling cost in *dollars* rewards
the arm that compounded less. Normalised by average NAV the ensemble is **3.54
bps/traded and 0.011 pt/yr worse at $1m**, and indistinguishable at $50m. Three
nights, three answers, from three denominators. The case for the ensemble rests
entirely on removing the 2.45 pt/yr date-luck range — not on cost. **CANON §16.**

**2. G7 cannot price impact.** Cost per dollar traded is **31.00 bps at ADV
multiples of 1,000,000×, 100×, 5× and 1×** — identical across a million-fold
range of liquidity. It models capacity as *delay*, never as *price*. Every
capacity number this programme has quoted is a **delay-only lower bound**,
including NIGHT-5's "$100m → $500m" and NIGHT-7's $50m rung. **CAPACITY-EDGE-1 is
blocked as scoped.** What G7 *does* do well is now measured: 0% false positives
in a frictionless world, cost recovered to 0.00 bps.

**3. N1 — learned rankers order better and earn less.** All three (GBM narrow,
GBM wide, MLP wide) beat the hand-written composite on rank-IC: mean IC 0.124 →
**0.158 / 0.192 / 0.180**, paired t **4.18 / 4.09 / 3.46** over 461 months. None
makes more money; all three `IMPLEMENTATION_FAILED`. **Turnover is ruled out by
measurement** — the best-ordering arm had the *lowest* turnover (0.401 vs the
control's 0.460). The pre-compute power table was accurate to within 2%.

**4. N2 — the book already refuses the worst.** A size-matched random veto moves
it **+0.00%/yr at t 0.01** (a clean placebo pass); accruals/issuance/distress
vetoes are all positive but below the 1.5%/yr bar. The diagnostic is the finding:
a random veto removes **13.9%** of the held book, the union of three anomalies
**9.3%**, distress alone **0.9%**. A profitability tilt is an implicit distress
veto.

**5. N3 — seasoning POWER_FAILED, and the buckets were not what they looked
like.** Fresh entrants beat fellow holdings by +4.27%/yr (NW t 2.10) but the
weakest bucket's MDE is 4.89%/yr against a 2%/yr bar. The exit hazard is
**0.0069** in months 1–6 and **0.0721** in months 7–12 — on an annual clock a
name *cannot* be sold before the next rebalance, so these buckets are first
half-year vs second half-year, not fresh vs stale. Band tuning does **not** close.

**6. A units bug in a published receipt.** `mde_annualized()` annualises its
input; five call sites pre-annualised. NIGHT-7's trigger receipts reported MDEs
of **43%–143%/yr**; true values are those ÷12. The *finding* is unaffected (12m
effect −8.19%/yr vs corrected MDE 3.61%/yr) and no prose quoted them, but the
receipts were wrong and are regenerated. The function now raises above 50%/yr.

## New machinery, all of it calibrated before use

| tool | what it does | its own error rate |
|---|---|---|
| `scripts/lint_prereg.py` | corpse-check vs 301 recorded experiments; BLOCKED / DUPLICATE / RESURRECTION / PASS | failed calibration 3× first; TEMPLATE.md no longer self-blocks; FP and FN pinned by tests on the real corpus |
| `discipline/manifest.py` | committable receipts + claim coverage | fabricated numbers "backed" **86.6% → 1.9%**; `calibrate()` ships inside every manifest |
| `discipline/citations.py` | qualifier is a **required field** | a citation that does not declare transfer does not load |
| `discipline/referee.py` | 5 checks from 5 real write-up failures | 9 blockers on its first pass over this night, 8 of them false; fixed, then **0 blockers** |

## Queue — nothing here is blocked on Murat

1. **`TRIAL-N1B-WHERE-DOES-THE-IC-LIVE-1`** — the highest-value open item. Decile
   IC decomposition + top-150-only IC. If the learned rankers' advantage sits in
   the bottom deciles (the §28 hypothesis), a long-only book structurally cannot
   collect it, and a symmetric regression loss is the wrong objective.
2. **`TRIAL-PF7B-TRIGGER-PENALTY-1`** — amended and ready; all arms through G7.
3. **T4b selection bootstrap** — amended, implementation frozen, coverage matrix
   first.
4. **`TRIAL-PF8-TRIGGER-CONFOUND-1`** — the path-geometry placebo is the sharp test.
5. **`TRIAL-N3B-FRESH-ENTRANT-CONFOUND-1`** — half-year placebo; I predict it fires.
6. **An impact term for G7**, or CAPACITY-EDGE-1 stays blocked.
7. **N4 LLM-VETO-CAL-1** — blocked on an EDGAR retrieval build, not on a decision.
8. `TRIAL-IMAGE-RANK-1` — backlog, gated on N1b.

## Decisions that are Murat's

Unchanged from NIGHT-7B. Nothing new tonight requires him: no lane, no flag, no
capital, no key, no claim that leaves the repository.
